"""Terrain on a fixed national 30 m EPSG:31287 grid, computed per 300 x 300 cell block with a 5 km catchment margin.

Two DEM variants (config `dem`): `srtm` (SRTMGL1 v3, February 2000; primary, provenance before every event >= 2001)
and `skadi` (the V0.4 Skadi tiles; sensitivity only). The feature algorithms are the unchanged V0.4/V0 primitives
(preslide.terrain.derivatives, preslide.v04.terrain.curvatures / focal_mean / fill_depressions / flow_accumulation).
"""
import gzip
import math
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds, Resampling
from rasterio.windows import from_bounds, Window
from scipy import ndimage

from ..common import read_json, write_json, digest
from ..sources import ROOT
from ..terrain import derivatives
from ..v04.terrain import curvatures, disc, focal_mean, fill_depressions, flow_accumulation
from .paths import DATA, guard, sha

CRS = 'EPSG:31287'
RES = 30
BLOCK = 300                      # cells per block side (9 km)
TERRAIN = ['elevation', 'slope', 'aspect_sin', 'aspect_cos', 'profile_curvature', 'plan_curvature', 'roughness_tri',
           'tpi_150m', 'tpi_500m', 'relative_position_500m', 'log10_catchment_m2', 'twi']
ALGORITHM = 'anfaelligkeit_at_v01-terrain-1'
SKADI_READ_ONLY = (ROOT / 'data/raw/terrain', ROOT / 'data/v04/cache/terrain_tiles', ROOT / 'data/v09/cache/terrain_tiles')
_VERIFIED = set()


def margin_cells(margin_m: float = 5010) -> int:
    return math.ceil(margin_m / RES)


def block_of(x_m, y_m):
    """Block index (bx, by) of EPSG:31287 coordinates; block bx covers x in [bx*9000, (bx+1)*9000)."""
    size = BLOCK * RES
    return np.floor(np.asarray(x_m) / size).astype(int), np.floor(np.asarray(y_m) / size).astype(int)


def block_origin(bx: int, by: int):
    size = BLOCK * RES
    return bx * size, (by + 1) * size          # left, top


# ---------- DEM tiles ----------

def _curl(url, out, headers):
    subprocess.run([shutil.which('curl.exe') or 'curl', '-f', '-sS', '-L', '--retry', '3', '--max-time', '600',
                    '-D', str(headers), '-o', str(out), url], check=True, timeout=900)
    last = [s.split(':', 1)[1].strip() for s in headers.read_text().splitlines() if s.lower().startswith('last-modified:')]
    return parsedate_to_datetime(last[-1]).isoformat() if last else None


def _verified(hgt, manifest):
    meta = read_json(manifest)
    if str(hgt) not in _VERIFIED:
        if sha(hgt) != meta['sha256']:
            raise ValueError(f'DEM tile checksum mismatch: {hgt}')
        _VERIFIED.add(str(hgt))
    return hgt, meta


def srtm_tile(lat: int, lon: int):
    name = f'N{lat:02d}E{lon:03d}'
    directory = DATA / 'cache/dem_srtm'
    hgt, manifest = directory / f'{name}.hgt', directory / f'{name}.json'
    if not manifest.exists():
        guard(directory)
        url = f'https://step.esa.int/auxdata/dem/SRTMGL1/{name}.SRTMGL1.hgt.zip'
        archive = directory / f'{name}.zip'
        modified = _curl(url, archive, directory / f'{name}.headers.txt')
        with zipfile.ZipFile(archive) as z:
            member = [m for m in z.namelist() if m.lower().endswith('.hgt')]
            if len(member) != 1:
                raise ValueError(f'Unexpected SRTM archive content: {z.namelist()}')
            with z.open(member[0]) as src, hgt.with_suffix('.tmp').open('wb') as dst:
                shutil.copyfileobj(src, dst)
        hgt.with_suffix('.tmp').replace(hgt)
        if hgt.stat().st_size != 3601 * 3601 * 2:
            raise ValueError('Unexpected SRTMGL1 dimensions')
        write_json(manifest, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'object_last_modified': modified,
                              'sha256': sha(hgt), 'source': 'NASA/USGS SRTMGL1 v3 via ESA STEP auxdata mirror',
                              'acquisition': '2000-02-11/2000-02-22 (voids filled from later sources)',
                              'vertical_datum': 'EGM96', 'resolution': '1 arc second', 'nodata': -32768})
    return _verified(hgt, manifest)


def skadi_tile(lat: int, lon: int):
    name = f'N{lat:02d}E{lon:03d}'
    for directory in SKADI_READ_ONLY:
        if (directory / f'{name}.json').exists():
            return _verified(directory / f'{name}.hgt', directory / f'{name}.json')
    directory = DATA / 'cache/dem_skadi'
    hgt, manifest = directory / f'{name}.hgt', directory / f'{name}.json'
    if not manifest.exists():
        guard(directory)
        url = f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat:02d}/{name}.hgt.gz'
        compressed = directory / f'{name}.hgt.gz'
        modified = _curl(url, compressed, directory / f'{name}.headers.txt')
        with gzip.open(compressed, 'rb') as src, hgt.with_suffix('.tmp').open('wb') as dst:
            shutil.copyfileobj(src, dst)
        hgt.with_suffix('.tmp').replace(hgt)
        if hgt.stat().st_size != 3601 * 3601 * 2:
            raise ValueError('Unexpected Skadi dimensions')
        write_json(manifest, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'object_last_modified': modified,
                              'sha256': sha(hgt), 'source': 'Mapzen Skadi composite; attribution includes Austrian DGM, EU-DEM and USGS',
                              'vertical_datum': 'EGM96', 'resolution': '1 arc second', 'nodata': -32768})
    return _verified(hgt, manifest)


TILES = {'srtm': srtm_tile, 'skadi': skadi_tile}


def dem_grid(variant: str, left: float, top: float, n: int):
    """n x n DEM on the 30 m EPSG:31287 grid with upper-left corner (left, top), mosaicked from 1-degree tiles."""
    if left % RES or top % RES:
        raise ValueError('DEM grid must be aligned to multiples of 30 m')
    transform = from_origin(left, top, RES, RES)
    dem = np.full((n, n), np.nan, dtype='float32')
    bounds = transform_bounds(CRS, 'EPSG:4326', left, top - n * RES, left + n * RES, top, densify_pts=21)
    sources = []
    for tlon in range(math.floor(bounds[0]), math.floor(bounds[2]) + 1):
        for tlat in range(math.floor(bounds[1]), math.floor(bounds[3]) + 1):
            path, meta = TILES[variant](tlat, tlon)
            with rasterio.open(path) as src:
                if src.crs.to_epsg() != 4326 or src.nodata != -32768:
                    raise ValueError('Unexpected DEM CRS/nodata')
                win = from_bounds(max(bounds[0] - .001, src.bounds.left), max(bounds[1] - .001, src.bounds.bottom),
                                  min(bounds[2] + .001, src.bounds.right), min(bounds[3] + .001, src.bounds.top), src.transform)
                win = win.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
                reproject(src.read(1, window=win), dem, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=transform, dst_crs=CRS, src_nodata=-32768, dst_nodata=np.nan,
                          init_dest_nodata=False, resampling=Resampling.bilinear)
            sources.append({'tile': path.stem, 'sha256': meta['sha256']})
    return dem, sources


# ---------- features (pure) ----------

def terrain_rasters(dem: np.ndarray, res: float = RES) -> dict:
    """All TERRAIN rasters for a DEM window (NaN = not computable; catchment/TWI NaN where truncated by the edge)."""
    z = dem.astype(float)
    slope, aspect = derivatives(dem, res)
    profile, plan, tri = curvatures(z, res)
    tpi150 = z - focal_mean(z, disc(150 / res))
    tpi500 = z - focal_mean(z, disc(500 / res))
    fp = disc(500 / res) > 0
    zmin = ndimage.minimum_filter(np.nan_to_num(z, nan=np.inf), footprint=fp, mode='constant', cval=np.inf)
    zmax = ndimage.maximum_filter(np.nan_to_num(z, nan=-np.inf), footprint=fp, mode='constant', cval=-np.inf)
    with np.errstate(invalid='ignore', divide='ignore'):
        relpos = (z - zmin) / (zmax - zmin)
    relpos[~np.isfinite(tpi500)] = np.nan
    filled, outlet, _ = fill_depressions(z)
    acc, edge = flow_accumulation(filled, outlet, res)
    area = acc * res * res
    beta = np.deg2rad(np.maximum(slope, 0.1))
    with np.errstate(invalid='ignore', divide='ignore'):
        catchment = np.where(edge | ~np.isfinite(z), np.nan, np.log10(area))
        twi = np.where(edge | ~np.isfinite(z), np.nan, np.log(area / res / np.tan(beta)))
    a = np.deg2rad(aspect.astype(float))
    nan = ~np.isfinite(z)
    out = {'elevation': z, 'slope': slope, 'aspect_sin': np.sin(a), 'aspect_cos': np.cos(a), 'profile_curvature': profile,
           'plan_curvature': plan, 'roughness_tri': tri, 'tpi_150m': tpi150, 'tpi_500m': tpi500,
           'relative_position_500m': relpos, 'log10_catchment_m2': catchment, 'twi': twi}
    for k in ('slope', 'aspect_sin', 'aspect_cos', 'profile_curvature', 'plan_curvature', 'roughness_tri'):
        out[k] = np.where(nan, np.nan, out[k])
    return {k: np.asarray(v, dtype='float32') for k, v in out.items()}


# ---------- block cache ----------

def block_identity(variant: str, bx: int, by: int, margin_m: float) -> str:
    return digest({'variant': variant, 'bx': int(bx), 'by': int(by), 'res': RES, 'block': BLOCK, 'margin_m': margin_m,
                   'crs': CRS, 'algorithm': ALGORITHM})


def block_path(variant: str, bx: int, by: int):
    return DATA / f'cache/blocks_{variant}' / f'b{bx}_{by}.npz'


def compute_block(variant: str, bx: int, by: int, margin_m: float = 5010) -> dict:
    path = block_path(variant, bx, by)
    identity = block_identity(variant, bx, by, margin_m)
    if path.exists():
        meta = read_json(path.with_suffix('.json'))
        if meta['identity'] != identity:
            raise ValueError(f'Block cache identity mismatch (config/algorithm changed): {path}')
        if sha(path) != meta['sha256']:
            raise ValueError(f'Block cache checksum mismatch: {path}')
        z = np.load(path)
        return {k: z[k] for k in z.files}
    m = margin_cells(margin_m)
    left, top = block_origin(bx, by)
    dem, sources = dem_grid(variant, left - m * RES, top + m * RES, BLOCK + 2 * m)
    rasters = terrain_rasters(dem)
    core = {k: v[m:m + BLOCK, m:m + BLOCK] for k, v in rasters.items()}
    guard(path.parent)
    tmp = path.with_name(path.stem + '.tmp.npz')
    np.savez_compressed(tmp, **core)
    tmp.replace(path)
    write_json(path.with_suffix('.json'), {'identity': identity, 'variant': variant, 'bx': int(bx), 'by': int(by),
                                           'left': left, 'top': top, 'sources': sources, 'sha256': sha(path),
                                           'window_nodata_cells': int(np.isnan(dem).sum())})
    return core


@lru_cache(maxsize=24)
def _block(variant, bx, by):
    return compute_block(variant, bx, by)


def sample(variant: str, x_m, y_m) -> pd.DataFrame:
    """TERRAIN values of the 30 m cells containing the points (EPSG:31287 metres)."""
    x_m, y_m = np.asarray(x_m, float), np.asarray(y_m, float)
    out = np.full((len(x_m), len(TERRAIN)), np.nan, dtype='float32')
    bx, by = block_of(x_m, y_m)
    for key in sorted(set(zip(bx.tolist(), by.tolist()))):
        idx = np.flatnonzero((bx == key[0]) & (by == key[1]))
        left, top = block_origin(*key)
        cols = np.floor((x_m[idx] - left) / RES).astype(int)
        rows = np.floor((top - y_m[idx]) / RES).astype(int)
        if (rows < 0).any() or (cols < 0).any() or (rows >= BLOCK).any() or (cols >= BLOCK).any():
            raise ValueError('Point outside its block')
        rasters = _block(variant, *key)
        for j, name in enumerate(TERRAIN):
            out[idx, j] = rasters[name][rows, cols]
    return pd.DataFrame(out, columns=TERRAIN)
