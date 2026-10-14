"""Small derived demonstration, explicitly separate from the raw inventory."""
import numpy as np
import pandas as pd
from PIL import Image
from pyproj import Transformer
from rasterio.transform import from_origin,array_bounds
from rasterio.warp import calculate_default_transform,reproject,Resampling
from matplotlib.colors import LightSource
from .common import read_json,write_json,candidates
from .pipeline import representative_events
from .sources import ROOT
from .terrain import local_terrain

def build_demo():
    from .baseline import pointer
    latest=pointer();directory=ROOT/'data/processed'/latest['identity']
    data=pd.read_parquet(directory/'evaluation_dataset.parquet')
    if data.event_group_id.nunique()<30: raise ValueError('Full scientific evaluation required before demo')
    metrics=read_json(ROOT/'reports/experiment/metrics.json')
    eligible=[e for e in candidates() if e['event_id'] in set(data.event_group_id)]
    selected=representative_events(eligible,5)
    dest=directory/'demo';dest.mkdir(exist_ok=True)
    cases=[]
    tolonlat=Transformer.from_crs(3857,4326,always_xy=True)
    for number,event in enumerate(selected,1):
        public_id=f'PS-{number:02d}'
        rows=data[data.event_group_id==event['event_id']]
        case={'id':public_id,'state':event['state'],'event_date':event['event_date'],
              'position_category_upper_m':event['position_accuracy_upper_m'],
              'partition':rows.partition.iloc[0],'samples':[],'history':[]}
        mapping={}
        for i,r in enumerate(rows.itertuples()):
            name='Ereignishang' if r.label==1 else f'Kontrolle {i}'
            mapping[r.sample_id]=name
            case['samples'].append({'name':name,'positive':bool(r.label),'longitude':round(r.longitude,5),'latitude':round(r.latitude,5),
                 'elevation':round(r.elevation,1),'slope':round(r.slope,1),'aspect':round(r.aspect,1),
                 'distance_m':round(r.distance_to_positive_m),'slope_difference':round(r.slope_difference_deg,1),
                 'elevation_difference':round(r.elevation_difference_m,1),'aspect_difference':round(r.aspect_difference_deg,1)})
        history=pd.read_parquet(directory/'events'/event['event_id']/'history.parquet')
        history['name']=history.sample_id.map(mapping)
        case['history']=history.drop(columns=['sample_id']).to_dict('records')
        terrain=local_terrain(event,latest['config']);z=terrain['elevation']
        src_transform=from_origin(float(terrain['left']),float(terrain['top']),float(terrain['resolution']),float(terrain['resolution']))
        bounds=array_bounds(*z.shape,src_transform)
        dst_transform,width,height=calculate_default_transform(31287,3857,z.shape[1],z.shape[0],*bounds)
        projected=np.full((height,width),np.nan,dtype='float32')
        reproject(z,projected,src_transform=src_transform,src_crs=31287,dst_transform=dst_transform,dst_crs=3857,
                  src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.bilinear)
        valid=np.isfinite(projected);filled=np.where(valid,projected,np.nanmedian(projected))
        shade=LightSource(azdeg=315,altdeg=40).hillshade(filled,vert_exag=1.2,dx=dst_transform.a,dy=abs(dst_transform.e))
        grey=(210+shade*43).astype('uint8')
        rgba=np.stack([grey,grey,grey,valid.astype('uint8')*255],axis=-1)
        Image.fromarray(rgba).save(dest/f'{public_id}.png')
        left,bottom,right,top=array_bounds(height,width,dst_transform)
        case['terrain_corners']=[list(tolonlat.transform(x,y)) for x,y in [(left,top),(right,top),(right,bottom),(left,bottom)]]
        case['terrain_url']=f'/api/cases/{public_id}/terrain.png'
        write_json(dest/f'{public_id}.json',case)
        cases.append({k:case[k] for k in ['id','state','event_date','position_category_upper_m']})
    write_json(dest/'cases.json',cases)
    write_json(dest/'summary.json',metrics)
    write_json(ROOT/'data/processed/demo.json',{'directory':str(dest),'dataset_identity':latest['identity'],
        'policy':'Five derived demonstration groups only. No raw inventory records, original identifiers, observer fields or bulk export.'})
    print('Prepared five derived demo groups:',[c['id'] for c in cases],flush=True)

if __name__=='__main__':build_demo()
