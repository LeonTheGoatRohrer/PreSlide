"""Write-once pre-registration of config/susceptibility_v02.json (before any v02 download, sample, feature or model)."""
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.common import read_json  # noqa: E402
from preslide.susceptibility import v02 as V  # noqa: E402

FILES = ['config/susceptibility_v02.json', 'reports/susceptibility_v02/DECISIONS.md',
         'reports/susceptibility_v02/phase0_data_audit.json', 'reports/susceptibility_v02/mutation_check.json',
         'preslide/susceptibility/v02.py', 'tests/test_susceptibility_v02.py',
         'reports/susceptibility_v01/PHASE4_GATE.md', 'reports/susceptibility_v01/phase4_cause_analysis.json']

if V.REGISTRATION.exists():
    sys.exit(f'{V.REGISTRATION} exists (write-once).')
cfg = read_json(V.CONFIG)
V.validate(cfg)
if read_json(V.REPORT / 'mutation_check.json')['status'] != 'PASS':
    sys.exit('mutation check must pass before registration')
started = [str(p) for p in V.ROOTS[:2] if p.exists() and any(p.rglob('*'))]
if started:
    sys.exit(f'v02 data or models already exist ({started}); registration must come first')
record = {'version': V.VERSION, 'registered_at_utc': datetime.now(timezone.utc).isoformat(),
          'config_sha256': V.text_sha(V.CONFIG),
          'files_sha256_lf': {f: V.text_sha(ROOT / f) for f in FILES},
          'known_at_registration': 'All susceptibility_v01 results (seen). RER2023 attribute audit from v01 Phase 1. '
                                   'Iburi and Wenchuan candidates: file lists, geometry types, counts, bounding boxes, '
                                   'CRS, field names, metadata text, catchment-id linkage. USGS ShakeMap product '
                                   'metadata for Gorkha and Iburi. No terrain value of Iburi or RER2023, no v02 sample '
                                   'and no model output. Suedtirol not opened.',
          'phase1_gate_at_registration': cfg['gates']['phase1_status_at_registration'],
          'pending': [o['item'] for o in cfg['open_items']]}
V.REGISTRATION.write_bytes(json.dumps(record, indent=1).encode('utf-8') + b'\n')
for p in (V.REGISTRATION, V.CONFIG):
    os.chmod(p, stat.S_IREAD)
print(json.dumps(record, indent=1))
