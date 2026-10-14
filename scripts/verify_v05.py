"""Verify the completed V0.5 run: registration, cohort freeze, CV integrity, stored predictions, V0.4 untouched."""
import hashlib
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.v05 import integrity  # noqa: E402
from preslide.v05 import models as M  # noqa: E402
from preslide.v05.experiment import prepare  # noqa: E402
from preslide.v05.paths import config  # noqa: E402
from preslide.v05 import pipeline as P  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    reg = json.loads((ROOT / 'reports/v05/PREREGISTRATION.json').read_text())
    fr = json.loads((ROOT / 'reports/v05/COHORT_FREEZE.json').read_text())
    res = json.loads((ROOT / 'reports/v05/cv_results.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / 'data/v05/cv/cv_plan.json').read_text())['primary']
    cfg = config()
    data = prepare(P.load(P.run_dir() / 'dataset.parquet'), cfg)
    oof = pd.read_parquet(ROOT / 'data/v05/analysis/oof_purged.parquet')
    unit = data.set_index('sample_id').independence_unit
    leak = 0
    for f in plan:
        o = oof[(oof.repetition == f['repetition']) & (oof.fold == f['fold'])]
        held = set(o.sample_id.map(unit))
        leak += int(bool(held - set(f['held_units'])) or bool(set(f['train_units']) & set(f['held_units'])) or
                    bool(set(f['purged_units']) & set(f['train_units'])))
    once = oof.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data)).all()
    refit = []
    for path, h in res['final_models'].items():
        refit.append(sha(ROOT / path) == h)
        b = joblib.load(ROOT / path)
        M.check_allowlist(b['columns'], cfg)
    checks = {
        'config_matches_registration': sha(ROOT / 'config/v05.json') == reg['config_sha256'],
        'config_matches_cohort_freeze': sha(ROOT / 'config/v05.json') == fr['config_sha256'],
        'dataset_matches_cohort_freeze': sha(P.run_dir() / 'dataset.parquet') == fr['dataset_sha256'],
        'cv_plan_matches_cohort_freeze': sha(ROOT / 'data/v05/cv/cv_plan.json') == fr['cv_plan_sha256'],
        'results_computed_on_frozen_cohort': res['frozen_inputs']['cohort_freeze_sha256'] == sha(ROOT / 'reports/v05/COHORT_FREEZE.json'),
        'registration_before_freeze': reg['registered_at'] < fr['frozen_at'],
        'held_out_units_never_trained_or_purged_reused': leak == 0,
        'one_oof_prediction_per_sample_and_repetition': bool(once),
        'final_models_hashes_and_allowlist': all(refit),
        'groups_complete_1_plus_10': bool((data.groupby('event_group_id').size() == 11).all()),
        'v04_untouched': integrity.after()['changed_or_missing'] == [],
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks,
           'note': 'Baseline manifest (reports/baseline) is verified in the main checkout; a git worktree has normalised '
                   'line endings and lacks git-ignored baseline files.'}
    (ROOT / 'reports/v05/verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return status == 'PASS'


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
