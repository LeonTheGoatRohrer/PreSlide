"""V0.5 unmatched controls: audit of the existing V0.4 pools and the registered random draw (config/v05.json: controls).

Selection never looks at matching columns (passes_calipers, matching_score, *_difference_*); only the registered
eligibility filters, the event-specific seed and the 400 m separation decide.
"""
import hashlib

import numpy as np
import pandas as pd
from numpy.random import Generator, PCG64
from shapely import contains_xy

from ..common import digest
from ..terrain import PROJECT
from .paths import V04_POOLS, sha

POOL_COLUMNS = ['x', 'y', 'longitude', 'latitude', 'distance_to_positive_m', 'elevation', 'slope', 'aspect',
                'slope_difference_deg', 'elevation_difference_m', 'aspect_difference_deg', 'inventory_clear',
                'inside_austria', 'matching_score', 'passes_calipers']
SELECTION_COLUMNS = ['pool_id', 'x', 'y', 'longitude', 'latitude', 'distance_to_positive_m', 'elevation', 'slope',
                     'aspect', 'inventory_clear', 'inside_austria']


def event_seed(event_id, tag='v05'):
    return int(hashlib.sha256(f'{event_id}|{tag}'.encode('utf-8')).hexdigest()[:16], 16)


def pilot_order(event_ids):
    """Deterministic pilot order from event IDs only (never from model results)."""
    return sorted(event_ids, key=lambda e: hashlib.sha256(f'{e}|v05-pilot'.encode('utf-8')).hexdigest())


def regenerate_pool_xy(event_id, px, py, m):
    """The V0.4 pool construction (preslide.v04.terrain.match_event): area-uniform ring around the positive."""
    rng = np.random.default_rng(int(digest([event_id, m['random_seed']])[:8], 16))
    n = m['candidate_pool_size']
    distance = np.sqrt(rng.uniform(m['control_min_distance_m'] ** 2, m['control_max_distance_m'] ** 2, n))
    angle = rng.uniform(0, 2 * np.pi, n)
    return np.column_stack([px + distance * np.cos(angle), py + distance * np.sin(angle)]), distance


def inventory_allowed(exclusions, xy):
    """Vectorised equivalent of preslide.matching.Exclusions.allowed (strictly farther than every radius)."""
    lists = exclusions.tree.query_ball_point(xy, float(exclusions.radii.max()))
    lengths = np.array([len(x) for x in lists])
    if lengths.sum() == 0:
        return np.ones(len(xy), bool)
    point = np.repeat(np.arange(len(xy)), lengths)
    other = np.concatenate([np.asarray(x, int) for x in lists if len(x)])
    d = np.linalg.norm(xy[point] - exclusions.xy[other], axis=1)
    blocked = np.zeros(len(xy), bool)
    np.logical_or.at(blocked, point[d <= exclusions.radii[other]], True)
    return ~blocked


def load_pool(event_id):
    path = V04_POOLS / f'{event_id}.parquet'
    pool = pd.read_parquet(path)
    return pool.reset_index(drop=True).assign(pool_id=np.arange(len(pool))), sha(path)


def audit_pool(event_id, px, py, m, exclusions, country):
    """Schema/CRS/row checks, exact regeneration of the ring points, and recomputation of the stored flags."""
    pool, digest_ = load_pool(event_id)
    problems = []
    if list(pool.columns[:-1]) != POOL_COLUMNS:
        problems.append('columns')
    if len(pool) != m['candidate_pool_size']:
        problems.append('rows')
    xy, distance = regenerate_pool_xy(event_id, px, py, m)
    if not np.allclose(pool[['x', 'y']].to_numpy(), xy, rtol=0, atol=1e-6):
        problems.append('xy_not_regenerated')
    if not np.allclose(pool.distance_to_positive_m, distance, rtol=0, atol=1e-6):
        problems.append('distance_not_regenerated')
    if (pool.distance_to_positive_m < m['control_min_distance_m']).any() or (pool.distance_to_positive_m > m['control_max_distance_m']).any():
        problems.append('ring')
    lx, ly = PROJECT.transform(pool.longitude.to_numpy(), pool.latitude.to_numpy())
    crs_error = float(np.max(np.hypot(lx - pool.x, ly - pool.y)))
    if crs_error > 1.0:          # pyproj forward/inverse round trip differs by < 1 m (30 m raster cells)
        problems.append('lonlat_xy_inconsistent')
    clear = inventory_allowed(exclusions, pool[['x', 'y']].to_numpy())
    inside = contains_xy(country, pool.longitude.to_numpy(), pool.latitude.to_numpy())
    flag_mismatch = {'inventory_clear': int((clear != pool.inventory_clear.to_numpy()).sum()),
                     'inside_austria': int((inside != pool.inside_austria.to_numpy()).sum())}
    return {'event_id': event_id, 'sha256': digest_, 'rows': int(len(pool)), 'problems': problems,
            'max_lonlat_xy_error_m': crs_error, 'flag_mismatch': flag_mismatch}


def eligible(pool, c):
    finite = np.isfinite(pool[['elevation', 'slope', 'aspect']]).all(axis=1)
    return (pool.inside_austria.astype(bool) & pool.inventory_clear.astype(bool) & finite &
            (pool.elevation >= 0) & (pool.elevation <= 4500) & (pool.slope >= 5))


def select_controls(event_id, pool, c):
    """Registered draw: one PCG64 permutation of the eligible pool_ids, greedy 400 m separation, stop at k.

    Returns (selected rows in draw order, record). Raises ValueError if fewer than k controls are selectable."""
    pool = pool[SELECTION_COLUMNS].sort_values('pool_id').reset_index(drop=True)
    ok = pool[eligible(pool, c).to_numpy()]
    seed = event_seed(event_id)
    order = Generator(PCG64(seed)).permutation(ok.pool_id.to_numpy())
    xy = pool.set_index('pool_id')[['x', 'y']]
    chosen, walked = [], 0
    for pid in order:
        walked += 1
        p = xy.loc[pid].to_numpy()
        if all(np.hypot(*(p - xy.loc[q].to_numpy())) >= c['separation_m'] for q in chosen):
            chosen.append(int(pid))
        if len(chosen) == c['per_event']:
            break
    record = {'event_id': event_id, 'seed': seed, 'eligible': int(len(ok)), 'walked': walked, 'selected_pool_ids': chosen,
              'numpy': np.__version__}
    if len(chosen) < c['per_event']:
        raise ValueError(f"insufficient_unmatched_controls:{len(chosen)}_from_{len(ok)}_eligible")
    rows = pool.set_index('pool_id').loc[chosen].reset_index()
    rows['draw_order'] = np.arange(1, len(chosen) + 1)
    return rows, record
