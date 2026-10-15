"""Resumable V0.9 data run with the unchanged V0.4 matching, terrain, context and weather code (see bind.py).

  python -m preslide.v09.pipeline match   --cohort media|kaernten --limit 1|5|20|0(all)
  python -m preslide.v09.pipeline static  --cohort ... --limit ...
  python -m preslide.v09.pipeline context --cohort ... --limit ...
  python -m preslide.v09.pipeline weather --cohort ... --limit ... --resource inca|spartacus-v2-1d-1km|snowgrid_cl-v2-1d-1km
  python -m preslide.v09.pipeline assemble [--pilot]

Every checkpoint carries a SHA-256 sidecar (preslide.v04.pipeline.save/load). Exclusions are recorded per event and
stage in status.json; nothing is filled in.
"""
import argparse
import hashlib
import json
import time

import numpy as np
import pandas as pd
from shapely import contains_xy

from ..common import read_json, write_json
from ..matching import austria_boundary
from ..pipeline import representative_events
from ..v04.pipeline import save, load, validate
from .audit import decisions
from .bind import bind, V09Exclusions
from .cohort import KTN_RAW, WLV_SLIDES, ktn_process_ok, parse_ktn_day
from ..sources import ROOT
from .paths import CONFIG, V09_DATA, config as load_config, guard, sha

from ..v04 import terrain, weather, context  # rebound to V0.9 paths by bind() in main()


def run_dir():
    return guard(V09_DATA / f'run_{sha(CONFIG)[:12]}')


def eligible():
    """Eligible events after the process audit: media main set (slide_confirmed, ambiguous, not_found) + Kärnten."""
    rows = json.loads((V09_DATA / 'audit/candidates.json').read_text(encoding='utf-8'))
    audit = decisions()
    out = []
    for r in rows:
        if r['cohort'] == 'media':
            category, main, confirmed = audit[r['event_id']]
            if not main:
                continue
            r = {**r, 'audit_category': category, 'slide_confirmed': confirmed}
        else:
            r = {**r, 'audit_category': None, 'slide_confirmed': None}
        out.append(r)
    return out


def ordered(cohort):
    """Registered pilot order: spread order of the first 20 (V0 helper), then event_day order."""
    rows = sorted([r for r in eligible() if r['cohort'] == cohort], key=lambda r: (r['event_day'], r['event_id']))
    if not rows:
        return []
    first = representative_events(rows, 20)
    ids = {r['event_id'] for r in first}
    return first + [r for r in rows if r['event_id'] not in ids]


def selected(cohort, limit):
    rows = ordered(cohort)
    return rows if not limit else rows[:limit]


def read_status():
    p = run_dir() / 'status.json'
    return read_json(p) if p.exists() else {}


def set_status(status, event_id, stage, state, reason=None):
    status.setdefault(event_id, {})[stage] = {'state': state, **({'reason': reason} if reason else {})}


def extra_exclusions(cfg):
    pts = [tuple(f['geometry']['coordinates'][:2]) for f in read_json(WLV_SLIDES)['features']]
    k = cfg['cohorts']['kaernten']
    for f in read_json(KTN_RAW)['features']:
        q = (f['properties'].get('magnitudeOrIntensity') or {}).get('qualitativeValue')
        if f.get('geometry') and ktn_process_ok(q, k['process_tokens']):
            pts.append(tuple(f['geometry']['coordinates'][:2]))
    return pts


def stage_match(cohort, limit):
    cfg = load_config()
    m = cfg['matching']
    status, country, exclusions = read_status(), austria_boundary(), None
    for n, event in enumerate(selected(cohort, limit), 1):
        d = guard(run_dir() / 'events' / event['event_id'])
        if load(d / 'samples.parquet') is not None or status.get(event['event_id'], {}).get('match', {}).get('state') == 'excluded':
            continue
        exclusions = exclusions or V09Exclusions(m, extra_exclusions(cfg))
        t = time.time()
        try:
            if not contains_xy(country, event['longitude'], event['latitude']):
                raise ValueError('positive_outside_boundary')
            samples, summary = terrain.match_event(event, m, exclusions, country)
            samples['cohort'] = cohort
            samples['reported_day'] = event['reported_day']
            save(samples, d / 'samples.parquet', {**summary, 'extra_exclusion_points': exclusions.extra_points})
            set_status(status, event['event_id'], 'match', 'complete')
            print(f"[{n}] {event['event_id']} matched {summary} {time.time() - t:.1f}s", flush=True)
        except ValueError as error:
            set_status(status, event['event_id'], 'match', 'excluded', str(error))
            print(f"[{n}] {event['event_id']} excluded: {error}", flush=True)
        write_json(run_dir() / 'status.json', status)


def matched(cohort, limit):
    out = []
    for event in selected(cohort, limit):
        s = load(run_dir() / 'events' / event['event_id'] / 'samples.parquet')
        if s is not None:
            out.append((event, s))
    return out


def stage_static(cohort, limit):
    cfg = load_config()['matching']
    status = read_status()
    for n, (event, samples) in enumerate(matched(cohort, limit), 1):
        path = run_dir() / 'events' / event['event_id'] / 'static.parquet'
        if load(path) is not None:
            continue
        t = time.time()
        features, meta = terrain.static_features(event, samples, cfg)
        diff = float(np.max(np.abs(features.static_dem_elevation_check - samples.elevation)))
        if not diff <= 5:
            raise RuntimeError(f"Static window misaligned with matching window: {event['event_id']} ({diff:.1f} m)")
        save(features, path, {**meta, 'max_elevation_difference_to_matching_m': diff, 'seconds': round(time.time() - t, 1)})
        set_status(status, event['event_id'], 'static', 'complete')
        print(f"[{n}] {event['event_id']} static {meta} {time.time() - t:.1f}s", flush=True)
    write_json(run_dir() / 'status.json', status)


def stage_context(cohort, limit):
    load_config()
    classes = read_json(ROOT / 'config/v04.json')['features']      # V0.4 class definitions (content, not bytes)
    for n, (event, samples) in enumerate(matched(cohort, limit), 1):
        path = run_dir() / 'events' / event['event_id'] / 'context.parquet'
        if load(path) is not None:
            continue
        lc = context.land_cover(samples, classes['land_cover']['classes'])
        geo = context.geology(samples, classes['geology']['classes'])
        save(lc.merge(geo, on='sample_id'), path)
        print(f"[{n}] {event['event_id']} context {lc.land_cover_class.tolist()} {geo.geology_class.tolist()}", flush=True)


def stage_weather(cohort, limit, resource):
    pairs = matched(cohort, limit)
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
            features, _ = weather.bundle_inca(samples.reset_index(drop=True))
        else:
            features = weather.bundle_daily(samples.reset_index(drop=True), resource)
        save(features, path, {'resource': resource, 'day': day, 'samples': len(samples)})
        print(f'{resource} {day}: {len(samples)} samples {time.time() - t:.1f}s', flush=True)


def latest(prefix, sample_ids):
    frames = [f for f in (load(p) for p in sorted((run_dir() / 'weather').glob(f'{prefix}_*.parquet'))) if f is not None]
    if not frames:
        return pd.DataFrame({'sample_id': []})
    f = pd.concat(frames, ignore_index=True).drop_duplicates('sample_id', keep='last')
    return f[f.sample_id.isin(sample_ids)]


def stage_assemble(pilot=False):
    cfg = load_config()
    status = read_status()
    rows = []
    for cohort in ('media', 'kaernten'):
        for event, samples in matched(cohort, 0):
            d = run_dir() / 'events' / event['event_id']
            static, ctx = load(d / 'static.parquet'), load(d / 'context.parquet')
            if static is None or ctx is None:
                set_status(status, event['event_id'], 'assemble', 'incomplete', 'static_or_context_missing')
                continue
            rows.append(samples.merge(static.drop(columns='static_dem_elevation_check'), on='sample_id').merge(ctx, on='sample_id')
                        .assign(audit_category=event['audit_category'], slide_confirmed=event['slide_confirmed']))
    data = pd.concat(rows, ignore_index=True)
    data = data.merge(latest('inca', set(data.sample_id)), on='sample_id', how='left')
    for resource in ('spartacus-v2-1d-1km', 'snowgrid_cl-v2-1d-1km'):
        part = latest(resource, set(data.sample_id))
        if len(part):
            data = data.merge(part, on='sample_id', how='left')
    data['weather_status'] = data.weather_status.fillna('not_retrieved')
    complete = data.groupby('event_group_id').weather_status.agg(lambda s: (s == 'complete').all())
    for gid, ok in complete.items():
        if ok:
            set_status(status, gid, 'weather', 'complete')
        else:
            reason = data.loc[(data.event_group_id == gid) & (data.weather_status != 'complete'), 'weather_status'].iloc[0]
            set_status(status, gid, 'weather', 'excluded', reason)
    data = data[data.event_group_id.map(complete)].reset_index(drop=True)
    data['event_day'] = data.event_day.astype(str)
    validation = {**validate(data, cfg), **validate_v09(data, cfg)}
    name = 'dataset_pilot.parquet' if pilot else 'dataset.parquet'
    write_json(run_dir() / ('validation_pilot.json' if pilot else 'validation.json'), validation)
    write_json(run_dir() / 'status.json', status)
    save(data, run_dir() / name, {'events': int(data.event_group_id.nunique()), 'config_sha256': sha(CONFIG),
                                  'by_cohort': data[data.label == 1].cohort.value_counts().to_dict()})
    print(f'{name}: {data.event_group_id.nunique()} groups, {len(data)} samples, '
          f'{data[data.label == 1].cohort.value_counts().to_dict()}', flush=True)
    return data


def validate_v09(data, cfg):
    """V0.9 invariants on top of the V0.4 validation; raises on any violation."""
    shift = pd.Timedelta(days=cfg['cohorts']['kaernten']['t0_shift_days'])
    for gid, g in data.groupby('event_group_id'):
        if g.cohort.nunique() != 1 or g.reported_day.nunique() != 1:
            raise ValueError(f'Mixed cohort or reported day in {gid}')
        t0 = pd.Timestamp(g.t0_utc.iloc[0])
        start = pd.Timestamp(g.reported_day.iloc[0], tz='Europe/Vienna').tz_convert('UTC')
        if g.cohort.iloc[0] == 'kaernten':
            if t0 != start - shift or (g.time_quality != 'day').any():
                raise ValueError(f'Kaernten t0 is not local midnight {shift.days} days before the reported day: {gid}')
        elif not start <= t0 < start + pd.Timedelta(days=1):
            raise ValueError(f'Media t0 outside its reported day: {gid}')
    return {'v09_checks': 'PASS', 'by_cohort': data[data.label == 1].cohort.value_counts().to_dict()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=['match', 'static', 'context', 'weather', 'assemble'])
    p.add_argument('--cohort', choices=['media', 'kaernten'], default='media')
    p.add_argument('--limit', type=int, default=1)
    p.add_argument('--resource', default='inca')
    p.add_argument('--pilot', action='store_true')
    a = p.parse_args()
    bind()
    {'match': lambda: stage_match(a.cohort, a.limit), 'static': lambda: stage_static(a.cohort, a.limit),
     'context': lambda: stage_context(a.cohort, a.limit), 'weather': lambda: stage_weather(a.cohort, a.limit, a.resource),
     'assemble': lambda: stage_assemble(a.pilot)}[a.stage]()


if __name__ == '__main__':
    main()
