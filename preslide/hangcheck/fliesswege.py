"""hangcheck_v01 step 5: one possible flow path downhill from every review point (scenario, unvalidated) and the
OpenStreetMap features lying inside the scenario corridor. Reuses the tested wirkungskette primitives unchanged."""
import hashlib
import json

import numpy as np

from ..common import read_json
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE
from ..v04.http import full_url, _read
from ..v04.terrain import fill_depressions
from ..v05 import terrain as T
from ..wirkungskette import core as W, store
from ..wirkungskette.build import parse_osm, osm_features
from ..wirkungskette.sources import OVERPASS, _curl, _store
from . import build
from .paths import DATA, config, guard

END_TEXT = {'gestoppt': 'Szenario endet innerhalb des Rechengebiets',
            'rand': 'Weg erreicht den Rand des Rechengebiets; das tatsächliche Ende ist unbekannt',
            'nodata': 'Weg erreicht eine Zelle ohne Höhenwert; nicht beurteilbar',
            'senke': 'Weg endet in einer nicht aufgelösten Senke',
            'max_laenge': 'Weg länger als die Höchstlänge'}


def scenario_config(cfg):
    """Fixed-reach scenarios, corridor and OSM types taken from config/wirkungskette_v01.json (literature values)."""
    wk = read_json(ROOT / cfg['flow_paths']['scenarios_from'])
    ids = cfg['flow_paths']['scenario_ids']
    scenarios = [s for s in wk['runout']['scenarios'] if s['id'] in ids]
    if [s['id'] for s in scenarios] != ids or any(s['kind'] != 'fixed_reach' for s in scenarios):
        raise RuntimeError('flow-path scenarios differ from the registered fixed-reach literature values')
    return scenarios, wk['runout']['corridor']['width_m'], wk['infrastructure']


def route_with_scenarios(filled, dem, row, col, res_m, left, top, scenarios, max_route_m):
    """D8 route on the filled surface and the stop index of every fixed-reach scenario (pure; EPSG:31287 metres)."""
    rows, cols, end = W.d8_route(filled, dem, row, col, res_m, max_route_m)
    s = W.path_distance_m(rows, cols, res_m)
    x, y = W.dem_cell_xy(left, top, res_m, rows, cols)
    stops = {sc['id']: W.fixed_reach_stop(s, sc['reach_m'], end) for sc in scenarios}
    return {'rows': rows, 'cols': cols, 'end': end, 's': s, 'x': x, 'y': y, 'stops': stops}


def overpass(query_body, bounds_lonlat, user_agent):
    """Wirkungskette Overpass request, cached immutably in this namespace (raw response + SHA-256 meta)."""
    w, s, e, n = bounds_lonlat
    query = f'[out:json][timeout:180][bbox:{s:.5f},{w:.5f},{n:.5f},{e:.5f}];({query_body});out geom;'
    target = full_url(OVERPASS, {'data': query})
    path = guard(DATA / 'cache/osm') / f'{hashlib.sha256(target.encode()).hexdigest()}.json'
    if not path.exists():
        body = _curl(['--max-time', '300', '-A', user_agent, '--data-urlencode', f'data={query}', OVERPASS], 360)
        if 'elements' not in json.loads(body):
            raise RuntimeError('Overpass response without elements')
        _store(path, target, body)
    meta = json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
    return _read(path, target), meta


def _lonlat(x, y):
    lon, lat = INVERSE.transform(np.asarray(x, float), np.asarray(y, float))
    return [[round(float(a), 6), round(float(b), 6)] for a, b in zip(np.atleast_1d(lon), np.atleast_1d(lat))]


def compute(lon, lat, radius_m=None):
    cfg = config()
    main = build.compute(lon, lat, radius_m)            # validates place and radius; cached
    radius_m = main['radius_m']
    ident = store.identity({'main': build.identity(lon, lat, radius_m, cfg), 'flow_paths': cfg['flow_paths'],
                            'scenarios': scenario_config(cfg)[0], 'algorithm': 1})
    path = guard(DATA / 'cache/fliesswege') / f'{ident}.json'
    if store.exists(path):
        return store.load_json(path, ident)
    result = _compute(lon, lat, radius_m, main, cfg)
    store.save_json(path, ident, result)
    return store.load_json(path, ident)


def inside_radius(cx_m, cy_m, px_m, py_m, radius_m):
    """True if a chosen start point lies inside the circle of the checked area (projected metres, EPSG:31287)."""
    return float(np.hypot(px_m - cx_m, py_m - cy_m)) <= radius_m


def compute_point(lon, lat, radius_m, point_lon, point_lat):
    """Possible flow path from one start point the user picks inside the checked area (same scenarios, no ranking)."""
    cfg = config()
    main = build.compute(lon, lat, radius_m)            # validates place and radius; cached
    radius_m = main['radius_m']
    cx, cy = PROJECT.transform(lon, lat)
    px, py = PROJECT.transform(point_lon, point_lat)
    if not inside_radius(cx, cy, px, py, radius_m):
        raise ValueError('Der Punkt liegt außerhalb des geprüften Umkreises. Bitte einen Punkt innerhalb des Kreises wählen.')
    point = [round(float(point_lon), 5), round(float(point_lat), 5)]
    ident = store.identity({'main': build.identity(lon, lat, radius_m, cfg), 'flow_paths': cfg['flow_paths'],
                            'scenarios': scenario_config(cfg)[0], 'algorithm': 1, 'punkt': point})
    path = guard(DATA / 'cache/fliesswege_punkt') / f'{ident}.json'
    if store.exists(path):
        return store.load_json(path, ident)
    ctx = _context(lon, lat, radius_m, cfg)
    result = _result(cfg, main, radius_m, ctx, [{'nr': 0, 'punkt': {'longitude': point[0], 'latitude': point[1]},
                                                 'szenarien': _flow(ctx, px, py, cfg)}])
    store.save_json(path, ident, result)
    return store.load_json(path, ident)


def _context(lon, lat, radius_m, cfg):
    """DEM window with filled surface and the OSM features of the area: shared by review points and a picked point."""
    fp, t = cfg['flow_paths'], cfg['terrain']
    scenarios, width_m, infra = scenario_config(cfg)
    res = t['resolution_m']
    window_m = radius_m + fp['window_extra_m']
    dem, left, top, _ = T.dem_window(lon, lat, window_m, res, t['crs'], t['reference_date'])
    filled, _, _ = fill_depressions(dem.astype(float))
    cx, cy = PROJECT.transform(lon, lat)
    bounds = INVERSE.transform([cx - window_m, cx + window_m], [cy - window_m, cy + window_m])
    data, meta = overpass(''.join(v['query'] + ';' for v in infra['types'].values()),
                          (bounds[0][0], bounds[1][0], bounds[0][1], bounds[1][1]), infra['user_agent'])
    features = osm_features(parse_osm(data['elements'])) if data['elements'] else []
    return {'dem': dem, 'filled': filled, 'left': left, 'top': top, 'res': res, 'scenarios': scenarios,
            'width_m': width_m, 'infra': infra, 'exposure': W.Exposure(features), 'data': data, 'meta': meta}


def _flow(ctx, px, py, cfg):
    r0, c0 = W.xy_to_cell(ctx['left'], ctx['top'], ctx['res'], [px], [py])
    route = route_with_scenarios(ctx['filled'], ctx['dem'], int(r0[0]), int(c0[0]), ctx['res'], ctx['left'], ctx['top'],
                                 ctx['scenarios'], cfg['flow_paths']['max_route_m'])
    types = list(ctx['infra']['types'])
    szen = []
    for sc in ctx['scenarios']:
        stop = route['stops'][sc['id']]
        area = W.corridor(route['x'], route['y'], stop['stop_index'], ctx['width_m'])
        szen.append({'id': sc['id'], 'bezeichnung': sc['label'], 'reichweite_m': sc['reach_m'], 'quelle': sc['source_de'],
                     'status': stop['status'], 'status_text': END_TEXT[stop['status']],
                     'laenge_m': round(float(route['s'][stop['stop_index']]), 1),
                     'weg': _lonlat(route['x'][:stop['stop_index'] + 1], route['y'][:stop['stop_index'] + 1]),
                     'korridor': {'type': 'Polygon', 'coordinates': [_lonlat(*area.exterior.xy)]},
                     'im_szenario': W.count_by_type(ctx['exposure'].hits(area), types)})
    return szen


def _result(cfg, main, radius_m, ctx, out):
    data, meta, infra = ctx['data'], ctx['meta'], ctx['infra']
    labels = {k: v['label'] for k, v in infra['types'].items()}
    return {'version': cfg['version'], 'centre': main['centre'], 'radius_m': radius_m, 'fliesswege': out,
            'korridor_breite_m': ctx['width_m'], 'typen': labels,
            'osm': {'stand': data.get('osm3s', {}).get('timestamp_osm_base'), 'abgerufen': meta.get('retrieved_at'),
                    'hinweis': 'heutiger OpenStreetMap-Stand (© OpenStreetMap-Mitwirkende, ODbL)'},
            'hinweis': cfg['flow_paths']['notice']}


def _compute(lon, lat, radius_m, main, cfg):
    ctx = _context(lon, lat, radius_m, cfg)
    out = []
    for p in main['pruefpunkte']:
        px, py = PROJECT.transform(p['longitude'], p['latitude'])
        out.append({'nr': p['nr'], 'szenarien': _flow(ctx, px, py, cfg)})
    return _result(cfg, main, radius_m, ctx, out)
