"""Generic hard negatives (RANDOM_LANDSCAPE): random points 1.5-8 km from each eligible positive, outside the V0.4
exclusion radius of every inventory event (floored at 400 m), inside Austria, on the positive's own before/after
acquisitions and locally usable by the same cloud/snow/validity rules. No terrain matching: fields, forest, water
and settlements are all allowed, which is the point. These rows never enter a Pipeline A table."""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from shapely import contains_xy

from ..common import read_json, write_json, digest
from ..matching import Exclusions, austria_boundary
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE
from . import events
from .dataset import build_sample, PAIR_ROLES
from .imagery import event_grid, utm_epsg, sample_dir
from .selection import covering_usable_item
from .paths import SAT_DATA, guard, config

SAMPLE_TYPE = 'RANDOM_LANDSCAPE'
PROVENANCE = 'RANDOM_POINT_NO_DOCUMENTED_EVENT_WITHIN_EXCLUSION_RADIUS'


def exclusion_index(rl=None):
    """V0.4 exclusion logic (full GeoSphere inventory, radius 250 m + position uncertainty) floored at the configured
    minimum distance to any known event."""
    rl = rl or config()['random_landscape']
    ex = Exclusions(read_json(ROOT / 'config/v04.json')['matching'])
    ex.radii = np.maximum(ex.radii, rl['min_distance_to_any_known_event_m'])
    return ex


def draw_points(px, py, rng, n, rl):
    """Uniform in the annulus [min_distance_m, max_distance_m] around the projected positive (EPSG:31287)."""
    distance = np.sqrt(rng.uniform(rl['min_distance_m'] ** 2, rl['max_distance_m'] ** 2, n))
    angle = rng.uniform(0, 2 * np.pi, n)
    xy = np.column_stack([px + distance * np.cos(angle), py + distance * np.sin(angle)])
    lon, lat = INVERSE.transform(xy[:, 0], xy[:, 1])
    return pd.DataFrame({'draw': np.arange(n), 'x': xy[:, 0], 'y': xy[:, 1], 'longitude': lon, 'latitude': lat,
                         'distance_to_positive_m': distance})


def geometric_filter(points, allowed, inside, separation_m):
    """Keep draws that pass the exclusion test (`allowed(xy) -> bool array`), lie inside the country
    (`inside(lon, lat) -> bool array`) and are at least `separation_m` from every earlier kept draw.
    Returns the frame with a `geometry_reason` column ('' = kept)."""
    pts = points.copy()
    xy = pts[['x', 'y']].to_numpy()
    ok_ex = np.asarray(allowed(xy), dtype=bool)
    ok_in = np.asarray(inside(pts['longitude'].to_numpy(), pts['latitude'].to_numpy()), dtype=bool)
    reasons, kept_xy = [], []
    for i in range(len(pts)):
        if not ok_ex[i]:
            reasons.append('within_exclusion_radius_of_known_event')
        elif not ok_in[i]:
            reasons.append('outside_austria')
        elif kept_xy and np.min(np.hypot(*(np.array(kept_xy) - xy[i]).T)) < separation_m:
            reasons.append('too_close_to_other_random_point')
        else:
            reasons.append('')
            kept_xy.append(xy[i])
    pts['geometry_reason'] = reasons
    return pts


def check_random_landscape_table(rl, frame, cfg=None):
    """Scientific preconditions, checked loudly: label 0, RANDOM_LANDSCAPE type, distance within bounds, and the
    same before/after acquisitions as the positive of the same event group."""
    rcfg = (cfg or config())['random_landscape']
    if len(rl) == 0:
        raise RuntimeError('random landscape table is empty')
    if (rl['label'] != 0).any() or (rl['sample_type'] != SAMPLE_TYPE).any():
        raise RuntimeError('random landscape rows must be label 0 / RANDOM_LANDSCAPE')
    d = rl['distance_to_positive_m']
    if (d < rcfg['min_distance_m']).any() or (d > rcfg['max_distance_m']).any():
        raise RuntimeError('random landscape point outside the configured distance band')
    if (rl['distance_to_nearest_inventory_event_m'] < rcfg['min_distance_to_any_known_event_m']).any():
        raise RuntimeError('random landscape point inside the exclusion distance of a known event')
    pos = frame[frame['label'] == 1].set_index('event_group_id')
    for col in ('before_datetime', 'after_datetime'):
        want = pos.loc[rl['event_group_id'], col].to_numpy()
        if (rl[col].str[:16].to_numpy() != pd.Series(want).str[:16].to_numpy()).any():
            raise RuntimeError(f'random landscape row not on the acquisition pair of its positive ({col})')
    return True


def _nearest_inventory_m(ex, xy):
    d, _ = ex.tree.query(xy)
    return float(d)


def sample_event(event_id, event_row, samples, ex, country, rl, el, workers_note=None):
    """Draw, screen and build the random landscape rows for one event; cached per event."""
    status_path = guard(SAT_DATA / 'landscape') / f'{event_id}.json'
    if status_path.exists():
        st = read_json(status_path)
        if st.get('config_digest') == digest(rl):
            return st
    sel = read_json(sample_dir(f'{event_id}_positive') / 'selection.json')
    epsg = utm_epsg(event_row['longitude'])
    px, py = PROJECT.transform(event_row['longitude'], event_row['latitude'])
    rng = np.random.default_rng(int(digest([event_id, 'random_landscape', rl['seed']])[:8], 16))
    pts = geometric_filter(draw_points(px, py, rng, rl['max_draws'], rl), ex.allowed,
                           lambda lon, lat: contains_xy(country, lon, lat), rl['separation_m'])
    accepted, imagery_reasons = [], {}
    for _, p in pts[pts['geometry_reason'] == ''].iterrows():
        if len(accepted) >= rl['n_per_event']:
            break
        sid = f"{event_id}_landscape_{int(p['draw']):02d}"
        grid = event_grid(p['longitude'], p['latitude'], epsg=epsg)
        items, reasons = {}, []
        for role in PAIR_ROLES:
            it, reason, _ = covering_usable_item(sel['items'][role], sid, p['longitude'], p['latitude'], grid, el)
            if it is None:
                reasons.append(f'{role}:{reason}')
                break
            items[role] = it
        if reasons:
            imagery_reasons[sid] = ';'.join(reasons)
            continue
        row = {'sample_id': sid, 'event_group_id': event_id, 'label': 0, 'longitude': float(p['longitude']), 'latitude': float(p['latitude']),
               'slope': None, 'land_cover_class': None, 'distance_to_positive_m': float(p['distance_to_positive_m'])}
        cache = sample_dir(sid) / 'features.json'
        try:
            rec, reason = build_sample(row, event_row, sel, epsg, items=items, sample_type=SAMPLE_TYPE, label_provenance=PROVENANCE)
        except Exception as error:      # recorded, never silently skipped
            rec, reason = None, f'error: {error}'
        if rec is None:
            imagery_reasons[sid] = reason
            continue
        rec['draw_index'] = int(p['draw'])
        rec['distance_to_nearest_inventory_event_m'] = _nearest_inventory_m(ex, [p['x'], p['y']])
        write_json(cache, rec)
        accepted.append(sid)
    st = {'event_group_id': event_id, 'config_digest': digest(rl), 'draws': int(len(pts)),
          'geometry_rejections': {k: int(v) for k, v in pts.loc[pts['geometry_reason'] != '', 'geometry_reason'].value_counts().items()},
          'imagery_rejections': imagery_reasons, 'accepted': accepted}
    write_json(status_path, st)
    return st


def run(limit=0, workers=2):
    cfg = config()
    rl = dict(cfg['random_landscape'])
    rl.setdefault('separation_m', read_json(ROOT / 'config/v04.json')['matching']['control_separation_m'])
    el = cfg['eligibility']
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    pos = frame[frame['label'] == 1].reset_index(drop=True)
    if limit:
        pos = pos.head(limit)
    samples = events.load_samples()
    event_rows = events.positives(samples).set_index('event_group_id')
    ex, country = exclusion_index(rl), austria_boundary()
    statuses, errors = [], {}

    def job(eid):
        try:
            return sample_event(eid, event_rows.loc[eid], samples, ex, country, rl, el)
        except Exception as error:      # transient network/raster failure: recorded, not cached, retried on rerun
            return {'event_group_id': eid, 'error': f'{type(error).__name__}: {error}', 'accepted': [], 'draws': 0,
                    'geometry_rejections': {}, 'imagery_rejections': {}}

    with ThreadPoolExecutor(max_workers=workers) as exe:
        for st in exe.map(job, list(pos['event_group_id'])):
            if 'error' in st:
                errors[st['event_group_id']] = st['error']
                print(f"{st['event_group_id']}: ERROR {st['error']}", flush=True)
                continue
            statuses.append(st)
            print(f"{st['event_group_id']}: accepted {len(st['accepted'])} of {st['draws']} draws; geometry {st['geometry_rejections']}; "
                  f"imagery {len(st['imagery_rejections'])}", flush=True)
    rows = [read_json(sample_dir(sid) / 'features.json') for st in statuses for sid in st['accepted']]
    rl_frame = pd.DataFrame(rows)
    out = guard(SAT_DATA / 'tables')
    check_random_landscape_table(rl_frame, frame, cfg)
    rl_frame.to_parquet(out / 'random_landscape.parquet', index=False)
    summary = {'events': len(statuses), 'events_with_error_not_cached': errors, 'rows': len(rl_frame), 'config': rl,
               'events_by_accepted_count': {int(k): int(v) for k, v in pd.Series([len(s['accepted']) for s in statuses]).value_counts().sort_index().items()},
               'geometry_rejections_total': {k: int(sum(s['geometry_rejections'].get(k, 0) for s in statuses)) for k in sorted({k for s in statuses for k in s['geometry_rejections']})},
               'imagery_rejections_total': int(sum(len(s['imagery_rejections']) for s in statuses)),
               'imagery_rejection_reasons': pd.Series([v.split(':')[-1].split('/')[0] for s in statuses for v in s['imagery_rejections'].values()]).value_counts().to_dict()}
    write_json(out / 'random_landscape_status.json', summary)
    return rl_frame, summary
