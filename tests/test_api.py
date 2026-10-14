from fastapi.testclient import TestClient
from preslide.api import app
from preslide.sources import ROOT
import pytest

pytestmark=pytest.mark.skipif(not (ROOT/'data/processed/demo.json').exists(),reason='Real local demonstration bundle required')

client=TestClient(app)

def test_local_aggregate_and_small_derived_demo():
    assert client.get('/api/health').json()['raw_data_exposed'] is False
    cases=client.get('/api/cases').json()
    assert len(cases)==5
    for case in cases:
        response=client.get('/api/cases/'+case['id'])
        assert response.status_code==200
        data=response.json()
        assert len(data['samples'])==6
        assert sum(x['positive'] for x in data['samples'])==1
        assert 'original_source_id' not in response.text and 'OBJECTID' not in response.text
        assert 'QUAL_MB' not in response.text and '1310112_001' not in response.text

def test_raw_paths_and_arbitrary_records_are_unavailable():
    for path in ['/api/raw','/api/events','/data/raw/geosphere_natural_hazards.json','/api/cases/1310112_001',
                 '/api/cases/PS-99','/api/cases/PS-99/terrain.png','/api/cases/..%2F..%2Fraw']:
        assert client.get(path).status_code==404,path

def test_derived_terrain_image_served():
    r=client.get('/api/cases/PS-01/terrain.png')
    assert r.status_code==200 and r.headers['content-type']=='image/png'
    assert r.content.startswith(b'\x89PNG')

def test_results_bundle_is_aggregate_and_separates_experiments():
    r=client.get('/api/results')
    if r.status_code==503: pytest.skip('results bundle not generated')
    data=r.json()
    assert {'original_test','stability_v02','diagnostics_v02','cases'}<=set(data)
    assert data['stability_v02']['events']==45 and data['original_test']['split']['test']['events']==15
    import re
    assert not re.search(r'\d{7}_\d{3}',r.text), 'source event identifiers must not be exposed'
    assert 'sample_id' not in r.text and 'longitude' not in r.text
    for case in data['cases'].values():
        assert len(case['rankings'])==9
        for entry in case['rankings']:
            assert 0<=entry['controls_beaten']<=5 and len(entry['order'])==6

def test_event_explorer_is_deidentified_complete_and_consistent():
    r=client.get('/api/results')
    if r.status_code==503: pytest.skip('results bundle not generated')
    data=r.json();events=data['event_explorer']['events']
    assert len(events)==60 and len({e['alias'] for e in events})==60
    assert sum(e['evaluation']=='test' for e in events)==15
    for e in events:
        assert len(e['slopes'])==6 and sum(s['positive'] for s in e['slopes'])==1
        assert not {'longitude','latitude','x','y','sample_id','event_group_id'} & (set(e) | set(e['slopes'][0]))
        for model in e['variants'].values():
            for v in model.values():
                assert len(v['scores'])==6 and 1<=v['rank']<=6 and 0<=v['controls_beaten']<=5
                pos=v['scores'][0];neg=v['scores'][1:]
                assert v['controls_beaten']==sum(pos>c for c in neg)  # rank shown == rank of shown scores
    # Demo cases and explorer use the same out-of-training scores, so their counts must agree.
    for e in (x for x in events if x['demo_case']):
        for entry in data['cases'][e['demo_case']]['rankings']:
            assert entry['controls_beaten']==e['variants'][entry['model']][entry['features']]['controls_beaten']
