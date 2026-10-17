"""hangmap_v01 safety tests: shares per group, circular aspect, CRS/distance, separation, no future information, caches."""
import numpy as np
import pandas as pd
import pytest

from preslide.hangmap import core
from preslide.hangmap.paths import config, DATA
from preslide.sources import ROOT
from preslide.terrain import PROJECT, GEOD
from preslide.v05.paths import config as v05_config

HAS_MODEL = (ROOT / config()['model']['bundle']).exists()
HAS_TILES = (ROOT / 'data/raw/terrain/N47E010.hgt').exists()
needs_model = pytest.mark.skipif(not HAS_MODEL, reason='data-dependent: V0.5 model bundle missing (worktree without data junction)')
needs_tiles = pytest.mark.skipif(not HAS_TILES, reason='data-dependent: DEM tile cache missing')


def test_shares_sum_to_one_in_every_group():
    rng = np.random.default_rng(3)
    groups = np.repeat(np.arange(40), rng.integers(1, 13, 40))      # includes groups of size 1
    score = rng.normal(0, 4, len(groups))
    share = core.shares(score, groups)
    assert np.all(share >= 0) and np.all(share <= 1)
    totals = pd.Series(share).groupby(groups).sum()
    assert np.allclose(totals, 1.0, atol=1e-12)


def test_shares_are_shift_invariant_and_order_follows_score():
    score = np.array([2.0, -1.0, 0.5, 7.0])
    a, b = core.shares(score, np.zeros(4, int)), core.shares(score + 100, np.zeros(4, int))
    assert np.allclose(a, b)
    assert list(np.argsort(a)) == list(np.argsort(score))
    assert np.isclose(core.shares(np.array([3.0]), np.array([0]))[0], 1.0)


def test_shares_stay_finite_for_extreme_scores():
    share = core.shares(np.array([800.0, -800.0, 0.0]), np.zeros(3, int))
    assert np.isfinite(share).all() and np.isclose(share.sum(), 1.0)


def test_aspect_is_circular():
    s1, c1 = core.aspect_features(359.0)
    s2, c2 = core.aspect_features(1.0)
    chord = float(np.hypot(s1 - s2, c1 - c2))
    assert np.isclose(chord, 2 * np.sin(np.deg2rad(1.0)), atol=1e-9)       # 2 deg apart, not 358
    far = core.aspect_features(181.0)
    assert np.hypot(s1 - far[0], c1 - far[1]) > 1.9
    assert np.allclose(core.aspect_features(0.0), core.aspect_features(360.0))


@pytest.mark.parametrize('lon,lat', [(9.6, 47.3), (13.5, 47.5), (16.9, 48.2)])
def test_projected_distance_matches_geodesic_at_zone_edges(lon, lat):
    x0, y0 = PROJECT.transform(lon, lat)
    for bearing in (0, 45, 90, 180, 270):
        x1, y1 = x0 + 3000 * np.sin(np.deg2rad(bearing)), y0 + 3000 * np.cos(np.deg2rad(bearing))
        from preslide.terrain import INVERSE
        lon1, lat1 = INVERSE.transform(x1, y1)
        _, _, geodesic = GEOD.inv(lon, lat, lon1, lat1)
        assert abs(geodesic - 3000) / 3000 < 2e-3
    # swapped coordinates must not produce a plausible Austrian position
    sx, sy = PROJECT.transform(lat, lon)
    assert not (np.isfinite(sx) and abs(sx - x0) < 1e5 and abs(sy - y0) < 1e5)


def test_grid_cells_lie_inside_circle_on_dem_cells():
    res, shape = 30.0, (400, 400)
    left, top = 500000.0, 400000.0
    cx, cy = left + 200 * res + 7, top - 200 * res - 11
    rows, cols, x, y = core.grid_cells(cx, cy, 1000.0, left, top, res, 90.0, shape)
    assert len(x) > 100
    assert np.all(np.hypot(x - cx, y - cy) <= 1000.0)
    assert np.all(((rows - rows[0]) % 3 == 0) & ((cols - cols[0]) % 3 == 0))
    r2 = np.floor((top - y) / res).astype(int)
    c2 = np.floor((x - left) / res).astype(int)
    assert (r2 == rows).all() and (c2 == cols).all()                         # centre -> same DEM cell
    with pytest.raises(ValueError):
        core.grid_cells(cx, cy, 1000.0, left, top, res, 100.0, shape)


def test_group_selection_is_separated_deterministic_and_complete():
    rng = np.random.default_rng(1)
    x, y = rng.uniform(0, 3000, 600), rng.uniform(0, 3000, 600)
    ids = np.arange(600)
    seed = core.group_seed(10.5617, 47.1478, 1500)
    a = core.select_group(ids, x, y, 10, 400.0, seed)
    b = core.select_group(ids[::-1].copy(), x[::-1].copy(), y[::-1].copy(), 10, 400.0, seed)   # input order must not matter
    assert list(a) == list(b) and len(a) == 10 and len(set(a)) == 10
    d = np.hypot(x[a][:, None] - x[a][None], y[a][:, None] - y[a][None])
    assert d[~np.eye(10, dtype=bool)].min() >= 400.0
    assert core.group_seed(10.5617, 47.1478, 1500) != core.group_seed(10.5617, 47.1478, 1600)


def test_request_validation():
    cfg = config()
    core.validate_request(2000, None, cfg)
    for bad in (100, 5000):
        with pytest.raises(ValueError):
            core.validate_request(bad, None, cfg)
    with pytest.raises(ValueError):
        core.validate_request(2000, [[10.0, 47.0]], cfg)                      # one point is no comparison
    with pytest.raises(ValueError):
        core.validate_request(2000, [[10.0, 47.0], [10.0, 47.0]], cfg)        # duplicates


def test_model_uses_only_registered_static_columns_no_weather_no_time():
    static = set(v05_config()['features']['static'])
    forbidden = {c for c in v05_config()['features']['forbidden_predictors'] if ' ' not in c}
    temporal = set(v05_config()['features']['temporal'])
    if HAS_MODEL:
        from preslide.hangmap import build
        cols = set(build.model_bundle()['columns'])
        assert cols == static and not cols & forbidden and not cols & temporal
        assert len(cols) == 22


def test_rain_layer_is_not_wired_into_the_score():
    from preslide.hangmap import build
    assert not hasattr(build, 'recent_rain') and not hasattr(build, 'daily_sums')
    assert not any('rain' in c for c in v05_config()['features']['static'])


def test_daily_sums_keep_complete_days_only_and_fail_on_bad_values():
    from preslide.hangmap.rain import daily_sums
    t = pd.date_range('2026-10-10 06:00', periods=24 * 3, freq='h', tz='UTC')
    out = daily_sums(t, [1.0] * len(t))
    assert [d['day_utc'] for d in out] == ['2026-10-11', '2026-10-12'] and all(d['rain_mm'] == 24.0 for d in out)
    with pytest.raises(ValueError):
        daily_sums(t, [1.0] * (len(t) - 1) + [-0.1])
    with pytest.raises(ValueError):
        daily_sums(t, [1.0] * (len(t) - 1) + [None])


@needs_tiles
def test_dem_tiles_must_predate_the_reference_date():
    from preslide.v05 import terrain as T
    T.tile(47, 10, config()['terrain']['reference_date'])
    with pytest.raises(ValueError, match='not_demonstrably_pre_event'):
        T.tile(47, 10, '2000-01-01')


@needs_model
def test_model_hash_mismatch_is_refused(monkeypatch):
    from preslide.hangmap import build
    bad = dict(config())
    bad['model'] = {**bad['model'], 'bundle_sha256': '0' * 64}
    build.model_bundle.cache_clear()
    monkeypatch.setattr(build, 'config', lambda: bad)
    with pytest.raises(RuntimeError, match='SHA-256 mismatch'):
        build.model_bundle()
    build.model_bundle.cache_clear()


@needs_model
def test_cached_example_result_invariants_and_checksum():
    from preslide.hangmap import build
    e = config()['examples'][0]
    if not (DATA / 'cache/results').exists():
        pytest.skip('data-dependent: example area not computed (python -m preslide.hangmap)')
    r = build.compute(e['longitude'], e['latitude'], e['radius_m'])
    shares = [m['share'] for m in r['group']]
    assert len(shares) == 10 and abs(sum(shares) - 1) < 1e-3 and abs(r['group_share_sum'] - 1) < 1e-9
    f = r['heat']['features']
    assert len(f) == r['counts']['eligible']
    assert 1.0 - 1e-3 <= np.mean([c['properties']['index'] for c in f]) <= 1.0 + 1e-3     # index is relative to the area mean
    assert all(0 < c['properties']['percentile'] <= 100 for c in f)
    assert 'Keine Eintrittswahrscheinlichkeit' in r['notice']
    # corrupting the cached file must be detected, not silently served
    from preslide.common import digest
    from preslide.v05.paths import sha
    from preslide.hangmap.paths import CONFIG
    key = digest({'lon': round(e['longitude'], 5), 'lat': round(e['latitude'], 5), 'r': float(e['radius_m']), 'pts': None, 'cfg': sha(CONFIG)})
    path = DATA / 'cache/results' / f'{key}.json'
    original = path.read_bytes()
    try:
        path.write_bytes(original + b' ')
        with pytest.raises(RuntimeError, match='checksum'):
            build.compute(e['longitude'], e['latitude'], e['radius_m'])
    finally:
        path.write_bytes(original)
    assert build.compute(e['longitude'], e['latitude'], e['radius_m'])['group_share_sum'] == r['group_share_sum']


@needs_model
def test_custom_points_form_their_own_group_and_sum_to_one():
    from preslide.hangmap import build
    e = config()['examples'][0]
    base = build.compute(e['longitude'], e['latitude'], e['radius_m'])
    pts = [[m['longitude'], m['latitude']] for m in base['group'][:3]]
    r = build.compute(e['longitude'], e['latitude'], e['radius_m'], pts)
    assert r['mode'] == 'custom_points' and len(r['group']) == 3
    assert abs(sum(m['share'] for m in r['group']) - 1) < 1e-3
    frame, _ = build.build_features(e['longitude'], e['latitude'], e['radius_m'], None, config())
    f = frame[frame.reason == 'slope_below_minimum'].iloc[0]
    flat = [float(f.longitude), float(f.latitude)]
    with pytest.raises(ValueError, match='nicht bewertbar'):        # flat point (below 5 deg) is refused, not silently scored
        build.compute(e['longitude'], e['latitude'], e['radius_m'], [pts[0], flat])
