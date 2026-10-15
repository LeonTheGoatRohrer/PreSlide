"""Resumable V0.5 run (config/v05.json). Every checkpoint carries a SHA-256 sidecar that is verified on reuse.

  python -m preslide.v05.pipeline pools                      # pool audit of all 423 events (no selection)
  python -m preslide.v05.pipeline select  --limit 1|5|20|0   # frozen unmatched controls
  python -m preslide.v05.pipeline static  --limit ...        # terrain features (V0.4 code, same window)
  python -m preslide.v05.pipeline context --limit ...        # CORINE + geology
  python -m preslide.v05.pipeline weather --resource inca|spartacus-v2-1d-1km|snowgrid_cl-v2-1d-1km --limit ...
  python -m preslide.v05.pipeline assemble [--limit ...]
"""
import argparse
import hashlib
import json
import time

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..matching import Exclusions, austria_boundary
from ..sources import ROOT
from . import terrain as T
from ..v04 import weather as W
from .paths import CONFIG, V05_DATA, V04_DATASET, config as load_config, guard, sha
from . import controls as K
from . import environment as E

V04_CONFIG = read_json(ROOT / 'config/v04.json')
BASE_COLUMNS = ['event_group_id', 'event_day', 't0_utc', 'time_quality', 'state', 'source_position_upper_m', 'process_type']
SAMPLE_COLUMNS = BASE_COLUMNS + ['sample_id', 'label', 'sample_type', 'pool_id', 'draw_order', 'longitude', 'latitude', 'x', 'y',
                                 'elevation', 'slope', 'aspect', 'aspect_sin', 'aspect_cos', 'distance_to_positive_m',
                                 'inventory_clear', 'inside_austria']


class CacheCorruption(RuntimeError):
    pass


def run_dir():
    return guard(V05_DATA / f"run_{sha(CONFIG)[:12]}")


def save(frame, path, meta=None):
    frame.to_parquet(path, index=False)
    write_json(path.with_suffix('.json'), {**(meta or {}), 'sha256': sha(path), 'rows': len(frame)})


def load(path):
    side = path.with_suffix('.json')
    if not path.exists() or not side.exists():
        return None
    if sha(path) != read_json(side)['sha256']:
        raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
    return pd.read_parquet(path)


def v04_dataset():
    return pd.read_parquet(V04_DATASET)


def positives():
    """The 423 V0.4 positives in the registered deterministic pilot order."""
    d = v04_dataset()
    pos = d[d.label == 1].set_index('event_group_id')
    return [pos.loc[e] for e in K.pilot_order(pos.index.tolist())]


def selected(limit):
    rows = positives()
    return rows if not limit else rows[:limit]


def read_status():
    p = run_dir() / 'status.json'
    return read_json(p) if p.exists() else {}


def write_status(status):
    write_json(run_dir() / 'status.json', status)


def set_status(status, event_id, stage, state, reason=None):
    status.setdefault(event_id, {})[stage] = {'state': state, **({'reason': reason} if reason else {})}


# ---------- pools ----------

def stage_pools():
    """Pool manifest and integrity audit; refuses to continue on any failure."""
    m = V04_CONFIG['matching']
    exclusions, country = Exclusions(m), austria_boundary()
    rows = []
    for n, p in enumerate(positives(), 1):
        rows.append(K.audit_pool(p.name, p.x, p.y, m, exclusions, country))
        if n % 50 == 0:
            print(f'pool audit {n}', flush=True)
    bad = [r for r in rows if r['problems'] or any(r['flag_mismatch'].values())]
    out = guard(V05_DATA / 'pool_audit')
    manifest = {r['event_id']: r['sha256'] for r in rows}
    write_json(out / 'pool_manifest.json', manifest)
    summary = {'pools': len(rows), 'failed': len(bad), 'failures': bad[:20],
               'max_lonlat_xy_error_m': max(r['max_lonlat_xy_error_m'] for r in rows),
               'flag_mismatch_total': {k: sum(r['flag_mismatch'][k] for r in rows) for k in ('inventory_clear', 'inside_austria')},
               'inventory_snapshot_sha256': sha(ROOT / 'data/raw/geosphere_natural_hazards.json'),
               'manifest_sha256': sha(out / 'pool_manifest.json'),
               'stored_flags_reused': not bad}
    write_json(out / 'pool_audit.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'failures'}, indent=1))
    if bad:
        raise RuntimeError(f'{len(bad)} pools failed the audit; stored flags may not be reused')
    return summary


def pool_manifest():
    path = V05_DATA / 'pool_audit/pool_manifest.json'
    if not path.exists() or not read_json(V05_DATA / 'pool_audit/pool_audit.json')['stored_flags_reused']:
        raise RuntimeError('Run the pool audit first (it must pass)')
    return read_json(path)


# ---------- selection ----------

def stage_select(limit):
    c = load_config()['controls']
    manifest, status = pool_manifest(), read_status()
    for n, p in enumerate(selected(limit), 1):
        eid = p.name
        d = guard(run_dir() / 'events' / eid)
        if load(d / 'samples.parquet') is not None or status.get(eid, {}).get('select', {}).get('state') == 'excluded':
            continue
        pool, digest_ = K.load_pool(eid)
        if digest_ != manifest[eid]:
            raise CacheCorruption(f'Pool changed since the audit: {eid}')
        try:
            rows, record = K.select_controls(eid, pool, c)
        except ValueError as error:
            set_status(status, eid, 'select', 'excluded', str(error))
            print(f'[{n}] {eid} excluded: {error}', flush=True)
            write_status(status)
            continue
        common = {k: p[k] for k in BASE_COLUMNS[1:]}
        positive = {'event_group_id': eid, **common, 'sample_id': eid + '_positive', 'label': 1, 'sample_type': 'POSITIVE',
                    'pool_id': -1, 'draw_order': 0, **{k: p[k] for k in ('longitude', 'latitude', 'x', 'y', 'elevation', 'slope', 'aspect')},
                    'distance_to_positive_m': 0.0, 'inventory_clear': True, 'inside_austria': True}
        ctrl = rows.assign(event_group_id=eid, **common, label=0, sample_type='PSEUDO_NEGATIVE',
                           sample_id=[f'{eid}_v05c_{i:02d}' for i in rows.draw_order])
        samples = pd.concat([pd.DataFrame([positive]), ctrl], ignore_index=True)
        samples['aspect_sin'] = np.sin(np.deg2rad(samples.aspect))
        samples['aspect_cos'] = np.cos(np.deg2rad(samples.aspect))
        samples = samples[SAMPLE_COLUMNS]
        save(samples, d / 'samples.parquet', {**record, 'pool_sha256': digest_})
        set_status(status, eid, 'select', 'complete')
        write_status(status)
        print(f"[{n}] {eid} selected 10 of {record['eligible']} eligible (walked {record['walked']})", flush=True)


def frozen_samples(limit):
    out = []
    for p in selected(limit):
        s = load(run_dir() / 'events' / p.name / 'samples.parquet')
        if s is not None:
            out.append((p, s))
    return out


# ---------- static terrain ----------

def _static_job(args):
    p, samples = args
    event = {'event_id': p.name, 'longitude': float(p.longitude), 'latitude': float(p.latitude), 'event_day': p.event_day}
    t = time.time()
    features, meta = T.static_features(event, samples, V04_CONFIG['matching'])
    return p.name, samples, features, meta, time.time() - t


def stage_static(limit, workers=4):
    from concurrent.futures import ProcessPoolExecutor
    status = read_status()
    todo = [(p, s) for p, s in frozen_samples(limit) if load(run_dir() / 'events' / p.name / 'static.parquet') is None
            and status.get(p.name, {}).get('static', {}).get('state') != 'excluded']
    tiles_before = sorted(x.name for x in (ROOT / 'data/v04/cache/terrain_tiles').glob('*'))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for n, (eid, samples, features, meta, seconds) in enumerate(pool.map(_static_job, todo), 1):
            diff = float(np.max(np.abs(features.static_dem_elevation_check - samples.elevation)))
            if not diff <= 5:
                # Same check as V0.4; a failure is a technical exclusion of the whole group (no replacement control).
                set_status(status, eid, 'static', 'excluded', f'static_matching_elevation_check:{diff:.1f}m')
                write_status(status)
                print(f'[{n}/{len(todo)}] {eid} excluded: elevation check {diff:.1f} m > 5 m', flush=True)
                continue
            save(features, run_dir() / 'events' / eid / 'static.parquet',
                 {**meta, 'max_elevation_difference_to_matching_m': diff, 'seconds': round(seconds, 1)})
            print(f'[{n}/{len(todo)}] {eid} static {meta} {seconds:.1f}s', flush=True)
    if sorted(x.name for x in (ROOT / 'data/v04/cache/terrain_tiles').glob('*')) != tiles_before:
        raise RuntimeError('A V0.4 terrain tile was written; V0.4 caches must stay read only')


# ---------- land cover and geology ----------

def stage_context(limit):
    classes = V04_CONFIG['features']
    for n, (p, samples) in enumerate(frozen_samples(limit), 1):
        path = run_dir() / 'events' / p.name / 'context.parquet'
        if load(path) is not None:
            continue
        lc = E.land_cover(samples, classes['land_cover']['classes'])
        geo = E.geology(samples, classes['geology']['classes'])
        save(lc.merge(geo, on='sample_id'), path)
        print(f'[{n}] {p.name} context {lc.land_cover_class.value_counts(dropna=False).to_dict()}', flush=True)


# ---------- weather ----------

def bundles(prefix):
    return [(path, load(path)) for path in sorted((run_dir() / 'weather').glob(f'{prefix}_*.parquet'))]


def stage_weather(limit, resource):
    pairs = frozen_samples(limit)
    if not pairs:
        return
    allsamples = pd.concat([s for _, s in pairs], ignore_index=True)
    out = guard(run_dir() / 'weather')
    done = set()
    for _, f in bundles(resource):
        if f is not None:
            done |= set(f.sample_id)
    for day, samples in allsamples.groupby('event_day'):
        samples = samples[~samples.sample_id.isin(done)].reset_index(drop=True)
        if samples.empty:
            continue
        key = hashlib.sha256(','.join(sorted(samples.sample_id)).encode()).hexdigest()[:10]
        t = time.time()
        if resource == 'inca':
            features, series = E.bundle_inca(samples)
            history = []
            for sid, s in series.items():
                s = s.assign(date=s.timestamp.dt.tz_convert('Europe/Vienna').dt.strftime('%Y-%m-%d'))
                for date, g in s.groupby('date'):
                    history.append({'sample_id': sid, 'date': date, 'rain_mm': float(g.rain.sum()),
                                    'temperature_c': float(g.temperature.mean()), 'hours': len(g)})
            save(pd.DataFrame(history), out / f'history_{day}_{key}.parquet')
        else:
            features = E.bundle_daily(samples, resource)
        save(features, out / f'{resource}_{day}_{key}.parquet', {'resource': resource, 'day': day, 'samples': len(samples)})
        print(f'{resource} {day}: {len(samples)} samples {time.time() - t:.1f}s', flush=True)


def latest(prefix, sample_ids):
    frames = [f for _, f in bundles(prefix) if f is not None]
    if not frames:
        return pd.DataFrame({'sample_id': []})
    f = pd.concat(frames, ignore_index=True)
    if f.sample_id.duplicated().any():
        raise RuntimeError(f'Duplicate samples across {prefix} bundles')
    return f[f.sample_id.isin(sample_ids)]


# ---------- assemble ----------

def stage_assemble(limit=0):
    cfg = load_config()
    status = read_status()
    rows = []
    for p, samples in frozen_samples(limit):
        d = run_dir() / 'events' / p.name
        static, ctx = load(d / 'static.parquet'), load(d / 'context.parquet')
        if status.get(p.name, {}).get('static', {}).get('state') == 'excluded':
            continue
        if static is None or ctx is None:
            set_status(status, p.name, 'assemble', 'incomplete', 'static_or_context_missing')
            continue
        set_status(status, p.name, 'assemble', 'complete')
        rows.append(samples.merge(static.drop(columns='static_dem_elevation_check'), on='sample_id').merge(ctx, on='sample_id'))
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
    validation = validate(data, cfg)
    validation['positives_vs_v04'] = positive_consistency(data)
    write_json(run_dir() / ('validation.json' if not limit else 'validation_pilot.json'), validation)
    write_status(status)
    name = 'dataset.parquet' if not limit else f'dataset_pilot_{limit}.parquet'
    save(data, run_dir() / name, {'events': int(data.event_group_id.nunique()), 'config_sha256': sha(CONFIG)})
    print(f'dataset: {data.event_group_id.nunique()} groups, {len(data)} samples', flush=True)
    print(json.dumps(validation['positives_vs_v04'], indent=1)[:1500])
    return data


def validate(data, cfg):
    """Scientific invariants of the assembled V0.5 dataset; raises on any violation."""
    c, k = cfg['controls'], cfg['controls']['per_event']
    if data.sample_id.duplicated().any():
        raise ValueError('Duplicate sample IDs')
    for gid, g in data.groupby('event_group_id'):
        ctrl = g[g.label == 0]
        if len(g) != k + 1 or g.label.sum() != 1 or g.t0_utc.nunique() != 1 or g.event_day.nunique() != 1 or g.time_quality.nunique() != 1:
            raise ValueError(f'Invalid group {gid}')
        if ctrl.pool_id.duplicated().any() or sorted(ctrl.draw_order) != list(range(1, k + 1)):
            raise ValueError(f'Duplicate or missing controls {gid}')
        t0 = pd.Timestamp(g.t0_utc.iloc[0])
        if ((pd.to_datetime(g.last_used_hour_utc, utc=True) + pd.Timedelta(hours=1)) >= t0).any():
            raise ValueError(f'Future weather in {gid}')
        for col in ('spartacus-v2-1d-1km_last_day', 'snowgrid_cl-v2-1d-1km_last_day'):
            if col in g and ((pd.to_datetime(g[col], utc=True).dropna() + pd.Timedelta(hours=30)) >= t0).any():
                raise ValueError(f'Future daily product in {gid}')
        xy = ctrl[['x', 'y']].to_numpy()
        dist = np.linalg.norm(xy[:, None] - xy[None], axis=2) + np.eye(k) * 1e9
        if dist.min() < c['separation_m']:
            raise ValueError(f'Overlapping controls {gid}')
        if not ctrl.inventory_clear.all() or not ctrl.inside_austria.all() or (ctrl.slope < 5).any():
            raise ValueError(f'Control eligibility violated {gid}')
        pos = g[g.label == 1][['x', 'y']].to_numpy()[0]
        ring = np.hypot(*(xy - pos).T)
        if (ring < 750 - 1e-6).any() or (ring > 10000 + 1e-6).any() or not np.allclose(ring, ctrl.distance_to_positive_m, atol=1e-3):
            raise ValueError(f'Control distance violated {gid}')
    return {'groups': int(data.event_group_id.nunique()), 'samples': int(len(data)), 'checks': 'PASS'}


FEATURE_COLUMNS = (['elevation', 'slope', 'aspect_sin', 'aspect_cos', 'profile_curvature', 'plan_curvature', 'roughness_tri',
                    'tpi_150m', 'tpi_500m', 'relative_position_500m', 'log10_catchment_m2', 'twi', 'land_cover_class',
                    'geology_class'] + W.INCA_FEATURES + W.SAME_DAY +
                   ['spartacus_rr_90d', 'spartacus_rr_180d', 'swe_last', 'snow_depth_last', 'swe_melt_3d', 'swe_melt_7d', 'swe_melt_14d'])


def positive_consistency(data):
    """Positives were recomputed with the controls; their features must equal the V0.4 values."""
    old = v04_dataset()
    old = old[old.label == 1].set_index('sample_id')
    new = data[data.label == 1].set_index('sample_id')
    old = old.loc[new.index]
    out = {}
    for col in FEATURE_COLUMNS:
        a, b = new[col], old[col]
        if not (pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b)):
            same = (a.fillna('NA').astype(str) == b.fillna('NA').astype(str))
            out[col] = {'mismatches': int((~same).sum())}
        else:
            a, b = a.astype(float), b.astype(float)
            both_nan = a.isna() & b.isna()
            diff = (a - b).abs()
            out[col] = {'mismatches': int(((diff > 1e-6) | (a.isna() != b.isna())).sum()),
                        'max_abs_diff': float(diff[~both_nan].max()) if (~both_nan).any() else 0.0}
    return {'positives': int(len(new)), 'columns_with_mismatch': {k: v for k, v in out.items() if v['mismatches']},
            'all_identical': not any(v['mismatches'] for v in out.values())}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=['pools', 'select', 'static', 'context', 'weather', 'assemble'])
    p.add_argument('--limit', type=int, default=1)
    p.add_argument('--resource', default='inca')
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    {'pools': stage_pools, 'select': lambda: stage_select(a.limit), 'static': lambda: stage_static(a.limit, a.workers),
     'context': lambda: stage_context(a.limit), 'weather': lambda: stage_weather(a.limit, a.resource),
     'assemble': lambda: stage_assemble(a.limit)}[a.stage]()


if __name__ == '__main__':
    main()
