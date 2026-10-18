"""hangmap_v01 area computation: DEM window -> static features (V0.5 code) -> frozen V0.5 static model -> shares."""
import hashlib
import json
import shutil
import subprocess
import time
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from shapely import STRtree, points as shp_points, contains_xy
from shapely.geometry import shape

from ..common import digest, read_json, write_json
from ..matching import austria_boundary
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE, derivatives
from ..v04 import context as C
from ..v04.http import full_url, _read
from ..v05 import terrain as T
from ..v05 import models as M5
from ..v05.paths import sha, config as v05_config
from . import core
from .paths import DATA, READ_ONLY_HTTP, CONFIG, config, guard

REASON_DE = {'outside_austria': 'außerhalb Österreichs', 'terrain_not_computable': 'Gelände nicht berechenbar',
             'elevation_out_of_range': 'Höhe außerhalb des Modellbereichs', 'slope_below_minimum': 'Neigung unter 5° (außerhalb des Modellbereichs)',
             'catchment_truncated': 'Einzugsgebiet am Fensterrand abgeschnitten', 'no_land_cover': 'Landbedeckung nicht eindeutig',
             'no_geology': 'Geologie nicht eindeutig'}
NOTICE = ('Relative Anteile zwischen Vergleichshängen aus Geländeinformation (V0.5, explorativ). Keine Eintrittswahrscheinlichkeit, '
          'keine Warnung, keine Kausalität. Ein Teil der Trennung kann Meldebias sein (Straßen, Siedlungen, Grünland); '
          'mit gematchten Kontrollen trennt das Modell deutlich schwächer (lokale AUC 0,70 statt 0,85).')


# ---------- cached requests (own write location, read-only reuse of earlier caches) ----------

def cached_json(url, params, f_param=True):
    target = full_url(url, {**params, 'f': 'json'} if f_param else params)
    key = hashlib.sha256(target.encode()).hexdigest()
    for directory in READ_ONLY_HTTP + (DATA / 'cache/http',):
        if (directory / f'{key}.json').exists():
            return _read(directory / f'{key}.json', target)
    path = guard(DATA / 'cache/http') / f'{key}.json'
    curl = shutil.which('curl.exe') or shutil.which('curl')
    for attempt in range(4):
        r = subprocess.run([curl, '--silent', '--show-error', '--location', '--max-time', '120', '-w', '\n%{http_code}', target],
                           capture_output=True, timeout=150)
        body, _, code = r.stdout.rpartition(b'\n')
        if r.returncode == 0 and code == b'200':
            data = json.loads(body)
            if isinstance(data, dict) and 'error' in data:
                raise RuntimeError(f"Source error: {data['error']}")
            path.write_bytes(body)
            path.with_suffix('.meta.json').write_text(json.dumps({'url': target, 'sha256': hashlib.sha256(body).hexdigest()}), encoding='utf-8')
            return data
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f'Request failed: {target[:160]}')


# ---------- land cover (polygons per area envelope) and geology (whole layer) ----------

def land_cover_cells(lon, lat, classes, vintage):
    """CORINE class per point; no or several polygons covering a point = missing (V0.4 rule)."""
    url, field = C.CLC[vintage]
    pad = 0.002
    env = {'xmin': float(lon.min()) - pad, 'ymin': float(lat.min()) - pad, 'xmax': float(lon.max()) + pad, 'ymax': float(lat.max()) + pad,
           'spatialReference': {'wkid': 4326}}
    r = cached_json(url, {'geometry': json.dumps(env), 'geometryType': 'esriGeometryEnvelope', 'inSR': '4326', 'outSR': '4326',
                          'spatialRel': 'esriSpatialRelIntersects', 'outFields': field, 'returnGeometry': 'true'})
    if r.get('exceededTransferLimit'):
        raise RuntimeError('CORINE response truncated; area too large for one request')
    geoms = [C._rings(f['geometry']['rings']) for f in r['features']]
    codes = [f['attributes'][field] for f in r['features']]
    tree = STRtree(geoms)
    out = []
    for p in shp_points(lon.to_numpy(), lat.to_numpy()):
        hit = {codes[i] for i in tree.query(p) if geoms[i].covers(p)}
        out.append(next(iter(hit)) if len(hit) == 1 else None)
    return pd.DataFrame({'clc_code': out, 'land_cover_class': [C.clc_class(c, classes) if c is not None else None for c in out]})


@lru_cache(maxsize=1)
def geology_layer():
    ids = sorted(cached_json(C.GEOLOGY, {'where': '1=1', 'returnIdsOnly': 'true'})['objectIds'])
    geoms, lith = [], []
    for i in range(0, len(ids), 200):
        r = cached_json(C.GEOLOGY, {'objectIds': ','.join(map(str, ids[i:i + 200])), 'outFields': 'OBJECTID,representativeLithology',
                                    'outSR': '4326', 'returnGeometry': 'true'})
        for f in r['features']:
            rings = f['geometry']['rings']
            geoms.append(shape({'type': 'Polygon', 'coordinates': rings}) if len(rings) == 1 else C._rings(rings))
            lith.append(f['attributes']['representativeLithology'])
    if len(geoms) != len(ids):
        raise ValueError('Incomplete geology layer')
    return {'tree': STRtree(geoms), 'geoms': geoms, 'lith': lith}


def geology_cells(lon, lat, classes):
    layer, out = geology_layer(), []
    for p in shp_points(lon.to_numpy(), lat.to_numpy()):
        names = {layer['lith'][i] for i in layer['tree'].query(p) if layer['geoms'][i].covers(p)}
        if len(names) != 1:
            out.append(None)
            continue
        lith = next(iter(names))
        out.append(next((k for k, v in classes.items() if isinstance(v, list) and lith in v), 'geo_crystalline_other'))
    return pd.DataFrame({'geology_class': out})


# ---------- model ----------

@lru_cache(maxsize=1)
def model_bundle():
    cfg = config()['model']
    path = ROOT / cfg['bundle']
    if sha(path) != cfg['bundle_sha256']:
        raise RuntimeError('V0.5 static model changed (SHA-256 mismatch); hangmap_v01 uses only the frozen model')
    bundle = joblib.load(path)
    v5 = v05_config()
    if list(bundle['columns']) != list(v5['features']['static']):
        raise RuntimeError('Model columns differ from the registered V0.5 static allowlist')
    M5.check_allowlist(bundle['columns'], v5)
    return bundle


def score_frame(frame):
    """Linear conditional-logit score of rows whose static features are all finite (no imputation)."""
    b = model_bundle()
    X = frame[b['columns']]
    if X.isna().any().any():
        raise ValueError('NaN in a required static feature')
    z = b['preprocessor'].transform(X, pd.Series(np.arange(len(X)), index=X.index))
    return b['model'].decision_function(z), z


# ---------- area ----------

@lru_cache(maxsize=1)
def _country():
    return austria_boundary()


def inside_austria(lon, lat):
    return contains_xy(_country(), np.atleast_1d(lon), np.atleast_1d(lat))


def terrain_cells(lon, lat, radius_m, extra_xy, reference_date, cfg):
    """Static feature table for grid cells (+ custom points) around (lon, lat); V0.5 static_features, unchanged."""
    t = cfg['terrain']
    tcfg = {'terrain_resolution_m': t['resolution_m'], 'terrain_crs': t['crs'], 'control_max_distance_m': radius_m}
    res = t['resolution_m']
    cx, cy = PROJECT.transform(lon, lat)
    window_radius = radius_m + 300 + t['catchment_margin_m']
    dem, left, top, sources = T.dem_window(lon, lat, window_radius, res, t['crs'], reference_date)
    rows, cols, x, y = core.grid_cells(cx, cy, radius_m, left, top, res, cfg['area']['cell_m'], dem.shape)
    kind = np.array(['grid'] * len(x))
    if extra_xy is not None and len(extra_xy):
        ex = np.asarray(extra_xy, float)
        er, ec = np.floor((top - ex[:, 1]) / res).astype(int), np.floor((ex[:, 0] - left) / res).astype(int)
        if (er < 0).any() or (ec < 0).any() or (er >= dem.shape[0]).any() or (ec >= dem.shape[1]).any():
            raise ValueError('custom point outside terrain window')
        rows, cols = np.concatenate([rows, er]), np.concatenate([cols, ec])
        x, y = core.dem_cell_xy(left, top, res, rows, cols)
        kind = np.concatenate([kind, ['custom'] * len(er)])
    lonlat = INVERSE.transform(x, y)
    frame = pd.DataFrame({'sample_id': [f'c{i}' for i in range(len(x))], 'kind': kind, 'row': rows, 'col': cols, 'x': x, 'y': y,
                          'longitude': lonlat[0], 'latitude': lonlat[1]})
    slope, aspect = derivatives(dem, res)
    frame['elevation'] = dem[rows, cols].astype(float)
    frame['slope'] = slope[rows, cols].astype(float)
    frame['aspect'] = aspect[rows, cols].astype(float)
    frame['aspect_sin'], frame['aspect_cos'] = core.aspect_features(frame.aspect)
    feats, meta = T.static_features({'longitude': lon, 'latitude': lat, 'event_day': reference_date}, frame[['sample_id', 'x', 'y']],
                                    tcfg, margin_m=t['catchment_margin_m'])
    if not np.allclose(feats.static_dem_elevation_check.to_numpy(), frame.elevation.to_numpy(), equal_nan=True):
        raise RuntimeError('DEM window of the feature code differs from the hangmap window')
    return frame.merge(feats.drop(columns='static_dem_elevation_check'), on='sample_id'), {**meta, 'dem_sources': len(sources)}


def eligibility(frame, cfg):
    """Reason per row ('' = eligible); first failing rule wins, counts are reported."""
    t = cfg['terrain']
    lo, hi = t['elevation_range_m']
    finite = frame[['elevation', 'slope', 'aspect_sin', 'aspect_cos', 'profile_curvature', 'plan_curvature', 'roughness_tri',
                    'tpi_150m', 'tpi_500m', 'relative_position_500m']].notna().all(axis=1)
    rules = [('outside_austria', ~frame.inside_austria), ('terrain_not_computable', ~finite),
             ('elevation_out_of_range', ~frame.elevation.between(lo, hi)), ('slope_below_minimum', frame.slope < t['minimum_slope_deg']),
             ('catchment_truncated', frame.catchment_truncated | frame.log10_catchment_m2.isna()),
             ('no_land_cover', frame.land_cover_class.isna()), ('no_geology', frame.geology_class.isna())]
    reason = pd.Series('', index=frame.index)
    for name, mask in rules:
        reason = reason.mask((reason == '') & mask.to_numpy(), name)
    return reason


def build_features(lon, lat, radius_m, points, cfg):
    reference_date = cfg['terrain']['reference_date']
    extra = None
    if points:
        extra = np.column_stack(PROJECT.transform(np.array([p[0] for p in points]), np.array([p[1] for p in points])))
    frame, meta = terrain_cells(lon, lat, radius_m, extra, reference_date, cfg)
    frame['inside_austria'] = inside_austria(frame.longitude.to_numpy(), frame.latitude.to_numpy())
    v4 = read_json(ROOT / 'config/v04.json')['features']
    lc = land_cover_cells(frame.longitude, frame.latitude, v4['land_cover']['classes'], cfg['land_cover']['vintage'])
    geo = geology_cells(frame.longitude, frame.latitude, v4['geology']['classes'])
    frame = M5.add_one_hot(pd.concat([frame, lc, geo], axis=1))
    frame['reason'] = eligibility(frame, cfg)
    return frame, meta


def compute(lon, lat, radius_m=None, points=None):
    """Full result (JSON-serialisable). Deterministic; cached by request + configuration hash with a verified sidecar."""
    cfg = config()
    radius_m = float(radius_m if radius_m is not None else cfg['area']['radius_m']['default'])
    points = [[float(a), float(b)] for a, b in points] if points else None
    core.validate_request(radius_m, points, cfg)
    if not inside_austria(lon, lat)[0]:
        raise ValueError('Das Gebiet muss in Österreich liegen')
    if points and not inside_austria(np.array([p[0] for p in points]), np.array([p[1] for p in points])).all():
        raise ValueError('Alle Punkte müssen in Österreich liegen')
    key = digest({'lon': round(lon, 5), 'lat': round(lat, 5), 'r': radius_m, 'pts': points, 'cfg': sha(CONFIG)})
    path = guard(DATA / 'cache/results') / f'{key}.json'
    side = path.with_suffix('.sha256')
    if path.exists() and side.exists():
        if sha(path) != side.read_text().strip():
            raise RuntimeError(f'Cache checksum mismatch: {path}')
        return read_json(path)
    result = _compute(lon, lat, radius_m, points, cfg)
    write_json(path, result)
    side.write_text(sha(path))
    return result


def _compute(lon, lat, radius_m, points, cfg):
    frame, meta = build_features(lon, lat, radius_m, points, cfg)
    grid = frame[frame.kind == 'grid']
    reasons = grid.reason[grid.reason != ''].value_counts().to_dict()
    bad = frame[(frame.kind == 'custom') & (frame.reason != '')]
    if len(bad):
        raise ValueError('Mindestens ein gewählter Punkt ist nicht bewertbar: ' + ', '.join(sorted({REASON_DE[x] for x in bad.reason})))
    ok = frame[frame.reason == ''].copy()
    score, z = score_frame(ok)
    ok['score'] = score
    ok['zvec'] = list(z)
    g = cfg['area']['comparison_group']
    heat = ok[ok.kind == 'grid'].copy()
    if len(heat) < g['size']:
        raise ValueError(f'Zu wenige bewertbare Hangzellen im Gebiet ({len(heat)} < {g["size"]}); Radius vergrößern')
    heat['share_area'] = core.shares(heat.score, np.zeros(len(heat), int))
    heat['index_area'], heat['percentile'] = core.area_index(heat.share_area, len(heat))
    if points:
        grp = ok[ok.kind == 'custom'].copy()
    else:
        ids = core.select_group(heat.index.to_numpy(), heat.x, heat.y, g['size'], g['separation_m'], core.group_seed(lon, lat, radius_m))
        if len(ids) < g['size']:
            raise ValueError('Vergleichsgruppe mit 10 getrennten Hängen nicht bildbar; Radius vergrößern')
        grp = heat.loc[ids].copy()
    grp['share'] = core.shares(grp.score, np.zeros(len(grp), int))
    bundle = model_bundle()
    coef = bundle['model'].coef_
    cols = bundle['columns']

    def drivers(row):
        c = row.zvec * coef
        return [{'feature': cols[i], 'contribution': round(float(c[i]), 3)} for i in np.argsort(-np.abs(c))[:3]]

    half = cfg['area']['cell_m'] / 2
    cells = []
    for r in heat.itertuples():
        corners = [INVERSE.transform(r.x + dx, r.y + dy) for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half), (-half, -half))]
        cells.append({'type': 'Feature', 'properties': {'index': round(r.index_area, 4), 'percentile': round(r.percentile, 1)},
                      'geometry': {'type': 'Polygon', 'coordinates': [[[round(a, 6), round(b, 6)] for a, b in corners]]}})
    members = [{'longitude': round(r.longitude, 6), 'latitude': round(r.latitude, 6), 'share': round(float(r.share), 4),
                'elevation_m': round(r.elevation), 'slope_deg': round(r.slope, 1), 'aspect_deg': round(r.aspect),
                'land_cover': r.land_cover_class, 'geology': r.geology_class, 'drivers': drivers(r)}
               for r in grp.sort_values('share', ascending=False).itertuples()]
    return {'version': cfg['version'], 'notice': NOTICE, 'centre': {'longitude': lon, 'latitude': lat}, 'radius_m': radius_m,
            'mode': 'custom_points' if points else 'auto_group', 'group': members,
            'group_share_sum': round(float(grp.share.sum()), 6),
            'heat': {'type': 'FeatureCollection', 'features': cells},
            'counts': {'grid_cells': int(len(grid)), 'eligible': int(len(heat)), 'excluded_by_reason': reasons},
            'terrain_meta': meta, 'model': {'bundle_sha256': cfg['model']['bundle_sha256'], 'variant': 'conditional_logit_static'}}
