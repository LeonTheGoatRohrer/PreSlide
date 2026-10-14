"""Build the satellite training table: eligible positives and their matched controls on the same acquisitions."""
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd

from ..common import write_json, read_json
from . import events, stac
from .features import feature_maps, features_at
from .imagery import event_grid, fetch_patch, coregistration_shift, utm_epsg, sample_dir
from .paths import SAT_DATA, guard, config
from .selection import run_selection, eligibility_row

PAIR_ROLES = ('before_primary', 'after_primary')


def eligible_positives(limit=0):
    pos = events.positives()
    el = config()['eligibility']
    pos = pos[(pos['event_day'].str[:4].astype(int) >= el['min_event_year'])]
    pos = events.representative_order(pos)
    if not limit:
        return pos
    # A pilot limit counts events whose position is fine enough for training; coarse-position events cost no network
    # requests and are always listed, so the eligibility table never silently omits them.
    fine = pos[pos['source_position_upper_m'] <= el['max_position_upper_m']].head(limit)
    coarse = pos[pos['source_position_upper_m'] > el['max_position_upper_m']]
    return pd.concat([fine, coarse]).reset_index(drop=True)


def run_eligibility(limit=0, workers=4):
    """Acquisition selection for every (pre-filtered) positive; writes eligibility_report rows for all 2018+ events."""
    pos = eligible_positives(limit)
    el = config()['eligibility']
    samples = events.load_samples()
    rows, log = [], []

    def job(row):
        sid = f"{row['event_group_id']}_positive"
        if int(row['source_position_upper_m']) > el['max_position_upper_m']:
            return row, None, 'position_coarse'
        t = time.time()
        ctrl = events.controls_of(samples, row['event_group_id'])
        members = list(zip(ctrl['sample_id'], ctrl['longitude'], ctrl['latitude']))
        sel = run_selection(sid, row['longitude'], row['latitude'], row['event_day'], members)
        return row, sel, f'{time.time() - t:.0f}s'

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for row, sel, note in ex.map(job, [r for _, r in pos.iterrows()]):
            rec = eligibility_row(row, sel, el)
            rows.append(rec)
            log.append(f"{rec['event_id']} {rec['event_date']} usable={rec['usable']} {rec['exclusion_reason']} {note}")
            print(log[-1], flush=True)
    frame = pd.DataFrame(rows)
    out = guard(SAT_DATA / 'tables') / 'eligibility.parquet'
    frame.to_parquet(out, index=False)
    return frame


def _doy_gap(d1, d2):
    a, b = date.fromisoformat(d1[:10]).timetuple().tm_yday, date.fromisoformat(d2[:10]).timetuple().tm_yday
    g = abs(a - b)
    return min(g, 365 - g)


def build_sample(sample_row, event_row, sel, epsg):
    """Features for one sample (positive or control) on the event's selected before/after acquisitions."""
    sid = sample_row['sample_id']
    lon, lat = sample_row['longitude'], sample_row['latitude']
    grid = event_grid(lon, lat, epsg=epsg)
    patches = {}
    for role in PAIR_ROLES:
        item = sel['items'][role] if sample_row['label'] == 1 else sel['control_items'].get(role, {}).get(sid)
        if item is None:
            return None, f'{role}_control_not_usable_on_group_acquisition'
        patches[role] = fetch_patch(sid, item, grid)
    (rb, sb, mb), (ra, sa, ma) = patches['before_primary'], patches['after_primary']
    maps = feature_maps(rb, ra, sb, sa, grid.res)
    r, c = grid.centre_pixel()
    feats = features_at(maps, r, c)
    valid = np.isfinite(rb).all(axis=0) & np.isfinite(ra).all(axis=0)
    dx, dy, ratio = coregistration_shift(rb[3], ra[3], valid)
    qb, qa = mb['quality'], ma['quality']
    rec = {'sample_id': sid, 'event_group_id': sample_row['event_group_id'], 'label': int(sample_row['label']),
           'sample_type': 'POSITIVE' if sample_row['label'] == 1 else 'CONTROL_PSEUDO_NEGATIVE',
           'label_provenance': 'OFFICIAL_INVENTORY' if sample_row['label'] == 1 else 'MATCHED_CONTROL_NO_DOCUMENTED_EVENT',
           'independence_unit': event_row['independence_unit'], 'v04_partition': event_row['partition'],
           'state': event_row['state'], 'event_day': event_row['event_day'], 'process_type': event_row['process_type'],
           'position_upper_m': int(event_row['source_position_upper_m']), 'slope': float(sample_row['slope']),
           'land_cover_class': sample_row.get('land_cover_class'), 'distance_to_positive_m': float(sample_row['distance_to_positive_m']),
           'longitude': lon, 'latitude': lat, 'grid_epsg': epsg,
           'before_item': mb['item_id'], 'after_item': ma['item_id'], 'before_datetime': mb['datetime'], 'after_datetime': ma['datetime'],
           'before_collection': mb['collection'], 'after_collection': ma['collection'], 'same_collection': mb['collection'] == ma['collection'],
           'days_before': sel['selected']['before_primary']['days_from_event'], 'days_after': sel['selected']['after_primary']['days_from_event'],
           'doy_gap': _doy_gap(mb['datetime'], ma['datetime']),
           'before_core_cloud': qb['core']['cloud'], 'before_core_snow': qb['core']['snow'], 'before_core_invalid': qb['core']['invalid'],
           'after_core_cloud': qa['core']['cloud'], 'after_core_snow': qa['core']['snow'], 'after_core_invalid': qa['core']['invalid'],
           'before_patch_cloud': qb['patch']['cloud'], 'after_patch_cloud': qa['patch']['cloud'],
           'coreg_dx_px': dx, 'coreg_dy_px': dy, 'coreg_peak_ratio': ratio}
    rec.update(feats)
    return rec, ''


def build_dataset(limit=0, workers=4):
    """Positives with a usable pair plus their 5 controls; cached per sample as JSON, assembled into one parquet table."""
    samples = events.load_samples()
    elig = pd.read_parquet(SAT_DATA / 'tables/eligibility.parquet')
    usable = elig[elig['usable']]
    if limit:
        usable = usable[usable['event_id'].isin(eligible_positives(limit)['event_group_id'])]
    pos = events.positives(samples).set_index('event_group_id')
    rows, status = [], {}

    def job(event_id):
        event_row = pos.loc[event_id]
        sel = read_json(sample_dir(f'{event_id}_positive') / 'selection.json')
        epsg = utm_epsg(event_row['longitude'])
        out = []
        ctrl = events.controls_of(samples, event_id)
        members = pd.concat([samples[samples['sample_id'] == f'{event_id}_positive'], ctrl[ctrl['sample_id'].isin(sel['usable_controls'])]])
        for _, srow in members.iterrows():
            cache = sample_dir(srow['sample_id']) / 'features.json'
            if cache.exists():
                rec = read_json(cache)
                same_pair = rec.get('before_datetime', '')[:16] == sel['selected']['before_primary']['datetime'][:16] and \
                    rec.get('after_datetime', '')[:16] == sel['selected']['after_primary']['datetime'][:16]
                if same_pair and rec.get('valid_core_frac', 0) >= config()['eligibility']['core_valid_min']:
                    out.append(rec)
                    continue
            try:
                rec, reason = build_sample(srow, event_row, sel, epsg)
            except Exception as error:  # network/raster failures are recorded, never silently skipped
                rec, reason = None, f'error: {error}'
            if rec is None:
                status[srow['sample_id']] = reason
                continue
            write_json(cache, rec)
            out.append(rec)
        return event_id, out

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for event_id, out in ex.map(job, list(usable['event_id'])):
            rows += out
            n_pos = sum(r['label'] for r in out)
            print(f'{event_id}: {len(out)} samples ({n_pos} positive)', flush=True)
    if not rows:
        raise RuntimeError(f'no sample could be built: {status}')
    frame = pd.DataFrame(rows)
    # Keep groups with one positive and at least min_controls_usable controls; group size is recorded for chance levels.
    sizes = frame.groupby('event_group_id')['label'].agg(['count', 'sum'])
    complete = sizes[(sizes['count'] >= 1 + config()['eligibility']['min_controls_usable']) & (sizes['sum'] == 1)].index
    incomplete = sorted(set(frame['event_group_id']) - set(complete))
    frame = frame[frame['event_group_id'].isin(complete)].reset_index(drop=True)
    frame['group_size'] = frame.groupby('event_group_id')['label'].transform('count')
    out = guard(SAT_DATA / 'tables')
    frame.to_parquet(out / 'dataset.parquet', index=False)
    write_json(out / 'dataset_status.json', {'groups_complete': len(complete), 'groups_incomplete': incomplete,
                                             'sample_failures': status, 'rows': len(frame)})
    return frame
