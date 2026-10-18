"""V0.7b output locations and write guard; V0.7b writes only data/v07b, models/v07b, reports/v07b."""
import os
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT
from ..v05.paths import sha

CONFIG = ROOT / 'config/v07b.json'
REGISTRATION = ROOT / 'reports/v07b/PREREGISTRATION.json'
V07B_DATA = ROOT / 'data/v07b'
V07B_REPORT = ROOT / 'reports/v07b'
ROOTS = (V07B_DATA, ROOT / 'models/v07b', V07B_REPORT)
V07_REPORT = ROOT / 'reports/v07'


def guard(path) -> Path:
    path = Path(os.path.abspath(path))
    if not any(path == Path(os.path.abspath(r)) or Path(os.path.abspath(r)) in path.parents for r in ROOTS):
        raise RuntimeError(f'V0.7b may only write under data/v07b, models/v07b, reports/v07b: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config() -> dict:
    """The registered configuration; refuses to run without registration or if it or any registered input changed."""
    cfg = read_json(CONFIG)
    if not REGISTRATION.exists() or sha(CONFIG) != read_json(REGISTRATION)['config_sha256']:
        raise RuntimeError('config/v07b.json is not registered or changed after registration; create a new version instead')
    for key, expected in cfg['inputs'].items():
        if key.endswith('_sha256') and sha(ROOT / cfg['inputs'][key[:-len('_sha256')]]) != expected:
            raise RuntimeError(f'registered input changed: {cfg["inputs"][key[:-len("_sha256")]]}')
    return cfg
