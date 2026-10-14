"""V0.4/baseline integrity: hash snapshot before V0.5 and comparison afterwards.

python -m preslide.v05.integrity before|after
"""
import hashlib
import json
import sys

from ..baseline import verify_manifest
from ..common import read_json, write_json
from ..sources import ROOT
from .paths import V05_DATA, V05_REPORT, guard, sha

TREES = ['data/v04', 'models/v04', 'reports/v04', 'preslide/v04']
FILES = ['config/v04.json', 'reports/baseline/BASELINE_MANIFEST.json', 'archive/v0.3-baseline/ARCHIVE_MANIFEST.json']


TEXT = ('.py', '.json', '.md', '.csv', '.txt')


def file_hash(rel):
    """Byte hash; git-tracked text outside data/ and models/ is compared with LF line endings (checkouts differ)."""
    p = ROOT / rel
    if rel.startswith(('data/', 'models/')) or not rel.endswith(TEXT):
        return sha(p)
    return hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def snapshot():
    out = {}
    for tree in TREES:
        for p in sorted((ROOT / tree).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                rel = p.relative_to(ROOT).as_posix()
                out[rel] = file_hash(rel)
    for f in FILES:
        out[f] = file_hash(f)
    return out


def before():
    path = guard(V05_DATA / 'integrity') / 'v04_before.json'
    if path.exists():
        sys.exit(f'{path} exists (write-once)')
    snap = snapshot()
    write_json(path, snap)
    return {'files': len(snap), 'snapshot_sha256': sha(path), 'baseline_manifest': verify_manifest()['status']}


def after():
    before_ = read_json(V05_DATA / 'integrity/v04_before.json')
    now = snapshot()
    changed = sorted(p for p, h in before_.items() if now.get(p) != h)
    added = sorted(set(now) - set(before_))
    result = {'files_before': len(before_), 'changed_or_missing': changed, 'added': added,
              'baseline_manifest': verify_manifest()['status'],
              'status': 'PASS' if not changed and not added and verify_manifest()['status'] == 'PASS' else 'FAIL'}
    write_json(guard(V05_REPORT) / 'v04_integrity_after.json', result)
    return result


if __name__ == '__main__':
    print(json.dumps({'before': before, 'after': after}[sys.argv[1]](), indent=1))
