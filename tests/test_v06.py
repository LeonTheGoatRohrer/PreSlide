import numpy as np
import pandas as pd
import pytest

from preslide.v04.weather import expected_hours
from preslide.v06 import hydro

CFG = {'api_half_lives_days': [3, 14], 'max_sum_hours': [3, 6, 12, 24, 72], 'wet_day_thresholds_mm': [1, 10],
       'wet_day_windows_days': [14, 30, 60], 'dry_hour_threshold_mm': 0.1}
T0 = pd.Timestamp('2022-08-05T10:00:00Z')


def series(value=0.0, extra_after_hours=6):
    times = pd.date_range((T0 - pd.Timedelta(days=60)).floor('h') - pd.Timedelta(hours=3), T0 + pd.Timedelta(hours=extra_after_hours), freq='h')
    return times, np.full(len(times), float(value))


def admissible_index(times):
    return times.get_indexer(expected_hours(T0, hydro.WINDOW))


def test_no_hour_at_or_after_t0_is_used():
    times, rain = series(0.2)
    base = hydro.hydro_features(times, rain, T0, CFG)
    spiked = rain.copy()
    spiked[times >= T0 - pd.Timedelta(hours=1)] = 9999.0       # T + 1 h < t0 fails for these hours
    assert hydro.hydro_features(times, spiked, T0, CFG) == base
    last = times[admissible_index(times)[-1]]
    assert last + pd.Timedelta(hours=1) < T0


def test_boundary_hour_inside_window_does_change_features():
    times, rain = series(0.2)
    idx = admissible_index(times)
    changed = rain.copy()
    changed[idx[-1]] = 50.0                                       # last admissible hour must be used
    a, b = hydro.hydro_features(times, rain, T0, CFG), hydro.hydro_features(times, changed, T0, CFG)
    assert b['max_sum_3h'] > a['max_sum_3h'] and b['api_hl3d'] > a['api_hl3d'] and b['current_dry_spell_h'] == 0


def test_api_matches_closed_form_for_constant_rain():
    r = np.ones(1438)
    k = 0.5 ** (1 / 72)
    assert hydro.api(r, 3) == pytest.approx((1 - k ** 1438) / (1 - k))
    assert hydro.api(np.zeros(10), 3) == 0.0


def test_max_sum_location_and_ties():
    r = np.zeros(100)
    r[40:43] = [1, 5, 1]
    value, hours_before = hydro.max_rolling_sum(r, 3)
    assert value == 7 and hours_before == 100 - 43
    r2 = np.zeros(10)
    r2[2], r2[7] = 1, 1
    assert hydro.max_rolling_sum(r2, 1) == (1.0, 2)               # latest of the tied maxima


def test_wet_days_use_blocks_anchored_at_the_end():
    r = np.zeros(48 + 5)
    r[-1] = 12.0                                                   # last hour: falls in the final block
    r[-24] = 1.5                                                   # first hour of the final block (index -24)
    r[-25] = 3.0                                                   # last hour of the previous block
    blocks = hydro.blocks_24h(r)
    assert len(blocks) == 2 and blocks[-1] == pytest.approx(13.5) and blocks[-2] == pytest.approx(3.0)


def test_dry_spells_and_boundaries():
    assert hydro.longest_run(np.array([1, 1, 0, 1, 1, 1, 0], bool)) == 3
    assert hydro._leading_run(np.array([1, 1, 0], bool)) == 2
    assert hydro._leading_run(np.ones(4, bool)) == 4 and hydro._leading_run(np.zeros(4, bool)) == 0
    times, rain = series(0.0)
    f = hydro.hydro_features(times, rain, T0, CFG)
    assert f['current_dry_spell_h'] == f['longest_dry_spell_h_60d'] == 1438


def test_incomplete_or_implausible_series_fail_loudly():
    times, rain = series(0.1)
    with pytest.raises(ValueError):
        hydro.hydro_features(times[5:], rain[5:], T0, CFG)         # missing hours at the start of the window
    bad = rain.copy()
    bad[admissible_index(times)[10]] = -0.5
    with pytest.raises(ValueError):
        hydro.hydro_features(times, bad, T0, CFG)
    nan = rain.copy()
    nan[admissible_index(times)[3]] = np.nan
    with pytest.raises(ValueError):
        hydro.hydro_features(times, nan, T0, CFG)


def test_available_water_needs_both_parts():
    times, rain = series(0.1)
    f = hydro.hydro_features(times, rain, T0, CFG, swe_melt={'3d': 4.0, '7d': np.nan}, rain_sums={'3d': 2.0, '7d': 5.0, '14d': 9.0})
    assert f['available_water_3d'] == 6.0 and np.isnan(f['available_water_7d']) and np.isnan(f['available_water_14d'])


def test_registered_feature_list_equals_function_output_and_variants_compose():
    import json
    from preslide.sources import ROOT
    from preslide.v05 import models as M
    from preslide.v06.experiment import variant_columns
    cfg = json.loads((ROOT / 'config/v06.json').read_text(encoding='utf-8'))
    v05 = json.loads((ROOT / 'config/v05.json').read_text(encoding='utf-8'))
    times, rain = series(0.3)
    out = hydro.hydro_features(times, rain, T0, cfg['hydrology'], {'3d': 1.0, '7d': 1.0, '14d': 1.0}, {'3d': 1.0, '7d': 1.0, '14d': 1.0})
    names = cfg['hydrology']['features']
    assert sorted(out) == sorted(names) and len(names) == 23
    combined = variant_columns('combined', 'conditional_logit', v05, names)
    assert variant_columns('combined_hydro', 'conditional_logit', v05, names) == combined + names
    assert variant_columns('hydro_only', 'hist_gradient_boosting', v05, names) == names
    assert not set(names) & set(M.columns('combined', 'conditional_logit', v05))
    assert not set(names) & {c for c in v05['features']['forbidden_predictors'] if ' ' not in c}
