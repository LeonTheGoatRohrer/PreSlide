import numpy as np
import pytest

from preslide.sources import ROOT
from preslide.v07 import experiment as V07E
from preslide.v07 import infrastructure as V07I
from preslide.v07b import experiment as E
from preslide.v07b import infrastructure as I
from preslide.v07b.paths import guard


def _road_samples():
    road = V07I.densify(np.array([[0.0, 0.0], [2000.0, 0.0]]))             # straight road along y = 0, 25 m vertices
    samples = np.array([[1000.0, 10.0], [1000.0, 100.0], [1000.0, 100.0], [1000.0, 6000.0]])
    return road, samples


@pytest.mark.parametrize('accumulator', [
    pytest.param(V07I.RunningMinimum, marks=pytest.mark.xfail(strict=True, reason='V0.7 bug: each vertex updates only its nearest sample')),
    I.NearestVertex])
def test_nearest_vertex_distance_is_exact_for_clustered_samples(accumulator):
    """Regression test for the V0.7 accumulator: fails (strict xfail) with preslide.v07, passes with the v07b fix."""
    road, samples = _road_samples()
    acc = accumulator(samples, 5000)
    for i in range(0, len(road), 7):
        acc.add(road[i:i + 7])
    d, capped = acc.result()
    assert d[:3] == pytest.approx([10.0, 100.0, 100.0], abs=0.5)
    assert capped.tolist() == [False, False, False, True] and d[3] == 5000


def test_v07_accumulator_overestimates_the_shadowed_sample_up_to_the_cap():
    road, samples = _road_samples()
    acc = V07I.RunningMinimum(samples, 5000)
    acc.add(road)
    d, capped = acc.result()
    assert d[0] == pytest.approx(10.0) and d[1] == d[2] == 5000 and capped.tolist() == [False, True, True, True]


@pytest.mark.parametrize('chunk', [3, 50, 10_000])
def test_exact_accumulator_matches_brute_force_on_clustered_random_data(chunk):
    rng = np.random.default_rng(7)
    centres = rng.uniform(0, 20_000, size=(5, 2))
    samples = np.vstack([c + rng.normal(0, 300, size=(12, 2)) for c in centres] + [[[60_000.0, 60_000.0]]])   # clusters + one far sample
    vertices = rng.uniform(-2000, 22_000, size=(800, 2))
    acc, brute = I.NearestVertex(samples, 5000, chunk=chunk), I.BruteForce(samples, chunk=chunk)
    for part in np.array_split(vertices, 37):
        acc.add(part)
        brute.add(part)
    d, capped = acc.result()
    ref = brute.result()
    assert np.allclose(d, np.minimum(ref, 5000)) and (capped == (ref > 5000)).all()
    assert capped[-1] and not capped[:-1].any()


def test_v07_stream_accumulator_is_restored_even_after_an_error():
    original = V07I.RunningMinimum
    with pytest.raises(ValueError):
        with I.v07_stream_with(I.paired_factory(np.array([0]))):
            assert V07I.RunningMinimum is not original
            raise ValueError
    assert V07I.RunningMinimum is original is I.V07_RUNNING_MINIMUM


def test_paired_accumulator_returns_exact_v07_and_brute_force():
    road, samples = _road_samples()
    acc = I.paired_factory(np.array([1, 3]))(samples, 5000)
    acc.add(road)
    (d, _), (d07, _), bf = acc.result()
    assert d[1] == pytest.approx(100.0) and d07[1] == 5000 and bf[0] == pytest.approx(100.0) and bf[1] > 5000


def test_table_keeps_v07_schema_and_minimum():
    t = I.table(['a', 'b'], (np.array([10.0, 5000.0]), np.array([False, True])), (np.array([30.0, 40.0]), np.array([False, False])))
    assert list(t.columns) == ['sample_id', 'dist_road_m', 'dist_building_m', 'road_capped', 'building_capped', 'dist_infrastructure_m']
    assert t.dist_infrastructure_m.tolist() == [10.0, 40.0]


def test_rebinding_redirects_v07_experiment_and_is_restored():
    before = (V07E.V07_DATA, V07E.V07_REPORT, V07E.guard)
    with E.bound():
        assert V07E.V07_DATA == ROOT / 'data/v07b' and V07E.V07_REPORT == ROOT / 'reports/v07b'
        with pytest.raises(RuntimeError):
            V07E.guard(ROOT / 'data/v07/analysis')                         # V0.7 outputs cannot be overwritten
    assert (V07E.V07_DATA, V07E.V07_REPORT, V07E.guard) == before


def test_guard_refuses_v07_and_other_versions():
    for p in ('data/v07', 'reports/v07', 'data/v05/analysis', 'config'):
        with pytest.raises(RuntimeError):
            guard(ROOT / p)
