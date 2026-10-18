"""wirkungskette_gebietstest_v01 tests (registered as wirkungskette_v02): feature fidelity to frozen V0.4, capture metric, bootstrap, land-cover vintage, area rule,
registration guard. Synthetic geometries/arrays are unit-test fixtures only; they never enter data/ or reports/."""
import json
import math

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from preslide.terrain import PROJECT
from preslide.wirkungskette import gebiete as G
from preslide.wirkungskette.paths import CONFIG_GT, REPORT_GT


# ---------- registration ----------

def test_config_matches_registration():
    reg = json.loads((REPORT_GT / 'PREREGISTRATION.json').read_text(encoding='utf-8'))
    import hashlib
    assert hashlib.sha256(CONFIG_GT.read_bytes()).hexdigest() == reg['config_sha256']
    assert G.config()['version'] == 'wirkungskette_v02'


# ---------- land-cover vintage (imagery must end before the campaign year) ----------

@pytest.mark.parametrize('year,vintage', [(2002, 'CLC2000'), (2005, 'CLC2000'), (2007, 'CLC2000'), (2008, 'CLC2006'),
                                          (2009, 'CLC2006'), (2012, 'CLC2006'), (2013, 'CLC2012'), (2015, 'CLC2012')])
def test_land_cover_vintage_precedes_campaign(year, vintage):
    assert G.land_cover_vintage(year) == vintage
    imagery_end = {'CLC2000': 2001, 'CLC2006': 2007, 'CLC2012': 2012}[vintage]
    assert imagery_end < year


@pytest.mark.parametrize('year', [1999, 2001, 2019])
def test_land_cover_vintage_outside_rule_fails(year):
    with pytest.raises(ValueError):
        G.land_cover_vintage(year)


# ---------- capture metric ----------

def test_capture_uses_top_fraction_of_grid_and_misses_unassessable():
    grid = np.arange(100, dtype=float)                 # top 5 % = 95..99, top 20 % = 80..99
    events = np.array([99, 95, 94.9, 80, 79, np.nan])
    f05, c05 = G.capture_flags(grid, events, .05)
    f20, c20 = G.capture_flags(grid, events, .20)
    assert c05 == 95 and c20 == 80
    assert f05.tolist() == [True, True, False, False, False, False]
    assert f20.tolist() == [True, True, True, True, False, False]


def test_capture_of_random_events_is_near_area_share():
    rng = np.random.default_rng(1)
    grid = rng.normal(size=20000)
    events = rng.choice(grid, 5000)
    assert abs(G.capture_flags(grid, events, .2)[0].mean() - .2) < .02


def test_capture_ignores_nan_grid_cells():
    grid = np.array([np.nan] * 50 + list(range(10)), float)
    flags, cutoff = G.capture_flags(grid, np.array([9.0, 8.0]), .1)
    assert cutoff == 9 and flags.tolist() == [True, False]


# ---------- bootstrap ----------

def frame(n, cap_model, cap_slope, x0):
    rng = np.random.default_rng(int(x0))
    return pd.DataFrame({'x': x0 + rng.uniform(0, 8000, n), 'y': 390000 + rng.uniform(0, 8000, n),
                         'cap_model_05': rng.random(n) < cap_model, 'cap_model_20': rng.random(n) < cap_model,
                         'cap_slope_05': rng.random(n) < cap_slope, 'cap_slope_20': rng.random(n) < cap_slope}).astype(
        {'cap_model_05': float, 'cap_model_20': float, 'cap_slope_05': float, 'cap_slope_20': float})


def test_bootstrap_is_seeded_and_covers_area_weighted_mean():
    per = {'a': frame(200, .5, .2, 500000), 'b': frame(50, .4, .2, 600000), 'c': frame(80, .6, .25, 700000)}
    r1, r2 = G.bootstrap(per, 300, 7), G.bootstrap(per, 300, 7)
    assert r1 == r2
    mean = np.mean([f.cap_model_20.mean() for f in per.values()])
    assert r1['cap_model_20'][0] <= mean <= r1['cap_model_20'][1]
    assert r1['diff_20'][0] > 0                       # clearly better model in the fixture


def test_bootstrap_difference_straddles_zero_without_signal():
    per = {k: frame(150, .2, .2, x) for k, x in (('a', 500000), ('b', 600000), ('c', 700000), ('d', 800000))}
    lo, hi = G.bootstrap(per, 400, 3)['diff_20']
    assert lo < 0 < hi


def test_blocks_are_metric_2km():
    assert G.block_ids([500100, 501900, 502100], [390000, 390000, 390000], 2000) == ['250_195', '250_195', '251_195']


# ---------- area rule ----------

def test_area_takes_municipalities_with_enough_points():
    x0, y0 = 550000.0, 380000.0
    lau = [{'lau_id': 'A', 'name': 'A', 'geometry': box(x0, y0, x0 + 5000, y0 + 5000)},
           {'lau_id': 'B', 'name': 'B', 'geometry': box(x0 + 5000, y0, x0 + 10000, y0 + 5000)},
           {'lau_id': 'C', 'name': 'C', 'geometry': box(x0 + 20000, y0, x0 + 25000, y0 + 5000)}]
    pts = pd.DataFrame({'x': [x0 + 100 * i for i in range(1, 7)] + [x0 + 6000] * 4 + [x0 + 21000] * 5,
                        'y': [y0 + 1000] * 15})
    a = G.area_of(pts, lau, 5)
    assert [m['lau_id'] for m in a['municipalities']] == ['A', 'C']
    assert len(a['components']) == 2
    assert a['inside'].sum() == 11 and not a['inside'][6:10].any()


# ---------- feature fidelity to frozen V0.4 ----------

def test_static_features_from_dem_equal_frozen_v04_code():
    """Same Skadi window as preslide.v04.terrain.static_features -> identical feature values."""
    from preslide.v04 import terrain as T4
    lon, lat, day = 15.49683, 47.44533, '2016-07-25'
    cfg = {'terrain_resolution_m': 30, 'terrain_crs': 'EPSG:31287', 'control_max_distance_m': 1500}
    cx, cy = PROJECT.transform(lon, lat)
    rng = np.random.default_rng(4)
    samples = pd.DataFrame({'sample_id': [f's{i}' for i in range(40)], 'x': cx + rng.uniform(-1400, 1400, 40),
                            'y': cy + rng.uniform(-1400, 1400, 40)})
    try:
        ref, _ = T4.static_features({'longitude': lon, 'latitude': lat, 'event_day': day}, samples, cfg, margin_m=2000)
    except FileNotFoundError:
        pytest.skip('Skadi tile cache not available')
    dem, left, top, _ = T4.dem_window(lon, lat, 1500 + 300 + 2000, 30, 'EPSG:31287', day)
    mine, _ = G.static_features_from_dem(dem, left, top, 30.0, samples.x, samples.y)
    for col in ['profile_curvature', 'plan_curvature', 'roughness_tri', 'tpi_150m', 'tpi_500m', 'relative_position_500m',
                'log10_catchment_m2', 'twi', 'catchment_truncated']:
        np.testing.assert_allclose(mine[col].to_numpy(float), ref[col].to_numpy(float), equal_nan=True, err_msg=col)


def test_dem_rect_reproduces_v04_window():
    from preslide.v04 import terrain as T4
    lon, lat = 15.49683, 47.44533
    dem, left, top, _ = T4.dem_window(lon, lat, 1200, 30, 'EPSG:31287', '2016-07-25')
    mine = G.dem_rect(G.skadi_tile, left, top, dem.shape[0], dem.shape[1], 30.0, 'EPSG:31287')
    np.testing.assert_allclose(mine, dem, atol=1e-3)


def test_srtm_tile_is_cached_with_provenance_when_present():
    d = G.DATA_GT / 'cache/srtm'
    tiles = sorted(d.glob('*.json')) if d.exists() else []
    if not tiles:
        pytest.skip('no SRTM tile cached yet')
    meta = json.loads(tiles[0].read_text(encoding='utf-8'))
    assert meta['acquisition'].endswith('February 2000') and len(meta['sha256']) == 64
    assert math.isclose(tiles[0].with_suffix('.hgt').stat().st_size, 3601 * 3601 * 2)


def test_bootstrap_resamples_whole_areas():
    """Areas constant inside (all captured vs none): only area-level resampling creates spread."""
    a, b = frame(60, 1.0, 1.0, 500000), frame(60, 0.0, 0.0, 600000)
    lo, hi = G.bootstrap({'a': a, 'b': b}, 400, 5)['cap_model_20']
    assert lo == 0.0 and hi == 1.0


# ---------- demo areas ----------

def test_demo_config_overrides_only_own_blocks():
    from preslide.wirkungskette.paths import config as demo_config
    base, mb = demo_config('stanz'), demo_config('mittelberg')
    assert mb['demo']['id'] == 'mittelberg_2005' and mb['terrain']['dem'] == 'srtm'
    assert mb['review_points']['land_cover_vintage'] == 'CLC2000'
    assert mb['runout'] == base['runout'] and mb['infrastructure'] == base['infrastructure']
    assert mb['review_points']['classes'] == base['review_points']['classes']
    assert mb['review_points']['model_sha256'] == base['review_points']['model_sha256']
    with pytest.raises(ValueError):
        demo_config('nirgendwo')


def test_demo_caches_are_separate_and_identities_differ():
    from preslide.wirkungskette import build as B
    from preslide.wirkungskette.paths import config as demo_config
    s, m = demo_config('stanz'), demo_config('mittelberg')
    assert B.paths(10000, s)['dir'] != B.paths(10000, m)['dir']
    assert B.terrain_identity(s, 10000) != B.terrain_identity(m, 10000)
    assert B.paths(10000)['dir'] == B.paths(10000, s)['dir']           # v01 default unchanged


def test_demo_centre_follows_registered_rule():
    import json as _json
    from preslide.wirkungskette.paths import config as demo_config
    areas = _json.loads((REPORT_GT / 'areas.json').read_text(encoding='utf-8'))
    biggest = max(areas, key=lambda a: a['targets'])
    top = max(biggest['municipalities'], key=lambda m: m['n_targets'])
    mb = demo_config('mittelberg')['demo']
    assert mb['campaign'] == biggest['campaign'] and top['name'] == 'Mittelberg'


def test_full_run_is_written_once():
    if not (REPORT_GT / 'test_results.json').exists():
        pytest.skip('test not yet scored')
    with pytest.raises(RuntimeError, match='scored once'):
        G.run('full', 'srtm')
