"""Candidate validation: the top UNVERIFIED satellite candidates, persistence of their change in the later
`after_confirm` acquisition, and contact sheets for visual review.

Nothing here promotes a candidate. A status other than UNVERIFIED needs stated independent evidence (persistence in
a later acquisition plus a visual review note), assigned by `assign_status`. The Pipeline A inventory is never written
(the write guard refuses every path outside data/satellite, models/satellite, reports/satellite)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from pyproj import Transformer

from ..common import read_json, write_json
from . import events
from .baseline import make_model, feature_columns
from .contact import stretch_rgb
from .discovery import score_map, peaks
from .features import feature_maps, model_feature_names, features_at, indices, valid_mask
from .imagery import Grid, fetch_patch, sample_dir
from .paths import SAT_DATA, SAT_REPORT, guard, config

REVIEW_VERDICTS = ('slide_like', 'transient_artifact', 'non_slide_land_use', 'water_change', 'ambiguous')


def _geod_min_distance_m(lon, lat, lons, lats):
    from preslide.terrain import GEOD
    if len(lons) == 0:
        return np.nan
    return float(np.min(GEOD.inv(np.full(len(lons), lon), np.full(len(lons), lat), np.asarray(lons), np.asarray(lats))[2]))


def physical_candidates(inv, known, min_sep_m, exclude_within_known_m):
    """Collapse detections of the same location seen from overlapping search patches into one physical candidate
    (greedy by score; later detections within `min_sep_m` become aliases) and drop everything within
    `exclude_within_known_m` of any known positive. Returns the ranked physical candidates."""
    inv = inv.copy()
    inv['nearest_v04_positive_m'] = [_geod_min_distance_m(lon, lat, known['longitude'], known['latitude'])
                                     for lon, lat in zip(inv['longitude'], inv['latitude'])]
    near_known = inv['nearest_v04_positive_m'] <= exclude_within_known_m
    ranked = inv[~near_known].sort_values(['model_score', 'candidate_id'], ascending=[False, True])
    kept, kept_lon, kept_lat, aliases = [], [], [], {}
    for _, row in ranked.iterrows():
        if kept:
            from preslide.terrain import GEOD
            d = GEOD.inv(np.full(len(kept), row['longitude']), np.full(len(kept), row['latitude']), np.array(kept_lon), np.array(kept_lat))[2]
            j = int(np.argmin(d))
            if d[j] < min_sep_m:
                aliases[kept[j]['candidate_id']].append(row['candidate_id'])
                continue
        kept.append(row)
        kept_lon.append(row['longitude']); kept_lat.append(row['latitude'])
        aliases[row['candidate_id']] = []
    out = pd.DataFrame(kept).reset_index(drop=True)
    out['aliases'] = [aliases[c] for c in out['candidate_id']]
    out['n_detections'] = 1 + out['aliases'].str.len()
    out['excluded_near_known_positive'] = int(near_known.sum())
    return out


def main_contrast_feature(f):
    """The change feature that carries a candidate's signature (declared before the confirm pair is looked at)."""
    if f['d_ndwi_contrast'] > 0.1:
        return 'd_ndwi_contrast'
    if f['d_ndvi_small_contrast'] < -0.1:
        return 'd_ndvi_small_contrast'
    if f['d_bsi_small_contrast'] > 0.1:
        return 'd_bsi_small_contrast'
    return 'd_brightness_contrast'


def persistence_rule(primary, confirm, score_confirm, vcfg):
    """Pure rule: the change persists when the confirm pair still scores as change (log-odds > 0) and the main
    contrast feature keeps its sign with at least `min_retained_contrast` of its primary magnitude.
    Returns (assessable, persists, main_feature, retained_fraction)."""
    assessable = (confirm['valid_core_frac'] >= vcfg['min_valid_core_frac'] and confirm['valid_ring_frac'] >= vcfg['min_valid_ring_frac']
                  and np.isfinite(score_confirm))
    main = main_contrast_feature(primary)
    p, c = primary[main], confirm[main]
    retained = float(c / p) if np.isfinite(p) and np.isfinite(c) and p != 0 else np.nan
    persists = bool(assessable and score_confirm > 0 and np.isfinite(retained) and retained >= vcfg['min_retained_contrast'])
    return bool(assessable), persists, main, retained


def assign_status(persistence_assessable, persists, review_verdict, review_note):
    """LIKELY / REJECTED only with stated independent evidence; everything else stays UNVERIFIED.

    LIKELY: change persists in the later acquisition AND the reviewer saw a slide-like scar.
    REJECTED: the reviewer named a non-slide cause (land use, water) or a transient artefact that did not persist.
    A verdict without a written note never changes the status."""
    if not review_note or review_verdict not in REVIEW_VERDICTS:
        return 'UNVERIFIED'
    if persistence_assessable and persists and review_verdict == 'slide_like':
        return 'LIKELY'
    if review_verdict in ('non_slide_land_use', 'water_change'):
        return 'REJECTED'
    if review_verdict == 'transient_artifact' and persistence_assessable and not persists:
        return 'REJECTED'
    return 'UNVERIFIED'


def _held_out_models(frame, cols, cfg, kind='logistic_regression'):
    models = {}
    for unit in frame['independence_unit'].unique():
        train = frame[frame['independence_unit'] != unit]
        models[unit] = make_model(kind, cfg).fit(train[cols].to_numpy(dtype=float), train['label'].to_numpy())
    return models


def _pixel_of(grid, lon, lat):
    x, y = Transformer.from_crs('EPSG:4326', grid.crs, always_xy=True).transform(lon, lat)
    return int((grid.y1 - y) // grid.res), int((x - grid.x0) // grid.res)


def persistence_record(cand, model, cols, cfg):
    """Recompute the change features on (before_primary, after_confirm) at the candidate pixel and apply the rule."""
    vcfg = cfg['validation']
    event = cand['source_search_event']
    sid = f'{event}_positive'
    sel = read_json(sample_dir(sid) / 'selection.json')
    grid = Grid(**sel['grid'])
    r, c = _pixel_of(grid, cand['longitude'], cand['latitude'])
    rec = {'candidate_id': cand['candidate_id'], 'row': r, 'col': c, 'persistence_assessable': False, 'persists': False,
           'confirm_date': None, 'confirm_days_from_event': None, 'confirm_days_after_primary': None}
    if 'after_confirm' not in sel['items']:
        rec['reason'] = 'no_after_confirm_acquisition'
        return rec
    rb, sb, _ = fetch_patch(sid, sel['items']['before_primary'], grid)
    ra, sa, _ = fetch_patch(sid, sel['items']['after_primary'], grid)
    rc, sc, mc = fetch_patch(sid, sel['items']['after_confirm'], grid)
    margin = int(round(cfg['patch']['medium_m'] / grid.res / 2))
    maps_p, maps_c = feature_maps(rb, ra, sb, sa, grid.res), feature_maps(rb, rc, sb, sc, grid.res)
    f_p, f_c = features_at(maps_p, r, c), features_at(maps_c, r, c)
    s_p, s_c = score_map(model, maps_p, cols, margin), score_map(model, maps_c, cols, margin)
    score_p, score_c = float(s_p[r, c]), float(s_c[r, c])
    assessable, persists, main, retained = persistence_rule(f_p, f_c, score_c, vcfg)
    min_px = int(round(cfg['discovery']['min_peak_distance_m'] / grid.res / 2))
    hit_px = cfg['discovery']['hit_radius_m'] / grid.res
    confirm_peak_rank, confirm_peak_dist = None, None
    for rank, (sc_, rr, cc) in enumerate(peaks(s_c, min_px), 1):
        if np.hypot(rr - r, cc - c) <= hit_px:
            confirm_peak_rank, confirm_peak_dist = rank, float(np.hypot(rr - r, cc - c) * grid.res)
            break
    sa_, sc_sel = sel['selected']['after_primary'], sel['selected']['after_confirm']
    rec.update({'persistence_assessable': assessable, 'persists': persists, 'main_contrast_feature': main,
                'retained_fraction': retained, 'score_primary': score_p, 'score_confirm': score_c,
                'confirm_valid_core_frac': f_c['valid_core_frac'], 'confirm_valid_ring_frac': f_c['valid_ring_frac'],
                'confirm_peak_rank_within_hit_radius': confirm_peak_rank, 'confirm_peak_distance_m': confirm_peak_dist,
                'confirm_date': sc_sel['datetime'][:10], 'confirm_days_from_event': sc_sel['days_from_event'],
                'confirm_days_after_primary': sc_sel['days_from_event'] - sa_['days_from_event'],
                'confirm_item': mc['item_id'],
                **{f'primary_{k}': f_p[k] for k in ('d_ndvi_small_contrast', 'd_bsi_small_contrast', 'd_ndwi_contrast', 'd_brightness_contrast', 'before_ndvi_core_mean')},
                **{f'confirm_{k}': f_c[k] for k in ('d_ndvi_small_contrast', 'd_bsi_small_contrast', 'd_ndwi_contrast', 'd_brightness_contrast')}})
    return rec


def _crop(a, r, c, half):
    return a[..., r - half:r + half, c - half:c + half]


def candidate_contact_sheet(rows, labels, out_path, extent_m=640):
    """Five panels per candidate: RGB before_primary, after_primary, after_confirm; dNDVI primary and confirm.
    Yellow box = 120 m small window around the candidate pixel."""
    cfg = config()
    small_m = cfg['patch']['small_m']
    n = len(rows)
    fig, axes = plt.subplots(n, 5, figsize=(16, 3.4 * n), squeeze=False)
    for i, (cand, lab) in enumerate(zip(rows, labels)):
        sid = f"{cand['source_search_event']}_positive"
        sel = read_json(sample_dir(sid) / 'selection.json')
        grid = Grid(**sel['grid'])
        r, c = _pixel_of(grid, cand['longitude'], cand['latitude'])
        half = int(round(extent_m / grid.res / 2))
        rb, sb, _ = fetch_patch(sid, sel['items']['before_primary'], grid)
        ra, sa, _ = fetch_patch(sid, sel['items']['after_primary'], grid)
        rc, sc, _ = fetch_patch(sid, sel['items']['after_confirm'], grid)
        rgb_b, lo, hi = stretch_rgb(_crop(rb, r, c, half))
        rgb_a, _, _ = stretch_rgb(_crop(ra, r, c, half), lo, hi)
        rgb_c, _, _ = stretch_rgb(_crop(rc, r, c, half), lo, hi)
        ib = indices(rb)['ndvi']
        dn_p = np.where(valid_mask(rb, sb) & valid_mask(ra, sa), indices(ra)['ndvi'] - ib, np.nan)
        dn_c = np.where(valid_mask(rb, sb) & valid_mask(rc, sc), indices(rc)['ndvi'] - ib, np.nan)
        px = rgb_b.shape[0]
        hs = small_m / grid.res / 2
        panels = (rgb_b, rgb_a, rgb_c, _crop(dn_p, r, c, half), _crop(dn_c, r, c, half))
        for ax, img, kind in zip(axes[i], panels, ('rgb', 'rgb', 'rgb', 'delta', 'delta')):
            if kind == 'delta':
                ax.imshow(img, cmap='RdBu', vmin=-0.5, vmax=0.5)
            else:
                ax.imshow(img)
            ax.add_patch(Rectangle((px / 2 - hs, px / 2 - hs), 2 * hs, 2 * hs, fill=False, ec='yellow', lw=1.2))
            ax.plot(px / 2, px / 2, marker='+', color='yellow', ms=9, mew=1.0)
            ax.set_xticks([]); ax.set_yticks([])
        s = sel['selected']
        axes[i][0].set_title(f"{lab} · vorher {s['before_primary']['datetime'][:10]} ({s['before_primary']['days_from_event']} d)", fontsize=8, loc='left')
        axes[i][1].set_title(f"nachher {s['after_primary']['datetime'][:10]} (+{s['after_primary']['days_from_event']} d) · Score {cand['model_score']:.1f}", fontsize=8, loc='left')
        axes[i][2].set_title(f"Bestätigung {s['after_confirm']['datetime'][:10]} (+{s['after_confirm']['days_from_event']} d) · Score {cand.get('score_confirm', float('nan')):.1f}", fontsize=8, loc='left')
        axes[i][3].set_title(f'ΔNDVI nachher − vorher · Ausschnitt {extent_m} m', fontsize=8, loc='left')
        axes[i][4].set_title(f"ΔNDVI Bestätigung − vorher · {cand['heuristic_type'].split(' (')[0]}", fontsize=8, loc='left')
    fig.suptitle('PreSlide Pipeline B – UNVERIFIED Kandidaten (Kreuz = Kandidatenpixel, Kasten = 120 m Fenster); keine Ereignislabels', fontsize=10)
    fig.tight_layout()
    guard(out_path.parent)
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path


def run(top_n=None):
    """Select the top candidates, fetch their after_confirm patches, test persistence and draw contact sheets.
    Writes the local table (ids, coordinates) and the committed review template (anonymised labels)."""
    cfg = config()
    vcfg = cfg['validation']
    top_n = top_n or vcfg['top_n']
    inv = pd.read_parquet(SAT_DATA / 'tables/candidate_inventory.parquet')
    inv = inv[inv['validation_status'] == 'UNVERIFIED']
    known = events.known_positive_positions()
    phys = physical_candidates(inv, known, vcfg['dedup_m'], vcfg['exclude_within_known_m'])
    top = phys.head(top_n).copy()
    top['validation_label'] = [f'KAND-{i + 1:02d}' for i in range(len(top))]
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    cols = model_feature_names(feature_columns(frame))
    unit_of = dict(zip(frame['event_group_id'], frame['independence_unit']))
    models = _held_out_models(frame, cols, cfg)
    recs = []
    for _, cand in top.iterrows():
        rec = persistence_record(cand, models[unit_of[cand['source_search_event']]], cols, cfg)
        print(cand['validation_label'], cand['candidate_id'], f"score {cand['model_score']:.1f} -> confirm {rec.get('score_confirm')}",
              'persists' if rec['persists'] else ('not persistent' if rec['persistence_assessable'] else 'not assessable'), flush=True)
        recs.append(rec)
    top = top.merge(pd.DataFrame(recs), on='candidate_id')
    out_dir = guard(SAT_DATA / 'tables')
    top.to_parquet(out_dir / 'candidate_validation.parquet', index=False)       # local only: ids and coordinates
    sheets = []
    rows = top.to_dict(orient='records')
    per_sheet = 6
    for k in range(0, len(rows), per_sheet):
        chunk = rows[k:k + per_sheet]
        p = candidate_contact_sheet(chunk, [c['validation_label'] for c in chunk],
                                    guard(SAT_REPORT / 'contact_sheets') / f'candidates_{k // per_sheet + 1:02d}.png')
        sheets.append(p.name)
        print('wrote', p, flush=True)
    summary = {'top_n': top_n, 'candidates_considered': int(len(inv)), 'physical_candidates': int(len(phys)),
               'excluded_within_known_positive_m': vcfg['exclude_within_known_m'],
               'excluded_near_known_positive': int(phys['excluded_near_known_positive'].iloc[0]) if len(phys) else 0,
               'dedup_m': vcfg['dedup_m'], 'rule': vcfg, 'sheets': sheets,
               'persistence': {'assessable': int(top['persistence_assessable'].sum()), 'persists': int(top['persists'].sum())}}
    write_json(SAT_REPORT / 'candidate_validation_summary.json', summary)
    return top, summary


def review_template_path():
    return SAT_REPORT / 'candidate_review.json'


def apply_review(top=None):
    """Join the written review (verdict + note per label) with the persistence table and assign statuses.
    The review file is written by a person; missing entries leave the candidate UNVERIFIED."""
    top = pd.read_parquet(SAT_DATA / 'tables/candidate_validation.parquet') if top is None else top
    review = read_json(review_template_path()) if review_template_path().exists() else {'reviews': {}}
    statuses, verdicts, notes = [], [], []
    for _, row in top.iterrows():
        rv = review['reviews'].get(row['validation_label'], {})
        verdict, note = rv.get('verdict', ''), rv.get('note', '')
        statuses.append(assign_status(bool(row['persistence_assessable']), bool(row['persists']), verdict, note))
        verdicts.append(verdict); notes.append(note)
    top = top.assign(review_verdict=verdicts, review_note=notes, validation_status=statuses)
    top.to_parquet(SAT_DATA / 'tables/candidate_validation.parquet', index=False)
    # Status also recorded in the local inventory copy (never in any Pipeline A table).
    inv = pd.read_parquet(SAT_DATA / 'tables/candidate_inventory.parquet')
    status_of = {}
    for _, row in top.iterrows():
        for cid in [row['candidate_id'], *list(row['aliases'])]:
            status_of[cid] = row['validation_status']
    inv['validation_status'] = [status_of.get(c, s) for c, s in zip(inv['candidate_id'], inv['validation_status'])]
    inv.to_parquet(SAT_DATA / 'tables/candidate_inventory.parquet', index=False)
    inv.to_csv(SAT_REPORT / 'candidate_inventory.csv', index=False)
    return top


def _f(x, nd=2):
    return '—' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.{nd}f}'


def write_report(top):
    """reports/satellite/candidate_validation.md: anonymised labels only (ids and coordinates stay local)."""
    cfg = config()
    vcfg = cfg['validation']
    summary = read_json(SAT_REPORT / 'candidate_validation_summary.json')
    counts = top['validation_status'].value_counts().to_dict()
    assessable = top[top['persistence_assessable']]
    lines = ['# Candidate validation (Pipeline B, satellite-0.2)', '',
             f"Top {len(top)} physical candidates of the held-out discovery scan by detector score, after removing every peak within "
             f"{vcfg['exclude_within_known_m']} m of any of the 423 known V0.4 positives and collapsing detections of the same location from "
             f"overlapping search patches (within {vcfg['dedup_m']} m) into one candidate. "
             f"{summary['candidates_considered']} UNVERIFIED detections → {summary['physical_candidates']} physical candidates "
             f"({summary['excluded_near_known_positive']} detections dropped near known positives).", '',
             '## Persistence test', '',
             'For every candidate the same change features are recomputed on the pair (before_primary, after_confirm), where after_confirm is the '
             f"earliest acquisition usable at the source event at least {cfg['eligibility']['confirm_min_gap_days']} days after after_primary. "
             'The held-out detector of the candidate\'s independence unit (never trained on it) scores both pairs at the candidate pixel. '
             'Rule (config/satellite.json, validation.rule): ' + vcfg['rule'], '',
             '| quantity | value |', '|---|---:|',
             f"| candidates | {len(top)} |", f"| persistence assessable (confirm pair valid at the candidate) | {len(assessable)} |",
             f"| not assessable (cloud, snow or nodata at the candidate in after_confirm) | {int((~top['persistence_assessable']).sum())} |",
             f"| change persists | {int(top['persists'].sum())} |",
             f"| change does not persist | {int((assessable['persists'] == False).sum())} |",
             f"| median days event → after_confirm | {_f(top['confirm_days_from_event'].median(), 0)} |", '',
             '## Status', '',
             'LIKELY needs persistence AND a slide-like scar in the visual review; REJECTED needs a named non-slide cause (land use, water) '
             'or a transient artefact that did not persist; everything else stays UNVERIFIED. No candidate is added to any inventory or to Pipeline A.', '',
             '| status | count |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in sorted(counts.items())] + ['',
             '## Candidates', '',
             'Columns: heuristic type from the change signature (triage only); d(known) = distance to the nearest known V0.4 positive; n = detections of this location '
             'from overlapping patches; score = held-out log-odds on the primary pair / on the confirm pair; retained = confirm/primary ratio of the main contrast feature; '
             'confirm peak = rank of a confirm-pair peak within 160 m (— none).', '',
             '| label | type | d(known) m | n | days (before / after / confirm) | score primary | score confirm | main feature | retained | assessable | persists | confirm peak | verdict | status | note |',
             '|---|---|---:|---:|---|---:|---:|---|---:|---|---|---:|---|---|---|']
    for _, r in top.iterrows():
        days = f"{r['candidate_date_window']} / +{r['confirm_days_from_event']} d" if r['confirm_days_from_event'] is not None else r['candidate_date_window']
        lines.append(f"| {r['validation_label']} | {r['heuristic_type'].split(' (')[0]} | {r['nearest_v04_positive_m']:.0f} | {r['n_detections']} | {days} | "
                     f"{_f(r['model_score'], 1)} | {_f(r.get('score_confirm'), 1)} | {r.get('main_contrast_feature', '—')} | {_f(r.get('retained_fraction'))} | "
                     f"{'yes' if r['persistence_assessable'] else 'no'} | {'yes' if r['persists'] else 'no'} | "
                     f"{'—' if r.get('confirm_peak_rank_within_hit_radius') is None or (isinstance(r.get('confirm_peak_rank_within_hit_radius'), float) and np.isnan(r.get('confirm_peak_rank_within_hit_radius'))) else int(r['confirm_peak_rank_within_hit_radius'])} | "
                     f"{r.get('review_verdict') or '—'} | {r['validation_status']} | {r.get('review_note') or ''} |")
    cp = SAT_REPORT / 'cloud_proximity.json'
    if cp.exists():
        c = read_json(cp)
        lines += ['', '## Cloud proximity of the candidates', '',
                  'Distance from each candidate pixel to the nearest cloud-like scene-classification pixel (SCL 2, 3, 7, 8, 9, 10, 11) in before_primary '
                  'or after_primary (`cloud_proximity.json`). Pairs are screened for cloud and snow only in the 960 m window around the source event; '
                  'the outer part of the 2.56 km patch is recorded but not required, and Sen2Cor misses thin cloud and haze edges.', '',
                  '| set | n | within 100 m of a cloud-like pixel | within 300 m |', '|---|---:|---:|---:|',
                  f"| all candidates | {c['candidate']['n']} | {c['candidate']['within_100_m']:.0%} | {c['candidate']['within_300_m']:.0%} |",
                  f"| top 30 by score | 30 | {c['top_30_candidates']['within_100_m']:.0%} | {c['top_30_candidates']['within_300_m']:.0%} |",
                  f"| top 100 by score | 100 | {c['top_100_candidates']['within_100_m']:.0%} | {c['top_100_candidates']['within_300_m']:.0%} |",
                  f"| top 300 by score | 300 | {c['top_300_candidates']['within_100_m']:.0%} | {c['top_300_candidates']['within_300_m']:.0%} |",
                  f"| rank-1 candidates per search | {c['rank1_candidates']['n']} | {c['rank1_candidates']['within_100_m']:.0%} | {c['rank1_candidates']['within_300_m']:.0%} |",
                  f"| rediscovered known events (reference) | {c['known_event_hit']['n']} | {c['known_event_hit']['within_100_m']:.0%} | {c['known_event_hit']['within_300_m']:.0%} |", '',
                  'The score ranking is dominated by cloud and haze edges: the detector was trained on cloud-free windows and extrapolates to extreme log-odds '
                  'at unmasked cloud borders. Candidate ranking by raw score is therefore not usable until the discovery scan screens the whole patch '
                  '(or masks a buffer around every cloud-like pixel); this is the first change for the next Pipeline B version, registered before re-running.']
    lines += ['', '## Visual review', '',
              f"Contact sheets `reports/satellite/contact_sheets/candidates_01..{len(summary['sheets']):02d}.png`: RGB before_primary, after_primary, after_confirm and "
              'ΔNDVI for both pairs, 640 m window, cross = candidate pixel, box = 120 m small window. The reviewer\'s verdicts and notes are in '
              '`reports/satellite/candidate_review.json` (one entry per label; a verdict without a note changes nothing).', '',
              '## Interpretation and limits', '',
              '- The top of the score list is dominated by extreme log-odds (the logistic detector extrapolates far outside its training range for water, '
              'river-bank and harvest changes); a high score is not evidence of a landslide.',
              '- Persistence separates transient changes (mowing, harvest, moisture, cloud edge) from lasting surface change; a lasting change can still be a '
              'clear-cut, construction or a river-bed shift, which only the visual review and later orthophotos or inventories can resolve.',
              '- after_confirm was screened for cloud and snow at the source event, not at the candidate; candidates with cloud at their own position are '
              'reported as not assessable rather than scored.',
              '- Candidates are UNVERIFIED by default; LIKELY is a hypothesis for field or orthophoto checking, not a documented event, and nothing here is '
              'written to the Pipeline A event tables (write guard).']
    (SAT_REPORT / 'candidate_validation.md').write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
    return SAT_REPORT / 'candidate_validation.md'


def cloud_proximity_m(scl, row, col, res_m, classes=(2, 3, 7, 8, 9, 10, 11)):
    """Distance (m) from (row, col) to the nearest pixel of a cloud-like SCL class (cloud, shadow, cirrus, snow,
    unclassified, dark area). inf when the patch has none."""
    from scipy.ndimage import distance_transform_edt
    bad = np.isin(scl, list(classes))
    if not bad.any():
        return float('inf')
    d = distance_transform_edt(~bad)
    return float(d[row, col] * res_m)


def cloud_proximity_report(radius_m=(100, 300)):
    """For every candidate of the suppressed inventory and for every rediscovered known event: distance to the
    nearest cloud-like SCL pixel in before_primary or after_primary. Written to reports/satellite/cloud_proximity.json."""
    cfg = config()
    inv = pd.read_parquet(SAT_DATA / 'tables/candidate_inventory.parquet')
    per_event = read_json(SAT_DATA / 'discovery/per_event.json')
    cache, rows = {}, []

    def scls(event):
        if event not in cache:
            sid = f'{event}_positive'
            sel = read_json(sample_dir(sid) / 'selection.json')
            grid = Grid(**sel['grid'])
            _, sb, _ = fetch_patch(sid, sel['items']['before_primary'], grid)
            _, sa, _ = fetch_patch(sid, sel['items']['after_primary'], grid)
            cache[event] = (grid, sb, sa)
        return cache[event]

    for _, c in inv.iterrows():
        grid, sb, sa = scls(c['source_search_event'])
        r, col = _pixel_of(grid, c['longitude'], c['latitude'])
        rows.append({'kind': 'candidate', 'score': c['model_score'], 'rank': c['rank_in_search'],
                     'cloud_m': min(cloud_proximity_m(sb, r, col, grid.res), cloud_proximity_m(sa, r, col, grid.res))})
    for e in per_event:
        if e['hit_rank'] is not None:
            grid, sb, sa = scls(e['event_group_id'])
            r, col = grid.centre_pixel()
            rows.append({'kind': 'known_event_hit', 'score': e['centre_score'], 'rank': e['hit_rank'],
                         'cloud_m': min(cloud_proximity_m(sb, r, col, grid.res), cloud_proximity_m(sa, r, col, grid.res))})
    t = pd.DataFrame(rows)
    out = {'classes': 'SCL 2 dark area, 3 cloud shadow, 7 unclassified, 8/9 cloud, 10 cirrus, 11 snow in before_primary or after_primary',
           'note': 'pairs are screened for cloud/snow only within the 960 m window around the source event; the outer patch is recorded, not required'}
    for kind, g in t.groupby('kind'):
        out[kind] = {'n': int(len(g)), 'median_cloud_m': float(g['cloud_m'].replace(np.inf, np.nan).median()),
                     **{f'within_{r}_m': float((g['cloud_m'] <= r).mean()) for r in radius_m}}
    top = t[t['kind'] == 'candidate'].sort_values('score', ascending=False)
    for n in (30, 100, 300):
        out[f'top_{n}_candidates'] = {f'within_{r}_m': float((top.head(n)['cloud_m'] <= r).mean()) for r in radius_m}
    r1 = t[(t['kind'] == 'candidate') & (t['rank'] == 1)]
    out['rank1_candidates'] = {'n': int(len(r1)), **{f'within_{r}_m': float((r1['cloud_m'] <= r).mean()) for r in radius_m}}
    write_json(SAT_REPORT / 'cloud_proximity.json', out)
    return out
