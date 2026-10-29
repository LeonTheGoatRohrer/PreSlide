"""Registered, group-held-out context ranking; never claims absolute hazard probabilities.

python -m preslide.cascade_pilot.context register|train
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ..baseline import sha
from ..common import read_json, write_json
from ..sources import ROOT
from ..v04 import models as M
from ..v04.pipeline import load, save
from ..v05 import metrics as R
from ..v05.partition import folds, purge

VERSION = 'mudslide_cascade_v01'
CONFIG = ROOT / 'config' / f'{VERSION}.json'
DATA = ROOT / 'data' / VERSION
MODELS = ROOT / 'models' / VERSION
REPORTS = ROOT / 'reports' / VERSION
REGISTRATION = REPORTS / 'CONTEXT_REGISTRATION.json'


def guard(path: Path) -> Path:
    """Resolve junctions, then allow writes only to this experiment's three roots."""
    path = Path(path).resolve()
    if not any(path.is_relative_to(root.resolve()) for root in (DATA, MODELS, REPORTS)):
        raise PermissionError(f'Outside {VERSION}: {path}')
    return path


def validate_table(frame: pd.DataFrame, columns: list[str]) -> None:
    if frame.empty or frame.sample_id.duplicated().any():
        raise ValueError('Empty table or duplicate sample IDs')
    if frame.independence_unit.isna().any():
        raise ValueError('Missing independence units')
    if not np.isfinite(frame[columns].to_numpy(float)).all():
        raise ValueError('Required context feature missing/non-finite')
    for _, group in frame.groupby('event_group_id'):
        if len(group) != 6 or sorted(group.label.tolist()) != [0, 0, 0, 0, 0, 1]:
            raise ValueError('Context groups must contain one positive and five controls')
        if group.independence_unit.nunique() != 1 or group.event_day.nunique() != 1:
            raise ValueError('Group split across units or dates')


def validate_split(train: pd.DataFrame, held: pd.DataFrame) -> None:
    if train.empty or held.empty:
        raise ValueError('Empty training or held-out fold')
    for col in ('sample_id', 'event_group_id', 'independence_unit'):
        if set(train[col]) & set(held[col]):
            raise ValueError(f'{col} leakage')


def selected_candidates(frame: pd.DataFrame, scores: np.ndarray, fraction: float, seed: int) -> np.ndarray:
    """Fixed search budget per local candidate set. Selection never reads class labels."""
    if not 0 < fraction <= 1 or not np.isfinite(scores).all():
        raise ValueError('Invalid budget or score')
    f = frame[['sample_id', 'event_group_id']].reset_index(drop=True).copy()
    f['score'] = np.asarray(scores)
    # Stable, label-independent tie order for reproducibility.
    order = np.random.default_rng(seed).permutation(len(f))
    f['tie'] = order
    chosen = np.zeros(len(f), dtype=bool)
    for _, group in f.groupby('event_group_id', sort=True):
        n = max(1, int(np.ceil(len(group) * fraction)))
        idx = group.sort_values(['score', 'tie'], ascending=[False, True]).index[:n]
        chosen[idx] = True
    return chosen


def register() -> dict:
    if REGISTRATION.exists():
        raise FileExistsError('Context design already registered; do not overwrite')
    cfg = read_json(CONFIG)
    c = cfg['context']
    sources = [ROOT / c['source_dataset'], ROOT / c['source_partition']]
    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    raw = load(sources[0])
    if raw is None:
        raise FileNotFoundError('Verified V0.4 input checkpoint missing')
    part = pd.DataFrame(read_json(sources[1]))
    data = M.add_one_hot(raw[raw.process_type.isin(c['accepted_process_types'])].copy())
    data = data.merge(part[['event_group_id', 'independence_unit']], on='event_group_id', validate='many_to_one')
    bad = ~np.isfinite(data[c['features']].to_numpy(float)).all(axis=1)
    excluded = sorted(data.loc[bad, 'event_group_id'].unique())
    data = data[~data.event_group_id.isin(excluded)].sort_values('sample_id').reset_index(drop=True)
    validate_table(data, c['features'])
    plan = []
    for i, held_units in enumerate(folds(data.independence_unit, c['seed'], c['folds']), 1):
        purged, minimum = purge(data, held_units, c['purge_distance_m'])
        train_units = sorted(set(data.independence_unit) - set(held_units) - set(purged))
        if len(train_units) < c['minimum_train_units']:
            raise ValueError(f'Infeasible fold {i}: {len(train_units)} training units')
        plan.append({'fold': i, 'held_units': held_units, 'purged_units': purged,
                     'train_units': train_units, 'minimum_train_test_distance_m': minimum})
    DATA.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    save(data, guard(DATA / 'context.parquet'), {'config_sha256': sha(CONFIG), 'sources': source_hashes})
    out = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha(CONFIG),
           'sources': source_hashes, 'dataset_sha256': sha(DATA / 'context.parquet'), 'plan': plan,
           'excluded_groups': {'nonfinite_required_features': excluded},
           'events': int(data.event_group_id.nunique()), 'independent_units': int(data.independence_unit.nunique()),
           'scope': 'Exploratory reanalysis of already seen inventory; no new sealed test or hazard map'}
    write_json(guard(REGISTRATION), out)
    return out


def frozen_data() -> tuple[pd.DataFrame, dict, dict]:
    cfg, reg = read_json(CONFIG), read_json(REGISTRATION)
    if sha(CONFIG) != reg['config_sha256'] or sha(DATA / 'context.parquet') != reg['dataset_sha256']:
        raise ValueError('Registered config/dataset changed')
    if any(sha(ROOT / path) != digest for path, digest in reg['sources'].items()):
        raise ValueError('Registered source changed')
    data = load(DATA / 'context.parquet')
    validate_table(data, cfg['context']['features'])
    return data, cfg, reg


def train() -> dict:
    if (REPORTS / 'context_results.json').exists():
        raise FileExistsError('Pilot already evaluated; create a new version to change design')
    data, cfg, reg = frozen_data()
    c, u = cfg['context'], cfg['uncertainty']
    MODELS.mkdir(parents=True, exist_ok=True)
    score = np.full(len(data), np.nan)
    fold_ids = np.zeros(len(data), int)
    model_files = []
    for fold in reg['plan']:
        tr = data[data.independence_unit.isin(fold['train_units'])]
        te = data[data.independence_unit.isin(fold['held_units'])]
        validate_split(tr, te)
        groups = tr.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
        weights = R.unit_weights(groups).to_dict()
        pred, bundle = M.fit_predict(c['model'], tr, te, c['features'], weights, c)
        score[te.index], fold_ids[te.index] = pred, fold['fold']
        path = guard(MODELS / f"context_fold_{fold['fold']}.joblib")
        joblib.dump(bundle, path)
        model_files.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
    if not np.isfinite(score).all() or (fold_ids == 0).any():
        raise ValueError('Incomplete out-of-fold predictions')
    selected = selected_candidates(data, score, c['candidate_budget_fraction'], c['seed'])
    predictions = data[['sample_id', 'event_group_id', 'independence_unit', 'label']].assign(
        score=score, selected=selected, fold=fold_ids)
    save(predictions, guard(DATA / 'context_oof.parquet'), {'registration_sha256': sha(REGISTRATION)})
    ranks = R.group_ranks(data, score, 5)
    units = data.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
    intervals = R.bootstrap({'context': ranks}, units, u['bootstrap_draws'], u['seed'])
    null = M.random_rank_null(units, draws=u['random_rank_draws'], seed=u['seed'])
    summary = R.summarize(ranks, units)
    retained = predictions[predictions.label.eq(1)].set_index('event_group_id').selected
    retention_by_unit = retained.groupby(units).mean()
    # Reuse the existing episode-bootstrap primitive for the gate-retention indicator.
    retention_ranks = pd.DataFrame({'event_group_id': retained.index, 'local_auc': retained.astype(float).to_numpy()})
    retention_ci = R.bootstrap({'retention': retention_ranks}, units, u['bootstrap_draws'], u['seed'])
    auc = summary['local_auc_units']
    result = {'version': VERSION, 'scope': reg['scope'], 'primary': summary,
              'auc_ci95': intervals['context']['ci95'], 'random_rank_null': {k: v for k, v in null.items() if k != 'samples'},
              'random_rank_upper_p': float((1 + np.sum(null['samples'] >= auc)) / (1 + len(null['samples']))),
              'candidate_budget_fraction': c['candidate_budget_fraction'],
              'positive_retention_units': float(retention_by_unit.mean()),
              'positive_retention_ci95': retention_ci['retention']['ci95'],
              'positive_retention_events': float(retained.mean()), 'random_budget_retention': 0.5,
              'features': c['features'], 'models': model_files,
              'exclusions': reg['excluded_groups'],
              'limitations': ['Controls are inventory pseudo-negatives, not confirmed stable slopes',
                              'No road/building distance or weather as feature; reporting bias can remain',
                              'Geology is not measured soil moisture or soil strength',
                              'Candidate budget is tested on local matched point sets, not continuous area',
                              'Group-normalised scores rank candidates; they are not hazard probabilities']}
    write_json(guard(REPORTS / 'context_results.json'), result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['register', 'train'])
    stage = parser.parse_args().stage
    result = register() if stage == 'register' else train()
    print({k: v for k, v in result.items() if k in ('events', 'independent_units', 'primary', 'auc_ci95', 'positive_retention_units')}, flush=True)


if __name__ == '__main__':
    main()
