"""Positives, areas, sampling regions and background points (config sections positives, areas, background).

All distances are EPSG:31287 metres (preslide.terrain.PROJECT). Nothing here reads a model, a score or a label of
another area; background acceptance uses only the registered geometry, DEM slope/elevation and inventory buffer.
"""
import re
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import contains_xy

from ..common import read_json, digest
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE
from . import terrain

INVENTORY = ROOT / 'data/raw/geosphere_natural_hazards.json'
LATTICE_M = 5000
TILE_M = 50000


class SpatialIndex:
    """Bucket grid for 'is any stored point within r metres?' queries (exact Euclidean test inside buckets)."""

    def __init__(self, r_m: float):
        self.r = float(r_m)
        self.buckets = defaultdict(list)

    def _key(self, x, y):
        return int(np.floor(x / self.r)), int(np.floor(y / self.r))

    def near(self, x, y) -> bool:
        kx, ky = self._key(x, y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for px, py in self.buckets.get((kx + dx, ky + dy), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < self.r ** 2:
                        return True
        return False

    def add(self, x, y):
        self.buckets[self._key(x, y)].append((x, y))


def project_xy(lon, lat):
    x, y = PROJECT.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.asarray(x), np.asarray(y)


def load_records(path=INVENTORY) -> pd.DataFrame:
    """Every inventory record with a point geometry (all processes), with EPSG:31287 coordinates."""
    rows = []
    for f in read_json(path)['features']:
        g = f.get('geometry')
        if not g or g.get('x') is None or g.get('y') is None:
            continue
        a = f['attributes']
        rows.append({'object_id': int(a['OBJECTID']), 'lon': float(g['x']), 'lat': float(g['y']),
                     'subgroup': (a.get('Prozessuntergruppe') or '').strip(), 'position_class': a.get('QUAL_LAGE'),
                     'project': (a.get('RegKatE_ID') or '').strip() or None, 'year_field': a.get('EREIGNIS_J'),
                     'qual_mb': a.get('QUAL_MB'), 'qual_proz': a.get('QUAL_PROZ'), 'method': (a.get('ERHEB_MET_agg') or '').strip(),
                     'state': a.get('Bundesland')})
    out = pd.DataFrame(rows)
    out['x'], out['y'] = project_xy(out.lon, out.lat)
    return out


def event_year(year_field, project):
    """EREIGNIS_J if present, else the single four-digit year in RegKatE_ID, else None."""
    if year_field is not None and not (isinstance(year_field, float) and np.isnan(year_field)):
        return int(year_field)
    if isinstance(project, str) and project:
        years = re.findall(r'(?<!\d)(\d{4})(?!\d)', project)
        if len(years) == 1:
            return int(years[0])
    return None


def area_of(project, x_m, y_m) -> str:
    if isinstance(project, str) and project:
        return project
    return f'tile_{int(np.floor(x_m / TILE_M))}_{int(np.floor(y_m / TILE_M))}'


def deduplicate(frame: pd.DataFrame, min_distance_m: float, fine_class: str) -> np.ndarray:
    """Greedy thinning in the registered priority order; returns a keep mask aligned with `frame`."""
    order = frame.assign(_p=frame.project.notna(), _y=frame.year.notna(), _f=frame.position_class == fine_class) \
        .sort_values(['_p', '_y', '_f', 'object_id'], ascending=[False, False, False, True]).index
    index, keep = SpatialIndex(min_distance_m), pd.Series(False, index=frame.index)
    for i in order:
        x, y = frame.at[i, 'x'], frame.at[i, 'y']
        if not index.near(x, y):
            index.add(x, y)
            keep[i] = True
    return keep.to_numpy()


def candidates(cfg: dict, records: pd.DataFrame, country) -> tuple[pd.DataFrame, dict]:
    """Registered positive candidates before any terrain value (process, position class, Austria, dedup)."""
    pos = cfg['positives']
    counts = {'records_with_geometry': int(len(records))}
    target = pos['process_subgroup'].split("'")[1]
    hm = records[records.subgroup == target].copy()
    counts['subgroup_hangmure'] = int(len(hm))
    counts['subgroups_not_used'] = {k: int(v) for k, v in records[records.subgroup.str.startswith('Hangmure') &
                                                                (records.subgroup != target)].subgroup.value_counts().items()}
    hm = hm[hm.position_class.isin(pos['position_classes'])].copy()
    counts['precise_position'] = int(len(hm))
    inside = contains_xy(country, hm.lon.to_numpy(), hm.lat.to_numpy())
    counts['outside_austria'] = int((~inside).sum())
    hm = hm[inside].copy()
    hm['year'] = [event_year(y, p) for y, p in zip(hm.year_field, hm.project)]
    hm['year'] = hm.year.astype('Int64')
    keep = deduplicate(hm, pos['deduplication_m'], pos['position_classes'][0])
    counts['duplicates_merged'] = int((~keep).sum())
    hm = hm[keep].copy()
    hm['area_id'] = [area_of(p, x, y) for p, x, y in zip(hm.project, hm.x, hm.y)]
    hm['sample_id'] = 'P' + hm.object_id.astype(str)
    counts['candidates'] = int(len(hm))
    counts['qual_mb'] = {str(k): int(v) for k, v in hm.qual_mb.value_counts(dropna=False).items()}
    counts['qual_proz'] = {str(k): int(v) for k, v in hm.qual_proz.value_counts(dropna=False).items()}
    counts['method_top'] = {str(k): int(v) for k, v in hm.method.value_counts().head(8).items()}
    return hm.reset_index(drop=True), counts


def year_eligible(years: pd.Series, variant: str) -> np.ndarray:
    """DEM provenance rule: SRTM (Feb 2000) only for events with a known year >= 2001; Skadi sensitivity uses all."""
    if variant == 'srtm':
        return (years.notna() & (years.fillna(0) >= 2001)).to_numpy(bool)
    if variant == 'skadi':
        return np.ones(len(years), bool)
    raise ValueError(variant)


def terrain_ok(t: pd.DataFrame, cfg: dict) -> pd.Series:
    lo, hi = cfg['background']['elevation_range_m']
    return t.elevation.notna() & t.elevation.between(lo, hi) & (t.slope >= cfg['background']['minimum_slope_deg'])


def lattice_cells(x_m, y_m) -> list:
    return sorted(set(zip(np.floor(np.asarray(x_m) / LATTICE_M).astype(int).tolist(),
                          np.floor(np.asarray(y_m) / LATTICE_M).astype(int).tolist())))


def cell_blocks(cells) -> list:
    """Terrain blocks overlapping the given 5 km lattice cells."""
    blocks = set()
    for cx, cy in cells:
        xs = np.array([cx * LATTICE_M, (cx + 1) * LATTICE_M - 1e-6])
        ys = np.array([cy * LATTICE_M, (cy + 1) * LATTICE_M - 1e-6])
        bx, by = terrain.block_of(xs, ys)
        for i in range(bx.min(), bx.max() + 1):
            for j in range(by.min(), by.max() + 1):
                blocks.add((int(i), int(j)))
    return sorted(blocks)


class InventoryBuffer:
    """Rejects points within `radius_m` of any inventory record (all processes and position classes)."""

    def __init__(self, records: pd.DataFrame, radius_m: float):
        self.tree, self.r = cKDTree(records[['x', 'y']].to_numpy(float)), float(radius_m)

    def clear(self, xy: np.ndarray) -> np.ndarray:
        d, _ = self.tree.query(xy, k=1)
        return d > self.r


def draw_background(area_id: str, cells: list, n_needed: int, variant: str, cfg: dict, buffer: InventoryBuffer,
                    country, sampler=None) -> tuple[pd.DataFrame, dict]:
    """Uniform points in the area's lattice cells, accepted in stream order (registered rule)."""
    bg = cfg['background']
    sampler = sampler or (lambda x, y: terrain.sample(variant, x, y))
    rng = np.random.default_rng(int(digest([area_id, bg['seed']])[:8], 16))
    cells = np.array(cells, dtype=float)
    limit = bg['max_candidates_per_needed_point'] * n_needed
    sep = SpatialIndex(bg['minimum_separation_m'])
    rows, drawn = [], 0
    reasons = {'outside_austria': 0, 'inventory_buffer': 0, 'terrain': 0, 'separation': 0}
    while len(rows) < n_needed and drawn < limit:
        k = min(2000, limit - drawn)
        pick = rng.integers(len(cells), size=k)
        x = (cells[pick, 0] + rng.uniform(0, 1, k)) * LATTICE_M
        y = (cells[pick, 1] + rng.uniform(0, 1, k)) * LATTICE_M
        drawn += k
        lon, lat = INVERSE.transform(x, y)
        ok_country = contains_xy(country, lon, lat)
        ok_buffer = buffer.clear(np.column_stack([x, y]))
        t = pd.DataFrame(np.nan, index=range(k), columns=terrain.TERRAIN)
        test = np.flatnonzero(ok_country & ok_buffer)
        if len(test):
            t.iloc[test] = sampler(x[test], y[test]).to_numpy()
        ok_terrain = terrain_ok(t, cfg).to_numpy()
        for i in range(k):
            if not ok_country[i]:
                reasons['outside_austria'] += 1
            elif not ok_buffer[i]:
                reasons['inventory_buffer'] += 1
            elif not ok_terrain[i]:
                reasons['terrain'] += 1
            elif sep.near(x[i], y[i]):
                reasons['separation'] += 1
            else:
                sep.add(x[i], y[i])
                rows.append({'x': x[i], 'y': y[i], 'lon': lon[i], 'lat': lat[i], **t.iloc[i].to_dict()})
                if len(rows) == n_needed:
                    break
    examined = sum(reasons.values()) + len(rows)
    out = pd.DataFrame(rows)
    if len(out):
        out.insert(0, 'sample_id', [f'B_{area_id}_{i:05d}' for i in range(len(out))])
    return out, {'needed': n_needed, 'accepted': len(out), 'candidates_examined': examined, 'rejected': reasons}
