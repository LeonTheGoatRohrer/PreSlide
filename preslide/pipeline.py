"""Resumable real-data experiment; exclusions are recorded, never silently relaxed."""
import hashlib
import traceback
import numpy as np
import pandas as pd
from shapely import contains_xy
from .common import candidates,experiment_config,digest,read_json,write_json
from .sources import ROOT
from .terrain import PROJECT
from .matching import Exclusions,austria_boundary,match_event
from .weather import enrich_weather,TEMPORAL,cutoff

STATIC=['elevation','slope','aspect_sin','aspect_cos']

def representative_events(events,n=5):
    xy=np.array([PROJECT.transform(e['longitude'],e['latitude']) for e in events])
    selected=[0]
    while len(selected)<min(n,len(events)):
        distances=np.min(np.linalg.norm(xy[:,None,:]-xy[selected][None,:,:],axis=2),axis=1)
        distances[selected]=-1
        selected.append(int(np.argmax(distances)))
    return [events[i] for i in selected]

def validate_dataset(data,config):
    if data.sample_id.duplicated().any(): raise ValueError('Duplicate sample IDs')
    if not np.isfinite(data[STATIC+TEMPORAL].to_numpy()).all(): raise ValueError('Nonfinite features')
    for group,d in data.groupby('event_group_id'):
        if len(d)!=6 or d.label.sum()!=1 or d.event_date.nunique()!=1: raise ValueError('Invalid event group')
        if d.weather_hours_60d.min()!=1438: raise ValueError('Incomplete retained weather')
        if (pd.to_datetime(d.weather_last_timestamp,utc=True)+pd.Timedelta(hours=1)>=cutoff(d.event_date.iloc[0])).any():
            raise ValueError('Future weather leakage')
        c=d[d.label==0]
        distances=np.linalg.norm(c[['x','y']].to_numpy()[:,None,:]-c[['x','y']].to_numpy()[None,:,:],axis=2)
        distances+=np.eye(len(c))*1e9
        if distances.min()<config['control_separation_m']: raise ValueError('Overlapping controls')
        for column,limit in [('slope_difference_deg','slope_caliper_deg'),('elevation_difference_m','elevation_caliper_m'),('aspect_difference_deg','aspect_caliper_deg')]:
            if (c[column]>config[limit]).any(): raise ValueError('Matching caliper violation')
        if not c.inventory_clear.all() or not c.inside_austria.all(): raise ValueError('Control exclusion violated')
    return {'groups':data.event_group_id.nunique(),'rows':len(data),'positives':int(data.label.sum()),
            'controls':int((data.label==0).sum()),'finite_features':True,'same_time':True,
            'pre_event_envelope':True,'control_separation':True,'calipers':True}

def run_pipeline(limit=5):
    config=experiment_config();events=candidates()
    selected=representative_events(events,5)
    if limit>5: selected+= [e for e in events if e not in selected]
    selected=selected[:limit]
    identity=digest({'config':config,'candidates':events,'pipeline_version':1})[:16]
    output=ROOT/'data/processed'/identity
    output.mkdir(parents=True,exist_ok=True)
    inputs={'exclusion_inventory_sha256':hashlib.sha256((ROOT/'data/raw/geosphere_natural_hazards.json').read_bytes()).hexdigest(),
            'candidates_sha256':digest(events),'config':config,'pipeline_version':1}
    if (output/'inputs.json').exists() and read_json(output/'inputs.json')!=inputs:
        raise RuntimeError('Changed source snapshot: archive processed cache before proceeding')
    write_json(output/'inputs.json',inputs)
    country=austria_boundary();exclusions=Exclusions(config)
    completed=[];status=[]
    for number,event in enumerate(selected,1):
        eventdir=output/'events'/event['event_id'];eventdir.mkdir(parents=True,exist_ok=True)
        print(f"[{number}/{len(selected)}] {event['event_id']} {event['event_date']}",flush=True)
        try:
            if not contains_xy(country,event['longitude'],event['latitude']): raise ValueError('positive_outside_boundary')
            if (eventdir/'features.parquet').exists() and (eventdir/'complete.json').exists():
                meta=read_json(eventdir/'complete.json')
                for name,sha in meta['sha256'].items():
                    if hashlib.sha256((eventdir/name).read_bytes()).hexdigest()!=sha: raise ValueError('Cache integrity failure')
                features=pd.read_parquet(eventdir/'features.parquet')
            else:
                if (eventdir/'samples.parquet').exists():
                    meta=read_json(eventdir/'matching.json')
                    if 'samples_sha256' in meta and hashlib.sha256((eventdir/'samples.parquet').read_bytes()).hexdigest()!=meta['samples_sha256']:
                        raise RuntimeError('Matching checkpoint checksum mismatch')
                    samples=pd.read_parquet(eventdir/'samples.parquet')
                else:
                    samples,summary=match_event(event,config,exclusions,country)
                    samples.to_parquet(eventdir/'samples.parquet',index=False)
                    summary['samples_sha256']=hashlib.sha256((eventdir/'samples.parquet').read_bytes()).hexdigest()
                    write_json(eventdir/'matching.json',summary)
                features=enrich_weather(samples,config,eventdir)
                validate_dataset(features,config)
                write_json(eventdir/'complete.json',{'identity':identity,'sha256':{
                    name:hashlib.sha256((eventdir/name).read_bytes()).hexdigest()
                    for name in ['samples.parquet','features.parquet','history.parquet']}})
            completed.append(features)
            status.append({'event_id':event['event_id'],'status':'complete','date':event['event_date']})
            print('  complete: 1 positive + 5 controls, terrain + 60d weather',flush=True)
        except (ValueError,RuntimeError) as error:
            status.append({'event_id':event['event_id'],'status':'excluded','reason':str(error)})
            print('  excluded:',error,flush=True)
        except Exception:
            write_json(output/'status.json',status)
            raise
        write_json(output/'status.json',status)
    if not completed: raise RuntimeError('No complete event groups')
    data=pd.concat(completed,ignore_index=True)
    validation=validate_dataset(data,config)
    data.to_parquet(output/f'dataset_{limit}.parquet',index=False)
    write_json(output/f'validation_{limit}.json',validation)
    write_json(ROOT/'data/processed/latest.json',{'identity':identity,'directory':str(output),'dataset':f'dataset_{limit}.parquet',
               'config':config,'status':status,'validation':validation})
    print(validation,flush=True)
    return data,output
