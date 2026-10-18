"""EXPLORATORY cause analysis after the failed Phase 4 gate of susceptibility_v01. Changes no registered choice.

python scripts/diagnose_susceptibility_phase4.py  ->  reports/susceptibility_v01/phase4_cause_analysis.json
Uses the stored samples, the stored LOIO predictions and the stored LOIO models only (no refit).
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.common import write_json  # noqa: E402
from preslide.susceptibility import evaluate as E  # noqa: E402
from preslide.susceptibility.paths import MODELS, REPORT, config  # noqa: E402
from preslide.v04.pipeline import load  # noqa: E402


def main():
    cfg = config()
    feats = cfg['features_terrain']
    data = E.samples(cfg)
    pred = load(E.PREDICTIONS / 'loio_predictions.parquet')
    inventories = sorted(data.dataset.unique())
    prim = cfg['model_spec']['primary_model']
    out = {'label': 'EXPLORATORY diagnostics after a failed gate; not a result and not used to change the design',
           'per_direction_minus_slope': {}, 'univariate_auc_within_inventory': {}, 'shift_between_inventories': {},
           'permutation_importance_primary': {}}
    names = list(E.BASELINES) + E.MODEL_NAMES
    for held in inventories:
        p = pred[pred.dataset == held]
        y = p.label.to_numpy()
        rng = np.random.default_rng([cfg['seeds']['bootstrap'], inventories.index(held)])   # same draws as loio
        w = E.block_weights(p.block_id.to_numpy(), cfg['metrics']['intervals']['n_resamples'], rng)
        b = E.bootstrap_aucs(y, {k: p[f'score_{k}'].to_numpy() for k in names}, w)
        out['per_direction_minus_slope'][held] = {
            k: {'point': float(roc_auc_score(y, p[f'score_{k}']) - roc_auc_score(y, p['score_slope_only'])),
                'interval_95': E.interval(b[k] - b['slope_only'])} for k in names if k != 'slope_only'}
        d = data[data.dataset == held]
        out['univariate_auc_within_inventory'][held] = {
            f: float(roc_auc_score(d.label, d[f].fillna(d[f].median()))) for f in feats}
        model = joblib.load(MODELS / f'loio_test-{held}_{prim}.joblib')
        sub = d.sample(min(len(d), 6000), random_state=cfg['seeds']['folds'])
        imp = permutation_importance(model, sub[feats], sub.label, scoring='roc_auc', n_repeats=5,
                                     random_state=cfg['seeds']['folds'])
        out['permutation_importance_primary'][held] = {f: {'mean_auc_drop': float(m), 'sd': float(s)}
                                                        for f, m, s in zip(feats, imp.importances_mean, imp.importances_std)}
    a, c = (data[data.dataset == i] for i in inventories)
    for label, name in ((1, 'positives'), (0, 'background')):
        xa, xc = a[a.label == label], c[c.label == label]
        out['shift_between_inventories'][name] = {
            f: {inventories[0]: float(xa[f].median()), inventories[1]: float(xc[f].median()),
                'standardized_mean_difference': float((xa[f].mean() - xc[f].mean()) /
                                                      np.sqrt((xa[f].var() + xc[f].var()) / 2))} for f in feats}
    write_json(REPORT / 'phase4_cause_analysis.json', out)
    print(json.dumps(out, indent=1)[:12000])


if __name__ == '__main__':
    main()
