"""Pipeline B (satellite) tests: isolation from the precursor pipeline, temporal ordering, grid alignment, quality
masks, box-filter features, event holdout and the write guard. Synthetic arrays are fixtures only."""
import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from preslide.sources import ROOT
from preslide.satellite import imagery, features, selection, stac
from preslide.satellite.paths import guard, config
from preslide.satellite.baseline import cross_validated_scores, within_group_metrics

CFG = config()


# ---------- isolation of Pipeline A from post-event imagery ----------

def _imports(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append((node.module or '') + ('.' * node.level))
    return names


def test_precursor_pipeline_never_imports_satellite_package():
    for path in list((ROOT / 'preslide').glob('*.py')) + list((ROOT / 'preslide/v04').glob('*.py')):
        assert not any('satellite' in n for n in _imports(path)), f'{path} imports Pipeline B'


def test_v04_dataset_has_no_satellite_columns():
    path = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'
    if not path.exists():
        pytest.skip('local V0.4 dataset required')
    cols = pd.read_parquet(path).columns
    assert not any(c.startswith(('d_ndvi', 'd_nbr', 'd_bsi', 'before_ndvi', 'after_', 'coreg_')) for c in cols)


def test_guard_refuses_pipeline_a_paths(tmp_path):
    for bad in ['data/v04/x', 'data/processed/x', 'reports/v04/x', 'models/x', 'data/raw/x']:
        with pytest.raises(RuntimeError):
            guard(ROOT / bad)
    assert guard(ROOT / 'data/satellite/_guard_test').exists()


# ---------- temporal ordering of acquisitions ----------

def _item(d, item_id=None):
    return {'id': item_id or f'I{d}', 'collection': 'c', 'datetime': f'{d}T10:00:00Z', 'date': d, 'epsg': 32633,
            'grid_code': 'MGRS-33TWN', 'processing_baseline': '05.00', 'bbox': [15, 47, 16, 48],
            'assets': {k: {'href': '', 'scale': 1e-4, 'offset': -0.1, 'nodata': 0} for k in stac.ASSET_NAMES}}


def test_before_strictly_before_and_after_strictly_after_event_day(monkeypatch):
    items = [_item(d) for d in ['2023-07-01', '2023-07-29', '2023-08-03', '2023-08-05', '2023-08-06', '2023-08-30']]
    clear = {'core': {'cloud': 0, 'snow': 0, 'invalid': 0}, 'medium': {'cloud': 0, 'snow': 0, 'invalid': 0}, 'patch': {'cloud': 0, 'snow': 0, 'invalid': 0}}
    monkeypatch.setattr(selection, 'quicklook', lambda sid, item, grid: dict(clear))
    monkeypatch.setattr(selection, 'event_grid', lambda lon, lat, epsg=None: imagery.Grid(32633, 0, 0, 10, 256, 0, 0))
    sel = selection.select_acquisitions('t', 15.5, 47.5, '2023-08-05', items=items)
    s = sel['selected']
    assert s['before_primary']['datetime'][:10] == '2023-08-03' and s['before_primary']['days_from_event'] == -2
    assert s['after_primary']['datetime'][:10] == '2023-08-06' and s['after_primary']['days_from_event'] == 1
    assert sel['same_day_items_excluded'] == ['I2023-08-05']
    assert s['before_reference']['datetime'][:10] == '2023-07-01'     # 07-29 is only 5 d before primary (< 30 d gap)
    assert s['after_confirm']['datetime'][:10] == '2023-08-30'


def test_cloudy_core_is_rejected_even_when_scene_is_clear(monkeypatch):
    items = [_item('2023-08-03'), _item('2023-08-06')]
    clear = {'cloud': 0, 'snow': 0, 'invalid': 0}
    q = {'I2023-08-03': {'core': {'cloud': 0.5, 'snow': 0, 'invalid': 0}, 'medium': clear, 'patch': {'cloud': 0.01, 'snow': 0, 'invalid': 0}},
         'I2023-08-06': {'core': {'cloud': 0, 'snow': 0.3, 'invalid': 0}, 'medium': clear, 'patch': {'cloud': 0, 'snow': 0.02, 'invalid': 0}}}
    monkeypatch.setattr(selection, 'quicklook', lambda sid, item, grid: q[item['id']])
    monkeypatch.setattr(selection, 'event_grid', lambda lon, lat, epsg=None: imagery.Grid(32633, 0, 0, 10, 256, 0, 0))
    sel = selection.select_acquisitions('t', 15.5, 47.5, '2023-08-05', items=items)
    assert sel['selected'] == {}
    assert {x['reason'] for x in sel['screened']} == {'core_cloud', 'core_snow'}


def test_group_acquisition_requires_controls_on_same_overpass(monkeypatch):
    items = [_item('2023-08-03'), _item('2023-07-29'), _item('2023-08-06')]
    clear = {'cloud': 0, 'snow': 0, 'invalid': 0}
    cloudy = {'cloud': 1.0, 'snow': 0, 'invalid': 0}

    def ql(sid, item, grid):
        # 08-03: positive clear, every control cloudy -> rejected for the group; 07-29: all clear.
        if item['id'] == 'I2023-08-03' and sid != 'pos':
            return {'core': cloudy, 'medium': cloudy, 'patch': cloudy}
        return {'core': clear, 'medium': clear, 'patch': clear}

    monkeypatch.setattr(selection, 'quicklook', ql)
    monkeypatch.setattr(selection, 'event_grid', lambda lon, lat, epsg=None: imagery.Grid(32633, 0, 0, 10, 256, 0, 0))
    monkeypatch.setattr(selection.stac, 'search', lambda *a, **k: [])
    members = [(f'c{i}', 15.5, 47.5) for i in range(5)]
    sel = selection.select_acquisitions('pos', 15.5, 47.5, '2023-08-05', members=members, items=items)
    assert sel['selected']['before_primary']['datetime'][:10] == '2023-07-29'
    assert [x for x in sel['screened'] if x['item_id'] == 'I2023-08-03'][0]['reason'] == 'controls_usable_0_of_5'
    assert sel['usable_controls'] == [f'c{i}' for i in range(5)]
    assert set(sel['control_items']['before_primary']) == set(sel['usable_controls'])


def test_eligibility_records_reasons_not_silent_drops():
    row = {'event_group_id': 'E', 'event_day': '2016-07-25', 'latitude': 47.0, 'longitude': 15.0, 'source_position_upper_m': 100,
           'time_quality': 'day', 'process_type': 'x', 'state': 'S', 'independence_unit': 'U', 'partition': 'development'}
    rec = selection.eligibility_row(row, None)
    assert rec['usable'] is False and 'year_before_2018_no_l2a' in rec['exclusion_reason'] and 'position_coarse' in rec['exclusion_reason']


# ---------- grid and alignment ----------

def test_grid_is_snapped_to_sentinel2_pixel_lattice_and_centred():
    g = imagery.event_grid(15.9357607, 47.4795272)
    assert g.epsg == 32633 and g.x0 % 10 == 0 and g.y1 % 10 == 0 and g.n == 256
    r, c = g.centre_pixel()
    assert (r, c) == (128, 128)
    assert abs((g.x0 + g.n * g.res / 2) - g.cx) <= 10 and abs((g.y1 - g.n * g.res / 2) - g.cy) <= 10
    assert imagery.utm_epsg(11.9) == 32632 and imagery.utm_epsg(12.1) == 32633


def test_phase_correlation_recovers_known_shift():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(128, 128))
    from scipy.ndimage import gaussian_filter
    base = gaussian_filter(base, 2)
    shifted = np.roll(np.roll(base, 3, axis=0), -2, axis=1)
    dx, dy, ratio = imagery.coregistration_shift(base, shifted, np.ones_like(base, dtype=bool))
    assert (dx, dy) == (2, -3) or (dx, dy) == (-2, 3)
    assert ratio > 5


# ---------- quality masks ----------

def test_scl_metrics_count_cloud_shadow_snow_and_nodata():
    scl = np.zeros((10, 10), dtype=np.uint8) + 4
    scl[0, :2] = 9; scl[0, 2] = 3; scl[1, :4] = 11; scl[2, :3] = 0
    m = imagery.scl_metrics(scl)
    assert m['cloud'] == pytest.approx(0.03) and m['snow'] == pytest.approx(0.04) and m['invalid'] == pytest.approx(0.03)
    clear = {'cloud': 0, 'snow': 0, 'invalid': 0}
    ok, reason = imagery.usable({'core': {'cloud': 0.05, 'snow': 0, 'invalid': 0}, 'medium': clear, 'patch': clear})
    assert not ok and reason == 'core_cloud'
    ok, reason = imagery.usable({'core': clear, 'medium': {'cloud': 0.2, 'snow': 0, 'invalid': 0}, 'patch': clear})
    assert not ok and reason == 'window_cloud'
    ok, reason = imagery.usable({'core': clear, 'medium': clear, 'patch': {'cloud': 0.9, 'snow': 0, 'invalid': 0}})
    assert ok, 'the outer 2.56 km patch is recorded but not required'


def test_ndsi_snow_detects_bright_snow_missed_by_scl():
    green = np.array([[0.6, 0.05, 0.3]]); swir = np.array([[0.1, 0.04, 0.25]]); nir = np.array([[0.7, 0.05, 0.4]])
    snow = imagery.ndsi_snow(green, swir, nir)
    assert snow.tolist() == [[True, False, False]]      # bright snow yes; dark pixel below NIR floor no; vegetation no
    q = {'core': {'cloud': 0, 'snow': 0.0, 'invalid': 0, 'snow_ndsi': 0.9}, 'medium': {'cloud': 0, 'snow': 0, 'invalid': 0, 'snow_ndsi': 0.9},
         'patch': {'cloud': 0, 'snow': 0, 'invalid': 0}}
    assert imagery.usable(q) == (False, 'core_snow_ndsi')


def test_seasonal_gap_is_recorded_and_excluded(monkeypatch):
    items = [_item('2021-11-24'), _item('2022-03-24')]
    clear = {'cloud': 0, 'snow': 0, 'invalid': 0, 'snow_ndsi': 0}
    monkeypatch.setattr(selection, 'quicklook', lambda sid, item, grid: {'core': clear, 'medium': clear, 'patch': clear})
    monkeypatch.setattr(selection, 'event_grid', lambda lon, lat, epsg=None: imagery.Grid(32633, 0, 0, 10, 256, 0, 0))
    sel = selection.select_acquisitions('t', 15.5, 47.5, '2022-02-21', items=items)
    assert sel['doy_gap_days'] == 120
    row = {'event_group_id': 'E', 'event_day': '2022-02-21', 'latitude': 47.0, 'longitude': 15.0, 'source_position_upper_m': 5,
           'time_quality': 'day', 'process_type': 'x', 'state': 'S', 'independence_unit': 'U', 'partition': 'development'}
    rec = selection.eligibility_row(row, sel)
    assert rec['usable'] is False and rec['exclusion_reason'] == 'seasonal_gap_gt_90d'


def test_reflectance_offset_depends_on_collection_not_on_advertised_metadata(monkeypatch):
    grid = imagery.Grid(32633, 0, 0, 10, 256, 0, 0)
    # Collection-1 COG: vegetation green DN 1400 carries the +1000 offset -> 0.04
    item = _item('2023-08-03'); item['collection'] = 'sentinel-2-c1-l2a'
    dn = np.full((256, 256), 1400, dtype=np.uint16); dn[0, 0] = 0
    monkeypatch.setattr(imagery, '_read_on_grid', lambda href, grid, resampling: dn if resampling.name == 'bilinear' else np.full((256, 256), 4, np.uint8))
    refl, scl = imagery.read_reflectance(item, grid)
    assert refl[1, 1, 1] == pytest.approx(0.04) and np.isnan(refl[0, 0, 0])
    # Original collection COG: the same vegetation is stored as DN 400 without the offset, although metadata says -0.1
    item2 = _item('2023-08-03'); item2['collection'] = 'sentinel-2-l2a'
    dn2 = np.full((256, 256), 400, dtype=np.uint16)
    monkeypatch.setattr(imagery, '_read_on_grid', lambda href, grid, resampling: dn2 if resampling.name == 'bilinear' else np.full((256, 256), 4, np.uint8))
    refl2, _ = imagery.read_reflectance(item2, grid)
    assert refl2[1, 1, 1] == pytest.approx(0.04)
    # A wrong offset would give negative vegetation reflectance: refused.
    item3 = _item('2023-08-03'); item3['collection'] = 'sentinel-2-c1-l2a'
    with pytest.raises(RuntimeError, match='radiometric offset'):
        imagery.read_reflectance(item3, grid)
    item['assets']['red']['scale'] = None
    with pytest.raises(RuntimeError, match='scale'):
        imagery.read_reflectance(item, grid)


# ---------- features ----------

def test_box_stats_match_explicit_window_computation():
    rng = np.random.default_rng(1)
    v = rng.normal(size=(64, 64)); valid = rng.random((64, 64)) > 0.2
    st = features.box_stats(v, valid, 8, 24)
    r, c = 32, 32
    core = v[r - 4:r + 4, c - 4:c + 4]; cm = valid[r - 4:r + 4, c - 4:c + 4]
    big = v[r - 12:r + 12, c - 12:c + 12]; bm = valid[r - 12:r + 12, c - 12:c + 12]
    assert st['core_mean'][r, c] == pytest.approx(core[cm].mean())
    assert st['core_std'][r, c] == pytest.approx(core[cm].std())
    ring_sum = big[bm].sum() - core[cm].sum(); ring_n = bm.sum() - cm.sum()
    assert st['ring_mean'][r, c] == pytest.approx(ring_sum / ring_n)


def test_contrast_isolates_local_change_from_scene_wide_change():
    n = 128
    before = np.full((6, n, n), 0.1, dtype=np.float32); before[3] = 0.5          # vegetated: NIR 0.5, red 0.1
    after = before.copy(); after[3] = 0.4                                      # scene-wide NIR drop (season)
    after[3, 60:68, 60:68] = 0.15; after[2, 60:68, 60:68] = 0.2                # local bare patch at centre
    scl = np.full((n, n), 4, np.uint8)
    maps = features.feature_maps(before, after, scl, scl, res_m=10.0)
    assert maps['d_ndvi_small_contrast'][64, 64] < -0.2                       # 80 m scar fills 44 % of the 120 m window
    assert maps['d_ndvi_small_frac'][64, 64] > 0.4 and maps['d_ndvi_core_frac'][64, 64] == pytest.approx(64 / 1024)
    assert abs(maps['d_ndvi_contrast'][20, 20]) < 0.02                        # no local change away from the patch
    assert maps['d_ndvi_ring_mean'][64, 64] < 0                               # the seasonal drop sits in the ring


# ---------- event holdout ----------

def test_no_independence_unit_in_train_and_test():
    rng = np.random.default_rng(0)
    rows = []
    for u in range(6):
        for g in range(3):
            for k in range(6):
                rows.append({'event_group_id': f'U{u}G{g}', 'independence_unit': f'U{u}', 'label': int(k == 0),
                             'f1': rng.normal() + (k == 0), 'f2': rng.normal()})
    frame = pd.DataFrame(rows)
    s = cross_validated_scores(frame, ['f1', 'f2'], 'logistic_regression', CFG)   # asserts unit separation internally
    assert np.isfinite(s).all()
    m = within_group_metrics(frame, s)
    assert m['groups'] == 18 and 0 <= m['within_group_auc'] <= 1


def test_within_group_auc_definition():
    frame = pd.DataFrame({'event_group_id': ['a'] * 6, 'label': [1, 0, 0, 0, 0, 0]})
    assert within_group_metrics(frame, np.array([0.9, 0.1, 0.2, 0.3, 0.4, 0.5]))['within_group_auc'] == 1.0
    assert within_group_metrics(frame, np.array([0.3, 0.1, 0.2, 0.4, 0.5, 0.6]))['top1_rate'] == 0.0
    assert within_group_metrics(frame, np.array([0.3, 0.1, 0.2, 0.4, 0.5, 0.6]))['within_group_auc'] == pytest.approx(0.4)
