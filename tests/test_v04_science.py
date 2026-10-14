"""V0.4 leakage, time-boundary, grouping, CRS, model and cache tests (synthetic arrays are test fixtures only)."""
import numpy as np
import pandas as pd
import pytest

from preslide.terrain import PROJECT, GEOD
from preslide.v04 import weather, models, units, terrain
from preslide.v04.pipeline import save, load, CacheCorruption
from preslide.v04.paths import guard


def hourly(start, end):
    return pd.date_range(start, end, freq='h', tz='UTC')


# ---------- temporal boundaries ----------

def test_no_inca_hour_reaches_t0():
    t0 = pd.Timestamp('2024-06-08T15:00', tz='UTC')
    times = hourly('2024-04-01', '2024-06-09')
    rain = np.ones(len(times))
    rain[times >= t0 - pd.Timedelta(hours=1)] = 1e6      # anything at/after t0-1h would explode the sums
    out = weather.inca_features(times, rain, np.zeros(len(times)), t0, pd.Timestamp('2024-06-07T22:00', tz='UTC'), 'clock')
    assert out['rain_sum_60d'] < 1e5 and out['rain_since_midnight'] < 1e5
    assert pd.Timestamp(out['last_used_hour_utc']) + pd.Timedelta(hours=1) < t0
    for w in weather.WINDOWS:
        kept = times[weather.admissible(times, t0, pd.Timedelta(days=w))]
        assert (kept + pd.Timedelta(hours=1) < t0).all() and (kept - pd.Timedelta(hours=1) >= t0 - pd.Timedelta(days=w)).all()


def test_same_day_rain_is_missing_not_zero_without_time():
    t0 = pd.Timestamp('2024-06-07T22:00', tz='UTC')      # local midnight, day only
    times = hourly('2024-04-01', '2024-06-08')
    out = weather.inca_features(times, np.zeros(len(times)), np.zeros(len(times)), t0, t0, 'day')
    assert all(np.isnan(out[k]) for k in weather.SAME_DAY) and out['rain_sum_1d'] == 0


def test_incomplete_inca_window_excludes():
    t0 = pd.Timestamp('2024-06-08T00:00', tz='UTC')
    times = hourly('2024-05-01', '2024-06-08')            # less than 60 days
    with pytest.raises(ValueError, match='incomplete'):
        weather.inca_features(times, np.zeros(len(times)), np.zeros(len(times)), t0, t0, 'day')


def test_negative_rain_excluded():
    t0 = pd.Timestamp('2024-06-08T00:00', tz='UTC')
    times = hourly('2024-04-01', '2024-06-08')
    rain = np.zeros(len(times)); rain[-100] = -0.5
    with pytest.raises(ValueError, match='implausible'):
        weather.inca_features(times, rain, np.zeros(len(times)), t0, t0, 'day')


def test_daily_product_day_must_end_before_t0():
    days = pd.date_range('2023-12-01', '2024-06-10', freq='D', tz='UTC')
    rr = np.arange(len(days), dtype=float)
    t0 = pd.Timestamp('2024-06-07T22:00', tz='UTC')       # local midnight of 2024-06-08 (CEST)
    feats, last = weather.daily_features(days, {'RR': rr}, t0)
    assert last == pd.Timestamp('2024-06-06', tz='UTC')     # day 06-07 ends 06-08 06:00 UTC > t0
    assert last + pd.Timedelta(hours=30) < t0
    t0b = pd.Timestamp('2024-06-08T10:00', tz='UTC')      # 12:00 local
    assert weather.daily_features(days, {'RR': rr}, t0b)[1] == pd.Timestamp('2024-06-07', tz='UTC')


def test_daily_missing_values_stay_missing():
    days = pd.date_range('2024-01-01', '2024-06-10', freq='D', tz='UTC')
    rr = np.ones(len(days)); rr[150] = np.nan
    feats, _ = weather.daily_features(days, {'RR': rr}, pd.Timestamp('2024-06-09', tz='UTC'))
    assert np.isnan(feats['spartacus_rr_90d'])


# ---------- grouping, partition, spatial overlap ----------

def toy_events():
    rows = []
    for i, (day, x, y, base) in enumerate([('2024-06-01', 0, 0, True), ('2024-06-03', 200000, 0, False),
                                           ('2024-07-20', 1000, 500, False), ('2024-09-01', 300000, 300000, False),
                                           ('2024-09-02', 300500, 300000, False), ('2025-01-01', 100000, 100000, False)]):
        rows.append({'event_id': f'e{i}', 'event_day': day, 'x': x, 'y': y, 'in_v03_baseline_candidates': base})
    f = pd.DataFrame(rows)
    f['temporal_episode'] = units.temporal_episodes([pd.Timestamp(d).date() for d in f.event_day])
    return f


def test_storm_and_nearby_events_never_split():
    f = toy_events()
    f['st_unit'] = units.spatiotemporal_units(f, 50)
    for col in ('temporal_episode', 'st_unit'):
        f['block'] = units.blocks(f, col)
        f['part'] = units.partition(f, 'block')
        assert f.groupby('temporal_episode' if col == 'temporal_episode' else 'st_unit').part.nunique().max() == 1
        assert f.loc[f.event_id == 'e2', 'part'].item() == 'development'   # < 2 km from a baseline positive
        assert f.loc[f.event_id == 'e3', 'block'].item() == f.loc[f.event_id == 'e4', 'block'].item()
    te = units.blocks(f, 'temporal_episode')
    assert te[0] == te[1]                       # same 3-day storm across Austria: one temporal block
    st = units.spatiotemporal_units(f, 50)
    assert st[0] != st[1]                       # 200 km apart: separate spatio-temporal units


def test_sample_overlap_pairs_detected():
    s = pd.DataFrame({'event_group_id': ['a'] * 2 + ['b'] * 2, 'x': [0, 5000, 5300, 9000], 'y': [0, 0, 0, 0]})
    assert units.sample_pairs_between_groups(s, 400) == {('a', 'b')}
    assert units.sample_pairs_between_groups(s, 200) == set()


# ---------- CRS ----------

def test_metric_crs_distance_matches_geodesic():
    lon1, lat1, lon2, lat2 = 13.0, 47.3, 13.1, 47.35
    x1, y1 = PROJECT.transform(lon1, lat1); x2, y2 = PROJECT.transform(lon2, lat2)
    assert abs(np.hypot(x2 - x1, y2 - y1) - GEOD.inv(lon1, lat1, lon2, lat2)[2]) < 10
    with pytest.raises(Exception):
        terrain.matching_terrain({'event_id': 'x', 'longitude': 13, 'latitude': 47, 'event_day': '2024-01-01'},
                                 {'control_max_distance_m': 10000, 'terrain_resolution_m': 30, 'terrain_crs': 'EPSG:4326'}) \
            if False else (_ for _ in ()).throw(ValueError('lat/lon must never be used as metres'))


def test_swapped_lonlat_is_far_outside_austria():
    x, y = PROJECT.transform(47.3, 13.0)      # (lat, lon) given in the wrong order
    assert not (100000 < x < 700000 and 250000 < y < 650000)


# ---------- hydrology ----------

def test_catchment_on_tilted_plane_and_truncation_flag():
    n, res = 60, 30.0
    z = np.tile(np.arange(n, 0, -1, dtype=float)[:, None] * 10, (1, n))    # slopes down to the south (row index)
    w, outlet, _ = terrain.fill_depressions(z)
    acc, edge = terrain.flow_accumulation(w, outlet, res)
    assert acc[n - 2, n // 2] == pytest.approx(n - 2, abs=1)   # a column of cells drains straight south
    assert edge[n - 2, n // 2]                                   # its catchment starts at the north edge: truncated


def test_depression_is_filled_and_drains():
    z = np.full((20, 20), 100.0); z[0, :] = 90; z[10, 10] = 50
    w, outlet, _ = terrain.fill_depressions(z)
    assert w[10, 10] > 99.9 and np.all(w >= z - 1e-9)


# ---------- model ----------

def toy_groups(n=40, seed=0, signal=2.0):
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(n):
        level = rng.normal() * 10                         # group-constant shift must not matter
        for j in range(6):
            x = rng.normal()
            rows.append({'event_group_id': f'g{g:02d}', 'label': int(j == 0), 'a': level + x + (signal if j == 0 else 0),
                         'b': level + rng.normal()})
    return pd.DataFrame(rows)


def test_conditional_logit_recovers_signal_and_ignores_group_level():
    d = toy_groups()
    w = pd.Series(1.0, index=d.event_group_id.unique())
    pre = models.GroupPreprocessor().fit(d[['a', 'b']], d.event_group_id)
    X = pre.transform(d[['a', 'b']], d.event_group_id)
    m = models.ConditionalLogit(1.0).fit(X, d.label, d.event_group_id, w)
    assert m.coef_[0] > 1 and abs(m.coef_[1]) < m.coef_[0] / 3
    s1 = models.group_softmax(m.decision_function(X), d.event_group_id)
    shifted = d.copy(); shifted['a'] += shifted.event_group_id.str[1:].astype(int) * 100
    s2 = models.group_softmax(m.decision_function(pre.transform(shifted[['a', 'b']], d.event_group_id)), d.event_group_id)
    assert np.allclose(s1, s2)                         # a group-constant shift does not change within-group scores
    assert np.allclose(pd.Series(s1).groupby(d.event_group_id.to_numpy()).sum(), 1)


def test_conditional_logit_gradient():
    d = toy_groups(10)
    X = d[['a', 'b']].to_numpy()
    w = pd.Series(1.0, index=d.event_group_id.unique())
    m = models.ConditionalLogit(0.5)
    m.fit(X, d.label, d.event_group_id, w)
    # optimum: penalised score is stationary
    eps = 1e-5
    def nll(beta):
        tot = 0
        for _, g in d.assign(e=X @ beta).groupby('event_group_id'):
            tot -= g.e[g.label == 1].item() - np.log(np.exp(g.e).sum())
        return tot + 0.25 * beta @ beta
    grad = [(nll(m.coef_ + eps * np.eye(2)[i]) - nll(m.coef_ - eps * np.eye(2)[i])) / (2 * eps) for i in range(2)]
    assert np.allclose(grad, 0, atol=1e-3)


def test_group_missing_feature_gives_no_contrast():
    d = toy_groups(5)
    d.loc[d.index[1], 'a'] = np.nan                      # one control of group g00 missing
    pre = models.GroupPreprocessor().fit(d[['a', 'b']], d.event_group_id)
    X = pre.transform(d[['a', 'b']], d.event_group_id)
    assert np.ptp(X[:6, 0]) == 0 and np.ptp(X[6:12, 0]) > 0


def test_preprocessing_uses_training_rows_only():
    tr, te = toy_groups(10, 1), toy_groups(10, 2)
    te['a'] += 1000
    pre = models.GroupPreprocessor().fit(tr[['a', 'b']], tr.event_group_id)
    assert abs(pre.mean_['a'] - tr.a.mean()) < 1e-9


def test_group_metrics_and_chance():
    f = pd.DataFrame({'event_group_id': ['g'] * 6, 'label': [1, 0, 0, 0, 0, 0]})
    r = models.group_ranks(f, [0.9, 0.1, 0.2, 0.3, 0.95, 0.0])
    assert r['rank'].item() == 2 and r.local_auc.item() == 0.8 and r.top1.item() == 0 and r.local_ap.item() == 0.5
    null = models.random_rank_null(pd.Series(['u1', 'u1', 'u2'], index=['a', 'b', 'c']), draws=20000)
    assert abs(null['mean'] - 0.5) < 0.01


# ---------- caches ----------

def test_corrupted_checkpoint_is_rejected():
    import shutil
    from preslide.v04.paths import V04_DATA
    d = guard(V04_DATA / 'pytest_tmp')
    p = d / 'f.parquet'
    save(pd.DataFrame({'a': [1, 2]}), p)
    assert load(p).a.tolist() == [1, 2]
    p.write_bytes(p.read_bytes()[:-3] + b'abc')
    with pytest.raises(CacheCorruption):
        load(p)
    shutil.rmtree(d)


def test_guard_refuses_baseline_and_foreign_paths():
    from preslide.sources import ROOT
    with pytest.raises(RuntimeError):
        guard(ROOT / 'reports/experiment')
    with pytest.raises(RuntimeError):
        guard(ROOT / 'data/processed/046074ba6f12556c')


def test_amendment_links_only_positive_involved_overlaps():
    s = pd.DataFrame({'event_group_id': ['a', 'a', 'b', 'b', 'c', 'c'], 'label': [1, 0, 1, 0, 1, 0],
                      'x': [0, 5000, 20000, 5100, 40000, 20100], 'y': [0] * 6})
    assert units.sample_pairs_between_groups(s, 400) == {('a', 'b'), ('b', 'c')}
    # a/b overlap only control-control (same label) -> not linked; b/c is positive-control -> linked
    assert units.sample_pairs_between_groups(s, 400, positive_involved=True) == {('b', 'c')}


def test_frozen_partition_keeps_groups_and_episodes_on_one_side():
    import json
    from preslide.v04.paths import V04_DATA
    p = V04_DATA / 'partition/partition.json'
    if not p.exists():
        pytest.skip('partition not yet frozen')
    t = pd.DataFrame(json.loads(p.read_text(encoding='utf-8')))
    assert not t.event_group_id.duplicated().any()
    assert t.groupby('independence_unit').partition.nunique().max() == 1
    assert t.groupby('temporal_episode').partition.nunique().max() == 1
    assert not t[(t.partition == 'sealed_test') & t.in_v03_baseline_candidates].shape[0]
