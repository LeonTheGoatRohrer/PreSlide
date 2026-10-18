"""Output locations, write guard and the registered configuration of extremwetter_v01."""
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT
from ..v05.paths import sha

CONFIG = ROOT / 'config/extremwetter_v01.json'
REGISTRATION = ROOT / 'reports/extremwetter_v01/REGISTRATION.json'
DATA = ROOT / 'data/extremwetter_v01'
REPORT = ROOT / 'reports/extremwetter_v01'
WEB = DATA / 'web/results.json'
V04_DATASET = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'
INVENTORY = ROOT / 'data/raw/geosphere_natural_hazards.json'
ROOTS = (DATA, REPORT)


def guard(path):
    """Create `path` (a directory) only inside data/extremwetter_v01 or reports/extremwetter_v01."""
    # abspath, not resolve: data/ may be a directory junction into the main checkout.
    path = Path(os.path.abspath(path))
    roots = [Path(os.path.abspath(r)) for r in ROOTS]
    if not any(path == r or r in path.parents for r in roots):
        raise RuntimeError(f'extremwetter_v01 may only write under data/extremwetter_v01, reports/extremwetter_v01: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config():
    """The registered configuration; refuses to run if it changed after registration."""
    if not REGISTRATION.exists():
        raise RuntimeError('extremwetter_v01 is not registered')
    if sha(CONFIG) != read_json(REGISTRATION)['config_sha256']:
        raise RuntimeError('config/extremwetter_v01.json changed after registration; write an amendment instead')
    return read_json(CONFIG)
