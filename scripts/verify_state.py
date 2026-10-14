"""Independent re-verification of the frozen PreSlide dataset, splits and saved metrics.

Read-only with respect to all experiment artifacts. Recomputes invariants and metrics directly
from saved parquet/joblib files instead of trusting Markdown/UI numbers.
Writes reports/verification/independent_checks.json (aggregate values only).
Run: .venv/Scripts/python scripts/verify_state.py
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.evaluation import metrics as project_metrics  # noqa: E402
from preslide.weather import TEMPORAL, cutoff  # noqa: E402

STATIC = ['elevation', 'slope', 'aspect_sin', 'aspect_cos']
from preslide.baseline import pointer  # noqa: E402
latest = pointer()  # pinned frozen baseline, not latest.json
RUN = ROOT / 'data/processed' / latest['identity']
STAB = ROOT / 'data/analysis/stability_v02'
cfg = latest['config']
errors, out = [], {}


def check(condition, message):
    if not bool(condition):
        errors.append(message)


def circular(a, b):
    d = np.abs(np.asarray(a) - np.asarray(b)) % 360
    return np.minimum(d, 360 - d)


def pairwise(data, score):
    """Independent within-group positive-vs-control statistics (ties = 0.5)."""
    rows = []
    for g, d in data.groupby('event_group_id'):
        pos = score[d.index[d.label == 1]].iloc[0]
        neg = score[d.index[d.label == 0]].to_numpy()
        rows.append({'event_group_id': g, 'beaten': int((pos > neg).sum()),
                     'auc': float(np.mean((pos > neg) + 0.5 * (pos == neg))),
                     'rank': 1 + float((neg > pos).sum() + 0.5 * (neg == pos).sum())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- dataset
data = pd.read_parquet(RUN / 'evaluation_dataset.parquet')
pos = data[data.label == 1]
ctrl = data[data.label == 0]
groups = data.groupby('event_group_id')
check(data.sample_id.is_unique, 'duplicate sample_id')
check((groups.label.sum() == 1).all(), 'group without exactly one positive')
check((groups.size() == 6).all(), 'group without exactly six samples')
check((groups.event_date.nunique() == 1).all(), 'controls do not inherit t0')
check(((data.label == 1) == (data.sample_type == 'POSITIVE')).all(), 'label/sample_type mismatch')
check(set(ctrl.sample_type) == {'PSEUDO_NEGATIVE'}, 'unexpected control type')
check(np.isfinite(data[STATIC + TEMPORAL].to_numpy()).all(), 'non-finite predictor')
check(data[STATIC + TEMPORAL].nunique().min() > 1, 'constant predictor')
check(not data[['x', 'y']].round(1).duplicated().any(), 'duplicate coordinates')

# CRS: recompute EPSG:31287 coordinates from WGS84 and compare
tr = Transformer.from_crs('EPSG:4326', cfg['terrain_crs'], always_xy=True)
x, y = tr.transform(data.longitude.to_numpy(), data.latitude.to_numpy())
crs_err = float(np.max(np.hypot(x - data.x, y - data.y)))
# Controls store rounded lon/lat (sub-metre); positives round-trip exactly. Irrelevant at 30 m DEM / 1 km weather.
check(crs_err < 1.0, f'CRS round-trip error {crs_err} m')
check(data.latitude.between(46.3, 49.1).all() and data.longitude.between(9.4, 17.2).all(), 'coordinate outside Austria box')
check(data.inside_austria.dropna().all(), 'control flagged outside Austria')

# Geometry and calipers recomputed from coordinates/terrain, not from stored differences
p = pos.set_index('event_group_id')
c = ctrl.join(p[['x', 'y', 'slope', 'elevation', 'aspect']], on='event_group_id', rsuffix='_pos')
dist = np.hypot(c.x - c.x_pos, c.y - c.y_pos)
check(np.allclose(dist, c.distance_to_positive_m, atol=0.5), 'stored control distance mismatch')
check(dist.between(cfg['control_min_distance_m'], cfg['control_max_distance_m']).all(), 'control distance outside annulus')
asp = circular(c.aspect, c.aspect_pos)
check(np.allclose(asp, c.aspect_difference_deg, atol=1e-6), 'aspect difference not circular / mismatch')
check((asp <= cfg['aspect_caliper_deg'] + 1e-9).all(), 'aspect caliper violated')
check(((c.slope - c.slope_pos).abs() <= cfg['slope_caliper_deg'] + 1e-9).all(), 'slope caliper violated')
check(((c.elevation - c.elevation_pos).abs() <= cfg['elevation_caliper_m'] + 1e-9).all(), 'elevation caliper violated')
check((data.slope >= cfg['minimum_slope_deg']).all(), 'slope below minimum')
check(data.aspect.between(0, 360).all() and data.slope.between(0, 90).all(), 'terrain range')
check(np.allclose(data.aspect_sin ** 2 + data.aspect_cos ** 2, 1), 'aspect sin/cos not unit')
min_sep = []
for _, d in ctrl.groupby('event_group_id'):
    xy = d[['x', 'y']].to_numpy()
    dd = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    min_sep.append(dd[np.triu_indices(len(xy), 1)].min())
check(min(min_sep) >= cfg['control_separation_m'], 'control separation violated')
# Controls must not sit on top of any positive of the dataset (subset of inventory buffer check)
nearest_pos = cKDTree(pos[['x', 'y']].to_numpy()).query(ctrl[['x', 'y']].to_numpy())[0]
check(nearest_pos.min() >= cfg['exclusion_extent_buffer_m'], 'control within buffer of a dataset positive')

# Temporal: every predictor window ends before local midnight of t0
last = pd.to_datetime(data.weather_last_timestamp, utc=True)
t0 = data.event_date.map(cutoff)
check((last < t0).all(), 'weather timestamp at/after t0')
check((data.weather_hours_60d == 1438).all(), 'unexpected retained hours')
check((data.weather_grid_distance_m <= 800).all(), 'weather cell too far')
for w in (1, 3, 7, 14, 30, 60):
    check((data[f'rain_sum_{w}d'] >= 0).all(), f'negative rain {w}d')
for a, b in zip((1, 3, 7, 14, 30), (3, 7, 14, 30, 60)):
    check((data[f'rain_sum_{b}d'] + 1e-6 >= data[f'rain_sum_{a}d']).all(), f'rain sums not nested {a}/{b}')
    check((data[f'rain_max_hour_{b}d'] + 1e-6 >= data[f'rain_max_hour_{a}d']).all(), f'rain max not nested {a}/{b}')
pairs_same_cell = int(((ctrl.set_index('event_group_id')[['weather_grid_lon', 'weather_grid_lat']].round(6)
                        == p[['weather_grid_lon', 'weather_grid_lat']].round(6).reindex(ctrl.event_group_id).values).all(axis=1)).sum())

# Dependence rule re-checked independently: no two positives <=3 days apart or <2 km in different clusters
pd_dates = pd.to_datetime(pos.event_date).to_numpy()
pxy = pos[['x', 'y']].to_numpy()
cl = pos.dependence_cluster.to_numpy()
for i in range(len(pos)):
    for j in range(i):
        linked = abs((pd_dates[i] - pd_dates[j]) / np.timedelta64(1, 'D')) <= 3 or np.hypot(*(pxy[i] - pxy[j])) < 2000
        if linked and cl[i] != cl[j]:
            errors.append(f'dependence rule split {pos.event_group_id.iloc[i]}/{pos.event_group_id.iloc[j]}')
for column in ('event_group_id', 'dependence_cluster'):
    check(data.groupby(column).partition.nunique().max() == 1, f'{column} crosses original partitions')

out['dataset'] = {
    'identity': latest['identity'], 'samples': len(data), 'positives': len(pos), 'controls': len(ctrl),
    'event_groups': int(data.event_group_id.nunique()), 'dependence_clusters': int(data.dependence_cluster.nunique()),
    'date_range': [str(pos.event_date.min()), str(pos.event_date.max())],
    'unique_event_dates': int(pos.event_date.nunique()),
    'years': pos.event_date.astype(str).str[:4].value_counts().sort_index().to_dict(),
    'states': pos.state.value_counts().to_dict(),
    'process_types': pos.process_type.value_counts().to_dict(),
    'source_position_upper_m': {str(k): int(v) for k, v in pos.source_position_upper_m.value_counts().sort_index().items()},
    'largest_cluster_events': int(pos.dependence_cluster.value_counts().max()),
    'cluster_sizes_events': sorted(pos.dependence_cluster.value_counts().tolist(), reverse=True),
    'crs_roundtrip_max_error_m': crs_err,
    'control_distance_m': {'min': float(dist.min()), 'median': float(dist.median()), 'max': float(dist.max())},
    'min_control_separation_m': float(min(min_sep)),
    'min_control_to_any_dataset_positive_m': float(nearest_pos.min()),
    'abs_slope_diff_deg_median': float((c.slope - c.slope_pos).abs().median()),
    'abs_elev_diff_m_median': float((c.elevation - c.elevation_pos).abs().median()),
    'aspect_diff_deg_median': float(np.median(asp)),
    'control_pairs_sharing_positive_weather_cell': pairs_same_cell,
    'weather_last_timestamp_max_lag_before_t0_h': float(((t0 - last).dt.total_seconds() / 3600).min()),
    'static_ranges': {k: [float(data[k].min()), float(data[k].max())] for k in ('elevation', 'slope', 'aspect')},
}
status = json.loads((RUN / 'status.json').read_text())
reasons = pd.Series([s.get('reason', 'complete').split(':')[0] for s in (status['status'] if isinstance(status, dict) else status)]).value_counts().to_dict()
out['dataset']['candidates'] = len(status['status'] if isinstance(status, dict) else status)
out['dataset']['candidate_outcomes'] = reasons

# ---------------------------------------------------------------- original split metrics
split = data.groupby('partition').agg(events=('event_group_id', 'nunique'), clusters=('dependence_cluster', 'nunique'))
out['original_split'] = split.to_dict('index')
test = data[data.partition == 'test'].reset_index(drop=True)
stored = json.loads((ROOT / 'reports/experiment/metrics.json').read_text())
tp = pd.read_parquet(RUN / 'test_predictions.parquet')
recomputed = []
for (model, feats), d in tp.groupby(['model', 'features']):
    m = test.merge(d, on='sample_id', how='left')
    check(m.probability_case_control.notna().all(), f'missing test prediction {model}/{feats}')
    bundle = joblib.load(ROOT / 'models' / latest['identity'] / f'{model}_{feats}.joblib')
    check(list(bundle['model'].classes_) == [0, 1], f'class orientation {model}/{feats}')
    check(not set(bundle['training_sample_ids']) & set(test.sample_id), f'test sample in training {model}/{feats}')
    check(set(data.loc[data.partition == 'train', 'sample_id']) == set(bundle['training_sample_ids']), f'training ids mismatch {model}/{feats}')
    # Re-predict from the saved model: guards against a mislabelled/stale prediction file
    fresh = bundle['model'].predict_proba(test[bundle['features']])[:, 1]
    check(np.allclose(fresh, m.probability_case_control, atol=1e-9), f'saved test predictions differ from saved model {model}/{feats}')
    s = m.probability_case_control
    pw = pairwise(m, s)
    rec = {'model': model, 'features': feats, 'roc_auc': roc_auc_score(m.label, s), 'average_precision': average_precision_score(m.label, s),
           'within_group_auc': pw.auc.mean(), 'mean_controls_beaten': pw.beaten.mean(), 'mean_positive_rank': pw['rank'].mean(),
           'first_place_strict': float((pw.beaten == 5).mean())}
    ref = next(r['test'] for r in stored['models'] if r['model'] == model and r['features'] == feats)
    for k in ('roc_auc', 'average_precision', 'within_group_auc'):
        check(abs(ref[k] - rec[k]) < 1e-9, f'stored test {k} not reproducible {model}/{feats}')
    full = project_metrics(m, s.to_numpy())
    for k in ('precision', 'recall', 'f1', 'balanced_accuracy'):
        check(abs(ref[k] - full[k]) < 1e-9, f'stored test {k} not reproducible {model}/{feats}')
    rec.update({k: full[k] for k in ('precision', 'recall', 'f1', 'balanced_accuracy', 'confusion_matrix')})
    recomputed.append(rec)
out['original_test_recomputed'] = recomputed

# ---------------------------------------------------------------- stability V0.2
splits = pd.read_parquet(STAB / 'splits.parquet')
dev_ids = set(data.loc[data.partition != 'test', 'sample_id'])
check(set(splits.sample_id) == dev_ids, 'stability splits are not exactly the development samples')
check(not set(splits.sample_id) & set(test.sample_id), 'original test sample inside stability analysis')
check((splits.groupby(['repetition', 'sample_id']).size() == 1).all(), 'sample in more than one fold')
check((splits.groupby(['repetition', 'dependence_cluster']).fold.nunique() == 1).all(), 'cluster crosses stability folds')
check(sorted(splits.seed.unique().tolist()) == [11, 23, 37, 51, 71], 'unexpected seeds')
pp = pd.read_parquet(STAB / 'primary_predictions.parquet')
fits = pp.groupby(['repetition', 'fold', 'model', 'features']).ngroups
check(fits == 180, f'primary fits {fits} != 180')
check(len(pp) == 5 * 9 * 270, 'primary prediction row count')
# Training ids of every primary fit must be disjoint from its predicted samples
leaks = 0
for f in (STAB / 'fits/primary').glob('*/*/*/complete.json'):
    spec = json.loads(f.read_text())['spec']
    rep, fold = map(int, f.parts[-4].lstrip('r').split('_f'))
    held = set(splits[(splits.repetition == rep) & (splits.fold == fold)].sample_id)
    leaks += bool(set(spec['train_ids']) & held)
    check(set(spec['train_ids']) == dev_ids - held, f'train ids are not complement of fold {f.parts[-4]}')
check(leaks == 0, f'{leaks} primary fits trained on held-out samples')
stored_stab = pd.read_csv(ROOT / 'reports/stability_v02/stability_metrics.csv')
rows = []
for (rep, model, feats), d in pp.groupby(['repetition', 'model', 'features']):
    d = d.reset_index(drop=True)
    pw = pairwise(d, d.probability)
    r = {'repetition': rep, 'model': model, 'features': feats, 'roc_auc': roc_auc_score(d.label, d.probability),
         'average_precision': average_precision_score(d.label, d.probability), 'within_group_auc': pw.auc.mean(),
         'mean_controls_beaten': pw.beaten.mean(), 'first_place_strict': float((pw.beaten == 5).mean())}
    ref = stored_stab[(stored_stab.repetition == rep) & (stored_stab.model == model) & (stored_stab.features == feats)].iloc[0]
    for k in ('roc_auc', 'average_precision', 'within_group_auc'):
        check(abs(ref[k] - r[k]) < 1e-9, f'stability {k} not reproducible r{rep} {model}/{feats}')
    rows.append(r)
stab = pd.DataFrame(rows)
summary = stab.groupby(['model', 'features'])[['roc_auc', 'average_precision', 'within_group_auc', 'mean_controls_beaten']].agg(['median', 'min', 'max'])
summary.columns = [f'{a}_{b}' for a, b in summary.columns]
out['stability_recomputed'] = summary.round(4).reset_index().to_dict('records')
wide = stab.pivot_table(index=['repetition', 'model'], columns='features', values=['average_precision', 'within_group_auc'])
delta = []
for model in stab.model.unique():
    w = wide.xs(model, level='model')
    for k in ('average_precision', 'within_group_auc'):
        dd = w[(k, 'combined')] - w[(k, 'static')]
        delta.append({'model': model, 'metric': k, 'combined_minus_static_median': float(dd.median()),
                      'min': float(dd.min()), 'max': float(dd.max()), 'repetitions_improved': int((dd > 0).sum())})
out['stability_weather_delta'] = delta

out['errors'] = errors
out['status'] = 'PASS' if not errors else 'FAIL'
target = ROOT / 'reports/verification/independent_checks.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(out, indent=2, default=lambda o: o.item() if hasattr(o, 'item') else str(o)), encoding='utf-8')
print(out['status'], len(errors), 'errors')
for e in errors[:30]:
    print(' -', e)
