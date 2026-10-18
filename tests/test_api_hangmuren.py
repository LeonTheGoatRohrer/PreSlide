"""The Hangmuren pilot endpoint serves verified aggregates only and reports a missing pilot as 503."""
import json
from fastapi.testclient import TestClient
import preslide.api as api

client=TestClient(api.app)

def write_pilot(directory,status='PASS'):
    directory.mkdir()
    (directory/'verification.json').write_text(json.dumps({'status':status}),encoding='utf-8')
    (directory/'context_results.json').write_text(json.dumps({
        'version':'mudslide_cascade_v01','scope':'exploratory',
        'primary':{'local_auc_units':0.54,'local_auc_events':0.43,'events':102,'units':19,'top1_units':0.17},
        'auc_ci95':[0.41,0.67],'random_rank_null':{'q95':0.6},'random_rank_upper_p':0.28,
        'features':['elevation'],'limitations':['x']}),encoding='utf-8')

def test_missing_or_unverified_pilot_is_503(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'HANGMUREN_PILOT',tmp_path/'absent')
    assert client.get('/api/hangmuren_pilot').status_code==503
    write_pilot(tmp_path/'failed',status='FAIL')
    monkeypatch.setattr(api,'HANGMUREN_PILOT',tmp_path/'failed')
    assert client.get('/api/hangmuren_pilot').status_code==503

def test_verified_pilot_exposes_only_aggregates_with_interval(tmp_path,monkeypatch):
    write_pilot(tmp_path/'ok')
    monkeypatch.setattr(api,'HANGMUREN_PILOT',tmp_path/'ok')
    r=client.get('/api/hangmuren_pilot')
    assert r.status_code==200
    data=r.json()
    assert data['local_auc_units']==0.54 and data['ci95']==[0.41,0.67] and data['units']==19
    assert data['status']=='explorativ'
    assert 'features' not in data and 'limitations' not in data and 'top1_units' not in data
