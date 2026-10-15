"""V0.6 stage: hydrological features for every sample of the frozen V0.5 cohort from cached hourly INCA responses.

  python -m preslide.v06.pipeline hydro [--limit N]

No network access: hourly series are located in the immutable V0.4/V0.5 response caches by sample coordinate;
a sample without a covering cached response is an error (never a download, never an imputed value).
"""
import argparse
import json
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from ..common import write_json
from ..sources import ROOT
from ..v05.paths import V05_DATA, sha
from ..v05.pipeline import CacheCorruption
from .hydro import hydro_features
from .paths import V06_DATA, V05_DATASET, config as load_config, guard

CACHES = (ROOT / 'data/raw/http', ROOT / 'data/v04/cache/http', V05_DATA / 'cache/http')


def inca_index() -> dict[str, list[tuple[str, int, pd.Timestamp, pd.Timestamp]]]:
    """'lat,lon' -> [(response file, point index, request start, request end)] over all cached INCA hourly responses."""
    index: dict[str, list] = {}
    for directory in CACHES:
        for meta in directory.glob('*.meta.json'):
            url = json.loads(meta.read_text(encoding='utf-8'))['url']
            if 'inca-v1-1h-1km' not in url:
                continue
            q = parse_qs(urlparse(url).query)
            if q.get('parameters') != ['RR,T2M']:
                continue
            body = meta.with_name(meta.name.replace('.meta.json', '.json'))
            start, end = (pd.Timestamp(q[k][0], tz='UTC') for k in ('start', 'end'))
            for i, ll in enumerate(q['lat_lon']):
                index.setdefault(ll, []).append((str(body), i, start, end))
    return index


def _series(path: str, point: int, cache: dict):
    if path not in cache:
        if len(cache) > 3:
            cache.clear()
        cache[path] = json.loads(open(path, encoding='utf-8').read())
    response = cache[path]
    rr = response['features'][point]['properties']['parameters']['RR']
    if rr['unit'] not in ('kg m-2', 'mm'):
        raise ValueError('Unexpected INCA units')
    return pd.to_datetime(response['timestamps'], utc=True), np.asarray(rr['data'], float)


def stage_hydro(limit: int = 0) -> pd.DataFrame:
    cfg = load_config()
    data = pd.read_parquet(V05_DATASET)
    if sha(V05_DATASET) != cfg['inputs']['dataset_sha256']:
        raise CacheCorruption('V0.5 dataset changed')
    if limit:
        keep = sorted(data.event_group_id.unique())[:limit]
        data = data[data.event_group_id.isin(keep)]
    index, cache, rows = inca_index(), {}, []
    for r in data.itertuples():
        key = f'{r.latitude:.8f},{r.longitude:.8f}'
        t0 = pd.Timestamp(r.t0_utc)
        need_start, need_end = (t0 - pd.Timedelta(days=60)).floor('h') - pd.Timedelta(hours=2), t0 - pd.Timedelta(hours=1)
        candidates = [c for c in index.get(key, []) if c[2] <= need_start and c[3] >= need_end]
        if not candidates:
            raise RuntimeError(f'No cached hourly INCA response covers {r.sample_id} ({key}); V0.6 does not download')
        times, rain = _series(candidates[0][0], candidates[0][1], cache)
        melt = {n: getattr(r, f'swe_melt_{n}', np.nan) for n in ('3d', '7d', '14d')}
        sums = {n: getattr(r, f'rain_sum_{n}', np.nan) for n in ('3d', '7d', '14d')}
        rows.append({'sample_id': r.sample_id, **hydro_features(times, rain, t0, cfg['hydrology'], melt, sums)})
    out = pd.DataFrame(rows)
    merged = out.merge(data[['sample_id', 'rain_sum_1d', 'rain_sum_3d', 'rain_max_hour_1d']], on='sample_id')
    if ((merged.max_sum_24h < merged.rain_sum_1d - 1e-6) | (merged.max_sum_72h < merged.rain_sum_3d - 1e-6) | (merged.max_sum_3h < merged.rain_max_hour_1d - 1e-6)).any():
        raise RuntimeError('Hydrological maxima are inconsistent with the V0.4 window sums (series mismatch)')
    missing = [c for c in cfg['hydrology']['features'] if c not in out]
    if missing:
        raise RuntimeError(f'Hydrological features missing from the output: {missing}')
    name = 'hydro.parquet' if not limit else f'hydro_pilot_{limit}.parquet'
    path = guard(V06_DATA) / name
    out.to_parquet(path, index=False)
    write_json(path.with_suffix('.json'), {'sha256': sha(path), 'rows': len(out), 'config_sha256': sha(ROOT / 'config/v06.json'),
                                           'dataset_sha256': cfg['inputs']['dataset_sha256']})
    print(f'{name}: {len(out)} samples, groups {data.event_group_id.nunique()}', flush=True)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['hydro'])
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    stage_hydro(a.limit)
