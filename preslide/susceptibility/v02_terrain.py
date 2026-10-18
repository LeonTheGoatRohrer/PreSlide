"""susceptibility_v02 Phase 2: NASADEM tiles and terrain blocks (Iburi: GSI extent, EPSG:32654; Gorkha and
Far-Western Nepal recomputed in the v02 namespace from the v01 tiles, read-only).

  python -I scripts/run_susceptibility_v02.py terrain_fetch iburi_2018
  python -I scripts/run_susceptibility_v02.py terrain <dataset> --limit 1|5|0(all)
  python -I scripts/run_susceptibility_v02.py terrain_check <dataset>
  python -I scripts/run_susceptibility_v02.py terrain_compare gorkha_2015|far_western_nepal   (v02 vs v01 blocks)

Feature computation is the v01 code (window_features, block_grid, reprojection) with the v01 Amendment 2 terrain
parameters, as registered. One correction: v01 terrain.dem_window passes the requested lon/lat bounds to
rasterio.merge, which then builds the mosaic on a lattice starting at those bounds and copies tile pixels with integer
offsets, i.e. the DEM is shifted by up to half a NASADEM pixel (0.5 arc-second, <= 15 m) per block. Here the merge
bounds are snapped outward to the tile lattice, so the registered bilinear resampling sees correctly located pixels.
Tiles and blocks are written under data/susceptibility_v02 through the v02 guard; v01 modules stay unchanged.
No sample is drawn here.
"""
import math
from pathlib import Path

import numpy as np
import rasterio
import shapely
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from ..common import read_json, write_json
from .dem import STAC, nasadem_id, tiles_for
from .download import download_object, fetch_json, file_digest
from .terrain import NASADEM_NODATA, CacheCorruption, block_grid, check_dem_date, reproject_to_grid, window_features
from .terrain import extent as v01_extent
from .v02 import DATA, REPORT, ROOT, config, guard, readable
from .v02_phase1 import _feature_collection, extent_polygon, gsi_files, lonlat_to_utm

DEM_DIR = DATA / 'dem' / 'nasadem'
V01_DEM_DIR = ROOT / 'data/susceptibility_v01/dem/nasadem'
V01_FEATURES = ROOT / 'data/susceptibility_v01/features'
TERRAIN = DATA / 'terrain'
MARGIN_DEG = 0.1  # as v01: covers the 3 km block margin around the extent
SUPPORTED = ('iburi_2018', 'gorkha_2015', 'far_western_nepal')
NEW_INVENTORIES = ('iburi_2018',)
_VERIFIED = {}
# Numbers written in the registered v02 text (config 'terrain_parameters.rule'); checked against v01 Amendment 2.
REGISTERED_TERRAIN = {'tpi_radius_m': 300, 'relief_radius_m': 1000, 'channel_threshold_m2': 1000000,
                      'block_core_m': 15000, 'block_margin_m': 3000}


def terrain_parameters(cfg):
    """v01 Amendment 2 terrain block, refused if it differs from the numbers registered in the v02 text."""
    t = read_json(ROOT / 'reports/susceptibility_v01/AMENDMENT_2.json')['add']['terrain']['value']
    rule = cfg['terrain_parameters']['rule'].replace('1e6', f'{1e6:g}')
    for k, v in REGISTERED_TERRAIN.items():
        if t[k] != v or f'{k} {v:g}' not in rule:
            raise RuntimeError(f'terrain parameter {k}: v01 Amendment 2 has {t[k]}, v02 registration {v}')
    return t


def working_crs(cfg, dataset):
    """Iburi: v02 Amendment 1; Gorkha and Far-Western Nepal: v01 Amendment 2 (registered as identical in v02)."""
    crs = cfg['registry']['datasets'][dataset].get('working_crs')
    if not crs:
        v01 = read_json(ROOT / 'reports/susceptibility_v01/AMENDMENT_2.json')['add']['terrain']['value']['crs_by_dataset']
        crs = v01.get(dataset)
    if not crs:
        raise RuntimeError(f'{dataset}: no registered working CRS')
    return crs


def extent_utm(dataset, epsg):
    """Mapping extent in the working CRS: GSI interpretation extent (Iburi) or the v01 extent layer (read-only)."""
    if dataset not in SUPPORTED:
        raise ValueError(f'{dataset}: no v02 terrain for this inventory ({SUPPORTED})')
    if dataset == 'iburi_2018':
        ring = _feature_collection(gsi_files()['extent'])['features'][0]['geometry']['coordinates']
        return lonlat_to_utm(extent_polygon(ring), epsg)
    poly, crs = v01_extent(dataset)
    if crs.to_epsg() != epsg:
        raise ValueError(f'{dataset}: extent CRS {crs.to_string()} is not EPSG:{epsg}')
    return poly


def dem_dir_for(dataset):
    return DEM_DIR if dataset in NEW_INVENTORIES else readable(V01_DEM_DIR)


def fetch_nasadem(lat, lon):
    """As susceptibility_v01 dem.fetch_nasadem (Planetary Computer, anonymous SAS token), written to the v02 namespace."""
    item = fetch_json(f'{STAC}/collections/nasadem/items/{nasadem_id(lat, lon)}')
    if math.floor(item['bbox'][1] + 0.5) != lat or math.floor(item['bbox'][0] + 0.5) != lon:
        raise RuntimeError(f'NASADEM item {item["id"]} footprint {item["bbox"]} does not match tile {lat},{lon}')
    href = item['assets']['elevation']['href']
    token = fetch_json(f'{STAC.replace("/stac/v1", "")}/sas/v1/token/nasadem')['token']
    folder = guard(DEM_DIR / item['id'])
    f = download_object(href, folder / Path(href).name, query='?' + token)
    rec = {'tile': item['id'], 'lat': lat, 'lon': lon, 'stac_datetime': item['properties'].get('datetime'), 'files': [f],
           'released_by_user': 'NASADEM tiles covering the Iburi GSI extent, released 2026-10-18'}
    write_json(folder / 'provenance.json', rec)
    return rec


def tiles_needed(extent, epsg):
    lon0, lat0, lon1, lat1 = transform_bounds(f'EPSG:{epsg}', 'EPSG:4326', *extent.bounds, densify_pts=21)
    return tiles_for((lon0 - MARGIN_DEG, lat0 - MARGIN_DEG, lon1 + MARGIN_DEG, lat1 + MARGIN_DEG))


def terrain_fetch(dataset):
    if dataset not in NEW_INVENTORIES:
        raise ValueError(f'{dataset}: v01 tiles are reused read-only; nothing to download')
    cfg = config()
    epsg = int(working_crs(cfg, dataset).split(':')[1])
    return [fetch_nasadem(lat, lon) for lat, lon in tiles_needed(extent_utm(dataset, epsg), epsg)]


def tile_file(lat, lon, dem_dir=DEM_DIR):
    """Verified NASADEM tile path; missing or changed tiles raise."""
    folder = dem_dir / nasadem_id(lat, lon)
    f = folder / f'{nasadem_id(lat, lon)}.tif'
    if not f.exists():
        raise FileNotFoundError(f'NASADEM tile missing: {f}')
    key = (str(f), f.stat().st_mtime_ns, f.stat().st_size)
    if key not in _VERIFIED:
        if file_digest(f, 'sha256') != read_json(folder / 'provenance.json')['files'][0]['sha256']:
            raise CacheCorruption(f'NASADEM tile changed since download: {f}')
        _VERIFIED[key] = True
    return f


def snap_to_lattice(bounds, x0, y0, res):
    """Expand lon/lat bounds outward to whole pixels of the tile lattice with corner (x0, y0) and pixel size res."""
    west, south, east, north = bounds
    return (x0 + math.floor((west - x0) / res) * res, y0 - math.ceil((y0 - south) / res) * res,
            x0 + math.ceil((east - x0) / res) * res, y0 - math.floor((y0 - north) / res) * res)


def dem_window(crs, left, bottom, right, top, res_m, dem_dir=DEM_DIR):
    """As v01 terrain.dem_window, reading verified tiles from `dem_dir`, with the mosaic on the tile lattice."""
    lon0, lat0, lon1, lat1 = transform_bounds(crs, 'EPSG:4326', left, bottom, right, top, densify_pts=21)
    pad = 0.01
    files = [rasterio.open(tile_file(lat, lon, dem_dir)) for lat, lon in tiles_for((lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad))]
    try:
        ref = files[0].transform
        res = ref.a
        for f in files:
            tr = f.transform
            if (abs(tr.a - res) > 1e-12 or abs(tr.e + res) > 1e-12 or abs((tr.c - ref.c) / res - round((tr.c - ref.c) / res)) > 1e-6
                    or abs((tr.f - ref.f) / res - round((tr.f - ref.f) / res)) > 1e-6):
                raise RuntimeError('NASADEM tiles do not share one pixel lattice')
        bounds = snap_to_lattice((lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad), ref.c, ref.f, res)
        mosaic, transform = merge(files, bounds=bounds, res=res, nodata=NASADEM_NODATA)
        if abs((transform.c - ref.c) / res - round((transform.c - ref.c) / res)) > 1e-6 or \
                abs((transform.f - ref.f) / res - round((transform.f - ref.f) / res)) > 1e-6:
            raise RuntimeError('mosaic is not on the tile lattice')
    finally:
        for f in files:
            f.close()
    shape = (round((top - bottom) / res_m), round((right - left) / res_m))
    return reproject_to_grid(mosaic[0], transform, 'EPSG:4326', left, top, shape, crs, res_m, NASADEM_NODATA)


def block_path(dataset, i, j):
    return TERRAIN / dataset / f'block_{i:03d}_{j:03d}.tif'


def blocks_for(extent, t, res_m):
    return [b for b in block_grid(extent.bounds, t['block_core_m'], res_m) if shapely.box(*b[2:]).intersects(extent)]


def build_block(dataset, cfg, t, crs, i, j, left, bottom, right, top):
    path = block_path(dataset, i, j)
    if path.exists():
        meta = read_json(path.with_suffix('.json'))
        if file_digest(path, 'sha256') != meta['sha256']:
            raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
        return meta
    res, m = cfg['sampling']['cell_m'], t['block_margin_m']
    dem = dem_window(crs, left - m, bottom - m, right + m, top + m, res, dem_dir_for(dataset))
    feats, meta = window_features(dem, res, t)
    k = round(m / res)
    names = cfg['features_terrain']
    stack = np.stack([feats[n][k:-k, k:-k] for n in names])
    guard(path.parent)
    profile = {'driver': 'GTiff', 'dtype': 'float32', 'count': len(names), 'height': stack.shape[1],
               'width': stack.shape[2], 'crs': crs, 'transform': from_origin(left, top, res, res), 'nodata': np.nan,
               'compress': 'deflate', 'predictor': 3, 'tiled': True, 'blockxsize': 256, 'blockysize': 256}
    tmp = path.with_suffix('.tmp.tif')
    with rasterio.open(tmp, 'w', **profile) as dst:
        dst.write(stack)
        dst.descriptions = tuple(names)
    tmp.replace(path)
    meta.update({'dataset': dataset, 'block': [i, j], 'bounds': [left, bottom, right, top], 'crs': crs,
                 'features': names, 'nan_cells': {n: int(np.isnan(stack[q]).sum()) for q, n in enumerate(names)},
                 'cells': int(stack[0].size), 'dem': cfg['dem']['primary'], 'sha256': file_digest(path, 'sha256')})
    write_json(path.with_suffix('.json'), meta)
    return meta


def build(dataset, limit=0):
    cfg = config()
    check_dem_date(cfg, dataset)
    crs = working_crs(cfg, dataset)
    t = terrain_parameters(cfg)
    extent = extent_utm(dataset, int(crs.split(':')[1]))
    blocks = blocks_for(extent, t, cfg['sampling']['cell_m'])
    selected = blocks[:limit] if limit else blocks
    metas = [build_block(dataset, cfg, t, crs, *b) for b in selected]
    cells = max(1, sum(m['cells'] for m in metas))
    summary = {'dataset': dataset, 'crs': crs, 'blocks_total': len(blocks), 'blocks_built': len(metas),
               'cells': sum(m['cells'] for m in metas),
               'nan_fraction': {n: sum(m['nan_cells'][n] for m in metas) / cells for n in cfg['features_terrain']}}
    if not limit:
        write_json(guard(TERRAIN / dataset) / 'summary.json', summary)
    return summary


def terrain_check(dataset):
    """Extent-wide plausibility of the blocks (cells whose centre lies in the mapping extent): no landslide location is
    used. Elevation range, share of non-positive elevation (sea / NASADEM water fill), NaN shares, block coverage."""
    cfg = config()
    crs = working_crs(cfg, dataset)
    extent = extent_utm(dataset, int(crs.split(':')[1]))
    t = terrain_parameters(cfg)
    blocks = blocks_for(extent, t, cfg['sampling']['cell_m'])
    names = cfg['features_terrain']
    vals = {n: [] for n in names}
    covered = shapely.union_all([shapely.box(*b[2:]) for b in blocks])
    for b in blocks:
        path = block_path(dataset, b[0], b[1])
        meta = read_json(path.with_suffix('.json'))
        if file_digest(path, 'sha256') != meta['sha256']:
            raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
        with rasterio.open(path) as src:
            if src.crs.to_string() != crs or abs(src.transform.a - cfg['sampling']['cell_m']) > 1e-9:
                raise RuntimeError(f'{path}: CRS {src.crs} / resolution {src.transform.a} differ from the registration')
            stack = src.read()
            rows, cols = np.mgrid[0:src.height, 0:src.width]
            xs, ys = rasterio.transform.xy(src.transform, rows.ravel(), cols.ravel())
        inside = shapely.contains_xy(extent, np.asarray(xs), np.asarray(ys)).reshape(src.height, src.width)
        for q, n in enumerate(names):
            vals[n].append(stack[q][inside])
    vals = {n: np.concatenate(v) for n, v in vals.items()}
    z = vals['elevation_m']
    out = {'dataset': dataset, 'crs': crs, 'blocks': len(blocks), 'extent_inside_blocks': bool(covered.contains(extent)),
           'cells_in_extent': int(z.size), 'extent_area_from_cells_km2': z.size * cfg['sampling']['cell_m'] ** 2 / 1e6,
           'extent_area_km2': extent.area / 1e6,
           'elevation_m_quantiles': {str(q): float(np.nanquantile(z, q)) for q in (0, 0.01, 0.5, 0.99, 1)},
           'share_elevation_le_0': float(np.nanmean(z <= 0)),
           'slope_deg_quantiles': {str(q): float(np.nanquantile(vals['slope_deg'], q)) for q in (0.5, 0.9, 0.99, 1)},
           'aspect_unit_circle_max_error': float(np.nanmax(np.abs(vals['aspect_sin'] ** 2 + vals['aspect_cos'] ** 2 - 1))),
           'nan_share_in_extent': {n: float(np.isnan(v).mean()) for n, v in vals.items()},
           'meridian_convergence_deg_max': meridian_convergence_max(extent, int(crs.split(':')[1])),
           'note': 'Extent-wide distributions only; no value at any landslide polygon, no sample.'}
    write_json(guard(REPORT) / f'phase2_terrain_{dataset}.json', out)
    return out


def meridian_convergence_max(extent, epsg):
    """Largest |grid convergence| over the extent vertices (UTM north zones: CM = 6*zone - 183)."""
    zone = epsg - 32600
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(*shapely.get_coordinates(extent).T)
    return float(np.max(np.abs(np.degrees(np.arctan(np.tan(np.radians(lon - (6 * zone - 183))) * np.sin(np.radians(lat)))))))


def terrain_compare(dataset):
    """v02 blocks against the v01 blocks of the same inventory (same grid): size of the v01 merge shift on features."""
    if dataset in NEW_INVENTORIES:
        raise ValueError(f'{dataset} has no v01 blocks')
    cfg = config()
    names = cfg['features_terrain']
    diffs = {n: [] for n in names}
    per_block = []
    for path in sorted((TERRAIN / dataset).glob('block_*.tif')):
        old = readable(V01_FEATURES / dataset / path.name)
        for q in (path, old):
            if file_digest(q, 'sha256') != read_json(q.with_suffix('.json'))['sha256']:
                raise CacheCorruption(f'Checkpoint checksum mismatch: {q}')
        with rasterio.open(path) as a, rasterio.open(old) as b:
            if a.transform != b.transform or a.crs != b.crs or a.shape != b.shape:
                raise RuntimeError(f'{path.name}: v02 and v01 grids differ')
            x, y = a.read(), b.read()
        d = x - y
        per_block.append(float(np.nanmean(np.abs(d[0]))))
        for q, n in enumerate(names):
            diffs[n].append(np.abs(d[q][np.isfinite(d[q])]))
    out = {'dataset': dataset, 'blocks': len(per_block),
           'abs_difference': {n: {'mean': float(np.concatenate(v).mean()), 'p99': float(np.quantile(np.concatenate(v), 0.99)),
                                  'max': float(np.concatenate(v).max())} for n, v in diffs.items()},
           'elevation_mean_abs_difference_by_block_quantiles': {str(q): float(np.quantile(per_block, q)) for q in (0, 0.5, 1)},
           'cause': 'v01 dem_window merged NASADEM on a lattice starting at the requested bounds (shift up to 0.5 arc-second '
                    'per block); v02 snaps the merge bounds to the tile lattice'}
    write_json(guard(REPORT) / f'phase2_terrain_v01_comparison_{dataset}.json', out)
    return out


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['terrain_fetch', 'terrain', 'terrain_check', 'terrain_compare'])
    ap.add_argument('dataset', choices=SUPPORTED)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    res = {'terrain_fetch': lambda: terrain_fetch(a.dataset), 'terrain': lambda: build(a.dataset, a.limit),
           'terrain_check': lambda: terrain_check(a.dataset), 'terrain_compare': lambda: terrain_compare(a.dataset)}[a.stage]()
    print(json.dumps(res, indent=1)[:8000])
