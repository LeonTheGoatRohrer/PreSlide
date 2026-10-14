"""Verify the completed V0.4 run: registration, freeze hashes, partition rules, single test scoring, baseline intact."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.baseline import verify_manifest  # noqa: E402


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    reg = json.loads((ROOT / 'reports/v04/PREREGISTRATION.json').read_text())
    freeze = json.loads((ROOT / 'reports/v04/FREEZE.json').read_text())
    test = json.loads((ROOT / 'reports/v04/test_results.json').read_text())
    part = pd.DataFrame(json.loads((ROOT / 'data/v04/partition/partition.json').read_text(encoding='utf-8')))
    run = next((ROOT / 'data/v04').glob('run_*'))
    checks = {
        'config_matches_registration': sha('config/v04.json') == reg['config_sha256'],
        'config_matches_freeze': sha('config/v04.json') == freeze['config_sha256'],
        'partition_matches_freeze': sha('data/v04/partition/partition.json') == freeze['partition_sha256'],
        'dataset_matches_freeze': sha(run.relative_to(ROOT) / 'dataset.parquet') == freeze['dataset_sha256'],
        'models_match_freeze': all(sha(p) == h for p, h in freeze['models'].items()),
        'test_scored_after_freeze': test['scored_at'] > freeze['frozen_at'],
        'test_freeze_checks_passed': all(test['freeze_checks'].values()),
        'units_on_one_side': bool(part.groupby('independence_unit').partition.nunique().max() == 1),
        'episodes_on_one_side': bool(part.groupby('temporal_episode').partition.nunique().max() == 1),
        'no_baseline_event_in_test': not bool(part[(part.partition == 'sealed_test') & part.in_v03_baseline_candidates].shape[0]),
        'baseline_manifest': verify_manifest()['status'] == 'PASS',
    }
    archive = subprocess.run([sys.executable, str(ROOT / 'scripts/archive_baseline.py'), '--verify'], capture_output=True, text=True)
    checks['baseline_archive'] = '"status": "PASS"' in archive.stdout and '"hash_only_changed_or_missing": 0' in archive.stdout
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks}
    (ROOT / 'reports/v04/verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return status == 'PASS'


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
