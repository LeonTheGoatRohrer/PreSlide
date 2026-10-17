"""V0.7 output locations and write guard; V0.7 writes only data/v07, models/v07, reports/v07."""
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT
from ..v05.paths import sha

CONFIG = ROOT / 'config/v07.json'
REGISTRATION = ROOT / 'reports/v07/PREREGISTRATION.json'
V07_DATA = ROOT / 'data/v07'
V07_REPORT = ROOT / 'reports/v07'
ROOTS = (V07_DATA, ROOT / 'models/v07', V07_REPORT)
V05_OOF = ROOT / 'data/v05/analysis/oof_purged.parquet'
V05_DATASET = ROOT / 'data/v05/run_5b86b6475ecb/dataset.parquet'
V05_CV_PLAN = ROOT / 'data/v05/cv/cv_plan.json'


def guard(path) -> Path:
    path = Path(os.path.abspath(path))
    if not any(path == Path(os.path.abspath(r)) or Path(os.path.abspath(r)) in path.parents for r in ROOTS):
        raise RuntimeError(f'V0.7 may only write under data/v07, models/v07, reports/v07: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config() -> dict:
    """The registered configuration; refuses to run if it or its inputs changed after registration."""
    cfg = read_json(CONFIG)
    if REGISTRATION.exists() and sha(CONFIG) != read_json(REGISTRATION)['config_sha256']:
        raise RuntimeError('config/v07.json changed after pre-registration; create a new version instead')
    for path, key in ((V05_DATASET, 'dataset_sha256'), (V05_CV_PLAN, 'cv_plan_sha256'), (V05_OOF, 'v05_oof_sha256')):
        if sha(path) != cfg['inputs'][key]:
            raise RuntimeError(f'V0.5 input changed: {path}')
    return cfg
