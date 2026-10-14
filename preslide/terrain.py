"""Pre-event, timestamp-checked Skadi tiles; local metric raster derivatives."""
import gzip
import hashlib
import math
import shutil
import subprocess
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import from_bounds, Window
from rasterio.warp import reproject, transform_bounds, Resampling
from pyproj import Transformer, Geod
from .common import read_json, write_json, digest
from .sources import ROOT

PROJECT = Transformer.from_crs('EPSG:4326','EPSG:31287',always_xy=True)
INVERSE = Transformer.from_crs('EPSG:31287','EPSG:4326',always_xy=True)
GEOD = Geod(ellps='WGS84')
_VERIFIED_TILES=set()

def tile(lat, lon, event_date):
    name = f'N{lat:02d}E{lon:03d}'
    directory = ROOT/'data/raw/terrain'
    directory.mkdir(parents=True,exist_ok=True)
    hgt = directory/f'{name}.hgt'
    manifest = directory/f'{name}.json'
    if not hgt.exists():
        url = f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat:02d}/{name}.hgt.gz'
        compressed = directory/f'{name}.hgt.gz'
        headers = directory/f'{name}.headers.txt'
        subprocess.run([shutil.which('curl.exe') or 'curl','-f','-sS','-L','--retry','2','--max-time','180',
                        '-D',str(headers),'-o',str(compressed),url],check=True,timeout=550)
        last = [s.split(':',1)[1].strip() for s in headers.read_text().splitlines() if s.lower().startswith('last-modified:')]
        if not last:
            raise ValueError('Terrain object lacks dated provenance')
        modified = parsedate_to_datetime(last[-1])
        if modified.date().isoformat() >= event_date:
            raise ValueError(f'Terrain object {name} is not demonstrated to predate event')
        with gzip.open(compressed,'rb') as src, hgt.with_suffix('.tmp').open('wb') as dst:
            shutil.copyfileobj(src,dst)
        hgt.with_suffix('.tmp').replace(hgt)
        if hgt.stat().st_size != 3601*3601*2:
            raise ValueError('Unexpected Skadi dimensions')
        write_json(manifest,{'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),
             'object_last_modified':modified.isoformat(),'sha256':hashlib.sha256(hgt.read_bytes()).hexdigest(),
             'source':'Mapzen Skadi composite; attribution includes Austrian DGM, EU-DEM and USGS',
             'vertical_datum':'EGM96','resolution':'1 arc second','nodata':-32768})
    meta = read_json(manifest)
    if str(hgt) not in _VERIFIED_TILES:
        if hashlib.sha256(hgt.read_bytes()).hexdigest()!=meta['sha256']:
            raise ValueError('Terrain source cache checksum mismatch')
        _VERIFIED_TILES.add(str(hgt))
    if meta['object_last_modified'][:10] >= event_date:
        raise ValueError('Post-event terrain object rejected')
    return hgt, meta

def derivatives(elevation, resolution):
    # Row increases southward; column increases eastward. Downslope azimuth is clockwise from north.
    south, east = np.gradient(elevation.astype(float), resolution, resolution)
    slope = np.degrees(np.arctan(np.hypot(east,south)))
    aspect = np.degrees(np.arctan2(-east, south)) % 360
    return slope.astype('float32'), aspect.astype('float32')

def local_terrain(event, config):
    if config['terrain_crs']!='EPSG:31287': raise ValueError('Matching requires Austria Lambert metric CRS')
    identity = digest({'lon':event['longitude'],'lat':event['latitude'],'t0':event['event_date'],
                       'radius':config['control_max_distance_m'],'resolution':config['terrain_resolution_m'],'algorithm':1})
    output = ROOT/'data/interim/terrain'/f'{identity}.npz'
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        meta=read_json(output.with_suffix('.json'))
        if hashlib.sha256(output.read_bytes()).hexdigest()!=meta['sha256']:
            raise ValueError('Terrain feature cache checksum mismatch')
        if any(s['object_last_modified'][:10]>=event['event_date'] for s in meta['sources']):
            raise ValueError('Cached terrain not pre-event')
        z = np.load(output)
        return {k:z[k] for k in z.files}
    px,py = PROJECT.transform(event['longitude'],event['latitude'])
    radius=config['control_max_distance_m']+300
    res=config['terrain_resolution_m']
    n=math.ceil(2*radius/res)
    left,top=px-radius,py+radius
    transform=from_origin(left,top,res,res)
    dem=np.full((n,n),np.nan,dtype='float32')
    bounds=transform_bounds(config['terrain_crs'],'EPSG:4326',left,top-n*res,left+n*res,top,densify_pts=21)
    sources=[]
    for lon in range(math.floor(bounds[0]),math.floor(bounds[2])+1):
        for lat in range(math.floor(bounds[1]),math.floor(bounds[3])+1):
            path,meta=tile(lat,lon,event['event_date'])
            with rasterio.open(path) as src:
                if src.crs.to_epsg()!=4326 or src.nodata!=-32768:
                    raise ValueError('Unexpected DEM CRS/nodata')
                win=from_bounds(max(bounds[0]-.001,src.bounds.left),max(bounds[1]-.001,src.bounds.bottom),
                                min(bounds[2]+.001,src.bounds.right),min(bounds[3]+.001,src.bounds.top),src.transform)
                win=win.round_offsets().round_lengths().intersection(Window(0,0,src.width,src.height))
                reproject(src.read(1,window=win), dem, src_transform=src.window_transform(win),src_crs=src.crs,
                          dst_transform=transform,dst_crs=config['terrain_crs'],src_nodata=-32768,dst_nodata=np.nan,
                          init_dest_nodata=False,resampling=Resampling.bilinear)
            sources.append(meta)
    slope,aspect=derivatives(dem,res)
    result={'elevation':dem,'slope':slope,'aspect':aspect,'left':np.array(left),'top':np.array(top),'resolution':np.array(res)}
    np.savez_compressed(output,**result)
    write_json(output.with_suffix('.json'),{'sources':sources,'event_id':event['event_id'],'config':config,
               'crs':config['terrain_crs'],'sha256':hashlib.sha256(output.read_bytes()).hexdigest()})
    return result

def sample(terrain, xs, ys):
    cols=np.floor((np.asarray(xs)-float(terrain['left']))/float(terrain['resolution'])).astype(int)
    rows=np.floor((float(terrain['top'])-np.asarray(ys))/float(terrain['resolution'])).astype(int)
    if np.any(cols<0) or np.any(rows<0) or np.any(cols>=terrain['elevation'].shape[1]) or np.any(rows>=terrain['elevation'].shape[0]):
        raise ValueError('Sample outside terrain window')
    return {name:terrain[name][rows,cols].astype(float) for name in ['elevation','slope','aspect']}
