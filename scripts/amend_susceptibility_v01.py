"""Write-once amendment to the registered susceptibility_v01 design (only before any sample, feature or model).

python scripts/amend_susceptibility_v01.py <draft.json>
The draft holds id, reason, and set/correct/add operations (see preslide.susceptibility.registry.apply_amendments).
"""
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

# An amendment states the earliest stage it must precede; everything from that stage on must not exist yet.
STAGES = {'samples': [P.DATA / 'samples', P.DATA / 'features', P.MODELS],
          'features': [P.DATA / 'features', P.DATA / 'samples', P.MODELS],
          'models': [P.MODELS, P.DATA / 'predictions']}


def main(draft_path):
    if not P.REGISTRATION.exists():
        sys.exit('not registered')
    draft = read_json(draft_path)
    later = STAGES[draft.get('before', 'samples')]
    started = [str(p) for p in later if p.exists() and any(p.rglob('*'))]
    if started:
        sys.exit(f'later-stage outputs already exist ({started}); a design change now needs a new version')
    existing = P.amendments()
    if draft['id'] != len(existing) + 1:
        sys.exit(f'amendment id must be {len(existing) + 1}')
    cfg = P.config()
    registry.apply_amendments(cfg, [draft])
    registry.validate(cfg)
    record = {**draft, 'written_at_utc': datetime.now(timezone.utc).isoformat(),
              'config_sha256': P.text_sha(P.CONFIG),
              'preconditions': f'registration present; nothing from stage {draft.get("before", "samples")!r} on existed'}
    out = P.REPORT / f'AMENDMENT_{draft["id"]}.json'
    if out.exists():
        sys.exit(f'{out} exists (write-once)')
    out.write_bytes(json.dumps(record, indent=1, ensure_ascii=False).encode('utf-8') + b'\n')
    side = out.with_suffix('.sha256')
    side.write_bytes((P.text_sha(out) + '\n').encode())
    for p in (out, side):
        os.chmod(p, stat.S_IREAD)
    P.config()  # re-load through the normal path to prove the amendment applies cleanly
    print(json.dumps(record, indent=1, ensure_ascii=False)[:3000])


if __name__ == '__main__':
    main(sys.argv[1])
