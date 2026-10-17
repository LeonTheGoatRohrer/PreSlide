"""susceptibility_v01 Phase 0 safety tests: sealed blind test isolation, registry rules, DEM date, amendments, write guard.

Configurations below are modified in-memory copies of the registered config; nothing is written to data/ or reports/.
"""
import copy
import math
import json

import numpy as np
import pytest
from pyproj import CRS, Transformer
from shapely.geometry import box

from preslide.common import read_json
from preslide.sources import ROOT
from preslide.susceptibility import inventory as I
from preslide.susceptibility import paths as P
from preslide.susceptibility import registry as G

CFG = read_json(ROOT / 'config/susceptibility_v01.json')
SEALED = CFG['south_tyrol_blind_test']['dataset']


def cfg():
    return copy.deepcopy(CFG)


def broken(mutate):
    c = cfg()
    mutate(c)
    return c


def test_registered_config_is_valid():
    assert G.validate(cfg())


def test_registered_config_matches_preregistration():
    if not P.REGISTRATION.exists():
        pytest.skip('not registered yet')
    assert P.text_sha(P.CONFIG) == read_json(P.REGISTRATION)['config_sha256']
    assert P.config()['version'] == 'susceptibility_v01'


@pytest.mark.parametrize('name,mutate,message', [
    ('sealed in training arm', lambda c: c['arms']['MODEL_Q'].append(SEALED), 'not a development dataset'),
    ('sealed allows training', lambda c: c['registry']['datasets'][SEALED].update(train_allowed=True), 'train_allowed'),
    ('sealed allows thresholds', lambda c: c['registry']['datasets'][SEALED].pop('threshold_selection_allowed'), 'threshold_selection_allowed'),
    ('sealed gets mapped negatives', lambda c: c['registry']['datasets'][SEALED].update(negative_policy='inside_mapping_extent'), 'presence_background'),
    ('sealed relabelled development', lambda c: c['registry']['datasets'][SEALED].update(role='development'), 'role sealed_blind_test'),
    ('unknown role', lambda c: c['registry']['datasets']['rer2023'].update(role='train'), 'not allowed'),
    ('negatives from gaps', lambda c: c['registry']['datasets']['rer2023'].update(negative_policy='presence_background'), 'mapping extent'),
    ('incomplete mapping', lambda c: c['registry']['datasets']['gorkha_2015'].update(mapping_complete=False), 'mapping_complete'),
    ('dem after event', lambda c: c['dem'].update(acquisition_end='2015-06-01'), 'DEM acquired after'),
    ('licence missing', lambda c: c['registry']['datasets']['far_western_nepal'].update(license=' '), 'licence'),
    ('ratio mismatch', lambda c: c['south_tyrol_blind_test']['background'].update(ratio=[1, 10]), 'ratio differs'),
    ('code overlap', lambda c: c['south_tyrol_blind_test']['positive_subset']['exclude_codes'].append(2), 'overlap'),
])
def test_injected_registry_bug_is_rejected(name, mutate, message):
    with pytest.raises(ValueError, match=message):
        G.validate(broken(mutate))


def test_dem_on_event_day_boundary():
    # Acquisition ending on the event day is allowed; one day later is not.
    c = cfg()
    for key in ('gorkha_2015', 'far_western_nepal'):
        c['registry']['datasets'][key]['earliest_event_date'] = None
    c['dem']['acquisition_end'] = c['registry']['datasets']['rer2023']['earliest_event_date']
    G.validate(c)
    c['dem']['acquisition_end'] = '2023-05-02'
    with pytest.raises(ValueError, match='rer2023: DEM acquired after'):
        G.validate(c)


def test_registered_dem_predates_every_development_event():
    first = [d['earliest_event_date'] for d in CFG['registry']['datasets'].values() if d['role'] == 'development']
    assert all(CFG['dem']['acquisition_end'] < f for f in first)


def test_training_datasets_never_include_sealed():
    for arm, members in CFG['arms'].items():
        if isinstance(members, list):
            assert SEALED not in G.training_datasets(CFG, arm)
    with pytest.raises(ValueError):
        G.training_datasets(broken(lambda c: c['arms']['MODEL_D'].append(SEALED)), 'MODEL_D')


def test_amendment_fills_placeholder_only():
    c = G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 120}}])
    assert c['sampling']['background_rule']['exclusion_buffer_m'] == 120
    with pytest.raises(ValueError, match='already registered'):
        G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.cell_m': 10}}])
    with pytest.raises(ValueError, match='unknown path'):
        G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.new_threshold': 1}}])
    with pytest.raises(ValueError, match='already registered'):
        G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 120}},
                                   {'id': 2, 'set': {'sampling.background_rule.exclusion_buffer_m': 60}}])


def test_correction_needs_current_value_and_reason():
    ok = {'id': 1, 'correct': {'sampling.cell_m': {'from': 30, 'to': 25, 'reason': 'test'}}}
    assert G.apply_amendments(cfg(), [ok])['sampling']['cell_m'] == 25
    with pytest.raises(ValueError, match='not 31'):
        G.apply_amendments(cfg(), [{'id': 1, 'correct': {'sampling.cell_m': {'from': 31, 'to': 25, 'reason': 'x'}}}])
    with pytest.raises(ValueError, match='needs a reason'):
        G.apply_amendments(cfg(), [{'id': 1, 'correct': {'sampling.cell_m': {'from': 30, 'to': 25, 'reason': ' '}}}])
    with pytest.raises(ValueError, match='already exists'):
        G.apply_amendments(cfg(), [{'id': 1, 'add': {'sampling.cell_m': {'value': 1, 'reason': 'x'}}}])
    with pytest.raises(ValueError, match='needs a reason'):
        G.apply_amendments(cfg(), [{'id': 1, 'add': {'sampling.new_key': {'value': 1}}}])
    assert G.apply_amendments(cfg(), [{'id': 1, 'add': {'sampling.new_key': {'value': 1, 'reason': 'x'}}}])['sampling']['new_key'] == 1


def test_changed_config_and_tampered_amendment_are_refused(tmp_path):
    conf, reg, rep = tmp_path / 'c.json', tmp_path / 'r.json', tmp_path / 'rep'
    rep.mkdir()
    conf.write_bytes(json.dumps(CFG).encode())
    reg.write_text(json.dumps({'config_sha256': P.text_sha(conf)}))
    assert P.config(conf, reg, rep)
    am = rep / 'AMENDMENT_1.json'
    am.write_text(json.dumps({'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 120}}))
    am.with_suffix('.sha256').write_text(P.text_sha(am))
    assert P.config(conf, reg, rep)['sampling']['background_rule']['exclusion_buffer_m'] == 120
    am.write_text(json.dumps({'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 60}}))
    with pytest.raises(RuntimeError, match='write-once'):
        P.config(conf, reg, rep)
    am.unlink()
    conf.write_bytes(json.dumps({**CFG, 'seeds': {}}).encode())
    with pytest.raises(RuntimeError, match='changed after pre-registration'):
        P.config(conf, reg, rep)


def test_text_hash_ignores_crlf(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_bytes(b'{\n "x": 1\n}\n')
    b.write_bytes(b'{\r\n "x": 1\r\n}\r\n')
    assert P.text_sha(a) == P.text_sha(b)


@pytest.mark.parametrize('name', ['../evil.shp', 'a/../../evil', '/abs/x.shp', 'C:/x.shp', '\\\\server\\x'])
def test_archive_members_cannot_escape(name):
    with pytest.raises(RuntimeError, match='unsafe'):
        I.safe_members(['ok/x.shp', name])


def test_polygon_area_from_geographic_crs_matches_utm():
    # 1 km x 1 km square built in UTM 44N (Far-Western Nepal), stored as lon/lat, measured again.
    utm, wgs = CRS.from_epsg(32644), CRS.from_epsg(4326)
    square = box(500000, 3200000, 501000, 3201000)
    lonlat = I.reproject(square, Transformer.from_crs(utm, wgs, always_xy=True).transform)
    areas, metric_crs, invalid, null = I.polygon_areas_m2([lonlat, None], wgs)
    assert metric_crs.to_epsg() == 32644 and invalid == 0 and null == 1
    assert areas[0] == pytest.approx(1e6, rel=1e-6)
    # Projected metre CRS is used unchanged.
    areas, metric_crs, _, _ = I.polygon_areas_m2([square], utm)
    assert metric_crs == utm and areas[0] == pytest.approx(1e6)


def test_latlon_swap_is_not_silently_accepted():
    # Swapped axis order lands far outside the UTM zone of the true location.
    _, wrong = I.metric_transformer(CRS.from_epsg(4326), 28.9, 81.0)
    _, right = I.metric_transformer(CRS.from_epsg(4326), 81.0, 28.9)
    assert right.to_epsg() == 32644 and wrong.to_epsg() != 32644


@pytest.mark.parametrize('rel', ['data/v04/x', 'reports/v05/x', 'models/v04', 'reports/baseline', 'data/susceptibility_v02', 'config'])
def test_guard_refuses_paths_outside_namespace(rel, monkeypatch):
    # A broken guard must not create directories in frozen trees while the test runs.
    def no_mkdir(*a, **k):
        raise AssertionError('guard tried to create a directory outside the namespace')
    monkeypatch.setattr(P.Path, 'mkdir', no_mkdir)
    with pytest.raises(RuntimeError):
        P.guard(ROOT / rel)


# ---------- Phase 2: terrain ----------

from rasterio.transform import from_origin  # noqa: E402

from preslide.matching import angular_distance  # noqa: E402
from preslide.susceptibility import terrain as T  # noqa: E402

TERRAIN = P.config()['terrain']


def test_dem_date_rule_is_strict():
    c = cfg()
    T.check_dem_date(c, 'gorkha_2015')
    c['dem']['acquisition_end'] = c['registry']['datasets']['gorkha_2015']['earliest_event_date']
    with pytest.raises(ValueError, match='not before'):
        T.check_dem_date(c, 'gorkha_2015')
    c['registry']['datasets']['gorkha_2015']['earliest_event_date'] = None
    with pytest.raises(ValueError):
        T.check_dem_date(c, 'gorkha_2015')


def test_reprojection_keeps_lon_lat_order():
    # z = 1000*lon + 10*lat on a geographic grid; the UTM grid must reproduce it at each cell centre.
    res_deg = 1 / 3600
    lon0, lat1 = 81.0, 29.2
    rows = cols = 720
    lat = lat1 - (np.arange(rows) + 0.5) * res_deg
    lon = lon0 + (np.arange(cols) + 0.5) * res_deg
    src = (1000 * lon[None, :] + 10 * lat[:, None]).astype('float32')
    tr = Transformer.from_crs(4326, 32644, always_xy=True)
    x0, y0 = tr.transform(81.05, 29.15)
    left, top = math.floor(x0 / 30) * 30, math.ceil(y0 / 30) * 30
    dst = T.reproject_to_grid(src, from_origin(lon0, lat1, res_deg, res_deg), 'EPSG:4326', left, top, (100, 100),
                              'EPSG:32644', 30, -32768)
    back = Transformer.from_crs(32644, 4326, always_xy=True)
    for r, c in [(5, 5), (50, 80), (95, 10)]:
        lo, la = back.transform(left + (c + 0.5) * 30, top - (r + 0.5) * 30)
        assert dst[r, c] == pytest.approx(1000 * lo + 10 * la, abs=0.05)


def plane(rows, cols, dz_south, dz_east, res=30.0):
    r, c = np.mgrid[0:rows, 0:cols]
    return (r * res * dz_south + c * res * dz_east + 1000).astype('float32')


def test_slope_and_circular_aspect_on_planes():
    north = T.window_features(plane(60, 60, math.tan(math.radians(30)), 0), 30, TERRAIN)[0]
    east = T.window_features(plane(60, 60, 0, -math.tan(math.radians(20))), 30, TERRAIN)[0]
    core = (slice(10, 50), slice(10, 50))
    assert np.nanmedian(north['slope_deg'][core]) == pytest.approx(30, abs=0.01)
    assert np.nanmedian(north['aspect_cos'][core]) == pytest.approx(1, abs=1e-6)   # faces north (downslope to row 0)
    assert np.nanmedian(east['aspect_sin'][core]) == pytest.approx(1, abs=1e-6)    # faces east
    assert angular_distance(359, 1) == 2 and angular_distance(10, 350) == 20


def test_catchment_truncation_is_nan_not_guessed():
    r, c = np.mgrid[0:61, 0:61]
    cone = (2000 - 30 * np.hypot(r - 30, c - 30)).astype('float32')
    f = T.window_features(cone, 30, TERRAIN)[0]
    assert np.isfinite(f['log10_catchment_m2'][20:41, 20:41]).all()
    tilted = T.window_features(plane(40, 40, -0.3, 0.01), 30, TERRAIN)[0]   # drains to row 0 across the edge
    assert np.isnan(tilted['log10_catchment_m2'][1:-1, 1:-1]).mean() > 0.9
    assert np.isnan(tilted['twi']).sum() == np.isnan(tilted['log10_catchment_m2']).sum()


def test_block_grid_is_aligned_and_covers_bounds():
    blocks = T.block_grid((516935.0, 3287900.0, 548000.0, 3302915.0), 15000, 30)
    assert all(b[2] % 30 == 0 and b[5] % 30 == 0 for b in blocks)
    assert min(b[2] for b in blocks) <= 516935 and max(b[4] for b in blocks) >= 548000
    assert min(b[3] for b in blocks) <= 3287900 and max(b[5] for b in blocks) >= 3302915


def test_corrupted_feature_block_is_rejected(tmp_path):
    path = tmp_path / 'block.tif'
    path.write_bytes(b'raster')
    path.with_suffix('.json').write_text(json.dumps({'sha256': 'wrong'}))
    with pytest.raises(T.CacheCorruption):
        T.load_block(path)
