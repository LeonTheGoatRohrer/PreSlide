"""Optional, separate recent-precipitation layer (INCA v1, hourly, ~1 km). Never an input of the relative shares.

This is precipitation of the last days, not soil moisture. Soil moisture needs a dedicated source (e.g. Sentinel-1) and
is not part of hangmap_v01.
"""
import numpy as np
import pandas as pd

from ..v04 import weather as W
from .build import cached_json
from .paths import config

LAG_HOURS = 3     # newest hours of the analysis may still be incomplete


def daily_sums(timestamps_utc, rain_mm):
    """UTC-day precipitation sums over complete days only; missing, negative or non-finite values raise."""
    rr = np.asarray([np.nan if v is None else v for v in rain_mm], float)
    if not np.isfinite(rr).all() or (rr < 0).any():
        raise ValueError('implausible or missing precipitation values')
    s = pd.Series(rr, index=pd.DatetimeIndex(timestamps_utc))
    counts = s.groupby(s.index.floor('D')).size()
    full = counts[counts == 24].index
    sums = s.groupby(s.index.floor('D')).sum()
    return [{'day_utc': d.strftime('%Y-%m-%d'), 'rain_mm': round(float(sums[d]), 1)} for d in full]


def recent_rain(lon, lat, now_utc=None):
    cfg = config()['recent_rain_layer']
    now = pd.Timestamp(now_utc if now_utc is not None else pd.Timestamp.now(tz='UTC')).floor('h')
    end = now - pd.Timedelta(hours=LAG_HOURS)
    start = (end - pd.Timedelta(days=cfg['days'] + 1)).floor('D')
    r = cached_json(W.API + 'inca-v1-1h-1km', {'parameters': 'RR', 'start': start.strftime('%Y-%m-%dT%H:%M'),
                                              'end': end.strftime('%Y-%m-%dT%H:%M'), 'lat_lon': f'{lat:.5f},{lon:.5f}',
                                              'output_format': 'geojson'}, f_param=False)
    par = r['features'][0]['properties']['parameters']['RR']
    if par['unit'] not in ('kg m-2', 'mm'):
        raise ValueError('Unexpected INCA unit')
    days = daily_sums(pd.to_datetime(r['timestamps'], utc=True), par['data'])[-cfg['days']:]
    return {'source': 'GeoSphere INCA v1 (1 km, stündlich)', 'label': cfg['label'], 'days': days,
            'sum_mm': round(sum(d['rain_mm'] for d in days), 1), 'in_score': False,
            'note': 'Niederschlag der letzten Tage am Gebietsmittelpunkt – keine Bodenfeuchte und nicht in den Anteilen enthalten.'}
