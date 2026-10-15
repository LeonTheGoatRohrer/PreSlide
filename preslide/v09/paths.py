"""V0.9 output locations and write guard. V0.9 never writes outside data/v09, models/v09, reports/v09."""
import hashlib
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/v09.json'
REGISTRATION = ROOT / 'reports/v09/PREREGISTRATION.json'
V09_DATA = ROOT / 'data/v09'
V09_MODELS = ROOT / 'models/v09'
V09_REPORT = ROOT / 'reports/v09'
ROOTS = (V09_DATA, V09_MODELS, V09_REPORT)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def inside(path, roots=ROOTS):
    # abspath, not resolve: data/ and models/ may be directory junctions into the main checkout.
    path = Path(os.path.abspath(path))
    return any(path == Path(os.path.abspath(r)) or Path(os.path.abspath(r)) in path.parents for r in roots)


def guard(path):
    """Create `path` (a directory) only inside the V0.9 roots and never on a frozen baseline path."""
    path = Path(os.path.abspath(path))
    if not inside(path):
        raise RuntimeError(f'V0.9 may only write under data/v09, models/v09, reports/v09: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config():
    """The registered configuration; refuses to run if it or a registered input changed after registration."""
    cfg = read_json(CONFIG)
    if not REGISTRATION.exists():
        raise RuntimeError('config/v09.json is not registered (scripts/register.py config/v09.json reports/v09)')
    reg = read_json(REGISTRATION)
    if sha(CONFIG) != reg['config_sha256']:
        raise RuntimeError('config/v09.json changed after pre-registration; write an amendment or a new version')
    for rel, expected in reg['input_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f'Registered V0.9 input changed: {rel}')
    return cfg
