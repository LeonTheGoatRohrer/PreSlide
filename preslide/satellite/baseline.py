"""Event-held-out baselines on the satellite change table: logistic regression and gradient boosting, plus shortcut checks."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from ..common import write_json
from .features import model_feature_names, ring_only_names
from .paths import SAT_DATA, SAT_REPORT, guard, config

NUISANCE = ['days_before', 'days_after', 'doy_gap', 'before_core_cloud', 'before_core_snow', 'after_core_cloud',
            'after_core_snow', 'before_patch_cloud', 'after_patch_cloud']


NON_FEATURE = {'group_size', 'draw_index', 'distance_to_nearest_inventory_event_m'}   # bookkeeping columns after the feature block


def feature_columns(frame):
    first = list(frame.columns).index('coreg_peak_ratio') + 1
    return [c for c in frame.columns[first:] if c not in NON_FEATURE]


def make_model(kind, cfg):
    if kind == 'logistic_regression':
        p = cfg['models']['logistic_regression']
        return make_pipeline(SimpleImputer(strategy='median'), StandardScaler(),
                             LogisticRegression(C=p['C'], class_weight=p['class_weight'], max_iter=p['max_iter']))
    p = cfg['models']['hist_gradient_boosting']
    return HistGradientBoostingClassifier(**p)


def within_group_metrics(frame, score):
    """Rank of the positive among its group: within-group AUC (fraction of controls below it), top-1 rate, mean rank."""
    aucs, top1, ranks = [], [], []
    for _, g in frame.assign(score=score).groupby('event_group_id'):
        p = g.loc[g['label'] == 1, 'score'].iloc[0]
        c = g.loc[g['label'] == 0, 'score'].to_numpy()
        auc = float(((c < p).sum() + 0.5 * (c == p).sum()) / len(c))
        aucs.append(auc)
        rank = 1 + (c > p).sum() + 0.5 * (c == p).sum()
        ranks.append(float(rank))
        top1.append(float(rank == 1))
    return {'within_group_auc': float(np.mean(aucs)), 'top1_rate': float(np.mean(top1)), 'mean_rank': float(np.mean(ranks)),
            'groups': len(aucs), 'per_group_auc': aucs}


def unit_weighted(frame, per_group):
    """Mean within-group AUC weighting every independence unit equally (storms with many events do not dominate)."""
    g = frame[frame['label'] == 1][['event_group_id', 'independence_unit']].reset_index(drop=True)
    g['auc'] = per_group
    return float(g.groupby('independence_unit')['auc'].mean().mean())


def cross_validated_scores(frame, cols, kind, cfg, seed=0, fit_mask=None):
    """Out-of-fold scores for every row; models are fit only on rows with `fit_mask` True (default: all rows),
    so extra negatives can be scored by a model that never saw them."""
    groups = frame['independence_unit'].to_numpy()
    fit_mask = np.ones(len(frame), dtype=bool) if fit_mask is None else np.asarray(fit_mask, dtype=bool)
    n_units = len(np.unique(groups))
    k = min(cfg['models']['cv_folds'], n_units)
    if k < 2:
        raise ValueError('at least two independence units are required for event-held-out evaluation')
    scores = np.full(len(frame), np.nan)
    X, y = frame[cols].to_numpy(dtype=float), frame['label'].to_numpy()
    # GroupKFold is deterministic; shuffle unit order once with the seed to vary fold composition across repeats.
    rng = np.random.default_rng(seed)
    unit_ids = {u: i for i, u in enumerate(rng.permutation(np.unique(groups)))}
    g = np.array([unit_ids[u] for u in groups])
    for tr, te in GroupKFold(n_splits=k).split(X, y, g):
        assert not set(groups[tr]) & set(groups[te]), 'independence unit leaked across folds'
        tr = tr[fit_mask[tr]]
        model = make_model(kind, cfg).fit(X[tr], y[tr])
        scores[te] = model.predict_proba(X[te])[:, 1]
    return scores


def evaluate(frame, cols, kind, cfg, seed=0):
    s = cross_validated_scores(frame, cols, kind, cfg, seed)
    y = frame['label'].to_numpy()
    wg = within_group_metrics(frame, s)
    return {'roc_auc': float(roc_auc_score(y, s)), 'average_precision': float(average_precision_score(y, s)),
            'within_group_auc': wg['within_group_auc'], 'within_group_auc_unit_weighted': unit_weighted(frame, wg['per_group_auc']),
            'top1_rate': wg['top1_rate'], 'mean_rank': wg['mean_rank'], 'groups': wg['groups'],
            'per_group_auc': wg['per_group_auc'], 'scores': s.tolist()}


def permutation_null(frame, cols, cfg, draws=100, seed=1):
    """Within-group label permutation: which member is 'the event' is reshuffled, models refit, metric recomputed."""
    rng = np.random.default_rng(seed)
    out = []
    base = frame.copy()
    for d in range(draws):
        perm = base.copy()
        for _, idx in perm.groupby('event_group_id').groups.items():
            labels = perm.loc[idx, 'label'].to_numpy()
            perm.loc[idx, 'label'] = rng.permutation(labels)
        s = cross_validated_scores(perm, cols, 'logistic_regression', cfg, seed=d)
        out.append(within_group_metrics(perm, s)['within_group_auc'])
    return out


def importance(frame, cols, cfg):
    X, y = frame[cols].to_numpy(dtype=float), frame['label'].to_numpy()
    lr = make_model('logistic_regression', cfg).fit(X, y)
    coef = lr[-1].coef_[0]
    order = np.argsort(-np.abs(coef))
    return [{'feature': cols[i], 'standardized_coefficient': float(coef[i])} for i in order]


def run(seeds=(0, 1, 2), null_draws=100):
    cfg = config()
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    sizes = frame.groupby('event_group_id')['label'].count()
    all_cols = feature_columns(frame)
    model_cols = model_feature_names(all_cols)
    sets = {'change_features': model_cols, 'ring_only_shortcut': ring_only_names(all_cols),
            'nuisance_only_shortcut': [c for c in NUISANCE if c in frame.columns],
            'contrast_only': [c for c in model_cols if 'contrast' in c]}
    results = {'dataset': {'rows': len(frame), 'groups': int(frame['event_group_id'].nunique()),
                           'independence_units': int(frame['independence_unit'].nunique()),
                           'positives': int(frame['label'].sum()), 'controls': int((frame['label'] == 0).sum()),
                           'units_by_partition': frame[frame.label == 1].groupby('v04_partition')['independence_unit'].nunique().to_dict()},
               'feature_sets': {k: v for k, v in sets.items()}, 'models': {},
               'chance': {'within_group_auc': 0.5, 'top1_rate': float((1 / sizes).mean()), 'mean_rank': float(((sizes + 1) / 2).mean())}}
    oof = {}
    for set_name, cols in sets.items():
        for kind in ('logistic_regression', 'hist_gradient_boosting'):
            reps = [evaluate(frame, cols, kind, cfg, seed) for seed in seeds]
            key = f'{set_name}/{kind}'
            results['models'][key] = {m: {'mean': float(np.mean([r[m] for r in reps])), 'per_seed': [r[m] for r in reps]}
                                      for m in ('roc_auc', 'average_precision', 'within_group_auc', 'within_group_auc_unit_weighted', 'top1_rate', 'mean_rank')}
            oof[key] = reps[0]
    null = permutation_null(frame, model_cols, cfg, draws=null_draws)
    observed = results['models']['change_features/logistic_regression']['within_group_auc']['mean']
    results['permutation_null'] = {'draws': null_draws, 'metric': 'within_group_auc (logistic regression, change_features, seed 0..)',
                                   'null_mean': float(np.mean(null)), 'null_95': float(np.percentile(null, 95)),
                                   'p_upper': float((np.sum(np.array(null) >= observed) + 1) / (len(null) + 1)), 'observed': observed}
    results['importance_logistic_regression'] = importance(frame, model_cols, cfg)
    results['per_group'] = [{'event_group_id': g, 'independence_unit': u, 'state': s, 'event_day': d,
                             'within_group_auc_lr': a, 'within_group_auc_hgb': b}
                            for g, u, s, d, a, b in zip(frame[frame.label == 1]['event_group_id'], frame[frame.label == 1]['independence_unit'],
                                                        frame[frame.label == 1]['state'], frame[frame.label == 1]['event_day'],
                                                        oof['change_features/logistic_regression']['per_group_auc'],
                                                        oof['change_features/hist_gradient_boosting']['per_group_auc'])]
    guard(SAT_REPORT)
    write_json(SAT_REPORT / 'baseline_results.json', {k: v for k, v in results.items() if k != 'per_group'})
    write_json(SAT_DATA / 'tables/baseline_per_group.json', results['per_group'])      # local: contains source ids
    frame.assign(score_lr=oof['change_features/logistic_regression']['scores'],
                 score_hgb=oof['change_features/hist_gradient_boosting']['scores'])[['sample_id', 'event_group_id', 'label', 'score_lr', 'score_hgb']] \
        .to_parquet(SAT_DATA / 'tables/baseline_oof_scores.parquet', index=False)
    return results


def within_group_vs_random(frame, score):
    """Per event: fraction of its RANDOM_LANDSCAPE points scored below the positive (chance 0.5), and whether the
    positive ranks first among controls + random points."""
    aucs, top1 = [], []
    for _, g in frame.assign(score=score).groupby('event_group_id'):
        p = g.loc[g['label'] == 1, 'score'].iloc[0]
        rnd = g.loc[g['sample_type'] == 'RANDOM_LANDSCAPE', 'score'].to_numpy()
        if len(rnd) == 0:
            continue
        aucs.append(float(((rnd < p).sum() + 0.5 * (rnd == p).sum()) / len(rnd)))
        neg = g.loc[g['label'] == 0, 'score'].to_numpy()
        top1.append(float((neg > p).sum() == 0))
    return {'positive_vs_random_auc': float(np.mean(aucs)), 'top1_vs_controls_and_random': float(np.mean(top1)), 'events_with_random': len(aucs)}


def evaluate_with_random(frame, cols, kind, cfg, seed, fit_random):
    """`frame` = groups + RANDOM_LANDSCAPE rows. Scores are out-of-fold over independence units; the model is fit
    with or without the random rows. Metrics on controls keep their original definition for comparability."""
    is_random = (frame['sample_type'] == 'RANDOM_LANDSCAPE').to_numpy()
    s = cross_validated_scores(frame, cols, kind, cfg, seed, fit_mask=None if fit_random else ~is_random)
    y = frame['label'].to_numpy()
    groups_only = frame[~is_random]
    wg = within_group_metrics(groups_only, s[~is_random])
    vr = within_group_vs_random(frame, s)
    return {'roc_auc_controls': float(roc_auc_score(y[~is_random], s[~is_random])),
            'roc_auc_controls_and_random': float(roc_auc_score(y, s)),
            'average_precision_controls_and_random': float(average_precision_score(y, s)),
            'within_group_auc': wg['within_group_auc'], 'within_group_auc_unit_weighted': unit_weighted(groups_only, wg['per_group_auc']),
            'top1_rate': wg['top1_rate'], 'mean_rank': wg['mean_rank'],
            'positive_vs_random_auc': vr['positive_vs_random_auc'], 'top1_vs_controls_and_random': vr['top1_vs_controls_and_random'],
            'random_mean_score': float(np.mean(s[is_random])), 'control_mean_score': float(np.mean(s[(y == 0) & ~is_random])),
            'positive_mean_score': float(np.mean(s[y == 1])),
            'random_scored_above_median_positive': float(np.mean(s[is_random] > np.median(s[y == 1]))),
            'groups': wg['groups'], 'events_with_random': vr['events_with_random']}


def run_random_landscape(seeds=(0, 1, 2)):
    """Baseline with and without the RANDOM_LANDSCAPE hard negatives (same folds, same feature set)."""
    cfg = config()
    groups = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    rl = pd.read_parquet(SAT_DATA / 'tables/random_landscape.parquet')
    rl = rl[rl['event_group_id'].isin(groups['event_group_id'])]
    frame = pd.concat([groups, rl], ignore_index=True)
    cols = model_feature_names(feature_columns(groups))
    metrics = ('roc_auc_controls', 'roc_auc_controls_and_random', 'average_precision_controls_and_random', 'within_group_auc',
               'within_group_auc_unit_weighted', 'top1_rate', 'mean_rank', 'positive_vs_random_auc', 'top1_vs_controls_and_random',
               'random_mean_score', 'control_mean_score', 'positive_mean_score', 'random_scored_above_median_positive')
    results = {'dataset': {'group_rows': len(groups), 'random_rows': int(len(rl)), 'groups': int(groups['event_group_id'].nunique()),
                           'events_with_random': int(rl['event_group_id'].nunique()),
                           'random_per_event': rl.groupby('event_group_id').size().value_counts().sort_index().to_dict(),
                           'random_distance_to_positive_m': {'min': float(rl['distance_to_positive_m'].min()), 'median': float(rl['distance_to_positive_m'].median()), 'max': float(rl['distance_to_positive_m'].max())},
                           'random_distance_to_nearest_inventory_event_m': {'min': float(rl['distance_to_nearest_inventory_event_m'].min()), 'median': float(rl['distance_to_nearest_inventory_event_m'].median())}},
               'feature_set': cols, 'models': {},
               'chance': {'within_group_auc': 0.5, 'positive_vs_random_auc': 0.5,
                          'top1_vs_controls_and_random': float((1 / frame.groupby('event_group_id').size()).mean())}}
    for kind in ('logistic_regression', 'hist_gradient_boosting'):
        for fit_random in (False, True):
            reps = [evaluate_with_random(frame, cols, kind, cfg, seed, fit_random) for seed in seeds]
            key = f"{kind}/{'trained_with_random_landscape' if fit_random else 'trained_controls_only'}"
            results['models'][key] = {m: {'mean': float(np.mean([r[m] for r in reps])), 'per_seed': [r[m] for r in reps]} for m in metrics}
    lr_with = make_model('logistic_regression', cfg).fit(frame[cols].to_numpy(dtype=float), frame['label'].to_numpy())
    coef = lr_with[-1].coef_[0]
    order = np.argsort(-np.abs(coef))
    results['importance_logistic_regression_with_random'] = [{'feature': cols[i], 'standardized_coefficient': float(coef[i])} for i in order[:15]]
    guard(SAT_REPORT)
    write_json(SAT_REPORT / 'baseline_results_random_landscape.json', results)
    return results
