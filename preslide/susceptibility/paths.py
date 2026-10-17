"""susceptibility_v01 output locations, write guard and registered configuration.

Nothing outside data/, models/ and reports/susceptibility_v01 is ever written by this version.
"""
import hashlib
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT
from . import registry

VERSION = 'susceptibility_v01'
CONFIG = ROOT / f'config/{VERSION}.json'
REGISTRATION = ROOT / f'reports/{VERSION}/PREREGISTRATION.json'
DATA = ROOT / f'data/{VERSION}'
MODELS = ROOT / f'models/{VERSION}'
REPORT = ROOT / f'reports/{VERSION}'
ROOTS = (DATA, MODELS, REPORT)
# Sealed blind-test raw data live here; only the Phase 15 script may read them.
SEALED = DATA / 'sealed'


def text_sha(path):
    """SHA-256 of a git-tracked text file with LF line endings (Windows text mode writes CRLF, git stores LF)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def guard(path):
    """Create directory `path` only inside the version roots and never on a frozen baseline path."""
    # abspath, not resolve: data/ and models/ may be directory junctions into the main checkout.
    path = Path(os.path.abspath(path))
    roots = [Path(os.path.abspath(r)) for r in ROOTS]
    if not any(path == r or r in path.parents for r in roots):
        raise RuntimeError(f'{VERSION} may only write under {", ".join(str(r) for r in ROOTS)}: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def amendments(report=REPORT):
    """Amendments in id order; each must still match the hash recorded in its own sidecar."""
    out = []
    for p in sorted(Path(report).glob('AMENDMENT_*.json')):
        am = read_json(p)
        side = p.with_suffix('.sha256')
        if not side.exists() or side.read_text(encoding='utf-8').strip() != text_sha(p):
            raise RuntimeError(f'{p} has no matching hash sidecar (amendments are write-once)')
        out.append(am)
    return out


def config(path=CONFIG, registration=REGISTRATION, report=REPORT):
    """The registered configuration plus amendments; refuses to run if it changed after registration."""
    cfg = read_json(path)
    if Path(registration).exists() and text_sha(path) != read_json(registration)['config_sha256']:
        raise RuntimeError(f'{path} changed after pre-registration; write an amendment or a new version')
    registry.apply_amendments(cfg, amendments(report))
    registry.validate(cfg)
    return cfg
