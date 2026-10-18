"""susceptibility_v02 Phase 3: positive and background cells (rules: config 'sampling' + Amendments 1-3).

  python -I scripts/run_susceptibility_v02.py sample <dataset> --limit 1|5|20|0(all)
  python -I scripts/run_susceptibility_v02.py sample_verify <dataset>

Reuses the v01 sampling functions (choose_positive, draw_background, exclusion_zone, Gorkha/Far-Western Nepal positive
and background definitions); features come from the v02 terrain blocks. Writes data/susceptibility_v02/samples/<dataset>
.parquet (write-once, SHA-256 sidecar) and reports/susceptibility_v02/phase3_sampling_<dataset>.json.
"""
import collections
import math

import numpy as np
import pandas as pd
import rasterio
import shapely
from scipy.spatial import cKDTree

from ..common import read_json, write_json
from ..v04.pipeline import load, save
from . import sampling as S1
from .download import file_digest
from .paths import config as v01_config
from .terrain import CacheCorruption, block_grid
from .v02 import DATA, REPORT, config, guard
from .v02_phase1 import (IBURI_EPSG, RAW, _feature_collection, gsi_files, intersects_any, lonlat_to_utm, pga_at, read_grid,
                         split_by_style, zenodo_layer)
from .v02_terrain import block_path, extent_utm, terrain_parameters, working_crs

SAMPLES = DATA / 'samples'
SAMPLED = ('far_western_nepal', 'gorkha_2015', 'iburi_2018')  # sorted: index k of the rng stream (Amendment 3)
EARTHQUAKE = ('gorkha_2015', 'iburi_2018')
BLOCK_M = 5000


class Reader:
    """Reads the v02 terrain blocks at cell centres (each block verified against its sidecar once)."""

    def __init__(self, dataset, cfg):
        self.dataset, self.names = dataset, cfg['features_terrain']
        t = terrain_parameters(cfg)
        epsg = int(working_crs(cfg, dataset).split(':')[1])
        blocks = block_grid(extent_utm(dataset, epsg).bounds, t['block_core_m'], cfg['sampling']['cell_m'])
        self.left, self.top, self.core = min(b[2] for b in blocks), max(b[5] for b in blocks), t['block_core_m']
        self.verified = set()
        self.elevation = {}  # per-block elevation band: the hot path of positive and background draws

    def band(self, r, path, b):
        if b != 'elevation_m':
            return r.read(self.names.index(b) + 1)
        if path not in self.elevation:
            self.elevation[path] = r.read(self.names.index(b) + 1)
        return self.elevation[path]

    def values(self, xs, ys, bands=None):
        bands = bands or self.names
        xs, ys = np.asarray(xs, float), np.asarray(ys, float)
        out = np.full((len(xs), len(bands)), np.nan)
        bi = np.floor((self.top - ys) / self.core).astype(int)
        bj = np.floor((xs - self.left) / self.core).astype(int)
        for key in set(zip(bi.tolist(), bj.tolist())):
            sel = np.flatnonzero((bi == key[0]) & (bj == key[1]))
            path = block_path(self.dataset, *key)
            if not path.exists():
                continue  # outside every built block: NaN, counted by the caller
            if path not in self.verified:
                if file_digest(path, 'sha256') != read_json(path.with_suffix('.json'))['sha256']:
                    raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
                self.verified.add(path)
            with rasterio.open(path) as r:
                rows, cols = rasterio.transform.rowcol(r.transform, xs[sel], ys[sel])
                for q, b in enumerate(bands):
                    out[sel, q] = self.band(r, path, b)[np.asarray(rows), np.asarray(cols)]
        return out


def v01_shim(dataset):
    """v01 registry entry (positive_filter, source_area_available) for the v01 positive functions; registered as
    unchanged in v02."""
    v1 = v01_config()
    return {'registry': {'datasets': {dataset: v1['registry']['datasets'][dataset]}}, 'sampling': {'cell_m': 30}}


def iburi_layers(epsg=IBURI_EPSG):
    """GSI positives (main style, not intersecting Zenodo old landslides), known polygons, cloud-obscured polygons."""
    files = gsi_files()
    feats = _feature_collection(files['landslides'])['features']
    main_i, other_i = split_by_style(feats)
    polys = [shapely.make_valid(lonlat_to_utm(shapely.geometry.shape(f['geometry']), epsg)) for f in feats]
    old, _ = zenodo_layer('old_landslides', epsg)
    react, _ = zenodo_layer('reactivated_landslides', epsg)
    main = [polys[i] for i in main_i]
    hit = intersects_any(main, old)
    positives = [(i, p) for i, p, h in zip(main_i, main, hit) if not h]
    known = polys + old + react
    obscured = [lonlat_to_utm(shapely.geometry.shape(f['geometry']), epsg) for f in _feature_collection(files['obscured'])['features']]
    counts = {'gsi_main_style': len(main_i), 'gsi_deviating_style_exclusion_only': len(other_i),
              'known_not_positive_intersects_old_landslide': int(hit.sum())}
    return positives, known, obscured, counts


def iburi_positives(cfg, limit, rng, reader, counts, positives, extent):
    """As v01 sampling.positives: one cell per polygon, top elevation third (no source area)."""
    shapely.prepare(extent)
    items = positives[:limit] if limit else positives
    rows, seen = [], set()
    for i, poly in items:
        x, y, how = S1.choose_positive(poly, cfg['sampling']['cell_m'], rng, lambda a, b: reader.values(a, b, ['elevation_m'])[:, 0])
        if x is None:
            counts[f'positive_{how}'] += 1
            continue
        if not shapely.contains_xy(extent, x, y):
            counts['positive_outside_mapping_extent'] += 1
            continue
        if (x, y) in seen:
            counts['positive_duplicate_cell'] += 1
            continue
        seen.add((x, y))
        counts[f'positive_{how}'] += 1
        rows.append({'polygon_index': i, 'x': x, 'y': y, 'year': None})
    return pd.DataFrame(rows)


def background_allowed(dataset, cfg, iburi=None):
    """Mapping extent minus buffered known landslides and obscured areas (v01 rule; Iburi layers from Amendments 1-2)."""
    if dataset != 'iburi_2018':
        return S1.allowed_background(dataset, cfg)
    _, known, obscured, _ = iburi
    excluded = S1.exclusion_zone(known, obscured, cfg['sampling']['background_rule']['exclusion_buffer_m'])
    extent = extent_utm(dataset, IBURI_EPSG)
    return shapely.difference(extent, excluded), excluded, len(known)


def elevation_accept(reader, counts):
    """Background acceptance: finite elevation and > 0 m (Amendment 3); rejections counted."""
    def accept(x, y):
        z = reader.values(x, y, ['elevation_m'])[:, 0]
        counts['background_candidates_rejected_no_elevation'] += int((~np.isfinite(z)).sum())
        counts['background_candidates_rejected_elevation_le_0'] += int((np.isfinite(z) & (z <= 0)).sum())
        return np.isfinite(z) & (z > 0)
    return accept


def buffer_accept(known, buffer_m, counts):
    """Exact distance rule: reject a candidate closer than buffer_m to any known landslide polygon.

    The polygonal exclusion zone (v01 exclusion_zone) is only a prefilter: GEOS simplifies buffer input by 1 % of the
    distance, so a buffered polygon can miss points about 1 m inside the true distance (found in the first v02 draw)."""
    tree = shapely.STRtree(known)

    def accept(x, y):
        pts = shapely.points(np.asarray(x, float), np.asarray(y, float))
        near = np.zeros(len(pts), bool)
        hit = tree.query(pts, predicate='dwithin', distance=buffer_m)[0]
        near[hit] = True
        if near.any():  # dwithin includes the boundary; keep candidates exactly at buffer_m
            idx = np.flatnonzero(near)
            d = tree.query_nearest(pts[idx], return_distance=True, all_matches=False)[1]
            near[idx[d >= buffer_m]] = False
        counts['background_candidates_rejected_exact_buffer'] += int(near.sum())
        return ~near
    return accept


def all_of(*accepts):
    def accept(x, y):
        ok = np.ones(len(x), bool)
        for a in accepts:
            idx = np.flatnonzero(ok)
            if len(idx):
                ok[idx] = a(np.asarray(x)[idx], np.asarray(y)[idx])
        return ok
    return accept


def block_ids(dataset, x, y, size_m=BLOCK_M):
    return [f'{dataset}:{int(math.floor(a / size_m))}:{int(math.floor(b / size_m))}' for a, b in zip(x, y)]


def run(dataset, limit=0, write=True):
    if dataset not in SAMPLED:
        raise ValueError(f'{dataset} is not sampled in v02')
    cfg = config()
    d = cfg['registry']['datasets'][dataset]
    if d['role'] != 'development':
        raise ValueError(f'{dataset} has role {d["role"]!r}')
    if cfg['sampling']['background_rule']['exclusion_buffer_m'] is None or 'min_elevation_rule' not in cfg['sampling']['background_rule']:
        raise RuntimeError('buffer (Amendment 2) and sea rule (Amendment 3) must be registered before sampling')
    s = cfg['sampling']
    rng = np.random.default_rng([cfg['seeds']['sampling'], SAMPLED.index(dataset)])
    counts = collections.Counter()
    reader = Reader(dataset, cfg)
    if dataset == 'iburi_2018':
        iburi = iburi_layers()
        counts.update(iburi[3])
        pos = iburi_positives(cfg, limit, rng, reader, counts, iburi[0], extent_utm(dataset, IBURI_EPSG))
    else:
        iburi = None
        pos = S1.positives(dataset, v01_shim(dataset), limit, rng, reader, counts)
    allowed, excluded, n_known = background_allowed(dataset, cfg, iburi)
    known = iburi[1] if iburi else known_and_obscured(dataset, cfg)[0]
    n_bg = len(pos) * s['class_ratio_positive_to_background'][1] // s['class_ratio_positive_to_background'][0]
    bx, by, drawn = S1.draw_background(allowed, n_bg, s['cell_m'], s['background_rule']['min_separation_m'], rng,
                                       all_of(elevation_accept(reader, counts),
                                              buffer_accept(known, s['background_rule']['exclusion_buffer_m'], counts)))
    bg = pd.DataFrame({'x': bx, 'y': by, 'polygon_index': -1, 'year': None})
    pos['label'], bg['label'] = 1, 0
    frame = pd.concat([pos, bg], ignore_index=True)
    feats = reader.values(frame.x.to_numpy(), frame.y.to_numpy())
    for q, name in enumerate(cfg['features_terrain']):
        frame[name] = feats[:, q]
    missing = ~np.isfinite(frame[['elevation_m', 'slope_deg']].to_numpy()).all(axis=1)
    counts['dropped_missing_elevation_or_slope_positive'] = int((missing & (frame.label == 1)).sum())
    counts['dropped_missing_elevation_or_slope_background'] = int((missing & (frame.label == 0)).sum())
    frame = frame[~missing].reset_index(drop=True)
    counts['positives_with_elevation_le_0'] = int(((frame.label == 1) & (frame.elevation_m <= 0)).sum())
    if dataset in EARTHQUAKE:
        prov = read_json(RAW / f'shakemap_{dataset}' / 'provenance.json')
        gpath = RAW / f'shakemap_{dataset}' / 'grid.xml'
        if file_digest(gpath, 'sha256') != prov['sha256']:
            raise RuntimeError(f'{gpath} changed since download (frozen)')
        frame['log10_pga_pctg'] = pga_at(frame.x.to_numpy(), frame.y.to_numpy(), working_crs(cfg, dataset), read_grid(gpath))
        counts['pga_nan'] = int(frame.log10_pga_pctg.isna().sum())
    frame['block_id'] = block_ids(dataset, frame.x, frame.y)
    frame.insert(0, 'dataset', dataset)
    frame.insert(1, 'sample_id', [f'{dataset}:{"p" if lab else "b"}:{k:06d}' for k, lab in enumerate(frame.label)])
    frame['year'] = frame['year'].astype('float64')
    summary = {'dataset': dataset, 'limit': limit, 'crs': working_crs(cfg, dataset), 'seed': [cfg['seeds']['sampling'], SAMPLED.index(dataset)],
               'positives': int(frame.label.sum()), 'background': int((frame.label == 0).sum()),
               'known_landslide_polygons': n_known, 'background_draws': int(drawn),
               'allowed_area_km2': allowed.area / 1e6, 'excluded_area_km2': excluded.area / 1e6,
               'blocks_5km': int(frame.block_id.nunique()), 'counts': dict(counts),
               'nan_by_feature': {n: int(frame[n].isna().sum()) for n in cfg['features_terrain']}}
    if not limit and write:
        path = guard(SAMPLES) / f'{dataset}.parquet'
        if load(path) is not None:
            raise RuntimeError(f'{path} exists; samples are write-once')
        save(frame, path, {'dataset': dataset, 'seed': summary['seed']})
        write_json(guard(REPORT) / f'phase3_sampling_{dataset}.json', summary)
    return frame, summary


def known_and_obscured(dataset, cfg):
    """Known landslide polygons (exclusion), obscured areas and the extent, as used for background (verification)."""
    if dataset == 'iburi_2018':
        _, known, obscured, _ = iburi_layers()
        return known, obscured, extent_utm(dataset, IBURI_EPSG)
    lay = S1.LAYERS[dataset]
    known = []
    for name in lay['known']:
        known += [g for g in S1.valid_geoms(S1.layer(dataset, name)['geoms']) if g is not None]
    obscured = [g for g in S1.valid_geoms(S1.layer(dataset, lay['obscured'])['geoms']) if g is not None] if lay['obscured'] else []
    return known, obscured, extent_utm(dataset, int(working_crs(cfg, dataset).split(':')[1]))


def verify(dataset, rerun=True):
    """Property checks on the stored samples; a rerun from the seed must reproduce them exactly."""
    cfg = config()
    frame = load(SAMPLES / f'{dataset}.parquet')
    if frame is None:
        raise RuntimeError(f'{dataset}: no stored samples')
    s = cfg['sampling']
    known, obscured, extent = known_and_obscured(dataset, cfg)
    bg = frame[frame.label == 0]
    nearest = shapely.STRtree(known).query_nearest(shapely.points(bg.x.to_numpy(), bg.y.to_numpy()),
                                                   return_distance=True, all_matches=False)[1]
    pairs = cKDTree(bg[['x', 'y']].to_numpy()).query_pairs(s['background_rule']['min_separation_m'] - 1e-6)
    checks = {
        'ratio_1_to_1': int(frame.label.sum()) * s['class_ratio_positive_to_background'][1] == int((frame.label == 0).sum()),
        'background_min_distance_to_known_m': float(nearest.min()),
        'background_buffer_respected': bool(nearest.min() >= s['background_rule']['exclusion_buffer_m'] - 1e-6),
        'background_pairs_closer_than_min_separation': len(pairs),
        'background_elevation_le_0': int((bg.elevation_m <= 0).sum()),
        'all_samples_in_mapping_extent': bool(shapely.contains_xy(extent, frame.x.to_numpy(), frame.y.to_numpy()).all()),
        'unique_cells': bool(not frame.duplicated(['x', 'y']).any()),
        'cell_centres_on_grid': bool(np.allclose(frame[['x', 'y']].to_numpy() % s['cell_m'], s['cell_m'] / 2)),
        'background_in_obscured': int(shapely.contains_xy(shapely.union_all(obscured), bg.x.to_numpy(), bg.y.to_numpy()).sum()) if obscured else 0,
        'pga_nan': int(frame['log10_pga_pctg'].isna().sum()) if 'log10_pga_pctg' in frame else None,
    }
    if rerun:
        again, _ = run(dataset, 0, write=False)
        checks['rerun_identical'] = bool(again.equals(frame))
    checks['status'] = 'PASS' if (checks['ratio_1_to_1'] and checks['background_buffer_respected']
                                  and checks['background_pairs_closer_than_min_separation'] == 0
                                  and checks['background_elevation_le_0'] == 0
                                  and checks['all_samples_in_mapping_extent'] and checks['unique_cells']
                                  and checks['cell_centres_on_grid'] and checks['background_in_obscured'] == 0
                                  and checks['pga_nan'] in (None, 0) and checks.get('rerun_identical', True)) else 'FAIL'
    write_json(guard(REPORT) / f'phase3_verification_{dataset}.json', checks)
    return checks


def main():
    import argparse
    import json
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['sample', 'sample_verify'])
    ap.add_argument('dataset', choices=SAMPLED)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    res = run(a.dataset, a.limit)[1] if a.stage == 'sample' else verify(a.dataset)
    print(json.dumps(res, indent=1, default=str))
