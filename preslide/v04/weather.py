"""V0.4 pre-event weather: INCA hourly (windows anchored at t0, same-day rain) and daily GeoSphere grids.

Timestamp rules (config/v04.json):
  * INCA hourly value at T is admissible iff T + 1 h < t0 (the 1-h interval may end or start at T).
  * Window [t0 - W, t0): additionally T - 1 h >= t0 - W.
  * Daily products: value labelled day D is valid at D+1 06:00 UTC and admissible iff that is < t0.
"""
import numpy as np
import pandas as pd

from ..terrain import PROJECT
from .http import cached_json

API = 'https://dataset.api.hub.geosphere.at/v1/timeseries/historical/'
WINDOWS = (1, 3, 7, 14, 30, 60)
INCA_FEATURES = [f'{n}_{w}d' for w in WINDOWS for n in ('rain_sum', 'rain_max_hour', 'temperature_mean')]
SAME_DAY = ['rain_since_midnight', 'rain_max_hour_since_midnight', 'rain_3h_before_t0', 'rain_6h_before_t0']
DAILY = {'spartacus-v2-1d-1km': ['RR'], 'snowgrid_cl-v2-1d-1km': ['swe_tot', 'snow_depth'],
         'winfore-v2-1d-1km': ['SPEI30', 'SPEI90']}
DAILY_FEATURES = ['spartacus_rr_90d', 'spartacus_rr_180d', 'swe_last', 'snow_depth_last', 'swe_melt_3d',
                  'swe_melt_7d', 'swe_melt_14d', 'spei30_last', 'spei90_last']
GUARD = pd.Timedelta(hours=1)
DAY_VALID = pd.Timedelta(hours=30)          # D 00:00 UTC label -> valid at D+1 06:00 UTC
POINTS_PER_REQUEST = 100
INTERVAL_S = 15.5                            # <= 232 requests/hour (limit 240/h, 5/s)


def admissible(times, t0, window=None):
    keep = times + GUARD < t0
    if window is not None:
        keep &= times - GUARD >= t0 - window
    return keep


def expected_hours(t0, window):
    times = pd.date_range((t0 - window).floor('h') - pd.Timedelta(hours=2), t0, freq='h')
    return times[admissible(times, t0, window)]


def inca_features(times, rain, temperature, t0, midnight, time_quality):
    """Core 60-day windows (complete or ValueError) and same-day rain (NaN unless the time of day is known)."""
    times = pd.DatetimeIndex(times)
    if times.tz is None or times.has_duplicates or not times.is_monotonic_increasing:
        raise ValueError('Weather timestamps must be unique, sorted and timezone-aware')
    rain, temperature = np.asarray(rain, float), np.asarray(temperature, float)
    out = {}
    for w in WINDOWS:
        keep = admissible(times, t0, pd.Timedelta(days=w))
        if not times[keep].equals(expected_hours(t0, pd.Timedelta(days=w))):
            raise ValueError(f'incomplete_weather_timestamps:{w}d')
        r, t = rain[keep], temperature[keep]
        if not np.isfinite(r).all() or not np.isfinite(t).all():
            raise ValueError(f'missing_weather_values:{w}d')
        if np.any((r < 0) | (r > 500)) or np.any((t < -60) | (t > 60)):
            raise ValueError(f'implausible_weather_values:{w}d_RRmin={r.min():.3f}_RRmax={r.max():.3f}')
        out.update({f'rain_sum_{w}d': float(r.sum()), f'rain_max_hour_{w}d': float(r.max()),
                    f'temperature_mean_{w}d': float(t.mean())})
    out.update({k: np.nan for k in SAME_DAY})
    out['same_day_hours'] = 0
    if time_quality in ('daypart', 'clock'):
        keep = admissible(times, t0) & (times - GUARD >= midnight)
        r = rain[keep]
        out['same_day_hours'] = int(keep.sum())
        if keep.sum() > 0 and np.isfinite(r).all():
            out['rain_since_midnight'] = float(r.sum())
            out['rain_max_hour_since_midnight'] = float(r.max())
        recent = rain[admissible(times, t0)]
        for k, name in ((3, 'rain_3h_before_t0'), (6, 'rain_6h_before_t0')):
            if keep.sum() >= k and np.isfinite(recent[-k:]).all():
                out[name] = float(recent[-k:].sum())     # the k most recent admissible hours, all after midnight
    out['last_used_hour_utc'] = times[admissible(times, t0)][-1].isoformat()
    return out


def nearest(points, x, y, tolerance=800):
    xy = np.array([PROJECT.transform(*p['geometry']['coordinates']) for p in points])
    d = np.linalg.norm(xy - np.array([x, y]), axis=1)
    i = int(np.argmin(d))
    if d[i] > tolerance:
        raise ValueError('Weather nearest-cell offset exceeds tolerance')
    return points[i], float(d[i])


def request_points(resource, parameters, start, end, latlon):
    """Chunked point time series requests; returns timestamps and feature list (cached, rate limited)."""
    features, timestamps = [], None
    for i in range(0, len(latlon), POINTS_PER_REQUEST):
        params = {'parameters': ','.join(parameters), 'start': start.strftime('%Y-%m-%dT%H:%M'),
                  'end': end.strftime('%Y-%m-%dT%H:%M'), 'lat_lon': latlon[i:i + POINTS_PER_REQUEST], 'output_format': 'geojson'}
        response = cached_json(API + resource, params, min_interval_s=INTERVAL_S, f_param=False)
        if timestamps is None:
            timestamps = response['timestamps']
        elif response['timestamps'] != timestamps:
            raise ValueError('Inconsistent timestamps across chunks')
        if len(response['features']) != len(latlon[i:i + POINTS_PER_REQUEST]):
            raise ValueError('Point count mismatch')
        features += response['features']
    return pd.to_datetime(timestamps, utc=True), features


def bundle_inca(samples):
    """samples: all samples of events sharing one event_day. Returns per-sample features or exclusion reason."""
    t0s = pd.to_datetime(samples.t0_utc, utc=True)
    start = (t0s.min() - pd.Timedelta(days=60)).floor('h') - pd.Timedelta(hours=2)
    end = t0s.max() - pd.Timedelta(hours=1)
    latlon = [f'{r.latitude:.8f},{r.longitude:.8f}' for r in samples.itertuples()]
    times, points = request_points('inca-v1-1h-1km', ['RR', 'T2M'], start, end, latlon)
    records, series = [], {}
    for row, point in zip(samples.itertuples(), points):
        pars = point['properties']['parameters']
        if pars['RR']['unit'] not in ('kg m-2', 'mm') or pars['T2M']['unit'] != 'degree_Celsius':
            raise ValueError('Unexpected INCA units')
        cell, offset = nearest([point], row.x, row.y)
        t0 = pd.Timestamp(row.t0_utc)
        midnight = pd.Timestamp(row.event_day, tz='Europe/Vienna').tz_convert('UTC')
        try:
            values = inca_features(times, pars['RR']['data'], pars['T2M']['data'], t0, midnight, row.time_quality)
            values.update(weather_grid_lon=cell['geometry']['coordinates'][0], weather_grid_lat=cell['geometry']['coordinates'][1],
                          weather_grid_distance_m=offset, weather_status='complete')
        except ValueError as error:
            values = {'weather_status': str(error)}
        records.append({'sample_id': row.sample_id, **values})
        keep = admissible(times, t0, pd.Timedelta(days=60))
        series[row.sample_id] = pd.DataFrame({'timestamp': times[keep], 'rain': np.asarray(pars['RR']['data'], float)[keep],
                                              'temperature': np.asarray(pars['T2M']['data'], float)[keep]})
    return pd.DataFrame(records), series


def daily_features(days, values, t0):
    """values: dict parameter -> array aligned to `days` (UTC midnight labels)."""
    keep = days + DAY_VALID < t0
    out = {k: np.nan for k in DAILY_FEATURES}
    idx = np.flatnonzero(keep)
    if len(idx) == 0:
        return out, None
    last = idx[-1]
    if 'RR' in values:
        rr = np.asarray(values['RR'], float)
        for n in (90, 180):
            window = rr[last - n + 1:last + 1] if last - n + 1 >= 0 else None
            if window is not None and np.isfinite(window).all() and (window >= 0).all():
                out[f'spartacus_rr_{n}d'] = float(window.sum())
    if 'swe_tot' in values:
        swe, depth = np.asarray(values['swe_tot'], float), np.asarray(values['snow_depth'], float)
        if np.isfinite(swe[last]) and swe[last] >= 0:
            out['swe_last'] = float(swe[last])
        if np.isfinite(depth[last]) and depth[last] >= 0:
            out['snow_depth_last'] = float(depth[last])
        for k in (3, 7, 14):
            if last - k >= 0 and np.isfinite(swe[[last - k, last]]).all():
                out[f'swe_melt_{k}d'] = float(max(0.0, swe[last - k] - swe[last]))
    for name in ('SPEI30', 'SPEI90'):
        if name in values:
            v = float(np.asarray(values[name], float)[last])
            if np.isfinite(v) and -10 < v < 10:
                out[f'{name.lower()}_last'] = v
    return out, days[last]


def bundle_daily(samples, resource):
    t0s = pd.to_datetime(samples.t0_utc, utc=True)
    start = (t0s.min() - pd.Timedelta(days=200)).floor('D')
    end = (t0s.max() - pd.Timedelta(days=1)).floor('D')
    latlon = [f'{r.latitude:.8f},{r.longitude:.8f}' for r in samples.itertuples()]
    days, points = request_points(resource, DAILY[resource], start, end, latlon)
    records = []
    for row, point in zip(samples.itertuples(), points):
        try:
            _, offset = nearest([point], row.x, row.y)
        except ValueError:
            records.append({'sample_id': row.sample_id, f'{resource}_status': 'grid_offset'})
            continue
        pars = point['properties']['parameters']
        values = {k: np.array([np.nan if v is None else v for v in pars[k]['data']], float) for k in DAILY[resource]}
        feats, last_day = daily_features(days, values, pd.Timestamp(row.t0_utc))
        keep = {k: v for k, v in feats.items() if not np.isnan(v) or k in RESOURCE_FEATURES[resource]}
        records.append({'sample_id': row.sample_id, **{k: keep[k] for k in RESOURCE_FEATURES[resource]},
                        f'{resource}_last_day': None if last_day is None else last_day.isoformat(),
                        f'{resource}_offset_m': offset})
    return pd.DataFrame(records)


RESOURCE_FEATURES = {'spartacus-v2-1d-1km': ['spartacus_rr_90d', 'spartacus_rr_180d'],
                     'snowgrid_cl-v2-1d-1km': ['swe_last', 'snow_depth_last', 'swe_melt_3d', 'swe_melt_7d', 'swe_melt_14d'],
                     'winfore-v2-1d-1km': ['spei30_last', 'spei90_last']}
