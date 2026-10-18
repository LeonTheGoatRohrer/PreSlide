"""Write-once pre-registration of config/susceptibility_v01.json (before any inventory download, feature or model)."""
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.common import read_json  # noqa: E402
from preslide.susceptibility import paths as P, registry  # noqa: E402

FILES = ['config/susceptibility_v01.json', 'reports/weiterentwicklung_2026-10-17/ANFAELLIGKEITSSYSTEM_PLAN.md',
         'reports/weiterentwicklung_2026-10-17/RUTSCHUNGSDATENSAETZE_WELTWEIT.md',
         'reports/susceptibility_v01/DECISIONS.md', 'reports/susceptibility_v01/phase0_evidence.json',
         'reports/susceptibility_v01/mutation_check.json', 'preslide/susceptibility/registry.py',
         'preslide/susceptibility/paths.py']

if P.REGISTRATION.exists():
    sys.exit(f'{P.REGISTRATION} exists (write-once).')
cfg = read_json(P.CONFIG)
registry.validate(cfg)
if read_json(ROOT / 'reports/susceptibility_v01/mutation_check.json')['status'] != 'PASS':
    sys.exit('mutation check must pass before registration')
if any(P.DATA.glob('raw/**/*')):
    sys.exit('inventory files already exist under data/susceptibility_v01/raw; registration must come first')
record = {'version': P.VERSION, 'registered_at_utc': datetime.now(timezone.utc).isoformat(),
          'config_sha256': P.text_sha(P.CONFIG),
          'files_sha256_lf': {f: P.text_sha(ROOT / f) for f in FILES},
          'known_at_registration': 'Plan, dataset survey, Zenodo metadata (licence, size, md5) for Far-Western Nepal and '
                                   'RER2023; Suedtirol WFS field list, layer counts and movement-class counts without '
                                   'geometry. No inventory geometry, terrain value, feature or model output.',
          'pending_by_amendment': [o['item'] for o in cfg['open_items']]}
P.REGISTRATION.write_bytes(json.dumps(record, indent=1).encode('utf-8') + b'\n')
for p in (P.REGISTRATION, P.CONFIG):
    os.chmod(p, stat.S_IREAD)
print(json.dumps(record, indent=1))
