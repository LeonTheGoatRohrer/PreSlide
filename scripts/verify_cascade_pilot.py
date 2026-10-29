"""Read-only verification of the new context pilot, source hashes and OOF predictions.

Writes only reports/mudslide_cascade_v01/verification.json; never trains or re-scores V0.4.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import numpy as np

from preslide.baseline import sha, verify_manifest
from preslide.common import read_json, write_json
from preslide.sources import ROOT
from preslide.cascade_pilot.context import (
    DATA, REPORTS, frozen_data, guard, selected_candidates, validate_split,
)
from preslide.v04 import models as M
from preslide.v04.pipeline import load
from preslide.v05 import metrics as R
from preslide.v05.partition import purge


def main():
    data, cfg, reg = frozen_data()
    c = cfg['context']
    result = read_json(REPORTS / 'context_results.json')
    preds = load(DATA / 'context_oof.parquet')
    checks = {'registered_inputs': True, 'prediction_ids_exactly_once': (
        preds.sample_id.is_unique and preds.sample_id.tolist() == data.sample_id.tolist()),
        'baseline_manifest': verify_manifest()['status'] == 'PASS'}
    reproduced = np.full(len(data), np.nan)
    for plan, model in zip(reg['plan'], result['models'], strict=True):
        train = data[data.independence_unit.isin(plan['train_units'])]
        held = data[data.independence_unit.isin(plan['held_units'])]
        validate_split(train, held)
        purged, minimum = purge(data, plan['held_units'], c['purge_distance_m'])
        checks[f"fold_{plan['fold']}_purge"] = purged == plan['purged_units'] and minimum >= c['purge_distance_m']
        path = ROOT / model['path']
        checks[f"fold_{plan['fold']}_model_hash"] = sha(path) == model['sha256']
        bundle = joblib.load(path)
        x = bundle['preprocessor'].transform(held[c['features']], held.event_group_id)
        reproduced[held.index] = M.group_softmax(bundle['model'].decision_function(x), held.event_group_id)
    checks['saved_models_reproduce_all_predictions'] = bool(np.allclose(reproduced, preds.score, atol=1e-12, rtol=0))
    checks['gate_reproduced'] = bool(np.array_equal(
        preds.selected, selected_candidates(data, reproduced, c['candidate_budget_fraction'], c['seed'])))
    units = data.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
    summary = R.summarize(R.group_ranks(data, reproduced, 5), units)
    checks['all_ranking_metrics_reproduced'] = all(np.isclose(summary[k], v, atol=1e-12) for k, v in result['primary'].items())
    out = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
           'max_prediction_difference': float(np.max(np.abs(reproduced - preds.score))),
           'scope': 'New exploratory context pilot only; no image detector trained or validated here'}
    write_json(guard(REPORTS / 'verification.json'), out)
    print(out, flush=True)
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
