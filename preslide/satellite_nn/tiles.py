"""Overlapping tile grid, validity gating and seam-free mosaicking (pure numpy)."""
from __future__ import annotations
import numpy as np
from scipy import ndimage

BAD_SCL = (0, 1, 3, 8, 9, 10, 11)  # nodata, saturated, shadow, cloud medium/high, cirrus, snow


def tile_origins(height_px: int, width_px: int, size_px: int = 128, stride_px: int = 64) -> list[tuple[int, int]]:
    """Top-left (row, col) of every tile; the last row/column is shifted so the raster edge is always covered."""
    if height_px < size_px or width_px < size_px:
        raise ValueError('raster smaller than one tile')

    def axis(n: int) -> list[int]:
        o = list(range(0, n - size_px + 1, stride_px))
        if o[-1] != n - size_px:
            o.append(n - size_px)
        return o

    return [(r, c) for r in axis(height_px) for c in axis(width_px)]


def invalid_mask(scl: np.ndarray, buffer_m: float = 100, pixel_m: float = 10) -> np.ndarray:
    """True = unusable incl. cloud/snow buffer. SCL is quality control only, never a model input."""
    bad = np.isin(scl, BAD_SCL)
    n = int(round(buffer_m / pixel_m))
    return ndimage.binary_dilation(bad, iterations=n) if n and bad.any() else bad


def assessable(invalid: np.ndarray, min_valid_fraction: float = 0.9) -> bool:
    return float(1.0 - invalid.mean()) >= min_valid_fraction


def mosaic(shape: tuple[int, int], origins: list[tuple[int, int]], probs: list[np.ndarray], size_px: int = 128) -> np.ndarray:
    """Edge-down-weighted overlap average so a scar at a tile border is not cut."""
    w1 = np.hanning(size_px + 2)[1:-1]
    w = np.outer(w1, w1).astype('float64')
    acc = np.zeros(shape); wsum = np.zeros(shape)
    for (r, c), p in zip(origins, probs):
        acc[r:r + size_px, c:c + size_px] += p * w
        wsum[r:r + size_px, c:c + size_px] += w
    if (wsum == 0).any():
        raise ValueError('mosaic leaves uncovered pixels')
    return acc / wsum


def objects(prob: np.ndarray, threshold: float, min_px: int = 4, invalid: np.ndarray | None = None):
    """Connected components after mosaicking: one scar = one object. Returns (label raster, kept ids)."""
    mask = prob >= threshold
    if invalid is not None:
        mask &= ~invalid
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    return lab, [i + 1 for i, s in enumerate(sizes) if s >= min_px]
