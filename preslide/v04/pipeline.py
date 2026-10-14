"""Resumable, versioned V0.4 run. Every checkpoint carries a SHA-256 sidecar that is verified on reuse.

  python -m preslide.v04.pipeline match   --limit 1|5|20|0(all)
  python -m preslide.v04.pipeline static  --limit ...
  python -m preslide.v04.pipeline context --limit ...
  python -m preslide.v04.pipeline weather --resource inca|spartacus-v2-1d-1km|... --limit ...
  python -m preslide.v04.pipeline assemble
"""
import argparse
import hashlib
import json
import time
import traceback

import numpy as np
import pandas as pd
from shapely import contains_xy

from ..common import read_json, write_json
from ..matching import Exclusions, austria_boundary
from ..pipeline import representative_events
from .paths import CONFIG, V04_DATA, config as load_config, guard
from . import terrain, weather, context


class CacheCorruption(RuntimeError):
    pass


def run_dir():
    return guard(V04_DATA / f"run_{hashlib.sha256(CONFIG.read_bytes()).hexdigest()[:12]}")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(frame, path, meta=None):
    frame.to_parquet(path, index=False)
    write_json(path.with_suffix('.json'), {**(meta or {}), 'sha256': sha(path), 'rows': len(frame)})


def load(path):
    side = path.with_suffix('.json')
    if not path.exists() or not side.exists():
        return None
    meta = read_json(side)
    if sha(path) != meta['sha256']:
        raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
    return pd.read_parquet(path)


def candidates():
    rows = json.loads((V04_DATA / 'audit/candidates.json').read_text(encoding='utf-8'))
    first = representative_events(rows, 20)
    ids = {r['event_id'] for r in first}
    return first + [r for r in rows if r['event_id'] not in ids]


def status_path():
    return run_dir() / 'status.json'


def read_status():
    p = status_path()
    return read_json(p) if p.exists() else {}


def set_status(status, event_id, stage, state, reason=None):
    status.setdefault(event_id, {})[stage] = {'state': state, **({'reason': reason} if reason else {})}


def selected(limit):
    rows = candidates()
    return rows if not limit else rows[:limit]


def stage_match(limit):
    cfg = load_config()['matching']
    status, country, exclusions = read_status(), austria_boundary(), None
    for n, event in enumerate(selected(limit), 1):
        d = guard(run_dir() / 'events' / event['event_id'])
        if load(d / 'samples.parquet') is not None or status.get(event['event_id'], {}).get('match', {}).get('state') == 'excluded':
            continue
        exclusions = exclusions or Exclusions(cfg)
        t = time.time()
        try:
            if not contains_xy(country, event['longitude'], event['latitude']):
                raise ValueError('positive_outside_boundary')
            samples, summary = terrain.match_event(event, cfg, exclusions, country)
            save(samples, d / 'samples.parquet', summary)
            set_status(status, event['event_id'], 'match', 'complete')
            print(f"[{n}] {event['event_id']} matched {summary} {time.time() - t:.1f}s", flush=True)
        except ValueError as error:
            set_status(status, event['event_id'], 'match', 'excluded', str(error))
            print(f"[{n}] {event['event_id']} excluded: {error}", flush=True)
        write_json(status_path(), status)


def matched(limit):
    out = []
    for event in selected(limit):
        s = load(run_dir() / 'events' / event['event_id'] / 'samples.parquet')
        if s is not None:
            out.append((event, s))
    return out


def _static_job(args):
    event, samples, cfg = args
    t = time.time()
    features, meta = terrain.static_features(event, samples, cfg)
    return event, samples, features, meta, time.time() - t


def stage_static(limit, workers=4):
    from concurrent.futures import ProcessPoolExecutor
    cfg = load_config()['matching']
    status = read_status()
    todo = [(e, s, cfg) for e, s in matched(limit) if load(run_dir() / 'events' / e['event_id'] / 'static.parquet') is None]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for n, (event, samples, features, meta, seconds) in enumerate(pool.map(_static_job, todo), 1):
            # Same 30 m grid; GDAL's approximate warp transform differs by a few metres at most (misalignment would not).
            diff = float(np.max(np.abs(features.static_dem_elevation_check - samples.elevation)))
            if not diff <= 5:
                raise RuntimeError(f"Static window misaligned with matching window: {event['event_id']} ({diff:.1f} m)")
            save(features, run_dir() / 'events' / event['event_id'] / 'static.parquet',
                 {**meta, 'max_elevation_difference_to_matching_m': diff, 'seconds': round(seconds, 1)})
            set_status(status, event['event_id'], 'static', 'complete')
            print(f"[{n}/{len(todo)}] {event['event_id']} static {meta} {seconds:.1f}s", flush=True)
            if n % 20 == 0:
                write_json(status_path(), status)
    write_json(status_path(), status)


def stage_context(limit):
    features = load_config()['features']
    for n, (event, samples) in enumerate(matched(limit), 1):
        path = run_dir() / 'events' / event['event_id'] / 'context.parquet'
        if load(path) is not None:
            continue
        lc = context.land_cover(samples, features['land_cover']['classes'])
        geo = context.geology(samples, features['geology']['classes'])
        save(lc.merge(geo, on='sample_id'), path)
        print(f"[{n}] {event['event_id']} context {lc.land_cover_class.tolist()} {geo.geology_class.tolist()}", flush=True)


def stage_weather(limit, resource):
    pairs = matched(limit)
    if not pairs:
        return
    allsamples = pd.concat([s for _, s in pairs], ignore_index=True)
    out = guard(run_dir() / 'weather')
    for day, samples in allsamples.groupby('event_day'):
        key = hashlib.sha256(','.join(sorted(samples.sample_id)).encode()).hexdigest()[:10]
        path = out / f'{resource}_{day}_{key}.parquet'
        if load(path) is not None:
            continue
        t = time.time()
        if resource == 'inca':
            features, series = weather.bundle_inca(samples.reset_index(drop=True))
            history = []
            for sid, s in series.items():
                s = s.assign(date=s.timestamp.dt.tz_convert('Europe/Vienna').dt.strftime('%Y-%m-%d'))
                for date, g in s.groupby('date'):
                    history.append({'sample_id': sid, 'date': date, 'rain_mm': float(g.rain.sum()),
                                    'temperature_c': float(g.temperature.mean()), 'hours': len(g)})
            save(pd.DataFrame(history), out / f'history_{day}_{key}.parquet')
            six = []
            for sid, s in series.items():
                g = s.set_index('timestamp').rain.resample('6h').sum(min_count=6)
                six.append(pd.DataFrame({'sample_id': sid, 'timestamp': g.index, 'rain_6h': g.to_numpy()}))
            save(pd.concat(six, ignore_index=True), out / f'rain6h_{day}_{key}.parquet')
        else:
            features = weather.bundle_daily(samples.reset_index(drop=True), resource)
        save(features, path, {'resource': resource, 'day': day, 'samples': len(samples)})
        print(f'{resource} {day}: {len(samples)} samples {time.time() - t:.1f}s', flush=True)


def latest(prefix, sample_ids):
    """The weather bundle files covering the given samples (newest complete bundle per day)."""
    frames = []
    for p in sorted((run_dir() / 'weather').glob(f'{prefix}_*.parquet')):
        f = load(p)
        if f is not None:
            frames.append(f)
    if not frames:
        return pd.DataFrame({'sample_id': []})
    f = pd.concat(frames, ignore_index=True).drop_duplicates('sample_id', keep='last')
    return f[f.sample_id.isin(sample_ids)]


def stage_assemble(limit=0):
    cfg = load_config()
    status = read_status()
    rows = []
    for event, samples in matched(limit):
        d = run_dir() / 'events' / event['event_id']
        static, ctx = load(d / 'static.parquet'), load(d / 'context.parquet')
        if static is None or ctx is None:
            set_status(status, event['event_id'], 'assemble', 'incomplete', 'static_or_context_missing')
            continue
        rows.append(samples.merge(static.drop(columns='static_dem_elevation_check'), on='sample_id').merge(ctx, on='sample_id'))
    data = pd.concat(rows, ignore_index=True)
    inca = latest('inca', set(data.sample_id))
    data = data.merge(inca, on='sample_id', how='left')
    for resource in weather.DAILY:
        part = latest(resource, set(data.sample_id))
        if len(part):
            data = data.merge(part, on='sample_id', how='left')
    data['weather_status'] = data.weather_status.fillna('not_retrieved')
    complete = data.groupby('event_group_id').weather_status.agg(lambda s: (s == 'complete').all())
    for gid, ok in complete.items():
        if not ok:
            reason = data.loc[(data.event_group_id == gid) & (data.weather_status != 'complete'), 'weather_status'].iloc[0]
            set_status(status, gid, 'weather', 'excluded', reason)
        else:
            set_status(status, gid, 'weather', 'complete')
    data = data[data.event_group_id.map(complete)].reset_index(drop=True)
    data['event_day'] = data.event_day.astype(str)
    validation = validate(data, cfg)
    write_json(run_dir() / 'validation.json', validation)
    write_json(status_path(), status)
    save(data, run_dir() / 'dataset.parquet', {'events': int(data.event_group_id.nunique()), 'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest()})
    print(f'dataset: {data.event_group_id.nunique()} groups, {len(data)} samples', flush=True)
    return data


def validate(data, cfg):
    """Scientific invariants of the assembled V0.4 dataset; raises on any violation."""
    m = cfg['matching']
    if data.sample_id.duplicated().any():
        raise ValueError('Duplicate sample IDs')
    for gid, g in data.groupby('event_group_id'):
        c = g[g.label == 0]
        if len(g) != 6 or g.label.sum() != 1 or g.t0_utc.nunique() != 1 or g.event_day.nunique() != 1:
            raise ValueError(f'Invalid group {gid}')
        last = pd.to_datetime(g.last_used_hour_utc, utc=True) + pd.Timedelta(hours=1)
        if (last >= pd.Timestamp(g.t0_utc.iloc[0])).any():
            raise ValueError(f'Future weather in {gid}')
        for col in ('spartacus-v2-1d-1km_last_day', 'snowgrid_cl-v2-1d-1km_last_day'):
            d = pd.to_datetime(g[col], utc=True).dropna() + pd.Timedelta(hours=30)
            if (d >= pd.Timestamp(g.t0_utc.iloc[0])).any():
                raise ValueError(f'Future daily product in {gid}')
        xy = c[['x', 'y']].to_numpy()
        dist = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(5) * 1e9
        if dist.min() < m['control_separation_m']:
            raise ValueError(f'Overlapping controls {gid}')
        if (c.slope_difference_deg > m['slope_caliper_deg']).any() or (c.elevation_difference_m > m['elevation_caliper_m']).any()                 or (c.aspect_difference_deg > m['aspect_caliper_deg']).any():
            raise ValueError(f'Caliper violation {gid}')
        if not c.inventory_clear.all() or not c.inside_austria.all():
            raise ValueError(f'Control exclusion violated {gid}')
        if not ((c.distance_to_positive_m >= m['control_min_distance_m']) & (c.distance_to_positive_m <= m['control_max_distance_m'])).all():
            raise ValueError(f'Control distance violated {gid}')
    return {'groups': int(data.event_group_id.nunique()), 'samples': int(len(data)), 'checks': 'PASS'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=['match', 'static', 'context', 'weather', 'assemble'])
    p.add_argument('--limit', type=int, default=1)
    p.add_argument('--resource', default='inca')
    a = p.parse_args()
    {'match': lambda: stage_match(a.limit), 'static': lambda: stage_static(a.limit),
     'context': lambda: stage_context(a.limit), 'weather': lambda: stage_weather(a.limit, a.resource),
     'assemble': lambda: stage_assemble(a.limit)}[a.stage]()


if __name__ == '__main__':
    main()
