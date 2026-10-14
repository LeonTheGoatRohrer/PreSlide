"""Write-once pre-registration of config/v04.json and the date/unit rules (before any V0.4 result)."""
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/v04/PREREGISTRATION.json'
FILES = ['config/v04.json', 'preslide/v04/dates.py', 'preslide/v04/units.py', 'preslide/v04/audit.py', 'tests/test_v04_dates.py']


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


if OUT.exists():
    sys.exit(f'{OUT} exists (write-once).')
summary = json.loads((ROOT / 'reports/v04/audit_summary.json').read_text(encoding='utf-8'))
record = {'registered_at': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha('config/v04.json'),
          'rule_files_sha256': {p: sha(p) for p in FILES},
          'known_at_registration': 'candidate counts, episodes and provisional partition sizes from the audit (no matching, weather, land cover, geology, features, models or scores)',
          'audit_counts': {k: summary[k] for k in ('main_candidates', 'main_temporal_episodes', 'main_spatiotemporal_units', 'provisional')},
          'baseline_manifest_sha256': sha('reports/baseline/BASELINE_MANIFEST.json'),
          'baseline_archive_manifest_sha256': sha('archive/v0.3-baseline/ARCHIVE_MANIFEST.json')}
OUT.write_text(json.dumps(record, indent=1), encoding='utf-8')
for p in (OUT, ROOT / 'config/v04.json'):
    os.chmod(p, stat.S_IREAD)
print(json.dumps(record, indent=1))
