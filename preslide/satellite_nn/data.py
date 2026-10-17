"""Landslide4Sense adapter: 14-band h5 tiles -> RGB (B4,B3,B2) + binary mask. Source audit only; no modelling."""
from __future__ import annotations
import hashlib
from pathlib import Path
import h5py
import numpy as np
from . import paths

RGB_IDX = (3, 2, 1)  # B4, B3, B2 in the 14-channel layout (B1..B12 incl. B8A order, slope, DEM)
N_BANDS = 14
TRAIN_DIR = paths.DATA / 'extracted' / 'TrainData'


def read_pair(i: int, root: Path = TRAIN_DIR) -> tuple[np.ndarray, np.ndarray]:
    """RGB float32 (H, W, 3) in source units and mask uint8 (H, W). Fails loudly on schema deviations."""
    with h5py.File(root / 'img' / f'image_{i}.h5') as f:
        img = f['img'][:]
    with h5py.File(root / 'mask' / f'mask_{i}.h5') as f:
        mask = f['mask'][:]
    if img.shape != (128, 128, N_BANDS) or mask.shape != (128, 128):
        raise ValueError(f'pair {i}: unexpected shapes {img.shape} {mask.shape}')
    if not np.isfinite(img).all():
        raise ValueError(f'pair {i}: non-finite pixels')
    if not set(np.unique(mask)) <= {0, 1}:
        raise ValueError(f'pair {i}: unexpected mask classes {np.unique(mask)}')
    return img[..., list(RGB_IDX)].astype('float32'), mask.astype('uint8')


def pair_hash(rgb: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(rgb).tobytes()).hexdigest()[:16]


def audit(ids: list[int], root: Path = TRAIN_DIR) -> dict:
    rows, hashes = [], {}
    for i in ids:
        rgb, m = read_pair(i, root)
        h = pair_hash(rgb)
        hashes.setdefault(h, []).append(i)
        rows.append({'id': i, 'landslide_fraction': float(m.mean()), 'rgb_min': float(rgb.min()), 'rgb_max': float(rgb.max()),
                     'rgb_mean': [float(x) for x in rgb.mean((0, 1))]})
    fr = np.array([r['landslide_fraction'] for r in rows])
    return {'n': len(ids), 'ids': ids, 'with_landslide': int((fr > 0).sum()), 'mean_fraction': float(fr.mean()),
            'duplicate_groups': {h: v for h, v in hashes.items() if len(v) > 1}, 'rows': rows}
