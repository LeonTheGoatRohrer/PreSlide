"""V0.4 output locations and write guard. Nothing outside these roots is ever written by V0.4."""
import hashlib
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/v04.json'
REGISTRATION = ROOT / 'reports/v04/PREREGISTRATION.json'
V04_DATA = ROOT / 'data/v04'
V04_MODELS = ROOT / 'models/v04'
V04_REPORT = ROOT / 'reports/v04'
ROOTS = (V04_DATA, V04_MODELS, V04_REPORT)


def guard(path):
    """Create `path` (a directory) only inside the V0.4 roots and never on a frozen baseline path."""
    path = Path(path).resolve()
    if not any(path == r.resolve() or r.resolve() in path.parents for r in ROOTS):
        raise RuntimeError(f'V0.4 may only write under data/v04, models/v04, reports/v04: {path}')
    rel = path.relative_to(ROOT.resolve()).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config():
    """The registered configuration; refuses to run if it changed after registration."""
    if REGISTRATION.exists():
        expected = read_json(REGISTRATION)['config_sha256']
        actual = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError('config/v04.json changed after pre-registration; create a new version instead')
    return read_json(CONFIG)
