"""extremwetter_v01 safety tests: pre-t0 windows, reference-day rules, percentile ranks, episode bootstrap, loud failures.

Synthetic series and events are test fixtures only; nothing is written to data/ or reports/.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from preslide.common import read_json
from preslide.extremwetter import analysis as A
from preslide.extremwetter import design as D
from preslide.sources import ROOT

CFG = read_json(ROOT / 'config/extremwetter_v01.json')
PRIMARY_END = CFG['exposure']['window_end']['primary']['last_label_offset_days']
FIRST = date(1960, 9, 1)


def synthetic_series(n_days=24200):
    """Value of label i = i (days since FIRST) mod 97, so window sums identify the labels used."""
    return np.arange(n_days, dtype=float) % 97


def label_sum(first_label, last_label):
    return sum(((first_label - FIRST).days + i) % 97 for i in range((last_label - first_label).days + 1))


# --- primary windows end before the event day -------------------------------------------------

@pytest.mark.parametrize('event_day', [date(2016, 7, 25), date(2024, 3, 31), date(2024, 10, 27), date(2023, 1, 1),
                                       date(2020, 2, 29), date(2025, 12, 31), date(2026, 3, 29)])
@pytest.mark.parametrize('window_days', CFG['exposure']['windows_days'])
def test_primary_window_complete_before_earliest_t0(event_day, window_days):
    first, last = D.window_labels(event_day, window_days, PRIMARY_END)
    assert (last - first).days == window_days - 1
    # every label used is complete strictly before local midnight of the event day (earliest possible t0)
    assert D.label_valid_utc(last) < D.earliest_t0_utc(event_day)
    # the next label (the calendar day before the event day) would end after t0: the rule is not vacuous
    assert D.label_valid_utc(last + timedelta(days=1)) > D.earliest_t0_utc(event_day)


def test_secondary_ends_are_flagged_as_post_t0():
    ends = CFG['exposure']['window_end']
    assert ends['primary']['last_label_offset_days'] == -2 and 'flag' not in ends['primary']
    assert ends['secondary_previous_day']['flag'] == 'MAY_CONTAIN_POST_T0'
    assert ends['secondary_event_day']['flag'] == 'CONTAINS_POST_T0'


def events_frame(days, episodes=None):
    return pd.DataFrame({'event_group_id': [f'E{i}' for i in range(len(days))], 'event_day': days,
                         'episode': episodes or [f'TE{i}' for i in range(len(days))]})


def test_case_and_reference_sums_use_exactly_the_registered_labels():
    days = [date(2016, 7, 25), date(2024, 1, 5)]
    ev = events_frame(days)
    series = {g: (FIRST, synthetic_series()) for g in ev.event_group_id}
    m = A.build(ev, series, {g: [] for g in ev.event_group_id}, CFG)
    for k in CFG['exposure']['windows_days']:
        for i, e in enumerate(days):
            assert m.cases[(k, PRIMARY_END)][i] == label_sum(e + timedelta(days=PRIMARY_END - k + 1), e + timedelta(days=PRIMARY_END))
        # reference cell (year 2000, offset +15) of event 0
        anchor = date(2000, 7, 25) + timedelta(days=15)
        y = list(m.years).index(2000)
        assert m.refs[(k, PRIMARY_END)][0, y, 30] == label_sum(anchor + timedelta(days=PRIMARY_END - k + 1), anchor + timedelta(days=PRIMARY_END))


# --- reference days ---------------------------------------------------------------------------

def test_reference_excludes_event_year_and_nearby_documented_days():
    e = date(2020, 8, 10)
    ev = events_frame([e])
    record = (date(2005, 8, 1), date(2005, 8, 2))         # documented event in 2005
    m = A.build(ev, {'E0': (FIRST, synthetic_series())}, {'E0': [record]}, CFG)
    years = list(m.years)
    assert not m.allowed[0, years.index(2020)].any()      # whole event year excluded
    anchors = D.anchor_grid(e, [2005], 15)[0]
    row = m.allowed[0, years.index(2005)]
    for a, ok in zip(anchors, row):
        near = record[0] - timedelta(days=3) <= a <= record[1] + timedelta(days=3)
        assert ok == (not near), a
    assert m.allowed[0, years.index(2004)].all() and m.allowed[0, years.index(2006)].all()
    # property: no allowed anchor lies in the event year or within +-3 days of a documented interval
    grid = D.anchor_grid(e, years, 15)
    for a in grid[m.allowed[0]]:
        assert a.year != 2020 or abs((a - e).days) > 15
        assert not (record[0] - timedelta(days=3) <= a <= record[1] + timedelta(days=3))


def test_inventory_exclusion_interval_boundaries():
    anchors = np.array([[date(2010, 6, d) for d in range(1, 21)]], dtype=object)
    hit = D.excluded_by_inventory(anchors, [(date(2010, 6, 10), date(2010, 6, 10))], 3)[0]
    assert [a.day for a, h in zip(anchors[0], hit) if h] == [7, 8, 9, 10, 11, 12, 13]
    assert not D.excluded_by_inventory(anchors, [], 3).any()


def test_seasonal_window_crosses_year_boundary_and_handles_leap_day():
    g = D.anchor_grid(date(2024, 1, 5), [2023, 2010], 15)
    assert g.shape == (2, 31)
    assert g[0, 0] == date(2022, 12, 21) and g[0, 15] == date(2023, 1, 5) and g[0, -1] == date(2023, 1, 20)
    assert g[1, 0] == date(2009, 12, 21)
    assert all((b - a).days == 1 for a, b in zip(g[0][:-1], g[0][1:]))
    leap = D.anchor_grid(date(2020, 2, 29), [2019, 2016], 15)
    assert leap[0, 15] == date(2019, 2, 28) and leap[1, 15] == date(2016, 2, 29)
    late = D.anchor_grid(date(2024, 12, 25), [2025], 15)
    assert late[0, -1] == date(2026, 1, 9)


# --- percentile ranks -------------------------------------------------------------------------

def test_percentile_rank_boundaries_and_ties():
    ref = np.array([1.0, 2.0, 2.0, 3.0])
    assert D.percentile_rank(0.5, ref) == 0.0           # strictly smallest
    assert D.percentile_rank(9.0, ref) == 1.0           # strictly largest
    assert D.percentile_rank(1.0, ref) == 0.125         # tie with the minimum: half counted
    assert D.percentile_rank(2.0, ref) == 0.5           # (1 + 0.5*2) / 4
    assert D.percentile_rank(3.0, ref) == 0.875
    assert D.percentile_rank(0.0, np.zeros(10)) == 0.5  # all dry: tie everywhere


def test_percentile_rank_is_unbiased_under_exchangeability_with_ties():
    values = np.array([0.0, 0.0, 0.0, 1.0, 2.5])        # many dry days, as in 1-day windows
    # the case is equally likely to be any of the five values: mean PR is exactly 0.5
    assert np.isclose(np.mean([D.percentile_rank(values[i], np.delete(values, i)) for i in range(5)]), 0.5)


def test_leave_one_out_scores_match_brute_force():
    rng = np.random.default_rng(1)
    v = np.round(rng.gamma(0.6, 8, size=60), 0)         # ties included
    pr, exc = D.leave_one_out_scores(v, (0.95, 0.99))
    for j in range(len(v)):
        others = np.delete(v, j)
        assert np.isclose(pr[j], D.percentile_rank(v[j], others))
        for p in (0.95, 0.99):
            assert exc[p][j] == D.exceeds(v[j], others, p)


def test_exceedance_and_rate_ratio():
    ref = np.arange(100, dtype=float)
    assert D.exceeds(99.0, ref, 0.95) and not D.exceeds(94.0, ref, 0.95)
    assert np.isclose(D.expected_exceedance(ref, 0.95), 0.05)
    assert np.isclose(D.rate_ratio(0.05, 0.05), 1.0)
    assert D.rate_ratio(1.0, 0.05) == float('inf')


# --- episode bootstrap ------------------------------------------------------------------------

def test_bootstrap_draws_whole_episodes():
    episodes = np.array(['A'] * 5 + ['B'] * 1 + ['C'] * 3 + ['D'] * 2)
    members = {e: set(np.flatnonzero(episodes == e)) for e in 'ABCD'}
    for idx, chosen in D.bootstrap_indices(episodes, 300, 7):
        assert len(chosen) == 4                          # as many episodes as observed
        counts = pd.Series(idx).value_counts()
        for e in 'ABCD':
            k = int((chosen == e).sum())
            assert all(counts.get(i, 0) == k for i in members[e])   # all members of an episode, k times each


def test_episode_weights_sum_to_one_per_episode():
    episodes = np.array(['A'] * 4 + ['B'])
    w = D.episode_weights(episodes, 'episode')
    assert np.isclose(w[:4].sum(), 1) and w[4] == 1
    assert (D.episode_weights(episodes, 'event') == 1).all()


# --- loud failures ----------------------------------------------------------------------------

@pytest.mark.parametrize('values, message', [([], 'empty_weather_series'), ([1.0, np.nan, 2.0], 'missing_weather_values'),
                                             ([1.0, -0.1], 'implausible_weather_values'), ([1.0, 600.0], 'implausible')])
def test_bad_weather_series_fail_loudly(values, message):
    with pytest.raises(ValueError, match=message):
        D.check_series(np.array(values, float))
    with pytest.raises(ValueError):
        D.window_sums(FIRST, np.array(values, float), np.array([[FIRST]], dtype=object), 1, 0)


def test_percentile_rank_rejects_empty_or_nan_reference():
    with pytest.raises(ValueError):
        D.percentile_rank(1.0, np.array([]))
    with pytest.raises(ValueError):
        D.percentile_rank(1.0, np.array([1.0, np.nan]))
    with pytest.raises(ValueError):
        D.percentile_rank(np.nan, np.array([1.0, 2.0]))


def test_case_window_outside_series_fails():
    ev = events_frame([date(1961, 1, 3)])
    with pytest.raises(ValueError, match='outside series'):
        A.build(ev, {'E0': (date(1961, 1, 1), synthetic_series(24000))}, {'E0': []}, CFG)


# --- end-to-end on synthetic data: null and bootstrap behave ----------------------------------

def test_evaluate_extreme_cases_versus_exchangeable_cases():
    days = [date(2018, 6, 1) + timedelta(days=40 * i) for i in range(8)]
    ev = events_frame(days, [f'TE{i // 2}' for i in range(8)])
    rng = np.random.default_rng(3)
    base = rng.gamma(0.7, 6, size=24200)
    wet = base.copy()
    for e in days:                                       # put 400 mm in every case window (primary end)
        wet[(e - FIRST).days + PRIMARY_END] = 400.0
    full = np.ones(len(ev), bool)
    m_wet = A.build(ev, {g: (FIRST, wet) for g in ev.event_group_id}, {g: [] for g in ev.event_group_id}, CFG)
    row, _ = A.evaluate(m_wet, ev, (1, PRIMARY_END), (1991, 2025), full, 'episode', CFG)
    assert row['mean_pr'] == 1.0 and row['n_episodes'] == 4 and row['p_one_sided'] < 0.01
    assert row['share_q99'] == 1.0
    m_null = A.build(ev, {g: (FIRST, base) for g in ev.event_group_id}, {g: [] for g in ev.event_group_id}, CFG)
    row0, _ = A.evaluate(m_null, ev, (3, PRIMARY_END), (1991, 2025), full, 'episode', CFG)
    assert abs(row0['null_mean_pr'] - 0.5) < 0.01
    assert row0['mean_pr_ci95'][0] <= row0['mean_pr'] <= row0['mean_pr_ci95'][1]


# --- API route --------------------------------------------------------------------------------

def test_route_returns_503_without_bundle_and_aggregate_bundle_otherwise(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from preslide.api import app
    from preslide.extremwetter import routes
    client = TestClient(app)
    monkeypatch.setattr(routes, 'WEB', tmp_path / 'missing.json')
    assert client.get('/api/extremwetter').status_code == 503
    bundle = tmp_path / 'results.json'
    bundle.write_text('{"version": "extremwetter_v01", "explorativ": true}', encoding='utf-8')
    monkeypatch.setattr(routes, 'WEB', bundle)
    response = client.get('/api/extremwetter')
    assert response.status_code == 200 and response.json()['explorativ'] is True
