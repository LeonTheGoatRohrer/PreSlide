"""Freeze split + design before the first domain training. Training refuses to run without a matching registration."""
from __future__ import annotations
import numpy as np
import torch
from ..common import digest, read_json, write_json
from . import paths

PREREG = paths.REPORTS / 'PREREGISTRATION.json'
N_TILES = 3799


def make_split(seed: int, dev_fraction: float = 0.2) -> dict:
    """Random tile split. Source has no coordinates -> tiles of one scene may straddle the split: dev numbers are optimistic."""
    perm = np.random.default_rng(seed).permutation(np.arange(1, N_TILES + 1))
    n_dev = int(round(N_TILES * dev_fraction))
    return {'dev': sorted(int(i) for i in perm[:n_dev]), 'train': sorted(int(i) for i in perm[n_dev:])}


def register() -> dict:
    if PREREG.exists():
        raise SystemExit('already registered; changes need a dated amendment, not an overwrite')
    cfg = read_json(paths.CONFIG)
    if cfg['status'] != 'REGISTERED':
        raise SystemExit("set config status to 'REGISTERED' first (it is part of the hashed identity)")
    split = make_split(cfg['seeds']['model_a'])
    write_json(paths.assert_writable(paths.DATA / 'split.json'), split)
    rec = {'version': cfg['version'], 'registered_utc': np.datetime64('now').astype(str) + 'Z',
           'config_sha256': digest(cfg), 'split_sha256': digest(split), 'n_train': len(split['train']), 'n_dev': len(split['dev']),
           'scope': 'Pretraining on Landslide4Sense RGB. Dev split is tile-random (no footprints available): NOT spatially independent, '
                    'no generalisation claim. No test split exists. Austrian evaluation requires separate labelled data.',
           'checkpoint_selection': 'best dev object-F1 (IoU>=0.30 1:1 matching, threshold 0.5, min 4 px)',
           'normalisation': 'per-channel mean/std from the train tiles only', 'init': 'ImageNet resnet18 encoder (torchvision IMAGENET1K_V1)',
           'torch': torch.__version__, 'n_comparisons': 'model A only; B and updates are separate registered runs'}
    write_json(paths.assert_writable(PREREG), rec)
    return rec


def verify() -> dict:
    """Raise if config or split changed since registration."""
    rec = read_json(PREREG)
    split = read_json(paths.DATA / 'split.json')
    if digest(read_json(paths.CONFIG)) != rec['config_sha256'] or digest(split) != rec['split_sha256']:
        raise RuntimeError('config or split differs from the registration')
    return split
