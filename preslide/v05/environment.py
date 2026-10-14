"""V0.5 environmental features with the unchanged V0.4 definitions; all requests go through the V0.5 cache.

Pure V0.4 functions (inca_features, daily_features, nearest, admissible, CORINE vintage/class rules, Esri ring
parsing) are reused unchanged; only the request layer is V0.5's, so nothing is ever written to data/v04.
"""
import json

import numpy as np
import pandas as pd
from shapely import STRtree, points
from shapely.geometry import shape

from ..v04 import weather as W
from ..v04 import context as C
from .http import cached_json


# ---------- weather ----------

def request_points(resource, parameters, start, end, latlon):
    features, timestamps = [], None
    for i in range(0, len(latlon), W.POINTS_PER_REQUEST):
        params = {'parameters': ','.join(parameters), 'start': start.strftime('%Y-%m-%dT%H:%M'),
                  'end': end.strftime('%Y-%m-%dT%H:%M'), 'lat_lon': latlon[i:i + W.POINTS_PER_REQUEST], 'output_format': 'geojson'}
        response = cached_json(W.API + resource, params, min_interval_s=W.INTERVAL_S, f_param=False)
        if timestamps is None:
            timestamps = response['timestamps']
        elif response['timestamps'] != timestamps:
            raise ValueError('Inconsistent timestamps across chunks')
        if len(response['features']) != len(latlon[i:i + W.POINTS_PER_REQUEST]):
            raise ValueError('Point count mismatch')
        features += response['features']
    return pd.to_datetime(timestamps, utc=True), features


def bundle_inca(samples):
    """Same as preslide.v04.weather.bundle_inca (one request window per event day), V0.5 cache."""
    t0s = pd.to_datetime(samples.t0_utc, utc=True)
    start = (t0s.min() - pd.Timedelta(days=60)).floor('h') - pd.Timedelta(hours=2)
    end = t0s.max() - pd.Timedelta(hours=1)
    latlon = [f'{r.latitude:.8f},{r.longitude:.8f}' for r in samples.itertuples()]
    times, pts = request_points('inca-v1-1h-1km', ['RR', 'T2M'], start, end, latlon)
    records, series = [], {}
    for row, point in zip(samples.itertuples(), pts):
        pars = point['properties']['parameters']
        if pars['RR']['unit'] not in ('kg m-2', 'mm') or pars['T2M']['unit'] != 'degree_Celsius':
            raise ValueError('Unexpected INCA units')
        cell, offset = W.nearest([point], row.x, row.y)
        t0 = pd.Timestamp(row.t0_utc)
        midnight = pd.Timestamp(row.event_day, tz='Europe/Vienna').tz_convert('UTC')
        try:
            values = W.inca_features(times, pars['RR']['data'], pars['T2M']['data'], t0, midnight, row.time_quality)
            values.update(weather_grid_lon=cell['geometry']['coordinates'][0], weather_grid_lat=cell['geometry']['coordinates'][1],
                          weather_grid_distance_m=offset, weather_status='complete')
        except ValueError as error:
            values = {'weather_status': str(error)}
        records.append({'sample_id': row.sample_id, **values})
        keep = W.admissible(times, t0, pd.Timedelta(days=60))
        series[row.sample_id] = pd.DataFrame({'timestamp': times[keep], 'rain': np.asarray(pars['RR']['data'], float)[keep],
                                              'temperature': np.asarray(pars['T2M']['data'], float)[keep]})
    return pd.DataFrame(records), series


def bundle_daily(samples, resource):
    t0s = pd.to_datetime(samples.t0_utc, utc=True)
    start = (t0s.min() - pd.Timedelta(days=200)).floor('D')
    end = (t0s.max() - pd.Timedelta(days=1)).floor('D')
    latlon = [f'{r.latitude:.8f},{r.longitude:.8f}' for r in samples.itertuples()]
    days, pts = request_points(resource, W.DAILY[resource], start, end, latlon)
    records = []
    for row, point in zip(samples.itertuples(), pts):
        try:
            _, offset = W.nearest([point], row.x, row.y)
        except ValueError:
            records.append({'sample_id': row.sample_id, f'{resource}_status': 'grid_offset'})
            continue
        pars = point['properties']['parameters']
        values = {k: np.array([np.nan if v is None else v for v in pars[k]['data']], float) for k in W.DAILY[resource]}
        feats, last_day = W.daily_features(days, values, pd.Timestamp(row.t0_utc))
        records.append({'sample_id': row.sample_id, **{k: feats[k] for k in W.RESOURCE_FEATURES[resource]},
                        f'{resource}_last_day': None if last_day is None else last_day.isoformat(),
                        f'{resource}_offset_m': offset})
    return pd.DataFrame(records)


# ---------- land cover and geology ----------

def land_cover(samples, classes):
    out = []
    for row in samples.itertuples():
        vintage = C.clc_vintage(row.t0_utc)
        url, field = C.CLC[vintage]
        response = cached_json(url, {'geometry': json.dumps({'x': round(row.longitude, 7), 'y': round(row.latitude, 7),
                                                             'spatialReference': {'wkid': 4326}}),
                                     'geometryType': 'esriGeometryPoint', 'inSR': '4326', 'spatialRel': 'esriSpatialRelIntersects',
                                     'outFields': field, 'returnGeometry': 'false'}, min_interval_s=0.2)
        codes = {f['attributes'][field] for f in response.get('features', [])}
        code = codes.pop() if len(codes) == 1 else None
        out.append({'sample_id': row.sample_id, 'clc_vintage': vintage, 'clc_code': code,
                    'land_cover_class': C.clc_class(code, classes) if code is not None else None})
    return pd.DataFrame(out)


_GEOLOGY = {}


def geology_layer():
    if 'tree' not in _GEOLOGY:
        ids = sorted(cached_json(C.GEOLOGY, {'where': '1=1', 'returnIdsOnly': 'true'})['objectIds'])
        geoms, lith = [], []
        for i in range(0, len(ids), 200):
            r = cached_json(C.GEOLOGY, {'objectIds': ','.join(map(str, ids[i:i + 200])), 'outFields': 'OBJECTID,representativeLithology',
                                        'outSR': '4326', 'returnGeometry': 'true'})
            for f in r['features']:
                rings = f['geometry']['rings']
                geoms.append(shape({'type': 'Polygon', 'coordinates': rings}) if len(rings) == 1 else C._rings(rings))
                lith.append(f['attributes']['representativeLithology'])
        if len(geoms) != len(ids):
            raise ValueError('Incomplete geology layer')
        _GEOLOGY.update(tree=STRtree(geoms), geoms=geoms, lith=lith)
    return _GEOLOGY


def geology(samples, classes):
    layer = geology_layer()
    pts = points(samples.longitude.to_numpy(), samples.latitude.to_numpy())
    out = []
    for sid, p in zip(samples.sample_id, pts):
        hits = [i for i in layer['tree'].query(p) if layer['geoms'][i].covers(p)]
        names = {layer['lith'][i] for i in hits}
        lith = names.pop() if len(names) == 1 else None
        cls = None
        if lith is not None:
            cls = next((k for k, v in classes.items() if isinstance(v, list) and lith in v), 'geo_crystalline_other')
        out.append({'sample_id': sid, 'lithology': lith, 'geology_class': cls})
    return pd.DataFrame(out)
