import numpy as np

from preslide.v07 import infrastructure as I


def test_densify_keeps_endpoints_and_limits_gaps():
    xy = np.array([[0.0, 0.0], [100.0, 0.0], [100.0, 60.0]])
    d = I.densify(xy, 25.0)
    assert (d[0] == xy[0]).all() and (d[-1] == xy[-1]).all()
    assert np.hypot(*np.diff(d, axis=0).T).max() <= 25.0 + 1e-9
    assert (d == [100.0, 0.0]).all(axis=1).any()                      # the corner vertex is kept
    assert len(I.densify(xy[:1])) == 1


def test_road_midpoint_is_found_only_after_densifying():
    sample = np.array([[100.0, 40.0]])
    line = np.array([[0.0, 0.0], [200.0, 0.0]])                      # nearest original vertex is 100 m x-offset away
    raw, dense = I.RunningMinimum(sample, 5000), I.RunningMinimum(sample, 5000)
    raw.add(line)
    dense.add(I.densify(line))
    assert raw.result()[0][0] > 100.0
    assert abs(dense.result()[0][0] - 40.0) <= 13.0


def test_running_minimum_caps_and_flags_far_samples_and_is_chunk_independent():
    sample = np.array([[0.0, 0.0], [20000.0, 0.0]])
    pts = np.array([[3.0, 4.0], [0.0, 100.0]])
    a = I.RunningMinimum(sample, 5000)
    a.add(pts)
    b = I.RunningMinimum(sample, 5000)
    b.add(pts[:1]); b.flush(); b.add(pts[1:])
    (da, ca), (db, cb) = a.result(), b.result()
    assert da[0] == db[0] == 5.0 and da[1] == 5000.0 and ca.tolist() == [False, True] and cb.tolist() == ca.tolist()


def test_registered_road_classes_match_the_config_text():
    import json
    cfg = json.loads((I.ROOT / 'config/v07.json').read_text(encoding='utf-8'))
    listed = set(cfg['infrastructure']['road'].split('[')[1].split(']')[0].replace(' ', '').split(','))
    assert listed == set(I.BASE_ROADS)


def test_caliper_keeps_positive_and_controls_within_factor_two_only():
    import pandas as pd
    from preslide.v07.experiment import caliper_keep, ranks_variable_k
    f = pd.DataFrame({'event_group_id': ['g'] * 5, 'label': [1, 0, 0, 0, 0],
                      'dist_infrastructure_m': [99.0, 49.0, 198.0, 48.0, 400.0]})     # ratios (1+d)/(100): .5, 1.99, <.5, 4.0
    assert caliper_keep(f).tolist() == [True, True, True, False, False]
    r = ranks_variable_k(f, [5.0, 1.0, 9.0, 3.0, 3.0], 2)
    assert r.controls.tolist() == [4] and r.local_auc.tolist() == [0.75]
    assert len(ranks_variable_k(f.iloc[:3], [5.0, 1.0, 9.0], 3)) == 0                  # fewer controls than the minimum: group omitted
