"""susceptibility_v02 Phase 3 safety tests: sea rule (Amendment 3), sampling streams, block ids, refusal of pending
or unregistered inventories, and preconditions. Synthetic inputs only; nothing is written to data/ or reports/.
"""
import collections

import numpy as np
import pytest

from preslide.susceptibility import v02_sampling as S


class FakeReader:
    def __init__(self, z):
        self.z = np.asarray(z, float)

    def values(self, x, y, bands=None):
        return self.z[np.asarray(x, int)][:, None]


def test_sea_rule_rejects_non_positive_and_missing_elevation():
    counts = collections.Counter()
    accept = S.elevation_accept(FakeReader([12.0, 0.0, -3.0, np.nan, 0.01]), counts)
    ok = accept(np.arange(5), np.zeros(5))
    assert ok.tolist() == [True, False, False, False, True]
    assert counts['background_candidates_rejected_elevation_le_0'] == 2
    assert counts['background_candidates_rejected_no_elevation'] == 1


def test_sampling_stream_order_is_registered():
    assert list(S.SAMPLED) == sorted(S.SAMPLED) == ['far_western_nepal', 'gorkha_2015', 'iburi_2018']
    assert 'rer2023' not in S.SAMPLED
    assert set(S.EARTHQUAKE) == {'gorkha_2015', 'iburi_2018'}


def test_block_ids_floor_on_5km_grid():
    ids = S.block_ids('iburi_2018', [4999.9, 5000.0, -0.1, 572345.0], [0.0, 9999.0, 10000.0, 4731000.0])
    assert ids == ['iburi_2018:0:0', 'iburi_2018:1:1', 'iburi_2018:-1:2', 'iburi_2018:114:946']


@pytest.mark.parametrize('dataset,message', [('rer2023', 'not sampled'), ('wenchuan_fan2019', 'not sampled')])
def test_unregistered_or_pending_inventory_is_refused(dataset, message):
    with pytest.raises(ValueError, match=message):
        S.run(dataset, limit=1, write=False)


def test_exact_buffer_rejects_inside_and_keeps_boundary():
    from shapely.geometry import box
    counts = collections.Counter()
    accept = S.buffer_accept([box(0, 0, 10, 10)], 100.0, counts)
    ok = accept(np.array([109.0, 110.0, 160.0, 5.0, 109.99]), np.array([5.0, 5.0, 5.0, 5.0, 5.0]))
    assert ok.tolist() == [False, True, True, False, False]
    assert counts['background_candidates_rejected_exact_buffer'] == 3


def test_exact_buffer_catches_geos_simplified_buffer():
    # A polygon whose GEOS buffer (simplify factor 1 %) misses a point 99.7 m away: the exact check must reject it.
    import math
    import shapely
    from shapely.geometry import Polygon
    rng = np.random.default_rng(0)
    ang = np.sort(rng.uniform(0, 2 * np.pi, 40))
    rad = 20 + rng.uniform(0, 3, 40)
    poly = Polygon(np.column_stack([rad * np.cos(ang), rad * np.sin(ang)])).buffer(0)
    r = 100 / math.cos(math.pi / 32)
    zone = shapely.buffer(poly, r, quad_segs=8)
    accept = S.buffer_accept([poly], 100.0, collections.Counter())
    grid = np.mgrid[-130:130:0.5, -130:130:0.5].reshape(2, -1).T
    d = shapely.distance(poly, shapely.points(grid))
    close = grid[(d < 100) & (d > 98)]
    assert not accept(close[:, 0], close[:, 1]).any()
    assert shapely.contains_xy(zone, close[:, 0], close[:, 1]).mean() > 0.9  # the zone alone is only a prefilter


def test_all_of_combines_rules():
    a = S.all_of(lambda x, y: np.asarray(x) > 0, lambda x, y: np.asarray(y) > 0)
    assert a(np.array([1, -1, 1]), np.array([1, 1, -1])).tolist() == [True, False, False]
