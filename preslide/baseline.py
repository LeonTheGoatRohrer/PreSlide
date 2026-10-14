"""PreSlide V0.3 baseline: freeze manifest, event-level error analysis and overwrite guard.

Never trains a model. Every number is derived from saved predictions and the frozen dataset:
original test events use the frozen V0 models' test predictions, development events use the
V0.2 out-of-training predictions (5 repetitions x 4 grouped folds).
"""
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import read_json, write_json
from .sources import ROOT

BASELINE_VERSION = 'PreSlide V0.3 Baseline'
BASELINE_ID = 'preslide-v0.3-baseline'
IDENTITY = '046074ba6f12556c'
RUN = ROOT / 'data/processed' / IDENTITY
REPORT = ROOT / 'reports/baseline'
MANIFEST = REPORT / 'BASELINE_MANIFEST.json'
MEMBERSHIP = REPORT / 'baseline_membership.json'   # record-level, local only (gitignored)
DIAGNOSTICS = REPORT / 'event_diagnostics.csv'      # record-level, local only (gitignored)
SAMPLE_SCORES = REPORT / 'sample_scores.csv'        # record-level, local only (gitignored)
V02 = ROOT / 'data/analysis/stability_v02'
MODELS = ['logistic_regression', 'random_forest', 'gradient_boosting']
SHORT = {'logistic_regression': 'lr', 'random_forest': 'rf', 'gradient_boosting': 'gb'}
VARIANTS = ['static', 'temporal', 'combined']

# Everything that produced or reports the baseline. Directories are hashed file by file.
FROZEN = ['config/experiment.json', 'config/audit.json', 'config/stability_v02.json', 'config/null_v03.json',
          'data/interim/quality_candidates_pending_source_clearance.json', 'data/raw/geosphere_natural_hazards.json',
          f'data/processed/{IDENTITY}/dataset_102.parquet', f'data/processed/{IDENTITY}/evaluation_dataset.parquet',
          f'data/processed/{IDENTITY}/test_predictions.parquet', f'data/processed/{IDENTITY}/status.json',
          f'data/processed/{IDENTITY}/inputs.json', f'data/processed/{IDENTITY}/position_sensitivity.json',
          f'models/{IDENTITY}', 'reports/experiment', 'reports/stability_v02', 'reports/null_v03',
          'reports/verification/independent_checks.json',
          'data/analysis/stability_v02/primary_predictions.parquet', 'data/analysis/stability_v02/splits.parquet',
          'data/analysis/stability_v02/event_results.parquet', 'data/analysis/stability_v02/protocol.json',
          'data/analysis/stability_v02/primary_complete.json', 'data/analysis/stability_v02/original_manifest.json',
          'requirements-lock.txt']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def pointer():
    """Pinned replacement for data/processed/latest.json, which later experiment versions overwrite."""
    return {'identity': IDENTITY, 'directory': str(RUN), 'dataset': 'dataset_102.parquet',
            'config': read_json(ROOT / 'config/experiment.json')}


def frozen_files():
    files = []
    for item in FROZEN:
        p = ROOT / item
        files.extend(sorted(x for x in p.rglob('*') if x.is_file()) if p.is_dir() else [p])
    return {f.relative_to(ROOT).as_posix(): f for f in files}


def frozen_paths():
    """Relative paths protected by an existing manifest (empty if the baseline was never frozen)."""
    return set(read_json(MANIFEST)['sha256']) if MANIFEST.exists() else set()


def assert_not_frozen(path):
    """Refuse to (over)write any artifact that belongs to the frozen baseline."""
    rel = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    if rel in frozen_paths():
        raise RuntimeError(f'{rel} belongs to {BASELINE_VERSION}; write a new experiment version instead')


def verify_manifest():
    manifest = read_json(MANIFEST)
    errors = [p for p, h in manifest['sha256'].items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    return {'files': len(manifest['sha256']), 'mismatched_or_missing': errors, 'status': 'PASS' if not errors else 'FAIL'}


# ---------------------------------------------------------------- event-level diagnostics

def rank_of_positive(frame, score):
    """Same rule as every project metric: rank = 1 + better controls + 0.5 * ties."""
    pos = frame.loc[frame.label == 1, score].iloc[0]
    neg = frame.loc[frame.label == 0, score].to_numpy()
    return 1 + float((neg > pos).sum() + .5 * (neg == pos).sum()), int((pos > neg).sum())


def load_data():
    return pd.read_parquet(RUN / 'evaluation_dataset.parquet')


def sample_scores(data):
    """Long table: one score per sample x model x feature set, from saved predictions only."""
    test = pd.read_parquet(RUN / 'test_predictions.parquet').rename(columns={'probability_case_control': 'score'})
    test['source'] = 'original_test_frozen_model'
    test['score_min'] = test['score_max'] = test['score']
    dev = pd.read_parquet(V02 / 'primary_predictions.parquet')
    dev = (dev.groupby(['sample_id', 'model', 'features']).probability
              .agg(score='median', score_min='min', score_max='max').reset_index())
    dev['source'] = 'v02_development_out_of_training_median_of_5'
    scores = pd.concat([test, dev], ignore_index=True)
    return scores.merge(data[['sample_id', 'event_group_id', 'label']], on='sample_id', validate='many_to_one')


def per_repetition_ranks(data):
    """Development: positive rank per repetition (each sample predicted exactly once per repetition)."""
    dev = pd.read_parquet(V02 / 'primary_predictions.parquet')
    rows = []
    for (rep, model, feats, event), g in dev.groupby(['repetition', 'model', 'features', 'event_group_id']):
        r, b = rank_of_positive(g, 'probability')
        rows.append({'repetition': rep, 'model': model, 'features': feats, 'event_group_id': event, 'rank': r, 'beaten': b})
    return pd.DataFrame(rows)


def build_diagnostics():
    data = load_data()
    scores = sample_scores(data)
    reps = per_repetition_ranks(data)
    position = {p['event_id']: p for p in read_json(RUN / 'position_sensitivity.json')}
    aliases = read_json(V02 / 'private_event_aliases.json')
    temporal = [c for c in data.columns if c.startswith(('rain_sum_', 'rain_max_hour_', 'temperature_mean_'))]
    pooled_sd = data[temporal].std()
    rows = []
    for event, g in data.groupby('event_group_id', sort=False):
        pos = g[g.label == 1].iloc[0]
        ctrl = g[g.label == 0]
        partition = pos.partition
        row = {'event_group_id': event, 'dev_alias': aliases.get(event, ''), 'evaluation': 'original_test' if partition == 'test' else 'development_oof',
               'original_partition': partition, 'dependence_cluster': pos.dependence_cluster, 'event_date': pos.event_date,
               'state': pos.state, 'process_type': pos.process_type, 'n_controls': len(ctrl)}
        for model in MODELS:
            m = SHORT[model]
            for feats in VARIANTS:
                s = scores[(scores.event_group_id == event) & (scores.model == model) & (scores.features == feats)]
                if partition == 'test':
                    r, b = rank_of_positive(s, 'score')
                    row[f'{m}_{feats}_rank'], row[f'{m}_{feats}_beaten'] = r, float(b)
                    row[f'{m}_{feats}_rank_min'] = row[f'{m}_{feats}_rank_max'] = r
                else:
                    e = reps[(reps.event_group_id == event) & (reps.model == model) & (reps.features == feats)]
                    if len(e) != 5: raise RuntimeError(f'expected 5 repetitions for {event} {model} {feats}')
                    row[f'{m}_{feats}_rank'], row[f'{m}_{feats}_beaten'] = float(e['rank'].median()), float(e.beaten.mean())
                    row[f'{m}_{feats}_rank_min'], row[f'{m}_{feats}_rank_max'] = float(e['rank'].min()), float(e['rank'].max())
                # Rank of the displayed (median) score; the web demo uses this so ranks match the shown scores.
                row[f'{m}_{feats}_score_rank'], row[f'{m}_{feats}_score_beaten'] = rank_of_positive(s, 'score')
                ps = s.loc[s.label == 1, 'score'].iloc[0]
                cs = np.sort(s.loc[s.label == 0, 'score'].to_numpy())[::-1]
                row[f'{m}_{feats}_positive_score'] = ps
                row[f'{m}_{feats}_margin_to_best_control'] = ps - cs[0]
                if feats == 'combined':
                    row[f'{m}_combined_control_scores'] = ';'.join(f'{v:.4f}' for v in cs)
            row[f'{m}_weather_rank_change'] = row[f'{m}_static_rank'] - row[f'{m}_combined_rank']  # >0: weather helped
        row.update({
            'control_distance_min_m': ctrl.distance_to_positive_m.min(), 'control_distance_median_m': ctrl.distance_to_positive_m.median(),
            'control_distance_max_m': ctrl.distance_to_positive_m.max(),
            'matching_score_mean': ctrl.matching_score.mean(), 'matching_score_max': ctrl.matching_score.max(),
            'slope_difference_mean_deg': ctrl.slope_difference_deg.mean(), 'elevation_difference_mean_m': ctrl.elevation_difference_m.mean(),
            'aspect_difference_mean_deg': ctrl.aspect_difference_deg.mean(),
            'positive_slope_deg': pos.slope, 'positive_elevation_m': pos.elevation, 'positive_aspect_deg': pos.aspect})
        z = ((pos[temporal] - ctrl[temporal].mean()).abs() / pooled_sd).astype(float)
        cells = set(map(tuple, ctrl[['weather_grid_lon', 'weather_grid_lat']].round(6).to_numpy()))
        row.update({
            'weather_std_diff_median': float(z.median()), 'weather_std_diff_max': float(z.max()),
            'weather_nearly_identical': bool(z.median() < 0.05),
            'controls_in_same_weather_cell': int(sum(c == (round(pos.weather_grid_lon, 6), round(pos.weather_grid_lat, 6)) for c in map(tuple, ctrl[['weather_grid_lon', 'weather_grid_lat']].round(6).to_numpy()))),
            'distinct_weather_cells': len(cells | {(round(pos.weather_grid_lon, 6), round(pos.weather_grid_lat, 6))}),
            'rain_sum_7d_positive_mm': pos.rain_sum_7d, 'rain_sum_7d_controls_mean_mm': ctrl.rain_sum_7d.mean(),
            'rain_sum_30d_positive_mm': pos.rain_sum_30d, 'rain_sum_30d_controls_mean_mm': ctrl.rain_sum_30d.mean(),
            'rain_sum_7d_positive_rank': 1 + int((ctrl.rain_sum_7d > pos.rain_sum_7d).sum()),
            'rain_sum_30d_positive_rank': 1 + int((ctrl.rain_sum_30d > pos.rain_sum_30d).sum())})
        p = position[event]
        row.update({'source_position_upper_m': int(pos.source_position_upper_m),
                    'position_category': {5: 'fein (≤5 m)', 20: 'mittel (≤20 m)', 100: 'grob (≤100 m)'}.get(int(pos.source_position_upper_m), 'unbekannt'),
                    'position_max_slope_change_deg': p['maximum_slope_change_deg'],
                    'position_crosses_slope_caliper': bool(p['maximum_slope_change_deg'] > 5)})
        rows.append(row)
    diag = pd.DataFrame(rows).sort_values(['evaluation', 'event_date', 'event_group_id']).reset_index(drop=True)
    return diag, scores


def check_against_v02(diag):
    """Cross-check development ranks with the independently produced V0.2 event table."""
    ref = pd.read_parquet(V02 / 'event_results.parquet')
    med = ref.groupby(['event_group_id', 'model', 'features']).positive_rank.median()
    worst = 0.0
    for (event, model, feats), v in med.items():
        worst = max(worst, abs(diag.set_index('event_group_id').loc[event, f'{SHORT[model]}_{feats}_rank'] - v))
    if worst > 1e-9: raise RuntimeError(f'development ranks differ from V0.2 event_results by {worst}')
    return worst


def check_against_metrics(scores):
    """Pooled test metrics recomputed from saved scores must equal the stored metrics.json."""
    from sklearn.metrics import roc_auc_score, average_precision_score
    metrics = read_json(ROOT / 'reports/experiment/metrics.json')
    worst = 0.0
    for rec in metrics['models']:
        s = scores[(scores.source == 'original_test_frozen_model') & (scores.model == rec['model']) & (scores.features == rec['features'])]
        worst = max(worst, abs(roc_auc_score(s.label, s.score) - rec['test']['roc_auc']),
                    abs(average_precision_score(s.label, s.score) - rec['test']['average_precision']))
    if worst > 1e-9: raise RuntimeError(f'test metrics not reproducible from saved predictions ({worst})')
    return worst


# ---------------------------------------------------------------- report

def fmt(v, d=2):
    return f'{v:.{d}f}'


def error_report(diag):
    from scipy.stats import spearmanr
    lines = [f'# {BASELINE_VERSION} — event-level error analysis', '',
             'Generated by `python -m preslide.baseline` from saved predictions; no model was retrained. '
             'Record-level table: `event_diagnostics.csv` (local only). Nothing was removed.', '',
             '## How to read', '',
             '- Each event group = 1 documented landslide slope + 5 matched pseudo-negative controls, all at the same t0.',
             '- `rank` 1–6 of the positive among its six slopes (1 = model put the landslide first; ties count half). '
             'Random ranking: expected rank 3.5, expected controls beaten 2.5, first-place rate 1/6 ≈ 16.7 %.',
             '- Development events (45): V0.2 out-of-training predictions, median rank over 5 repetitions. '
             'Original test events (15): frozen V0 models, single prediction. The two sources are reported separately.',
             '- `weather_rank_change` = terrain-only rank − terrain+weather rank (> 0: adding weather moved the landslide up).',
             '- The CSV also holds `*_score_rank`: the rank of the median out-of-training score per slope. The web explorer shows this one, '
             'so that the displayed rank always matches the displayed scores. For development events it can differ from the median of the '
             'per-repetition ranks used in the tables below.', '']
    for evaluation, title in [('development_oof', 'Development (45 events, V0.2 out-of-training)'), ('original_test', 'Original frozen test (15 events)')]:
        d = diag[diag.evaluation == evaluation]
        lines += [f'## {title}', '', '| Model | Variant | Mean rank | Mean controls beaten | Events ranked 1st | Events ranked last (6) |', '|---|---|---:|---:|---:|---:|']
        for model in MODELS:
            m = SHORT[model]
            for feats in VARIANTS:
                r = d[f'{m}_{feats}_rank']
                lines.append(f'| {model} | {feats} | {fmt(r.mean())} | {fmt(d[f"{m}_{feats}_beaten"].mean())} | {int((r <= 1).sum())}/{len(d)} | {int((r >= 6).sum())}/{len(d)} |')
        lines += ['', 'Chance: mean rank 3.50, controls beaten 2.50, rank 1 in ≈ 1/6 of events.', '']
        lines += ['| Model | Weather improved rank | unchanged | worsened | Mean change |', '|---|---:|---:|---:|---:|']
        for model in MODELS:
            c = d[f'{SHORT[model]}_weather_rank_change']
            lines.append(f'| {model} | {int((c > 0).sum())} | {int((c == 0).sum())} | {int((c < 0).sum())} | {fmt(c.mean())} |')
        lines.append('')
    dev = diag[diag.evaluation == 'development_oof']
    lines += ['## Worst and best development events (Random Forest, terrain + weather)', '',
              'Sorted by median rank; listed by de-identified alias. Rank range = min–max over 5 repetitions.', '',
              '| Alias | Cluster | Date | Rank (range) | Beaten | Weather Δrank | Position | Matching score | Weather std. diff |', '|---|---|---|---|---:|---:|---|---:|---:|']
    order = dev.sort_values(['rf_combined_rank', 'rf_combined_beaten'], ascending=[False, True])
    for _, r in pd.concat([order.head(8), order.tail(5)]).iterrows():
        lines.append(f'| {r.dev_alias} | {r.dependence_cluster} | {r.event_date} | {fmt(r.rf_combined_rank,1)} ({fmt(r.rf_combined_rank_min,0)}–{fmt(r.rf_combined_rank_max,0)}) | '
                     f'{fmt(r.rf_combined_beaten,1)} | {fmt(r.rf_weather_rank_change,1)} | {r.position_category} | {fmt(r.matching_score_mean)} | {fmt(r.weather_std_diff_median)} |')
    lines += ['', '(First 8 rows = worst, last 5 = best.)', '',
              '## Are errors associated with data quality? (exploratory, development events)', '',
              'Spearman correlation with the median Random Forest combined rank (higher rank = worse). '
              'Events in the same dependence cluster are not independent, so these p-values are optimistic and descriptive only.', '',
              '| Event property | Spearman ρ | nominal p |', '|---|---:|---:|']
    for col, label in [('source_position_upper_m', 'source position category (m)'), ('position_max_slope_change_deg', 'slope change under position offsets (°)'),
                       ('matching_score_mean', 'mean control matching score (lower = closer)'), ('control_distance_median_m', 'median control distance (m)'),
                       ('weather_std_diff_median', 'weather difference positive vs controls (std.)'), ('positive_slope_deg', 'positive slope (°)')]:
        rho, p = spearmanr(dev[col], dev.rf_combined_rank)
        lines.append(f'| {label} | {fmt(rho)} | {fmt(p, 3)} |')
    nearly = int(diag.weather_nearly_identical.sum())
    same_cell = int((diag.controls_in_same_weather_cell > 0).sum())
    cl = dev.groupby('dependence_cluster').agg(events=('event_group_id', 'size'), mean_rank=('rf_combined_rank', 'mean')).sort_values('events', ascending=False)
    lines += ['', '## Weather distinguishability', '',
              f'- Events whose positive and controls have nearly identical weather (median standardised difference < 0.05): {nearly}/60.',
              f'- Events in which any control shares the positive\'s 1 km INCA cell: {same_cell}/60.',
              f'- Positive was the wettest of its six slopes (7-day rain): {int((diag.rain_sum_7d_positive_rank == 1).sum())}/60 (chance ≈ 10).',
              '- Weather differences between nearby slopes therefore exist in the data; whether a 1 km product resolves slope-scale forcing is not established.', '',
              '## Dependence clusters (development, Random Forest combined)', '', '| Cluster | Events | Mean rank |', '|---|---:|---:|']
    for c, r in cl.iterrows():
        lines.append(f'| {c} | {int(r.events)} | {fmt(r.mean_rank)} |')
    lines += ['', '## Interpretation', '',
              'Errors are spread across clusters, position categories and matching quality; the rank distribution is close to the random reference '
              '(see the tables above and `reports/null_v03/summary.md`). No single data-quality property explains the poor events. '
              'These diagnostics describe the baseline; they were not used to select models, features or events.', '']
    return '\n'.join(lines)


# ---------------------------------------------------------------- manifest

def software():
    import sklearn, numpy, pandas, scipy, pyarrow
    return {'python': sys.version.split()[0], 'platform': platform.platform(), 'scikit-learn': sklearn.__version__,
            'numpy': numpy.__version__, 'pandas': pandas.__version__, 'scipy': scipy.__version__, 'pyarrow': pyarrow.__version__}


def build_manifest(data):
    from .evaluation import FEATURE_SETS, make_model
    metrics = read_json(ROOT / 'reports/experiment/metrics.json')
    status = read_json(RUN / 'status.json')
    groups = data.groupby('event_group_id')
    membership = {
        'baseline_id': BASELINE_ID, 'dataset_identity': IDENTITY,
        'events': {e: {'controls': sorted(g.loc[g.label == 0, 'sample_id']), 'positive': g.loc[g.label == 1, 'sample_id'].iloc[0],
                       'event_date': g.event_date.iloc[0], 'dependence_cluster': g.dependence_cluster.iloc[0],
                       'original_partition': g.partition.iloc[0]} for e, g in groups},
        'excluded': [s for s in status if s['status'] != 'complete'],
        'v02_folds': pd.read_parquet(V02 / 'splits.parquet').query('label == 1')[['event_group_id', 'repetition', 'seed', 'fold']].to_dict('records')}
    write_json(MEMBERSHIP, membership)
    files = frozen_files()
    files[MEMBERSHIP.relative_to(ROOT).as_posix()] = MEMBERSHIP
    hashes = {k: sha(v) for k, v in sorted(files.items())}
    pos = data[data.label == 1]
    return {
        'baseline_version': BASELINE_VERSION, 'baseline_id': BASELINE_ID,
        'frozen_on': '2026-10-14',
        'scope': 'Original V0 experiment (frozen split, 9 models, Steiermark holdout), V0.2 development stability/diagnostics, V0.3 label-permutation null reference.',
        'dataset': {'identity': IDENTITY, 'dataset_file': f'data/processed/{IDENTITY}/dataset_102.parquet',
                    'evaluation_dataset_sha256': hashes[f'data/processed/{IDENTITY}/evaluation_dataset.parquet'],
                    'feature_dataset_hash': metrics['dataset_hash'],
                    'candidates': len(status), 'events': int(pos.event_group_id.nunique()), 'controls': int((data.label == 0).sum()),
                    'samples': len(data), 'controls_per_event': 5, 'dependence_clusters': int(data.dependence_cluster.nunique()),
                    'event_dates': [pos.event_date.min(), pos.event_date.max()], 'distinct_dates': int(pos.event_date.nunique()),
                    'exclusions': pd.Series([s['reason'].split(':')[0] for s in status if s['status'] != 'complete']).value_counts().to_dict(),
                    'event_ids_sha256': hashlib.sha256('\n'.join(sorted(pos.event_group_id)).encode()).hexdigest(),
                    'control_ids_sha256': hashlib.sha256('\n'.join(sorted(data.loc[data.label == 0, 'sample_id'])).encode()).hexdigest(),
                    'membership_file': MEMBERSHIP.relative_to(ROOT).as_posix()},
        'features': {k: v for k, v in FEATURE_SETS.items()},
        'feature_counts': {'static': len(FEATURE_SETS['static']), 'temporal': len(FEATURE_SETS['temporal'])},
        'feature_configuration': read_json(ROOT / 'config/experiment.json'),
        'splits': {'original': metrics['split'], 'v02': read_json(ROOT / 'config/stability_v02.json').get('seeds', [11, 23, 37, 51, 71]),
                   'v02_folds': 4, 'v02_development_events': int((pos.partition != 'test').sum())},
        'models': {name: {k: str(v) for k, v in make_model(name).get_params(deep=False).items()} for name in MODELS},
        'artifacts': {'original_metrics': 'reports/experiment/metrics.json', 'original_test_predictions': f'data/processed/{IDENTITY}/test_predictions.parquet',
                      'original_models': f'models/{IDENTITY}/', 'v02_predictions': 'data/analysis/stability_v02/primary_predictions.parquet',
                      'v02_report': 'reports/stability_v02/summary.md', 'v02_verification': 'reports/stability_v02/verification.json',
                      'v03_null': 'reports/null_v03/summary.md', 'independent_checks': 'reports/verification/independent_checks.json',
                      'event_diagnostics': DIAGNOSTICS.relative_to(ROOT).as_posix(), 'error_analysis': 'reports/baseline/error_analysis.md'},
        'software': software(),
        'code_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in sorted([*(ROOT / 'preslide').glob('*.py'), *(ROOT / 'scripts').glob('*.py')])},
        'sha256': hashes}


def run():
    REPORT.mkdir(parents=True, exist_ok=True)
    diag, scores = build_diagnostics()
    dev_check = check_against_v02(diag)
    test_check = check_against_metrics(scores)
    diag.to_csv(DIAGNOSTICS, index=False)
    scores.sort_values(['event_group_id', 'model', 'features', 'label'], ascending=[True, True, True, False]).to_csv(SAMPLE_SCORES, index=False)
    (REPORT / 'error_analysis.md').write_text(error_report(diag), encoding='utf-8')
    data = load_data()
    if MANIFEST.exists():
        result = verify_manifest()
        print('existing manifest', result['status'], result['mismatched_or_missing'][:5])
        if result['status'] != 'PASS': raise RuntimeError('Frozen baseline artifacts changed; do not refreeze silently')
    else:
        manifest = build_manifest(data)
        for name in ['event_diagnostics.csv', 'sample_scores.csv', 'error_analysis.md']:
            manifest['sha256'][f'reports/baseline/{name}'] = sha(REPORT / name)
        write_json(MANIFEST, manifest)
    print(json.dumps({'events': len(diag), 'dev_rank_check': dev_check, 'test_metric_check': test_check, 'manifest': verify_manifest()['status']}))


if __name__ == '__main__':
    run()
