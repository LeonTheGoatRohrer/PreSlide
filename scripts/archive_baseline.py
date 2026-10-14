"""Write-once archive of the frozen PreSlide V0.3 baseline (run before any V0.4 computation).

Copies every report, metric, prediction, model, split, figure, config, source file and the
cached raw API responses into one ZIP, records a SHA-256 for every archived member and for
every (non-archived, large) raw/interim cache file, and marks the archive read-only.
Refuses to run if the archive already exists; `--verify` re-checks it.
"""
import hashlib
import json
import os
import stat
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.baseline import verify_manifest  # noqa: E402

ARCHIVE = ROOT / 'archive/v0.3-baseline'
ZIP = ARCHIVE / 'preslide_v0.3_baseline.zip'
MANIFEST = ARCHIVE / 'ARCHIVE_MANIFEST.json'
INCLUDE = ['config', 'reports', 'models/046074ba6f12556c', 'data/processed', 'data/analysis', 'data/web',
           'data/interim/quality_candidates_pending_source_clearance.json',
           'data/interim/event_exclusion_decisions.json', 'data/raw/http',
           'data/raw/geosphere_natural_hazards.json', 'data/raw/geosphere_mass_movements.json',
           'data/raw/geosphere_inspire_media.json', 'data/raw/wlv_slides.json',
           'preslide', 'tests', 'scripts', 'frontend/src', 'frontend/package.json', 'frontend/package-lock.json',
           'requirements-lock.txt', 'README.md', 'AGENTS.md', 'PROJEKTUEBERBLICK.md', 'PROJECT_STATE.md',
           'IMPROVEMENT_PLAN.md', 'DATA_SOURCES.md', 'METHODOLOGY.md', 'RESULTS.md', 'LIMITATIONS.md']
HASH_ONLY = ['data/raw/terrain', 'data/interim/terrain', 'data/interim/control_pools']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def files(items):
    out = []
    for item in items:
        p = ROOT / item
        if p.is_dir():
            out += sorted(x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
        elif p.exists():
            out.append(p)
    return out


def create():
    if ARCHIVE.exists():
        raise SystemExit(f'{ARCHIVE} exists; the archive is write-once. Use --verify.')
    check = verify_manifest()
    if check['status'] != 'PASS':
        raise SystemExit(f'Baseline manifest does not verify: {check}')
    ARCHIVE.mkdir(parents=True)
    members = {}
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files(INCLUDE):
            rel = f.relative_to(ROOT).as_posix()
            members[rel] = sha(f)
            z.write(f, rel)
    manifest = {
        'archive': 'PreSlide V0.3 Baseline (write-once copy)', 'created_at': datetime.now(timezone.utc).isoformat(),
        'baseline_manifest_check': check, 'baseline_manifest_sha256': sha(ROOT / 'reports/baseline/BASELINE_MANIFEST.json'),
        'zip': ZIP.name, 'zip_sha256': sha(ZIP), 'members': members,
        'hash_only_not_copied': {f.relative_to(ROOT).as_posix(): sha(f) for f in files(HASH_ONLY)},
        'restore': 'Extract the ZIP into an empty directory; member paths are repository-relative.',
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    for p in (ZIP, MANIFEST):
        os.chmod(p, stat.S_IREAD)
    print(json.dumps({'members': len(members), 'hash_only': len(manifest['hash_only_not_copied']),
                      'zip_mb': round(ZIP.stat().st_size / 1e6, 1), 'zip_sha256': manifest['zip_sha256']}))


def verify():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    errors = []
    if sha(ZIP) != m['zip_sha256']:
        errors.append('zip checksum')
    with zipfile.ZipFile(ZIP) as z:
        for rel, digest in m['members'].items():
            if hashlib.sha256(z.read(rel)).hexdigest() != digest:
                errors.append(rel)
    changed_live = [rel for rel, digest in m['hash_only_not_copied'].items()
                    if not (ROOT / rel).exists() or sha(ROOT / rel) != digest]
    result = {'status': 'PASS' if not errors else 'FAIL', 'members': len(m['members']), 'errors': errors,
              'baseline_manifest': verify_manifest()['status'], 'hash_only_changed_or_missing': len(changed_live)}
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify() if '--verify' in sys.argv else create()
