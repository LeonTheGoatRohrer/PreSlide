"""V0.6 registered analysis: hydrological features on the frozen V0.5 cohort and CV plan (config/v06.json).

  python -m preslide.v06.experiment main
"""
import json
import sys

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from ..v05 import metrics as R
from ..v05 import models as M
from ..v05.experiment import prepare as prepare_v05, units_of
from ..v05.paths import config as load_v05_config, sha
from .paths import V06_DATA, V06_REPORT, V05_CV_PLAN, V05_DATASET, config as load_config, guard

VARIANTS = ['static', 'temporal', 'combined', 'hydro_only', 'temporal_hydro', 'combined_hydro']
COMPARISONS = [('temporal_hydro', 'temporal'), ('combined_hydro', 'combined')]
PRIMARY = 'conditional_logit: combined_hydro - combined'


def variant_columns(variant: str, model: str, v05: dict, hydro: list[str]) -> list[str]:
    """Registered column sets; the V0.5 allowlist check applies to the V0.5 part, hydrology is the registered list."""
    if variant in ('static', 'temporal', 'combined'):
        return M.columns(variant, model, v05)
    base = {'hydro_only': [], 'temporal_hydro': M.columns('temporal', model, v05), 'combined_hydro': M.columns('combined', model, v05)}[variant]
    return base + hydro


def prepare() -> tuple[pd.DataFrame, dict]:
    v05 = load_v05_config()
    data = pd.read_parquet(V05_DATASET)
    path = V06_DATA / 'hydro.parquet'
    if sha(path) != read_json(path.with_suffix('.json'))['sha256']:
        raise RuntimeError('hydro.parquet checksum mismatch')
    hydro = pd.read_parquet(path)
    if set(hydro.sample_id) != set(data.sample_id):
        raise RuntimeError('Hydrological features do not cover exactly the V0.5 cohort')
    data = data.merge(hydro, on='sample_id', how='left', validate='one_to_one')
    return prepare_v05(data, v05), v05


def run_cv(data, plan, v05, hydro, models, variants, reps=None):
    preds = []
    for f in plan:
        if reps and f['repetition'] not in reps:
            continue
        held = set(f['held_units'])
        te = data[data.independence_unit.isin(held)]
        tr = data[data.independence_unit.isin(f['train_units'])]
        if set(tr.event_group_id) & set(te.event_group_id) or set(tr.independence_unit) & held:
            raise RuntimeError('Group or unit leakage between CV folds')
        for model in models:
            for variant in variants:
                score, _ = M.fit_predict(model, tr, te, variant_columns(variant, model, v05, hydro), v05)
                preds.append(pd.DataFrame({'sample_id': te.sample_id.to_numpy(), 'event_group_id': te.event_group_id.to_numpy(),
                                           'label': te.label.to_numpy(), 'repetition': f['repetition'], 'fold': f['fold'],
                                           'model': model, 'variant': variant, 'score': score}))
    preds = pd.concat(preds, ignore_index=True)
    once = preds.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data))
    if not once.all():
        raise RuntimeError('A sample lacks exactly one out-of-fold prediction in some repetition')
    return preds


def local_auc(preds, units, k, model, variant, rep, groups=None):
    q = preds[(preds.model == model) & (preds.variant == variant) & (preds.repetition == rep)]
    if groups is not None:
        q = q[q.event_group_id.isin(groups)]
    return R.summarize(R.group_ranks(q, q.score, k), units)['local_auc_units']


def paired(preds, units, k, a, b, model, reps, groups=None):
    """Per repetition: unit-weighted local AUC of a minus b (same groups, folds and purge)."""
    return [local_auc(preds, units, k, model, a, r, groups) - local_auc(preds, units, k, model, b, r, groups) for r in reps]


def main():
    cfg = load_config()
    hydro = cfg['hydrology']['features']
    data, v05 = prepare()
    k = v05['controls']['per_event']
    plan = read_json(V05_CV_PLAN)['primary']
    units = units_of(data)
    preds = run_cv(data, plan, v05, hydro, M.MODELS, VARIANTS)
    guard(V06_DATA / 'analysis')
    preds.to_parquet(V06_DATA / 'analysis/oof_purged.parquet', index=False)
    reps = sorted(preds.repetition.unique())
    summary = {}
    for (model, variant), p in preds.groupby(['model', 'variant']):
        per_rep = [R.summarize(R.group_ranks(q, q.score, k), units) for _, q in p.groupby('repetition')]
        summary[f'{model}/{variant}'] = {
            'median_local_auc_units': float(np.median([r['local_auc_units'] for r in per_rep])),
            'range_local_auc_units': [min(r['local_auc_units'] for r in per_rep), max(r['local_auc_units'] for r in per_rep)],
            'median_top1_units': float(np.median([r['top1_units'] for r in per_rep])),
            'median_mrr_units': float(np.median([r['mrr_units'] for r in per_rep])),
            'events': per_rep[0]['events'], 'units': per_rep[0]['units']}
    boot_cfg = cfg['bootstrap']
    comparisons = {}
    for model in M.MODELS:
        rv = {v: R.group_ranks(q, q.score, k) for v in VARIANTS
              for q in [preds[(preds.model == model) & (preds.variant == v) & (preds.repetition == 1)]]}
        boot = R.bootstrap(rv, units, boot_cfg['draws'], boot_cfg['seed'])
        for a, b in COMPARISONS:
            per_rep = paired(preds, units, k, a, b, model, reps)
            comparisons[f'{model}: {a} - {b}'] = {'per_repetition': per_rep, 'median': float(np.median(per_rep)),
                                                  'bootstrap_rep1': boot[f'{a}_minus_{b}']}
    largest = units.value_counts().idxmax()
    keep = units[units != largest]
    no_largest = {f'{a} - {b}': (lambda v: {'per_repetition': v, 'median': float(np.median(v))})(
        paired(preds, keep, k, a, b, 'conditional_logit', reps, groups=set(keep.index))) for a, b in COMPARISONS}
    temporal = v05['features']['temporal']
    spearman = {c: float(data[[c] + temporal].corr(method='spearman')[c].drop(c).abs().max()) for c in hydro}
    coverage = {c: {'positive': float(data[data.label == 1][c].notna().mean()), 'control': float(data[data.label == 0][c].notna().mean())}
                for c in hydro}
    result = {'cohort': {'events': int(data.event_group_id.nunique()), 'units': int(units.nunique()), 'samples': int(len(data))},
              'chance_local_auc': 0.5, 'variants': summary, 'paired_comparisons_counted': len(comparisons), 'paired': comparisons,
              'primary': comparisons[PRIMARY], 'without_largest_unit_conditional_logit': {'unit': str(largest), **no_largest},
              'max_abs_spearman_with_v05_temporal': spearman, 'coverage': coverage,
              'inputs': {'config_sha256': sha(ROOT / 'config/v06.json'), 'oof_sha256': sha(V06_DATA / 'analysis/oof_purged.parquet')}}
    write_json(guard(V06_REPORT) / 'cv_results.json', result)
    print(json.dumps({k_: round(v['median_local_auc_units'], 3) for k_, v in summary.items()}, indent=1))
    print(json.dumps({k_: (round(v['median'], 4), [round(x, 4) for x in v['bootstrap_rep1']['ci95']]) for k_, v in comparisons.items()}, indent=1))


if __name__ == '__main__':
    {'main': main}[sys.argv[1]]()
