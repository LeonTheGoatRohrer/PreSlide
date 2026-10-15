"""Retrospective discovery test: score every position of a held-out event's 2.56 km patch with a model that never saw
its independence unit, cluster the score map into candidates and ask whether the known event is rediscovered.

The search region is small (one patch, ~6.6 km²) and centred on the known event, so detection rates here are an
upper bound for an unknown-region scan; false positives per km² are the comparable quantity."""
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.ndimage import maximum_filter, label as cc_label

from ..common import write_json, read_json
from .baseline import make_model, feature_columns
from .features import feature_maps, model_feature_names
from .imagery import Grid, fetch_patch, sample_dir
from .paths import SAT_DATA, SAT_REPORT, guard, config


def score_map(model, maps, cols, margin_px):
    """Log-odds map (probabilities saturate at 1.0 and would create plateaus of tied maxima)."""
    n = next(iter(maps.values())).shape[0]
    X = np.stack([maps[c] for c in cols], axis=-1).reshape(-1, len(cols))
    out = np.full(X.shape[0], np.nan)
    ok = ~np.isnan(X).any(axis=1)
    if ok.any():
        out[ok] = model.decision_function(X[ok])      # unbounded log-odds: no saturation ties
    s = out.reshape(n, n)
    s[:margin_px, :] = s[-margin_px:, :] = s[:, :margin_px] = s[:, -margin_px:] = np.nan
    return s


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


def rediscover_event(event_id, model, cols, cfg):
    sid = f'{event_id}_positive'
    sel = read_json(sample_dir(sid) / 'selection.json')
    grid = Grid(**sel['grid'])
    rb, sb, _ = fetch_patch(sid, sel['items']['before_primary'], grid)
    ra, sa, _ = fetch_patch(sid, sel['items']['after_primary'], grid)
    maps = feature_maps(rb, ra, sb, sa, grid.res)
    margin = int(round(cfg['patch']['medium_m'] / grid.res / 2))
    s = score_map(model, maps, cols, margin)
    d = cfg['discovery']
    pk = peaks(s, int(round(d['min_peak_distance_m'] / grid.res / 2)))
    r0, c0 = grid.centre_pixel()
    hit_px = d['hit_radius_m'] / grid.res
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
    return {'event_group_id': event_id, 'peaks': len(pk), 'hit_rank': hit_rank, 'hit_distance_m': hit_dist,
            'top_score': pk[0][0] if pk else None, 'centre_score': float(np.nan_to_num(s[r0, c0], nan=-1)),
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


def run(kind='logistic_regression', score_threshold=0.0):
    cfg = config()
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    cols = model_feature_names(feature_columns(frame))
    results, maps_dir, candidates = [], guard(SAT_DATA / 'discovery'), []
    known = frame[frame['label'] == 1][['event_group_id', 'longitude', 'latitude']]
    for unit, held in frame.groupby('independence_unit'):
        train = frame[frame['independence_unit'] != unit]
        if train['independence_unit'].nunique() < 2:
            continue
        model = make_model(kind, cfg).fit(train[cols].to_numpy(dtype=float), train['label'].to_numpy())
        for event_id in held[held['label'] == 1]['event_group_id']:
            r = rediscover_event(event_id, model, cols, cfg)
            np.save(maps_dir / f'{event_id}_score.npy', r.pop('score_map'))
            candidates += r.pop('candidates')
            r['independence_unit'] = unit
            r['peaks_above_threshold'] = int(sum(1 for p in r['peaks_list'] if p[0] >= score_threshold))
            results.append(r)
            print(f"{event_id}: hit_rank={r['hit_rank']} dist={r['hit_distance_m']} peaks={r['peaks']} top={r['top_score']}", flush=True)
    res = pd.DataFrame(results)
    hits = res['hit_rank'].notna()
    summary = {'model': kind, 'events': len(res), 'independence_units': int(res['independence_unit'].nunique()),
               'hit_radius_m': cfg['discovery']['hit_radius_m'], 'searched_km2_per_event': float(res['searched_km2'].iloc[0]) if len(res) else None,
               'detected_any_rank': int(hits.sum()), 'detected_rank1': int((res['hit_rank'] == 1).sum()),
               'detected_top3': int((res['hit_rank'] <= 3).sum()), 'detected_top5': int((res['hit_rank'] <= 5).sum()),
               'median_hit_rank': float(res.loc[hits, 'hit_rank'].median()) if hits.any() else None,
               'median_hit_distance_m': float(res.loc[hits, 'hit_distance_m'].median()) if hits.any() else None,
               'false_peaks_above_hit_mean': float(res['false_peaks_above_hit'].mean()),
               'peaks_per_km2_mean': float((res['peaks'] / res['searched_km2']).mean()),
               'chance_rank1': 'a random peak order gives P(rank 1) = 1/peaks per event; mean 1/peaks = ' + f"{float((1 / res['peaks'].clip(lower=1)).mean()):.3f}",
               'per_event': res.drop(columns=['peaks_list']).astype(object).where(res.drop(columns=['peaks_list']).notna(), None).to_dict(orient='records')}
    guard(SAT_REPORT)
    write_json(SAT_REPORT / 'heldout_discovery_results.json', {k: v for k, v in summary.items() if k != 'per_event'})
    inv = candidate_inventory(candidates, known, score_threshold)
    inv.to_parquet(SAT_DATA / 'tables/candidate_inventory.parquet', index=False)
    inv.to_csv(SAT_REPORT / 'candidate_inventory.csv', index=False)        # local only (coordinates)
    false_positive_report(inv)
    write_json(SAT_DATA / 'discovery/per_event.json', summary['per_event'])
    return summary


def candidate_inventory(candidates, known, score_threshold):
    """Ranked, UNVERIFIED satellite candidates (score >= threshold, not the known event). Never auto-labelled."""
    from preslide.terrain import GEOD
    rows = []
    for c in candidates:
        if c['is_known_event_hit'] or c['score'] < score_threshold:   # score = log-odds
            continue
        d = [GEOD.inv(c['longitude'], c['latitude'], lon, lat)[2] for lon, lat in zip(known['longitude'], known['latitude'])]
        rows.append({'candidate_id': f"SATC_{c['source_event']}_{c['rank']:02d}", 'longitude': c['longitude'], 'latitude': c['latitude'],
                     'candidate_date_window': f"{c['before_date']}..{c['after_date']}", 'model_score': c['score'],
                     'source_search_event': c['source_event'], 'rank_in_search': c['rank'],
                     'nearest_known_event_distance_m': float(min(d)) if d else None,
                     'heuristic_type': heuristic_type(c), 'before_ndvi': c['before_ndvi'], 'd_ndvi_small_contrast': c['d_ndvi_small_contrast'],
                     'd_bsi_small_contrast': c['d_bsi_small_contrast'], 'd_ndwi_contrast': c['d_ndwi_contrast'],
                     'before_image': f"data/satellite/samples/{c['source_event']}_positive/patches/", 'after_image': 'same directory',
                     'change_visualization': f"data/satellite/discovery/{c['source_event']}_score.npy",
                     'label': 'satellite_detected_candidate', 'validation_status': 'UNVERIFIED'})
    return pd.DataFrame(rows)


def false_positive_report(inv):
    lines = ['# False-positive analysis (held-out discovery scans)', '',
             'Every peak above the score threshold that is not the known event is a candidate detection with '
             '`validation_status = UNVERIFIED`. Types below are coarse heuristics from the change signature '
             '(before-state NDVI, local NDVI/NDWI/brightness contrast) to guide manual inspection; they are not labels.', '',
             f'Candidates: {len(inv)}', '']
    if len(inv):
        lines += ['| heuristic type | count | median score | median distance to nearest known event (m) |', '|---|---:|---:|---:|']
        for t, g in inv.groupby('heuristic_type'):
            lines.append(f"| {t} | {len(g)} | {g['model_score'].median():.3f} | {g['nearest_known_event_distance_m'].median():.0f} |")
        near = inv[inv['nearest_known_event_distance_m'] < 500]
        lines += ['', f"{len(near)} candidates lie within 500 m of a known inventory event other than the search centre "
                  '(possible additional source areas of the same storm, or the same slide at a different pixel).', '',
                  'Next validation steps (none performed automatically): inspect `after_confirm` imagery for persistence, '
                  'check Sentinel-1 backscatter change, compare with later inventory updates and orthophotos.']
    (SAT_REPORT / 'false_positive_analysis.md').write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
