"""DEM tiles for susceptibility_v01: NASADEM (registered primary, SRTM Feb 2000) and Copernicus GLO-30 (documented
per tile with its TanDEM-X acquisition period; not a registered training input).

  python -m preslide.susceptibility.dem fetch gorkha_2015|far_western_nepal|rer2023 [--limit N]
  python -m preslide.susceptibility.dem usability   -> reports/susceptibility_v01/dem_tile_usability.json
"""
import argparse
import json
import math
import re
from pathlib import Path

import shapefile
from pyproj import Transformer

from ..common import read_json, write_json
from .download import download_object, fetch_json
from .inventory import RAW, layer_crs
from .paths import DATA, REPORT, config, guard

DEM = DATA / 'dem'
COP_BASE = 'https://copernicus-dem-30m.s3.amazonaws.com'
STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1'
EXTENT_LAYERS = {'gorkha_2015': 'MappingExtent20170209.shp', 'far_western_nepal': 'LandslideInventory_FarWesternNepal_AOI.shp',
                 'rer2023': 'RER2023_V1.shp'}


def extent_bbox_lonlat(dataset):
    shp = next((RAW / dataset / 'extracted').rglob(EXTENT_LAYERS[dataset]))
    with shapefile.Reader(str(shp)) as r:
        b = r.bbox
    t = Transformer.from_crs(layer_crs(shp), 4326, always_xy=True)
    pts = [t.transform(x, y) for x in (b[0], b[2]) for y in (b[1], b[3])]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def tiles_for(bbox):
    lon0, lat0, lon1, lat1 = bbox
    return [(lat, lon) for lat in range(math.floor(lat0), math.floor(lat1) + 1)
            for lon in range(math.floor(lon0), math.floor(lon1) + 1)]


def cop_name(lat, lon):
    return f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"


def cop_temporal_coverage(xml_text):
    """TanDEM-X acquisition period of the tile from its metadata (start, stop as ISO dates)."""
    start = re.search(r'<tsxx:tsxx_startTime>([^<]+)<', xml_text)
    stop = re.search(r'<tsxx:tsxx_stopTime>([^<]+)<', xml_text)
    if not start or not stop:
        raise RuntimeError('Copernicus tile metadata has no temporal coverage; tile cannot be dated')
    return start.group(1)[:10], stop.group(1)[:10]


def fetch_cop(lat, lon):
    name = cop_name(lat, lon)
    folder = guard(DEM / 'copernicus' / name)
    base = f'{COP_BASE}/{name}'
    short = name.replace('_COG', '').replace('_DEM', '')
    files = [download_object(f'{base}/{name}.tif', folder / f'{name}.tif'),
             download_object(f'{base}/{short}.xml', folder / f'{short}.xml'),
             download_object(f'{base}/AUXFILES/{name.replace("_DEM", "_FLM")}.tif', folder / f'{name.replace("_DEM", "_FLM")}.tif')]
    start, stop = cop_temporal_coverage((folder / f'{short}.xml').read_text(encoding='utf-8'))
    rec = {'tile': name, 'lat': lat, 'lon': lon, 'acquisition_start': start, 'acquisition_stop': stop, 'files': files}
    write_json(folder / 'provenance.json', rec)
    return rec


def nasadem_id(lat, lon):
    return f"NASADEM_HGT_{'n' if lat >= 0 else 's'}{abs(lat):02d}{'e' if lon >= 0 else 'w'}{abs(lon):03d}"


def fetch_nasadem(lat, lon):
    # The items endpoint ignores bbox; fetch the tile by id and check its footprint.
    item = fetch_json(f'{STAC}/collections/nasadem/items/{nasadem_id(lat, lon)}')
    if math.floor(item['bbox'][1] + 0.5) != lat or math.floor(item['bbox'][0] + 0.5) != lon:
        raise RuntimeError(f'NASADEM item {item["id"]} footprint {item["bbox"]} does not match tile {lat},{lon}')
    href = item['assets']['elevation']['href']
    token = fetch_json(f'{STAC.replace("/stac/v1", "")}/sas/v1/token/nasadem')['token']
    folder = guard(DEM / 'nasadem' / item['id'])
    f = download_object(href, folder / Path(href).name, query='?' + token)
    rec = {'tile': item['id'], 'lat': lat, 'lon': lon, 'stac_datetime': item['properties'].get('datetime'), 'files': [f]}
    write_json(folder / 'provenance.json', rec)
    return rec


MARGIN_DEG = 0.1  # covers the terrain block margin (3 km) around the extent


def fetch(dataset, limit=0):
    lon0, lat0, lon1, lat1 = extent_bbox_lonlat(dataset)
    tiles = tiles_for((lon0 - MARGIN_DEG, lat0 - MARGIN_DEG, lon1 + MARGIN_DEG, lat1 + MARGIN_DEG))
    tiles = tiles[:limit] if limit else tiles
    out = []
    for lat, lon in tiles:
        out.append({'lat': lat, 'lon': lon, 'nasadem': fetch_nasadem(lat, lon)['tile'],
                    'copernicus': {k: v for k, v in fetch_cop(lat, lon).items() if k != 'files'}})
    return out


def usability():
    """Per Copernicus tile and development inventory: usable only if its acquisition stop is before the event."""
    cfg = config()
    rows = []
    for dataset, d in cfg['registry']['datasets'].items():
        if d['role'] != 'development' or not (RAW / dataset / 'extracted').exists():
            continue
        for lat, lon in tiles_for(extent_bbox_lonlat(dataset)):
            prov = DEM / 'copernicus' / cop_name(lat, lon) / 'provenance.json'
            if not prov.exists():
                rows.append({'dataset': dataset, 'tile': cop_name(lat, lon), 'status': 'not downloaded'})
                continue
            p = read_json(prov)
            first = d['earliest_event_date']
            rows.append({'dataset': dataset, 'tile': p['tile'], 'acquisition_start': p['acquisition_start'],
                         'acquisition_stop': p['acquisition_stop'], 'registered_earliest_event': first,
                         'usable_for_all_events': bool(first) and p['acquisition_stop'] < first,
                         'usable_rule': 'only for landslides dated after acquisition_stop'})
    write_json(guard(REPORT) / 'dem_tile_usability.json', rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['fetch', 'usability'])
    ap.add_argument('dataset', nargs='?', choices=sorted(EXTENT_LAYERS))
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    print(json.dumps(fetch(a.dataset, a.limit) if a.stage == 'fetch' else usability(), indent=1)[:5000])


if __name__ == '__main__':
    main()
