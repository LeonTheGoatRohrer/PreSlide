import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import shape
from shapely import contains_xy
from .sources import ROOT, cached_json
from .common import read_json, write_json, digest
from .terrain import PROJECT, INVERSE, local_terrain, sample
from .audit import position_bounds

def austria_boundary():
    data=cached_json('https://gisco-services.ec.europa.eu/distribution/v2/nuts/distribution/AT-region-01m-4326-2016.geojson')
    if data['type']=='FeatureCollection':
        from shapely.ops import unary_union
        return unary_union([shape(f['geometry']) for f in data['features']])
    return shape(data['geometry'] if data['type']=='Feature' else data)

def angular_distance(a,b):
    return np.abs((np.asarray(a)-np.asarray(b)+180)%360-180)

class Exclusions:
    def __init__(self,config):
        features=read_json(ROOT/'data/raw/geosphere_natural_hazards.json')['features']
        xy=[]; radii=[]
        for f in features:
            if not f.get('geometry'): continue
            a=f['attributes'];g=f['geometry']
            if a.get('Prozessgruppe') not in ['Gleiten/Rutschen','Fliessen','Massenbewegung (unklarer Typ)']: continue
            lower,upper=position_bounds(a.get('QUAL_LAGE'))
            uncertainty=upper if upper is not None else config['unknown_position_buffer_m']
            xy.append(PROJECT.transform(g['x'],g['y']))
            radii.append(config['exclusion_extent_buffer_m']+uncertainty)
        self.xy=np.array(xy);self.radii=np.array(radii);self.tree=cKDTree(self.xy)

    def allowed(self,xy):
        neighbors=self.tree.query_ball_point(xy,float(self.radii.max()))
        return np.array([all(np.linalg.norm(p-self.xy[j])>self.radii[j] for j in js) for p,js in zip(xy,neighbors)])

def match_event(event,config,exclusions,country=None):
    terrain=local_terrain(event,config)
    px,py=PROJECT.transform(event['longitude'],event['latitude'])
    positive={k:float(v[0]) for k,v in sample(terrain,[px],[py]).items()}
    if not all(np.isfinite(v) for v in positive.values()) or not 0<=positive['elevation']<=4500:
        raise ValueError('invalid_positive_terrain')
    if positive['slope']<config['minimum_slope_deg']:
        raise ValueError('positive_dem_slope_below_minimum')
    seed=int(digest([event['event_id'],config['random_seed']])[:8],16)
    rng=np.random.default_rng(seed)
    n=config['candidate_pool_size']
    distance=np.sqrt(rng.uniform(config['control_min_distance_m']**2,config['control_max_distance_m']**2,n))
    angle=rng.uniform(0,2*np.pi,n)
    xy=np.column_stack([px+distance*np.cos(angle),py+distance*np.sin(angle)])
    lon,lat=INVERSE.transform(xy[:,0],xy[:,1])
    values=sample(terrain,xy[:,0],xy[:,1])
    frame=pd.DataFrame({'x':xy[:,0],'y':xy[:,1],'longitude':lon,'latitude':lat,
                       'distance_to_positive_m':distance,**values})
    frame['slope_difference_deg']=np.abs(frame.slope-positive['slope'])
    frame['elevation_difference_m']=np.abs(frame.elevation-positive['elevation'])
    frame['aspect_difference_deg']=angular_distance(frame.aspect,positive['aspect'])
    frame['inventory_clear']=exclusions.allowed(xy)
    frame['inside_austria']=contains_xy(country,lon,lat) if country is not None else True
    keep=(frame.inventory_clear & frame.inside_austria & (frame.slope>=config['minimum_slope_deg']) &
          (frame.slope_difference_deg<=config['slope_caliper_deg']) &
          (frame.elevation_difference_m<=config['elevation_caliper_m']) &
          (frame.aspect_difference_deg<=config['aspect_caliper_deg']))
    frame['matching_score']=(frame.slope_difference_deg/config['slope_caliper_deg'])**2+(
        frame.elevation_difference_m/config['elevation_caliper_m'])**2+(
        frame.aspect_difference_deg/config['aspect_caliper_deg'])**2+0.15*(distance/config['control_max_distance_m'])**2
    frame['passes_calipers']=keep
    selected=[]
    for i,row in frame[keep].sort_values('matching_score').iterrows():
        if all(np.linalg.norm(xy[i]-xy[j])>=config['control_separation_m'] for j in selected):
            selected.append(i)
        if len(selected)==config['controls_per_event']: break
    pool=ROOT/'data/interim/control_pools'/f"{event['event_id']}_{digest(config)[:12]}.parquet"
    pool.parent.mkdir(parents=True,exist_ok=True);frame.to_parquet(pool,index=False)
    if len(selected)<config['controls_per_event']:
        raise ValueError(f'insufficient_controls:{len(selected)}_from_{int(keep.sum())}_eligible')
    common={'event_group_id':event['event_id'],'event_date':event['event_date'],'state':event['state'],
            'source_position_upper_m':event['position_accuracy_upper_m'],
            'source_status':event['source_status'],'date_quality':event['date_quality'],
            'source_attribution':'GeoSphere Austria; Naturgefahren Test; license unidentified',
            'process_type':event['process_type_original']}
    rows=[{**common,'sample_id':event['event_id']+'_positive','label':1,'sample_type':'POSITIVE',
           'longitude':event['longitude'],'latitude':event['latitude'],'x':px,'y':py,**positive,
           'distance_to_positive_m':0.,'matching_score':0.,'slope_difference_deg':0.,'elevation_difference_m':0.,'aspect_difference_deg':0.}]
    for number,i in enumerate(selected,1):
        rows.append({**common,**frame.loc[i].to_dict(),'sample_id':f"{event['event_id']}_control_{number:02d}",
                     'label':0,'sample_type':'PSEUDO_NEGATIVE'})
    data=pd.DataFrame(rows)
    data['aspect_sin']=np.sin(np.deg2rad(data.aspect));data['aspect_cos']=np.cos(np.deg2rad(data.aspect))
    return data,{'candidate_pool':n,'eligible_pool':int(keep.sum()),'selected':len(selected)}
