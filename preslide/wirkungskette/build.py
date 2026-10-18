"""Expensive, cached preparation of the demo window: terrain, scored cells, relief, contours, infrastructure.

Run `python -m preslide.wirkungskette build [--radius-m R]`; every checkpoint is identity- and SHA-256-sealed.
"""
import io
import math

import joblib
import numpy as np
import pandas as pd
from PIL import Image
from shapely import wkb
from shapely.geometry import LineString, Polygon

from ..matching import austria_boundary
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE, derivatives
from ..v04 import terrain as T4
from ..v04.models import STATIC, add_one_hot
from ..common import read_json
from . import core, sources, store
from .paths import DATA, config, guard, sha

REASONS = ['outside_austria', 'terrain_not_computable', 'elevation_out_of_range', 'slope_below_minimum',
           'catchment_truncated', 'no_land_cover', 'no_geology']


# ---------- identities (a config change of a relevant block changes the checkpoint identity) ----------

def terrain_identity(cfg, radius_max_m):
    return store.identity({'demo': cfg['demo'], 'terrain': cfg['terrain'], 'radius_max_m': float(radius_max_m), 'algorithm': 1})


def cells_identity(cfg, radius_max_m):
    return store.identity({'terrain': terrain_identity(cfg, radius_max_m), 'review_points': cfg['review_points'],
                           'release_points': cfg['release_points'], 'algorithm': 1})


def osm_identity(cfg, radius_max_m):
    return store.identity({'terrain': terrain_identity(cfg, radius_max_m), 'infrastructure': cfg['infrastructure'], 'algorithm': 1})


def window_radius_m(cfg, radius_max_m):
    t = cfg['terrain']
    return radius_max_m + t['window_extra_m'] + t['catchment_margin_m']


def paths(radius_max_m):
    d = DATA / f'demo_r{int(float(radius_max_m))}'
    return {'dir': d, 'terrain': d / 'terrain.npz', 'cells': d / 'cells.parquet', 'relief': d / 'relief.png',
            'relief_meta': d / 'relief.json', 'contours': d / 'contours.json', 'osm': d / 'infrastructure.parquet'}


# ---------- terrain ----------

def build_terrain(cfg, radius_max_m):
    p, ident = paths(radius_max_m), terrain_identity(cfg, radius_max_m)
    if store.exists(p['terrain']):
        return store.load_npz(p['terrain'], ident)
    d, t = cfg['demo'], cfg['terrain']
    dem, left, top, srcs = T4.dem_window(d['centre_longitude'], d['centre_latitude'], window_radius_m(cfg, radius_max_m),
                                         t['resolution_m'], t['crs'], d['reference_day'])
    filled, outlet, iterations = T4.fill_depressions(dem.astype(float))
    _, edge = T4.flow_accumulation(filled, outlet, t['resolution_m'])
    guard(p['dir'])
    arrays = {'dem': dem, 'filled': filled, 'edge': edge, 'left': np.array(left), 'top': np.array(top),
              'resolution': np.array(t['resolution_m'])}
    store.save_npz(p['terrain'], ident, arrays, {'dem_sources': srcs, 'fill_iterations': int(iterations),
                                                 'nodata_cells': int(np.isnan(dem).sum()), 'shape': list(dem.shape)})
    return arrays


# ---------- scored cells ----------

def model_bundle(cfg):
    rp = cfg['review_points']
    path = ROOT / rp['model']
    if sha(path) != rp['model_sha256']:
        raise RuntimeError('V0.4 static model changed (SHA-256 mismatch); only the frozen model may be used')
    bundle = joblib.load(path)
    if list(bundle['columns']) != list(STATIC):
        raise RuntimeError('Model columns differ from the registered V0.4 static feature list')
    return bundle


def demo_events(cfg, radius_max_m):
    """Documented V0.4 positives of the reference day inside the window (frozen V0.4 dataset, read only)."""
    data = pd.read_parquet(ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet')
    pos = data[(data.label == 1) & (data.event_day == cfg['demo']['reference_day'])].copy()
    cx, cy = PROJECT.transform(cfg['demo']['centre_longitude'], cfg['demo']['centre_latitude'])
    pos = pos[core.distance_m(pos.x, pos.y, cx, cy) <= radius_max_m]
    return pos[['event_group_id', 'process_type', 'x', 'y', 'longitude', 'latitude']].reset_index(drop=True)


def eligibility(frame, cfg):
    """Reason per row ('' = assessable); first failing rule wins (counts are reported)."""
    t = cfg['terrain']
    lo, hi = t['elevation_range_m']
    finite = frame[['elevation', 'slope', 'aspect_sin', 'aspect_cos', 'profile_curvature', 'plan_curvature', 'roughness_tri',
                    'tpi_150m', 'tpi_500m', 'relative_position_500m']].notna().all(axis=1)
    rules = [~frame.inside_austria, ~finite, ~frame.elevation.between(lo, hi), frame.slope < t['minimum_slope_deg'],
             frame.catchment_truncated.astype(bool) | frame.log10_catchment_m2.isna(),
             frame.land_cover_class.isna(), frame.geology_class.isna()]
    reason = pd.Series('', index=frame.index)
    for name, mask in zip(REASONS, rules):
        reason = reason.mask((reason == '') & mask.to_numpy(), name)
    return reason


def build_cells(cfg, radius_max_m, terrain):
    p, ident = paths(radius_max_m), cells_identity(cfg, radius_max_m)
    if store.exists(p['cells']):
        return store.load_parquet(p['cells'], ident)
    d, t, rp = cfg['demo'], cfg['terrain'], cfg['review_points']
    res, left, top, dem = float(terrain['resolution']), float(terrain['left']), float(terrain['top']), terrain['dem']
    cx, cy = PROJECT.transform(d['centre_longitude'], d['centre_latitude'])
    rows, cols, x, y = core.grid_cells(cx, cy, radius_max_m, left, top, res, rp['cell_m'], dem.shape)
    ev = demo_events(cfg, radius_max_m)
    er, ec = core.xy_to_cell(left, top, res, ev.x, ev.y)
    frame = pd.DataFrame({'kind': ['grid'] * len(rows) + ['event'] * len(ev),
                          'event_id': [''] * len(rows) + ev.event_group_id.tolist(),
                          'process_type': [''] * len(rows) + ev.process_type.tolist(),
                          'row': np.concatenate([rows, er]), 'col': np.concatenate([cols, ec]),
                          'x': np.concatenate([x, ev.x.to_numpy()]), 'y': np.concatenate([y, ev.y.to_numpy()])})
    frame['sample_id'] = [f's{i}' for i in range(len(frame))]
    frame['longitude'], frame['latitude'] = INVERSE.transform(frame.x.to_numpy(), frame.y.to_numpy())
    frame['distance_m'] = core.distance_m(frame.x, frame.y, cx, cy)
    slope, aspect = derivatives(dem, res)
    frame['elevation'] = dem[frame.row, frame.col].astype(float)
    frame['slope'] = slope[frame.row, frame.col].astype(float)
    frame['aspect'] = aspect[frame.row, frame.col].astype(float)
    frame['aspect_sin'], frame['aspect_cos'] = np.sin(np.deg2rad(frame.aspect)), np.cos(np.deg2rad(frame.aspect))
    tcfg = {'terrain_resolution_m': res, 'terrain_crs': t['crs'], 'control_max_distance_m': radius_max_m}
    feats, meta = T4.static_features({'longitude': d['centre_longitude'], 'latitude': d['centre_latitude'], 'event_day': d['reference_day']},
                                     frame[['sample_id', 'x', 'y']], tcfg, margin_m=t['catchment_margin_m'])
    if not np.allclose(feats.static_dem_elevation_check.to_numpy(), frame.elevation.to_numpy(), equal_nan=True):
        raise RuntimeError('DEM window of the V0.4 feature code differs from the demo window')
    frame = frame.merge(feats.drop(columns='static_dem_elevation_check'), on='sample_id')
    frame['inside_austria'] = core_inside_austria(frame.longitude.to_numpy(), frame.latitude.to_numpy())
    v4 = read_json(ROOT / 'config/v04.json')['features']
    pad = 0.003
    bounds = (frame.longitude.min() - pad, frame.latitude.min() - pad, frame.longitude.max() + pad, frame.latitude.max() + pad)
    geoms, codes = sources.land_cover_polygons(bounds, rp['land_cover_vintage'], tiles=max(1, math.ceil(radius_max_m / 2500)))
    lc = sources.land_cover_at(frame.longitude, frame.latitude, geoms, codes, v4['land_cover']['classes'])
    geo = sources.geology_at(frame.longitude, frame.latitude, v4['geology']['classes'])
    frame = add_one_hot(pd.concat([frame, lc, geo], axis=1))
    frame['reason'] = eligibility(frame, cfg)
    bundle = model_bundle(cfg)
    ok = frame.reason == ''
    X = frame.loc[ok, bundle['columns']]
    if X.isna().any().any():
        raise ValueError('NaN in a required static feature of an assessable cell')
    z = bundle['preprocessor'].transform(X, pd.Series(np.arange(len(X)), index=X.index))
    frame['score'] = np.nan
    frame.loc[ok, 'score'] = bundle['model'].decision_function(z)
    store.save_parquet(p['cells'], ident, frame.drop(columns=['sample_id']),
                       {'terrain_meta': meta, 'land_cover_polygons': len(geoms), 'model_sha256': rp['model_sha256']})
    return store.load_parquet(p['cells'], ident)


_COUNTRY = []


def core_inside_austria(lon, lat):
    from shapely import contains_xy
    if not _COUNTRY:
        _COUNTRY.append(austria_boundary())
    return contains_xy(_COUNTRY[0], lon, lat)


# ---------- relief and contours ----------

def corners_lonlat(left, top, res, shape_rc):
    """MapLibre image corners (top-left, top-right, bottom-right, bottom-left) of an EPSG:31287 raster."""
    right, bottom = left + shape_rc[1] * res, top - shape_rc[0] * res
    return [[round(v, 7) for v in INVERSE.transform(px, py)] for px, py in ((left, top), (right, top), (right, bottom), (left, bottom))]


def build_relief(cfg, radius_max_m, terrain):
    p, ident = paths(radius_max_m), terrain_identity(cfg, radius_max_m)
    if store.exists(p['relief']) and store.exists(p['relief_meta']) and store.exists(p['contours']):
        return store.load_json(p['relief_meta'], ident)
    dem, res = terrain['dem'], float(terrain['resolution'])
    shade = core.hillshade(dem, res)
    ok = np.isfinite(shade)
    rgba = np.zeros(dem.shape + (4,), np.uint8)
    rgba[..., :3] = np.where(ok, shade, 0).astype(np.uint8)[..., None]
    rgba[..., 3] = np.where(ok, 255, 0)
    buf = io.BytesIO()
    Image.fromarray(rgba, 'RGBA').save(buf, format='PNG', optimize=True)
    store.save_bytes(p['relief'], ident, buf.getvalue())
    meta = {'corners': corners_lonlat(float(terrain['left']), float(terrain['top']), res, dem.shape),
            'shape': list(dem.shape), 'resolution_m': res, 'crs': cfg['terrain']['crs']}
    store.save_json(p['relief_meta'], ident, meta)
    store.save_json(p['contours'], ident, contours(dem, float(terrain['left']), float(terrain['top']), res))
    return meta


def contours(dem, left, top, res, interval_m=50, major_m=250, simplify_m=8):
    """Contour lines (GeoJSON, WGS84) from the DEM; drawn with matplotlib's marching squares, simplified in metres."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    z = np.where(np.isfinite(dem), dem, np.nan)
    levels = np.arange(math.ceil(np.nanmin(z) / interval_m) * interval_m, np.nanmax(z), interval_m)
    xs = left + (np.arange(dem.shape[1]) + .5) * res
    ys = top - (np.arange(dem.shape[0]) + .5) * res
    fig = plt.figure()
    cs = plt.contour(xs, ys, z, levels=levels)
    features = []
    for level, segs in zip(cs.levels, cs.allsegs):
        for seg in segs:
            if len(seg) < 4:
                continue
            line = LineString(seg).simplify(simplify_m)
            lon, lat = INVERSE.transform(*np.asarray(line.coords).T)
            features.append({'type': 'Feature', 'properties': {'hoehe_m': int(level), 'haupt': bool(level % major_m == 0)},
                             'geometry': {'type': 'LineString', 'coordinates': [[round(a, 5), round(b, 5)] for a, b in zip(lon, lat)]}})
    plt.close(fig)
    return {'type': 'FeatureCollection', 'features': features}


# ---------- infrastructure ----------

def window_bounds_lonlat(cfg, radius_max_m):
    d = cfg['demo']
    cx, cy = PROJECT.transform(d['centre_longitude'], d['centre_latitude'])
    r = window_radius_m(cfg, radius_max_m)
    lon, lat = INVERSE.transform([cx - r, cx + r, cx + r, cx - r], [cy - r, cy - r, cy + r, cy + r])
    return min(lon), min(lat), max(lon), max(lat)


def classify_way(tags):
    if 'building' in tags:
        return 'gebaeude'
    if 'railway' in tags:
        return 'bahn'
    if tags.get('highway') == 'track':
        return 'weg'
    if 'highway' in tags:
        return 'strasse'
    return None


def parse_osm(elements):
    rows = []
    for e in elements:
        if e.get('type') != 'way' or 'geometry' not in e:
            continue
        typ = classify_way(e.get('tags', {}))
        if typ is None:
            continue
        lon = np.array([g['lon'] for g in e['geometry']])
        lat = np.array([g['lat'] for g in e['geometry']])
        x, y = PROJECT.transform(lon, lat)
        coords = np.column_stack([x, y])
        if typ == 'gebaeude':
            if len(coords) < 4:
                continue
            geom = Polygon(coords).buffer(0)
        else:
            if len(coords) < 2:
                continue
            geom = LineString(coords)
        tags = e.get('tags', {})
        rows.append({'osm_id': int(e['id']), 'typ': typ, 'name': tags.get('name', ''),
                     'klasse': tags.get('highway') or tags.get('railway') or tags.get('building', ''),
                     'geometry_wkb': wkb.dumps(geom)})
    return pd.DataFrame(rows)


def build_osm(cfg, radius_max_m):
    p, ident = paths(radius_max_m), osm_identity(cfg, radius_max_m)
    if store.exists(p['osm']):
        return store.load_parquet(p['osm'], ident)
    inf = cfg['infrastructure']
    body = ''.join(t['query'] + ';' for t in inf['types'].values())
    data, meta = sources.overpass(body, window_bounds_lonlat(cfg, radius_max_m), inf['user_agent'])
    frame = parse_osm(data['elements'])
    guard(p['dir'])
    store.save_parquet(p['osm'], ident, frame, {'overpass_url_sha256': meta['sha256'], 'retrieved_at': meta.get('retrieved_at'),
                                                'osm_base': data.get('osm3s', {}).get('timestamp_osm_base'),
                                                'counts': frame.typ.value_counts().to_dict()})
    return store.load_parquet(p['osm'], ident)


def osm_features(frame):
    return [{'geometry': wkb.loads(g), 'typ': t, 'name': n, 'klasse': k, 'osm_id': int(o)}
            for g, t, n, k, o in zip(frame.geometry_wkb, frame.typ, frame.name, frame.klasse, frame.osm_id)]


def build(radius_max_m=None):
    cfg = config()
    radius_max_m = float(radius_max_m or cfg['radius_m']['max'])
    terrain = build_terrain(cfg, radius_max_m)
    cells = build_cells(cfg, radius_max_m, terrain)
    relief = build_relief(cfg, radius_max_m, terrain)
    osm = build_osm(cfg, radius_max_m)
    return {'cells': len(cells), 'assessable': int((cells.reason == '').sum()),
            'reasons': cells.reason[cells.reason != ''].value_counts().to_dict(),
            'events': int((cells.kind == 'event').sum()), 'relief_shape': relief['shape'],
            'infrastructure': osm.typ.value_counts().to_dict()}

