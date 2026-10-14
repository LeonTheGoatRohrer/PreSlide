"""Write-once pre-registration of config/v05.json (before any V0.5 control, feature, model or score)."""
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.v05 import integrity  # noqa: E402

OUT = ROOT / 'reports/v05/PREREGISTRATION.json'
FILES = ['config/v05.json', 'reports/weiterentwicklung_2026-10-14/V05_NACHBARHANG_PLAN.md',
         'data/v04/run_c6d67a854ba7/dataset.parquet', 'data/v04/partition/partition.json', 'data/v04/audit/candidates.json']


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


if OUT.exists():
    sys.exit(f'{OUT} exists (write-once).')
cfg = json.loads((ROOT / 'config/v05.json').read_text(encoding='utf-8'))
for key, path in (('dataset_sha256', FILES[2]), ('partition_sha256', FILES[3])):
    if sha(path) != cfg['inputs'][key]:
        sys.exit(f'{path} does not match the hash in config/v05.json')
snap = integrity.before()
OUT.parent.mkdir(parents=True, exist_ok=True)
record = {'registered_at': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha('config/v05.json'),
          'files_sha256': {p: sha(p) for p in FILES},
          'v04_integrity_snapshot': snap,
          'known_at_registration': 'V0.4 artifacts and results (V0.4 test already seen); existence of 485 V0.4 control pools. '
                                   'No V0.5 control selection, feature, model or score.',
          'nature': 'exploratory grouped CV; no new independent test'}
OUT.write_text(json.dumps(record, indent=1), encoding='utf-8')
for p in (OUT, ROOT / 'config/v05.json'):
    os.chmod(p, stat.S_IREAD)
print(json.dumps(record, indent=1))
