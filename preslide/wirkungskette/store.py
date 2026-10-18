"""Checkpoint IO for wirkungskette_v01: every file has a sidecar with SHA-256 and the identity it was built for.

A checkpoint whose bytes or identity do not match raises; nothing is silently rebuilt over a mismatch.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..common import write_json, read_json


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sidecar(path):
    return Path(path).with_name(Path(path).name + '.meta.json')


def _seal(path, identity, extra=None):
    write_json(_sidecar(path), {'identity': identity, 'sha256': _sha(path), **(extra or {})})


def exists(path):
    return Path(path).exists() and _sidecar(path).exists()


def check(path, identity):
    meta = read_json(_sidecar(path))
    if meta['identity'] != identity:
        raise RuntimeError(f'Checkpoint {Path(path).name} was built for another configuration (identity mismatch)')
    if meta['sha256'] != _sha(path):
        raise RuntimeError(f'Checkpoint {Path(path).name} checksum mismatch')
    return meta


def save_npz(path, identity, arrays, extra=None):
    np.savez_compressed(path, **arrays)
    _seal(path, identity, extra)


def load_npz(path, identity):
    check(path, identity)
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def save_parquet(path, identity, frame, extra=None):
    frame.to_parquet(path, index=False)
    _seal(path, identity, extra)


def load_parquet(path, identity):
    check(path, identity)
    return pd.read_parquet(path)


def save_json(path, identity, value, extra=None):
    write_json(path, value)
    _seal(path, identity, extra)


def load_json(path, identity):
    check(path, identity)
    return read_json(path)


def save_bytes(path, identity, data, extra=None):
    Path(path).write_bytes(data)
    _seal(path, identity, extra)


def load_bytes(path, identity):
    check(path, identity)
    return Path(path).read_bytes()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]
