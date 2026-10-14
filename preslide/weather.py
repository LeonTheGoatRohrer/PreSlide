"""Observed INCA weather, conservative timestamp envelopes, no event-day data."""
import numpy as np
import pandas as pd
from .sources import ROOT, cached_json
from .terrain import PROJECT
from .common import write_json

WINDOWS=(1,3,7,14,30,60)
TEMPORAL=[f'{name}_{w}d' for w in WINDOWS for name in ('rain_sum','rain_max_hour','temperature_mean')]

def cutoff(event_date):
    return pd.Timestamp(event_date,tz='Europe/Vienna').tz_convert('UTC')

def window_mask(times,event_date,days,guard=1):
    end=cutoff(event_date)
    delta=pd.Timedelta(hours=guard)
    return (times-delta>=end-pd.Timedelta(days=days)) & (times+delta<end)

def expected_times(event_date,days,guard=1):
    end=cutoff(event_date)
    times=pd.date_range(end-pd.Timedelta(days=days),end,freq='h')
    return times[window_mask(times,event_date,days,guard)]

def features_from_series(times,rain,temperature,event_date,guard=1):
    times=pd.DatetimeIndex(times)
    if times.tz is None or times.has_duplicates or not times.is_monotonic_increasing:
        raise ValueError('Weather timestamps must be unique, sorted and timezone-aware')
    rain=np.asarray(rain,dtype=float);temperature=np.asarray(temperature,dtype=float)
    if len(times)!=len(rain) or len(times)!=len(temperature): raise ValueError('Weather length mismatch')
    result={}
    for w in WINDOWS:
        keep=window_mask(times,event_date,w,guard)
        if not times[keep].equals(expected_times(event_date,w,guard)):
            raise ValueError(f'incomplete_weather_timestamps:{w}d')
        r=rain[keep];t=temperature[keep]
        if not np.isfinite(r).all() or not np.isfinite(t).all():
            raise ValueError(f'missing_weather_values:{w}d_RR={int((~np.isfinite(r)).sum())}_T2M={int((~np.isfinite(t)).sum())}')
        if np.any((r<0)|(r>500)) or np.any((t< -60)|(t>60)):
            raise ValueError(f'implausible_weather_values:{w}d_RRmin={r.min():.3f}_RRmax={r.max():.3f}_Tmin={t.min():.3f}_Tmax={t.max():.3f}')
        result.update({f'rain_sum_{w}d':float(r.sum()),f'rain_max_hour_{w}d':float(r.max()),
                       f'temperature_mean_{w}d':float(t.mean())})
    return result

def enrich_weather(samples,config,output_dir):
    event_date=samples.event_date.iloc[0]
    if samples.event_date.nunique()!=1: raise ValueError('Controls must inherit same event date')
    end=cutoff(event_date)
    start=end-pd.Timedelta(days=config['history_days'])
    params={'parameters':'RR,T2M','start':start.strftime('%Y-%m-%dT%H:%M'),
            'end':(end-pd.Timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'lat_lon':[f'{r.latitude:.8f},{r.longitude:.8f}' for r in samples.itertuples()],
            'output_format':'geojson'}
    response=cached_json('https://dataset.api.hub.geosphere.at/v1/timeseries/historical/'+config['weather_resource'],params)
    times=pd.to_datetime(response['timestamps'],utc=True)
    points=response['features']
    xy=np.array([PROJECT.transform(*p['geometry']['coordinates']) for p in points])
    records=[];histories=[]
    for row in samples.to_dict('records'):
        distances=np.linalg.norm(xy-np.array([row['x'],row['y']]),axis=1)
        i=int(np.argmin(distances))
        if distances[i]>800: raise ValueError('Weather nearest-cell offset exceeds half-grid diagonal tolerance')
        p=points[i];pars=p['properties']['parameters']
        if pars['RR']['unit'] not in ['kg m-2','kg m**-2','mm']: raise ValueError('Unexpected RR unit: '+pars['RR']['unit'])
        if pars['T2M']['unit'] not in ['degree_Celsius','degC','°C']: raise ValueError('Unexpected T2M unit: '+pars['T2M']['unit'])
        values=features_from_series(times,pars['RR']['data'],pars['T2M']['data'],event_date,config['weather_boundary_guard_hours'])
        lon,lat=p['geometry']['coordinates']
        row.update(values)
        row.update(weather_grid_lon=lon,weather_grid_lat=lat,weather_grid_distance_m=float(distances[i]),
                   weather_last_timestamp=expected_times(event_date,60)[-1].isoformat(),
                   weather_first_timestamp=expected_times(event_date,60)[0].isoformat(),
                   weather_hours_60d=len(expected_times(event_date,60)))
        records.append(row)
        mask=window_mask(times,event_date,60,config['weather_boundary_guard_hours'])
        daily=pd.DataFrame({'timestamp':times[mask], 'rain':np.array(pars['RR']['data'])[mask],
                            'temperature':np.array(pars['T2M']['data'])[mask]})
        daily['date']=daily.timestamp.dt.tz_convert('Europe/Vienna').dt.strftime('%Y-%m-%d')
        for day,d in daily.groupby('date'):
            histories.append({'sample_id':row['sample_id'],'date':day,'rain_mm':float(d.rain.sum()),
                              'temperature_c':float(d.temperature.mean()),'hours':len(d)})
    result=pd.DataFrame(records)
    result.to_parquet(output_dir/'features.parquet',index=False)
    pd.DataFrame(histories).to_parquet(output_dir/'history.parquet',index=False)
    write_json(output_dir/'weather_validation.json',{'resource':config['weather_resource'],
        'requested_samples':len(samples),'returned_cells':len(points),
        'unique_matched_cells':result[['weather_grid_lon','weather_grid_lat']].drop_duplicates().shape[0],
        'retained_hours_60d':len(expected_times(event_date,60)),'cutoff_utc':end.isoformat(),
        'timestamp_envelope_hours':config['weather_boundary_guard_hours'],'params':params})
    return result
