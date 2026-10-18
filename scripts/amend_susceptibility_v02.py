"""Write-once amendment to the registered susceptibility_v02 design (only before the stage it names has outputs).

python scripts/amend_susceptibility_v02.py <draft.json>
The draft holds id, before, title, basis and set/correct/add operations
(see preslide.susceptibility.registry.apply_amendments); the v02 rules (v02.validate) must hold afterwards.
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
from preslide.susceptibility import v02 as V  # noqa: E402
from preslide.susceptibility.paths import amendments, text_sha  # noqa: E402
from preslide.susceptibility.registry import apply_amendments  # noqa: E402

# Everything from the named stage on must not exist yet. A 'features' amendment (terrain parameters) must precede the
# v02 terrain blocks; a 'samples' amendment (sampling rules) must precede v02 samples and models; a 'models' amendment
# must precede models and predictions. data/features and data/predictions also hold the registered Gorkha
# sensitivity, which runs on the read-only v01 samples and depends on no sampling parameter.
STAGES = {'features': [V.DATA / 'terrain', V.DATA / 'samples', V.MODELS],
          'samples': [V.DATA / 'samples', V.MODELS],
          'models': [V.MODELS, V.DATA / 'predictions']}


def main(draft_path):
    if not V.REGISTRATION.exists():
        sys.exit('not registered')
    draft = read_json(draft_path)
    later = STAGES[draft.get('before', 'samples')]
    started = [str(p) for p in later if p.exists() and any(p.rglob('*'))]
    if started:
        sys.exit(f'later-stage outputs already exist ({started}); a design change now needs a new version')
    existing = amendments(V.REPORT)
    if draft['id'] != len(existing) + 1:
        sys.exit(f'amendment id must be {len(existing) + 1}')
    cfg = V.config()
    apply_amendments(cfg, [draft])
    V.validate(cfg)
    record = {**draft, 'written_at_utc': datetime.now(timezone.utc).isoformat(),
              'config_sha256': text_sha(V.CONFIG),
              'preconditions': f'registration present; nothing from stage {draft.get("before", "samples")!r} on existed'}
    out = V.REPORT / f'AMENDMENT_{draft["id"]}.json'
    if out.exists():
        sys.exit(f'{out} exists (write-once)')
    out.write_bytes(json.dumps(record, indent=1, ensure_ascii=False).encode('utf-8') + b'\n')
    side = out.with_suffix('.sha256')
    side.write_bytes((text_sha(out) + '\n').encode())
    for p in (out, side):
        os.chmod(p, stat.S_IREAD)
    V.config()  # re-load through the normal path to prove the amendment applies cleanly
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(record, indent=1, ensure_ascii=False)[:4000])


if __name__ == '__main__':
    main(sys.argv[1])
