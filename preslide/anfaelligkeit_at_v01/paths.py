"""anfaelligkeit_at_v01 output locations, write guard, registered config and hashed checkpoints.

Nothing is written outside data/anfaelligkeit_at_v01, models/anfaelligkeit_at_v01, reports/anfaelligkeit_at_v01.
"""
import hashlib
import os
from pathlib import Path

import pandas as pd

from ..baseline import frozen_paths
from ..common import read_json, write_json
from ..sources import ROOT

NAME = 'anfaelligkeit_at_v01'
CONFIG = ROOT / f'config/{NAME}.json'
REGISTRATION = ROOT / f'reports/{NAME}/PREREGISTRATION.json'
DATA = ROOT / f'data/{NAME}'
MODELS = ROOT / f'models/{NAME}'
REPORT = ROOT / f'reports/{NAME}'
ROOTS = (DATA, MODELS, REPORT)


class CacheCorruption(RuntimeError):
    pass


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def inside(path, roots=ROOTS) -> bool:
    # abspath, not resolve: data/ and models/ may be directory junctions into the main checkout.
    path = Path(os.path.abspath(path))
    return any(path == Path(os.path.abspath(r)) or Path(os.path.abspath(r)) in path.parents for r in roots)


def guard(path) -> Path:
    """Create `path` (a directory) only inside the version roots and never on a frozen baseline path."""
    path = Path(os.path.abspath(path))
    if not inside(path):
        raise RuntimeError(f'{NAME} may only write under data/, models/, reports/{NAME}: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def config() -> dict:
    """The registered configuration; refuses to run if it or a registered input changed after registration."""
    if not REGISTRATION.exists():
        raise RuntimeError(f'config/{NAME}.json is not registered')
    reg = read_json(REGISTRATION)
    if sha(CONFIG) != reg['config_sha256']:
        raise RuntimeError(f'config/{NAME}.json changed after pre-registration; write an amendment or a new version')
    for rel, expected in reg['input_sha256'].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f'Registered input changed: {rel}')
    return read_json(CONFIG)


def save(frame: pd.DataFrame, path, meta=None) -> None:
    """Parquet checkpoint with a SHA-256 sidecar (same contract as preslide.v04.pipeline.save)."""
    path = Path(path)
    guard(path.parent)
    frame.to_parquet(path, index=False)
    write_json(path.with_suffix('.json'), {**(meta or {}), 'sha256': sha(path), 'rows': len(frame)})


def load(path):
    """Checkpoint or None; a checksum mismatch raises instead of silently recomputing."""
    path = Path(path)
    side = path.with_suffix('.json')
    if not path.exists() or not side.exists():
        return None
    if sha(path) != read_json(side)['sha256']:
        raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
    return pd.read_parquet(path)


def load_meta(path) -> dict:
    return read_json(Path(path).with_suffix('.json'))
