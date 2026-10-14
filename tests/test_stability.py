"""Scientific invariants for repeated development evaluation (real cohort + tiny metric fixtures)."""
import numpy as np
import pandas as pd
import pytest
from preslide.stability import development, split_table, assert_split, event_scores, prepare, LOCAL, sha
from preslide.common import read_json


@pytest.fixture(scope='module')
def prepared():
    return prepare()


def test_frozen_development_coverage_and_group_isolation(prepared):
    dev, splits, config, directory = prepared
    original = pd.read_parquet(directory/'evaluation_dataset.parquet')
    assert not set(dev.sample_id) & set(original.loc[original.partition=='test', 'sample_id'])
    assert len(dev)==270 and dev.dependence_cluster.nunique()==16
    assert splits.groupby(['repetition','sample_id']).size().eq(1).all()
    assert splits.groupby(['repetition','dependence_cluster']).fold.nunique().eq(1).all()
    pd.testing.assert_frame_equal(split_table(dev, config), splits)
    for _, ids in splits.groupby(['repetition','fold']):
        held=dev[dev.sample_id.isin(ids.sample_id)]
        train=dev[~dev.sample_id.isin(ids.sample_id)]
        assert_split(train,held)
        with pytest.raises(ValueError,match='overlap'):
            assert_split(pd.concat([train,held.iloc[:1]]),held)


def test_detect_original_partition_leakage(prepared):
    _,_,_,directory=prepared
    data=pd.read_parquet(directory/'evaluation_dataset.parquet')
    data.loc[data.index[0],'partition']='test' if data.partition.iloc[0]!='test' else 'train'
    with pytest.raises(ValueError,match='crosses'):
        development(data)


def test_ranking_ties_and_orientation():
    frame=pd.DataFrame({'sample_id':list('abcdef'),'event_group_id':['e']*6,
                        'dependence_cluster':['c']*6,'label':[1,0,0,0,0,0]})
    tie=event_scores(frame,np.ones(6)).iloc[0]
    assert tie.controls_beaten==0 and tie.controls_tied==5
    assert tie.positive_rank==3.5 and tie.pairwise_auc==.5
    assert tie.top1_fractional==pytest.approx(1/6)
    best=event_scores(frame,[1,0,0,0,0,0]).iloc[0]
    worst=event_scores(frame,[0,1,1,1,1,1]).iloc[0]
    assert best.controls_beaten==5 and best.positive_rank==1
    assert worst.controls_beaten==0 and worst.positive_rank==6


def test_persisted_fits_are_disjoint_and_hash_verified(prepared):
    for path in (LOCAL/'fits').rglob('complete.json'):
        meta=read_json(path);spec=meta['spec']
        assert not set(spec['train_ids']) & set(spec['evaluation_ids'])
        assert not set(spec['train_clusters']) & set(spec['held_clusters'])
        for name,value in meta['sha256'].items():
            assert sha(path.parent/name)==value
        p=pd.read_parquet(path.parent/'predictions.parquet')
        assert p.sample_id.tolist()==spec['evaluation_ids']
        assert p.probability.between(0,1).all()


def test_learning_subsets_are_nested_and_holdouts_unchanged(prepared):
    dev,splits,config,_=prepared
    for (rep,fold),held in splits.groupby(['repetition','fold']):
        previous=set()
        for fraction in [.25,.5,.75]:
            path=LOCAL/'fits/learning'/f'r{rep}_f{fold}'/f'fraction_{fraction}'/'logistic_regression'/'complete.json'
            if not path.exists():pytest.skip('Diagnostic fits not yet complete')
            spec=read_json(path)['spec'];current=set(spec['train_ids'])
            assert previous<=current
            assert set(spec['evaluation_ids'])==set(held.sample_id)
            assert dev[dev.sample_id.isin(current)].groupby('event_group_id').size().eq(6).all()
            previous=current


def test_public_bundle_ties_match_scientific_metrics():
    from preslide.results_bundle import pairwise_summary
    frame=pd.DataFrame({'event_group_id':['e']*6,'label':[1,0,0,0,0,0],'p':[.5]*6})
    assert pairwise_summary(frame)['first_place_rate']==pytest.approx(1/6)
    assert pairwise_summary(frame)['mean_controls_beaten']==0


def test_scientific_figures_only_are_served():
    from fastapi.testclient import TestClient
    from preslide.api import app
    client=TestClient(app)
    for path in ['/api/stability/figures/event_pairwise_results.png',
                 '/reports/stability_v02/event_pairwise_results.csv',
                 '/api/stability/figures/..%2F..%2Fdata.png']:
        assert client.get(path).status_code==404
    if (LOCAL.parent.parent.parent/'reports').exists():
        assert client.get('/api/stability/figures/B_weather_delta.png').status_code in [200,503]
