"""Pipeline B roots and write guard. Pipeline A paths (data/v04, data/processed, baseline) are read only here."""
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/satellite.json'
SAT_DATA = ROOT / 'data/satellite'
SAT_MODELS = ROOT / 'models/satellite'
SAT_REPORT = ROOT / 'reports/satellite'
ROOTS = (SAT_DATA, SAT_MODELS, SAT_REPORT)
CA_BUNDLE = ROOT / 'data/runtime/windows-ca.pem'


def guard(path):
    """Create directory `path` only inside the Pipeline B roots and never on a frozen baseline path."""
    # os.path.abspath normalises without following junctions (data/ may be a junction to another checkout).
    path = Path(os.path.abspath(path))
    roots = [Path(os.path.abspath(r)) for r in ROOTS]
    if not any(path == r or r in path.parents for r in roots):
        raise RuntimeError(f'Pipeline B may only write under data/satellite, models/satellite, reports/satellite: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config():
    return read_json(CONFIG)
