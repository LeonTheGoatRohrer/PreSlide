"""V0.8 registered analysis: time-stratified case-crossover at the reported slope (config/v08.json).

  python -m preslide.v08.experiment main
"""
import json
import sys

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from ..v04 import weather as W
from ..v05 import metrics as R
from ..v05 import models as M
from ..v05.experiment import units_of
from ..v05.partition import v04_units
from ..v05.paths import config as load_v05_config, sha
from ..v06.paths import V06_DATA
from ..v07.experiment import ranks_variable_k
from .paths import V05_CV_PLAN, V08_DATA, V08_REPORT, config as load_config, guard

TEMPORAL = W.INCA_FEATURES + W.SAME_DAY
VARIANTS = ['temporal', 'temporal_hydro', 'hydro_only']
COMPARISON = ('temporal_hydro', 'temporal')


def columns(variant: str, hydro: list[str]) -> list[str]:
    return {'temporal': TEMPORAL, 'temporal_hydro': TEMPORAL + hydro, 'hydro_only': hydro}[variant]


def prepare() -> pd.DataFrame:
    path = V08_DATA / 'dataset.parquet'
    if sha(path) != read_json(path.with_suffix('.json'))['sha256']:
        raise RuntimeError('dataset.parquet checksum mismatch')
    data = pd.read_parquet(path)
    return data.assign(independence_unit=data.event_group_id.map(v04_units().independence_unit))


def run_cv(data, plan, v05, hydro, models, variants):
    preds = []
    for f in plan:
        held = set(f['held_units'])
        te = data[data.independence_unit.isin(held)]
        tr = data[data.independence_unit.isin(f['train_units'])]
        if set(tr.event_group_id) & set(te.event_group_id) or set(tr.independence_unit) & held:
            raise RuntimeError('Group or unit leakage between CV folds')
        for model in models:
            for variant in variants:
                score, _ = M.fit_predict(model, tr, te, columns(variant, hydro), v05)
                preds.append(pd.DataFrame({'sample_id': te.sample_id.to_numpy(), 'event_group_id': te.event_group_id.to_numpy(),
                                           'label': te.label.to_numpy(), 'repetition': f['repetition'], 'fold': f['fold'],
                                           'model': model, 'variant': variant, 'score': score}))
    preds = pd.concat(preds, ignore_index=True)
    once = preds.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data))
    if not once.all():
        raise RuntimeError('A sample lacks exactly one out-of-fold prediction in some repetition')
    return preds


def summarize(preds, data, units, model, variant, keep=None, groups=None, min_controls=1):
    out = []
    for _, q in preds[(preds.model == model) & (preds.variant == variant)].groupby('repetition'):
        if keep is not None:
            q = q[q.sample_id.isin(data.sample_id[keep])]
        if groups is not None:
            q = q[q.event_group_id.isin(groups)]
        ranks = ranks_variable_k(q, q.score, min_controls)
        out.append((R.summarize(ranks, units[units.index.isin(ranks.event_group_id)]), ranks))
    vals = [o[0]['local_auc_units'] for o in out]
    first = out[0][0]
    return {'median_local_auc_units': float(np.median(vals)), 'range': [min(vals), max(vals)], 'top1_units': first['top1_units'],
            'mrr_units': first['mrr_units'], 'events': first['events'], 'units': first['units']}


def main():
    cfg = load_config()
    v05 = load_v05_config()
    hydro = cfg['features']['hydro']
    data = prepare()
    units = units_of(data)
    plan = read_json(V05_CV_PLAN)['primary']
    preds = run_cv(data, plan, v05, hydro, M.MODELS, VARIANTS)
    guard(V08_DATA / 'analysis')
    preds.to_parquet(V08_DATA / 'analysis/oof.parquet', index=False)
    boot_cfg = cfg['bootstrap']
    minc = cfg['design']['min_referents_per_group']
    result = {'cohort': {'events': int(data.event_group_id.nunique()), 'units': int(units.nunique()), 'rows': int(len(data)),
                         'referents_per_group': data[data.label == 0].groupby('event_group_id').size().value_counts().sort_index().to_dict()},
              'chance_local_auc': 0.5, 'variants': {}, 'paired': {}}
    for model in M.MODELS:
        for v in VARIANTS:
            result['variants'][f'{model}/{v}'] = summarize(preds, data, units, model, v, min_controls=minc)
        rv = {}
        for v in VARIANTS:
            q = preds[(preds.model == model) & (preds.variant == v) & (preds.repetition == 1)]
            rv[v] = ranks_variable_k(q, q.score, minc)
        boot = R.bootstrap(rv, units, boot_cfg['draws'], boot_cfg['seed'])
        result['paired'][f'{model}: {COMPARISON[0]} - {COMPARISON[1]}'] = boot[f'{COMPARISON[0]}_minus_{COMPARISON[1]}']
        for v in VARIANTS:
            result['variants'][f'{model}/{v}']['ci95_rep1'] = boot[v]['ci95']
    # Diagnostics
    largest = units.value_counts().idxmax()
    other = units.index[units != largest]
    side = data.offset_days.map(lambda o: 'before' if o < 0 else 'after' if o > 0 else 'event')
    diag = {'largest_unit': str(largest), 'events_in_largest_unit': int((units == largest).sum()), 'by_time_quality': {}, 'by_referent_side': {}}
    diag['without_largest_unit'] = summarize(preds, data, units, 'conditional_logit', 'temporal', groups=set(other), min_controls=minc)
    for tq in sorted(data.time_quality.unique()):
        g = set(data[(data.label == 1) & (data.time_quality == tq)].event_group_id)
        diag['by_time_quality'][tq] = summarize(preds, data, units, 'conditional_logit', 'temporal', groups=g, min_controls=minc)
    for s in ('before', 'after'):
        diag['by_referent_side'][s] = summarize(preds, data, units, 'conditional_logit', 'temporal', keep=(side != ('after' if s == 'before' else 'before')), min_controls=1)
    result['diagnostics'] = diag
    # Reference: stored neighbour-slope (V0.5 / V0.6) out-of-fold rankings on the same groups
    groups = set(data.event_group_id)
    ref = {}
    for name, path, variant in (('v05_temporal', ROOT / 'data/v05/analysis/oof_purged.parquet', 'temporal'),
                                ('v06_temporal_hydro', V06_DATA / 'analysis/oof_purged.parquet', 'temporal_hydro')):
        o = pd.read_parquet(path)
        o = o[(o.model == 'conditional_logit') & (o.variant == variant) & o.event_group_id.isin(groups)]
        vals = []
        for _, q in o.groupby('repetition'):
            r = R.group_ranks(q, q.score, 10)
            vals.append(R.summarize(r, units[units.index.isin(r.event_group_id)])['local_auc_units'])
        ref[name] = {'median_local_auc_units': float(np.median(vals)), 'events': len(groups)}
    result['neighbour_slope_reference_same_groups'] = ref
    result['inputs'] = {'config_sha256': sha(ROOT / 'config/v08.json'), 'dataset_sha256': sha(V08_DATA / 'dataset.parquet'),
                        'oof_sha256': sha(V08_DATA / 'analysis/oof.parquet')}
    write_json(guard(V08_REPORT) / 'cv_results.json', result)
    print(json.dumps({k: round(v['median_local_auc_units'], 3) for k, v in result['variants'].items()}, indent=1))
    print(json.dumps(result['paired'], indent=1))


if __name__ == '__main__':
    {'main': main}[sys.argv[1]]()
