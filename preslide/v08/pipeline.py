"""V0.8 stages: referent plan (inventory exclusion) and referent-time INCA features (config/v08.json).

  python -m preslide.v08.pipeline plan
  python -m preslide.v08.pipeline weather [--limit-days N]
  python -m preslide.v08.pipeline assemble
"""
import argparse
import hashlib
import json
import time

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT
from ..v04 import weather as W
from ..v05.paths import sha
from ..v06.hydro import hydro_features
from . import referents as RF
from .http import cached_json
from .paths import V05_DATASET, V08_DATA, config as load_config, guard

INVENTORY = ROOT / 'data/raw/geosphere_natural_hazards.json'
HYDRO_V06 = ROOT / 'data/v06/hydro.parquet'
INCA_END_MARGIN_H = 6
HYDRO_PARAMETERS = read_json(ROOT / 'config/v06.json')['hydrology']


def positives() -> pd.DataFrame:
    data = pd.read_parquet(V05_DATASET)
    return data[data.label == 1].reset_index(drop=True)


def inventory_index():
    feats = read_json(INVENTORY)['features']
    xy, intervals = [], []
    for f in feats:
        a = f['attributes']
        if not f.get('geometry') or a.get('Prozessgruppe') not in RF.PROCESS_GROUPS:
            continue
        xy.append(PROJECT.transform(f['geometry']['x'], f['geometry']['y']))
        intervals.append(RF.record_interval(a))
    return cKDTree(np.array(xy)), intervals


def stage_plan() -> pd.DataFrame:
    cfg = load_config()
    d = cfg['design']
    inca_end = pd.Timestamp(read_json_cached_end(), tz='UTC') - pd.Timedelta(hours=INCA_END_MARGIN_H)
    tree, intervals = inventory_index()
    undated = sum(iv is None for iv in intervals)
    rows = []
    for p in positives().itertuples():
        times = RF.referent_times(pd.Timestamp(p.t0_utc), d['referent_offsets_days'])
        days = [RF.local_day(t) for t in times]
        near = tree.query_ball_point([p.x, p.y], d['inventory_exclusion']['radius_m'])
        blocked = RF.blocked_referents([intervals[i] for i in near], days)
        for off, t, day, b in zip(d['referent_offsets_days'], times, days, blocked):
            reason = 'inventory_event_near_referent' if b else ('after_last_inca_timestamp' if t >= inca_end else 'kept')
            rows.append({'event_group_id': p.event_group_id, 'offset_days': off, 'referent_t0_utc': t.isoformat(), 'referent_day': day.isoformat(),
                         'latitude': p.latitude, 'longitude': p.longitude, 'x': p.x, 'y': p.y, 'time_quality': p.time_quality,
                         'sample_id': f'{p.event_group_id}|r{off:+d}', 'status': reason})
    plan = pd.DataFrame(rows)
    path = guard(V08_DATA) / 'referent_plan.parquet'
    plan.to_parquet(path, index=False)
    summary = {'by_status': plan.status.value_counts().to_dict(), 'inventory_records_without_usable_date': int(undated),
               'inventory_records_considered': len(intervals), 'sha256': sha(path), 'inca_end_used': inca_end.isoformat()}
    write_json(path.with_suffix('.json'), summary)
    print(json.dumps(summary, indent=1))
    return plan


def read_json_cached_end() -> str:
    meta = guard(V08_DATA / 'cache') / 'inca_metadata.json'
    if not meta.exists():
        meta.write_text(json.dumps(cached_json(W.API + 'inca-v1-1h-1km/metadata', {}, f_param=False)), encoding='utf-8')
    return json.loads(meta.read_text(encoding='utf-8'))['end_time']


def request_points(parameters, start, end, latlon):
    features, timestamps = [], None
    for i in range(0, len(latlon), W.POINTS_PER_REQUEST):
        params = {'parameters': ','.join(parameters), 'start': start.strftime('%Y-%m-%dT%H:%M'), 'end': end.strftime('%Y-%m-%dT%H:%M'),
                  'lat_lon': latlon[i:i + W.POINTS_PER_REQUEST], 'output_format': 'geojson'}
        response = cached_json(W.API + 'inca-v1-1h-1km', params, min_interval_s=W.INTERVAL_S, f_param=False)
        timestamps = timestamps or response['timestamps']
        if response['timestamps'] != timestamps or len(response['features']) != len(latlon[i:i + W.POINTS_PER_REQUEST]):
            raise ValueError('Inconsistent INCA response')
        features += response['features']
    return pd.to_datetime(timestamps, utc=True), features


def referent_features(times, rain, temp, t0, midnight, time_quality, hydro_cfg) -> dict:
    out = W.inca_features(times, rain, temp, t0, midnight, time_quality)
    out.update(hydro_features(times, rain, t0, hydro_cfg))
    return out


def stage_weather(limit_days: int = 0) -> None:
    load_config()
    plan = pd.read_parquet(V08_DATA / 'referent_plan.parquet')
    todo = plan[plan.status == 'kept']
    out_dir = guard(V08_DATA / 'weather')
    days = sorted(todo.referent_day.unique())[:limit_days or None]
    for n, day in enumerate(days, 1):
        samples = todo[todo.referent_day == day].reset_index(drop=True)
        key = hashlib.sha256(','.join(sorted(samples.sample_id)).encode()).hexdigest()[:10]
        path = out_dir / f'inca_{day}_{key}.parquet'
        if path.exists() and path.with_suffix('.json').exists() and sha(path) == read_json(path.with_suffix('.json'))['sha256']:
            continue
        t0s = pd.to_datetime(samples.referent_t0_utc, utc=True)
        start = (t0s.min() - pd.Timedelta(days=60)).floor('h') - pd.Timedelta(hours=2)
        end = t0s.max() - pd.Timedelta(hours=1)
        latlon = [f'{r.latitude:.8f},{r.longitude:.8f}' for r in samples.itertuples()]
        t = time.time()
        times, points = request_points(['RR', 'T2M'], start, end, latlon)
        rows = []
        for r, pt in zip(samples.itertuples(), points):
            pars = pt['properties']['parameters']
            if pars['RR']['unit'] not in ('kg m-2', 'mm') or pars['T2M']['unit'] != 'degree_Celsius':
                raise ValueError('Unexpected INCA units')
            t0 = pd.Timestamp(r.referent_t0_utc)
            midnight = RF.local_midnight_utc(pd.Timestamp(r.referent_day).date())
            try:
                vals = referent_features(times, pars['RR']['data'], pars['T2M']['data'], t0, midnight, r.time_quality, HYDRO_PARAMETERS)
                vals['weather_status'] = 'complete'
            except ValueError as error:
                vals = {'weather_status': str(error)}
            rows.append({'sample_id': r.sample_id, **vals})
        frame = pd.DataFrame(rows)
        frame.to_parquet(path, index=False)
        write_json(path.with_suffix('.json'), {'sha256': sha(path), 'rows': len(frame), 'day': day})
        print(f'[{n}/{len(days)}] {day}: {len(frame)} referents {time.time() - t:.1f}s', flush=True)


def stage_assemble() -> pd.DataFrame:
    cfg = load_config()
    plan = pd.read_parquet(V08_DATA / 'referent_plan.parquet')
    parts = []
    for p in sorted((V08_DATA / 'weather').glob('inca_*.parquet')):
        if sha(p) != read_json(p.with_suffix('.json'))['sha256']:
            raise RuntimeError(f'Checkpoint checksum mismatch: {p}')
        parts.append(pd.read_parquet(p))
    ref = plan.merge(pd.concat(parts, ignore_index=True), on='sample_id', how='left')
    ref['label'] = 0
    ref.loc[ref.status != 'kept', 'weather_status'] = ref.status
    ref['weather_status'] = ref.weather_status.fillna('not_retrieved')
    pos = positives()
    hydro = pd.read_parquet(HYDRO_V06)
    pos = pos.merge(hydro, on='sample_id', how='left')
    pos = pos.assign(offset_days=0, weather_status='complete', label=1)
    feature_cols = [c for c in W.INCA_FEATURES + W.SAME_DAY if c in pos] + cfg['features']['hydro']
    keep = ['event_group_id', 'sample_id', 'label', 'offset_days', 'time_quality', 'weather_status', 'x', 'y'] + feature_cols
    both = pd.concat([pos[keep], ref[ref.weather_status == 'complete'][keep]], ignore_index=True)
    counts = ref.groupby('event_group_id').apply(lambda g: int((g.weather_status == 'complete').sum()), include_groups=False)
    ok = counts[counts >= cfg['design']['min_referents_per_group']].index
    dropped_groups = sorted(set(pos.event_group_id) - set(ok))
    both = both[both.event_group_id.isin(ok)].reset_index(drop=True)
    report = {'groups_total': int(pos.event_group_id.nunique()), 'groups_kept': int(len(ok)), 'groups_dropped_too_few_referents': len(dropped_groups),
              'referents_by_status': ref.weather_status.map(lambda s: s if s in ('complete',) or s.startswith(('inventory', 'after')) else 'weather_failed:' + s.split(':')[0]).value_counts().to_dict(),
              'referents_per_kept_group': both[both.label == 0].groupby('event_group_id').size().value_counts().sort_index().to_dict()}
    path = guard(V08_DATA) / 'dataset.parquet'
    both.to_parquet(path, index=False)
    write_json(path.with_suffix('.json'), {**report, 'sha256': sha(path), 'rows': len(both)})
    print(json.dumps(report, indent=1))
    return both


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['plan', 'weather', 'assemble'])
    ap.add_argument('--limit-days', type=int, default=0)
    a = ap.parse_args()
    {'plan': stage_plan, 'weather': lambda: stage_weather(a.limit_days), 'assemble': stage_assemble}[a.stage]()
