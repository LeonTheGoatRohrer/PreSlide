"""Phase 2: terrain feature rasters per block from NASADEM on a 30 m UTM grid (parameters: config 'terrain').

  python -m preslide.susceptibility.terrain build gorkha_2015|far_western_nepal --limit 1|5|20|0(all)

Each block stores only its core (block_core_m); hydrology and neighbourhood features see block_margin_m around it.
Every raster has a JSON sidecar with its SHA-256; a mismatch on reuse raises.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import rasterio
import shapely
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from scipy import ndimage

from ..common import read_json, write_json
from ..terrain import derivatives
from ..v04.terrain import curvatures, disc, fill_depressions, flow_accumulation, focal_mean
from .dem import DEM, nasadem_id, tiles_for
from .download import file_digest
from .inventory import RAW, layer_crs, read_layer
from .paths import DATA, config, guard

FEATURES_DIR = DATA / 'features'
EXTENT_LAYERS = {'gorkha_2015': 'MappingExtent20170209.shp', 'far_western_nepal': 'LandslideInventory_FarWesternNepal_AOI.shp'}
NASADEM_NODATA = -32768


class CacheCorruption(RuntimeError):
    pass


def check_dem_date(cfg, dataset):
    """Leakage rule: the DEM must be acquired strictly before the earliest positive event of the dataset."""
    first = cfg['registry']['datasets'][dataset]['earliest_event_date']
    if not first or not cfg['dem']['acquisition_end'] < first:
        raise ValueError(f'{dataset}: DEM acquisition_end {cfg["dem"]["acquisition_end"]} is not before {first}')


def extent(dataset):
    """Mapping-extent polygon in the inventory CRS (made valid)."""
    shp = next((RAW / dataset / 'extracted').rglob(EXTENT_LAYERS[dataset]))
    layer = read_layer(shp)
    return shapely.make_valid(shapely.union_all([g for g in layer['geoms'] if g is not None])), layer_crs(shp)


def block_grid(bounds, core_m, res_m):
    """Block cores (i, j, left, bottom, right, top) covering `bounds`, aligned to multiples of res_m."""
    left = math.floor(bounds[0] / res_m) * res_m
    top = math.ceil(bounds[3] / res_m) * res_m
    n_i = math.ceil((top - bounds[1]) / core_m)
    n_j = math.ceil((bounds[2] - left) / core_m)
    return [(i, j, left + j * core_m, top - (i + 1) * core_m, left + (j + 1) * core_m, top - i * core_m)
            for i in range(n_i) for j in range(n_j)]


def reproject_to_grid(src, src_transform, src_crs, left, top, shape, crs, res_m, src_nodata):
    dst = np.full(shape, np.nan, dtype='float32')
    reproject(src.astype('float32'), dst, src_transform=src_transform, src_crs=src_crs, src_nodata=src_nodata,
              dst_transform=from_origin(left, top, res_m, res_m), dst_crs=crs, dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    return dst


def dem_window(crs, left, bottom, right, top, res_m):
    """NASADEM mosaic reprojected to the 30 m grid of the window (NaN = nodata)."""
    lon0, lat0, lon1, lat1 = transform_bounds(crs, 'EPSG:4326', left, bottom, right, top, densify_pts=21)
    pad = 0.01
    files = []
    for lat, lon in tiles_for((lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad)):
        f = DEM / 'nasadem' / nasadem_id(lat, lon) / f'{nasadem_id(lat, lon)}.tif'
        if not f.exists():
            raise FileNotFoundError(f'NASADEM tile missing: {f}')
        files.append(rasterio.open(f))
    try:
        mosaic, transform = merge(files, bounds=(lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad), nodata=NASADEM_NODATA)
    finally:
        for f in files:
            f.close()
    shape = (round((top - bottom) / res_m), round((right - left) / res_m))
    return reproject_to_grid(mosaic[0], transform, 'EPSG:4326', left, top, shape, crs, res_m, NASADEM_NODATA)


def window_features(dem, res_m, t):
    """All registered terrain features on a DEM window (NaN where not computable)."""
    z = dem.astype(float)
    slope, aspect = derivatives(dem, res_m)
    profile, plan, tri = curvatures(z, res_m)
    tpi = z - focal_mean(z, disc(t['tpi_radius_m'] / res_m))
    fp = disc(t['relief_radius_m'] / res_m) > 0
    zmax = ndimage.maximum_filter(np.where(np.isfinite(z), z, -np.inf), footprint=fp, mode='constant', cval=np.nan)
    zmin = ndimage.minimum_filter(np.where(np.isfinite(z), z, np.inf), footprint=fp, mode='constant', cval=np.nan)
    relief = zmax - zmin
    relief[~np.isfinite(relief)] = np.nan
    filled, outlet, iterations = fill_depressions(z)
    acc, edge = flow_accumulation(filled, outlet, res_m)
    area = acc * res_m * res_m
    channel = area >= t['channel_threshold_m2']
    drainage = ndimage.distance_transform_edt(~channel) * res_m if channel.any() else np.full(z.shape, np.nan)
    beta = np.deg2rad(np.maximum(slope, 0.1))
    with np.errstate(invalid='ignore', divide='ignore'):
        twi = np.log(area / res_m / np.tan(beta))
    invalid = ~np.isfinite(z)
    out = {'elevation_m': z, 'slope_deg': slope, 'aspect_sin': np.sin(np.deg2rad(aspect)),
           'aspect_cos': np.cos(np.deg2rad(aspect)), 'profile_curvature': profile, 'plan_curvature': plan,
           'tri_m': tri, 'tpi_m': tpi, 'relief_1km_m': relief,
           'log10_catchment_m2': np.where(edge, np.nan, np.log10(area)), 'twi': np.where(edge, np.nan, twi),
           'drainage_distance_m': drainage}
    for k in out:
        out[k] = np.where(invalid, np.nan, out[k]).astype('float32')
    return out, {'fill_iterations': int(iterations), 'truncated_cells': int(edge.sum())}


def block_path(dataset, i, j):
    return FEATURES_DIR / dataset / f'block_{i:03d}_{j:03d}.tif'


def load_block(path):
    meta = read_json(Path(path).with_suffix('.json'))
    if file_digest(path, 'sha256') != meta['sha256']:
        raise CacheCorruption(f'Checkpoint checksum mismatch: {path}')
    return path, meta


def build_block(dataset, cfg, crs, i, j, left, bottom, right, top):
    path = block_path(dataset, i, j)
    if path.exists():
        return load_block(path)[1]
    t, res = cfg['terrain'], cfg['sampling']['cell_m']
    m = t['block_margin_m']
    dem = dem_window(crs, left - m, bottom - m, right + m, top + m, res)
    feats, meta = window_features(dem, res, t)
    k = round(m / res)
    names = cfg['features_terrain']
    stack = np.stack([feats[n][k:-k, k:-k] for n in names])
    guard(path.parent)
    profile = {'driver': 'GTiff', 'dtype': 'float32', 'count': len(names), 'height': stack.shape[1],
               'width': stack.shape[2], 'crs': crs, 'transform': from_origin(left, top, res, res), 'nodata': np.nan,
               'compress': 'deflate', 'predictor': 3, 'tiled': True, 'blockxsize': 256, 'blockysize': 256}
    tmp = path.with_suffix('.tmp.tif')
    with rasterio.open(tmp, 'w', **profile) as dst:
        dst.write(stack)
        dst.descriptions = tuple(names)
    tmp.replace(path)
    meta.update({'dataset': dataset, 'block': [i, j], 'bounds': [left, bottom, right, top], 'crs': crs,
                 'features': names, 'nan_cells': {n: int(np.isnan(stack[q]).sum()) for q, n in enumerate(names)},
                 'cells': int(stack[0].size), 'dem': cfg['dem']['primary'], 'sha256': file_digest(path, 'sha256')})
    write_json(path.with_suffix('.json'), meta)
    return meta


def build(dataset, limit=0):
    cfg = config()
    check_dem_date(cfg, dataset)
    poly, crs = extent(dataset)
    if crs.to_string() != cfg['terrain']['crs_by_dataset'][dataset]:
        raise ValueError(f'{dataset}: inventory CRS {crs.to_string()} differs from registered working CRS')
    t = cfg['terrain']
    blocks = [b for b in block_grid(poly.bounds, t['block_core_m'], cfg['sampling']['cell_m'])
              if shapely.box(*b[2:]).intersects(poly)]
    selected = blocks[:limit] if limit else blocks
    metas = [build_block(dataset, cfg, crs.to_string(), *b) for b in selected]
    summary = {'dataset': dataset, 'blocks_total': len(blocks), 'blocks_built': len(metas),
               'cells': sum(m['cells'] for m in metas),
               'nan_fraction': {n: sum(m['nan_cells'][n] for m in metas) / max(1, sum(m['cells'] for m in metas))
                                for n in cfg['features_terrain']}}
    if not limit:
        write_json(guard(FEATURES_DIR / dataset) / 'summary.json', summary)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['build'])
    ap.add_argument('dataset', choices=sorted(EXTENT_LAYERS))
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    print(json.dumps(build(a.dataset, a.limit), indent=1))


if __name__ == '__main__':
    main()
