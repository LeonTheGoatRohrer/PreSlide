"""Safety tests for anfaelligkeit_at_v01 (synthetic fixtures built in the tests; nothing is written to data/ or reports/).

Each dangerous failure has an injected-bug counterpart in scripts/anfaelligkeit_at_v01_mutation_check.py.
"""
import json

import numpy as np
import pandas as pd
import pytest
from pyproj import Geod
from shapely.geometry import box

from preslide.anfaelligkeit_at_v01 import context, experiment, inventory, terrain


def synthetic_areas(seed=0):
    """Three areas: A and B 1.5 km apart (B partly within the purge radius of A), C far away."""
    rng = np.random.default_rng(seed)
    rows = []
    for area, (cx, cy) in {'A': (500_000, 400_000), 'B': (501_500, 400_000), 'C': (560_000, 420_000)}.items():
        for i in range(40):
            rows.append({'sample_id': f'{area}{i}', 'area_id': area, 'label': int(i < 10),
                         'x': cx + rng.uniform(-400, 400), 'y': cy + rng.uniform(-400, 400)})
    return pd.DataFrame(rows)


# 1. the held-out area stays completely in the test, and nothing within the purge radius is trained on
def test_held_out_area_never_in_training_and_purged():
    data = synthetic_areas()
    seen = 0
    for a, train, test in experiment.folds(data, ['A', 'B', 'C'], 1000):
        seen += 1
        assert set(test.area_id) == {a} and len(test) == (data.area_id == a).sum()
        assert a not in set(train.area_id)
        assert not set(train.sample_id) & set(test.sample_id)
        d = np.hypot(train.x.to_numpy()[:, None] - test.x.to_numpy()[None, :], train.y.to_numpy()[:, None] - test.y.to_numpy()[None, :])
        assert (d > 1000).all()
    assert seen == 3
    # B lies 1.5 km from A: part of B must have been purged when A is held out
    _, train_a, _ = next(experiment.folds(data, ['A'], 1000))
    assert (train_a.area_id == 'B').sum() < (data.area_id == 'B').sum()


# 2. no model feature may come from other events, coordinates, identifiers or infrastructure
def test_no_features_from_neighbouring_events_or_reporting():
    for cols in experiment.FEATURE_SETS.values():
        experiment.check_features(cols)
    for bad in (['slope', 'dist_infrastructure_m'], ['slope', 'n_inventory_within_500m'], ['slope', 'x'], ['lat', 'slope'],
                ['slope', 'area_id'], ['slope', 'event_year'], ['slope', 'neighbour_positive_count']):
        with pytest.raises(ValueError):
            experiment.check_features(bad)


def test_score_models_refuses_a_leaking_feature_set(monkeypatch):
    data = synthetic_areas()
    for c in terrain.TERRAIN + context.GEO:
        data[c] = np.random.default_rng(1).normal(size=len(data))
    data['dist_infrastructure_m'] = 1.0
    monkeypatch.setitem(experiment.FEATURE_SETS, 'terrain_geology', terrain.TERRAIN + context.GEO + ['dist_infrastructure_m'])
    cfg = {'models': {'hist_gradient_boosting': {'max_iter': 5}, 'logistic_regression': {'C': 1.0, 'class_weight': 'balanced', 'max_iter': 100}}}
    with pytest.raises(ValueError):
        experiment.score_models(data[data.area_id != 'A'], data[data.area_id == 'A'], cfg)


# 3. aspect is circular: downslope azimuth 359 deg and 1 deg give nearly the same features
def tilted(azimuth_deg, n=40, res=30.0, grade=0.4):
    """Plane DEM whose downslope direction is `azimuth_deg` (clockwise from north; rows run southward)."""
    rows, cols = np.mgrid[0:n, 0:n] * res
    north, east = -rows, cols
    a = np.deg2rad(azimuth_deg)
    return (-(north * np.cos(a) + east * np.sin(a)) * grade + 2000).astype('float32')


def test_aspect_features_are_circular():
    f359 = terrain.terrain_rasters(tilted(359.0))
    f1 = terrain.terrain_rasters(tilted(1.0))
    f180 = terrain.terrain_rasters(tilted(180.0))
    c = (20, 20)
    v = lambda f: np.array([f['aspect_sin'][c], f['aspect_cos'][c]])
    assert np.linalg.norm(v(f359) - v(f1)) < 0.05
    assert np.linalg.norm(v(f359) - v(f180)) > 1.9
    assert 'aspect' not in experiment.FEATURE_SETS['terrain_geology']


# 4. metre distances come from EPSG:31287 with lon/lat in the right order
def test_projected_distances_match_geodesic():
    lon = np.array([9.9, 9.9, 15.4, 16.2])
    lat = np.array([47.25, 47.30, 47.07, 47.0701])
    x, y = inventory.project_xy(lon, lat)
    geod = Geod(ellps='WGS84')
    for i, j in ((0, 1), (2, 3), (0, 2)):
        _, _, d = geod.inv(lon[i], lat[i], lon[j], lat[j])
        assert abs(np.hypot(x[i] - x[j], y[i] - y[j]) - d) / d < 0.003
    assert inventory.area_of(None, 120_000.0, 380_000.0) == 'tile_2_7'
    assert inventory.area_of(float('nan'), 120_000.0, 380_000.0) == 'tile_2_7'


# 5. background respects the inventory buffer, the separation and the lattice cells
def test_background_buffer_separation_and_region():
    cfg = {'background': {'seed': 7, 'inventory_buffer_m': 100, 'minimum_separation_m': 60, 'minimum_slope_deg': 5,
                          'elevation_range_m': [0, 4500], 'max_candidates_per_needed_point': 200}}
    gx, gy = np.meshgrid(np.arange(500_000, 505_000, 250.0), np.arange(400_000, 405_000, 250.0))
    records = pd.DataFrame({'x': gx.ravel(), 'y': gy.ravel()})
    buffer = inventory.InventoryBuffer(records, 100)
    flat = lambda x, y: pd.DataFrame({c: np.full(len(x), 20.0 if c == 'slope' else 1000.0) for c in terrain.TERRAIN})
    bg, info = inventory.draw_background('T', [(100, 80)], 150, 'srtm', cfg, buffer, box(9, 46, 18, 49.5), sampler=flat)
    assert len(bg) == 150
    d, _ = buffer.tree.query(bg[['x', 'y']].to_numpy(), k=1)
    assert (d > 100).all()
    xy = bg[['x', 'y']].to_numpy()
    pair = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1)) + np.eye(len(xy)) * 1e9
    assert pair.min() >= 60
    assert bg.x.between(500_000, 505_000).all() and bg.y.between(400_000, 405_000).all()
    assert info['rejected']['inventory_buffer'] > 0
    steep_only = lambda x, y: flat(x, y).assign(slope=np.where(np.arange(len(x)) % 2, 2.0, 20.0))
    bg2, _ = inventory.draw_background('T', [(100, 80)], 50, 'srtm', cfg, buffer, box(9, 46, 18, 49.5), sampler=steep_only)
    assert len(bg2) == 50


def test_background_is_reproducible():
    cfg = {'background': {'seed': 7, 'inventory_buffer_m': 100, 'minimum_separation_m': 60, 'minimum_slope_deg': 5,
                          'elevation_range_m': [0, 4500], 'max_candidates_per_needed_point': 200}}
    buffer = inventory.InventoryBuffer(pd.DataFrame({'x': [0.0], 'y': [0.0]}), 100)
    flat = lambda x, y: pd.DataFrame({c: np.full(len(x), 20.0) for c in terrain.TERRAIN})
    a, _ = inventory.draw_background('T', [(100, 80), (101, 80)], 30, 'srtm', cfg, buffer, box(9, 46, 18, 49.5), sampler=flat)
    b, _ = inventory.draw_background('T', [(100, 80), (101, 80)], 30, 'srtm', cfg, buffer, box(9, 46, 18, 49.5), sampler=flat)
    pd.testing.assert_frame_equal(a, b)


# 6. cache identity: a block cache from another variant/config or with a wrong checksum is refused
def test_block_cache_identity_and_checksum(tmp_path, monkeypatch):
    path = tmp_path / 'b1_2.npz'
    monkeypatch.setattr(terrain, 'block_path', lambda variant, bx, by: path)
    arrays = {k: np.zeros((2, 2), 'float32') for k in terrain.TERRAIN}
    np.savez_compressed(path, **arrays)
    good = terrain.block_identity('srtm', 1, 2, 5010)
    assert good != terrain.block_identity('skadi', 1, 2, 5010)
    assert good != terrain.block_identity('srtm', 1, 3, 5010)
    assert good != terrain.block_identity('srtm', 1, 2, 4000)
    meta = {'identity': terrain.block_identity('skadi', 1, 2, 5010), 'sha256': terrain.sha(path)}
    path.with_suffix('.json').write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='identity'):
        terrain.compute_block('srtm', 1, 2)
    path.with_suffix('.json').write_text(json.dumps({'identity': good, 'sha256': '0' * 64}))
    with pytest.raises(ValueError, match='checksum'):
        terrain.compute_block('srtm', 1, 2)
    path.with_suffix('.json').write_text(json.dumps({'identity': good, 'sha256': terrain.sha(path)}))
    assert set(terrain.compute_block('srtm', 1, 2)) == set(terrain.TERRAIN)


# supporting rules
def test_deduplication_and_priority():
    x0, y0 = 500_000.0, 400_000.0
    f = pd.DataFrame({'object_id': [1, 2, 3, 4], 'x': [x0, x0 + 20, x0 + 100, x0 + 125], 'y': [y0] * 4,
                      'project': [None, 'P', None, None], 'year': pd.array([2005, 2005, None, 2010], dtype='Int64'),
                      'position_class': ['fine', 'coarse', 'fine', 'fine']})
    keep = inventory.deduplicate(f, 30, 'fine')
    assert keep.tolist() == [False, True, False, True]          # project wins at 20 m; known year wins at 25 m


def test_dem_provenance_year_rule():
    years = pd.Series(pd.array([None, 1970, 2000, 2001, 2024], dtype='Int64'))
    assert inventory.year_eligible(years, 'srtm').tolist() == [False, False, False, True, True]
    assert inventory.year_eligible(years, 'skadi').all()
    assert inventory.event_year(None, 'Thiersee_1970') == 1970
    assert inventory.event_year(2005.0, 'X_2013') == 2005
    assert inventory.event_year(None, None) is None


def test_corine_vintage_strictly_before_event_year():
    assert [context.clc_vintage(y) for y in (1970, 2001, 2002, 2007, 2008, 2012, 2013, 2018, 2019, None)] == \
        [None, None, 'CLC2000', 'CLC2000', 'CLC2006', 'CLC2006', 'CLC2012', 'CLC2012', 'CLC2018', None]


def test_missing_class_is_missing_not_zero():
    oh = context.one_hot(pd.Series(['geo_carbonate', None]), context.GEO)
    assert oh.iloc[0].sum() == 1 and oh.iloc[1].isna().all()


def test_metrics_and_bootstrap():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    s = np.array([9, 1, 8, 2, 3, 4, 5, 6, 7, 0], float)
    m = experiment.area_metrics(y, s)
    assert m['auc'] == pytest.approx(9 / 16) and m['capture_top20'] == pytest.approx(0.5)
    a = experiment.bootstrap_mean(np.array([0.1, 0.2, 0.3]), 500, 1)
    assert a == experiment.bootstrap_mean(np.array([0.1, 0.2, 0.3]), 500, 1)
    assert a['ci95'][0] <= a['mean'] <= a['ci95'][1]
