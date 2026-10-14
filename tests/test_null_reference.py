import numpy as np
import pandas as pd
import pytest

from preslide.null_reference import permuted_labels, within_group
from preslide.sources import ROOT


def toy():
    rows = [{'event_group_id': f'g{g}', 'label': int(i == 0)} for g in range(10) for i in range(6)]
    return pd.DataFrame(rows)


def test_identity_draw_keeps_true_labels():
    dev = toy()
    assert (permuted_labels(dev, 0, 1) == dev.label.to_numpy()).all()


def test_permutation_keeps_one_positive_per_group_and_is_deterministic():
    dev = toy()
    a, b = permuted_labels(dev, 3, 7), permuted_labels(dev, 3, 7)
    assert (a == b).all()
    assert (dev.assign(label=a).groupby('event_group_id').label.sum() == 1).all()
    assert not (permuted_labels(dev, 4, 7) == a).all()


def test_within_group_ties_count_half():
    groups = np.array(['a'] * 3)
    assert within_group(groups, np.array([1, 0, 0]), np.array([.5, .5, .1])) == pytest.approx(.75)


@pytest.mark.skipif(not (ROOT / 'reports/null_v03/null_summary.csv').exists(), reason='null reference not run')
def test_null_summary_complete_and_identity_reproduced():
    s = pd.read_csv(ROOT / 'reports/null_v03/null_summary.csv')
    assert (s.draws == 100).all()
    assert set(s.model) == {'logistic_regression', 'random_forest', 'gradient_boosting'}
    assert s[['p_upper', 'p_lower']].apply(lambda c: c.between(0, 1)).all().all()
    delta = pd.read_csv(ROOT / 'reports/stability_v02/delta_summary.csv')
    for r in delta[delta.metric.isin(['average_precision', 'within_group_auc'])].itertuples():
        obs = s[(s.model == r.model) & (s.statistic == f'delta_combined_minus_static_{r.metric}')].observed.iloc[0]
        assert obs == pytest.approx(r.median, abs=1e-12)
