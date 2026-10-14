"""Cached STAC search against Earth Search (AWS, public, no credentials). Items are normalised to plain dicts."""
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

from ..common import write_json
from .paths import SAT_DATA, guard, config

ASSET_NAMES = ('blue', 'green', 'red', 'nir', 'swir16', 'swir22', 'scl')
_last_call = [0.0]


def _cached_get(url, params, min_interval_s=0.2):
    target = url + '?' + urlencode(sorted(params.items()), doseq=True)
    key = hashlib.sha256(target.encode()).hexdigest()
    directory = guard(SAT_DATA / 'cache/stac')
    path = directory / f'{key}.json'
    if path.exists():
        meta = json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
        if meta['url'] != target or meta['sha256'] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise RuntimeError(f'STAC cache integrity failure: {path}')
        return json.loads(path.read_text(encoding='utf-8'))
    wait = _last_call[0] + min_interval_s - time.time()
    if wait > 0:
        time.sleep(wait)
    curl = shutil.which('curl.exe') or shutil.which('curl')
    code, body = b'', b''
    for attempt in range(4):
        _last_call[0] = time.time()
        result = subprocess.run([curl, '--silent', '--show-error', '--location', '--max-time', '120',
                                 '-w', '\n%{http_code}', target], capture_output=True, timeout=180)
        body, _, code = result.stdout.rpartition(b'\n')
        if result.returncode == 0 and code == b'200':
            break
        if code.startswith(b'5') and attempt == 1:
            return None            # persistent server error: caller splits the range
        time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f'STAC request failed: {target[:200]} {code!r} {body[:200]!r}')
    data = json.loads(body)
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(body)
    tmp.replace(path)
    write_json(path.with_suffix('.meta.json'), {'url': target, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                                                'sha256': hashlib.sha256(body).hexdigest()})
    return data


def _normalise(feature):
    p = feature['properties']
    epsg = p.get('proj:epsg')
    if epsg is None and str(p.get('proj:code', '')).startswith('EPSG:'):
        epsg = int(p['proj:code'].split(':')[1])
    assets = {}
    for name in ASSET_NAMES:
        a = feature['assets'].get(name)
        if a is None:
            return None
        band = (a.get('raster:bands') or [{}])[0]
        assets[name] = {'href': a['href'], 'scale': band.get('scale'), 'offset': band.get('offset'),
                        'nodata': band.get('nodata', 0), 'resolution_m': band.get('spatial_resolution')}
    return {'id': feature['id'], 'collection': feature['collection'], 'datetime': p['datetime'],
            'date': p['datetime'][:10], 'epsg': int(epsg), 'grid_code': p.get('grid:code'),
            'platform': p.get('platform'), 'processing_baseline': p.get('s2:processing_baseline'),
            'scene_cloud_cover': p.get('eo:cloud_cover'), 'scene_nodata_pct': p.get('s2:nodata_pixel_percentage'),
            'scene_snow_pct': p.get('s2:snow_ice_percentage'), 'bbox': feature.get('bbox'),
            'boa_offset_applied': p.get('earthsearch:boa_offset_applied'), 'assets': assets}


def search(lon, lat, start, end, collections=None):
    """All Sentinel-2 L2A items covering the point in [start, end] (dates, inclusive), one per acquisition and tile."""
    cfg = config()['stac']
    collections = collections or cfg['collections']
    h = cfg['point_bbox_half_deg']
    items = []
    for collection in collections:
        items += _search_range(cfg['endpoint'], collection, [lon - h, lat - h, lon + h, lat + h], start, end, cfg['page_limit'])
    # One item per acquisition: prefer the first-listed collection, then the tile in which the point is most interior
    # (neighbouring MGRS tiles overlap; the interior tile has the smaller chance of a nodata swath edge in the patch).
    rank = {c: i for i, c in enumerate(collections)}

    def interior(it):
        b = it['bbox'] or [lon, lat, lon, lat]
        return min(lon - b[0], b[2] - lon, lat - b[1], b[3] - lat)

    best = {}
    for it in items:
        k = it['datetime'][:16]
        if k not in best or (rank[it['collection']], -interior(it)) < (rank[best[k]['collection']], -interior(best[k])):
            best[k] = it
    return sorted(best.values(), key=lambda i: i['datetime'])


def _search_range(endpoint, collection, bbox, start, end, limit):
    params = {'collections': collection, 'bbox': ','.join(f'{v:.5f}' for v in bbox),
              'datetime': f'{start}T00:00:00Z/{end}T23:59:59Z', 'limit': limit}
    data = _cached_get(endpoint, params)
    matched = data.get('numberMatched', len(data['features'])) if data else 1
    returned = data.get('numberReturned', len(data['features'])) if data else 0
    if matched > returned:
        d0, d1 = datetime.fromisoformat(start), datetime.fromisoformat(end)
        if (d1 - d0).days < 2:
            raise RuntimeError(f'STAC page overflow on a 1-day range: {params}')
        mid = d0 + (d1 - d0) / 2
        return (_search_range(endpoint, collection, bbox, start, mid.date().isoformat(), limit) +
                _search_range(endpoint, collection, bbox, (mid + timedelta(days=1)).date().isoformat(), end, limit))
    return [n for n in (_normalise(f) for f in data['features']) if n is not None]


def covers(item, lon, lat):
    b = item.get('bbox')
    return bool(b) and b[0] <= lon <= b[2] and b[1] <= lat <= b[3]


def sibling_item(item, lon, lat):
    """The item of the same acquisition (same minute, same collection) whose tile covers the point, or None."""
    if covers(item, lon, lat):
        return item
    for cand in search(lon, lat, item['date'], item['date'], [item['collection']]):
        if cand['datetime'][:16] == item['datetime'][:16] and covers(cand, lon, lat):
            return cand
    return None
