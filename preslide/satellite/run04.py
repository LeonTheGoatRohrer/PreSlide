"""satellite-0.4 stages (config/satellite_0_4.json).

  python -m preslide.satellite.run04 norm [--limit N] [--workers W]   # reference / confirm patches + normalised features
  python -m preslide.satellite.run04 baseline                          # event-held-out baselines, paired bootstrap
  python -m preslide.satellite.run04 discovery [--limit N]             # held-out rediscovery with filters, position refinement
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.ndimage import label as cc_label

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT
from ..v04.terrain import matching_terrain
from . import events
from .baseline import evaluate, feature_columns, make_model
from .change04 import NORM_FEATURES, PERSIST_FEATURES, cloud_snow_mask, config04, distance_to_mask_m, filter_peaks, norm_maps, water_core_share
from .discovery import known_pixels, peaks, score_map, suppress_near_known
from .features import feature_maps, features_at, indices, model_feature_names, valid_mask
from .imagery import Grid, event_grid, fetch_patch, sample_dir
from .paths import SAT_DATA, SAT_REPORT, config as base_config, guard
from .selection import covering_usable_item

ROLES = {'ref': 'before_reference', 'confirm': 'after_confirm'}


def _norm_cache(sid):
    return sample_dir(sid) / 'features_norm.json'


def _role_item(row, sel, role):
    """Acquisition of `role` usable at the sample: the positive's item, or the covering tile for a control."""
    item = sel['items'].get(role)
    if item is None:
        return None, 'role_not_selected'
    if row['label'] == 1:
        return item, ''
    grid = event_grid(row['longitude'], row['latitude'], epsg=int(row['grid_epsg']))
    got, reason, _ = covering_usable_item(item, row['sample_id'], row['longitude'], row['latitude'], grid, base_config()['eligibility'])
    return got, reason


def sample_norm(row, cfg04):
    """Normalised / persistence features of one dataset row; cached per sample."""
    sid = row['sample_id']
    cache = _norm_cache(sid)
    if cache.exists():
        return read_json(cache)
    sel = read_json(sample_dir(f"{row['event_group_id']}_positive") / 'selection.json')
    grid = event_grid(row['longitude'], row['latitude'], epsg=int(row['grid_epsg']))
    base_items = {}
    for role in ('before_primary', 'after_primary'):
        base_items[role] = sel['items'][role] if row['label'] == 1 else sel['control_items'][role][sid]
    rb, sb, _ = fetch_patch(sid, base_items['before_primary'], grid)
    ra, sa, _ = fetch_patch(sid, base_items['after_primary'], grid)
    extra, notes = {}, {}
    for key, role in ROLES.items():
        item, reason = _role_item(row, sel, role)
        notes[key] = reason or 'ok'
        extra[key] = (None, None)
        if item is not None:
            try:
                extra[key] = fetch_patch(sid, item, grid)[:2]
            except RuntimeError as error:       # radiometric plausibility check refused the acquisition: treated as not usable
                notes[key] = 'radiometry_check_failed'
                print(f'{sid} {role}: {str(error)[:120]}', flush=True)
    rr, sr = extra['ref']
    rc, sc = extra['confirm']
    ok = np.ones(rb.shape[1:], bool)
    maps = norm_maps(rr, rb, ra, rc, valid_mask(rr, sr) if rr is not None else ok, valid_mask(rb, sb), valid_mask(ra, sa),
                     valid_mask(rc, sc) if rc is not None else ok, grid.res, cfg04, base_config())
    feats = features_at(maps, *grid.centre_pixel())
    rec = {'sample_id': sid, **{k: (v if np.isfinite(v) else None) for k, v in feats.items()}, 'norm_reference': notes['ref'], 'norm_confirm': notes['confirm']}
    write_json(cache, rec)
    return rec


def stage_norm(limit=0, workers=2):
    cfg04 = config04()
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    if limit:
        frame = frame[frame['event_group_id'].isin(sorted(frame['event_group_id'].unique())[:limit])]

    def job(i):
        try:
            return sample_norm(frame.iloc[i], cfg04)
        except Exception as error:  # recorded, rerun continues from the cache
            return {'sample_id': frame.iloc[i]['sample_id'], 'error': str(error)[:200]}

    recs, t = [], time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for n, rec in enumerate(ex.map(job, range(len(frame))), 1):
            recs.append(rec)
            if n % 25 == 0:
                print(f'{n}/{len(frame)} {time.time() - t:.0f}s errors={sum("error" in r for r in recs)}', flush=True)
    errors = [r for r in recs if 'error' in r]
    if errors:
        print('ERRORS', json.dumps(errors[:5]))
        sys.exit(2)
    norm = pd.DataFrame(recs)
    norm[NORM_FEATURES + PERSIST_FEATURES] = norm[NORM_FEATURES + PERSIST_FEATURES].astype(float)
    out = frame.merge(norm, on='sample_id', how='left', validate='one_to_one')
    name = 'dataset_norm.parquet' if not limit else f'dataset_norm_pilot_{limit}.parquet'
    out.to_parquet(guard(SAT_DATA / 'tables') / name, index=False)
    summary = {'rows': len(out), 'reference_ok_share': float((out['norm_reference'] == 'ok').mean()), 'confirm_ok_share': float((out['norm_confirm'] == 'ok').mean()),
               'reference_by_label': out.groupby('label')['norm_reference'].apply(lambda s: float((s == 'ok').mean())).to_dict(),
               'confirm_by_label': out.groupby('label')['norm_confirm'].apply(lambda s: float((s == 'ok').mean())).to_dict(),
               'missing_reasons_reference': out.loc[out['norm_reference'] != 'ok', 'norm_reference'].value_counts().to_dict(),
               'missing_reasons_confirm': out.loc[out['norm_confirm'] != 'ok', 'norm_confirm'].value_counts().to_dict()}
    write_json(SAT_DATA / 'tables' / name.replace('.parquet', '_status.json'), summary)
    print(json.dumps(summary, indent=1))


# ---------- baselines ----------

def unit_bootstrap_difference(frame, auc_a, auc_b, draws, seed):
    """Paired unit bootstrap of mean(auc_a - auc_b) over event groups, resampling independence units (unit-weighted)."""
    pos = frame[frame['label'] == 1][['event_group_id', 'independence_unit']].reset_index(drop=True)
    d = np.asarray(auc_a) - np.asarray(auc_b)
    units = pos['independence_unit'].to_numpy()
    uniq = np.unique(units)
    per_unit = {u: d[units == u].mean() for u in uniq}
    rng = np.random.default_rng(seed)
    boots = [np.mean([per_unit[u] for u in rng.choice(uniq, len(uniq), replace=True)]) for _ in range(draws)]
    return {'mean_unit_weighted': float(np.mean(list(per_unit.values()))), 'ci95': np.quantile(boots, [.025, .975]).tolist()}


def stage_baseline(seeds=(0, 1, 2), draws=2000):
    cfg04, cfg = config04(), base_config()
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset_norm.parquet')
    old = model_feature_names([c for c in feature_columns(frame) if c not in NORM_FEATURES + PERSIST_FEATURES and not c.startswith('norm_')])
    sets = {'change_features': old, 'change_norm': old + NORM_FEATURES + PERSIST_FEATURES, 'norm_only': NORM_FEATURES, 'persistence_only': PERSIST_FEATURES}
    out = {'dataset': {'rows': len(frame), 'groups': int(frame['event_group_id'].nunique()), 'units': int(frame['independence_unit'].nunique())},
           'coverage': {c: float(frame[c].notna().mean()) for c in NORM_FEATURES[:1] + PERSIST_FEATURES[:1]}, 'models': {}, 'paired': {}}
    per = {}
    for name, cols in sets.items():
        for kind in ('logistic_regression', 'hist_gradient_boosting'):
            reps = [evaluate(frame, cols, kind, cfg, s) for s in seeds]
            per[(name, kind)] = reps
            out['models'][f'{name}/{kind}'] = {m: float(np.mean([r[m] for r in reps])) for m in ('within_group_auc', 'within_group_auc_unit_weighted', 'top1_rate', 'roc_auc')}
    for kind in ('logistic_regression', 'hist_gradient_boosting'):
        for name in ('change_norm', 'norm_only', 'persistence_only'):
            a = np.mean([r['per_group_auc'] for r in per[(name, kind)]], axis=0)
            b = np.mean([r['per_group_auc'] for r in per[('change_features', kind)]], axis=0)
            out['paired'][f'{name} - change_features / {kind}'] = unit_bootstrap_difference(frame, a, b, draws, 20261018)
    write_json(guard(SAT_REPORT) / 'baseline_0_4.json', out)
    print(json.dumps({k: round(v['within_group_auc_unit_weighted'], 3) for k, v in out['models'].items()}, indent=1))
    print(json.dumps(out['paired'], indent=1))
    return cfg04


# ---------- discovery ----------

def scar_refinement(maps_delta, grid, pk, cfg_base, hit_px):
    """Centroid of the contiguous change region nearest to the hit pixel (position refinement proposal)."""
    thr = cfg_base['features']['change_thresholds']
    mask = (maps_delta['ndvi'] < thr['ndvi']) | (maps_delta['bsi'] > thr['bsi']) | (maps_delta['brightness'] > thr['brightness'])
    mask &= maps_delta['valid']
    half = 32
    r0, c0 = pk[1], pk[2]
    window = np.zeros_like(mask)
    window[max(r0 - half, 0):r0 + half + 1, max(c0 - half, 0):c0 + half + 1] = True
    lab, n = cc_label(mask & window)
    if n == 0:
        return None
    best, best_d = None, np.inf
    for k in range(1, n + 1):
        rr, cc = np.nonzero(lab == k)
        d = np.min(np.hypot(rr - r0, cc - c0))
        if d < best_d:
            best, best_d = (rr, cc), d
    if best_d > hit_px:
        return None
    rr, cc = best
    return {'row': float(rr.mean()), 'col': float(cc.mean()), 'area_m2': int(len(rr) * grid.res ** 2)}


def event_maps(event_id, cfg04, cfg_base):
    sid = f'{event_id}_positive'
    sel = read_json(sample_dir(sid) / 'selection.json')
    grid = Grid(**sel['grid'])
    got = {}
    for key, role in (('b', 'before_primary'), ('a', 'after_primary'), ('r', 'before_reference'), ('c', 'after_confirm')):
        item = sel['items'].get(role)
        got[key] = fetch_patch(sid, item, grid)[:2] if item is not None else (None, None)
    (rb, sb), (ra, sa), (rr, sr), (rc, sc) = got['b'], got['a'], got['r'], got['c']
    maps = feature_maps(rb, ra, sb, sa, grid.res)
    ok = np.ones(rb.shape[1:], bool)
    maps.update(norm_maps(rr, rb, ra, rc, valid_mask(rr, sr) if rr is not None else ok, valid_mask(rb, sb), valid_mask(ra, sa),
                          valid_mask(rc, sc) if rc is not None else ok, grid.res, cfg04, cfg_base))
    ib, ia = indices(rb), indices(ra)
    v = valid_mask(rb, sb) & valid_mask(ra, sa)
    delta = {k: ia[k] - ib[k] for k in ('ndvi', 'bsi', 'brightness')}
    delta['valid'] = v & np.all([np.isfinite(d) for d in delta.values()], axis=0)
    cloud = cloud_snow_mask(rb, sb, ra, sa, cfg04['filters']['cloud_classes'])
    return grid, sel, maps, delta, (sb, sa), cloud


def stage_discovery(limit=0):
    cfg04, cfg = config04(), base_config()
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset_norm.parquet')
    old = model_feature_names([c for c in feature_columns(frame) if c not in NORM_FEATURES + PERSIST_FEATURES and not c.startswith('norm_')])
    sets = {'change_features': old, 'change_norm': old + NORM_FEATURES + PERSIST_FEATURES}
    known = events.known_positive_positions()
    d = cfg['discovery']
    filters = cfg04['filters']
    core_px = int(round(cfg['patch']['core_m'] / cfg['patch']['resolution_m']))
    margin = int(round(cfg['patch']['medium_m'] / cfg['patch']['resolution_m'] / 2))
    wanted = sorted(frame[frame['label'] == 1]['event_group_id'])
    if limit:
        wanted = wanted[:limit]
    rows, refinements = [], []
    for unit, held in frame.groupby('independence_unit'):
        train = frame[frame['independence_unit'] != unit]
        ev = [e for e in held[held['label'] == 1]['event_group_id'] if e in wanted]
        if not ev or train['independence_unit'].nunique() < 2:
            continue
        models = {k: make_model('logistic_regression', cfg).fit(train[cols].to_numpy(float), train['label'].to_numpy()) for k, cols in sets.items()}
        for eid in ev:
            grid, sel, maps, delta, (sb, sa), cloud = event_maps(eid, cfg04, cfg)
            pos_row = frame[(frame['event_group_id'] == eid) & (frame['label'] == 1)].iloc[0]
            terrain = matching_terrain({'event_id': eid, 'longitude': float(pos_row['longitude']), 'latitude': float(pos_row['latitude']),
                                        'event_day': pos_row['event_day']}, read_json(ROOT / 'config/v04.json')['matching'])
            to31287 = Transformer.from_crs(grid.crs, 'EPSG:31287', always_xy=True)

            def slope_at(r, c, terrain=terrain, grid=grid, to31287=to31287):
                x, y = to31287.transform(grid.x0 + (c + 0.5) * grid.res, grid.y1 - (r + 0.5) * grid.res)
                col, row = int((x - float(terrain['left'])) // float(terrain['resolution'])), int((float(terrain['top']) - y) // float(terrain['resolution']))
                ok = 0 <= row < terrain['slope'].shape[0] and 0 <= col < terrain['slope'].shape[1]
                return float(terrain['slope'][row, col]) if ok else np.nan

            water = water_core_share(sb, sa, core_px, filters['water_scl_class'])
            cdist = distance_to_mask_m(cloud, grid.res)
            r0, c0 = grid.centre_pixel()
            hit_px = d['hit_radius_m'] / grid.res
            other = known_pixels(grid, known, exclude_event=eid)
            searched = ((grid.n - 2 * margin) * grid.res / 1000) ** 2
            for name, cols in sets.items():
                s = score_map(models[name], {k: maps[k] for k in cols}, cols, margin)
                pk_all = peaks(s, int(round(d['min_peak_distance_m'] / grid.res / 2)))
                pk_sup, sup = suppress_near_known(pk_all, other, d.get('suppress_known_positives_m', 0) / grid.res, (r0, c0), hit_px)
                variants = {'no_filter': pk_sup}
                removed = {}
                variants['cloud_buffer_only'], removed['cloud_buffer_only'] = filter_peaks(pk_sup, lambda r, c: 99.0, np.zeros_like(water), cdist, {**filters, 'min_slope_deg': 0})
                variants['terrain_water_only'], removed['terrain_water_only'] = filter_peaks(pk_sup, slope_at, water, np.full_like(cdist, 1e9), filters)
                variants['all_filters'], removed['all_filters'] = filter_peaks(pk_sup, slope_at, water, cdist, filters)
                for vname, pk in variants.items():
                    hit_rank = next((i for i, (_, r, c) in enumerate(pk, 1) if np.hypot(r - r0, c - c0) <= hit_px), None)
                    rows.append({'event_group_id': eid, 'independence_unit': unit, 'feature_set': name, 'variant': vname, 'peaks': len(pk),
                                 'hit_rank': hit_rank, 'searched_km2': searched, 'peaks_suppressed_known': len(sup),
                                 'removed': json.dumps(removed.get(vname, {}))})
                    if name == 'change_norm' and vname == 'all_filters' and hit_rank is not None:
                        persists = float(maps['persistence_ndvi'][pk[hit_rank - 1][1], pk[hit_rank - 1][2]]) < 0 or \
                            float(maps['persistence_bsi'][pk[hit_rank - 1][1], pk[hit_rank - 1][2]]) > 0
                        ref = scar_refinement(delta, grid, pk[hit_rank - 1], cfg, hit_px) if persists else None
                        if ref:
                            to_wgs = Transformer.from_crs(grid.crs, 'EPSG:4326', always_xy=True)
                            x, y = grid.x0 + (ref['col'] + 0.5) * grid.res, grid.y1 - (ref['row'] + 0.5) * grid.res
                            lon, lat = to_wgs.transform(x, y)
                            x31, y31 = PROJECT.transform(lon, lat)
                            ox, oy = PROJECT.transform(float(pos_row['longitude']), float(pos_row['latitude']))
                            refinements.append({'event_group_id': eid, 'old_longitude': float(pos_row['longitude']), 'old_latitude': float(pos_row['latitude']),
                                                'new_longitude': float(lon), 'new_latitude': float(lat), 'shift_m': float(np.hypot(x31 - ox, y31 - oy)),
                                                'scar_area_m2': ref['area_m2'], 'source': 'satellite_scar_centroid',
                                                'source_position_upper_m': int(pos_row['position_upper_m']), 'hit_rank': hit_rank})
            print(f'{eid}: ' + ', '.join(f"{r['feature_set']}/{r['variant']}={r['hit_rank']}" for r in rows[-8:] if r['event_group_id'] == eid), flush=True)
    res = pd.DataFrame(rows)
    name = 'discovery_0_4.parquet' if not limit else f'discovery_0_4_pilot_{limit}.parquet'
    res.to_parquet(guard(SAT_DATA / 'tables') / name, index=False)
    summary = {}
    for (fs, vn), g in res.groupby(['feature_set', 'variant']):
        hit = g['hit_rank'].notna()
        summary[f'{fs}/{vn}'] = {'events': len(g), 'units': int(g['independence_unit'].nunique()), 'found_any_rank': int(hit.sum()),
                                 'found_top1': int((g['hit_rank'] <= 1).sum()), 'found_top3': int((g['hit_rank'] <= 3).sum()),
                                 'found_top5': int((g['hit_rank'] <= 5).sum()), 'peaks_per_km2_mean': float((g['peaks'] / g['searched_km2']).mean()),
                                 'share_top3': float((g['hit_rank'] <= 3).mean())}
    ref = pd.DataFrame(refinements)
    if len(ref):
        ref.to_parquet(guard(SAT_DATA / 'tables') / ('position_refinement.parquet' if not limit else 'position_refinement_pilot.parquet'), index=False)
    write_json(guard(SAT_REPORT) / ('discovery_0_4.json' if not limit else 'discovery_0_4_pilot.json'), {'summary': summary, 'refinements': len(ref)})
    print(json.dumps(summary, indent=1))



if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['norm', 'baseline', 'discovery'])
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    {'norm': lambda: stage_norm(a.limit, a.workers), 'baseline': stage_baseline, 'discovery': lambda: stage_discovery(a.limit)}[a.stage]()
