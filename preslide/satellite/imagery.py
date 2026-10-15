"""Event-centred 10 m grids, windowed Sentinel-2 COG reads, scene-classification quality metrics and patch caching."""
import hashlib
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

from ..common import write_json, read_json
from .paths import SAT_DATA, CA_BUNDLE, guard, config

REFLECTANCE_BANDS = ('blue', 'green', 'red', 'nir', 'swir16', 'swir22')
CLOUD, SNOW, INVALID = {3, 8, 9, 10}, {11}, {0, 1}


def gdal_env():
    opts = {'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR', 'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': '.tif',
            'GDAL_HTTP_MAX_RETRY': '4', 'GDAL_HTTP_RETRY_DELAY': '5', 'VSI_CACHE': 'TRUE',
            'GDAL_HTTP_MERGE_CONSECUTIVE_RANGES': 'YES', 'GDAL_HTTP_MULTIRANGE': 'YES'}
    if CA_BUNDLE.exists():
        opts['GDAL_CURL_CA_BUNDLE'] = str(CA_BUNDLE)
    return rasterio.Env(**opts)


def utm_epsg(lon):
    return 32632 if lon < 12.0 else 32633


@dataclass(frozen=True)
class Grid:
    epsg: int
    x0: float          # left edge
    y1: float          # top edge
    res: float
    n: int             # pixels per side
    cx: float          # event position in grid CRS
    cy: float

    @property
    def transform(self):
        return from_origin(self.x0, self.y1, self.res, self.res)

    @property
    def crs(self):
        return f'EPSG:{self.epsg}'

    @property
    def bounds(self):
        return (self.x0, self.y1 - self.n * self.res, self.x0 + self.n * self.res, self.y1)

    def centre_pixel(self):
        """(row, col) of the pixel containing the event position."""
        return int((self.y1 - self.cy) // self.res), int((self.cx - self.x0) // self.res)

    def to_dict(self):
        return asdict(self)


def event_grid(lon, lat, extent_m=None, res=None, epsg=None):
    pcfg = config()['patch']
    res = res or pcfg['resolution_m']
    extent_m = extent_m or pcfg['extent_m']
    epsg = epsg or utm_epsg(lon)
    x, y = Transformer.from_crs('EPSG:4326', f'EPSG:{epsg}', always_xy=True).transform(lon, lat)
    n = int(round(extent_m / res))
    half = n // 2
    x0 = math.floor(x / res) * res - half * res
    y1 = math.ceil(y / res) * res + half * res
    return Grid(epsg, float(x0), float(y1), float(res), n, float(x), float(y))


def _read_on_grid(href, grid, resampling, env_open=True):
    with rasterio.open(href) as src:
        with WarpedVRT(src, crs=grid.crs, transform=grid.transform, width=grid.n, height=grid.n,
                       resampling=resampling, nodata=0, src_nodata=0) as vrt:
            return vrt.read(1)


def read_scl(item, grid):
    with gdal_env():
        return _read_on_grid(item['assets']['scl']['href'], grid, Resampling.nearest).astype(np.uint8)


def scale_offset(item, band):
    """(scale, offset) converting DN to reflectance. The offset depends on the collection, not on the advertised
    raster:bands value: Earth Search's sentinel-2-l2a COGs are stored without the BOA_ADD_OFFSET for every baseline,
    the Collection-1 COGs with it (verified on vegetation DN medians, see config/satellite.json)."""
    a = item['assets'][band]
    if a['scale'] is None:
        raise RuntimeError(f"{item['id']} {band}: STAC asset lacks raster:bands scale; refusing to guess reflectance")
    offsets = config()['stac']['offset_by_collection']
    if item['collection'] not in offsets:
        raise RuntimeError(f"{item['id']}: no verified reflectance offset for collection {item['collection']}")
    return a['scale'], offsets[item['collection']]


def check_radiometry(refl, scl, item):
    """Refuse an acquisition whose SCL-vegetation green reflectance is implausible (wrong offset would shift it by 0.1)."""
    veg = scl == 4
    if veg.sum() >= 50:
        med = float(np.nanmedian(refl[REFLECTANCE_BANDS.index('green')][veg]))
        if not 0.01 <= med <= 0.2:
            raise RuntimeError(f"{item['id']}: vegetation green reflectance median {med:.3f} outside [0.01, 0.2]; radiometric offset inconsistent")


def read_reflectance(item, grid):
    """float32 (6, n, n) surface reflectance (NaN = nodata) and uint8 SCL on the grid."""
    out = np.full((len(REFLECTANCE_BANDS), grid.n, grid.n), np.nan, dtype=np.float32)
    for band in REFLECTANCE_BANDS:
        scale_offset(item, band)

    def read_band(band):
        with gdal_env():
            if band == 'scl':
                return _read_on_grid(item['assets']['scl']['href'], grid, Resampling.nearest).astype(np.uint8)
            return read_band_on_grid(item, band, grid)

    with ThreadPoolExecutor(max_workers=2) as ex:     # independent HTTP range reads; each thread opens its own dataset (more threads x workers segfaulted GDAL)
        results = list(ex.map(read_band, list(REFLECTANCE_BANDS) + ['scl']))
    for i in range(len(REFLECTANCE_BANDS)):
        out[i] = results[i]
    check_radiometry(out, results[-1], item)
    return out, results[-1]


def region_masks(grid, core_m=None, medium_m=None):
    pcfg = config()['patch']
    core_m, medium_m = core_m or pcfg['core_m'], medium_m or pcfg['medium_m']
    r, c = grid.centre_pixel()
    rows, cols = np.ogrid[:grid.n, :grid.n]
    core = int(round(core_m / grid.res / 2))
    med = int(round(medium_m / grid.res / 2))
    core_mask = (abs(rows - r) < core) & (abs(cols - c) < core)
    medium_mask = (abs(rows - r) < med) & (abs(cols - c) < med)
    return core_mask, medium_mask


def scl_metrics(scl, mask=None, refl=None):
    """Fractions of cloud/shadow, snow and invalid pixels inside `mask` (whole array if None)."""
    sel = scl if mask is None else scl[mask]
    n = sel.size
    invalid = np.isin(sel, list(INVALID))
    if refl is not None:
        nodata = np.isnan(refl).any(axis=0)
        invalid |= (nodata if mask is None else nodata[mask])
    return {'cloud': float(np.isin(sel, list(CLOUD)).mean()) if n else 1.0,
            'snow': float(np.isin(sel, list(SNOW)).mean()) if n else 1.0,
            'invalid': float(invalid.mean()) if n else 1.0,
            'water': float((sel == 6).mean()) if n else 0.0,
            'pixels': int(n)}


def quality(scl, grid, refl=None):
    core, medium = region_masks(grid)
    q = {'core': scl_metrics(scl, core, refl), 'medium': scl_metrics(scl, medium, refl), 'patch': scl_metrics(scl, None, refl)}
    if refl is not None:
        snow = ndsi_snow(refl[B_GREEN], refl[B_SWIR16], refl[B_NIR])
        for name, mask in (('core', core), ('medium', medium), ('patch', None)):
            sel = snow if mask is None else snow[mask]
            q[name]['snow_ndsi'] = float(np.nanmean(sel)) if sel.size else 1.0
    return q


B_GREEN, B_NIR, B_SWIR16 = REFLECTANCE_BANDS.index('green'), REFLECTANCE_BANDS.index('nir'), REFLECTANCE_BANDS.index('swir16')


def ndsi_snow(green, swir16, nir, el=None):
    """Boolean snow mask from the normalised-difference snow index (NaN inputs -> False)."""
    el = el or config()['eligibility']['ndsi_snow']
    with np.errstate(divide='ignore', invalid='ignore'):
        ndsi = (green - swir16) / (green + swir16)
    return (np.nan_to_num(ndsi, nan=-1.0) > el['ndsi_min']) & (np.nan_to_num(nir, nan=0.0) > el['nir_min'])


def usable(q, el=None):
    """Apply the configured local cloud/snow/validity thresholds; returns (ok, reason)."""
    el = el or config()['eligibility']
    c, m = q['core'], q['medium']
    if c['invalid'] > 1 - el['core_valid_min']:
        return False, 'core_invalid'
    if c['cloud'] > el['core_cloud_max']:
        return False, 'core_cloud'
    if c['snow'] > el['core_snow_max']:
        return False, 'core_snow'
    if m['invalid'] > 1 - el['window_valid_min']:
        return False, 'window_invalid'
    if m['cloud'] > el['window_cloud_max']:
        return False, 'window_cloud'
    if m['snow'] > el['window_snow_max']:
        return False, 'window_snow'
    if c.get('snow_ndsi', 0.0) > el['core_snow_max']:
        return False, 'core_snow_ndsi'
    if m.get('snow_ndsi', 0.0) > el['window_snow_max']:
        return False, 'window_snow_ndsi'
    return True, ''


# ---------- caching ----------

def sample_dir(sample_id):
    return guard(SAT_DATA / 'samples' / sample_id)


def quicklook(sample_id, item, grid):
    """Cached SCL-only quality metrics for one item on one grid (cheap: a single 20 m band window)."""
    path = sample_dir(sample_id) / 'quicklook' / f"{item['id']}.json"
    q = read_json(path) if path.exists() else None
    if q is None:
        scl = read_scl(item, grid)
        q = quality(scl, grid)
        q.update({'item_id': item['id'], 'collection': item['collection'], 'datetime': item['datetime'],
                  'grid': grid.to_dict(), 'retrieved_at': datetime.now(timezone.utc).isoformat()})
    if 'snow_ndsi' not in q['core'] and usable(q)[0]:
        # Second stage, only for SCL-clean candidates: NDSI snow test from green, SWIR1 and NIR windows.
        snow = ndsi_snow(*(read_band_on_grid(item, b, grid) for b in ('green', 'swir16', 'nir')))
        core, medium = region_masks(grid)
        for name, mask in (('core', core), ('medium', medium), ('patch', None)):
            sel = snow if mask is None else snow[mask]
            q[name]['snow_ndsi'] = float(sel.mean()) if sel.size else 1.0
    guard(path.parent)
    write_json(path, q)
    return q


def read_band_on_grid(item, band, grid):
    a = item['assets'][band]
    scale, offset = scale_offset(item, band)
    with gdal_env():
        dn = _read_on_grid(a['href'], grid, Resampling.bilinear).astype(np.float32)
    refl = dn * scale + offset
    refl[dn == a['nodata']] = np.nan
    return refl


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_paths(sample_id, item_id):
    d = sample_dir(sample_id) / 'patches'
    return d / f'{item_id}_refl.tif', d / f'{item_id}_scl.tif', d / f'{item_id}.json'


def fetch_patch(sample_id, item, grid):
    """Download (once) and return (refl, scl, meta) for one acquisition on the sample grid. Stored as deflated GeoTIFFs."""
    refl_path, scl_path, meta_path = patch_paths(sample_id, item['id'])
    if meta_path.exists():
        meta = read_json(meta_path)
        if _sha(refl_path) != meta['sha256_refl'] or _sha(scl_path) != meta['sha256_scl']:
            raise RuntimeError(f'patch cache corrupted: {meta_path}')
        with rasterio.open(refl_path) as r, rasterio.open(scl_path) as s:
            return r.read().astype(np.float32), s.read(1), meta
    refl, scl = read_reflectance(item, grid)
    guard(refl_path.parent)
    profile = {'driver': 'GTiff', 'height': grid.n, 'width': grid.n, 'crs': grid.crs, 'transform': grid.transform,
               'compress': 'deflate', 'predictor': 2, 'tiled': False}
    with rasterio.open(refl_path, 'w', count=len(REFLECTANCE_BANDS), dtype='float32', nodata=np.nan, **profile) as dst:
        dst.write(refl)
        dst.descriptions = REFLECTANCE_BANDS
    with rasterio.open(scl_path, 'w', count=1, dtype='uint8', nodata=0, **profile) as dst:
        dst.write(scl, 1)
    meta = {'item_id': item['id'], 'collection': item['collection'], 'datetime': item['datetime'], 'platform': item['platform'],
            'processing_baseline': item['processing_baseline'], 'epsg_source': item['epsg'], 'grid_code': item['grid_code'],
            'assets': {k: v['href'] for k, v in item['assets'].items()},
            'reflectance_rule': 'DN * scale + offset_by_collection (config/satellite.json); DN 0 -> NaN',
            'scale_offset': {k: list(scale_offset(item, k)) for k in REFLECTANCE_BANDS},
            'advertised_offset': {k: v['offset'] for k, v in item['assets'].items() if k != 'scl'},
            'grid': grid.to_dict(), 'bands': list(REFLECTANCE_BANDS), 'quality': quality(scl, grid, refl),
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'sha256_refl': _sha(refl_path), 'sha256_scl': _sha(scl_path)}
    write_json(meta_path, meta)
    return refl, scl, meta


def coregistration_shift(before_nir, after_nir, valid):
    """Integer-pixel shift (dx, dy) of `after` relative to `before` by phase correlation of the NIR band.

    Vegetation change biases this slightly; it is a QA indicator, not a correction. Returns (dx, dy, peak_ratio)."""
    a = np.where(valid, before_nir, np.nan)
    b = np.where(valid, after_nir, np.nan)
    a = np.nan_to_num(a - np.nanmean(a))
    b = np.nan_to_num(b - np.nanmean(b))
    fa, fb = np.fft.fft2(a), np.fft.fft2(b)
    cross = fa * np.conj(fb)
    cross /= np.abs(cross) + 1e-12
    corr = np.real(np.fft.ifft2(cross))
    peak = np.unravel_index(np.argmax(corr), corr.shape)
    dy, dx = peak
    n = corr.shape[0]
    dy = dy - n if dy > n // 2 else dy
    dx = dx - n if dx > n // 2 else dx
    ratio = float(corr.max() / (corr.std() + 1e-12))     # peak sharpness; a clean shift gives a ratio far above ~5
    return int(dx), int(dy), ratio
