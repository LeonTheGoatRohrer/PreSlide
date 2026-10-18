"""Phases 4-5: baselines, models and spatial evaluation (design: config 'evaluation' and 'model_spec', Amendment 3).

  python -m preslide.susceptibility.evaluate loio      primary leave-one-inventory-out + Phase 4 gate
  python -m preslide.susceptibility.evaluate blockcv   secondary 5-fold spatial block CV inside each inventory

Scores are relative ranks, not probabilities. Every model and baseline evaluated is reported.
"""
import argparse
import json

import joblib
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..common import write_json
from ..v04.pipeline import load, save
from .paths import DATA, MODELS, REPORT, config, guard

PREDICTIONS = DATA / 'predictions'
MODEL_NAMES = ['hist_gradient_boosting', 'random_forest', 'logistic_regression', 'small_mlp']
BASELINES = {'slope_only': ['slope_deg'], 'elevation_only': ['elevation_m'],
             'simple_logistic': ['slope_deg', 'elevation_m', 'profile_curvature', 'plan_curvature']}


def samples(cfg):
    frames = []
    for name, d in cfg['registry']['datasets'].items():
        if d['role'] != 'development':
            continue
        f = load(DATA / 'samples' / f'{name}.parquet')
        if f is None:
            raise RuntimeError(f'{name}: samples missing')
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def make(name, spec, seed):
    if name == 'hist_gradient_boosting':
        p = {k: v for k, v in spec[name].items() if k != 'random_state'}
        return HistGradientBoostingClassifier(**p, random_state=seed)
    if name == 'random_forest':
        p = {k: v for k, v in spec[name].items() if k != 'random_state'}
        return make_pipeline(SimpleImputer(strategy='median'), RandomForestClassifier(**p, random_state=seed))
    if name == 'small_mlp':
        p = {k: v for k, v in spec[name].items() if k != 'random_state'}
        p['hidden_layer_sizes'] = tuple(p['hidden_layer_sizes'])
        return make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), MLPClassifier(**p, random_state=seed))
    return make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(**spec['logistic_regression']))


def fit_predict(name, train, test, cfg):
    """Fit on `train` only (imputation and scaling inside the pipeline) and score `test`."""
    spec, seed = cfg['model_spec'], cfg['seeds']['folds']
    cols = BASELINES.get(name, cfg['features_terrain'])
    model = make('logistic_regression' if name in BASELINES else name, spec, seed)
    model.fit(train[cols], train['label'])
    return model, model.predict_proba(test[cols])[:, 1]


def boyce(y, s, windows=101, width=0.1):
    """Continuous Boyce index (Hirzel et al. 2006) on min-max scaled scores."""
    s = np.asarray(s, float)
    span = s.max() - s.min()
    z = (s - s.min()) / span if span > 0 else np.zeros_like(s)
    pres, back = z[y == 1], z[y == 0]
    centres = np.linspace(width / 2, 1 - width / 2, windows)
    ratio, keep = [], []
    for c in centres:
        lo, hi = c - width / 2, c + width / 2
        e = np.mean((back >= lo) & (back <= hi))
        if e > 0:
            ratio.append(np.mean((pres >= lo) & (pres <= hi)) / e)
            keep.append(c)
    return float(spearmanr(keep, ratio).statistic) if len(keep) > 2 else float('nan')


def threshold_metrics(y, s, top_fraction):
    t = np.quantile(s[y == 0], 1 - top_fraction)
    pred = (s > t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    recall = tp / (tp + fn) if tp + fn else float('nan')
    precision = tp / (tp + fp) if tp + fp else float('nan')
    spec_ = tn / (tn + fp) if tn + fp else float('nan')
    return {'threshold': float(t), 'recall_top_area': float(recall), 'precision': float(precision),
            'f1': float(2 * precision * recall / (precision + recall)) if precision + recall else 0.0,
            'balanced_accuracy': float((recall + spec_) / 2), 'confusion_matrix_tn_fp_fn_tp': [int(tn), int(fp), int(fn), int(tp)]}


def point_metrics(y, s, cfg):
    return {'roc_auc': float(roc_auc_score(y, s)), 'average_precision_at_1_to_1': float(average_precision_score(y, s)),
            'boyce': boyce(y, s), **threshold_metrics(y, s, cfg['metrics']['top_area_fraction'])}


def block_weights(blocks, n, rng):
    """n bootstrap resamples of blocks: per-sample weight = how often its block was drawn."""
    codes, uniq = pd.factorize(blocks)
    draws = rng.integers(0, len(uniq), size=(n, len(uniq)))
    counts = np.stack([np.bincount(d, minlength=len(uniq)) for d in draws])
    return counts[:, codes]


def bootstrap_aucs(y, scores, weights):
    """AUC per resample for every score column (paired: same weights)."""
    return {k: np.array([roc_auc_score(y, s, sample_weight=w) if ((w > 0) & (y == 1)).any() and ((w > 0) & (y == 0)).any()
                         else np.nan for w in weights]) for k, s in scores.items()}


def permutation_null(y, s, blocks, n, rng):
    codes = pd.factorize(blocks)[0]
    order = np.argsort(codes, kind='stable')
    bounds = np.flatnonzero(np.diff(codes[order])) + 1
    groups = np.split(order, bounds)
    out = np.empty(n)
    for k in range(n):
        perm = y.copy()
        for g in groups:
            perm[g] = rng.permutation(y[g])
        out[k] = roc_auc_score(perm, s)
    return out


def interval(a):
    a = a[np.isfinite(a)]
    return [float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975))]


def split_loio(data, held):
    """Training = every other inventory; the held-out inventory never enters training."""
    return data[data.dataset != held], data[data.dataset == held].reset_index(drop=True)


def loio():
    cfg = config()
    out_path = PREDICTIONS / 'loio_predictions.parquet'
    if out_path.exists():
        raise RuntimeError(f'{out_path} exists; predictions are write-once')
    ev = cfg['evaluation']
    data = samples(cfg)
    names = list(BASELINES) + MODEL_NAMES
    inventories = sorted(data.dataset.unique())
    n_boot, n_perm = cfg['metrics']['intervals']['n_resamples'], cfg['metrics']['null_reference']['n_permutations']
    per, boots, preds = {}, {}, []
    for held in inventories:
        train, test = split_loio(data, held)
        scores = {}
        for name in names:
            model, scores[name] = fit_predict(name, train, test, cfg)
            path = guard(MODELS) / f'loio_test-{held}_{name}.joblib'
            joblib.dump(model, path)
        y = test.label.to_numpy()
        rng = np.random.default_rng([cfg['seeds']['bootstrap'], inventories.index(held)])
        w = block_weights(test.block_id.to_numpy(), n_boot, rng)
        boots[held] = bootstrap_aucs(y, scores, w)
        prim = cfg['model_spec']['primary_model']
        null = permutation_null(y, scores[prim], test.block_id.to_numpy(), n_perm,
                                np.random.default_rng([cfg['seeds']['permutation'], inventories.index(held)]))
        share = test[test.label == 1].block_id.value_counts(normalize=True)
        per[held] = {'trained_on': sorted(train.dataset.unique()), 'n_positives': int(y.sum()), 'n_background': int((y == 0).sum()),
                     'independent_units_5km_blocks': int(test.block_id.nunique()),
                     'largest_block_positive_share': float(share.iloc[0]),
                     'metrics': {k: point_metrics(y, s, cfg) for k, s in scores.items()},
                     'auc_interval_95': {k: interval(v) for k, v in boots[held].items()},
                     'primary_null_auc_95': float(np.quantile(null, 0.95)),
                     'primary_null_p': float((1 + (null >= roc_auc_score(y, scores[prim])).sum()) / (1 + n_perm))}
        if per[held]['largest_block_positive_share'] > 0.2:
            keep = test.block_id != share.index[0]
            per[held]['without_largest_block'] = {k: float(roc_auc_score(y[keep], s[keep])) for k, s in scores.items()}
        pf = test[['sample_id', 'dataset', 'label', 'block_id', 'x', 'y']].copy()
        for k, s in scores.items():
            pf[f'score_{k}'] = s
        preds.append(pf)
    mean_boot = {k: np.nanmean([boots[h][k] for h in inventories], axis=0) for k in names}
    point_mean = {k: float(np.mean([per[h]['metrics'][k]['roc_auc'] for h in inventories])) for k in names}
    prim = cfg['model_spec']['primary_model']
    diffs = {k: {'point': point_mean[prim] - point_mean[k], 'interval_95': interval(mean_boot[prim] - mean_boot[k])}
             for k in names if k != prim}
    gate_low = diffs['slope_only']['interval_95'][0]
    result = {'design': ev['primary_design'], 'statistic': ev['primary_statistic'], 'primary_model': prim,
              'per_held_out_inventory': per,
              'mean_auc': {k: {'point': point_mean[k], 'interval_95': interval(mean_boot[k])} for k in names},
              'primary_minus_other_mean_auc': diffs,
              'comparisons_counted': len(names) * len(inventories),
              'phase4_gate': {'rule': ev['phase4_gate'], 'lower_bound': gate_low, 'passed': bool(gate_low > 0)}}
    pred = pd.concat(preds, ignore_index=True)
    guard(PREDICTIONS)
    save(pred, out_path, {'design': 'loio'})
    write_json(guard(REPORT) / 'phase4_loio_results.json', result)
    return result


def block_folds(blocks, k, seed):
    uniq = np.array(sorted(set(blocks)))
    order = np.random.default_rng(seed).permutation(len(uniq))
    fold_of = {uniq[i]: n % k for n, i in enumerate(order)}
    return np.array([fold_of[b] for b in blocks])


def purge(train, test, gap_m):
    """Training samples closer than gap_m to any test sample are removed."""
    d, _ = cKDTree(test[['x', 'y']].to_numpy()).query(train[['x', 'y']].to_numpy(), k=1)
    return train[d >= gap_m]


def blockcv():
    cfg = config()
    path = PREDICTIONS / 'blockcv_predictions.parquet'
    if path.exists():
        raise RuntimeError(f'{path} exists; predictions are write-once')
    data = samples(cfg)
    names = list(BASELINES) + MODEL_NAMES
    gap = cfg['splits']['gap_between_train_and_test_blocks_m']
    out, preds = {}, []
    for inv in sorted(data.dataset.unique()):
        d = data[data.dataset == inv].reset_index(drop=True)
        folds = block_folds(d.block_id.to_numpy(), 5, cfg['seeds']['folds'])
        oof = {k: np.full(len(d), np.nan) for k in names}
        purged = []
        for f in range(5):
            test = d[folds == f]
            train = purge(d[folds != f], test, gap)
            purged.append(int((folds != f).sum() - len(train)))
            for k in names:
                oof[k][test.index] = fit_predict(k, train, test, cfg)[1]
        y = d.label.to_numpy()
        w = block_weights(d.block_id.to_numpy(), cfg['metrics']['intervals']['n_resamples'],
                          np.random.default_rng([cfg['seeds']['bootstrap'], 100 + sorted(data.dataset.unique()).index(inv)]))
        b = bootstrap_aucs(y, oof, w)
        prim = cfg['model_spec']['primary_model']
        out[inv] = {'folds': 5, 'independent_units_5km_blocks': int(d.block_id.nunique()), 'purged_training_samples_per_fold': purged,
                    'metrics': {k: point_metrics(y, s, cfg) for k, s in oof.items()},
                    'auc_interval_95': {k: interval(v) for k, v in b.items()},
                    'primary_minus_other_auc': {k: {'point': float(roc_auc_score(y, oof[prim]) - roc_auc_score(y, oof[k])),
                                                     'interval_95': interval(b[prim] - b[k])} for k in names if k != prim}}
        pf = d[['sample_id', 'dataset', 'label', 'block_id', 'x', 'y']].copy()
        pf['fold'] = folds
        for k, s in oof.items():
            pf[f'score_{k}'] = s
        preds.append(pf)
    guard(PREDICTIONS)
    save(pd.concat(preds, ignore_index=True), path, {'design': 'blockcv'})
    write_json(guard(REPORT) / 'phase5_blockcv_results.json', out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['loio', 'blockcv'])
    a = ap.parse_args()
    print(json.dumps(loio() if a.stage == 'loio' else blockcv(), indent=1)[:8000])


if __name__ == '__main__':
    main()
