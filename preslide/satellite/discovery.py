"""Retrospective discovery test: score every position of a held-out event's 2.56 km patch with a model that never saw
its independence unit, cluster the score map into candidates and ask whether the known event is rediscovered.

The search region is small (one patch, ~6.6 km²) and centred on the known event, so detection rates here are an
upper bound for an unknown-region scan; false positives per km² are the comparable quantity.

Peaks within `suppress_known_positives_m` of any OTHER known V0.4 positive are documented events: they are removed
from the ranking (not counted as false peaks, not listed as candidates) and reported separately.

satellite-0.3: the whole patch is screened. Every pixel within `cloud_buffer_m` of a cloud-like SCL pixel or an
NDSI-snow pixel in either image is removed from the valid mask, and a position is scored only if its core and ring
keep the configured minimum of valid pixels (`scorable_mask`); the fraction removed by the buffer is recorded."""
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.ndimage import maximum_filter, label as cc_label

from ..common import write_json, read_json
from . import events
from .baseline import make_model, feature_columns
from .features import feature_maps, model_feature_names, pair_valid_mask, scorable_mask, features_at
from .imagery import Grid, fetch_patch, sample_dir
from .paths import SAT_DATA, SAT_REPORT, guard, config


def score_map(model, maps, cols, margin_px, scorable=None):
    """Log-odds map (probabilities saturate at 1.0 and would create plateaus of tied maxima). Positions outside
    `scorable` (core/ring too cloudy after buffering) and inside the border margin get NaN and cannot form a peak."""
    n = next(iter(maps.values())).shape[0]
    X = np.stack([maps[c] for c in cols], axis=-1).reshape(-1, len(cols))
    out = np.full(X.shape[0], np.nan)
    ok = ~np.isnan(X).any(axis=1)
    if scorable is not None:
        ok &= scorable.reshape(-1)
    if ok.any():
        out[ok] = model.decision_function(X[ok])      # unbounded log-odds: no saturation ties
    s = out.reshape(n, n)
    s[:margin_px, :] = s[-margin_px:, :] = s[:, :margin_px] = s[:, -margin_px:] = np.nan
    return s


def buffered_maps(rb, ra, sb, sa, res_m, cfg):
    """Feature maps with the satellite-0.3 buffered mask plus the scorable-position mask and mask diagnostics."""
    d = cfg['discovery']
    buffer_m = d.get('cloud_buffer_m', 0)
    maps = feature_maps(rb, ra, sb, sa, res_m, cloud_buffer_m=buffer_m)
    plain, _ = pair_valid_mask(rb, ra, sb, sa, 0, res_m, d)
    valid, masked_frac = pair_valid_mask(rb, ra, sb, sa, buffer_m, res_m, d)
    scorable = scorable_mask(maps, d) if buffer_m else None
    diag = {'cloud_buffer_m': buffer_m, 'valid_frac_unbuffered': float(plain.mean()), 'valid_frac_buffered': float(valid.mean()),
            'buffer_masked_frac': masked_frac}
    return maps, scorable, diag


def peaks(score, min_distance_px, threshold=0.0):
    """Local maxima (non-maximum suppression) of the log-odds map above `threshold` (0 = p 0.5), ranked by score.
    A plateau of tied maxima counts once (its centroid)."""
    s = np.nan_to_num(score, nan=-np.inf)
    mx = maximum_filter(s, size=2 * min_distance_px + 1, mode='constant', cval=-np.inf)
    is_max = (s == mx) & (s > threshold)
    lab, n = cc_label(is_max)
    out = []
    for k in range(1, n + 1):
        rr, cc = np.nonzero(lab == k)
        r, c = int(round(rr.mean())), int(round(cc.mean()))
        out.append((float(s[rr[0], cc[0]]), r, c))
    return sorted(out, reverse=True)


def known_pixels(grid, known, exclude_event=None):
    """(row, col) of every known positive that falls inside the grid, except `exclude_event` (the search centre)."""
    if known is None or not len(known):
        return []
    to_grid = Transformer.from_crs('EPSG:4326', grid.crs, always_xy=True)
    out = []
    for eid, lon, lat in zip(known['event_group_id'], known['longitude'], known['latitude']):
        if eid == exclude_event:
            continue
        x, y = to_grid.transform(lon, lat)
        r, c = int((grid.y1 - y) // grid.res), int((x - grid.x0) // grid.res)
        if 0 <= r < grid.n and 0 <= c < grid.n:
            out.append((r, c))
    return out


def suppress_near_known(pk, known_px, radius_px, centre=None, hit_px=0.0):
    """Split ranked peaks into (kept, suppressed): a peak within `radius_px` of any known pixel is suppressed,
    unless it lies within `hit_px` of `centre` (the search centre defines the hit and keeps priority: in storm
    clusters several documented slides sit within 160 m of each other)."""
    if not known_px:
        return list(pk), []
    kr = np.array([k[0] for k in known_px], dtype=float)
    kc = np.array([k[1] for k in known_px], dtype=float)
    kept, suppressed = [], []
    for p in pk:
        near_centre = centre is not None and np.hypot(centre[0] - p[1], centre[1] - p[2]) <= hit_px
        d = np.hypot(kr - p[1], kc - p[2])
        (suppressed if d.min() <= radius_px and not near_centre else kept).append(p)
    return kept, suppressed


def rediscover_event(event_id, model, cols, cfg, known=None):
    sid = f'{event_id}_positive'
    sel = read_json(sample_dir(sid) / 'selection.json')
    grid = Grid(**sel['grid'])
    rb, sb, _ = fetch_patch(sid, sel['items']['before_primary'], grid)
    ra, sa, _ = fetch_patch(sid, sel['items']['after_primary'], grid)
    maps, scorable, diag = buffered_maps(rb, ra, sb, sa, grid.res, cfg)
    margin = int(round(cfg['patch']['medium_m'] / grid.res / 2))
    s = score_map(model, maps, cols, margin, scorable)
    inner = np.zeros_like(s, dtype=bool); inner[margin:-margin, margin:-margin] = True
    diag['scored_positions_frac'] = float(np.isfinite(s[inner]).mean())
    d = cfg['discovery']
    pk_all = peaks(s, int(round(d['min_peak_distance_m'] / grid.res / 2)))
    other_known = known_pixels(grid, known, exclude_event=event_id)
    r0, c0 = grid.centre_pixel()
    hit_px = d['hit_radius_m'] / grid.res
    pk, suppressed = suppress_near_known(pk_all, other_known, d.get('suppress_known_positives_m', 0) / grid.res, (r0, c0), hit_px)
    hit_rank, hit_dist = None, None
    for rank, (sc, r, c) in enumerate(pk, 1):
        dist = float(np.hypot(r - r0, c - c0))
        if dist <= hit_px:
            hit_rank, hit_dist = rank, dist * grid.res
            break
    area_km2 = ((grid.n - 2 * margin) * grid.res / 1000) ** 2
    to_wgs = Transformer.from_crs(grid.crs, 'EPSG:4326', always_xy=True)
    cands = []
    for rank, (sc, r, c) in enumerate(pk[:20], 1):
        x, y = grid.x0 + (c + 0.5) * grid.res, grid.y1 - (r + 0.5) * grid.res
        lon, lat = to_wgs.transform(x, y)
        cands.append({'source_event': event_id, 'rank': rank, 'score': sc, 'longitude': float(lon), 'latitude': float(lat),
                      'distance_to_source_event_m': float(np.hypot(r - r0, c - c0) * grid.res),
                      'is_known_event_hit': rank == hit_rank,
                      'before_ndvi': float(maps['before_ndvi_core_mean'][r, c]), 'd_ndvi_small_contrast': float(maps['d_ndvi_small_contrast'][r, c]),
                      'd_bsi_small_contrast': float(maps['d_bsi_small_contrast'][r, c]), 'd_ndwi_contrast': float(maps['d_ndwi_contrast'][r, c]),
                      'd_brightness_contrast': float(maps['d_brightness_contrast'][r, c]),
                      'before_date': sel['selected']['before_primary']['datetime'][:10], 'after_date': sel['selected']['after_primary']['datetime'][:10]})
    return {'event_group_id': event_id, 'peaks': len(pk), 'peaks_before_suppression': len(pk_all),
            'peaks_suppressed_known': len(suppressed), 'other_known_positives_in_patch': len(other_known),
            'hit_rank': hit_rank, 'hit_distance_m': hit_dist,
            'top_score': pk[0][0] if pk else None, 'centre_score': float(np.nan_to_num(s[r0, c0], nan=-1)),
            'centre_scorable': bool(np.isfinite(s[r0, c0])), **diag,
            'searched_km2': area_km2, 'false_peaks_above_hit': (hit_rank - 1) if hit_rank else len(pk),
            'score_map': s, 'peaks_list': pk[:10], 'candidates': cands}


def heuristic_type(c):
    """Coarse, heuristic false-positive category from the change signature (for triage only, not a label)."""
    if c['is_known_event_hit']:
        return 'known_event'
    if c['d_ndwi_contrast'] > 0.1:
        return 'water_or_wetness_change'
    if c['before_ndvi'] > 0.6 and c['d_ndvi_small_contrast'] < -0.15:
        return 'vegetation_loss_in_dense_vegetation (forestry or possible undocumented slide)'
    if 0.3 <= c['before_ndvi'] <= 0.6 and c['d_ndvi_small_contrast'] < -0.1:
        return 'vegetation_loss_in_grass_or_crop (harvest, mowing or possible slide)'
    if c['before_ndvi'] < 0.3:
        return 'change_on_bare_or_built_surface (construction, roads, quarry)'
    if c['d_brightness_contrast'] > 0.03:
        return 'local_brightening (bare soil, snow remnant, cloud edge)'
    return 'other_or_weak'


def training_frame(negatives='controls'):
    """Training table: the event groups (positives + matched controls) and, for 'controls_plus_random_landscape',
    the RANDOM_LANDSCAPE rows as additional label-0 samples (same independence unit as their positive)."""
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    if negatives == 'controls':
        return frame
    if negatives != 'controls_plus_random_landscape':
        raise ValueError(negatives)
    rl = pd.read_parquet(SAT_DATA / 'tables/random_landscape.parquet')
    rl = rl[rl['event_group_id'].isin(frame['event_group_id'])]
    return pd.concat([frame, rl], ignore_index=True)


def summarise(res, kind, cfg, negatives):
    hits = res['hit_rank'].notna()
    return {'model': kind, 'negatives': negatives, 'events': len(res), 'independence_units': int(res['independence_unit'].nunique()),
            'hit_radius_m': cfg['discovery']['hit_radius_m'], 'suppress_known_positives_m': cfg['discovery'].get('suppress_known_positives_m', 0),
            'searched_km2_per_event': float(res['searched_km2'].iloc[0]) if len(res) else None,
            'detected_any_rank': int(hits.sum()), 'detected_rank1': int((res['hit_rank'] == 1).sum()),
            'detected_top3': int((res['hit_rank'] <= 3).sum()), 'detected_top5': int((res['hit_rank'] <= 5).sum()),
            'median_hit_rank': float(res.loc[hits, 'hit_rank'].median()) if hits.any() else None,
            'median_hit_distance_m': float(res.loc[hits, 'hit_distance_m'].median()) if hits.any() else None,
            'false_peaks_above_hit_mean': float(res['false_peaks_above_hit'].mean()),
            'peaks_per_km2_mean': float((res['peaks'] / res['searched_km2']).mean()),
            'peaks_suppressed_known_total': int(res['peaks_suppressed_known'].sum()),
            'events_with_other_known_positive_in_patch': int((res['other_known_positives_in_patch'] > 0).sum()),
            'cloud_buffer_m': cfg['discovery'].get('cloud_buffer_m', 0),
            'buffer_masked_frac_mean': float(res['buffer_masked_frac'].mean()), 'buffer_masked_frac_median': float(res['buffer_masked_frac'].median()),
            'valid_frac_buffered_mean': float(res['valid_frac_buffered'].mean()),
            'scored_positions_frac_mean': float(res['scored_positions_frac'].mean()),
            'events_centre_not_scorable': int((~res['centre_scorable']).sum()),
            'detected_any_rank_centre_scorable': int((hits & res['centre_scorable']).sum()),
            'detected_rank1_centre_scorable': int(((res['hit_rank'] == 1) & res['centre_scorable']).sum()),
            'events_centre_scorable': int(res['centre_scorable'].sum()),
            'searched_km2_scorable_mean': float((res['searched_km2'] * res['scored_positions_frac']).mean()),
            'chance_rank1': 'a random peak order gives P(rank 1) = 1/peaks per event; mean 1/peaks = ' + f"{float((1 / res['peaks'].clip(lower=1)).mean()):.3f}",
            'per_event': res.drop(columns=['peaks_list']).astype(object).where(res.drop(columns=['peaks_list']).notna(), None).to_dict(orient='records')}


def run(kind='logistic_regression', score_threshold=0.0, negatives='controls'):
    """Held-out rediscovery for every eligible event. `negatives` selects the training table; outputs for the
    random-landscape variant carry the suffix `_random_landscape` so the two runs coexist."""
    cfg = config()
    frame = training_frame(negatives)
    cols = model_feature_names(feature_columns(frame))
    suffix = '' if negatives == 'controls' else '_random_landscape'
    known = events.known_positive_positions()
    results, maps_dir, candidates = [], guard(SAT_DATA / 'discovery'), []
    for unit, held in frame.groupby('independence_unit'):
        train = frame[frame['independence_unit'] != unit]
        if train['independence_unit'].nunique() < 2:
            continue
        model = make_model(kind, cfg).fit(train[cols].to_numpy(dtype=float), train['label'].to_numpy())
        for event_id in held[held['label'] == 1]['event_group_id']:
            r = rediscover_event(event_id, model, cols, cfg, known)
            np.save(maps_dir / f'{event_id}_score{suffix}.npy', r.pop('score_map'))
            candidates += r.pop('candidates')
            r['independence_unit'] = unit
            r['peaks_above_threshold'] = int(sum(1 for p in r['peaks_list'] if p[0] >= score_threshold))
            results.append(r)
            print(f"{event_id}: hit_rank={r['hit_rank']} dist={r['hit_distance_m']} peaks={r['peaks']} suppressed={r['peaks_suppressed_known']} top={r['top_score']}", flush=True)
    res = pd.DataFrame(results)
    summary = summarise(res, kind, cfg, negatives)
    guard(SAT_REPORT)
    write_json(SAT_REPORT / f'heldout_discovery_results{suffix}.json', {k: v for k, v in summary.items() if k != 'per_event'})
    inv = candidate_inventory(candidates, known, score_threshold, suffix)
    inv.to_parquet(SAT_DATA / f'tables/candidate_inventory{suffix}.parquet', index=False)
    inv.to_csv(SAT_REPORT / f'candidate_inventory{suffix}.csv', index=False)        # local only (coordinates)
    false_positive_report(inv, suffix)
    write_json(SAT_DATA / f'discovery/per_event{suffix}.json', summary['per_event'])
    if negatives == 'controls' and cfg['discovery'].get('cloud_buffer_m', 0):
        training_buffer_diagnostic(frame, cfg)
    return summary


def training_buffer_diagnostic(frame, cfg):
    """How the buffer would have changed the training windows: valid core/ring fractions of every training sample
    recomputed with the buffered mask from the cached patches (features themselves are NOT recomputed; the table and
    the baselines stay as built). Written to reports/satellite/training_buffer_diagnostic.json."""
    d = cfg['discovery']
    rows = []
    for _, s in frame.iterrows():
        sid = s['sample_id']
        meta = read_json(sample_dir(sid) / 'features.json')
        grid = Grid(**read_json(sample_dir(sid) / f"patches/{meta['before_item']}.json")['grid'])
        rb, sb, _ = fetch_patch(sid, {'id': meta['before_item']}, grid)
        ra, sa, _ = fetch_patch(sid, {'id': meta['after_item']}, grid)
        maps, scorable, diag = buffered_maps(rb, ra, sb, sa, grid.res, cfg)
        r, c = grid.centre_pixel()
        f = features_at({k: maps[k] for k in ('valid_core_frac', 'valid_ring_frac')}, r, c)
        rows.append({'sample_id': sid, 'label': int(s['label']), 'valid_core_frac_unbuffered': float(s['valid_core_frac']),
                     'valid_ring_frac_unbuffered': float(s['valid_ring_frac']), 'valid_core_frac_buffered': f['valid_core_frac'],
                     'valid_ring_frac_buffered': f['valid_ring_frac'], 'scorable': bool(scorable[r, c]), 'buffer_masked_frac_patch': diag['buffer_masked_frac']})
    t = pd.DataFrame(rows)
    out = {'cloud_buffer_m': d['cloud_buffer_m'], 'samples': int(len(t)),
           'note': 'training features were computed without the buffer; this records what the buffered mask would have removed from the training windows',
           'valid_core_frac_buffered': {'median': float(t['valid_core_frac_buffered'].median()), 'min': float(t['valid_core_frac_buffered'].min())},
           'valid_ring_frac_buffered': {'median': float(t['valid_ring_frac_buffered'].median()), 'min': float(t['valid_ring_frac_buffered'].min())},
           'samples_not_scorable_under_discovery_rule': int((~t['scorable']).sum()),
           'positives_not_scorable': int((~t['scorable'] & (t['label'] == 1)).sum()),
           'samples_with_any_pixel_removed_in_window': int(((t['valid_core_frac_buffered'] < t['valid_core_frac_unbuffered'] - 1e-9)
                                                              | (t['valid_ring_frac_buffered'] < t['valid_ring_frac_unbuffered'] - 1e-9)).sum()),
           'buffer_masked_frac_patch_mean': float(t['buffer_masked_frac_patch'].mean())}
    write_json(SAT_REPORT / 'training_buffer_diagnostic.json', out)
    t.to_parquet(SAT_DATA / 'tables/training_buffer_diagnostic.parquet', index=False)
    return out


def candidate_inventory(candidates, known, score_threshold, suffix=''):
    """Ranked, UNVERIFIED satellite candidates (score >= threshold, not the known event). Never auto-labelled.
    Distances are to all known V0.4 positives."""
    from preslide.terrain import GEOD
    rows = []
    klon, klat = known['longitude'].to_numpy(), known['latitude'].to_numpy()
    for c in candidates:
        if c['is_known_event_hit'] or c['score'] < score_threshold:   # score = log-odds
            continue
        d = GEOD.inv(np.full(len(klon), c['longitude']), np.full(len(klat), c['latitude']), klon, klat)[2] if len(klon) else []
        rows.append({'candidate_id': f"SATC_{c['source_event']}_{c['rank']:02d}", 'longitude': c['longitude'], 'latitude': c['latitude'],
                     'candidate_date_window': f"{c['before_date']}..{c['after_date']}", 'model_score': c['score'],
                     'source_search_event': c['source_event'], 'rank_in_search': c['rank'],
                     'nearest_known_event_distance_m': float(np.min(d)) if len(d) else None,
                     'heuristic_type': heuristic_type(c), 'before_ndvi': c['before_ndvi'], 'd_ndvi_small_contrast': c['d_ndvi_small_contrast'],
                     'd_bsi_small_contrast': c['d_bsi_small_contrast'], 'd_ndwi_contrast': c['d_ndwi_contrast'],
                     'before_image': f"data/satellite/samples/{c['source_event']}_positive/patches/", 'after_image': 'same directory',
                     'change_visualization': f"data/satellite/discovery/{c['source_event']}_score{suffix}.npy",
                     'label': 'satellite_detected_candidate', 'validation_status': 'UNVERIFIED'})
    return pd.DataFrame(rows)


def false_positive_report(inv, suffix=''):
    lines = ['# False-positive analysis (held-out discovery scans)', '',
             'Every peak above the score threshold that is not the known event is a candidate detection with '
             '`validation_status = UNVERIFIED`. Types below are coarse heuristics from the change signature '
             '(before-state NDVI, local NDVI/NDWI/brightness contrast) to guide manual inspection; they are not labels. '
             'Peaks within the suppression radius of another known V0.4 positive are not listed (documented events).', '',
             f'Candidates: {len(inv)}', '']
    if len(inv):
        lines += ['| heuristic type | count | median score | median distance to nearest known V0.4 positive (m) |', '|---|---:|---:|---:|']
        for t, g in inv.groupby('heuristic_type'):
            lines.append(f"| {t} | {len(g)} | {g['model_score'].median():.3f} | {g['nearest_known_event_distance_m'].median():.0f} |")
        near = inv[inv['nearest_known_event_distance_m'] < 500]
        lines += ['', f"{len(near)} candidates lie within 500 m of a known V0.4 positive other than the search centre "
                  '(possible additional source areas of the same storm, or the same slide at a different pixel).', '',
                  'Validation of the top candidates (persistence in `after_confirm`, visual review): `candidate_validation.md`.']
    (SAT_REPORT / f'false_positive_analysis{suffix}.md').write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
