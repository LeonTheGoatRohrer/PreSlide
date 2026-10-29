"""Synthetic fixtures stay in tests. Safety checks are mutation-probed separately."""
import numpy as np
import pandas as pd
import pytest

from preslide.cascade_pilot.context import guard, selected_candidates, validate_split, validate_table


def fixture_frame():
    return pd.DataFrame({'sample_id': list('abcdef'), 'event_group_id': ['g'] * 6,
                         'independence_unit': ['u'] * 6, 'event_day': ['2020-01-01'] * 6,
                         'label': [1, 0, 0, 0, 0, 0], 'x': np.arange(6, dtype=float)})


def test_whole_table_preconditions():
    frame = fixture_frame()
    validate_table(frame, ['x'])
    for col, value in [('x', np.nan), ('event_day', '2020-01-02'), ('independence_unit', 'other'), ('sample_id', 'b')]:
        broken = frame.copy()
        broken.loc[0, col] = value
        with pytest.raises(ValueError):
            validate_table(broken, ['x'])


def test_split_rejects_one_leaking_unit_even_when_ids_differ():
    train = fixture_frame()
    held = train.assign(sample_id=lambda d: d.sample_id + '_held', event_group_id='new')
    with pytest.raises(ValueError, match='independence_unit leakage'):
        validate_split(train, held)
    validate_split(train, held.assign(independence_unit='other'))


def test_gate_does_not_read_labels_and_has_fixed_budget():
    frame = fixture_frame()
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
    chosen = selected_candidates(frame, scores, 0.5, 42)
    assert chosen.tolist() == [True, True, True, False, False, False]
    assert np.array_equal(chosen, selected_candidates(frame.assign(label=1-frame.label), scores, 0.5, 42))
    assert np.array_equal(selected_candidates(frame, scores * 0, 0.5, 42), selected_candidates(frame, scores * 0, 0.5, 42))


def test_singleton_group_and_one_group_cannot_be_silently_admitted():
    with pytest.raises(ValueError):
        validate_table(fixture_frame().iloc[:1], ['x'])


def test_write_guard_protects_frozen_artifacts():
    with pytest.raises(PermissionError):
        guard('reports/v04/test_results.json')


def test_appearance_uses_no_terrain_or_other_non_rgb_channels():
    from preslide.cascade_pilot.appearance import source_rgb
    from preslide.common import read_json
    cfg = read_json('config/mudslide_appearance_pilot_v01.json')
    image = np.random.default_rng(42).random((128, 128, 14))
    expected = source_rgb(image, cfg)
    changed = image.copy()
    changed[:, :, [0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]] = 1e9
    assert np.array_equal(source_rgb(changed, cfg), expected)


def test_appearance_metrics_detect_all_background_failure():
    from preslide.cascade_pilot.appearance import binary_counts, stretch
    truth = np.array([[[1, 0], [1, 0]]])
    result = binary_counts(np.zeros_like(truth, dtype=float), truth, 0.5)
    assert result['recall'] == result['dice'] == 0
    assert result['fn'] == 2
    with pytest.raises(ValueError):
        stretch(np.zeros((3, 128, 128)), [1, 99], 1e-6)


def test_transfer_ranking_supports_four_controls_without_changing_chance():
    from preslide.cascade_pilot.transfer import variable_ranks
    frame = fixture_frame().iloc[:5]
    assert variable_ranks(frame, np.ones(5)).iloc[0].local_auc == 0.5
    assert variable_ranks(frame, np.array([1, 0, 0, 0, 0])).iloc[0].local_auc == 1
    with pytest.raises(ValueError):
        variable_ranks(frame, np.full(5, np.nan))
