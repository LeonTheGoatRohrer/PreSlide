import numpy as np

from preslide.satellite import change04 as C
from preslide.satellite.paths import config as base_config

N, RES = 128, 10.0
CFG04, BASE = C.config04(), base_config()


def scene(ndvi_map, rng=None):
    """6-band reflectance stack (blue, green, red, nir, swir16, swir22) with the requested NDVI (red fixed)."""
    red = np.full((N, N), 0.05)
    nir = red * (1 + ndvi_map) / (1 - ndvi_map)
    stack = np.stack([np.full((N, N), 0.03), np.full((N, N), 0.06), red, nir, np.full((N, N), 0.12), np.full((N, N), 0.08)])
    return stack


def maps(before, after, ref=None, confirm=None):
    ok = np.ones((N, N), bool)
    return C.norm_maps(ref, before, after, confirm, ok, ok, ok, ok, RES, CFG04, BASE)


def noise(seed, sd=0.03):
    return np.random.default_rng(seed).normal(0, sd, (N, N))


def test_uniform_harvest_gives_small_z_but_local_scar_gives_large_negative_z():
    base = 0.7 + noise(1)
    ref = scene(np.clip(base + noise(2), 0.05, 0.95))
    before = scene(np.clip(base, 0.05, 0.95))
    uniform = scene(np.clip(base - 0.3, 0.05, 0.95))             # whole scene loses NDVI (harvest / season)
    scar_ndvi = base.copy()
    scar_ndvi[60:68, 60:68] -= 0.5                                 # 80 m scar in the centre
    scar = scene(np.clip(scar_ndvi, 0.05, 0.95))
    zu, zs = maps(before, uniform, ref)['z_small_ndvi'][64, 64], maps(before, scar, ref)['z_small_ndvi'][64, 64]
    assert abs(zu) < 1.0 and zs < -4.0


def test_missing_reference_or_confirm_gives_nan_not_values():
    before, after = scene(np.full((N, N), 0.7)), scene(np.full((N, N), 0.4))
    m = maps(before, after)
    assert all(np.isnan(m[k]).all() for k in C.NORM_FEATURES + C.PERSIST_FEATURES)


def test_persistence_requires_same_sign_in_the_confirm_image_and_regrowth_is_detected():
    base = np.full((N, N), 0.7)
    ref, before = scene(base), scene(base)
    lost = base.copy()
    lost[60:68, 60:68] -= 0.5
    after = scene(lost)
    persist = maps(before, after, ref, confirm=scene(lost))
    regrow = maps(before, after, ref, confirm=scene(base))        # vegetation back in the confirm image
    over = base.copy()
    over[60:68, 60:68] += 0.2                                       # opposite-sign change in the confirm image
    opposite = maps(before, after, ref, confirm=scene(over))
    assert opposite['persistence_ndvi'][64, 64] == 0.0
    assert persist['persistence_ndvi'][64, 64] < -0.1 and persist['regrowth_ndvi'][64, 64] == 0.0
    assert regrow['persistence_ndvi'][64, 64] == 0.0 and regrow['regrowth_ndvi'][64, 64] > 0.1


def test_cloud_buffer_distance_and_filters():
    mask = np.zeros((N, N), bool)
    mask[10, 10] = True
    d = C.distance_to_mask_m(mask, RES)
    assert d[10, 10] == 0 and abs(d[10, 20] - 100.0) < 1e-6 and np.isinf(C.distance_to_mask_m(np.zeros((4, 4), bool), RES)).all()
    filt = CFG04['filters']
    water = np.zeros((N, N))
    water[:, 100:] = 0.5
    peaks = [(3.0, 64, 64), (2.5, 64, 105), (2.0, 10, 15), (1.5, 90, 30), (1.0, 50, 50)]
    slopes = {(64, 64): 20.0, (64, 105): 20.0, (10, 15): 20.0, (90, 30): 5.0, (50, 50): 8.0}      # (50, 50): exactly the threshold
    kept, reasons = C.filter_peaks(peaks, lambda r, c: slopes[(r, c)], water, d, filt)
    assert [(r, c) for _, r, c in kept] == [(64, 64), (50, 50)] and reasons == {'slope': 1, 'water': 1, 'cloud_buffer': 1}


def test_registered_features_match_the_config_text():
    assert len(C.NORM_FEATURES) == 12 and len(C.PERSIST_FEATURES) == 8
    assert CFG04['comparisons_counted'] == 6 and CFG04['filters']['min_slope_deg'] == 8
