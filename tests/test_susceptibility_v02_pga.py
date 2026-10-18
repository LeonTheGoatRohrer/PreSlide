"""susceptibility_v02 Phase 1/2 safety tests: ShakeMap lattice and bilinear PGA, CRS of the sample transform,
GSI extent handling and the Gorkha 20 km sensitivity (blocks, folds, purge, models, interpretation rule).

Synthetic grids and points are built inside the tests; nothing is written to data/ or reports/.
"""
import re
import zipfile

import numpy as np
import pandas as pd
import pytest
from pyproj import Transformer

from preslide.common import read_json
from preslide.sources import ROOT
from preslide.susceptibility import v02_phase1 as P
from preslide.susceptibility import v02_sensitivity as S
from preslide.susceptibility.evaluate import block_folds, purge

CFG = read_json(ROOT / 'config/susceptibility_v02.json')
SPEC = {'lon_min': '80.8500', 'lat_min': '23.9833', 'lon_max': '90.1333', 'lat_max': '31.9500',
        'nominal_lon_spacing': '0.0167', 'nominal_lat_spacing': '0.0167', 'nlon': '558', 'nlat': '479'}


def plane(lon, lat):
    return 3.0 + 2.0 * (lon - 80.85) - 1.5 * (lat - 23.9833)


def grid_rows(spec=SPEC, decimals=4, f=plane):
    """grid.xml-like rows (north-west first, longitude fastest) with coordinates rounded as in the file."""
    nlon, nlat = int(spec['nlon']), int(spec['nlat'])
    lons = np.linspace(float(spec['lon_min']), float(spec['lon_max']), nlon)
    lats = np.linspace(float(spec['lat_max']), float(spec['lat_min']), nlat)
    lon, lat = np.meshgrid(lons, lats)
    return np.round(lon.ravel(), decimals), np.round(lat.ravel(), decimals), f(lon, lat).ravel()


def test_lattice_spacing_from_corners_not_rounded_header():
    lon, lat, v = grid_rows()
    values, lon0, lat_top, dlon, dlat = P.lattice(lon, lat, v, 558, 479, SPEC)
    assert dlon == pytest.approx((90.1333 - 80.85) / 557, abs=1e-9)
    assert dlat == pytest.approx((31.95 - 23.9833) / 478, abs=1e-9)
    # Far corner: the rounded header spacing (0.0167) would put it about 0.019 deg (~2 km) off.
    far = P.bilinear(values, lon0, lat_top, dlon, dlat, np.array([90.13]), np.array([24.0]))
    assert far[0] == pytest.approx(plane(90.13, 24.0), abs=1e-3)


def test_bilinear_reproduces_plane_and_nodes():
    lon, lat, v = grid_rows()
    g = P.lattice(lon, lat, v, 558, 479, SPEC)
    rng = np.random.default_rng(0)
    qlon, qlat = rng.uniform(80.86, 90.12, 500), rng.uniform(23.99, 31.94, 500)
    assert np.allclose(P.bilinear(*g, qlon, qlat), plane(qlon, qlat), atol=1e-3)
    # Exactly at a node: the node value (not a neighbour); asymmetric field so swapped axes would differ.
    vals = g[0]
    assert P.bilinear(*g, np.array([g[1] + 3 * g[3]]), np.array([g[2] - 7 * g[4]]))[0] == pytest.approx(vals[7, 3])


def test_bilinear_outside_is_nan_and_edges_are_inside():
    lon, lat, v = grid_rows()
    g = P.lattice(lon, lat, v, 558, 479, SPEC)
    out = P.bilinear(*g, np.array([80.80, 90.20, 85.0, 85.0, g[1], 90.1333]), np.array([28.0, 28.0, 23.9, 32.0, g[2], 23.9833]))
    assert np.isnan(out[:4]).all()
    assert np.isfinite(out[4:]).all()


@pytest.mark.parametrize('bug', ['south_first', 'lat_fastest', 'irregular', 'corner_mismatch'])
def test_lattice_rejects_unexpected_order(bug):
    spec = dict(SPEC, nlon='6', nlat='5', lon_max=str(80.85 + 5 * 0.0167), lat_min=str(31.95 - 4 * 0.0167))
    lon, lat, v = grid_rows(spec)
    if bug == 'south_first':
        lon, lat, v = lon.reshape(5, 6)[::-1].ravel(), lat.reshape(5, 6)[::-1].ravel(), v.reshape(5, 6)[::-1].ravel()
    elif bug == 'lat_fastest':
        lon, lat, v = lon.reshape(5, 6).T.ravel(), lat.reshape(5, 6).T.ravel(), v.reshape(5, 6).T.ravel()
    elif bug == 'irregular':
        lon = lon.copy()
        lon[2] += 0.005
    else:
        spec['lon_min'] = '80.9000'
    with pytest.raises(RuntimeError):
        P.lattice(lon, lat, v, 6, 5, spec)


def test_utm45n_to_lonlat_orientation():
    # Central meridian of UTM 45N is 87 E; easting 500 km lies on it. The equator is northing 0.
    lon, lat = P.to_lonlat([500000.0, 500000.0, 600000.0], [0.0, 3100000.0, 3100000.0], 'EPSG:32645')
    assert lon[0] == pytest.approx(87.0) and lat[0] == pytest.approx(0.0, abs=1e-9)
    assert lon[1] == pytest.approx(87.0) and 27.9 < lat[1] < 28.1
    assert lon[2] > 87.9 and 27.9 < lat[2] < 28.1


def test_pga_at_matches_known_lonlat_point():
    lon, lat, v = grid_rows(f=lambda lo, la: 10 ** (1 + 0.1 * (lo - 80) + 0.02 * (la - 20)))
    g = (*P.lattice(lon, lat, v, 558, 479, SPEC), '%g')
    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:32645', always_xy=True)
    qlon, qlat = np.array([84.73, 85.32, 86.5]), np.array([28.23, 27.70, 27.9])
    x, y = fwd.transform(qlon, qlat)
    got = P.pga_at(x, y, 'EPSG:32645', g)
    assert np.allclose(got, 1 + 0.1 * (qlon - 80) + 0.02 * (qlat - 20), atol=1e-4)
    with pytest.raises(RuntimeError, match='units'):
        P.pga_at(x, y, 'EPSG:32645', (*g[:5], 'cm/s'))


def test_log10_pga_never_fills():
    out = P.log10_pga_pctg([10.0, 0.0, -1.0, np.nan, 100.0])
    assert out[0] == 1.0 and out[4] == 2.0
    assert np.isnan(out[1:4]).all()


def test_gsi_roles_distinguish_extent_from_cloud_layer():
    stem = 'x/国土地理院技術資料 D1-No_991 平成30年…（北海道厚真町周辺）'
    assert P.gsi_role(stem + '_判読範囲.geojson') == 'extent'
    assert P.gsi_role(stem + '_雲による未判読範囲.geojson') == 'obscured'
    assert P.gsi_role(stem + '_斜面崩壊・堆積範囲.geojson') == 'landslides'
    assert P.gsi_role(stem + '_other.geojson') is None


def test_extent_polygon_only_from_closed_ring():
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    assert P.extent_polygon(ring).area == pytest.approx(1.0)
    with pytest.raises(RuntimeError, match='closed'):
        P.extent_polygon(ring[:-1])
    with pytest.raises(RuntimeError, match='closed'):
        P.extent_polygon([[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]])  # self-intersecting


def test_zip_member_names_decoded_and_checked(tmp_path):
    # Legacy archives store cp932 bytes without the UTF-8 flag: write an ASCII placeholder, then patch the bytes.
    z = tmp_path / 'a.zip'
    raw = '判読範囲'.encode('cp932')
    with zipfile.ZipFile(z, 'w') as f:
        f.writestr('dir/' + 'X' * len(raw) + '.geojson', b'{}')
    z.write_bytes(z.read_bytes().replace(b'X' * len(raw), raw))
    with zipfile.ZipFile(z) as f:
        assert not f.infolist()[0].flag_bits & 0x800
        assert P.member_name(f.infolist()[0]) == 'dir/判読範囲.geojson'
    with pytest.raises(RuntimeError, match='unsafe'):
        P.safe_members(['ok.txt', '../evil.py'])


# ---------------------------------------------------------------- sensitivity

def test_design_constants_match_registered_text():
    reg = str(CFG["sensitivity_gorkha_20km"])
    assert '20 km blocks, 5 folds' in reg and 'closer than 1000 m' in reg
    assert '2000 resamples' in reg and "at least 25" in reg
    assert S.DESIGN == {'block_sizes_m': (5000, 20000), 'folds': 5, 'purge_m': 1000, 'n_resamples': 2000,
                        'min_blocks_with_positives': 25}
    assert re.search(r'EQ_TERRAIN vs slope_only', reg) and re.search(r'EQ_TERRAIN_PGA vs slope_pga_logistic', reg)


def test_models_use_registered_features():
    m = S.model_table(CFG)
    terrain = CFG['features_terrain']
    assert m['EQ_TERRAIN'] == ('hist_gradient_boosting', terrain)
    assert m['EQ_TERRAIN_PGA'] == ('hist_gradient_boosting', terrain + [S.PGA])
    assert m['slope_only'] == ('logistic_regression', ['slope_deg'])
    assert m['slope_pga_logistic'] == ('logistic_regression', ['slope_deg', S.PGA])
    assert S.PGA not in terrain


def test_hyperparameters_equal_v01_amendment3():
    spec = S.model_spec(CFG)
    assert spec['hist_gradient_boosting']['max_iter'] == 300 and spec['logistic_regression'] == {'C': 1.0, 'max_iter': 2000}
    bad = read_json(ROOT / 'config/susceptibility_v02.json')
    bad['model_spec']['hist_gradient_boosting']['learning_rate'] = 0.1
    with pytest.raises(RuntimeError, match='Amendment 3'):
        S.model_spec(bad)


def test_20km_blocks_nest_5km_blocks():
    rng = np.random.default_rng(1)
    x, y = rng.uniform(200000, 450000, 3000), rng.uniform(2.95e6, 3.2e6, 3000)
    b5, b20 = S.block_ids(x, y, 5000), S.block_ids(x, y, 20000)
    parent = {}
    for a, b in zip(b5, b20):
        assert parent.setdefault(a, b) == b
    assert S.block_ids([4999.9, 5000.0, -0.1], [0, 0, 0], 5000).tolist() == ['gorkha_2015:0:0', 'gorkha_2015:1:0',
                                                                          'gorkha_2015:-1:0']


def test_folds_keep_blocks_whole_and_purge_gap():
    rng = np.random.default_rng(2)
    d = pd.DataFrame({'x': rng.uniform(0, 100000, 4000), 'y': rng.uniform(0, 100000, 4000)})
    blocks = S.block_ids(d.x, d.y, 20000)
    folds = block_folds(blocks, 5, 302)
    assert pd.Series(folds).groupby(blocks).nunique().max() == 1
    assert sorted(set(folds)) == [0, 1, 2, 3, 4]
    test, train = d[folds == 0], purge(d[folds != 0], d[folds == 0], 1000)
    dist = np.hypot(train.x.to_numpy()[:, None] - test.x.to_numpy()[None, :],
                    train.y.to_numpy()[:, None] - test.y.to_numpy()[None, :]).min(axis=1)
    assert dist.min() >= 1000
    assert not set(train.index) & set(test.index)


def test_cross_validation_scores_every_sample_out_of_fold():
    rng = np.random.default_rng(3)
    n = 600
    d = pd.DataFrame({'x': rng.uniform(0, 80000, n), 'y': rng.uniform(0, 80000, n), 'label': rng.integers(0, 2, n)})
    for c in CFG['features_terrain'] + [S.PGA]:
        d[c] = rng.normal(size=n)
    models = {k: v for k, v in S.model_table(CFG).items() if v[0] == 'logistic_regression'}
    folds, oof, purged = S.cross_validate(d, S.block_ids(d.x, d.y, 20000), CFG, models, S.model_spec(CFG), 5, 1000)
    assert all(np.isfinite(s).all() for s in oof.values())
    # Purge count per fold equals a brute-force count of training samples within 1000 m of the test fold.
    xy = d[['x', 'y']].to_numpy()
    for f in range(5):
        tr, te = xy[folds != f], xy[folds == f]
        near = (np.hypot(tr[:, None, 0] - te[None, :, 0], tr[:, None, 1] - te[None, :, 1]).min(axis=1) < 1000).sum()
        assert purged[f] == near
    assert sum(purged) > 0


@pytest.mark.parametrize('d5,d20,ci,dpga,prox,shake', [
    (0.12, 0.10, [0.05, 0.15], 0.10, False, False),
    (0.12, 0.05, [0.01, 0.09], 0.10, True, False),   # below half
    (0.12, 0.07, [-0.01, 0.15], 0.10, True, False),  # interval includes 0
    (0.12, 0.10, [0.05, 0.15], 0.05, False, True),   # PGA removes most of the advantage
    (0.12, 0.06, [0.01, 0.11], 0.06, False, False),  # exactly half is not "below half"
])
def test_interpretation_rule(d5, d20, ci, dpga, prox, shake):
    r = S.interpretation(d5, d20, ci, dpga)
    assert r['spatial_proximity_share_large'] is prox and r['largely_explained_by_modelled_shaking'] is shake


# ---------------------------------------------------------------- Iburi Phase 1 helpers

@pytest.mark.parametrize('p90,expected', [
    ({'a': 17.47, 'b': 93.54, 'c': 87.11}, (100, False)),  # maximum, rounded up
    ({'a': 90.0}, (90, False)),                            # exact multiple stays
    ({'a': 90.0000001}, (100, False)),                     # any excess rounds up
    ({'a': 12.0}, (60, False)),                            # floor
    ({'a': 301.0}, (300, True)),                           # cap is a gate finding, flagged
])
def test_buffer_value_rule(p90, expected):
    assert P.buffer_value(p90) == expected


def test_equivalent_radius_of_circles():
    radii = np.arange(1, 101, dtype=float)
    assert P.equivalent_radius_p90(np.pi * radii ** 2) == pytest.approx(np.quantile(radii, 0.9))


def test_intersects_any_counts_touching_not_disjoint():
    from shapely.geometry import box
    old = [box(0, 0, 10, 10)]
    geoms = [box(5, 5, 6, 6), box(10, 0, 12, 2), box(20, 20, 21, 21)]
    assert P.intersects_any(geoms, old).tolist() == [True, True, False]
    assert P.intersects_any(geoms, []).tolist() == [False, False, False]


def test_split_by_style_keeps_majority_style():
    f = [{'properties': {'c': 'red'}}] * 3 + [{'properties': {'c': 'black'}}]
    assert P.split_by_style(f) == ([0, 1, 2], [3])
