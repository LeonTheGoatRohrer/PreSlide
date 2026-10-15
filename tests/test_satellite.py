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


# ---------- satellite-0.2: known-event suppression, hard negatives, candidate validation ----------

def test_suppression_removes_peaks_at_other_known_events_but_keeps_the_search_centre():
    from preslide.satellite import discovery
    other_px = [(60, 60), (130, 125)]                             # one far from the centre, one 5 px (50 m) from it
    pk = [(9.0, 60, 61), (8.0, 129, 127), (7.0, 200, 200)]
    kept, suppressed = discovery.suppress_near_known(pk, other_px, radius_px=16, centre=(128, 128), hit_px=16)
    assert [p[1:] for p in suppressed] == [(60, 61)]              # the peak at the other documented event is removed
    assert [p[1:] for p in kept] == [(129, 127), (200, 200)]      # the centre hit survives although a neighbour is within 160 m
    # Injected bug check: without centre priority the hit would be lost.
    kept2, _ = discovery.suppress_near_known(pk, other_px, radius_px=16)
    assert (129, 127) not in [p[1:] for p in kept2]
    # No known events -> nothing changes.
    assert discovery.suppress_near_known(pk, [], 16, (128, 128), 16) == (pk, [])


def test_known_pixels_excludes_the_search_event_and_points_outside_the_grid():
    from preslide.satellite import discovery
    g = imagery.event_grid(15.9357607, 47.4795272)
    known = pd.DataFrame({'event_group_id': ['self', 'near', 'far'], 'longitude': [15.9357607, 15.9370, 16.5],
                          'latitude': [47.4795272, 47.4800, 47.0]})
    px = discovery.known_pixels(g, known, exclude_event='self')
    assert len(px) == 1 and all(0 <= v < g.n for v in px[0])
    assert len(discovery.known_pixels(g, known)) == 2


def test_random_landscape_geometry_rules():
    from preslide.satellite import landscape
    rl = {'min_distance_m': 1500, 'max_distance_m': 8000}
    rng = np.random.default_rng(3)
    pts = landscape.draw_points(500000.0, 300000.0, rng, 400, rl)
    assert pts['distance_to_positive_m'].between(1500, 8000).all()
    # exclusion: everything east of the positive is 'near a known event'; country: everything north of y=300000
    allowed = lambda xy: np.asarray(xy)[:, 0] <= 500000.0
    out = landscape.geometric_filter(pts, allowed, lambda lon, lat: pts['y'].to_numpy() >= 300000.0, separation_m=400)
    kept = out[out['geometry_reason'] == '']
    assert (kept['x'] <= 500000.0).all() and (kept['y'] >= 300000.0).all()
    assert set(out['geometry_reason']) <= {'', 'within_exclusion_radius_of_known_event', 'outside_austria', 'too_close_to_other_random_point'}
    from scipy.spatial.distance import pdist
    assert len(kept) < 2 or pdist(kept[['x', 'y']].to_numpy()).min() >= 400
    assert (out['geometry_reason'] == 'within_exclusion_radius_of_known_event').sum() > 0


def test_random_landscape_table_check_fails_on_injected_violations():
    from preslide.satellite import landscape
    cfg = {'random_landscape': {'min_distance_m': 1500, 'max_distance_m': 8000, 'min_distance_to_any_known_event_m': 400}}
    frame = pd.DataFrame({'event_group_id': ['E1'], 'label': [1], 'before_datetime': ['2023-08-03T10:00:00Z'], 'after_datetime': ['2023-08-06T10:00:00Z']})
    good = pd.DataFrame({'event_group_id': ['E1', 'E1'], 'label': [0, 0], 'sample_type': ['RANDOM_LANDSCAPE'] * 2,
                         'distance_to_positive_m': [2000.0, 7000.0], 'distance_to_nearest_inventory_event_m': [900.0, 450.0],
                         'before_datetime': ['2023-08-03T10:00:00Z'] * 2, 'after_datetime': ['2023-08-06T10:00:00Z'] * 2})
    assert landscape.check_random_landscape_table(good, frame, cfg)
    for col, val in [('distance_to_positive_m', 900.0), ('distance_to_nearest_inventory_event_m', 100.0),
                     ('after_datetime', '2023-09-01T10:00:00Z'), ('label', 1), ('sample_type', 'CONTROL_PSEUDO_NEGATIVE')]:
        bad = good.copy(); bad.loc[0, col] = val
        with pytest.raises(RuntimeError):
            landscape.check_random_landscape_table(bad, frame, cfg)


def test_cross_validated_scores_fit_mask_excludes_rows_from_training_only():
    rng = np.random.default_rng(0)
    rows = []
    for u in range(6):
        for g in range(2):
            for k in range(8):
                rows.append({'event_group_id': f'U{u}G{g}', 'independence_unit': f'U{u}', 'label': int(k == 0),
                             'sample_type': 'RANDOM_LANDSCAPE' if k >= 6 else 'x', 'f1': rng.normal() + (k == 0) + 5 * (k >= 6), 'f2': rng.normal()})
    frame = pd.DataFrame(rows)
    mask = (frame['sample_type'] != 'RANDOM_LANDSCAPE').to_numpy()
    s_without = cross_validated_scores(frame, ['f1', 'f2'], 'logistic_regression', CFG, fit_mask=mask)
    s_with = cross_validated_scores(frame, ['f1', 'f2'], 'logistic_regression', CFG)
    assert np.isfinite(s_without).all() and np.isfinite(s_with).all()
    # The random rows have a huge f1: a model that never saw them scores them high; one trained on them does not.
    assert s_without[~mask].mean() > s_with[~mask].mean()


def test_persistence_rule_and_status_assignment():
    from preslide.satellite import validation
    vcfg = {'min_retained_contrast': 0.5, 'min_valid_core_frac': 0.9, 'min_valid_ring_frac': 0.8}
    primary = {'d_ndwi_contrast': 0.0, 'd_ndvi_small_contrast': -0.3, 'd_bsi_small_contrast': 0.2, 'd_brightness_contrast': 0.01}
    confirm_ok = {'valid_core_frac': 1.0, 'valid_ring_frac': 1.0, 'd_ndvi_small_contrast': -0.2, **{k: 0 for k in ('d_ndwi_contrast', 'd_bsi_small_contrast', 'd_brightness_contrast')}}
    assessable, persists, main, retained = validation.persistence_rule(primary, confirm_ok, score_confirm=2.0, vcfg=vcfg)
    assert assessable and persists and main == 'd_ndvi_small_contrast' and retained == pytest.approx(2 / 3)
    # regrowth: contrast mostly gone -> not persistent even with positive log-odds
    confirm_gone = dict(confirm_ok, d_ndvi_small_contrast=-0.1)
    assert validation.persistence_rule(primary, confirm_gone, 2.0, vcfg)[1] is False
    # negative log-odds -> not persistent
    assert validation.persistence_rule(primary, confirm_ok, -0.5, vcfg)[1] is False
    # cloud at the candidate -> not assessable, never persistent
    cloudy = dict(confirm_ok, valid_core_frac=0.5)
    assert validation.persistence_rule(primary, cloudy, 5.0, vcfg)[:2] == (False, False)
    # water signature takes precedence as the main feature
    assert validation.main_contrast_feature(dict(primary, d_ndwi_contrast=0.2)) == 'd_ndwi_contrast'
    # statuses
    assert validation.assign_status(True, True, 'slide_like', 'fresh scar on slope') == 'LIKELY'
    assert validation.assign_status(True, True, 'slide_like', '') == 'UNVERIFIED'           # no note, no status
    assert validation.assign_status(True, False, 'slide_like', 'scar') == 'UNVERIFIED'      # not persistent -> not LIKELY
    assert validation.assign_status(False, False, 'slide_like', 'scar') == 'UNVERIFIED'     # not assessable -> not LIKELY
    assert validation.assign_status(True, False, 'transient_artifact', 'mown meadow') == 'REJECTED'
    assert validation.assign_status(True, True, 'transient_artifact', 'mown meadow') == 'UNVERIFIED'   # persisted: contradiction
    assert validation.assign_status(False, False, 'non_slide_land_use', 'clear-cut') == 'REJECTED'
    assert validation.assign_status(True, True, 'water_change', 'river bank') == 'REJECTED'
    assert validation.assign_status(True, True, 'ambiguous', 'unclear') == 'UNVERIFIED'
    assert validation.assign_status(True, True, 'made_up_verdict', 'x') == 'UNVERIFIED'


def test_physical_candidates_dedup_and_known_exclusion():
    from preslide.satellite import validation
    inv = pd.DataFrame({'candidate_id': ['A', 'B', 'C', 'D'], 'model_score': [10.0, 9.0, 8.0, 7.0],
                        'longitude': [15.0, 15.0005, 15.1, 15.2], 'latitude': [47.0, 47.0, 47.0, 47.0]})     # A and B ~38 m apart
    known = pd.DataFrame({'event_group_id': ['K'], 'longitude': [15.1001], 'latitude': [47.0]})               # ~8 m from C
    out = validation.physical_candidates(inv, known, min_sep_m=160, exclude_within_known_m=160)
    assert list(out['candidate_id']) == ['A', 'D']
    assert list(out['aliases'].iloc[0]) == ['B'] and out['n_detections'].iloc[0] == 2
    assert out['excluded_near_known_positive'].iloc[0] == 1
    assert (out['nearest_v04_positive_m'] > 160).all()


def test_candidate_statuses_are_from_the_configured_list_and_pipeline_a_tables_untouched():
    path = ROOT / 'data/satellite/tables/candidate_inventory.parquet'
    if not path.exists():
        pytest.skip('local candidate inventory required')
    inv = pd.read_parquet(path)
    assert set(inv['validation_status']) <= set(CFG['candidate_status'])
    assert (inv['label'] == 'satellite_detected_candidate').all()
    v04 = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'
    if v04.exists():
        d = pd.read_parquet(v04)
        assert not d['sample_type'].isin(['RANDOM_LANDSCAPE', 'satellite_detected_candidate']).any()
        assert int(d['label'].sum()) == 423


def test_embedding_chip_is_normalised_and_nan_free():
    from preslide.satellite import embeddings
    g = imagery.Grid(32633, 0, 2560, 10, 256, 1280, 1280)
    refl = np.full((6, 256, 256), 0.1, dtype=np.float32); refl[:, 0, 0] = np.nan; refl[0, 100, 100] = 5.0
    chip = embeddings.rgb_chip(refl, g)
    assert chip.shape == (3, 96, 96) and np.isfinite(chip).all()
    assert chip[2, 30, 30] == pytest.approx((0.1 / 0.3 - 0.406) / 0.225)      # blue channel is index 2
    assert chip[2, 20, 20] == pytest.approx((1.0 - 0.406) / 0.225)               # clipped bright pixel at (100, 100)


# ---------- satellite-0.3: whole-patch buffered cloud mask ----------

def _cloud_edge_pair(n=256, blob=(108, 132), scl_margin=8):
    """Vegetated scene; in `after` a thin bright cloud 24 px (240 m) across of which Sen2Cor classified only the 8 px
    core (the outer `scl_margin` = 80 m stay SCL 4): the unclassified rim is what produced the satellite-0.2 false peaks.
    A rim wider than the buffer is not covered by design (documented limit)."""
    before = np.full((6, n, n), 0.1, dtype=np.float32); before[3] = 0.5
    after = before.copy()
    a, b = blob
    after[:, a:b, a:b] = 0.6                                   # bright in every band: NDVI collapses, brightness jumps
    scl_b = np.full((n, n), 4, np.uint8)
    scl_a = scl_b.copy()
    scl_a[a + scl_margin:b - scl_margin, a + scl_margin:b - scl_margin] = 9      # only the cloud interior is classified
    return before, after, scl_b, scl_a


def test_buffer_mask_radius_covers_scl_cloud_and_ndsi_snow_but_not_nodata():
    n = 128
    refl = np.full((6, n, n), 0.1, dtype=np.float32); refl[3] = 0.5
    scl = np.full((n, n), 4, np.uint8)
    scl[50, 50] = 9                                             # one classified cloud pixel
    refl[1, 20, 20], refl[4, 20, 20], refl[3, 20, 20] = 0.6, 0.1, 0.7      # bright NDSI snow, SCL says vegetation
    scl[100, 100] = 0                                           # nodata: excluded itself, not buffered
    v = features.valid_mask(refl, scl, buffer_px=10, buffer_classes=CFG['discovery']['cloud_buffer_scl_classes'])
    assert not v[50, 50] and not v[50, 60] and v[50, 61]        # inclusive 10 px radius (100 m)
    assert not v[57, 57] and v[58, 58]                          # Euclidean: 9.9 px masked, 11.3 px valid
    assert not v[20, 20] and not v[20, 30] and v[20, 31]        # NDSI snow is buffered too
    assert not v[100, 100] and v[100, 101]                      # nodata pixel excluded, neighbour untouched
    plain = features.valid_mask(refl, scl)
    assert not plain[50, 50] and plain[50, 51] and not plain[20, 20] and plain[20, 21]
    assert features.buffer_px_for(100, 10.0) == 10 and features.buffer_px_for(95, 10.0) == 10 and features.buffer_px_for(0, 10.0) == 0


def test_cloud_buffer_removes_synthetic_cloud_edge_peak():
    from preslide.satellite import discovery
    before, after, scl_b, scl_a = _cloud_edge_pair()
    d = CFG['discovery']
    assert d['cloud_buffer_m'] >= 100
    unbuffered = features.feature_maps(before, after, scl_b, scl_a, 10.0, cloud_buffer_m=0)
    buffered = features.feature_maps(before, after, scl_b, scl_a, 10.0, cloud_buffer_m=d['cloud_buffer_m'])
    # The unclassified cloud rim (8 px) is a strong local NDVI loss in the unbuffered maps: a cloud-edge peak.
    def score(maps, mask=None):
        v = maps['d_ndvi_small_contrast']
        ok = np.isfinite(v) if mask is None else (np.isfinite(v) & mask)
        s = np.where(ok, -v, -np.inf)                                  # NDVI loss scores high; unusable positions never peak
        s[:48, :] = s[-48:, :] = s[:, :48] = s[:, -48:] = -np.inf
        return s
    s0 = score(unbuffered)
    pk0 = discovery.peaks(s0, 16, threshold=0.1)
    assert pk0, 'injected cloud edge must produce a peak without the buffer'
    sc, r, c = pk0[0]
    assert sc > 0.3 and 80 <= r <= 160 and 80 <= c <= 160          # the top peak sits at the cloud
    # With the buffer the rim is masked and positions whose core/ring lost too many pixels are not scorable.
    scorable = features.scorable_mask(buffered, d)
    pk1 = discovery.peaks(score(buffered, scorable), 16, threshold=0.1)
    assert not pk1, f'cloud-edge peak survived the buffer: {pk1[:3]}'
    assert not scorable[r, c]
    # The buffer leaves cloud-free positions untouched and the pair mask reports what it removed.
    far = (200, 60)
    for k in ('d_ndvi_small_contrast', 'd_brightness_contrast', 'before_ndvi_core_mean'):
        assert buffered[k][far] == pytest.approx(unbuffered[k][far], nan_ok=True)
    assert scorable[far]
    valid, masked_frac = features.pair_valid_mask(before, after, scl_b, scl_a, d['cloud_buffer_m'], 10.0, d)
    expect = (28 ** 2 - 4 * (100 - np.pi * 25) - 8 ** 2) / 256 ** 2     # Euclidean 10 px buffer (rounded corners) around the 8 px SCL core, minus the core
    assert masked_frac == pytest.approx(expect, rel=0.1)                # discrete pixel disk vs continuous area
    # Injected-bug check: a 1 px buffer (10 m) leaves the rim scorable and the cloud-edge peak survives.
    short = features.feature_maps(before, after, scl_b, scl_a, 10.0, cloud_buffer_m=10)
    assert discovery.peaks(score(short, features.scorable_mask(short, d)), 16, 0.1)


def test_buffer_is_a_no_op_on_a_clean_pair_and_off_by_default():
    n = 128
    before = np.full((6, n, n), 0.1, dtype=np.float32); before[3] = 0.5
    after = before.copy(); after[3, 60:68, 60:68] = 0.15; after[2, 60:68, 60:68] = 0.2
    scl = np.full((n, n), 4, np.uint8)
    plain = features.feature_maps(before, after, scl, scl, 10.0)
    buffered = features.feature_maps(before, after, scl, scl, 10.0, cloud_buffer_m=100)
    for k in plain:
        np.testing.assert_array_equal(plain[k], buffered[k])
    assert features.pair_valid_mask(before, after, scl, scl, 100, 10.0, CFG['discovery'])[1] == 0.0
    import inspect
    assert inspect.signature(features.feature_maps).parameters['cloud_buffer_m'].default == 0   # training path stays unbuffered
    from preslide.satellite import dataset
    src = inspect.getsource(dataset.build_sample)
    assert 'cloud_buffer_m' not in src
