"""Synthetic invariants only: these fixtures never enter research artifacts."""
import numpy as np
import pandas as pd
import pytest
from preslide.weather import cutoff,expected_times,features_from_series,TEMPORAL
from preslide.terrain import derivatives,PROJECT,GEOD
from preslide.matching import angular_distance,Exclusions
from preslide.evaluation import dependent_clusters,grouped_split,FEATURE_SETS,metrics

def test_aspect_wrap():
    assert angular_distance(359,1)==2

def test_metric_plane_derivatives():
    z=np.tile(np.arange(9)*30.,(9,1))
    s,a=derivatives(z,30)
    assert np.allclose(s,45) and np.allclose(a,270)
    s,a=derivatives(z.T,30)
    assert np.allclose(a,0)

def test_projected_units_and_axis_order():
    p=PROJECT.transform(14,47);q=PROJECT.transform(14.01,47)
    distance=np.linalg.norm(np.array(p)-q)
    geodesic=GEOD.inv(14,47,14.01,47)[2]
    assert abs(distance/geodesic-1)<.002

@pytest.mark.parametrize('date',['2023-03-27','2023-10-30','2023-08-05'])
def test_no_future_weather_even_event_day_changes(date):
    times=pd.date_range(cutoff(date)-pd.Timedelta(days=60),cutoff(date)+pd.Timedelta(days=2),freq='h')
    rain=np.ones(len(times));temp=np.ones(len(times))*10
    a=features_from_series(times,rain,temp,date)
    rain[times+pd.Timedelta(hours=1)>=cutoff(date)]=100
    temp[times+pd.Timedelta(hours=1)>=cutoff(date)]=40
    assert a==features_from_series(times,rain,temp,date)
    assert a['rain_sum_60d']==1438 and a['rain_sum_1d']==22
    assert expected_times(date,60)[-1]+pd.Timedelta(hours=1)<cutoff(date)

def test_missing_hours_and_nans_rejected():
    t=expected_times('2022-08-19',60)
    with pytest.raises(ValueError): features_from_series(t.delete(100),np.ones(len(t)-1),np.ones(len(t)-1),'2022-08-19')
    rain=np.ones(len(t));rain[100]=np.nan
    with pytest.raises(ValueError): features_from_series(t,rain,np.ones(len(t)),'2022-08-19')

def groups_fixture():
    rows=[]
    for i in range(10):
        for j in range(6):
            rows.append({'event_group_id':str(i),'event_date':str(pd.Timestamp('2020-01-01')+pd.Timedelta(days=i*20))[:10],
                         'label':int(j==0),'x':i*50000+j*1000.,'y':0.})
    return pd.DataFrame(rows)

def test_groups_storms_and_nearby_patches_never_split():
    d=groups_fixture();d.loc[d.event_group_id=='1','event_date']='2020-01-02'
    d.loc[d.event_group_id=='2','x']=d.loc[d.event_group_id=='0','x'].to_numpy()+100
    d['dependence_cluster']=dependent_clusters(d);d['split']=grouped_split(d)
    assert d[d.event_group_id.isin(['0','1','2'])].dependence_cluster.nunique()==1
    assert d.groupby('event_group_id').split.nunique().max()==1
    assert d.groupby('dependence_cluster').split.nunique().max()==1

def test_metadata_and_matching_are_never_predictors():
    forbidden={'label','event_date','sample_id','longitude','latitude','matching_score','distance_to_positive_m','source_position_upper_m'}
    assert not forbidden.intersection(FEATURE_SETS['combined'])

def test_rank_baseline_handles_ties():
    d=groups_fixture();d['dependence_cluster']=dependent_clusters(d)
    m=metrics(d,np.ones(len(d))/6)
    assert m['within_group_auc']==.5
    assert np.isclose(m['top1_fractional'],1/6)

def test_exclusion_boundary():
    from scipy.spatial import cKDTree
    e=Exclusions.__new__(Exclusions);e.xy=np.array([[0.,0.],[1000.,0.]])
    e.radii=np.array([350.,500.]);e.tree=cKDTree(e.xy)
    assert e.allowed(np.array([[350.,0.],[351.,0.],[500.,0.],[1501.,0.]])).tolist()==[False,True,False,True]
