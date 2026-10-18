"""susceptibility_v02 Phase 1 data: GSI D1-No.991 archive check (Iburi extent) and USGS ShakeMap PGA.

  python scripts/run_susceptibility_v02.py gsi_fetch        download + member check + extraction (write-once)
  python scripts/run_susceptibility_v02.py gsi_inspect      layer-level metadata only (no terrain, no sample)
  python scripts/run_susceptibility_v02.py shakemap gorkha_2015
  python scripts/run_susceptibility_v02.py pga gorkha_2015 --limit 1|5|20|0(all)
  python scripts/run_susceptibility_v02.py iburi            ShakeMap coverage, old-landslide counts, buffer statistic

Downloads are restricted to the two URLs released by the user for this session. Raw files go to their own folders
under data/susceptibility_v02/raw and are never overwritten. All writes pass the v02 guard.
"""
import argparse
import collections
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import shapefile
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Polygon, shape

from ..common import read_json, write_json
from ..v04.pipeline import load, save
from .download import download_object, file_digest
from .inventory import layer_crs, read_layer, safe_members
from .v02 import DATA, REPORT, ROOT, config, guard, readable

RAW = DATA / 'raw'
GSI_URL = 'https://www.gsi.go.jp/common/000204728.zip'
GSI_PAGE = 'https://www.gsi.go.jp/BOUSAI/H30-hokkaidoiburi-east-earthquake-index.html'
GSI_DIR = RAW / 'gsi_d1_991'
V01_SAMPLES = ROOT / 'data/susceptibility_v01/samples'
V01_RAW = ROOT / 'data/susceptibility_v01/raw'
# Words that would mark an interpretation / mapping extent layer (Japanese: 判読範囲 = interpretation extent).
GSI_ROLES = {'判読範囲.geojson': 'extent', '雲による未判読範囲.geojson': 'obscured',
             '斜面崩壊・堆積範囲.geojson': 'landslides', '免責事項.txt': 'disclaimer'}
EXTENT_WORDS = ('判読範囲', '判読', '範囲', 'extent', 'area', 'boundary', 'coverage', 'hani')


# ---------------------------------------------------------------- GSI archive

def member_name(info):
    """Archive member name; legacy Japanese zips store cp932 bytes without the UTF-8 flag."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode('cp437').decode('cp932')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def gsi_fetch():
    folder = guard(GSI_DIR)
    target = folder / 'gsi_d1_991.zip'
    others = [p.name for p in folder.iterdir() if p.name not in ('gsi_d1_991.zip', 'extracted', 'provenance.json')]
    if others:
        raise RuntimeError(f'{folder} must hold only this download, found {others}')
    prov = download_object(GSI_URL, target)
    with zipfile.ZipFile(target) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        names = safe_members([member_name(i) for i in infos])
        out = folder / 'extracted'
        if not out.exists():
            tmp = guard(folder / 'extracting')
            for info, name in zip(infos, names):
                dest = tmp / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(info))
            tmp.replace(out)
    prov.update({'dataset': 'GSI technical document D1-No.991 (slope failure / deposit distribution, 2018 Hokkaido '
                            'Eastern Iburi earthquake)', 'page': GSI_PAGE,
                 'licence': 'GSI content terms of use (attribution required); see page',
                 'released_by_user': 'download released by the user for this session (2026-10-18)',
                 'members': [{'name': n, 'bytes': i.file_size} for i, n in zip(infos, names)]})
    write_json(folder / 'provenance.json', prov)
    return prov


def _coords(geom):
    t, c = geom.get('type'), geom.get('coordinates')
    if t == 'GeometryCollection':
        for g in geom.get('geometries', []):
            yield from _coords(g)
        return
    stack = [c]
    while stack:
        v = stack.pop()
        if v and isinstance(v[0], (int, float)):
            yield v[0], v[1]
        elif v:
            stack.extend(v)


def describe_geojson(path, max_categories=20):
    """Layer-level description: CRS member, feature count, geometry types, fields, low-cardinality field values, bbox."""
    d = json.loads(Path(path).read_bytes().decode('utf-8-sig'))
    feats = d.get('features', []) if d.get('type') == 'FeatureCollection' else [d]
    types = collections.Counter((f.get('geometry') or {}).get('type') for f in feats)
    values = collections.defaultdict(collections.Counter)
    for f in feats:
        for k, v in (f.get('properties') or {}).items():
            values[k][json.dumps(v, ensure_ascii=False)] += 1
    xs, ys = [], []
    for f in feats:
        if f.get('geometry'):
            for x, y in _coords(f['geometry']):
                xs.append(x)
                ys.append(y)
    fields = {k: {'distinct': len(c), **({'values': dict(c.most_common())} if len(c) <= max_categories else {})}
              for k, c in values.items()}
    return {'format': 'GeoJSON', 'top_level_keys': sorted(d), 'name': d.get('name'), 'crs_member': d.get('crs'),
            'n_features': len(feats), 'geometry_types': dict(types), 'fields': fields,
            'bbox': [min(xs), min(ys), max(xs), max(ys)] if xs else None}


def describe_shapefile(path):
    lay = read_layer(path)
    try:
        crs = layer_crs(path).to_string()
    except RuntimeError as e:
        crs = str(e)
    return {'format': 'ESRI Shapefile', 'n_features': lay['n_total'], 'geometry_type': lay['shape_type'],
            'fields': lay['fields'], 'crs': crs, 'bbox': lay['bbox']}


def mentions_extent(text):
    low = text.lower()
    return sorted({w for w in EXTENT_WORDS if w in low})


def decode_text(raw):
    """GSI text files are Shift-JIS (cp932); UTF-8 is tried first."""
    for enc in ('utf-8-sig', 'cp932'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace'), 'utf-8 (replaced)'


def gsi_role(name):
    """Role of a GSI archive member from the suffix after the last underscore of its file name."""
    return GSI_ROLES.get(Path(name).name.split('_')[-1])


def lonlat_to_utm(geom, epsg):
    t = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(epsg), always_xy=True)
    return shapely.transform(geom, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))


def extent_polygon(line_coords):
    """Polygon of a provider-drawn extent line; only an exactly closed, simple ring is accepted (nothing is inferred)."""
    line = LineString(line_coords)
    if tuple(line_coords[0]) != tuple(line_coords[-1]) or not line.is_ring:
        raise RuntimeError('extent line is not a closed simple ring; no polygon is constructed from it')
    return Polygon(line_coords)


def _feature_collection(path):
    return json.loads(Path(path).read_bytes().decode('utf-8-sig'))


def gsi_extent_check(files, epsg):
    """Extent geometry, obscured areas and polygon counts relative to the extent (counts only, no terrain, no sample)."""
    ext = _feature_collection(files['extent'])['features']
    if len(ext) != 1 or ext[0]['geometry']['type'] != 'LineString':
        raise RuntimeError('expected one LineString interpretation extent')
    poly = lonlat_to_utm(extent_polygon(ext[0]['geometry']['coordinates']), epsg)
    clouds = [lonlat_to_utm(shape(f['geometry']), epsg) for f in _feature_collection(files['obscured'])['features']]
    feats = _feature_collection(files['landslides'])['features']
    keys = [json.dumps(f['properties'], sort_keys=True) for f in feats]
    styles = collections.Counter(keys)
    main_style = styles.most_common(1)[0][0]
    slides = [lonlat_to_utm(shape(f['geometry']), epsg) for f in feats]
    main = [g for k, g in zip(keys, slides) if k == main_style]
    other = [(f['properties'], g) for f, k, g in zip(feats, keys, slides) if k != main_style]
    return {
        'working_crs': f'EPSG:{epsg}',
        'extent': {'vertices': len(ext[0]['geometry']['coordinates']), 'closed': True, 'simple_ring': True,
                   'polygon_valid': bool(poly.is_valid), 'area_km2': poly.area / 1e6},
        'obscured_by_cloud': {'polygons': len(clouds), 'area_km2': sum(c.area for c in clouds) / 1e6,
                              'inside_extent': int(sum(poly.buffer(1.0).contains(c) for c in clouds))},
        'slope_failure_deposit_polygons': {
            'n_total': len(feats), 'style_groups': dict(styles),
            'n_main_style': len(main), 'main_style_inside_extent': int(sum(poly.contains(g) for g in main)),
            'main_style_invalid_geometry': int(sum(not g.is_valid for g in main)),
            'deviating_style_features': [{'properties': p, 'area_m2': g.area, 'inside_extent': bool(poly.contains(g))}
                                         for p, g in other]},
    }


def gsi_inspect(epsg=32654):
    folder = GSI_DIR / 'extracted'
    prov = read_json(GSI_DIR / 'provenance.json')
    if file_digest(GSI_DIR / 'gsi_d1_991.zip', 'sha256') != prov['sha256']:
        raise RuntimeError('GSI archive changed since download')
    layers, roles = {}, {}
    for p in sorted(folder.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(folder).as_posix()
        entry = {'bytes': p.stat().st_size, 'sha256': file_digest(p, 'sha256'), 'role': gsi_role(rel),
                 'name_mentions_extent_words': mentions_extent(rel)}
        if entry['role']:
            roles[entry['role']] = p
        suf = p.suffix.lower()
        if suf in ('.geojson', '.json'):
            entry.update(describe_geojson(p))
        elif suf == '.shp':
            entry.update(describe_shapefile(p))
        elif suf in ('.txt', '.csv', '.xml', '.htm', '.html', '.md'):
            text, enc = decode_text(p.read_bytes())
            entry.update({'format': f'text ({enc})', 'mentions_extent_words': mentions_extent(text), 'text': text[:1500]})
        else:
            entry['format'] = suf or 'none'
        layers[rel] = entry
    has_extent = 'extent' in roles
    out = {'version': 'susceptibility_v02', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
           'scope': 'Layer-level and metadata check of the GSI D1-No.991 archive: files, geometry types, counts, fields, '
                    'CRS; extent closure and area; counts of polygons inside the extent. No terrain value, no sample, '
                    'no per-landslide statistic beyond counts, no model.',
           'archive': {'url': GSI_URL, 'page': GSI_PAGE, 'sha256': prov['sha256'], 'size_bytes': prov['size_bytes'],
                       'last_modified': prov.get('last_modified'), 'verified_at_utc': prov['verified_at_utc']},
           'layers': layers, 'contains_interpretation_extent_as_data': has_extent}
    if has_extent:
        out['extent_check'] = gsi_extent_check(roles, epsg)
    write_json(guard(REPORT) / 'phase1_iburi_gsi_check.json', out)
    return out


# ---------------------------------------------------------------- ShakeMap

def shakemap_url(dataset):
    """Registered grid.xml URL of the preferred product seen at registration (phase0_data_audit.json)."""
    audit = read_json(REPORT / 'phase0_data_audit.json')
    return audit[dataset]['shakemap']['grid_xml'], audit


def shakemap_fetch(dataset):
    cfg = config()
    d = cfg['registry']['datasets'][dataset]
    if d['trigger_class'] != 'earthquake' or d['role'] != 'development':
        raise ValueError(f'{dataset}: ShakeMap only for development earthquake inventories')
    url, audit = shakemap_url(dataset)
    if d['shakemap_event_id'] not in url:
        raise RuntimeError(f'{url} does not belong to event {d["shakemap_event_id"]}')
    folder = guard(RAW / f'shakemap_{dataset}')
    target = folder / 'grid.xml'
    prov = download_object(url, target)
    registered = audit[dataset]['shakemap']['grid_xml_bytes']
    if prov['size_bytes'] != registered:
        raise RuntimeError(f'grid.xml has {prov["size_bytes"]} B, registration saw {registered} B')
    head = grid_header(target)
    if head['event_id'] not in d['shakemap_event_id']:
        raise RuntimeError(f'grid.xml event {head["event_id"]} is not {d["shakemap_event_id"]}')
    seen = cfg['ground_motion']['events'][dataset]['seen_at_registration']
    m = re.search(r'updateTime (\d+)', seen)
    prov.update({'dataset': dataset, 'event_id': d['shakemap_event_id'], 'product_source': 'atlas',
                 'product_update_time_ms': int(m.group(1)) if m else None, 'registered_bytes': registered,
                 'grid_header': head, 'frozen_note': cfg['ground_motion']['freeze'],
                 'released_by_user': 'download released by the user for this session (2026-10-18)'})
    write_json(folder / 'provenance.json', prov)
    return prov


def grid_header(path):
    """Event, version and grid specification of a ShakeMap grid.xml (no data rows)."""
    head = {}
    for ev, el in ET.iterparse(path, events=('start',)):
        tag = el.tag.split('}')[-1]
        if tag == 'shakemap_grid':
            head.update({k: el.get(k) for k in ('event_id', 'shakemap_id', 'shakemap_version', 'code_version',
                                                'process_timestamp', 'shakemap_originator', 'map_status',
                                                'shakemap_event_type')})
        elif tag == 'event':
            head['event'] = dict(el.attrib)
        elif tag == 'grid_specification':
            head['grid_specification'] = dict(el.attrib)
        elif tag == 'grid_field':
            head.setdefault('grid_fields', []).append(dict(el.attrib))
        elif tag == 'grid_data':
            break
    return head


def read_grid(path, field='PGA'):
    """(values[nlat, nlon] with row 0 = northernmost, lon0, lat_top, dlon, dlat, units). Order checked from the data."""
    head = grid_header(path)
    spec = head['grid_specification']
    nlon, nlat = int(spec['nlon']), int(spec['nlat'])
    fields = {f['name']: (int(f['index']) - 1, f.get('units')) for f in head['grid_fields']}
    col, units = fields[field]
    text = None
    for ev, el in ET.iterparse(path, events=('end',)):
        if el.tag.split('}')[-1] == 'grid_data':
            text = el.text
            break
    rows = np.loadtxt(text.strip().splitlines(), dtype=float)
    if rows.shape != (nlon * nlat, len(fields)):
        raise RuntimeError(f'grid.xml data shape {rows.shape} does not match {nlat} x {nlon} x {len(fields)}')
    return (*lattice(rows[:, 0], rows[:, 1], rows[:, col], nlon, nlat, spec), units)


def lattice(lon, lat, values, nlon, nlat, spec, tol_deg=1e-4):
    """Regular north-up lattice from grid.xml rows: (values[nlat, nlon], lon0, lat_top, dlon, dlat).

    The spacing comes from the corner coordinates, not from nominal_*_spacing (rounded to 4 decimals in the header,
    which would shift the far edge by kilometres). Row-major order from the north-west corner with longitude fastest
    is verified node by node instead of assumed."""
    lon, lat = np.asarray(lon, float).reshape(nlat, nlon), np.asarray(lat, float).reshape(nlat, nlon)
    lon0, lat_top = lon[0, 0], lat[0, 0]
    dlon, dlat = (lon[0, -1] - lon0) / (nlon - 1), (lat_top - lat[-1, 0]) / (nlat - 1)
    expect_lon = lon0 + dlon * np.arange(nlon)[None, :]
    expect_lat = lat_top - dlat * np.arange(nlat)[:, None]
    if not (dlon > 0 and dlat > 0 and np.abs(lon - expect_lon).max() <= tol_deg and np.abs(lat - expect_lat).max() <= tol_deg):
        raise RuntimeError('grid.xml rows are not a regular north-to-south, west-to-east lattice')
    corners = [(lon0, 'lon_min'), (lon[0, -1], 'lon_max'), (lat_top, 'lat_max'), (lat[-1, 0], 'lat_min')]
    if any(abs(v - float(spec[k])) > tol_deg for v, k in corners):
        raise RuntimeError('grid.xml corner coordinates differ from grid_specification')
    return np.asarray(values, float).reshape(nlat, nlon), float(lon0), float(lat_top), float(dlon), float(dlat)


def bilinear(values, lon0, lat_top, dlon, dlat, lon, lat):
    """Bilinear interpolation on a north-up lattice whose node (0, 0) is at (lon0, lat_top). Outside -> NaN."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    fc = (lon - lon0) / dlon
    fr = (lat_top - lat) / dlat
    nr, nc = values.shape
    out = np.full(lon.shape, np.nan)
    ok = (fc >= 0) & (fc <= nc - 1) & (fr >= 0) & (fr <= nr - 1)
    c0 = np.minimum(np.floor(fc[ok]).astype(int), nc - 2)
    r0 = np.minimum(np.floor(fr[ok]).astype(int), nr - 2)
    tc, tr = fc[ok] - c0, fr[ok] - r0
    v = values
    out[ok] = ((1 - tr) * ((1 - tc) * v[r0, c0] + tc * v[r0, c0 + 1])
               + tr * ((1 - tc) * v[r0 + 1, c0] + tc * v[r0 + 1, c0 + 1]))
    return out


def to_lonlat(x, y, crs):
    """Projected metres in `crs` to WGS84 lon/lat (always_xy: x = easting -> lon)."""
    t = Transformer.from_crs(CRS.from_user_input(crs), CRS.from_epsg(4326), always_xy=True)
    return t.transform(np.asarray(x, float), np.asarray(y, float))


def log10_pga_pctg(pga_pctg):
    """log10 of PGA in percent g; non-positive or missing values stay NaN (never filled)."""
    p = np.asarray(pga_pctg, float)
    out = np.full(p.shape, np.nan)
    ok = np.isfinite(p) & (p > 0)
    out[ok] = np.log10(p[ok])
    return out


def pga_at(x, y, crs, grid):
    values, lon0, lat_top, dlon, dlat, units = grid
    if units.strip().lower() not in ('pctg', '%g'):
        raise RuntimeError(f'PGA units {units!r}, expected percent g')
    lon, lat = to_lonlat(x, y, crs)
    return log10_pga_pctg(bilinear(values, lon0, lat_top, dlon, dlat, lon, lat))


def v01_samples(dataset):
    """Read-only v01 samples; the hashed sidecar must verify and match the sha recorded at v01 Phase 3."""
    path = readable(V01_SAMPLES / f'{dataset}.parquet')
    frame = load(path)
    if frame is None:
        raise RuntimeError(f'{path} missing')
    return frame, read_json(path.with_suffix('.json'))


def extent_coverage(dataset, grid, crs):
    """Share of mapping-extent vertices inside the ShakeMap grid (Phase 1 coverage rule, documentation only)."""
    folder = readable(V01_RAW / dataset / 'extracted')
    shp = next(folder.rglob('MappingExtent*.shp'))
    lay = read_layer(shp)
    if layer_crs(shp).to_epsg() != CRS.from_user_input(crs).to_epsg():
        raise RuntimeError(f'{shp}: extent CRS differs from {crs}')
    xs, ys = [], []
    for g in lay['geoms']:
        for poly in getattr(g, 'geoms', [g]):
            cx, cy = poly.exterior.coords.xy
            xs.extend(cx)
            ys.extend(cy)
    values, lon0, lat_top, dlon, dlat, _ = grid
    lon, lat = to_lonlat(xs, ys, crs)
    inside = np.isfinite(bilinear(values, lon0, lat_top, dlon, dlat, lon, lat))
    return {'extent_file': shp.name, 'vertices': len(xs), 'vertices_inside_grid': int(inside.sum()),
            'extent_lonlat_bbox': [float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max())]}


def pga(dataset, limit=0):
    config()  # refuses to run if the registered configuration changed
    crs = read_json(ROOT / 'reports/susceptibility_v01/AMENDMENT_2.json')['add']['terrain']['value']['crs_by_dataset'][dataset]
    prov = read_json(RAW / f'shakemap_{dataset}' / 'provenance.json')
    gpath = RAW / f'shakemap_{dataset}' / 'grid.xml'
    if file_digest(gpath, 'sha256') != prov['sha256']:
        raise RuntimeError(f'{gpath} changed since download (frozen)')
    grid = read_grid(gpath)
    frame, side = v01_samples(dataset)
    if limit:
        frame = frame.iloc[np.r_[0:limit, len(frame) - limit:len(frame)]]
    vals = pga_at(frame.x.to_numpy(), frame.y.to_numpy(), crs, grid)
    out = frame[['sample_id', 'label', 'x', 'y']].copy()
    out['log10_pga_pctg'] = vals
    summary = {'dataset': dataset, 'crs': crs, 'v01_samples_sha256': side['sha256'], 'grid_sha256': prov['sha256'],
               'grid_version': prov['grid_header'].get('shakemap_version'),
               'process_timestamp': prov['grid_header'].get('process_timestamp'),
               'interpolation': 'bilinear interpolation of PGA (percent g) at the 30 m cell centre on the WGS84 grid '
                                'lattice, then log10; cells outside the grid stay NaN',
               'n': len(out), 'nan_outside_grid': int(np.isnan(vals).sum()),
               'nan_by_label': {str(k): int(np.isnan(vals[out.label.to_numpy() == k]).sum()) for k in (0, 1)},
               'quantiles_log10_pga': {str(q): float(np.nanquantile(vals, q)) for q in (0, 0.05, 0.5, 0.95, 1)},
               'extent_coverage': extent_coverage(dataset, grid, crs),
               'computed_at_utc': datetime.now(timezone.utc).isoformat()}
    if not limit:
        path = guard(DATA / 'features') / f'{dataset}_pga.parquet'
        if load(path) is not None:
            raise RuntimeError(f'{path} exists; features are write-once')
        save(out, path, {'dataset': dataset, 'grid_sha256': prov['sha256'], 'v01_samples_sha256': side['sha256']})
        write_json(guard(REPORT) / f'phase1_pga_{dataset}.json', summary)
    return out, summary


# ---------------------------------------------------------------- Iburi Phase 1 (coverage, old landslides, buffer)

ZENODO_IBURI = V01_RAW / 'candidates' / 'iburi_2018' / 'extracted'
IBURI_EPSG = 32654


def gsi_files():
    files = {}
    for p in (GSI_DIR / 'extracted').rglob('*'):
        role = gsi_role(p.name) if p.is_file() else None
        if role:
            files[role] = p
    return files


def split_by_style(features):
    """(main-style indices, other indices): the most frequent property set is the inventory style."""
    keys = [json.dumps(f['properties'], sort_keys=True) for f in features]
    main = collections.Counter(keys).most_common(1)[0][0]
    return [i for i, k in enumerate(keys) if k == main], [i for i, k in enumerate(keys) if k != main]


def intersects_any(geoms, others):
    """Boolean per geometry: intersects at least one of `others` (STRtree, exact predicate)."""
    if not len(others):
        return np.zeros(len(geoms), bool)
    tree = shapely.STRtree(others)
    hit = np.zeros(len(geoms), bool)
    idx, _ = tree.query(np.asarray(geoms, dtype=object), predicate='intersects')
    hit[np.unique(idx)] = True
    return hit


def equivalent_radius_p90(areas_m2):
    """90th percentile of sqrt(area / pi) (registered buffer statistic)."""
    return float(np.quantile(np.sqrt(np.asarray(areas_m2, float) / np.pi), 0.9))


def buffer_value(p90_by_inventory, step_m=10, floor_m=60, cap_m=300):
    """Registered rule: maximum over inventories, rounded up to step_m, floor floor_m, cap cap_m.

    Returns (value_m, cap_exceeded). Exceeding the cap is a gate finding, never silently clipped."""
    top = max(p90_by_inventory.values())
    value = max(floor_m, math.ceil(round(top, 9) / step_m) * step_m)
    return (min(value, cap_m), value > cap_m)


def zenodo_layer(name, epsg):
    # Geometry only; the DBF declares code page 'ANSI 932', which pyshp cannot resolve, so cp932 is given explicitly.
    shp = next(readable(ZENODO_IBURI).rglob(f'{name}.shp'))
    with shapefile.Reader(str(shp), encoding='cp932', encodingErrors='replace') as r:
        n_total, bbox = len(r), list(r.bbox)
        raw = [shape(s.__geo_interface__) for s in r.shapes() if s.shapeType != shapefile.NULL]
    t = Transformer.from_crs(layer_crs(shp), CRS.from_epsg(epsg), always_xy=True)
    geoms = [shapely.make_valid(shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1]))))
             for g in raw]
    return geoms, {'file': shp.name, 'crs': layer_crs(shp).to_string(), 'n_total': n_total,
                   'n_null': n_total - len(geoms), 'bbox_native': bbox}


def iburi_phase1(epsg=IBURI_EPSG):
    """ShakeMap coverage of the GSI extent, coverage of the Zenodo old-landslide layer, positives after the registered
    old-landslide rule and the Iburi buffer statistic. Counts and polygon areas only: no terrain value, no sample."""
    cfg = config()
    ib = cfg['registry']['datasets']['iburi_2018']
    if ib['role'] != 'development' or ib.get('working_crs') != f'EPSG:{epsg}':
        raise RuntimeError('Iburi is not registered as a development inventory in EPSG:%d (Amendment 1)' % epsg)
    files = gsi_files()
    ext = _feature_collection(files['extent'])['features'][0]['geometry']['coordinates']
    extent_ll = extent_polygon(ext)
    extent = lonlat_to_utm(extent_ll, epsg)
    feats = _feature_collection(files['landslides'])['features']
    main_i, other_i = split_by_style(feats)
    polys = [shapely.make_valid(lonlat_to_utm(shape(feats[i]['geometry']), epsg)) for i in main_i]
    old, old_meta = zenodo_layer('old_landslides', epsg)
    react, react_meta = zenodo_layer('reactivated_landslides', epsg)

    # ShakeMap coverage of the extent (grid is a lon/lat rectangle: all vertices inside -> extent inside).
    prov = read_json(RAW / 'shakemap_iburi_2018' / 'provenance.json')
    gpath = RAW / 'shakemap_iburi_2018' / 'grid.xml'
    if file_digest(gpath, 'sha256') != prov['sha256']:
        raise RuntimeError(f'{gpath} changed since download (frozen)')
    values, lon0, lat_top, dlon, dlat, units = read_grid(gpath)
    lon, lat = np.asarray(extent_ll.exterior.coords).T
    at_vertices = bilinear(values, lon0, lat_top, dlon, dlat, lon, lat)
    coverage = {'grid_sha256': prov['sha256'], 'shakemap_version': prov['grid_header']['shakemap_version'],
                'process_timestamp': prov['grid_header']['process_timestamp'],
                'point_source': prov['grid_header']['event'].get('point_source'),
                'grid_lonlat_bbox': [lon0, lat_top - dlat * (values.shape[0] - 1), lon0 + dlon * (values.shape[1] - 1), lat_top],
                'extent_vertices': len(lon), 'extent_vertices_inside_grid_with_value': int(np.isfinite(at_vertices).sum()),
                'extent_covered': bool(np.isfinite(at_vertices).all())}

    # Coverage of the Zenodo old-landslide mapping (no extent file exists): its bounding box against the GSI extent.
    ob = old_meta['bbox_native']
    box_ll = Polygon([(ob[0], ob[1]), (ob[2], ob[1]), (ob[2], ob[3]), (ob[0], ob[3])])
    box = lonlat_to_utm(box_ll.segmentize(0.01), epsg)
    outside = extent.difference(box)
    old_hit = intersects_any(polys, old)
    outside_box = np.array([not box.contains(p.representative_point()) for p in polys])
    positives = [p for p, h in zip(polys, old_hit) if not h]
    areas = np.array([p.area for p in positives])
    react_in_old = intersects_any(react, old)
    result = {
        'version': 'susceptibility_v02', 'computed_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Iburi Phase 1: ShakeMap coverage, old-landslide coverage and counts, buffer statistic. Polygon counts and '
                 'areas only; no terrain value, no sample, no model.',
        'working_crs': f'EPSG:{epsg}',
        'shakemap_coverage': coverage,
        'old_landslides': {
            'layer': old_meta, 'reactivated_layer': react_meta,
            'reactivated_intersecting_old': int(react_in_old.sum()),
            'old_inside_or_touching_gsi_extent': int(intersects_any(old, [extent]).sum()),
            'old_bbox_lonlat': ob,
            'gsi_extent_area_km2': extent.area / 1e6,
            'gsi_extent_area_outside_old_bbox_km2': outside.area / 1e6,
            'gsi_extent_share_outside_old_bbox': outside.area / extent.area,
            'note': 'The Zenodo record has no extent for its old-landslide mapping; its bounding box is an upper bound of '
                    'the mapped area. Inside the box, absence of old landslides is not proof of coverage.'},
        'gsi_polygons': {
            'main_style': len(polys), 'deviating_style_exclusion_only': len(other_i),
            'intersecting_old_landslides_not_positive': int(old_hit.sum()),
            'positives_after_old_landslide_rule': len(positives),
            'main_style_outside_old_bbox': int(outside_box.sum()),
            'positives_outside_old_bbox': int((outside_box & ~old_hit).sum())},
        'buffer_statistic': {
            'rule': cfg['sampling']['background_rule']['exclusion_buffer_rule'],
            'iburi_positive_p90_equivalent_radius_m': equivalent_radius_p90(areas),
            'iburi_positive_area_m2_quantiles': {str(q): float(np.quantile(areas, q)) for q in (0.1, 0.5, 0.9)}},
    }
    write_json(guard(REPORT) / 'phase1_iburi_extent_counts.json', result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['gsi_fetch', 'gsi_inspect', 'shakemap', 'pga', 'iburi'])
    ap.add_argument('dataset', nargs='?')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.stage == 'gsi_fetch':
        res = gsi_fetch()
    elif a.stage == 'gsi_inspect':
        res = gsi_inspect()
    elif a.stage == 'iburi':
        res = iburi_phase1()
    elif a.stage == 'shakemap':
        res = shakemap_fetch(a.dataset)
    else:
        res = pga(a.dataset, a.limit)[1]
    print(json.dumps(res, indent=1, ensure_ascii=False)[:12000])


if __name__ == '__main__':
    main()
