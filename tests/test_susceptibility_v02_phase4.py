"""susceptibility_v02 Phase 4 safety tests: registered models, Bonferroni decision, single scoring, no train/test
overlap, the pilot never reads the confirmatory test inventory. Synthetic frames only; nothing is written.
"""
import numpy as np
import pandas as pd
import pytest

from preslide.common import read_json
from preslide.sources import ROOT
from preslide.susceptibility import v02_evaluate as E

CFG = read_json(ROOT / 'config/susceptibility_v02.json')


def test_registered_models():
    t = E.model_table(CFG)
    terrain = CFG['features_terrain']
    assert t['EQ_TERRAIN_PGA'] == ('hist_gradient_boosting', terrain + ['log10_pga_pctg'])
    assert t['EQ_TERRAIN'] == ('hist_gradient_boosting', terrain)
    assert t['slope_pga_logistic'] == ('logistic_regression', ['slope_deg', 'log10_pga_pctg'])
    assert t['slope_only'] == ('logistic_regression', ['slope_deg'])
    assert t['pga_only'] == ('logistic_regression', ['log10_pga_pctg'])
    assert set(t) == set(CFG['trigger_arms']['earthquake']['models']) | set(CFG['trigger_arms']['earthquake']['baselines'])


@pytest.mark.parametrize('l1,l2,s1,s2,sup', [(0.01, 0.02, True, True, True), (0.01, -0.001, True, False, False),
                                             (0.0, 0.05, False, True, False), (-0.1, -0.1, False, False, False)])
def test_decision_requires_both_lower_bounds_above_zero(l1, l2, s1, s2, sup):
    d = E.decide({'lower_bound_bonferroni': l1}, {'lower_bound_bonferroni': l2})
    assert (d['H1_passed'], d['H2_passed'], d['supported']) == (s1, s2, sup)


def test_paired_uses_bonferroni_percentile():
    boot = {'a': np.linspace(0, 1, 1001), 'b': np.zeros(1001)}
    p = E.paired(boot, 'a', 'b', 0.625)
    assert p['lower_bound_bonferroni'] == pytest.approx(np.percentile(np.linspace(0, 1, 1001), 0.625))
    assert p['lower_bound_bonferroni'] < p['interval_95'][0]


def frame(name, n=200, seed=0):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({c: rng.normal(size=n) for c in CFG['features_terrain'] + ['log10_pga_pctg']})
    d['label'] = rng.integers(0, 2, n)
    d['dataset'] = name
    d['sample_id'] = [f'{name}:{i}' for i in range(n)]
    d['block_id'] = [f'{name}:{i % 20}:0' for i in range(n)]
    d['x'], d['y'] = rng.uniform(0, 1e5, n), rng.uniform(0, 1e5, n)
    return d


def test_pilot_never_reads_confirmatory_test(monkeypatch):
    read = []

    def fake(name):
        read.append(name)
        return frame(name, seed=len(read))
    monkeypatch.setattr(E, 'samples', fake)
    res = E.run(pilot=True)
    assert 'iburi_2018' not in read and res['pilot']


def test_train_test_overlap_refused(monkeypatch):
    monkeypatch.setattr(E, 'samples', lambda name: frame('gorkha_2015'))
    with pytest.raises(RuntimeError, match='overlap'):
        E.direction(E.config(), 'gorkha_2015', 'iburi_2018', 'far_western_nepal', 0, 5, 5, store_models=False)


def test_second_scoring_refused(monkeypatch, tmp_path):
    done = tmp_path / 'phase4_results.json'
    done.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(E, 'RESULT', done)
    monkeypatch.setattr(E, 'samples', lambda name: pytest.fail('samples read'))
    with pytest.raises(RuntimeError, match='run once'):
        E.run()
