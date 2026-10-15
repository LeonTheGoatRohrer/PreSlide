"""Interpretable change features: spectral-index differences summarised in a core box and a surrounding ring.

All statistics are computed as full maps with box filters, so the same code scores a centred known-event patch
(value at the centre pixel) and every position of a sliding-window discovery scan.

satellite-0.3: in discovery/validation mode the valid mask can be buffered (`cloud_buffer_m`) around every
cloud-like SCL pixel and NDSI-snow pixel of either image, so that no scored position sits on a cloud, haze or
shadow edge. The training table is built without the buffer (see config discovery.cloud_buffer_note)."""
import numpy as np
from scipy.ndimage import uniform_filter, distance_transform_edt

from .imagery import REFLECTANCE_BANDS, CLOUD, SNOW, INVALID, ndsi_snow
from .paths import config

B = {name: i for i, name in enumerate(REFLECTANCE_BANDS)}


def indices(refl):
    """Dictionary of spectral indices from a (6, n, n) reflectance stack."""
    blue, green, red, nir, swir16, swir22 = (refl[B[k]] for k in REFLECTANCE_BANDS)

    def ratio(num, den):
        with np.errstate(divide='ignore', invalid='ignore'):
            out = num / den
        out[~np.isfinite(out)] = np.nan
        return out

    return {'ndvi': ratio(nir - red, nir + red),
            'nbr': ratio(nir - swir22, nir + swir22),
            'bsi': ratio((swir16 + red) - (nir + blue), (swir16 + red) + (nir + blue)),
            'ndwi': ratio(green - nir, green + nir),
            'brightness': (blue + green + red) / 3.0}


def cloud_like_mask(refl, scl, classes, with_ndsi_snow=True):
    """Pixels that are cloud, shadow, cirrus, snow, dark or unclassified by SCL, or snow by NDSI (either is enough)."""
    bad = np.isin(scl, list(classes))
    if with_ndsi_snow:
        bad = bad | ndsi_snow(refl[B['green']], refl[B['swir16']], refl[B['nir']])
    return bad


def buffer_mask(bad, buffer_px):
    """True within `buffer_px` (Euclidean pixel distance, inclusive) of any True pixel of `bad`."""
    if buffer_px <= 0 or not bad.any():
        return bad.copy()
    return distance_transform_edt(~bad) <= buffer_px


def valid_mask(refl, scl, buffer_px=0, buffer_classes=None, buffer_ndsi_snow=True):
    """Usable pixels of one acquisition: finite reflectance, not cloud/snow/invalid by SCL, not NDSI snow.
    With `buffer_px` > 0 every pixel within that distance of a cloud-like pixel (`buffer_classes`, default the
    discovery classes 2, 3, 7, 8, 9, 10, 11) or an NDSI-snow pixel is removed as well."""
    bad = np.isin(scl, list(CLOUD | SNOW | INVALID))
    snow = ndsi_snow(refl[B['green']], refl[B['swir16']], refl[B['nir']])
    valid = np.isfinite(refl).all(axis=0) & ~bad & ~snow
    if buffer_px > 0:
        classes = buffer_classes if buffer_classes is not None else config()['discovery']['cloud_buffer_scl_classes']
        valid &= ~buffer_mask(cloud_like_mask(refl, scl, classes, buffer_ndsi_snow), buffer_px)
    return valid


def _box_sum(a, size):
    return uniform_filter(a, size=size, mode='constant', cval=0.0) * (size * size)


def box_stats(values, valid, core_px, big_px, small_px=None):
    """NaN-aware core mean/std/count and ring mean/count for every pixel position (ring = big box minus core box).
    With `small_px`, also the mean of a smaller central box (small slides occupy few pixels of a 320 m core)."""
    v = np.where(valid, values, 0.0).astype(np.float64)
    w = valid.astype(np.float64)
    s_c, s_b = _box_sum(v, core_px), _box_sum(v, big_px)
    q_c = _box_sum(v * v, core_px)
    n_c, n_b = _box_sum(w, core_px), _box_sum(w, big_px)
    n_r, s_r = n_b - n_c, s_b - s_c
    with np.errstate(divide='ignore', invalid='ignore'):
        core_mean = np.where(n_c > 0, s_c / n_c, np.nan)
        core_std = np.sqrt(np.maximum(np.where(n_c > 1, q_c / n_c - core_mean ** 2, np.nan), 0.0))
        ring_mean = np.where(n_r > 0, s_r / n_r, np.nan)
        out = {'core_mean': core_mean, 'core_std': core_std, 'ring_mean': ring_mean, 'core_n': n_c, 'ring_n': n_r}
        if small_px:
            s_s, n_s = _box_sum(v, small_px), _box_sum(w, small_px)
            out['small_mean'] = np.where(n_s > 0, s_s / n_s, np.nan)
            out['small_n'] = n_s
    return out


def buffer_px_for(cloud_buffer_m, res_m):
    """Buffer radius in pixels (rounded up so that the metre radius is never under-covered); 0 disables it."""
    return int(np.ceil(cloud_buffer_m / res_m)) if cloud_buffer_m else 0


def pair_valid_mask(before, after, scl_before, scl_after, cloud_buffer_m=0, res_m=10.0, dcfg=None):
    """Valid mask of a before/after pair; with `cloud_buffer_m` > 0 the buffered mask of either image is applied.
    Returns (valid, masked_by_buffer_fraction) where the fraction counts pixels valid without the buffer but
    removed by it (relative to all patch pixels)."""
    plain = valid_mask(before, scl_before) & valid_mask(after, scl_after)
    px = buffer_px_for(cloud_buffer_m, res_m)
    if px <= 0:
        return plain, 0.0
    dcfg = dcfg or config()['discovery']
    classes, with_snow = dcfg['cloud_buffer_scl_classes'], dcfg.get('cloud_buffer_ndsi_snow', True)
    valid = valid_mask(before, scl_before, px, classes, with_snow) & valid_mask(after, scl_after, px, classes, with_snow)
    return valid, float((plain & ~valid).mean())


def feature_maps(before, after, scl_before, scl_after, res_m=10.0, cloud_buffer_m=0):
    """Per-pixel maps of all model features for a before/after pair (dict name -> (n, n) array).
    `cloud_buffer_m` > 0 applies the satellite-0.3 buffered mask (discovery and validation only; the training table
    is built with 0)."""
    cfg = config()
    core_px = int(round(cfg['patch']['core_m'] / res_m))
    big_px = int(round(cfg['patch']['medium_m'] / res_m))
    small_px = int(round(cfg['patch']['small_m'] / res_m))
    thresholds = cfg['features']['change_thresholds']
    valid, _ = pair_valid_mask(before, after, scl_before, scl_after, cloud_buffer_m, res_m, cfg['discovery'])
    ib, ia = indices(before), indices(after)
    out = {}
    for name in cfg['features']['indices']:
        delta = ia[name] - ib[name]
        v = valid & np.isfinite(delta)
        st = box_stats(delta, v, core_px, big_px, small_px)
        out[f'd_{name}_core_mean'] = st['core_mean']
        out[f'd_{name}_core_std'] = st['core_std']
        out[f'd_{name}_ring_mean'] = st['ring_mean']
        out[f'd_{name}_contrast'] = st['core_mean'] - st['ring_mean']
        out[f'd_{name}_small_contrast'] = st['small_mean'] - st['ring_mean']
        if name in thresholds:
            t = thresholds[name]
            hit = (delta < t) if t < 0 else (delta > t)
            fr = box_stats(hit.astype(np.float64), v, core_px, big_px, small_px)
            out[f'd_{name}_core_frac'] = fr['core_mean']
            out[f'd_{name}_small_frac'] = fr['small_mean']
            out[f'd_{name}_ring_frac'] = fr['ring_mean']
            out[f'd_{name}_frac_contrast'] = fr['core_mean'] - fr['ring_mean']
    for name in cfg['features']['before_state']:
        st = box_stats(ib[name], valid & np.isfinite(ib[name]), core_px, big_px)
        out[f'before_{name}_core_mean'] = st['core_mean']
        out[f'before_{name}_contrast'] = st['core_mean'] - st['ring_mean']
    cnt = box_stats(np.ones_like(valid, dtype=np.float64), np.ones_like(valid, dtype=bool), core_px, big_px)
    vv = box_stats(np.ones_like(valid, dtype=np.float64), valid, core_px, big_px)
    out['valid_core_frac'] = vv['core_n'] / cnt['core_n']
    out['valid_ring_frac'] = vv['ring_n'] / cnt['ring_n']
    return out


def scorable_mask(maps, dcfg):
    """Positions whose core and ring keep enough valid pixels (after buffering) to be scored at all."""
    return ((maps['valid_core_frac'] >= dcfg['scorable_min_valid_core_frac'])
            & (maps['valid_ring_frac'] >= dcfg['scorable_min_valid_ring_frac']))


def features_at(maps, row, col):
    return {k: float(v[row, col]) for k, v in maps.items()}


def model_feature_names(names):
    """Features a detector may use: everything except validity fractions."""
    return [n for n in names if not n.startswith('valid_')]


def ring_only_names(names):
    return [n for n in names if '_ring_' in n]
