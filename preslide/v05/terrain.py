"""V0.5 static terrain: the V0.4 feature code on a strictly read-only DEM tile layer.

preslide.v04.terrain.static_features is reproduced here line by line except that DEM tiles are only read from the
existing baseline/V0.4 caches (checksum and pre-event provenance verified) and never downloaded or written. The
pure raster functions (curvatures, focal means, depression filling, D8) are imported unchanged. Equality with V0.4
is verified on every recomputed positive (pipeline.positive_consistency).
"""
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds, Resampling
from rasterio.windows import from_bounds, Window
from scipy import ndimage

from ..common import read_json
from ..sources import ROOT
from ..terrain import PROJECT, derivatives
from ..v04.terrain import curvatures, disc, focal_mean, fill_depressions, flow_accumulation
from .paths import sha

TILE_DIRS = (ROOT / 'data/raw/terrain', ROOT / 'data/v04/cache/terrain_tiles')
_VERIFIED = set()


def tile(lat, lon, event_day):
    name = f'N{lat:02d}E{lon:03d}'
    for directory in TILE_DIRS:
        hgt, manifest = directory / f'{name}.hgt', directory / f'{name}.json'
        if manifest.exists():
            meta = read_json(manifest)
            if str(hgt) not in _VERIFIED:
                if sha(hgt) != meta['sha256']:
                    raise ValueError('Terrain source cache checksum mismatch')
                _VERIFIED.add(str(hgt))
            if meta['object_last_modified'][:10] >= event_day:
                raise ValueError('terrain_source_not_demonstrably_pre_event')
            return hgt, meta
    raise ValueError(f'terrain_tile_not_cached:{name} (V0.5 never downloads DEM tiles)')


def dem_window(lon, lat, radius, res, crs, event_day):
    px, py = PROJECT.transform(lon, lat)
    n = math.ceil(2 * radius / res)
    left, top = px - radius, py + radius
    transform = from_origin(left, top, res, res)
    dem = np.full((n, n), np.nan, dtype='float32')
    bounds = transform_bounds(crs, 'EPSG:4326', left, top - n * res, left + n * res, top, densify_pts=21)
    sources = []
    for tlon in range(math.floor(bounds[0]), math.floor(bounds[2]) + 1):
        for tlat in range(math.floor(bounds[1]), math.floor(bounds[3]) + 1):
            path, meta = tile(tlat, tlon, event_day)
            with rasterio.open(path) as src:
                if src.crs.to_epsg() != 4326 or src.nodata != -32768:
                    raise ValueError('Unexpected DEM CRS/nodata')
                win = from_bounds(max(bounds[0] - .001, src.bounds.left), max(bounds[1] - .001, src.bounds.bottom),
                                  min(bounds[2] + .001, src.bounds.right), min(bounds[3] + .001, src.bounds.top), src.transform)
                win = win.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
                reproject(src.read(1, window=win), dem, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, src_nodata=-32768, dst_nodata=np.nan,
                          init_dest_nodata=False, resampling=Resampling.bilinear)
            sources.append(meta)
    return dem, left, top, sources


def static_features(event, samples, cfg, margin_m=5010):
    """Identical to preslide.v04.terrain.static_features (NaN = not computable, never imputed)."""
    res = cfg['terrain_resolution_m']
    radius = cfg['control_max_distance_m'] + 300 + margin_m
    dem, left, top, _ = dem_window(event['longitude'], event['latitude'], radius, res, cfg['terrain_crs'], event['event_day'])
    slope, _ = derivatives(dem, res)
    profile, plan, tri = curvatures(dem.astype(float), res)
    tpi150 = dem - focal_mean(dem.astype(float), disc(150 / res))
    tpi500 = dem - focal_mean(dem.astype(float), disc(500 / res))
    fp = disc(500 / res) > 0
    zmin = ndimage.minimum_filter(np.nan_to_num(dem, nan=np.inf), footprint=fp, mode='constant', cval=np.inf)
    zmax = ndimage.maximum_filter(np.nan_to_num(dem, nan=-np.inf), footprint=fp, mode='constant', cval=-np.inf)
    with np.errstate(invalid='ignore', divide='ignore'):
        relpos = (dem - zmin) / (zmax - zmin)
    relpos[~np.isfinite(tpi500)] = np.nan
    filled, outlet, iterations = fill_depressions(dem.astype(float))
    acc, edge = flow_accumulation(filled, outlet, res)
    cols = np.floor((samples.x.to_numpy() - left) / res).astype(int)
    rows = np.floor((top - samples.y.to_numpy()) / res).astype(int)
    if (rows < 0).any() or (cols < 0).any() or (rows >= dem.shape[0]).any() or (cols >= dem.shape[1]).any():
        raise ValueError('Sample outside static terrain window')
    area = acc[rows, cols] * res * res
    truncated = edge[rows, cols]
    beta = np.deg2rad(np.maximum(slope[rows, cols], 0.1))
    out = pd.DataFrame({'sample_id': samples.sample_id.to_numpy(),
                        'profile_curvature': profile[rows, cols], 'plan_curvature': plan[rows, cols],
                        'roughness_tri': tri[rows, cols], 'tpi_150m': tpi150[rows, cols], 'tpi_500m': tpi500[rows, cols],
                        'relative_position_500m': relpos[rows, cols],
                        'log10_catchment_m2': np.where(truncated, np.nan, np.log10(area)),
                        'twi': np.where(truncated, np.nan, np.log(area / res / np.tan(beta))),
                        'catchment_truncated': truncated,
                        'static_dem_elevation_check': dem[rows, cols]})
    meta = {'window_radius_m': radius, 'cells': int(dem.size), 'fill_iterations': int(iterations),
            'nodata_cells': int(np.isnan(dem).sum()), 'truncated_samples': int(truncated.sum())}
    return out, meta
