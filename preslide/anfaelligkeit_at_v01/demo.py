"""Demo layer (config demo): relative susceptibility for one 9 km block of the demo area, scored by the
leave-one-area-out model that did NOT have the demo area in its training.

  python -m preslide.anfaelligkeit_at_v01 demo
"""
import json

import joblib
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from shapely import contains_xy

from ..common import read_json, write_json
from ..matching import austria_boundary
from ..terrain import INVERSE
from . import context, terrain
from .context import GEO, one_hot
from .paths import DATA, MODELS, REPORT, config, guard, load


def percentile_rank(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """0-100 rank among the valid cells of the block (ties share the mean rank); NaN outside."""
    out = np.full(values.shape, np.nan)
    v = values[valid]
    order = pd.Series(v).rank(method='average').to_numpy()
    out[valid] = 100.0 * (order - 0.5) / len(v)
    return out


def run() -> dict:
    cfg = config()
    results = read_json(REPORT / 'results_srtm.json')
    area = results['largest_area']
    bundle = joblib.load(MODELS / 'srtm/demo_fold.joblib')
    if bundle['held_out_area'] != area:
        raise RuntimeError('demo model was not the fold that held out the demo area')
    samples = load(DATA / 'samples_srtm.parquet')
    pos = samples[(samples.area_id == area) & (samples.label == 1)]
    bx, by = terrain.block_of(pos.x, pos.y)
    counts = pd.Series(list(zip(bx.tolist(), by.tolist()))).value_counts()
    best = max(counts.index, key=lambda k: (counts[k], -k[0], -k[1]))
    rasters = terrain.compute_block('srtm', *best)
    left, top = terrain.block_origin(*best)
    n = terrain.BLOCK
    cols, rows = np.meshgrid(np.arange(n), np.arange(n))
    x = left + (cols + 0.5) * terrain.RES
    y = top - (rows + 0.5) * terrain.RES
    lon, lat = INVERSE.transform(x.ravel(), y.ravel())
    lo, hi = cfg['background']['elevation_range_m']
    elev, slope = rasters['elevation'].ravel(), rasters['slope'].ravel()
    valid = contains_xy(austria_boundary(), lon, lat) & np.isfinite(elev) & (elev >= lo) & (elev <= hi) & \
        (slope >= cfg['background']['minimum_slope_deg'])
    geo = one_hot(context.geology(lon, lat, cfg), GEO)
    feats = pd.DataFrame({k: rasters[k].ravel() for k in terrain.TERRAIN})
    feats = pd.concat([feats, geo.reset_index(drop=True)], axis=1)
    cols_tg = bundle['features']['terrain_geology']
    model = bundle['models'][('hgb', 'terrain_geology')]
    slope_model = bundle['models'][('hgb', 'slope_only')]
    score = model.predict_proba(feats[cols_tg].to_numpy(float))[:, 1]
    score_slope = slope_model.predict_proba(feats[['slope']].to_numpy(float))[:, 1]
    rank = percentile_rank(score, valid).reshape(n, n)
    rank_slope = percentile_rank(score_slope, valid).reshape(n, n)
    out = guard(DATA / 'demo')
    with rasterio.open(out / 'demo_relative_susceptibility.tif', 'w', driver='GTiff', height=n, width=n, count=2, dtype='float32',
                       crs=terrain.CRS, transform=from_origin(left, top, terrain.RES, terrain.RES), nodata=np.nan, compress='deflate') as dst:
        dst.write(rank.astype('float32'), 1)
        dst.write(rank_slope.astype('float32'), 2)
        dst.set_band_description(1, 'percentile rank hgb terrain_geology (relative, held-out fold)')
        dst.set_band_description(2, 'percentile rank hgb slope_only (relative, held-out fold)')
    # documented positives of the demo area inside the block, located on the layers (descriptive only)
    inb = pos[(bx == best[0]) & (by == best[1])]
    c = np.floor((inb.x.to_numpy() - left) / terrain.RES).astype(int)
    r = np.floor((top - inb.y.to_numpy()) / terrain.RES).astype(int)
    pr, ps = rank[r, c], rank_slope[r, c]
    corners = INVERSE.transform(np.array([left, left + n * terrain.RES, left + n * terrain.RES, left]),
                                np.array([top, top, top - n * terrain.RES, top - n * terrain.RES]))
    meta = {'area_id': area, 'block': list(best), 'block_left_top_epsg31287': [left, top], 'cells': n * n,
            'valid_cells': int(valid.sum()), 'corners_lonlat_tl_tr_br_bl': [[float(a), float(b)] for a, b in zip(*corners)],
            'model': 'hgb terrain_geology, fold holding out ' + area, 'positives_in_block': int(len(inb)),
            'positives_in_top20_model': float(np.mean(pr >= 80)) if len(inb) else None,
            'positives_in_top20_slope': float(np.mean(ps >= 80)) if len(inb) else None,
            'note': 'descriptive: one block chosen by positive count, values are percentile ranks within the block (relative '
                    'susceptibility), not probabilities'}
    write_json(out / 'demo_meta.json', meta)
    np.savez_compressed(out / 'demo_layers.npz', rank=rank.astype('float32'), rank_slope=rank_slope.astype('float32'))
    pd.DataFrame({'lon': inb.lon, 'lat': inb.lat, 'rank_model': pr, 'rank_slope': ps}).to_parquet(out / 'demo_positives.parquet', index=False)
    print(json.dumps(meta, indent=1))
    return meta
