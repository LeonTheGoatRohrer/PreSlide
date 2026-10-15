"""Reports for Pipeline B (reports/satellite/). Record-level tables with coordinates and source ids stay local."""
import json

import numpy as np
import pandas as pd

from ..common import read_json
from .paths import SAT_DATA, SAT_REPORT, guard, config

LOCAL_ONLY = ('eligibility_report.csv', 'event_imagery_index.csv', 'candidate_inventory.csv')


def _fmt(x, nd=3):
    return '—' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.{nd}f}'


def write_reports():
    cfg = config()
    out = guard(SAT_REPORT)
    elig = pd.read_parquet(SAT_DATA / 'tables/eligibility.parquet')
    elig.to_csv(out / 'eligibility_report.csv', index=False)
    data_path = SAT_DATA / 'tables/dataset.parquet'
    data = pd.read_parquet(data_path) if data_path.exists() else None
    lines = ['# Satellite dataset summary (Pipeline B)', '',
             f"Configuration `config/satellite.json` version {cfg['version']}. Source positives: V0.4 run (read only). "
             'Pipeline B uses post-event imagery and is isolated from the precursor model (Pipeline A); see tests/test_satellite.py.', '',
             '## Eligibility', '',
             f'| Events screened (2018+ positives) | {len(elig)} |', '|---|---:|',
             f"| usable (before + after pair found) | {int(elig['usable'].sum())} |"]
    for reason, n in elig.loc[~elig['usable'], 'exclusion_reason'].value_counts().items():
        lines.append(f'| excluded: {reason} | {n} |')
    u = elig[elig['usable']]
    if len(u):
        lines += ['', '## Acquisition timing of usable pairs', '',
                  '| quantity | median | min | max |', '|---|---:|---:|---:|',
                  f"| days before event (before_primary) | {u['days_before'].median():.0f} | {u['days_before'].min():.0f} | {u['days_before'].max():.0f} |",
                  f"| days after event (after_primary) | {u['days_after'].median():.0f} | {u['days_after'].min():.0f} | {u['days_after'].max():.0f} |",
                  f"| candidates screened per event | {u['candidates_screened'].median():.0f} | {u['candidates_screened'].min():.0f} | {u['candidates_screened'].max():.0f} |",
                  f"| before patch cloud fraction | {u['before_cloud_fraction'].median():.3f} | {u['before_cloud_fraction'].min():.3f} | {u['before_cloud_fraction'].max():.3f} |",
                  f"| after patch cloud fraction | {u['after_cloud_fraction'].median():.3f} | {u['after_cloud_fraction'].min():.3f} | {u['after_cloud_fraction'].max():.3f} |",
                  f"| before snow fraction | {u['before_snow_fraction'].median():.3f} | {u['before_snow_fraction'].min():.3f} | {u['before_snow_fraction'].max():.3f} |",
                  f"| after snow fraction | {u['after_snow_fraction'].median():.3f} | {u['after_snow_fraction'].min():.3f} | {u['after_snow_fraction'].max():.3f} |",
                  '', f"Usable events by year: {u['event_date'].str[:4].value_counts().sort_index().to_dict()}",
                  f"by state: {u['state'].value_counts().to_dict()}", f"by process: {u['process_type'].value_counts().to_dict()}",
                  f"independence units: {u['independence_unit'].nunique()}"]
    if data is not None:
        pos = data[data['label'] == 1]
        idx = data[['sample_id', 'event_group_id', 'label', 'longitude', 'latitude', 'grid_epsg', 'before_item', 'after_item',
                    'before_datetime', 'after_datetime', 'days_before', 'days_after', 'doy_gap', 'before_core_cloud', 'after_core_cloud',
                    'before_core_snow', 'after_core_snow', 'before_patch_cloud', 'after_patch_cloud', 'coreg_dx_px', 'coreg_dy_px', 'coreg_peak_ratio']]
        idx.to_csv(out / 'event_imagery_index.csv', index=False)
        status = read_json(SAT_DATA / 'tables/dataset_status.json')
        shift = np.hypot(data['coreg_dx_px'], data['coreg_dy_px'])
        lines += ['', '## Training table', '',
                  f"| samples | {len(data)} |", '|---|---:|', f"| groups (1 positive + 4-5 controls on the same acquisitions) | {data['event_group_id'].nunique()} |",
                  f"| groups with all 5 controls | {int((data[data.label == 1]['group_size'] == 6).sum())} |",
                  f"| independence units | {data['independence_unit'].nunique()} |", f"| incomplete groups dropped | {len(status['groups_incomplete'])} |",
                  f"| sample failures | {len(status['sample_failures'])} |",
                  f"| patches with estimated co-registration shift > {cfg['patch']['max_coregistration_shift_px']} px | {int((shift > cfg['patch']['max_coregistration_shift_px']).sum())} |",
                  '', f"Patch: {cfg['patch']['extent_m']} m × {cfg['patch']['extent_m']} m at {cfg['patch']['resolution_m']} m "
                  f"({cfg['patch']['extent_m'] // cfg['patch']['resolution_m']} px); windows small {cfg['patch']['small_m']} m, core {cfg['patch']['core_m']} m, ring to {cfg['patch']['medium_m']} m.",
                  f"Positives by V0.4 partition: {pos['v04_partition'].value_counts().to_dict()} (the V0.4 sealed test is not a Pipeline B test; Pipeline B uses its own unit holdout).",
                  '', 'Negatives are the matched V0.4 controls (pseudo-negatives: no documented event, matched terrain, same acquisitions). '
                  'They are hard negatives for terrain and for scene-wide temporal change, but they do not deliberately sample forestry, construction or river change; '
                  'those false-positive types are examined in the discovery scan instead.']
        if (SAT_DATA / 'tables/contact_sheet_labels.csv').exists():
            lines += ['', 'Contact sheets (anonymised labels SAT-xx): `reports/satellite/contact_sheets/`; the label ↔ event mapping is local only.']
    (out / 'dataset_summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    br = SAT_REPORT / 'baseline_results.json'
    if br.exists():
        r = read_json(br)
        lines = ['# Satellite change baselines (event-held-out)', '',
                 f"{r['dataset']['rows']} samples, {r['dataset']['groups']} groups, {r['dataset']['independence_units']} independence units. "
                 f"GroupKFold over independence units ({cfg['models']['cv_folds']} folds, 3 fold shuffles); scores are out-of-fold. "
                 'Within-group AUC = fraction of the 5 controls scored below their positive (chance 0.5); top-1 = positive ranked first (chance 0.167).', '',
                 '| feature set / model | ROC AUC | AP | within-group AUC | unit-weighted | top-1 | mean rank |', '|---|---:|---:|---:|---:|---:|---:|']
        for key, m in r['models'].items():
            lines.append(f"| {key} | {m['roc_auc']['mean']:.3f} | {m['average_precision']['mean']:.3f} | {m['within_group_auc']['mean']:.3f} | "
                         f"{m['within_group_auc_unit_weighted']['mean']:.3f} | {m['top1_rate']['mean']:.3f} | {m['mean_rank']['mean']:.2f} |")
        n = r['permutation_null']
        lines += ['', f"Within-group label permutation null ({n['draws']} draws, logistic regression, change features): null mean {n['null_mean']:.3f}, "
                  f"null 95th percentile {n['null_95']:.3f}, observed {n['observed']:.3f}, upper p = {n['p_upper']:.3f}.", '',
                  '`ring_only_shortcut` uses only scene-wide change around the sample (should stay near chance if the model learns local change); '
                  '`nuisance_only_shortcut` uses acquisition timing and cloud/snow fractions, which are identical within a group except for local cloud/snow, '
                  'so it must stay at chance for the within-group metrics. Held-out values away from 0.5 mean the feature set carries structure that '
                  'transfers between independence units: above 0.5 for ring-only means the surroundings of positives change differently from the surroundings of '
                  'controls (storm clusters put neighbouring slides into the ring; land cover around reported slopes differs), which the detector may exploit; '
                  'below 0.5 with few units is small-sample reversal. Both are reported, not corrected. '
                  'The contrast-only set was not pre-registered as primary; its advantage is noted, not selected on.', '',
                  '## Logistic-regression coefficients (standardised, full data; predictive association, not causation)', '',
                  '| feature | coefficient |', '|---|---:|']
        for row in r['importance_logistic_regression'][:15]:
            lines.append(f"| {row['feature']} | {row['standardized_coefficient']:+.3f} |")
        (out / 'baseline_results.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    hd = SAT_REPORT / 'heldout_discovery_results.json'
    if hd.exists():
        r = read_json(hd)
        lines = ['# Held-out rediscovery of known events', '',
                 f"For each independence unit a {r['model']} detector is trained on all other units, then every position of the "
                 f"{cfg['patch']['extent_m']} m patch around each held-out event is scored (sliding windows), local maxima at least "
                 f"{cfg['discovery']['min_peak_distance_m']} m apart are ranked, and a hit is a peak within {r['hit_radius_m']} m of the reported position.", '',
                 '| quantity | value |', '|---|---:|',
                 f"| held-out events | {r['events']} |", f"| independence units | {r['independence_units']} |",
                 f"| searched area per event (km²) | {_fmt(r['searched_km2_per_event'], 2)} |",
                 f"| rediscovered at rank 1 | {r['detected_rank1']} |", f"| rediscovered within top 3 | {r['detected_top3']} |",
                 f"| rediscovered within top 5 | {r['detected_top5']} |", f"| rediscovered at any rank | {r['detected_any_rank']} |",
                 f"| median hit rank | {_fmt(r['median_hit_rank'], 1)} |", f"| median localisation error (m) | {_fmt(r['median_hit_distance_m'], 0)} |",
                 f"| false peaks ranked above the hit (mean) | {_fmt(r['false_peaks_above_hit_mean'], 2)} |",
                 f"| peaks per km² (mean) | {_fmt(r['peaks_per_km2_mean'], 2)} |", '',
                 f"Chance reference: {r['chance_rank1']}.", '',
                 'The search region is centred on the known event, so this is a localisation test inside a small area, not an unknown-region scan. '
                 'Peaks that are not the known event are candidate detections for the false-positive analysis; they are NOT labelled as landslides.']
        (out / 'heldout_discovery_results.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write_web_bundle(cfg, elig, data)
    print('reports written to', out)


def write_web_bundle(cfg, elig, data):
    """Aggregate-only bundle for the local web demo (no coordinates, no source identifiers)."""
    u = elig[elig['usable']]
    bundle = {'config': {'version': cfg['version'], 'patch_m': cfg['patch']['extent_m'], 'small_m': cfg['patch']['small_m'],
                         'core_m': cfg['patch']['core_m'], 'ring_m': cfg['patch']['medium_m'], 'resolution_m': cfg['patch']['resolution_m'],
                         'core_cloud_max': cfg['eligibility']['core_cloud_max'], 'core_snow_max': cfg['eligibility']['core_snow_max'],
                         'min_event_year': cfg['eligibility']['min_event_year'], 'max_position_upper_m': cfg['eligibility']['max_position_upper_m']},
              'eligibility': {'screened': int(len(elig)), 'usable': int(elig['usable'].sum()),
                              'exclusions': {k: int(v) for k, v in elig.loc[~elig['usable'], 'exclusion_reason'].value_counts().items()},
                              'usable_by_year': {k: int(v) for k, v in u['event_date'].str[:4].value_counts().sort_index().items()},
                              'days_before_median': float(u['days_before'].median()) if len(u) else None,
                              'days_after_median': float(u['days_after'].median()) if len(u) else None,
                              'independence_units': int(u['independence_unit'].nunique())},
              'dataset': None, 'baseline': None, 'discovery': None,
              'contact_sheets': sorted(p.name for p in (SAT_REPORT / 'contact_sheets').glob('contact_sheet_*.png')) if (SAT_REPORT / 'contact_sheets').exists() else []}
    if data is not None:
        bundle['dataset'] = {'samples': int(len(data)), 'groups': int(data['event_group_id'].nunique()),
                             'independence_units': int(data['independence_unit'].nunique()),
                             'coreg_shift_gt1px': int((np.hypot(data['coreg_dx_px'], data['coreg_dy_px']) > 1).sum())}
    br = SAT_REPORT / 'baseline_results.json'
    if br.exists():
        r = read_json(br)
        bundle['baseline'] = {'models': {k: {m: v[m]['mean'] for m in v} for k, v in r['models'].items()},
                              'permutation_null': r['permutation_null'], 'chance': r['chance'],
                              'importance': r['importance_logistic_regression'][:10]}
    hd = SAT_REPORT / 'heldout_discovery_results.json'
    if hd.exists():
        bundle['discovery'] = read_json(hd)
    guard(SAT_DATA / 'web')
    (SAT_DATA / 'web/results.json').write_text(json.dumps(bundle, indent=1, ensure_ascii=False, allow_nan=False), encoding='utf-8')
