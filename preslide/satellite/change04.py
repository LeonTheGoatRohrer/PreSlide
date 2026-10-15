"""satellite-0.4 (config/satellite_0_4.json): normalised change, persistence and filtered rediscovery.

Pure feature maps (``norm_maps``) are separated from the I/O stages so they can be tested with synthetic arrays.
"""
import hashlib

import numpy as np
from scipy.ndimage import distance_transform_edt

from ..common import read_json
from ..sources import ROOT
from .features import B, _box_sum, box_stats, indices
from .imagery import CLOUD, INVALID, SNOW, ndsi_snow

CONFIG04 = ROOT / 'config/satellite_0_4.json'
REGISTRATION04 = ROOT / 'reports/satellite_0_4/PREREGISTRATION.json'
IDX = ('ndvi', 'nbr', 'bsi', 'brightness')
LOSS_SIGN = {'ndvi': -1.0, 'nbr': -1.0, 'bsi': 1.0, 'brightness': 1.0}   # direction of a scar-like change
NORM_FEATURES = [f'{p}_{i}' for p in ('z_small', 'z_core', 'frac_z_below') for i in IDX]
PERSIST_FEATURES = [f'{p}_{i}' for p in ('persistence', 'regrowth') for i in IDX]


def config04() -> dict:
    """Registered satellite-0.4 configuration; refuses to run if it changed after registration."""
    digest = hashlib.sha256(CONFIG04.read_bytes()).hexdigest()
    if REGISTRATION04.exists() and read_json(REGISTRATION04)['config_sha256'] != digest:
        raise RuntimeError('config/satellite_0_4.json changed after registration')
    cfg = read_json(CONFIG04)
    if hashlib.sha256((ROOT / 'config/satellite.json').read_bytes()).hexdigest() != cfg['inputs']['base_config_sha256']:
        raise RuntimeError('config/satellite.json changed')
    return cfg


def ring_std(values, valid, core_px, big_px):
    """NaN-aware std of `values` in the ring (big box minus core box) for every window position."""
    v = np.where(valid, values, 0.0).astype(np.float64)
    w = valid.astype(np.float64)
    s = _box_sum(v, big_px) - _box_sum(v, core_px)
    q = _box_sum(v * v, big_px) - _box_sum(v * v, core_px)
    n = _box_sum(w, big_px) - _box_sum(w, core_px)
    with np.errstate(divide='ignore', invalid='ignore'):
        mean = np.where(n > 1, s / n, np.nan)
        var = np.where(n > 1, q / n - mean ** 2, np.nan)
    return np.sqrt(np.maximum(var, 0.0))


def norm_maps(ref, before, after, confirm, valid_ref, valid_before, valid_after, valid_confirm, res_m, cfg04, cfg_base):
    """Normalised-change and persistence maps. Any of `ref` / `confirm` (reflectance stacks) may be None: the
    corresponding features are then all-NaN maps (never invented)."""
    core_px = int(round(cfg_base['patch']['core_m'] / res_m))
    big_px = int(round(cfg_base['patch']['medium_m'] / res_m))
    small_px = int(round(cfg_base['patch']['small_m'] / res_m))
    floor = cfg04['normalisation']['sigma_floor']
    ib, ia = indices(before), indices(after)
    ir = indices(ref) if ref is not None else None
    ic = indices(confirm) if confirm is not None else None
    shape = valid_before.shape
    nan = np.full(shape, np.nan)
    out = {}
    for name in IDX:
        sign = LOSS_SIGN[name]
        delta = ia[name] - ib[name]
        v_ab = valid_before & valid_after & np.isfinite(delta)
        st = box_stats(delta, v_ab, core_px, big_px, small_px)
        small_contrast = st['small_mean'] - st['ring_mean']
        core_contrast = st['core_mean'] - st['ring_mean']
        if ir is not None:
            pre = ib[name] - ir[name]
            v_pre = valid_before & valid_ref & np.isfinite(pre)
            if v_pre.sum() < 0.5 * pre.size:
                ir = None                                         # insufficient valid reference pixels
        if ir is not None:
            core_sd = np.sqrt(np.maximum(box_stats(pre ** 2, v_pre, core_px, big_px)['core_mean'] - box_stats(pre, v_pre, core_px, big_px)['core_mean'] ** 2, 0.0))
            sigma_core = np.maximum(core_sd, floor)
            sigma_ring = np.maximum(ring_std(pre, v_pre, core_px, big_px), floor)
            vals = pre[v_pre]
            sigma_scene = max(1.4826 * float(np.median(np.abs(vals - np.median(vals)))), floor)
            z = (delta - np.nanmedian(delta[v_ab])) / sigma_scene * (-sign)
            hit = (z < -2).astype(np.float64)
            out[f'z_small_{name}'] = small_contrast / sigma_ring
            out[f'z_core_{name}'] = core_contrast / sigma_core
            out[f'frac_z_below_{name}'] = box_stats(hit, v_ab, core_px, big_px)['core_mean']
        else:
            out[f'z_small_{name}'] = out[f'z_core_{name}'] = out[f'frac_z_below_{name}'] = nan
        if ic is not None:
            d_c = ic[name] - ib[name]
            v_c = valid_before & valid_confirm & np.isfinite(d_c)
            c1 = (lambda s: s['small_mean'] - s['ring_mean'])(box_stats(d_c, v_c, core_px, big_px, small_px))
            same = np.sign(small_contrast) == np.sign(c1)
            out[f'persistence_{name}'] = np.where(same, np.sign(small_contrast) * np.minimum(np.abs(small_contrast), np.abs(c1)), 0.0)
            d_r = ic[name] - ia[name]
            v_r = valid_after & valid_confirm & np.isfinite(d_r)
            out[f'regrowth_{name}'] = (lambda s: s['small_mean'] - s['ring_mean'])(box_stats(d_r, v_r, core_px, big_px, small_px))
            out[f'persistence_{name}'] = np.where(np.isfinite(small_contrast) & np.isfinite(c1), out[f'persistence_{name}'], np.nan)
        else:
            out[f'persistence_{name}'] = out[f'regrowth_{name}'] = nan
    return out


def cloud_snow_mask(refl_b, scl_b, refl_a, scl_a, classes):
    """True where either primary scene has cloud-like, snow or invalid pixels (whole patch)."""
    def one(refl, scl):
        snow = ndsi_snow(refl[B['green']], refl[B['swir16']], refl[B['nir']])
        return np.isin(scl, list(classes)) | snow | np.isin(scl, list(CLOUD | SNOW | INVALID)) | ~np.isfinite(refl).all(axis=0)
    return one(refl_b, scl_b) | one(refl_a, scl_a)


def distance_to_mask_m(mask, res_m):
    """Metres from every pixel to the nearest True pixel of `mask` (inf when the mask is empty)."""
    if not mask.any():
        return np.full(mask.shape, np.inf)
    return distance_transform_edt(~mask) * res_m


def water_core_share(scl_b, scl_a, core_px, water_class):
    """Share of 320 m core pixels labelled water in either primary scene, for every window position."""
    water = (np.asarray(scl_b) == water_class) | (np.asarray(scl_a) == water_class)
    return box_stats(water.astype(np.float64), np.ones(water.shape, bool), core_px, core_px + 2)['core_mean']


def filter_peaks(peaks, slope_at, water_share, cloud_distance_m, filters):
    """Split ranked peaks (score, row, col) into kept and a Counter-like dict of removal reasons."""
    kept, reasons = [], {'slope': 0, 'water': 0, 'cloud_buffer': 0}
    for p in peaks:
        _, r, c = p
        slope = slope_at(r, c)
        if not np.isfinite(slope) or slope < filters['min_slope_deg']:
            reasons['slope'] += 1
        elif water_share[r, c] >= filters['max_water_core_share']:
            reasons['water'] += 1
        elif cloud_distance_m[r, c] < filters['cloud_buffer_m']:
            reasons['cloud_buffer'] += 1
        else:
            kept.append(p)
    return kept, reasons

