"""V0.5 scientific safety tests: rank metrics with ties, registered control draw, spatial purge, allowlist, leakage.

Synthetic frames below are unit-test fixtures only; they never enter any V0.5 dataset or result.
"""
import itertools

import numpy as np
import pandas as pd
import pytest
from scipy.spatial import cKDTree

from preslide.common import read_json
from preslide.sources import ROOT
from preslide.v05 import controls as K
from preslide.v05 import metrics as R
from preslide.v05 import models as M
from preslide.v05.partition import purge, folds

CFG = read_json(ROOT / 'config/v05.json')


# ---------- metrics ----------

@pytest.mark.parametrize('k', [5, 10])
def test_constant_scores_give_exact_chance_independent_of_row_order(k):
    for positive_row in (0, k):
        labels = np.zeros(k + 1, int)
        labels[positive_row] = 1
        frame = pd.DataFrame({'event_group_id': 'g', 'label': labels})
        r = R.group_ranks(frame, np.ones(k + 1), k).iloc[0]
        ch = R.chance(k)
        for m in ('local_auc', 'top1', 'top3', 'mean_rank', 'mrr'):
            assert r[m] == pytest.approx(ch[m])
    assert R.chance(10)['mrr'] == pytest.approx(CFG['metrics']['chance']['mrr'], abs=1e-9)
    assert R.chance(10)['top1'] == pytest.approx(1 / 11)


@pytest.mark.parametrize('k', [5, 10])
def test_first_and_last_positive(k):
    best = R.rank_metrics(10.0, np.arange(k))
    worst = R.rank_metrics(-1.0, np.arange(k))
    assert (best['local_auc'], best['top1'], best['top3'], best['mean_rank'], best['mrr']) == (1, 1, 1, 1, 1)
    assert worst['local_auc'] == 0 and worst['top1'] == 0 and worst['mean_rank'] == k + 1
    assert worst['mrr'] == pytest.approx(1 / (k + 1))


def test_partial_ties_follow_random_tie_order():
    # a = 1 control above, t = 2 tied: positive at rank 2, 3 or 4 with equal probability.
    m = R.rank_metrics(5.0, [9.0, 5.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    assert m['top1'] == 0
    assert m['top3'] == pytest.approx(2 / 3)
    assert m['mean_rank'] == pytest.approx(3)
    assert m['mrr'] == pytest.approx(np.mean([1 / 2, 1 / 3, 1 / 4]))
    assert m['local_auc'] == pytest.approx((7 + 1) / 10)


def test_group_ranks_reject_wrong_control_count():
    frame = pd.DataFrame({'event_group_id': 'g', 'label': [1, 0, 0, 0, 0, 0]})
    with pytest.raises(ValueError):
        R.group_ranks(frame, np.arange(6), 10)


def test_unit_weighting_gives_each_unit_equal_weight():
    ranks = pd.DataFrame({'event_group_id': ['a', 'b', 'c'], **{m: [1.0, 1.0, 0.0] for m in R.METRICS}})
    units = pd.Series({'a': 'U1', 'b': 'U1', 'c': 'U2'})
    s = R.summarize(ranks, units)
    assert s['local_auc_units'] == pytest.approx(0.5) and s['local_auc_events'] == pytest.approx(2 / 3)


# ---------- controls ----------

def fake_pool(n=600, seed=0):
    rng = np.random.default_rng(seed)
    d = np.sqrt(rng.uniform(750 ** 2, 10000 ** 2, n))
    a = rng.uniform(0, 2 * np.pi, n)
    return pd.DataFrame({'pool_id': np.arange(n), 'x': d * np.cos(a), 'y': d * np.sin(a), 'longitude': 0.0, 'latitude': 0.0,
                         'distance_to_positive_m': d, 'elevation': rng.uniform(200, 2000, n), 'slope': rng.uniform(0, 40, n),
                         'aspect': rng.uniform(0, 360, n), 'inventory_clear': rng.random(n) > .2, 'inside_austria': rng.random(n) > .05,
                         'passes_calipers': rng.random(n) > .5, 'matching_score': rng.random(n),
                         'slope_difference_deg': rng.random(n), 'elevation_difference_m': rng.random(n), 'aspect_difference_deg': rng.random(n)})


def test_seed_rule():
    import hashlib
    assert K.event_seed('1200834_001') == int(hashlib.sha256('1200834_001|v05'.encode()).hexdigest()[:16], 16)


def test_selection_deterministic_eligible_separated_and_ignores_matching_columns():
    pool = fake_pool()
    a, rec = K.select_controls('E1', pool, CFG['controls'])
    b, _ = K.select_controls('E1', pool.sample(frac=1, random_state=3), CFG['controls'])   # row order irrelevant
    assert a.pool_id.tolist() == b.pool_id.tolist() == rec['selected_pool_ids']
    changed = pool.assign(passes_calipers=~pool.passes_calipers, matching_score=-pool.matching_score,
                          slope_difference_deg=99.0, elevation_difference_m=999.0, aspect_difference_deg=180.0)
    assert K.select_controls('E1', changed, CFG['controls'])[0].pool_id.tolist() == a.pool_id.tolist()
    assert len(a) == 10 and a.pool_id.is_unique and a.draw_order.tolist() == list(range(1, 11))
    chosen = pool.set_index('pool_id').loc[a.pool_id]
    assert chosen.inventory_clear.all() and chosen.inside_austria.all() and (chosen.slope >= 5).all()
    xy = chosen[['x', 'y']].to_numpy()
    assert min(np.hypot(*(xy[i] - xy[j])) for i, j in itertools.combinations(range(10), 2)) >= 400
    assert K.select_controls('E2', pool, CFG['controls'])[0].pool_id.tolist() != a.pool_id.tolist()


def test_insufficient_controls_exclude_the_group_without_redraw():
    pool = fake_pool().assign(slope=1.0)
    pool.loc[:3, 'slope'] = 20.0
    with pytest.raises(ValueError, match='insufficient_unmatched_controls'):
        K.select_controls('E1', pool, CFG['controls'])


def test_vectorised_inventory_rule_equals_loop():
    class Ex:
        pass
    rng = np.random.default_rng(1)
    ex = Ex()
    ex.xy = rng.uniform(0, 20000, (300, 2))
    ex.radii = rng.uniform(250, 2250, 300)
    ex.tree = cKDTree(ex.xy)
    pts = rng.uniform(0, 20000, (2000, 2))
    loop = np.array([all(np.linalg.norm(p - ex.xy[j]) > ex.radii[j] for j in js)
                     for p, js in zip(pts, ex.tree.query_ball_point(pts, float(ex.radii.max())))])
    assert (K.inventory_allowed(ex, pts) == loop).all()


def test_pool_regeneration_matches_v04_construction():
    m = read_json(ROOT / 'config/v04.json')['matching']
    xy, d = K.regenerate_pool_xy('X', 1000.0, 2000.0, m)
    assert len(xy) == 6000 and d.min() >= 750 and d.max() <= 10000
    assert np.allclose(np.hypot(xy[:, 0] - 1000, xy[:, 1] - 2000), d)


# ---------- CV and purge ----------

def test_folds_cover_units_once():
    f = folds([f'U{i}' for i in range(30)] * 2, 11, 5)
    flat = sum(f, [])
    assert sorted(flat) == sorted(set(flat)) and len(flat) == 30 and len(f) == 5


def test_purge_removes_whole_units_including_control_control_proximity():
    s = pd.DataFrame({'independence_unit': ['H', 'H', 'A', 'A', 'B', 'C'], 'label': [1, 0, 1, 0, 1, 1],
                      'x': [0, 5000, 20000, 5600, 900, 40000], 'y': [0, 0, 0, 0, 0, 0]})
    purged, min_remaining = purge(s, ['H'], 1000)
    # A: its control (5600) is 600 m from H's control (5000) -> whole unit A removed. B: positive 900 m from H.
    assert purged == ['A', 'B'] and min_remaining == pytest.approx(35000)


# ---------- models ----------

def test_registered_column_counts_and_allowlist():
    n = {(v, m): len(M.columns(v, m, CFG)) for v in M.VARIANTS for m in M.MODELS}
    assert n[('static', 'conditional_logit')] == 22 and n[('temporal', 'conditional_logit')] == 29
    assert n[('combined', 'conditional_logit')] == 54 and n[('combined', 'hist_gradient_boosting')] == 51
    for bad in (['distance_to_positive_m'], ['x'], ['sample_id'], ['matching_score'], ['spartacus-v2-1d-1km_offset_m'], ['draw_order']):
        with pytest.raises(ValueError):
            M.check_allowlist(bad, CFG)


def test_conditional_logit_converges_and_preprocessing_uses_training_only():
    rng = np.random.default_rng(0)
    rows = []
    for g in range(40):
        for j in range(11):
            rows.append({'event_group_id': f'g{g}', 'independence_unit': f'U{g % 8}', 'label': int(j == 0),
                         **{c: rng.normal() + (0.8 if j == 0 and c == 'slope' else 0) for c in CFG['features']['static']}})
    frame = pd.DataFrame(rows)
    train, test = frame[frame.event_group_id.isin([f'g{i}' for i in range(30)])], frame[~frame.event_group_id.isin([f'g{i}' for i in range(30)])]
    shifted = test.assign(slope=test.slope + 100)
    s1, b1 = M.fit_predict('conditional_logit', train, test, M.columns('static', 'conditional_logit', CFG), CFG)
    _, b2 = M.fit_predict('conditional_logit', train, shifted, M.columns('static', 'conditional_logit', CFG), CFG)
    assert b1['model'].converged_ and np.allclose(b1['preprocessor'].mean_, b2['preprocessor'].mean_)
    assert np.allclose(pd.Series(s1).groupby(test.event_group_id.to_numpy()).sum(), 1)


def test_group_missing_mask_sets_whole_group_to_training_mean():
    from preslide.v04.models import GroupPreprocessor
    X = pd.DataFrame({'a': [1.0, 2.0, np.nan, 4.0, 5.0, 6.0]})
    g = pd.Series(['x', 'x', 'x', 'y', 'y', 'y'])
    pre = GroupPreprocessor().fit(X, g)
    out = pre.transform(X, g)
    assert np.allclose(out[:3], 0.0) and pre.mean_['a'] == pytest.approx(5.0)


# ---------- assembled data (only if the local V0.5 run exists) ----------

def assembled():
    runs = sorted((ROOT / 'data/v05').glob('run_*/dataset*.parquet')) if (ROOT / 'data/v05').exists() else []
    if not runs:
        pytest.skip('no local V0.5 dataset')
    return pd.read_parquet(runs[0])


def test_assembled_groups_same_t0_and_no_future_weather():
    from preslide.v05.pipeline import validate
    data = assembled()
    assert validate(data, CFG)['checks'] == 'PASS'
    g = data.groupby('event_group_id')
    assert (g.t0_utc.nunique() == 1).all() and (g.size() == 11).all() and (g.label.sum() == 1).all()
    tampered = data.copy()
    gid = tampered.event_group_id.iloc[0]
    tampered.loc[tampered.event_group_id == gid, 'last_used_hour_utc'] = tampered.loc[tampered.event_group_id == gid, 't0_utc']
    with pytest.raises(ValueError, match='Future weather'):
        validate(tampered, CFG)
