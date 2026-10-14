"""V0.5 exploratory grouped CV (config/v05.json), references, bootstrap and registered diagnostics.

  python -m preslide.v05.experiment pilot   # technical pilot: one conditional logit on the 20-event pilot dataset
  python -m preslide.v05.experiment main    # registered analysis on the frozen cohort and CV plan
"""
import json
import sys

import joblib
import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from .paths import V05_DATA, V05_MODELS, V05_REPORT, config as load_config, guard, sha
from . import metrics as R
from . import models as M
from . import pipeline as P
from .partition import CV_DIR, v04_units, cv_plan

ANALYSIS = V05_DATA / 'analysis'
LC = ['lc_forest', 'lc_grass_shrub', 'lc_agriculture', 'lc_open_bare', 'lc_artificial_water_other']


def prepare(data, cfg):
    data = M.add_one_hot(data)
    data = data.assign(independence_unit=data.event_group_id.map(v04_units().independence_unit))
    return pd.concat([data, M.interaction_columns(data, cfg)], axis=1)


def units_of(frame):
    return frame.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit


def frozen_inputs():
    freeze = read_json(V05_REPORT / 'COHORT_FREEZE.json')
    dataset, plan_path = P.run_dir() / 'dataset.parquet', CV_DIR / 'cv_plan.json'
    if sha(dataset) != freeze['dataset_sha256'] or sha(plan_path) != freeze['cv_plan_sha256']:
        raise RuntimeError('Dataset or CV plan changed after the cohort freeze')
    return P.load(dataset), read_json(plan_path), freeze


def run_cv(data, plan, cfg, k, models=M.MODELS, variants=M.VARIANTS, purged=True, drop=(), reps=None):
    """Out-of-fold scores for every (model, variant); each sample exactly once per repetition."""
    preds = []
    for f in plan:
        if reps and f['repetition'] not in reps:
            continue
        held = set(f['held_units'])
        te = data[data.independence_unit.isin(held)]
        tr = data[data.independence_unit.isin(f['train_units'])] if purged else data[~data.independence_unit.isin(held)]
        if set(tr.event_group_id) & set(te.event_group_id) or set(tr.independence_unit) & held:
            raise RuntimeError('Group or unit leakage between CV folds')
        if tr.label.nunique() != 2:
            raise RuntimeError('Training fold without both classes')
        for model in models:
            for variant in variants:
                cols = M.columns(variant, model, cfg, drop)
                score, _ = M.fit_predict(model, tr, te, cols, cfg)
                preds.append(pd.DataFrame({'sample_id': te.sample_id.to_numpy(), 'event_group_id': te.event_group_id.to_numpy(),
                                           'label': te.label.to_numpy(), 'repetition': f['repetition'], 'fold': f['fold'],
                                           'model': model, 'variant': variant, 'score': score, 'train_groups': tr.event_group_id.nunique()}))
    preds = pd.concat(preds, ignore_index=True)
    once = preds.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data))
    if not once.all():
        raise RuntimeError('A sample lacks exactly one out-of-fold prediction in some repetition')
    return preds


def summarize_preds(preds, units, k):
    out = {}
    for (model, variant), p in preds.groupby(['model', 'variant']):
        reps = []
        for rep, q in p.groupby('repetition'):
            reps.append({**R.summarize(R.group_ranks(q, q.score, k), units), 'pooled_ap': R.pooled_ap(q, q.score), 'repetition': int(rep)})
        frame = pd.DataFrame(reps).drop(columns='repetition')
        out[f'{model}/{variant}'] = {'median': frame.median().to_dict(), 'min': frame.min().to_dict(), 'max': frame.max().to_dict(),
                                     'repetitions': reps}
    return out


def ranks_rep1(preds, model, variants, k):
    return {v: R.group_ranks(q, q.score, k) for v in variants
            for q in [preds[(preds.model == model) & (preds.variant == v) & (preds.repetition == 1)]]}


def slope_reference(data, units, k):
    ranks = R.group_ranks(data, data.slope.to_numpy(), k)
    return ranks, {**R.summarize(ranks, units), 'pooled_ap': R.pooled_ap(data, data.slope)}


# ---------- diagnostics ----------

def distributions(data):
    pos, ctrl = data[data.label == 1], data[data.label == 0]
    num = {c: {'positive': pos[c].describe(percentiles=[.25, .5, .75]).to_dict(), 'control': ctrl[c].describe(percentiles=[.25, .5, .75]).to_dict()}
           for c in ('slope', 'elevation', 'roughness_tri', 'tpi_150m')}
    aspect = {lab: np.histogram(g.aspect % 360, bins=8, range=(0, 360))[0].tolist() for lab, g in (('positive', pos), ('control', ctrl))}
    cat = {c: {'positive': pos[c].fillna('missing').value_counts(normalize=True).to_dict(),
               'control': ctrl[c].fillna('missing').value_counts(normalize=True).to_dict()} for c in ('land_cover_class', 'geology_class')}
    bins = pd.cut(ctrl.distance_to_positive_m, [750, 2000, 5000, 10000], labels=['0.75-2km', '2-5km', '5-10km'], include_lowest=True)
    return {'numeric': num, 'aspect_8_bins_from_north': aspect, 'categorical': cat,
            'control_distance_bins': bins.value_counts().sort_index().astype(int).to_dict(),
            'slope_ge_5_share_controls': float((ctrl.slope >= 5).mean())}


def indirect_cues(data, cols):
    """Missingness and truncation flags (never predictors) must not separate positives from controls."""
    pos, ctrl = data[data.label == 1], data[data.label == 0]
    miss = {c: {'positive': float(pos[c].isna().mean()), 'control': float(ctrl[c].isna().mean())} for c in cols}
    return {'catchment_truncated': {'positive': float(pos.catchment_truncated.mean()), 'control': float(ctrl.catchment_truncated.mean())},
            'missing_share': {c: v for c, v in miss.items() if v['positive'] or v['control']},
            'weather_grid_distance_m_median': {'positive': float(pos.weather_grid_distance_m.median()), 'control': float(ctrl.weather_grid_distance_m.median())}}


def subsets(data, ranks, units, meta):
    r = ranks.merge(meta, on='event_group_id')
    out = {}
    for col in ('survey_method', 'state', 'year', 'position_category'):
        rows = {}
        for value, g in r.groupby(col):
            s = R.summarize(g.drop(columns=[col]), units[units.index.isin(g.event_group_id)])
            rows[str(value)] = {'events': s['events'], 'units': s['units'], 'local_auc_units': s['local_auc_units'],
                                'local_auc_events': s['local_auc_events'], 'top1_events': s['top1_events']}
        out[col] = rows
    return out


def event_meta(data):
    cand = pd.DataFrame(json.loads((ROOT / 'data/v04/audit/candidates.json').read_text(encoding='utf-8')))
    cand = cand.rename(columns={'event_id': 'event_group_id'})[['event_group_id', 'survey_method', 'position_accuracy_original']]
    pos = data[data.label == 1][['event_group_id', 'state', 'event_day']].merge(cand, on='event_group_id', how='left')
    pos['year'] = pos.event_day.str[:4]
    pos['position_category'] = pos.position_accuracy_original.fillna('unknown')
    return pos[['event_group_id', 'survey_method', 'state', 'year', 'position_category']]


def stanz_unit(units, data):
    """The 2016 Stanz storm unit: the largest unit; checked to be a 2016 Styrian unit."""
    unit = units.value_counts().idxmax()
    pos = data[(data.label == 1) & data.event_group_id.isin(units.index[units == unit])]
    if not (pos.event_day.str[:4] == '2016').mean() > .5 or not (pos.state == 'Steiermark').mean() > .5:
        raise RuntimeError(f'Largest unit {unit} is not the 2016 Styrian (Stanz) unit')
    return unit, int(len(pos))


def control_variants(data, plan_union, cfg):
    """(a) 5 original matched V0.4 controls, (b) first 5 unmatched draws, (c) all 10 unmatched; same units and purge."""
    v04 = prepare(P.v04_dataset(), cfg)
    cohort = sorted(set(data.event_group_id) & set(v04.event_group_id))
    a = v04[v04.event_group_id.isin(cohort)]
    c = data[data.event_group_id.isin(cohort)]
    b = c[(c.label == 1) | (c.draw_order <= 5)]
    out = {'cohort_events': len(cohort), 'cohort_units': int(units_of(c).nunique())}
    for name, frame, k in (('a_matched_5', a, 5), ('b_unmatched_first_5', b, 5), ('c_unmatched_10', c, 10)):
        preds = run_cv(frame, plan_union, cfg, k, models=['conditional_logit'], variants=['static', 'combined'], reps=[1])
        res = {}
        for v in ('static', 'combined'):
            q = preds[preds.variant == v]
            res[v] = R.summarize(R.group_ranks(q, q.score, k), units_of(frame))
        res['combined_minus_static_local_auc_units'] = res['combined']['local_auc_units'] - res['static']['local_auc_units']
        res['chance'] = R.chance(k)
        out[name] = res
    return out


def final_models(data, cfg):
    outdir = guard(V05_MODELS / 'final_all_data')
    saved, coefs = {}, {}
    for model in M.MODELS:
        for variant in M.VARIANTS:
            cols = M.columns(variant, model, cfg)
            _, bundle = M.fit_predict(model, data, data.head(11), cols, cfg)
            path = outdir / f'{model}_{variant}.joblib'
            joblib.dump(bundle, path)
            saved[path.relative_to(ROOT).as_posix()] = sha(path)
            if model == 'conditional_logit':
                coefs[variant] = dict(sorted(zip(cols, bundle['model'].coef_.round(4).tolist()), key=lambda kv: -abs(kv[1])))
    return saved, coefs


# ---------- entry points ----------

def pilot():
    cfg = load_config()
    data = prepare(P.load(P.run_dir() / 'dataset_pilot_20.parquet'), cfg)
    plan, feasible = cv_plan(data, cfg)
    plan = [f for f in plan if f['repetition'] == 1]
    preds = run_cv(data, plan, cfg, cfg['controls']['per_event'], models=['conditional_logit'], variants=['static'], purged=False)
    s = summarize_preds(preds, units_of(data), cfg['controls']['per_event'])
    out = {'note': 'Technical pilot (code check), not a scientific result. Unpurged, repetition 1 only.',
           'groups': int(data.event_group_id.nunique()), 'units': int(data.independence_unit.nunique()),
           'purge_feasible_on_pilot': feasible, 'conditional_logit_static_rep1': s['conditional_logit/static']['repetitions'][0]}
    write_json(guard(V05_REPORT / 'pilot') / 'technical_pilot.json', out)
    print(json.dumps(out, indent=1))


def main():
    cfg = load_config()
    k = cfg['controls']['per_event']
    raw, plans, freeze = frozen_inputs()
    data = prepare(raw, cfg)
    units = units_of(data)
    plan = plans['primary']
    result = {'cohort': freeze['cohort'], 'cv_feasible': freeze['cv_feasible'], 'chance': R.chance(k),
              'folds': [{x: f[x] for x in ('repetition', 'fold', 'held_groups', 'purged_groups', 'train_groups',
                                           'unpurged_train_groups', 'min_train_to_held_distance_m')} | {'held_units': len(f['held_units']),
                         'purged_units': len(f['purged_units']), 'train_units': len(f['train_units'])} for f in plan]}
    guard(ANALYSIS)
    preds = run_cv(data, plan, cfg, k)
    preds.to_parquet(ANALYSIS / 'oof_purged.parquet', index=False)
    print('purged CV done', flush=True)
    sens = run_cv(data, plan, cfg, k, purged=False)
    sens.to_parquet(ANALYSIS / 'oof_unpurged.parquet', index=False)
    print('unpurged CV done', flush=True)
    result['purged'] = summarize_preds(preds, units, k)
    result['unpurged_sensitivity'] = summarize_preds(sens, units, k)
    slope_ranks, result['slope_rule'] = slope_reference(data, units, k)
    ev = cfg['metrics']['bootstrap']
    boot = {}
    for model in M.MODELS:
        rv = ranks_rep1(preds, model, M.VARIANTS, k)
        rv['slope_rule'] = slope_ranks
        boot[model] = {m: R.bootstrap(rv, units, ev['draws'], ev['seed'], metric=m) for m in ('local_auc', 'top1', 'mrr')}
    result['bootstrap_rep1'] = boot
    primary = result['purged']['conditional_logit/combined']
    static = result['purged']['conditional_logit/static']
    result['primary'] = {
        'endpoint': cfg['metrics']['primary_endpoint'],
        'median': primary['median']['local_auc_units'], 'range': [primary['min']['local_auc_units'], primary['max']['local_auc_units']],
        'ci95_rep1': boot['conditional_logit']['local_auc']['combined']['ci95'],
        'combined_minus_static_per_repetition': [a['local_auc_units'] - b['local_auc_units'] for a, b in zip(primary['repetitions'], static['repetitions'])],
        'combined_minus_static_rep1_bootstrap': boot['conditional_logit']['local_auc']['combined_minus_static'],
        'chance': 0.5, 'slope_rule': result['slope_rule']['local_auc_units']}
    # Diagnostics (all registered; none selects a new primary model).
    meta = event_meta(data)
    cl1 = ranks_rep1(preds, 'conditional_logit', M.VARIANTS, k)
    result['subsets_conditional_logit_combined_rep1'] = subsets(data, cl1['combined'], units, meta)
    abl = run_cv(data, plan, cfg, k, models=['conditional_logit'], variants=['combined'], drop=LC, reps=[1])
    abl_s = R.summarize(R.group_ranks(abl, abl.score, k), units)
    result['land_cover_ablation_rep1'] = {'without_land_cover': abl_s,
                                          'with_land_cover': R.summarize(cl1['combined'], units),
                                          'difference_local_auc_units': abl_s['local_auc_units'] - R.summarize(cl1['combined'], units)['local_auc_units']}
    su, sn = stanz_unit(units, data)
    stanz = {'unit': su, 'events': sn}
    for v in M.VARIANTS:
        r = cl1[v]
        keep = ~r.event_group_id.isin(units.index[units == su])
        stanz[v] = {'all': R.summarize(r, units), 'without_stanz': R.summarize(r[keep], units[units != su]),
                    'stanz_only': R.summarize(r[~keep], units[units == su])}
    result['stanz_conditional_logit_rep1'] = stanz
    result['distributions'] = distributions(data)
    result['indirect_cues'] = indirect_cues(data, cfg['features']['static'] + cfg['features']['temporal'])
    result['control_variants'] = control_variants(data, plans['control_variants_union'], cfg)
    result['final_models'], result['conditional_logit_coefficients_all_data'] = final_models(data, cfg)
    result['frozen_inputs'] = {'cohort_freeze_sha256': sha(V05_REPORT / 'COHORT_FREEZE.json')}
    write_json(V05_REPORT / 'cv_results.json', result)
    print(json.dumps(result['primary'], indent=1))
    print(json.dumps({k_: round(v['median']['local_auc_units'], 3) for k_, v in result['purged'].items()}, indent=1))


if __name__ == '__main__':
    {'pilot': pilot, 'main': main}[sys.argv[1]]()
