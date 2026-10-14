"""Frozen V0.3 baseline: integrity, overwrite guard and event-level diagnostics."""
import pandas as pd
import pytest

from preslide.baseline import (DIAGNOSTICS, IDENTITY, MANIFEST, ROOT, SAMPLE_SCORES, assert_not_frozen,
                               rank_of_positive, verify_manifest)

pytestmark = pytest.mark.skipif(not MANIFEST.exists(), reason='Local baseline artifacts required')


def test_manifest_hashes_unchanged():
    result = verify_manifest()
    assert result['status'] == 'PASS', result['mismatched_or_missing']


@pytest.mark.parametrize('path', ['reports/experiment/metrics.json', f'data/processed/{IDENTITY}/evaluation_dataset.parquet',
                                  f'data/processed/{IDENTITY}/test_predictions.parquet', f'models/{IDENTITY}/random_forest_combined.joblib'])
def test_frozen_artifacts_cannot_be_overwritten(path):
    with pytest.raises(RuntimeError, match='frozen|belongs to'):
        assert_not_frozen(ROOT / path)


def test_new_experiment_paths_are_writable():
    assert_not_frozen(ROOT / 'reports/experiments/ffffffffffffffff/full/metrics.json')


def test_rank_rule_counts_ties_half():
    frame = pd.DataFrame({'label': [1, 0, 0, 0, 0, 0], 's': [.5, .9, .5, .1, .1, .1]})
    assert rank_of_positive(frame, 's') == (2.5, 3)


def test_event_diagnostics_complete_and_consistent():
    d = pd.read_csv(DIAGNOSTICS)
    assert len(d) == 60 and d.event_group_id.is_unique and (d.n_controls == 5).all()
    assert (d.evaluation == 'original_test').sum() == 15 and (d.evaluation == 'development_oof').sum() == 45
    for m in ['lr', 'rf', 'gb']:
        for f in ['static', 'temporal', 'combined']:
            assert d[f'{m}_{f}_rank'].between(1, 6).all() and d[f'{m}_{f}_beaten'].between(0, 5).all()
        assert (d[f'{m}_weather_rank_change'] == d[f'{m}_static_rank'] - d[f'{m}_combined_rank']).all()
    test = d[d.evaluation == 'original_test']
    # Single frozen-model predictions on test have no ties: rank = 6 - controls beaten.
    assert (test.rf_combined_rank == 6 - test.rf_combined_beaten).all()


def test_sample_scores_cover_every_sample_once_per_variant():
    s = pd.read_csv(SAMPLE_SCORES)
    assert len(s) == 360 * 9 and not s.duplicated(['sample_id', 'model', 'features']).any()
    assert (s.groupby(['event_group_id', 'model', 'features']).label.agg(['sum', 'size']).values == [1, 6]).all()
