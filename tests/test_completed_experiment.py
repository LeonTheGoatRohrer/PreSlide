"""Meaningful real-artifact integration checks; skipped without local snapshots."""
import numpy as np
import pandas as pd
import pytest
from preslide.sources import ROOT
from preslide.common import read_json
from preslide.pipeline import validate_dataset
from preslide.evaluation import FEATURE_SETS
from preslide.matching import Exclusions

pytestmark=pytest.mark.skipif(not (ROOT/'data/processed/046074ba6f12556c/status.json').exists(),reason='Local experiment artifacts required')

@pytest.fixture
def completed():
    from preslide.baseline import pointer
    latest=pointer()  # frozen baseline, not latest.json
    return pd.read_parquet(ROOT/'data/processed'/latest['identity']/'evaluation_dataset.parquet'),latest

def test_real_split_feature_and_exclusion_invariants(completed):
    data,latest=completed
    validate_dataset(data,latest['config'])
    assert data.groupby('event_group_id').partition.nunique().max()==1
    assert data.groupby('dependence_cluster').partition.nunique().max()==1
    controls=data[data.label==0]
    assert Exclusions(latest['config']).allowed(controls[['x','y']].to_numpy()).all()
    assert controls.distance_to_positive_m.between(750,10000).all()
    assert set(FEATURE_SETS['combined']).issubset(data.columns)

def test_wrong_control_date_is_rejected(completed):
    data,latest=completed
    bad=data.copy();bad.loc[bad[bad.label==0].index[0],'event_date']='2020-01-01'
    with pytest.raises(ValueError,match='Invalid event group'):validate_dataset(bad,latest['config'])

def test_future_timestamp_is_rejected(completed):
    data,latest=completed
    bad=data.copy();bad['weather_last_timestamp']='2030-01-01T00:00:00+00:00'
    with pytest.raises(ValueError,match='Future weather leakage'):validate_dataset(bad,latest['config'])

def test_duplicate_controls_are_rejected(completed):
    data,latest=completed
    bad=data.copy();ii=bad[bad.label==0].index[:2]
    bad.loc[ii[1],['x','y']]=bad.loc[ii[0],['x','y']].to_numpy()
    with pytest.raises(ValueError,match='Overlapping controls'):validate_dataset(bad,latest['config'])
