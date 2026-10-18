"""Phase 3: positive cells and area-uniform background cells inside mapping extents (rules: config 'sampling').

  python -m preslide.susceptibility.sampling run gorkha_2015|far_western_nepal --limit 1|5|20|0(all)

Writes data/susceptibility_v01/samples/<dataset>.parquet with a SHA-256 sidecar (full runs only) and
reports/susceptibility_v01/phase3_sampling_<dataset>.json with exclusion counts by reason.
"""
import argparse
import collections
import json
import math
import re

import numpy as np
import pandas as pd
import rasterio
import shapely
from scipy.spatial import cKDTree

from ..common import write_json
from ..v04.pipeline import load, save
from .inventory import RAW, read_layer
from .paths import DATA, REPORT, config, guard
from .terrain import block_grid, block_path, extent, load_block

SAMPLES = DATA / 'samples'
LAYERS = {
    'gorkha_2015': {'positive': 'Source20170209.shp', 'known': ['Full20170209.shp', 'Source20170209.shp'],
                    'obscured': 'ObscuredAreas20170209.shp'},
    'far_western_nepal': {'positive': 'LandslideInventory_FarWesternNepal_Pol.shp',
                          'known': ['LandslideInventory_FarWesternNepal_Pol.shp'], 'obscured': None,
                          'dated': 'LandslideInventory_FarWesternNepal_Points_Dated1992_2018.shp'},
}


def layer(dataset, name):
    return read_layer(next((RAW / dataset / 'extracted').rglob(name)))


def valid_geoms(geoms):
    return [None if g is None or g.is_empty else (g if g.is_valid else shapely.make_valid(g)) for g in geoms]


def cell_centre(v, cell):
    return (np.floor(np.asarray(v) / cell) + 0.5) * cell


def cells_in(poly, cell):
    """Centres of grid cells whose centre lies inside the polygon."""
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(math.floor(x0 / cell), math.ceil(x1 / cell)) * cell + cell / 2
    ys = np.arange(math.floor(y0 / cell), math.ceil(y1 / cell)) * cell + cell / 2
    gx, gy = np.meshgrid(xs, ys)
    gx, gy = gx.ravel(), gy.ravel()
    inside = shapely.contains_xy(poly, gx, gy)
    return gx[inside], gy[inside]


def choose_positive(poly, cell, rng, elevation_at=None):
    """One cell per polygon: uniform among inside cells (top elevation third if elevation_at is given);
    a polygon smaller than a cell gives the cell containing its representative point."""
    xs, ys = cells_in(poly, cell)
    if len(xs) == 0:
        p = poly.representative_point()
        return float(cell_centre(p.x, cell)), float(cell_centre(p.y, cell)), 'containing_cell'
    if elevation_at is not None:
        z = elevation_at(xs, ys)
        ok = np.isfinite(z)
        if not ok.any():
            return None, None, 'no_elevation'
        xs, ys, z = xs[ok], ys[ok], z[ok]
        top = z >= np.quantile(z, 2 / 3)
        xs, ys = xs[top], ys[top]
    k = rng.integers(len(xs))
    return float(xs[k]), float(ys[k]), 'inside_cell'


def too_close(x, y, tree, recent_x, recent_y, min_sep_m):
    """True if (x, y) is closer than min_sep_m to an indexed (tree) or recently kept point."""
    if tree is not None and tree.query_ball_point((x, y), min_sep_m - 1e-6):
        return True
    return any((x - a) ** 2 + (y - b) ** 2 < min_sep_m ** 2 for a, b in zip(recent_x, recent_y))


def draw_background(allowed, n, cell, min_sep_m, rng, accept=None, batch=20000, max_draws=10_000_000):
    """Area-uniform cells inside `allowed`, pairwise >= min_sep_m apart (greedy in draw order)."""
    x0, y0, x1, y1 = allowed.bounds
    shapely.prepare(allowed)
    kept_x, kept_y, drawn = [], [], 0
    tree_pts = np.empty((0, 2))
    while len(kept_x) < n:
        if drawn >= max_draws:
            raise RuntimeError(f'only {len(kept_x)} of {n} background cells after {drawn} draws')
        x = cell_centre(rng.uniform(x0, x1, batch), cell)
        y = cell_centre(rng.uniform(y0, y1, batch), cell)
        drawn += batch
        inside = shapely.contains_xy(allowed, x, y)
        x, y = x[inside], y[inside]
        if accept is not None and len(x):
            ok = accept(x, y)
            x, y = x[ok], y[ok]
        tree = cKDTree(tree_pts) if len(tree_pts) else None
        for xi, yi in zip(x, y):
            if too_close(xi, yi, tree, kept_x[len(tree_pts):], kept_y[len(tree_pts):], min_sep_m):
                continue
            kept_x.append(xi)
            kept_y.append(yi)
            if len(kept_x) == n:
                break
            if len(kept_x) - len(tree_pts) >= 500:
                tree_pts = np.column_stack([kept_x, kept_y])
                tree = cKDTree(tree_pts)
    return np.array(kept_x), np.array(kept_y), drawn


class FeatureReader:
    """Reads the Phase 2 block rasters at cell centres, one block at a time."""

    def __init__(self, dataset, cfg):
        self.dataset, self.cfg = dataset, cfg
        poly, _ = extent(dataset)
        t = cfg['terrain']
        self.blocks = {(b[0], b[1]): b for b in block_grid(poly.bounds, t['block_core_m'], cfg['sampling']['cell_m'])}
        self.left = min(b[2] for b in self.blocks.values())
        self.top = max(b[5] for b in self.blocks.values())
        self.core = t['block_core_m']
        self.verified = set()

    def values(self, xs, ys, bands=None):
        names = self.cfg['features_terrain']
        bands = bands or names
        out = np.full((len(xs), len(bands)), np.nan, dtype='float64')
        bi = np.floor((self.top - np.asarray(ys)) / self.core).astype(int)
        bj = np.floor((np.asarray(xs) - self.left) / self.core).astype(int)
        for key in set(zip(bi.tolist(), bj.tolist())):
            sel = np.flatnonzero((bi == key[0]) & (bj == key[1]))
            path = block_path(self.dataset, *key)
            if not path.exists():
                continue  # outside every built block: stays NaN and is counted by the caller
            if path not in self.verified:
                load_block(path)
                self.verified.add(path)
            with rasterio.open(path) as r:
                rows, cols = rasterio.transform.rowcol(r.transform, np.asarray(xs)[sel], np.asarray(ys)[sel])
                rows, cols = np.asarray(rows), np.asarray(cols)
                for q, b in enumerate(bands):
                    arr = r.read(names.index(b) + 1)
                    out[sel, q] = arr[rows, cols]
        return out


def positives(dataset, cfg, limit, rng, reader, counts):
    lay = LAYERS[dataset]
    pol = layer(dataset, lay['positive'])
    geoms = valid_geoms(pol['geoms'])
    ids = list(range(len(geoms)))
    years = {}
    if dataset == 'far_western_nepal':
        rule = re.search(r'minimum Year of those points is >= (\d{4})', cfg['registry']['datasets'][dataset]['positive_filter'])
        if not rule:
            raise RuntimeError('positive_filter of far_western_nepal has no parsable minimum year')
        min_year = int(rule.group(1))
        dated = layer(dataset, lay['dated'])
        idx = [i for i, g in enumerate(geoms) if g is not None]
        tree = shapely.STRtree([geoms[i] for i in idx])
        found = collections.defaultdict(list)
        for p, r in zip(dated['geoms'], dated['records']):
            for h in tree.query(p, predicate='intersects'):
                found[idx[h]].append(int(r['Year']))
        years = {k: min(v) for k, v in found.items()}
        counts['known_not_positive_undated'] = sum(1 for i in ids if geoms[i] is not None and i not in years)
        counts['known_not_positive_dated_before_min_year'] = sum(1 for y in years.values() if y < min_year)
        ids = sorted(k for k, y in years.items() if y >= min_year)
    counts['null_or_empty_geometry'] = sum(geoms[i] is None for i in ids)
    ids = [i for i in ids if geoms[i] is not None]
    ids = ids[:limit] if limit else ids
    poly_extent, _ = extent(dataset)
    shapely.prepare(poly_extent)
    elevation_at = None if cfg['registry']['datasets'][dataset]['source_area_available'] else (
        lambda x, y: reader.values(x, y, ['elevation_m'])[:, 0])
    rows, seen = [], set()
    for i in ids:
        x, y, how = choose_positive(geoms[i], cfg['sampling']['cell_m'], rng, elevation_at)
        if x is None:
            counts[f'positive_{how}'] += 1
            continue
        if not shapely.contains_xy(poly_extent, x, y):
            counts['positive_outside_mapping_extent'] += 1
            continue
        if (x, y) in seen:
            counts['positive_duplicate_cell'] += 1
            continue
        seen.add((x, y))
        counts[f'positive_{how}'] += 1
        rows.append({'polygon_index': i, 'x': x, 'y': y, 'year': years.get(i)})
    return pd.DataFrame(rows)


def exclusion_zone(known, obscured, buffer_m):
    """Known landslides buffered by buffer_m, plus obscured areas (not buffered).

    Round joins are polygons whose chords lie inside the true circle; the distance is enlarged so that the
    polygonal buffer circumscribes it and every point closer than buffer_m is excluded."""
    quad_segs = 8
    circumscribed = buffer_m / math.cos(math.pi / (4 * quad_segs))
    zone = shapely.union_all(shapely.buffer(np.array(known, dtype=object), circumscribed, quad_segs=quad_segs))
    if obscured:
        zone = shapely.union(zone, shapely.union_all(obscured))
    return zone


def allowed_background(dataset, cfg):
    lay = LAYERS[dataset]
    buffer_m = cfg['sampling']['background_rule']['exclusion_buffer_m']
    known = []
    for name in lay['known']:
        known += [g for g in valid_geoms(layer(dataset, name)['geoms']) if g is not None]
    obscured = [g for g in valid_geoms(layer(dataset, lay['obscured'])['geoms']) if g is not None] if lay['obscured'] else []
    excluded = exclusion_zone(known, obscured, buffer_m)
    poly_extent, _ = extent(dataset)
    return shapely.difference(poly_extent, excluded), excluded, len(known)


def run(dataset, limit=0, write=True):
    cfg = config()
    s = cfg['sampling']
    rng = np.random.default_rng([cfg['seeds']['sampling'], sorted(LAYERS).index(dataset)])
    counts = collections.Counter()
    reader = FeatureReader(dataset, cfg)
    pos = positives(dataset, cfg, limit, rng, reader, counts)
    allowed, excluded, n_known = allowed_background(dataset, cfg)
    ratio = s['class_ratio_positive_to_background']
    n_bg = len(pos) * ratio[1] // ratio[0]

    def accept(x, y):
        return np.isfinite(reader.values(x, y, ['elevation_m'])[:, 0])

    bx, by, drawn = draw_background(allowed, n_bg, s['cell_m'], s['background_rule']['min_separation_m'], rng, accept)
    bg = pd.DataFrame({'x': bx, 'y': by, 'polygon_index': -1, 'year': None})
    pos['label'], bg['label'] = 1, 0
    frame = pd.concat([pos, bg], ignore_index=True)
    feats = reader.values(frame.x.to_numpy(), frame.y.to_numpy())
    for q, name in enumerate(cfg['features_terrain']):
        frame[name] = feats[:, q]
    missing_core = ~np.isfinite(frame[['elevation_m', 'slope_deg']].to_numpy()).all(axis=1)
    counts['dropped_missing_elevation_or_slope_positive'] = int((missing_core & (frame.label == 1)).sum())
    counts['dropped_missing_elevation_or_slope_background'] = int((missing_core & (frame.label == 0)).sum())
    frame = frame[~missing_core].reset_index(drop=True)
    block = cfg['splits']['block_size_m']
    frame['block_id'] = [f'{dataset}:{int(math.floor(x / block))}:{int(math.floor(y / block))}' for x, y in zip(frame.x, frame.y)]
    frame.insert(0, 'dataset', dataset)
    frame.insert(1, 'sample_id', [f'{dataset}:{"p" if lab else "b"}:{k:06d}' for k, lab in enumerate(frame.label)])
    frame['year'] = frame['year'].astype('float64')
    summary = {'dataset': dataset, 'limit': limit, 'positives': int(frame.label.sum()), 'background': int((frame.label == 0).sum()),
               'known_landslide_polygons': n_known, 'background_draws': int(drawn),
               'allowed_area_km2': allowed.area / 1e6, 'excluded_area_km2': excluded.area / 1e6,
               'blocks_5km': int(frame.block_id.nunique()), 'counts': dict(counts),
               'nan_by_feature': {n: int(frame[n].isna().sum()) for n in cfg['features_terrain']}}
    if not limit and write:
        path = guard(SAMPLES) / f'{dataset}.parquet'
        if load(path) is not None:
            raise RuntimeError(f'{path} exists; samples are write-once')
        save(frame, path, {'dataset': dataset, 'config_seed': cfg['seeds']['sampling']})
        write_json(guard(REPORT) / f'phase3_sampling_{dataset}.json', summary)
    return frame, summary


def verify(dataset, rerun=True):
    """Property checks on the stored samples; a rerun from the seed must reproduce them exactly."""
    cfg = config()
    frame = load(SAMPLES / f'{dataset}.parquet')
    if frame is None:
        raise RuntimeError(f'{dataset}: no stored samples')
    s = cfg['sampling']
    lay = LAYERS[dataset]
    known = []
    for name in lay['known']:
        known += [g for g in valid_geoms(layer(dataset, name)['geoms']) if g is not None]
    tree = shapely.STRtree(known)
    bg = frame[frame.label == 0]
    pts = shapely.points(bg.x.to_numpy(), bg.y.to_numpy())
    nearest = tree.query_nearest(pts, return_distance=True, all_matches=False)[1]
    poly_extent, _ = extent(dataset)
    xy = bg[['x', 'y']].to_numpy()
    pairs = cKDTree(xy).query_pairs(s['background_rule']['min_separation_m'] - 1e-6)
    checks = {
        'ratio_1_to_1': int(frame.label.sum()) * s['class_ratio_positive_to_background'][1] == int((frame.label == 0).sum()),
        'background_min_distance_to_known_m': float(nearest.min()),
        'background_buffer_respected': bool(nearest.min() >= s['background_rule']['exclusion_buffer_m'] - 1e-6),
        'background_pairs_closer_than_min_separation': len(pairs),
        'all_samples_in_mapping_extent': bool(shapely.contains_xy(poly_extent, frame.x.to_numpy(), frame.y.to_numpy()).all()),
        'unique_cells': bool(not frame.duplicated(['x', 'y']).any()),
        'cell_centres_on_grid': bool(np.allclose((frame[['x', 'y']].to_numpy() % s['cell_m']), s['cell_m'] / 2)),
    }
    if lay['obscured']:
        obscured = shapely.union_all([g for g in valid_geoms(layer(dataset, lay['obscured'])['geoms']) if g is not None])
        checks['background_in_obscured'] = int(shapely.contains_xy(obscured, bg.x.to_numpy(), bg.y.to_numpy()).sum())
    if rerun:
        again, _ = run(dataset, 0, write=False)
        checks['rerun_identical'] = bool(again.equals(frame))
    checks['status'] = 'PASS' if (checks['ratio_1_to_1'] and checks['background_buffer_respected']
                                  and checks['background_pairs_closer_than_min_separation'] == 0
                                  and checks['all_samples_in_mapping_extent'] and checks['unique_cells']
                                  and checks['cell_centres_on_grid'] and checks.get('background_in_obscured', 0) == 0
                                  and checks.get('rerun_identical', True)) else 'FAIL'
    write_json(guard(REPORT) / f'phase3_verification_{dataset}.json', checks)
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['run', 'verify'])
    ap.add_argument('dataset', choices=sorted(LAYERS))
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    print(json.dumps(run(a.dataset, a.limit)[1] if a.stage == 'run' else verify(a.dataset), indent=1, default=str))


if __name__ == '__main__':
    main()
