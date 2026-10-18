"""Exact distance of every V0.5 sample to the nearest OSM building vertex and public-road vertex (config/v07b.json).

  python -m preslide.v07b.infrastructure distances [--limit N]

The unchanged V0.7 stream (preslide.v07.infrastructure.extract: way filter, road classes, 25 m densification, cap)
runs once with its accumulator replaced by `Paired`, which feeds every vertex chunk to
  * NearestVertex  - exact: each chunk gets its own KD-tree and every sample queries it,
  * the V0.7 RunningMinimum - must reproduce data/v07/infrastructure.parquet exactly,
  * a brute-force full distance matrix for a few check samples (no tree, no cap).
NearestVertex is the same algorithm as preslide/anfaelligkeit_at_v01/infrastructure.py (branch claude/anfaelligkeit-at-v01,
not merged into main when this was written); when both are on main, keep one of them.
"""
import argparse
import contextlib
import json

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..common import write_json
from ..sources import ROOT
from ..v05.paths import sha
from ..v07 import infrastructure as V07I
from ..v07.paths import V05_DATASET, config as load_v07_config
from .paths import V07B_DATA, config as load_config, guard

CHECK_SAMPLES = 20
CHECK_SEED = 20261018
CHUNK = 400_000            # same buffer size as the V0.7 accumulator
V07_RUNNING_MINIMUM = V07I.RunningMinimum   # captured before any rebinding


class NearestVertex:
    """Exact minimum distance from every sample to all vertices added so far, capped at cap_m."""

    def __init__(self, sample_xy: np.ndarray, cap_m: float, chunk: int = CHUNK):
        self.samples, self.cap, self.chunk = np.asarray(sample_xy, float), float(cap_m), chunk
        self.best = np.full(len(self.samples), np.inf)
        self.buffer: list[np.ndarray] = []
        self.size = 0

    def add(self, xy: np.ndarray) -> None:
        self.buffer.append(xy)
        self.size += len(xy)
        if self.size > self.chunk:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        tree = cKDTree(np.vstack(self.buffer))
        self.buffer, self.size = [], 0
        d, _ = tree.query(self.samples, k=1, distance_upper_bound=self.cap)
        self.best = np.minimum(self.best, d)

    def result(self) -> tuple[np.ndarray, np.ndarray]:
        self.flush()
        capped = ~np.isfinite(self.best)
        return np.where(capped, self.cap, self.best), capped


class BruteForce:
    """Uncapped nearest distance for a few samples from the full distance matrix (reference for the exact accumulator)."""

    def __init__(self, sample_xy: np.ndarray, chunk: int = CHUNK):
        self.samples, self.chunk = np.asarray(sample_xy, float), chunk
        self.best = np.full(len(self.samples), np.inf)
        self.buffer: list[np.ndarray] = []
        self.size = 0

    def add(self, xy: np.ndarray) -> None:
        self.buffer.append(xy)
        self.size += len(xy)
        if self.size > self.chunk:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        pts = np.vstack(self.buffer)
        self.buffer, self.size = [], 0
        for i, s in enumerate(self.samples):
            self.best[i] = min(self.best[i], float(np.sqrt(((pts - s) ** 2).sum(axis=1)).min()))

    def result(self) -> np.ndarray:
        self.flush()
        return self.best


def paired_factory(check_idx: np.ndarray):
    class Paired:
        """Drop-in for V0.7 RunningMinimum inside V0.7 extract(); result() returns (exact, v07, brute_force)."""

        def __init__(self, sample_xy: np.ndarray, cap_m: float):
            self.exact = NearestVertex(sample_xy, cap_m)
            self.v07 = V07_RUNNING_MINIMUM(sample_xy, cap_m)
            self.brute = BruteForce(np.asarray(sample_xy, float)[check_idx])

        def add(self, xy: np.ndarray) -> None:
            self.exact.add(xy)
            self.v07.add(xy)
            self.brute.add(xy)

        def result(self):
            return self.exact.result(), self.v07.result(), self.brute.result()
    return Paired


@contextlib.contextmanager
def v07_stream_with(accumulator):
    """Run V0.7 extract() with its accumulator class replaced; the V0.7 class is restored afterwards."""
    original = V07I.RunningMinimum
    V07I.RunningMinimum = accumulator
    try:
        yield
    finally:
        V07I.RunningMinimum = original


def table(sample_id, road, bld) -> pd.DataFrame:
    """V0.7 table schema: distances (m, capped), cap flags and dist_infrastructure_m = min(road, building)."""
    (road_d, road_c), (bld_d, bld_c) = road, bld
    out = pd.DataFrame({'sample_id': sample_id, 'dist_road_m': road_d, 'dist_building_m': bld_d,
                        'road_capped': road_c, 'building_capped': bld_c})
    out['dist_infrastructure_m'] = out[['dist_road_m', 'dist_building_m']].min(axis=1)
    return out


def stage_distances(limit: int = 0) -> pd.DataFrame:
    cfg, v07cfg = load_config(), load_v07_config()
    data = pd.read_parquet(V05_DATASET)
    sample_xy = data[['x', 'y']].to_numpy(float)
    check_idx = np.sort(np.random.default_rng(CHECK_SEED).choice(len(data), CHECK_SAMPLES, replace=False))
    with v07_stream_with(paired_factory(check_idx)):
        (road, road_v07, road_bf), (bld, bld_v07, bld_bf), counts = V07I.extract(sample_xy, v07cfg, limit_ways=limit)
    exact, v07 = table(data.sample_id, road, bld), table(data.sample_id, road_v07, bld_v07)
    cap = v07cfg['infrastructure']['distance_cap_m']
    check = {'sample_index': check_idx.tolist(), 'sample_id': data.sample_id.iloc[check_idx].tolist()}
    for name, bf, col in (('road', road_bf, 'dist_road_m'), ('building', bld_bf, 'dist_building_m')):
        ref = np.minimum(bf, cap)
        check[f'{name}_max_abs_difference_m'] = float(np.abs(exact[col].to_numpy()[check_idx] - ref).max())
    check['brute_force_ok'] = max(check['road_max_abs_difference_m'], check['building_max_abs_difference_m']) <= 0.01
    out_dir = guard(V07B_DATA)
    suffix = '' if not limit else f'_pilot_{limit}'
    meta = {'rows': len(exact), 'config_sha256': sha(ROOT / 'config/v07b.json'), 'v07_config_sha256': sha(ROOT / 'config/v07.json'),
            'dataset_sha256': cfg['inputs']['dataset_sha256'], 'limit_ways': limit, **counts}
    for name, frame in ((f'infrastructure{suffix}', exact), (f'infrastructure_v07_accumulator{suffix}', v07)):
        path = out_dir / f'{name}.parquet'
        frame.to_parquet(path, index=False)
        write_json(path.with_suffix('.json'), {'sha256': sha(path), **meta})
    if not limit:
        old = pd.read_parquet(ROOT / cfg['inputs']['v07_infrastructure'])
        cols = ['dist_road_m', 'dist_building_m', 'road_capped', 'building_capped', 'dist_infrastructure_m']
        check['v07_reproduced_exactly'] = bool(old.sample_id.equals(v07.sample_id) and all((old[c].to_numpy() == v07[c].to_numpy()).all() for c in cols))
    write_json(out_dir / f'distance_checks{suffix}.json', check)
    print(json.dumps(counts), json.dumps(check), exact.describe().round(1).to_string(), flush=True)
    if not check['brute_force_ok'] or check.get('v07_reproduced_exactly') is False:
        raise RuntimeError('distance checks failed; see distance_checks.json')
    return exact


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['distances'])
    ap.add_argument('--limit', type=int, default=0, help='stop after N ways (code check only)')
    a = ap.parse_args()
    stage_distances(a.limit)
