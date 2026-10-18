"""Pure hangmap_v01 logic (no IO): cell grid, comparison-group draw, shares, input validation."""
import hashlib
import math

import numpy as np
import pandas as pd

from ..v04.models import group_softmax


def aspect_features(aspect_deg):
    """Aspect enters the model as sine/cosine, hence circular (359 deg and 1 deg are 2 deg apart)."""
    a = np.deg2rad(np.asarray(aspect_deg, float))
    return np.sin(a), np.cos(a)


def validate_request(radius_m, points, cfg):
    a = cfg['area']
    lo, hi = a['radius_m']['min'], a['radius_m']['max']
    if not lo <= radius_m <= hi:
        raise ValueError(f'radius_m must be within [{lo}, {hi}]')
    if points is not None:
        c = a['custom_points']
        if not c['min'] <= len(points) <= c['max']:
            raise ValueError(f"custom points: {c['min']} to {c['max']} required, got {len(points)}")
        if len({(round(lon, 6), round(lat, 6)) for lon, lat in points}) != len(points):
            raise ValueError('custom points contain duplicates')


def dem_cell_xy(left, top, res_m, rows, cols):
    """Centres (EPSG:31287 metres) of DEM cells; inverse of the floor lookup used by the feature code."""
    return left + (np.asarray(cols) + .5) * res_m, top - (np.asarray(rows) + .5) * res_m


def grid_cells(cx, cy, radius_m, left, top, res_m, cell_m, shape):
    """DEM cells on a cell_m grid anchored at the centre cell, inside the circle (projected metres)."""
    step = int(round(cell_m / res_m))
    if step < 1 or abs(step * res_m - cell_m) > 1e-9:
        raise ValueError('cell_m must be a multiple of the DEM resolution')
    r0, c0 = int(math.floor((top - cy) / res_m)), int(math.floor((cx - left) / res_m))
    span = int(radius_m // res_m) + 1
    rows, cols = np.meshgrid(np.arange(r0 - span // step * step, r0 + span + 1, step),
                             np.arange(c0 - span // step * step, c0 + span + 1, step), indexing='ij')
    rows, cols = rows.ravel(), cols.ravel()
    ok = (rows >= 0) & (cols >= 0) & (rows < shape[0]) & (cols < shape[1])
    rows, cols = rows[ok], cols[ok]
    x, y = dem_cell_xy(left, top, res_m, rows, cols)
    inside = np.hypot(x - cx, y - cy) <= radius_m
    return rows[inside], cols[inside], x[inside], y[inside]


def group_seed(lon, lat, radius_m):
    return int(hashlib.sha256(f'{lon:.5f}|{lat:.5f}|{radius_m}|hangmap_v01'.encode()).hexdigest()[:16], 16)


def select_group(cell_ids, x, y, size, separation_m, seed):
    """Registered draw: permutation of sorted ids, accept cells >= separation_m from all accepted ones."""
    order = np.argsort(cell_ids, kind='stable')
    ids, x, y = np.asarray(cell_ids)[order], np.asarray(x, float)[order], np.asarray(y, float)[order]
    perm = np.random.Generator(np.random.PCG64(seed)).permutation(len(ids))
    chosen = []
    for i in perm:
        if all(math.hypot(x[i] - x[j], y[i] - y[j]) >= separation_m for j in chosen):
            chosen.append(i)
            if len(chosen) == size:
                break
    return ids[chosen]


def shares(score, groups):
    """Softmax of the linear score inside each group: shares sum to 1 per group."""
    return group_softmax(np.asarray(score, float), np.asarray(groups))


def area_index(share, n):
    """1.0 = area average; rank percentile 0..100 (higher = higher share)."""
    share = np.asarray(share, float)
    return share * n, pd.Series(share).rank(method='average', pct=True).to_numpy() * 100
