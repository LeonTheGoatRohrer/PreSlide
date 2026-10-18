"""susceptibility_v02 Phase 4: leave-one-inventory-out within the earthquake arm, confirmatory H1-EQ / H2-EQ.

  python -I scripts/run_susceptibility_v02.py phase4 --pilot   (Gorkha -> Far-Western Nepal code path, seen data, no writes)
  python -I scripts/run_susceptibility_v02.py phase4           (single scoring; write-once predictions, models, report)

Design, models, seeds and the Bonferroni rule are the registered ones (config 'trigger_arms', 'model_spec',
'evaluation', 'hypotheses'). The rain arm is not feasible (rer2023 pending_extent) and is reported as such.
Reuses the v01 evaluation helpers (model construction, block bootstrap, permutation null, Boyce, threshold metrics).
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from ..common import write_json
from ..v04.pipeline import load, save
from .evaluate import block_weights, bootstrap_aucs, boyce, interval, make, permutation_null, threshold_metrics
from .v02 import DATA, MODELS, REPORT, config, cross_trigger_reference, guard, lower_bound_percentile, training_datasets
from .v02_sampling import SAMPLES
from .v02_sensitivity import PGA, model_spec

PREDICTIONS = DATA / 'predictions' / 'phase4_predictions.parquet'
RESULT = REPORT / 'phase4_results.json'
TOP_AREA = 0.2  # registered: recall in the top 20 % area, threshold at the background 80th percentile
CONFIRMATORY_TEST = {'earthquake': 'iburi_2018', 'rain': 'rer2023'}


def model_table(cfg):
    """Registered earthquake-arm models and baselines: name -> (family, features)."""
    terrain = list(cfg['features_terrain'])
    return {'EQ_TERRAIN_PGA': ('hist_gradient_boosting', terrain + [PGA]),
            'EQ_TERRAIN': ('hist_gradient_boosting', terrain),
            'slope_pga_logistic': ('logistic_regression', ['slope_deg', PGA]),
            'slope_only': ('logistic_regression', ['slope_deg']),
            'pga_only': ('logistic_regression', [PGA])}


def samples(dataset):
    frame = load(SAMPLES / f'{dataset}.parquet')
    if frame is None:
        raise RuntimeError(f'{dataset}: v02 samples missing')
    return frame


def fit(family, cols, train, cfg, spec):
    m = make(family, spec, cfg['seeds']['folds'])
    m.fit(train[cols], train['label'])
    return m


def metrics(y, s):
    return {'roc_auc': float(roc_auc_score(y, s)), 'average_precision_at_1_to_1': float(average_precision_score(y, s)),
            'boyce': boyce(y, s), **threshold_metrics(y, s, TOP_AREA)}


def paired(boot, a, b, lower_pct):
    d = boot[a] - boot[b]
    d = d[np.isfinite(d)]
    return {'interval_95': interval(d), 'lower_bound_bonferroni': float(np.percentile(d, lower_pct)),
            'lower_percentile': lower_pct}


def direction(cfg, train_name, test_name, cross_name, k, n_boot, n_perm, store_models=True, use_pga=True):
    """Fit every registered model on `train_name`, the cross-trigger reference (EQ_TERRAIN architecture) on
    `cross_name`, and score `test_name`. Bootstrap/permutation over 5 km blocks of the test inventory."""
    spec = model_spec(cfg)
    table = model_table(cfg)
    if not use_pga:
        table = {k_: v for k_, v in table.items() if PGA not in v[1]}
    train, test = samples(train_name), samples(test_name).reset_index(drop=True)
    if set(train.dataset) & set(test.dataset):
        raise RuntimeError('training and test inventories overlap')
    scores = {}
    for name, (family, cols) in table.items():
        m = fit(family, cols, train, cfg, spec)
        scores[name] = m.predict_proba(test[cols])[:, 1]
        if store_models:
            joblib.dump(m, guard(MODELS) / f'phase4_{name}_train-{train_name}.joblib')
    family, cols = table['EQ_TERRAIN']
    cross = samples(cross_name)
    m = fit(family, cols, cross, cfg, spec)
    xname = f'EQ_TERRAIN_from_{cross_name}'
    scores[xname] = m.predict_proba(test[cols])[:, 1]
    if store_models:
        joblib.dump(m, guard(MODELS) / f'phase4_EQ_TERRAIN_train-{cross_name}.joblib')
    y = test.label.to_numpy()
    blocks = test.block_id.to_numpy()
    w = block_weights(blocks, n_boot, np.random.default_rng([cfg['seeds']['bootstrap'], k]))
    tpi = test['tpi_m'].to_numpy()
    boot = bootstrap_aucs(y, {**scores, 'univariate_tpi': tpi}, w)
    share = test[test.label == 1].block_id.value_counts(normalize=True)
    lower = lower_bound_percentile(cfg)
    res = {'train': train_name, 'test': test_name, 'cross_trigger_train': cross_name,
           'n_positives': int(y.sum()), 'n_background': int((y == 0).sum()),
           'independent_units_5km_blocks': int(len(set(blocks))),
           'largest_block_positive_share': float(share.iloc[0]),
           'metrics': {n: metrics(y, s) for n, s in scores.items()},
           'auc_interval_95': {n: interval(boot[n]) for n in scores},
           'univariate_tpi_auc': {'point': float(roc_auc_score(y, tpi)), 'interval_95': interval(boot['univariate_tpi'])},
           'contrasts': {}}
    pairs = {'H1 terrain+PGA - slope+PGA': ('EQ_TERRAIN_PGA', 'slope_pga_logistic'),
             'H2 same-trigger - other-trigger terrain': ('EQ_TERRAIN', xname),
             'H4 PGA increment': ('EQ_TERRAIN_PGA', 'EQ_TERRAIN'),
             'terrain - slope': ('EQ_TERRAIN', 'slope_only'),
             'terrain+PGA - PGA only': ('EQ_TERRAIN_PGA', 'pga_only')}
    for label, (a, b) in pairs.items():
        if a in scores and b in scores:
            res['contrasts'][label] = {'models': [a, b], 'point': res['metrics'][a]['roc_auc'] - res['metrics'][b]['roc_auc'],
                                       **paired(boot, a, b, lower)}
    for name in ('EQ_TERRAIN_PGA', 'EQ_TERRAIN'):
        if name in scores:
            null = permutation_null(y, scores[name], blocks, n_perm,
                                    np.random.default_rng([cfg['seeds']['permutation'], k, list(scores).index(name)]))
            res.setdefault('null', {})[name] = {'null_auc_95': float(np.quantile(null, 0.95)),
                                                'p': float((1 + (null >= roc_auc_score(y, scores[name])).sum()) / (1 + n_perm))}
    if res['largest_block_positive_share'] > 0.2:
        keep = blocks != share.index[0]
        res['without_largest_block'] = {n: float(roc_auc_score(y[keep], s[keep])) for n, s in scores.items()}
    pred = test[['sample_id', 'dataset', 'label', 'block_id', 'x', 'y']].copy()
    for n, s in scores.items():
        pred[f'score_{n}'] = s
    return res, pred


def decide(h1, h2):
    """Registered conclusion rule for one trigger: supported only if H1 and H2 both pass (Bonferroni lower bound > 0)."""
    p1, p2 = h1['lower_bound_bonferroni'] > 0, h2['lower_bound_bonferroni'] > 0
    return {'H1_passed': bool(p1), 'H2_passed': bool(p2), 'supported': bool(p1 and p2)}


def run(pilot=False):
    cfg = config()
    if not pilot and (PREDICTIONS.exists() or RESULT.exists()):
        raise RuntimeError('Phase 4 has been scored; the confirmatory test is run once (write-once outputs)')
    arm = cfg['trigger_arms']['earthquake']
    test, train = arm['confirmatory_test'], arm['confirmatory_train']
    if training_datasets(cfg, 'earthquake', test) != [train]:
        raise RuntimeError('registered training list for the earthquake arm changed')
    cross = cross_trigger_reference(cfg, test)
    if pilot:
        res, _ = direction(cfg, 'gorkha_2015', 'far_western_nepal', 'far_western_nepal', 99, 50, 20, store_models=False,
                           use_pga=False)
        return {'pilot': True, 'note': 'code path on seen data only (Gorkha -> Far-Western Nepal); Iburi not touched',
                'result': res}
    conf, pred_c = direction(cfg, train, test, cross, 0, 2000, 500)
    rev_cross = cross_trigger_reference(cfg, train)  # rain arm's confirmatory train for the reverse H2 contrast
    if training_datasets(cfg, 'earthquake', train) != [test]:
        raise RuntimeError('registered reverse training list changed')
    rev, pred_r = direction(cfg, test, train, rev_cross, 1, 2000, 500)
    h1 = conf['contrasts']['H1 terrain+PGA - slope+PGA']
    h2 = conf['contrasts']['H2 same-trigger - other-trigger terrain']
    rain_reason = (f"not feasible: {CONFIRMATORY_TEST['rain']} has role "
                   f"{cfg['registry']['datasets'][CONFIRMATORY_TEST['rain']]['role']!r} (no independent mapping extent); "
                   'the rain arm is not modelled and not replaced (Phase 1 gate)')
    eq = decide(h1, h2)
    result = {
        'version': 'susceptibility_v02', 'phase': 4, 'scored_at_utc': datetime.now(timezone.utc).isoformat(),
        'confirmatory_direction': f'{train} -> {test}',
        'bonferroni': {'n_confirmatory_tests': 4, 'lower_percentile': lower_bound_percentile(cfg)},
        'hypotheses': {
            'H1_EQ': {'registered': cfg['hypotheses']['H1_EQ']['test'], **h1, 'passed': eq['H1_passed']},
            'H2_EQ': {'registered': cfg['hypotheses']['H2_EQ']['test'], **h2, 'passed': eq['H2_passed']},
            'H1_RAIN': {'registered': cfg['hypotheses']['H1_RAIN']['test'], 'status': rain_reason},
            'H2_RAIN': {'registered': cfg['hypotheses']['H2_RAIN']['test'], 'status': rain_reason},
            'H3_TPI_sign': {'registered': cfg['hypotheses']['H3_TPI_sign']['test'], 'iburi_2018': conf['univariate_tpi_auc'],
                            'iburi_condition_met': bool(conf['univariate_tpi_auc']['interval_95'][0] > 0.5),
                            'rer2023': rain_reason},
            'H4_PGA_increment': {'registered': cfg['hypotheses']['H4_PGA_increment']['test'],
                                 **conf['contrasts']['H4 PGA increment']}},
        'conclusion': {'earthquake': 'trigger-specific terrain susceptibility supported for earthquakes'
                                     if eq['supported'] else 'not supported for earthquakes',
                       'rain': 'not tested (not feasible)',
                       'overall': ('supported for the earthquake trigger only; the rain trigger could not be tested'
                                   if eq['supported'] else 'not supported (earthquake arm failed; rain arm not testable)'),
                       'rule': cfg['hypotheses']['conclusion_rule']},
        'confirmatory': conf,
        'reverse_secondary_test_inventory_seen_in_v01': rev,
        'counted_comparisons': {
            'models_per_direction': list(model_table(cfg)) + ['EQ_TERRAIN cross-trigger reference'],
            'directions': [f'{train} -> {test} (confirmatory)', f'{test} -> {train} (secondary, seen)'],
            'contrasts_per_direction': list(conf['contrasts']),
            'secondary': ['univariate TPI AUC', 'permutation null for EQ_TERRAIN_PGA and EQ_TERRAIN',
                          'secondary metrics for every model']},
    }
    guard(PREDICTIONS.parent)
    save(pd.concat([pred_c, pred_r], ignore_index=True), PREDICTIONS, {'phase': 4})
    write_json(guard(REPORT) / RESULT.name, result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', action='store_true')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    res = run(a.pilot)
    show = res if a.pilot else {k: res[k] for k in ('hypotheses', 'conclusion')}
    print(json.dumps(show, indent=1, default=str)[:12000])


def cause_analysis():
    """Exploratory cause analysis after the Phase 4 result (registered: a failed test leads to cause analysis, never to
    a new model choice). Univariate AUC per feature on each earthquake inventory and the share of test samples inside
    the training range of each feature. Iburi is seen data from here on."""
    if not RESULT.exists():
        raise RuntimeError('cause analysis only after the single Phase 4 scoring')
    cfg = config()
    cols = list(cfg['features_terrain']) + [PGA]
    data = {n: samples(n) for n in ('gorkha_2015', 'iburi_2018')}
    out = {'status': 'EXPLORATORY (after the confirmatory result; Iburi is now seen data)', 'univariate_auc': {},
           'test_inside_training_range': {}, 'quantiles': {}}
    for n, d in data.items():
        out['univariate_auc'][n] = {c: float(roc_auc_score(d.label, d[c].fillna(d[c].median()))) for c in cols}
        out['quantiles'][n] = {c: [float(d[c].quantile(q)) for q in (0.01, 0.5, 0.99)] for c in cols}
    for train, test in (('gorkha_2015', 'iburi_2018'), ('iburi_2018', 'gorkha_2015')):
        a, b = data[train], data[test]
        out['test_inside_training_range'][f'{train} -> {test}'] = {
            c: float(((b[c] >= a[c].min()) & (b[c] <= a[c].max())).mean()) for c in cols}
    write_json(guard(REPORT) / 'phase4_cause_analysis.json', out)
    return out
