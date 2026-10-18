"""External inputs with immutable caches: CORINE polygons, GeoSphere geology and OpenStreetMap (Overpass).

Earlier caches (data/raw/http, data/v04/cache/http, data/hangmap_v01/cache/http) are read only; new responses
go to data/wirkungskette_v01/cache/http with url + SHA-256 sidecar (same format as preslide.v04.http).
"""
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np
import pandas as pd
from shapely import STRtree, points as shp_points
from shapely.geometry import shape

from ..v04 import context as C
from ..v04.http import full_url, _read
from .paths import DATA, READ_ONLY_HTTP, guard


def _store(path, target, body):
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(body)
    tmp.replace(path)
    path.with_suffix('.meta.json').write_text(json.dumps({'url': target, 'sha256': hashlib.sha256(body).hexdigest(),
                                                                          'retrieved_at': datetime.now(timezone.utc).isoformat()}),
                                              encoding='utf-8')


def _curl(args, timeout):
    curl = shutil.which('curl.exe') or shutil.which('curl')
    for attempt in range(4):
        r = subprocess.run([curl, '--silent', '--show-error', '--location', '-w', '\n%{http_code}', *args],
                           capture_output=True, timeout=timeout)
        body, _, code = r.stdout.rpartition(b'\n')
        if r.returncode == 0 and code == b'200':
            return body
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'Request failed: {args[-1][:160]}')


def cached_json(url, params, f_param=True):
    target = full_url(url, {**params, 'f': 'json'} if f_param else params)
    key = hashlib.sha256(target.encode()).hexdigest()
    for directory in READ_ONLY_HTTP + (DATA / 'cache/http',):
        if (directory / f'{key}.json').exists():
            return _read(directory / f'{key}.json', target)
    body = _curl(['--max-time', '180', target], 240)
    data = json.loads(body)
    if isinstance(data, dict) and 'error' in data:
        raise RuntimeError(f"Source error: {data['error']}")
    _store(guard(DATA / 'cache/http') / f'{key}.json', target, body)
    return data


# ---------- land cover ----------

def land_cover_polygons(bounds_lonlat, vintage, tiles):
    """All CORINE polygons intersecting the envelope, requested as tiles x tiles sub-envelopes, deduplicated by OBJECTID."""
    url, field = C.CLC[vintage]
    w, s, e, n = bounds_lonlat
    xs, ys = np.linspace(w, e, tiles + 1), np.linspace(s, n, tiles + 1)
    seen, geoms, codes = set(), [], []
    for i in range(tiles):
        for j in range(tiles):
            env = {'xmin': round(float(xs[i]), 6), 'ymin': round(float(ys[j]), 6), 'xmax': round(float(xs[i + 1]), 6),
                   'ymax': round(float(ys[j + 1]), 6), 'spatialReference': {'wkid': 4326}}
            r = cached_json(url, {'geometry': json.dumps(env), 'geometryType': 'esriGeometryEnvelope', 'inSR': '4326',
                                  'outSR': '4326', 'spatialRel': 'esriSpatialRelIntersects', 'outFields': f'OBJECTID,{field}',
                                  'returnGeometry': 'true'})
            if r.get('exceededTransferLimit'):
                raise RuntimeError('CORINE response truncated; increase land-cover tiles')
            for f in r['features']:
                oid = f['attributes']['OBJECTID']
                if oid not in seen:
                    seen.add(oid)
                    geoms.append(C._rings(f['geometry']['rings']))
                    codes.append(f['attributes'][field])
    return geoms, codes


def land_cover_at(lon, lat, geoms, codes, classes):
    """CORINE class per point; no or several distinct codes covering a point = missing (V0.4 rule)."""
    tree = STRtree(geoms)
    out = []
    for p in shp_points(np.asarray(lon), np.asarray(lat)):
        hit = {codes[i] for i in tree.query(p) if geoms[i].covers(p)}
        out.append(next(iter(hit)) if len(hit) == 1 else None)
    return pd.DataFrame({'clc_code': out, 'land_cover_class': [C.clc_class(c, classes) if c is not None else None for c in out]})


# ---------- geology ----------

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


def geology_at(lon, lat, classes):
    layer, out = geology_layer(), []
    for p in shp_points(np.asarray(lon), np.asarray(lat)):
        names = {layer['lith'][i] for i in layer['tree'].query(p) if layer['geoms'][i].covers(p)}
        if len(names) != 1:
            out.append(None)
            continue
        lith = next(iter(names))
        out.append(next((k for k, v in classes.items() if isinstance(v, list) and lith in v), 'geo_crystalline_other'))
    return pd.DataFrame({'geology_class': out})


# ---------- OpenStreetMap ----------

OVERPASS = 'https://overpass-api.de/api/interpreter'


def overpass(query_body, bounds_lonlat, user_agent):
    """One Overpass request for the window bbox (south, west, north, east); raw response cached immutably."""
    w, s, e, n = bounds_lonlat
    bbox = f'{s:.5f},{w:.5f},{n:.5f},{e:.5f}'
    query = f'[out:json][timeout:180][bbox:{bbox}];({query_body});out geom;'
    target = full_url(OVERPASS, {'data': query})
    key = hashlib.sha256(target.encode()).hexdigest()
    path = DATA / 'cache/http' / f'{key}.json'
    if path.exists():
        return _read(path, target), json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
    body = _curl(['--max-time', '300', '-A', user_agent, '--data-urlencode', f'data={query}', OVERPASS], 360)
    data = json.loads(body)
    if 'elements' not in data:
        raise RuntimeError('Overpass response without elements')
    _store(guard(DATA / 'cache/http') / f'{key}.json', target, body)
    return data, json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
