"""wirkungskette_v01 safety tests: radius limits, metric CRS, D8 route, end reasons, energy line, corridor counts,
wording, cache identity. Synthetic arrays below are unit-test fixtures only; they never enter data/ or reports/."""
import math

import numpy as np
import pytest
from pyproj import Geod
from shapely.geometry import LineString, box

from preslide.terrain import PROJECT
from preslide.wirkungskette import build as B
from preslide.wirkungskette import core, store
from preslide.wirkungskette.paths import config

CFG = config()
RES = 30.0


# ---------- radius ----------

@pytest.mark.parametrize('r', [1000, 2000, 5000, 10000])
def test_radius_inside_limits_accepted(r):
    assert core.validate_radius(r, CFG) == r


@pytest.mark.parametrize('r', [0, 999, 10001, 20000, -3000, float('nan'), float('inf'), 'abc', None, 2500])
def test_radius_outside_limits_or_off_step_refused(r):
    with pytest.raises(ValueError):
        core.validate_radius(r, CFG)


def test_radius_limits_match_control_design():
    v04 = __import__('json').load(open('config/v04.json', encoding='utf-8'))['matching']
    assert CFG['radius_m']['max'] == v04['control_max_distance_m']
    assert CFG['radius_m']['min'] >= v04['control_min_distance_m']


# ---------- metric CRS ----------

def test_distances_are_metres_in_epsg31287_not_degrees():
    lon0, lat0, lon1, lat1 = 15.49683, 47.44533, 15.56, 47.47
    x0, y0 = PROJECT.transform(lon0, lat0)
    x1, y1 = PROJECT.transform(lon1, lat1)
    planar = float(core.distance_m([x1], [y1], x0, y0)[0])
    geodesic = Geod(ellps='WGS84').inv(lon0, lat0, lon1, lat1)[2]
    assert abs(planar - geodesic) / geodesic < 2e-3
    assert planar > 1000


def test_degree_coordinates_are_refused():
    with pytest.raises(ValueError):
        core.distance_m([15.56], [47.47], 15.49, 47.44)
    with pytest.raises(ValueError):
        core.corridor([15.5, 15.51], [47.4, 47.41], 1, 50)


def test_grid_cells_stay_inside_radius_in_metres():
    x0, y0 = PROJECT.transform(15.49683, 47.44533)
    left, top = x0 - 3000, y0 + 3000
    rows, cols, x, y = core.grid_cells(x0, y0, 2000, left, top, RES, 90, (200, 200))
    d = np.hypot(x - x0, y - y0)
    assert d.max() <= 2000 and d.max() > 1900
    assert len(rows) == pytest.approx(math.pi * 2000 ** 2 / 90 ** 2, rel=0.05)


# ---------- D8 route ----------

def plane(n=40, dip=0.2, noise=0.0, seed=1):
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    z = 1000 - dip * RES * (xx + 0.3 * yy)
    return z + np.random.default_rng(seed).normal(0, noise, z.shape)


def test_d8_route_descends_strictly_and_moves_to_neighbours():
    z = plane(noise=0.3)
    from preslide.v04.terrain import fill_depressions
    filled, _, _ = fill_depressions(z)
    for start in [(20, 2), (5, 5), (35, 10), (18, 20)]:
        rows, cols, end = core.d8_route(filled, z, *start, RES, 1e6)
        surface = filled[rows, cols]
        assert (np.diff(surface) < 0).all()
        assert (np.maximum(np.abs(np.diff(rows)), np.abs(np.diff(cols))) == 1).all()
        assert end == 'rand'


def test_end_reasons_sink_nodata_border_are_distinguished():
    yy, xx = np.mgrid[0:21, 0:21].astype(float)
    bowl = 100 + (xx - 10) ** 2 + (yy - 10) ** 2
    assert core.d8_route(bowl, bowl, 10, 3, RES, 1e6)[2] == 'senke'
    z = plane()
    z_nan = z.copy()
    z_nan[:, 30] = np.nan
    surface = np.where(np.isfinite(z_nan), z_nan, -1e9)
    rows, cols, end = core.d8_route(surface, z_nan, 20, 2, RES, 1e6)
    assert end == 'nodata' and np.isfinite(z_nan[rows, cols]).all()
    assert core.d8_route(z, z, 20, 2, RES, 1e6)[2] == 'rand'
    assert core.d8_route(z, z, 20, 2, RES, 200)[2] == 'max_laenge'


def test_border_exit_is_never_reported_as_scenario_stop():
    z = plane(dip=1.0)
    rows, cols, end = core.d8_route(z, z, 20, 2, RES, 1e6)
    s = core.path_distance_m(rows, cols, RES)
    stop = core.energy_line_stop(z[rows, cols], s, 11, 15, 9.81, end)
    assert end == 'rand' and stop['status'] == 'rand'
    assert core.fixed_reach_stop(s, s[-1] + 100, end)['status'] == 'rand'


def test_real_window_routes_descend_when_built():
    p = B.paths(CFG['radius_m']['max'])
    if not store.exists(p['terrain']):
        pytest.skip('demo window not built (python -m preslide.wirkungskette build)')
    t = store.load_npz(p['terrain'], B.terrain_identity(CFG, CFG['radius_m']['max']))
    rng = np.random.default_rng(3)
    n = t['dem'].shape[0]
    for r, c in rng.integers(n // 4, 3 * n // 4, size=(40, 2)):
        rows, cols, end = core.d8_route(t['filled'], t['dem'], r, c, RES, 15000)
        assert (np.diff(t['filled'][rows, cols]) < 0).all()
        assert end in ('rand', 'nodata', 'senke', 'max_laenge')
        assert np.isfinite(t['dem'][rows, cols]).all()


# ---------- runout scenarios ----------

def slope_then_flat(slope_deg=30.0, slope_m=300.0, flat_m=3000.0, dx=RES):
    s = np.arange(0, slope_m + flat_m + dx, dx)
    z = np.where(s <= slope_m, 1000 - s * math.tan(math.radians(slope_deg)), 1000 - slope_m * math.tan(math.radians(slope_deg)))
    return s, z


@pytest.mark.parametrize('angle', [7, 11, 20])
def test_energy_line_stops_where_analytic_energy_is_spent(angle):
    s, z = slope_then_flat()
    cap = 15 ** 2 / (2 * 9.81)
    t_a, t_s = math.tan(math.radians(angle)), math.tan(math.radians(30))
    # On the 30 deg slope h grows by dx*(tan30 - tan a) until the cap; on the flat it drops by dx*tan a.
    h_end_slope = min(300 * (t_s - t_a), cap)
    expected = 300 + h_end_slope / t_a
    out = core.energy_line_stop(z, s, angle, 15, 9.81, 'rand')
    assert out['status'] == 'gestoppt'
    assert abs(s[out['stop_index']] - expected) <= RES
    assert min(np.asarray(out['energy_height_m']) - z[:out['stop_index'] + 1]) >= -1e-9


def test_energy_line_does_not_start_on_slope_flatter_than_angle():
    s = np.arange(0, 600, RES)
    z = 1000 - s * math.tan(math.radians(5))
    assert core.energy_line_stop(z, s, 11, 15, 9.81, 'rand')['stop_index'] == 0


def test_lower_angle_reaches_at_least_as_far():
    s, z = slope_then_flat()
    stops = [core.energy_line_stop(z, s, a, 15, 9.81, 'rand')['stop_index'] for a in (20, 11, 7)]
    assert stops == sorted(stops)


def test_fixed_reach_stop():
    s = np.arange(0, 1000, RES)
    out = core.fixed_reach_stop(s, 45, 'rand')
    assert out == {'stop_index': 1, 'status': 'gestoppt'} and s[1] <= 45 < s[2]


def test_scenarios_in_config_have_literature_sources_and_are_not_fitted():
    for sc in CFG['runout']['scenarios']:
        assert sc['source'] and ('Hürlimann' in sc['source'] or 'Horton' in sc['source'])
    assert 'none was fitted' in CFG['runout']['scenario_rule']


# ---------- corridor and exposure ----------

def test_corridor_counts_buildings_roads_and_lengths():
    x0, y0 = 560000.0, 390000.0
    xs, ys = x0 + np.arange(0, 301, 30.0), np.full(11, y0)
    area = core.corridor(xs, ys, 10, 50)
    feats = [{'geometry': box(x0 + 100, y0 + 10, x0 + 110, y0 + 20), 'typ': 'gebaeude'},       # inside
             {'geometry': box(x0 + 100, y0 + 30, x0 + 110, y0 + 40), 'typ': 'gebaeude'},       # 30 m off: outside
             {'geometry': box(x0 + 400, y0 - 5, x0 + 410, y0 + 5), 'typ': 'gebaeude'},         # beyond the stop
             {'geometry': LineString([(x0 + 150, y0 - 200), (x0 + 150, y0 + 200)]), 'typ': 'strasse'},
             {'geometry': LineString([(x0 - 500, y0 + 500), (x0 + 500, y0 + 500)]), 'typ': 'bahn'}]
    counts = core.count_by_type(core.Exposure(feats).hits(area), ['gebaeude', 'strasse', 'bahn', 'weg'])
    assert counts['gebaeude']['anzahl'] == 1
    assert counts['strasse'] == {'anzahl': 1, 'laenge_m': pytest.approx(50.0, abs=0.5)}
    assert counts['bahn']['anzahl'] == 0 and counts['weg']['anzahl'] == 0
    shorter = core.corridor(xs, ys, 2, 50)                     # stops at 60 m: nothing reached
    assert all(v['anzahl'] == 0 for v in core.count_by_type(core.Exposure(feats).hits(shorter), ['gebaeude', 'strasse']).values())


# ---------- review classes ----------

def test_review_classes_follow_rank_fractions_relative_to_window():
    score = np.random.default_rng(5).normal(size=1000)
    cls = core.review_classes(score, CFG['review_points']['classes'])
    assert [(cls == k).sum() for k in (1, 2, 3, 4)] == [50, 150, 300, 500]
    assert score[cls == 1].min() > score[cls == 2].max() > score[cls == 3].max()
    shifted = core.review_classes(score + 100, CFG['review_points']['classes'])
    assert (shifted == cls).all()                              # relative: a constant shift changes nothing
    with pytest.raises(ValueError):
        core.review_classes(np.array([1.0, np.nan]), CFG['review_points']['classes'])


def test_release_points_are_separated():
    rng = np.random.default_rng(2)
    x, y = 560000 + rng.uniform(0, 2000, 500), 390000 + rng.uniform(0, 2000, 500)
    idx = core.select_release_points(x, y, rng.normal(size=500), 5, 300)
    assert len(idx) == 5
    for i in idx:
        for j in idx:
            assert i == j or math.hypot(x[i] - x[j], y[i] - y[j]) >= 300


# ---------- wording ----------

def test_banned_words_are_detected():
    assert core.banned_words({'a': ['ok', {'b': 'Eintrittswahrscheinlichkeit'}]}) == ['$.a[1].b']
    assert core.banned_words({'Risiko': 1}) == ['$.Risiko (Schlüssel)']
    assert core.banned_words({'t': 'liegt im Auslaufszenario'}) == []
    assert core.banned_words(['gefährdet']) and core.banned_words(['probability'])


def test_api_outputs_contain_no_probability_or_risk_words_when_built():
    p = B.paths(CFG['radius_m']['max'])
    if not store.exists(p['cells']):
        pytest.skip('demo window not built (python -m preslide.wirkungskette build)')
    from fastapi.testclient import TestClient
    from preslide.api import app
    client = TestClient(app)
    for url in ('/api/wirkungskette?radius_m=3000&modus=pruefpunkte', '/api/wirkungskette?radius_m=1000&modus=hangmuren',
                '/api/wirkungskette/pruefstufen?radius_m=5000'):
        r = client.get(url)
        assert r.status_code == 200, url
        assert core.banned_words(r.json()) == []
    assert client.get('/api/wirkungskette?radius_m=12000').status_code == 422
    assert client.get('/api/wirkungskette?radius_m=3000&modus=x').status_code == 422


# ---------- cache identity ----------

def test_checkpoint_refuses_other_configuration_and_tampering(tmp_path):
    path = tmp_path / 'a.npz'
    store.save_npz(path, 'id1', {'z': np.arange(3)})
    assert store.load_npz(path, 'id1')['z'].tolist() == [0, 1, 2]
    with pytest.raises(RuntimeError, match='identity'):
        store.load_npz(path, 'id2')
    path.write_bytes(path.read_bytes() + b'x')
    with pytest.raises(RuntimeError, match='checksum'):
        store.load_npz(path, 'id1')


def test_relevant_config_change_changes_identity():
    import copy
    r = CFG['radius_m']['max']
    changed = copy.deepcopy(CFG)
    changed['terrain']['minimum_slope_deg'] += 1
    assert B.terrain_identity(changed, r) != B.terrain_identity(CFG, r)
    assert B.cells_identity(changed, r) != B.cells_identity(CFG, r)
    changed = copy.deepcopy(CFG)
    changed['review_points']['model_sha256'] = '0' * 64
    assert B.cells_identity(changed, r) != B.cells_identity(CFG, r)
    assert B.terrain_identity(CFG, r) != B.terrain_identity(CFG, r - 1000)
    # regression: int and float radius must address the same checkpoint (found when 10000 vs 10000.0 mismatched)
    assert B.terrain_identity(CFG, int(r)) == B.terrain_identity(CFG, float(r))


# ---------- relief ----------

def test_hillshade_lights_northwest_faces():
    yy, xx = np.mgrid[0:30, 0:30].astype(float)
    faces_nw = 1000 + 10 * (xx + yy)          # rises to the south-east -> faces north-west
    faces_se = 1000 - 10 * (xx + yy)
    assert core.hillshade(faces_nw, RES)[15, 15] > core.hillshade(faces_se, RES)[15, 15] + 50


def test_image_corners_enclose_projected_centre():
    x0, y0 = PROJECT.transform(15.49683, 47.44533)
    corners = np.array(B.corners_lonlat(x0 - 1500, y0 + 1500, 30, (100, 100)))
    assert corners[:, 0].min() < 15.49683 < corners[:, 0].max()
    assert corners[:, 1].min() < 47.44533 < corners[:, 1].max()
    assert corners[0, 1] > corners[3, 1] and corners[1, 0] > corners[0, 0]   # top above bottom, right east of left
