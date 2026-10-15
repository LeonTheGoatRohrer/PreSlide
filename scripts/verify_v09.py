"""Verify the completed V0.9 run: registration, untouched V0.4, cohort rules, audit, dataset, units, freeze, scores.

  .venv\\Scripts\\python scripts/verify_v09.py      -> reports/v09/verification.json
"""
import json
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.common import read_json, write_json  # noqa: E402
from preslide.v04 import models as M  # noqa: E402
from preslide.v04.pipeline import load, validate  # noqa: E402
from preslide.v09 import audit, cohort, experiment as X  # noqa: E402
from preslide.v09.paths import V09_DATA, V09_REPORT, config, sha  # noqa: E402
from preslide.v09.pipeline import eligible, validate_v09  # noqa: E402


def git_clean(paths):
    out = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, capture_output=True, text=True)
    return out.returncode == 0 and out.stdout.strip() == ''


def main():
    cfg = config()                                              # registration + registered input hashes
    checks = {'registration_and_inputs': True}
    checks['frozen_v04_models'] = all(sha(ROOT / p) == h for p, h in cfg['frozen_v04_models'].items())
    checks['v04_and_baseline_tracked_files_unmodified'] = git_clean(['reports/v04', 'config/v04.json', 'reports/baseline',
                                                                     'archive', 'reports/v05', 'config/v05.json'])
    cand = pd.DataFrame(json.loads((V09_DATA / 'audit/candidates.json').read_text(encoding='utf-8')))
    seen = pd.DataFrame(read_json(cohort.V04_CANDIDATES))[['event_id', 'event_day', 'x', 'y']]
    redo = cohort.unseen_blocks(seen, cand[['event_id', 'event_day', 'x', 'y']], cfg['partition']['positive_link_m'])
    checks['no_eligible_event_in_a_seen_block'] = not redo.seen_block.any()
    checks['no_eligible_event_is_a_v04_candidate'] = not set(cand.event_id) & set(seen.event_id)
    checks['no_media_process_conflict'] = not cand[cand.cohort == 'media'].process_conflict_other_source.astype(bool).any()
    entries = read_json(V09_DATA / 'audit/process_audit.json')['entries']
    checks['audit_covers_exactly_the_media_candidates'] = {e['event_id'] for e in entries} == set(cand[cand.cohort == 'media'].event_id)
    gate = audit.gate([e['category'] for e in entries], cfg)
    stored = read_json(V09_REPORT / 'process_audit_summary.json')['gate']
    checks['audit_gate_recomputed'] = gate['passes'] == stored['passes'] and gate['counts'] == stored['counts']
    data = load(X.run_dir() / 'dataset.parquet')
    checks['dataset_v04_invariants'] = validate(data, cfg)['checks'] == 'PASS'
    checks['dataset_v09_invariants'] = validate_v09(data, cfg)['v09_checks'] == 'PASS'
    allowed = {e['event_id'] for e in eligible()}
    checks['dataset_only_audited_eligible_events'] = set(data.event_group_id) <= allowed
    excluded = {e['event_id'] for e in entries if e['category'] in ('other_process', 'date_conflict')}
    checks['no_audit_excluded_event_in_dataset'] = not set(data.event_group_id) & excluded
    last = pd.to_datetime(data.last_used_hour_utc, utc=True) + pd.Timedelta(hours=1)
    checks['all_inca_hours_before_t0'] = bool((last < pd.to_datetime(data.t0_utc, utc=True)).all())
    units = pd.DataFrame(read_json(X.UNITS))
    part = read_json(V09_REPORT / 'partition_summary.json')
    checks['purged_groups_absent'] = not set(part['purged_seen_location']) & set(units.event_group_id)
    v04 = load(X.V04_DATASET)
    checks['purge_recomputed'] = X.seen_location_groups(data, v04, cfg['partition']['spatial_purge_m']) == set(part['purged_seen_location'])
    kept = data[data.event_group_id.isin(units.event_group_id)]
    redo_units = X.unit_table(kept, cfg['partition']['positive_link_m'], cfg['matching']['control_separation_m'])
    same = units.set_index('event_group_id').pooled_unit.sort_index().equals(redo_units.unit.sort_index())
    checks['pooled_units_recomputed'] = bool(same)
    checks['units_one_per_group'] = units.event_group_id.is_unique
    f = read_json(X.FREEZE)
    checks['freeze_hashes'] = (sha(X.run_dir() / 'dataset.parquet') == f['dataset_sha256'] and sha(X.UNITS) == f['units_sha256']
                               and sha(V09_DATA / 'audit/process_audit.json') == f['process_audit_sha256']
                               and all(sha(ROOT / p) == h for p, h in {**f['refit_models'], **f['frozen_v04_models']}.items()))
    res = read_json(X.RESULT)
    checks['scored_once_after_freeze'] = res['scored_at'] > f['frozen_at']
    pred = pd.read_parquet(V09_DATA / 'analysis/test_predictions.parquet')
    table, _ = X.with_derived(data)
    table = table.merge(units[['event_group_id', 'cohort_unit', 'pooled_unit']], on='event_group_id').reset_index(drop=True)
    worst = 0.0
    for name, paths in X.model_sets(cfg).items():
        for (model, variant), p in paths.items():
            s = X.scores(joblib.load(ROOT / p), model, table)
            stored_s = pred[(pred.model_set == name) & (pred.model == model) & (pred.variant == variant)].set_index('sample_id').score
            worst = max(worst, float(np.max(np.abs(stored_s.loc[table.sample_id].to_numpy() - s))))
    checks['stored_predictions_reproduced'] = worst < 1e-9
    rows, gu = X.cohort_rows(table, 'media')
    s = X.scores(joblib.load(ROOT / X.model_sets(cfg)['refit_all'][('conditional_logit', 'combined')]), 'conditional_logit', table)
    auc = M.summarize(M.group_ranks(rows, s[rows.index.to_numpy()]), gu)['local_auc_weighted']
    checks['primary_auc_recomputed'] = abs(auc - res['primary']['combined']['local_auc_weighted']) < 1e-12
    out = {'checks': checks, 'max_prediction_difference': worst, 'status': 'PASS' if all(checks.values()) else 'FAIL'}
    write_json(V09_REPORT / 'verification.json', out)
    print(json.dumps(out, indent=1))
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
