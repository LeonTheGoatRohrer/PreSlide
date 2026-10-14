"""V0.4 development evaluation (grouped CV on independence units), freeze, and the single sealed-test scoring.

  python -m preslide.v04.experiment admission   # daily-product admission from the 20-event pilot
  python -m preslide.v04.experiment develop     # CV, null, leave-one-state-out (development only)
  python -m preslide.v04.experiment freeze      # final models on all development data + hashes
  python -m preslide.v04.experiment test        # exactly once; refuses to run twice
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from .paths import CONFIG, V04_DATA, V04_MODELS, V04_REPORT, config as load_config, guard
from .pipeline import run_dir, load
from . import models as M
from .weather import DAILY_FEATURES, RESOURCE_FEATURES

ANALYSIS = V04_DATA / 'analysis'
PARTITION = V04_DATA / 'partition/partition.json'
DEV_REPORT = V04_REPORT / 'dev_metrics.json'


def use_pilot():
    """Code verification on the pilot dataset: separate partition, analysis and report files; test refused."""
    global ANALYSIS, PARTITION, DEV_REPORT
    ANALYSIS, PARTITION = V04_DATA / 'analysis_pilot', V04_DATA / 'partition_pilot/partition.json'
    DEV_REPORT = V04_REPORT / 'pilot/dev_metrics.json'
FREEZE = V04_REPORT / 'FREEZE.json'
TEST_RESULT = V04_REPORT / 'test_results.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admitted_daily():
    p = V04_REPORT / 'admission.json'
    return read_json(p)['admitted_features'] if p.exists() else []


def table():
    data = load(run_dir() / 'dataset.parquet')
    part = pd.DataFrame(json.loads(PARTITION.read_text(encoding='utf-8')))
    data = data.merge(part[['event_group_id', 'independence_unit', 'partition', 'temporal_episode']], on='event_group_id', how='inner')
    data = M.add_one_hot(data)
    inter = M.interaction_columns(data)
    return pd.concat([data, inter], axis=1), list(inter.columns)


def columns(variant, model, interactions, admitted):
    temporal = M.temporal_columns(admitted)
    cols = {'static': M.STATIC, 'temporal': temporal, 'combined': M.STATIC + temporal}[variant]
    if variant == 'combined' and model == 'conditional_logit':
        cols = cols + interactions
    return cols


def train_weights(frame):
    gu = frame.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
    counts = gu.value_counts()
    return gu.map(lambda u: 1 / np.sqrt(counts[u]))


def folds(units, seed, k):
    ids = np.array(sorted(units.unique()))
    return np.array_split(np.random.default_rng(seed).permutation(ids), k)


def units_of(frame):
    return frame.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit


# ---------- admission ----------

def admission():
    data = load(run_dir() / 'dataset.parquet')
    pilot_groups = data.event_group_id.unique()
    result = {'pilot_groups': int(len(pilot_groups)), 'products': {}, 'admitted_features': []}
    for resource, feats in RESOURCE_FEATURES.items():
        cov = {f: float(data[f].notna().mean()) if f in data else 0.0 for f in feats}
        last = pd.to_datetime(data.get(f'{resource}_last_day'), utc=True)
        boundary_ok = bool(((last + pd.Timedelta(hours=30)) < pd.to_datetime(data.t0_utc, utc=True)).all()) if last is not None else False
        plausible = {f: [float(data[f].min()), float(data[f].max())] if f in data else None for f in feats}
        admit = boundary_ok and min(cov.values()) >= 0.95
        result['products'][resource] = {'coverage': cov, 'boundary_ok': boundary_ok, 'range': plausible, 'admitted': admit}
        if admit:
            result['admitted_features'] += feats
    write_json(V04_REPORT / 'admission.json', result)
    print(json.dumps(result, indent=1))


# ---------- development ----------

def develop():
    cfg = load_config()
    ev = cfg['evaluation']
    data, inter = table()
    dev = data[data.partition == 'development'].reset_index(drop=True)
    admitted = admitted_daily()
    seeds, k = [11, 23, 37, 51, 71], 5
    preds = []
    for rep, seed in enumerate(seeds, 1):
        for fold, held in enumerate(folds(units_of(dev), seed, k), 1):
            tr, te = dev[~dev.independence_unit.isin(held)], dev[dev.independence_unit.isin(held)]
            if set(tr.event_group_id) & set(te.event_group_id) or set(tr.independence_unit) & set(te.independence_unit):
                raise RuntimeError('Group or unit leakage between CV folds')
            w = train_weights(tr)
            for model in M.MODELS:
                for variant in M.VARIANTS:
                    cols = columns(variant, model, inter, admitted)
                    score, _ = M.fit_predict(model, tr, te, cols, w, cfg['models'])
                    preds.append(pd.DataFrame({'sample_id': te.sample_id, 'event_group_id': te.event_group_id, 'label': te.label,
                                               'repetition': rep, 'fold': fold, 'model': model, 'variant': variant, 'score': score}))
        print(f'repetition {rep} done', flush=True)
    preds = pd.concat(preds, ignore_index=True)
    guard(ANALYSIS)
    preds.to_parquet(ANALYSIS / 'dev_predictions.parquet', index=False)
    gu = units_of(dev)
    report = {'development': {'events': int(dev.event_group_id.nunique()), 'units': int(gu.nunique()),
                              'samples': int(len(dev))}, 'admitted_daily_features': admitted, 'results': {}}
    for model in M.MODELS:
        for variant in M.VARIANTS:
            reps = []
            for rep in range(1, len(seeds) + 1):
                p = preds[(preds.model == model) & (preds.variant == variant) & (preds.repetition == rep)]
                ranks = M.group_ranks(p, p.score.to_numpy())
                reps.append({**M.summarize(ranks, gu), 'pooled_ap': M.pooled_ap(p, p.score)})
            frame = pd.DataFrame(reps)
            report['results'][f'{model}/{variant}'] = {
                'median': frame.median(numeric_only=True).to_dict(), 'min': frame.min(numeric_only=True).to_dict(),
                'max': frame.max(numeric_only=True).to_dict(), 'repetitions': reps}
    # Unit bootstrap (repetition 1 out-of-fold ranks), paired across variants of each model.
    report['bootstrap_rep1'] = {}
    for model in M.MODELS:
        rv = {}
        for variant in M.VARIANTS:
            p = preds[(preds.model == model) & (preds.variant == variant) & (preds.repetition == 1)]
            rv[variant] = M.group_ranks(p, p.score.to_numpy())
        report['bootstrap_rep1'][model] = M.bootstrap(rv, gu, ev['bootstrap']['draws'], ev['bootstrap']['seed'])
    null = M.random_rank_null(gu)
    report['random_rank_null'] = {k: v for k, v in null.items() if k != 'samples'}
    report['label_permutation_null'] = permutation_null(dev, inter, admitted, cfg, seeds[0], k)
    report['leave_one_state_out'] = leave_one_state_out(dev, inter, admitted, cfg)
    report['coverage'] = coverage(dev, admitted)
    write_json(DEV_REPORT, report)
    print(json.dumps({k: v['median'] for k, v in report['results'].items()}, indent=1))


def permutation_null(dev, inter, admitted, cfg, seed, k, draws=100):
    """Conditional logit refit on within-group label permutations (repetition-1 folds)."""
    rng = np.random.default_rng(20261015)
    gu = units_of(dev)
    out = {v: [] for v in M.VARIANTS}
    split = folds(gu, seed, k)
    for draw in range(draws):
        perm = dev.copy()
        new_pos = perm.groupby('event_group_id').sample_id.transform(lambda s: s.iloc[rng.integers(len(s))])
        perm['label'] = (perm.sample_id == new_pos).astype(int)
        for variant in M.VARIANTS:
            cols = columns(variant, 'conditional_logit', inter, admitted)
            parts = []
            for held in split:
                tr, te = perm[~perm.independence_unit.isin(held)], perm[perm.independence_unit.isin(held)]
                score, _ = M.fit_predict('conditional_logit', tr, te, cols, train_weights(tr), cfg['models'])
                parts.append(M.group_ranks(te, score))
            out[variant].append(M.summarize(pd.concat(parts), gu)['local_auc_weighted'])
    return {v: {'mean': float(np.mean(x)), 'q05': float(np.quantile(x, .05)), 'q95': float(np.quantile(x, .95)), 'draws': draws}
            for v, x in out.items()}


def leave_one_state_out(dev, inter, admitted, cfg):
    gu = units_of(dev)
    states = dev[dev.label == 1].groupby('state').independence_unit.nunique()
    out = {}
    for state in sorted(states[states >= 3].index):
        held_groups = set(dev.loc[(dev.label == 1) & (dev.state == state), 'event_group_id'])
        held_units = set(gu[gu.index.isin(held_groups)])
        te = dev[dev.event_group_id.isin(held_groups)]
        tr = dev[~dev.independence_unit.isin(held_units) & ~dev.event_group_id.isin(held_groups)]
        res = {'test_events': int(te.event_group_id.nunique()), 'train_events': int(tr.event_group_id.nunique())}
        for variant in M.VARIANTS:
            score, _ = M.fit_predict('conditional_logit', tr, te, columns(variant, 'conditional_logit', inter, admitted), train_weights(tr), cfg['models'])
            res[variant] = M.summarize(M.group_ranks(te, score), gu[gu.index.isin(held_groups)])['local_auc_weighted']
        out[state] = res
    return out


def coverage(frame, admitted):
    cols = M.STATIC + M.temporal_columns(admitted)
    by_group = frame.groupby('event_group_id')[cols].agg(lambda s: s.notna().all())
    return {c: {'samples_present': float(frame[c].notna().mean()), 'groups_complete': float(by_group[c].mean())} for c in cols}


# ---------- freeze and test ----------

def code_hashes():
    files = sorted((ROOT / 'preslide/v04').glob('*.py'))
    return {f.relative_to(ROOT).as_posix(): sha(f) for f in files}


def freeze():
    if FREEZE.exists():
        sys.exit('FREEZE.json exists; the V0.4 decisions are already frozen.')
    cfg = load_config()
    data, inter = table()
    dev = data[data.partition == 'development'].reset_index(drop=True)
    admitted = admitted_daily()
    outdir = guard(V04_MODELS / f'final_{sha(CONFIG)[:12]}')
    w = train_weights(dev)
    saved = {}
    for model in M.MODELS:
        for variant in M.VARIANTS:
            cols = columns(variant, model, inter, admitted)
            _, bundle = M.fit_predict(model, dev, dev.head(6), cols, w, cfg['models'])
            path = outdir / f'{model}_{variant}.joblib'
            joblib.dump({**bundle, 'columns': cols, 'training_groups': sorted(dev.event_group_id.unique())}, path)
            saved[path.relative_to(ROOT).as_posix()] = sha(path)
    record = {'frozen_at': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha(CONFIG),
              'partition_sha256': sha(PARTITION), 'dataset_sha256': sha(run_dir() / 'dataset.parquet'),
              'dev_metrics_sha256': sha(V04_REPORT / 'dev_metrics.json'), 'admission_sha256': sha(V04_REPORT / 'admission.json'),
              'code_sha256': code_hashes(), 'models': saved, 'admitted_daily_features': admitted,
              'statement': 'All V0.4 data rules, features, models and code are fixed. The sealed test is scored once after this point.'}
    write_json(FREEZE, record)
    print(json.dumps({k: v for k, v in record.items() if k != 'code_sha256'}, indent=1))


def test():
    if TEST_RESULT.exists():
        sys.exit('The sealed test was already scored; it is never scored twice.')
    f = read_json(FREEZE)
    checks = {'config': sha(CONFIG) == f['config_sha256'], 'partition': sha(PARTITION) == f['partition_sha256'],
              'dataset': sha(run_dir() / 'dataset.parquet') == f['dataset_sha256'], 'code': code_hashes() == f['code_sha256'],
              'models': all(sha(ROOT / p) == h for p, h in f['models'].items())}
    if not all(checks.values()):
        raise RuntimeError(f'Frozen state changed: {checks}')
    cfg = load_config()
    data, inter = table()
    test_rows = data[data.partition == 'sealed_test'].reset_index(drop=True)
    dev_groups = set(data.loc[data.partition == 'development', 'event_group_id'])
    if set(test_rows.event_group_id) & dev_groups:
        raise RuntimeError('Test group also in development')
    gu = units_of(test_rows)
    result = {'scored_at': datetime.now(timezone.utc).isoformat(), 'freeze_checks': checks,
              'test': {'events': int(gu.size), 'units': int(gu.nunique()), 'samples': int(len(test_rows))}, 'results': {}}
    ranks_by = {}
    predictions = []
    for path in f['models']:
        b = joblib.load(ROOT / path)
        model, variant = path.split('/')[-1][:-7].rsplit('_', 1)
        X = test_rows[b['columns']]
        if model == 'conditional_logit':
            score = M.group_softmax(b['model'].decision_function(b['preprocessor'].transform(X, test_rows.event_group_id)), test_rows.event_group_id)
        elif model == 'logistic_regression':
            score = b['model'].predict_proba(b['preprocessor'].transform(X, test_rows.event_group_id))[:, 1]
        else:
            score = b['model'].predict_proba(X.to_numpy(float))[:, 1]
        ranks = M.group_ranks(test_rows, score)
        ranks_by[(model, variant)] = ranks
        result['results'][f'{model}/{variant}'] = {**M.summarize(ranks, gu), 'pooled_ap': M.pooled_ap(test_rows, score)}
        predictions.append(pd.DataFrame({'sample_id': test_rows.sample_id, 'model': model, 'variant': variant, 'score': score}))
    ev = cfg['evaluation']
    result['bootstrap'] = {m: M.bootstrap({v: ranks_by[(m, v)] for v in M.VARIANTS}, gu, ev['bootstrap']['draws'], ev['bootstrap']['seed'])
                           for m in M.MODELS}
    null = M.random_rank_null(gu)
    result['random_rank_null'] = {k: v for k, v in null.items() if k != 'samples'}
    for key, r in result['results'].items():
        r['p_upper_vs_random_rank'] = float((null['samples'] >= r['local_auc_weighted']).mean())
    primary = result['results']['conditional_logit/combined']
    delta = result['bootstrap']['conditional_logit']['static_minus_combined']
    result['primary'] = {'endpoint': cfg['evaluation']['primary_endpoint'], 'value': primary['local_auc_weighted'],
                         'ci95': result['bootstrap']['conditional_logit']['combined']['ci95'],
                         'combined_minus_static': {'mean': -delta['mean'], 'ci95': [-delta['ci95'][1], -delta['ci95'][0]]},
                         'chance': 0.5, 'random_rank_null_q95': null['q95']}
    tk = test_rows[test_rows.time_quality.isin(['daypart', 'clock'])].event_group_id.unique()
    result['time_known_subset'] = {f'{m}/{v}': M.summarize(r[r.event_group_id.isin(tk)], gu[gu.index.isin(tk)]) if len(tk) else None
                                   for (m, v), r in ranks_by.items()}
    guard(ANALYSIS)
    pd.concat(predictions).to_parquet(ANALYSIS / 'test_predictions.parquet', index=False)
    for (m, v), r in ranks_by.items():
        r.assign(model=m, variant=v).to_parquet(ANALYSIS / f'test_ranks_{m}_{v}.parquet', index=False)
    write_json(TEST_RESULT, result)
    print(json.dumps(result['primary'], indent=1))
    print(json.dumps({k: round(v['local_auc_weighted'], 3) for k, v in result['results'].items()}, indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('step', choices=['admission', 'develop', 'freeze', 'test'])
    p.add_argument('--pilot', action='store_true')
    a = p.parse_args()
    if a.pilot:
        if a.step in ('freeze', 'test'):
            sys.exit('Pilot data are never frozen or tested')
        use_pilot()
    {'admission': admission, 'develop': develop, 'freeze': freeze, 'test': test}[a.step]()
