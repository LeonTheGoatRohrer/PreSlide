"""V0.7 registered analysis: reporting-bias control with infrastructure distances (config/v07.json).

  python -m preslide.v07.experiment main
"""
import json
import sys

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from ..v05 import metrics as R
from ..v05 import models as M
from ..v05.experiment import LC, prepare as prepare_v05, units_of
from ..v05.paths import config as load_v05_config, sha
from .paths import V05_CV_PLAN, V05_DATASET, V05_OOF, V07_DATA, V07_REPORT, config as load_config, guard

INFRA = ['log10_dist_building', 'log10_dist_road']
NEW_VARIANTS = ['infra_only', 'static_infra', 'combined_infra']


def variant_columns(variant: str, model: str, v05: dict) -> list[str]:
    base = {'infra_only': [], 'static_infra': M.columns('static', model, v05), 'combined_infra': M.columns('combined', model, v05)}
    return base[variant] + INFRA


def prepare() -> tuple[pd.DataFrame, dict]:
    v05 = load_v05_config()
    data = pd.read_parquet(V05_DATASET)
    path = V07_DATA / 'infrastructure.parquet'
    if sha(path) != read_json(path.with_suffix('.json'))['sha256']:
        raise RuntimeError('infrastructure.parquet checksum mismatch')
    infra = pd.read_parquet(path)
    if set(infra.sample_id) != set(data.sample_id):
        raise RuntimeError('Infrastructure distances do not cover exactly the V0.5 cohort')
    data = data.merge(infra, on='sample_id', how='left', validate='one_to_one')
    data['log10_dist_building'] = np.log10(1 + data.dist_building_m)
    data['log10_dist_road'] = np.log10(1 + data.dist_road_m)
    return prepare_v05(data, v05), v05


def run_cv(data, plan, v05, models, variants, drop=(), reps=None, columns=variant_columns):
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
                cols = [c for c in columns(variant, model, v05) if c not in drop]
                score, _ = M.fit_predict(model, tr, te, cols, v05)
                preds.append(pd.DataFrame({'sample_id': te.sample_id.to_numpy(), 'event_group_id': te.event_group_id.to_numpy(),
                                           'label': te.label.to_numpy(), 'repetition': f['repetition'], 'fold': f['fold'],
                                           'model': model, 'variant': variant, 'score': score}))
    preds = pd.concat(preds, ignore_index=True)
    once = preds.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data))
    if not once.all():
        raise RuntimeError('A sample lacks exactly one out-of-fold prediction in some repetition')
    return preds


def caliper_keep(frame: pd.DataFrame, factor: float = 2.0) -> pd.Series:
    """Boolean per sample: positives always kept; a control is kept iff 1/factor <= (1+d_ctrl)/(1+d_pos) <= factor."""
    pos = frame[frame.label == 1].set_index('event_group_id').dist_infrastructure_m
    ratio = (1 + frame.dist_infrastructure_m) / (1 + frame.event_group_id.map(pos))
    return (frame.label == 1) | ((ratio >= 1 / factor) & (ratio <= factor))


def ranks_variable_k(frame: pd.DataFrame, score, min_controls: int) -> pd.DataFrame:
    """Per-group rank metrics with any number of controls; groups below min_controls are omitted."""
    f = frame[['event_group_id', 'label']].assign(score=np.asarray(score, float))
    rows = []
    for gid, g in f.groupby('event_group_id', sort=True):
        pos, neg = g.score[g.label == 1].to_numpy(), g.score[g.label == 0].to_numpy()
        if len(pos) != 1:
            raise ValueError(f'Group {gid} lacks exactly one positive')
        if len(neg) >= min_controls:
            rows.append({'event_group_id': gid, 'controls': len(neg), **R.rank_metrics(pos[0], neg)})
    return pd.DataFrame(rows)


def median_auc(preds, data, units, model, variant, keep=None, min_controls=1):
    out = []
    for rep, q in preds[(preds.model == model) & (preds.variant == variant)].groupby('repetition'):
        q = q.merge(data[['sample_id']].assign(_keep=True if keep is None else keep.to_numpy()), on='sample_id')
        q = q[q._keep]
        ranks = ranks_variable_k(q, q.score, min_controls)
        out.append(R.summarize(ranks, units[units.index.isin(ranks.event_group_id)]))
    return {'median_local_auc_units': float(np.median([o['local_auc_units'] for o in out])),
            'range': [min(o['local_auc_units'] for o in out), max(o['local_auc_units'] for o in out)],
            'events': out[0]['events'], 'units': out[0]['units']}


def main():
    cfg = load_config()
    data, v05 = prepare()
    data = data.reset_index(drop=True)
    units = units_of(data)
    plan = read_json(V05_CV_PLAN)['primary']
    k = v05['controls']['per_event']
    guard(V07_DATA / 'analysis')
    boot_cfg = cfg['bootstrap']

    # (a) in-model
    new = run_cv(data, plan, v05, M.MODELS, NEW_VARIANTS)
    new.to_parquet(V07_DATA / 'analysis/oof_infra.parquet', index=False)
    old = pd.read_parquet(V05_OOF)
    allp = pd.concat([old, new], ignore_index=True)
    result = {'cohort': {'events': int(data.event_group_id.nunique()), 'units': int(units.nunique()), 'samples': int(len(data))},
              'chance_local_auc': 0.5}
    a = {}
    for model in M.MODELS:
        for v in ['static', 'combined'] + NEW_VARIANTS:
            a[f'{model}/{v}'] = median_auc(allp, data, units, model, v)
        rv = {v: R.group_ranks(q, q.score, k) for v in ['static', 'combined', 'static_infra', 'combined_infra', 'infra_only']
              for q in [allp[(allp.model == model) & (allp.variant == v) & (allp.repetition == 1)]]}
        boot = R.bootstrap(rv, units, boot_cfg['draws'], boot_cfg['seed'])
        a[f'{model}/paired'] = {'static_infra - static': boot['static_infra_minus_static'], 'combined_infra - combined': boot['combined_infra_minus_combined'],
                                'infra_only_ci95': boot['infra_only']['ci95']}
    result['a_in_model'] = a

    # (b) equal visibility: re-rank stored V0.5 scores within caliper-retained controls
    b_cfg = cfg['analyses']['b_equal_visibility']
    keep = caliper_keep(data)
    minc = b_cfg['min_controls_per_group']
    kept_controls = keep[data.label == 0].groupby(data.event_group_id[data.label == 0]).sum()
    retained_groups = kept_controls.index[kept_controls >= minc]
    in_groups = data.event_group_id.isin(retained_groups)
    result['b_caliper'] = {'groups_kept': int(len(retained_groups)), 'groups_total': int(data.event_group_id.nunique()),
                           'controls_kept_share': float(keep[data.label == 0].mean()),
                           'units_kept': int(units[units.index.isin(retained_groups)].nunique())}
    b = {}
    sub_units = units[units.index.isin(retained_groups)]
    ranks_rep1 = {}
    for model in ['conditional_logit']:
        for v in ('static', 'temporal', 'combined'):
            all_g = median_auc(old, data, units, model, v, keep=in_groups)                       # all controls, same groups
            restricted = median_auc(old, data, units, model, v, keep=keep, min_controls=minc)    # caliper-retained controls
            b[f'{model}/{v}'] = {'all_controls_same_groups': all_g, 'caliper_controls': restricted,
                                 'difference': restricted['median_local_auc_units'] - all_g['median_local_auc_units']}
        for v in ('static', 'combined'):
            q = old[(old.model == model) & (old.variant == v) & (old.repetition == 1)].merge(data[['sample_id']].assign(_k=keep.to_numpy(), _g=in_groups.to_numpy()), on='sample_id')
            ranks_rep1[f'{v}_all'] = ranks_variable_k(q[q._g], q.score[q._g], 1)
            ranks_rep1[f'{v}_caliper'] = ranks_variable_k(q[q._k & q._g], q.score[q._k & q._g], minc)
    ranks_rep1 = {n: r[r.event_group_id.isin(retained_groups)] for n, r in ranks_rep1.items()}
    boot_b = R.bootstrap(ranks_rep1, sub_units, boot_cfg['draws'], boot_cfg['seed'])
    for v in ('static', 'combined'):
        b[f'conditional_logit/{v}']['bootstrap_rep1_difference'] = boot_b[f'{v}_caliper_minus_{v}_all'] if f'{v}_caliper_minus_{v}_all' in boot_b else boot_b[f'{v}_all_minus_{v}_caliper']
    b['bootstrap_ci95_caliper_static'] = boot_b['static_caliper']['ci95']

    # land-cover ablation on all groups and on the caliper-restricted groups
    abl = run_cv(data, plan, v05, ['conditional_logit'], ['combined'], drop=LC, columns=lambda v, m, c: M.columns('combined', m, c))
    b['land_cover_ablation_combined'] = {
        'with_lc_all_groups': median_auc(old, data, units, 'conditional_logit', 'combined', keep=in_groups),
        'without_lc_all_groups': median_auc(abl, data, units, 'conditional_logit', 'combined', keep=in_groups),
        'with_lc_caliper': b['conditional_logit/combined']['caliper_controls'],
        'without_lc_caliper': median_auc(abl, data, units, 'conditional_logit', 'combined', keep=keep, min_controls=minc)}
    result['b_equal_visibility'] = b

    # diagnostics
    pos, ctrl = data[data.label == 1], data[data.label == 0]
    result['diagnostics'] = {
        'distance_quantiles_m': {c: {'positive': pos[c].quantile([.1, .25, .5, .75, .9]).round(1).tolist(), 'control': ctrl[c].quantile([.1, .25, .5, .75, .9]).round(1).tolist()}
                                 for c in ('dist_building_m', 'dist_road_m', 'dist_infrastructure_m')},
        'capped_share': {c: {'positive': float(pos[c].mean()), 'control': float(ctrl[c].mean())} for c in ('building_capped', 'road_capped')},
        'spearman_dist_infrastructure': {c: float(data[['dist_infrastructure_m', c]].corr(method='spearman').iloc[0, 1]) for c in ['elevation'] + LC}}
    result['inputs'] = {'config_sha256': sha(ROOT / 'config/v07.json'), 'oof_infra_sha256': sha(V07_DATA / 'analysis/oof_infra.parquet'),
                        'infrastructure_sha256': sha(V07_DATA / 'infrastructure.parquet')}
    write_json(guard(V07_REPORT) / 'cv_results.json', result)
    print(json.dumps({k_: v['median_local_auc_units'] for k_, v in a.items() if 'median_local_auc_units' in v}, indent=1))
    print(json.dumps(result['b_caliper']), json.dumps({k_: v.get('difference') for k_, v in b.items() if isinstance(v, dict)}, indent=1))


if __name__ == '__main__':
    {'main': main}[sys.argv[1]]()
