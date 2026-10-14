"""V0.5 output locations and write guard. V0.5 never writes outside data/v05, models/v05, reports/v05."""
import hashlib
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/v05.json'
REGISTRATION = ROOT / 'reports/v05/PREREGISTRATION.json'
V05_DATA = ROOT / 'data/v05'
V05_MODELS = ROOT / 'models/v05'
V05_REPORT = ROOT / 'reports/v05'
ROOTS = (V05_DATA, V05_MODELS, V05_REPORT)
V04_DATASET = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'
V04_PARTITION = ROOT / 'data/v04/partition/partition.json'
V04_POOLS = ROOT / 'data/v04/cache/control_pools'
V04_CANDIDATES = ROOT / 'data/v04/audit/candidates.json'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def guard(path):
    """Create `path` (a directory) only inside the V0.5 roots and never on a frozen baseline path."""
    # abspath, not resolve: data/ and models/ may be directory junctions into the main checkout.
    path = Path(os.path.abspath(path))
    roots = [Path(os.path.abspath(r)) for r in ROOTS]
    if not any(path == r or r in path.parents for r in roots):
        raise RuntimeError(f'V0.5 may only write under data/v05, models/v05, reports/v05: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config():
    """The registered configuration; refuses to run if it or its inputs changed after registration."""
    cfg = read_json(CONFIG)
    if REGISTRATION.exists():
        reg = read_json(REGISTRATION)
        if sha(CONFIG) != reg['config_sha256']:
            raise RuntimeError('config/v05.json changed after pre-registration; create a new version instead')
    for path, key in ((V04_DATASET, 'dataset_sha256'), (V04_PARTITION, 'partition_sha256')):
        if sha(path) != cfg['inputs'][key]:
            raise RuntimeError(f'V0.4 input changed: {path}')
    return cfg
