"""Cohort, SPARTACUS daily series and dated inventory records for extremwetter_v01 (IO layer)."""
import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..pruefgebiete.overview import process_class
from ..terrain import PROJECT
from ..v04.units import temporal_episodes
from ..v04.weather import nearest
from .design import TZ, check_series
from .http import cached_json
from .paths import INVENTORY, V04_DATASET

API = 'https://dataset.api.hub.geosphere.at/v1/timeseries/historical/'
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def cohort(cfg: dict) -> pd.DataFrame:
    """One row per positive of the frozen V0.4 run, with process class and temporal episode."""
    data = pd.read_parquet(V04_DATASET)
    events = data[data.label == 1].copy()
    if len(events) != cfg['cohort']['expected_events'] or events.event_group_id.duplicated().any():
        raise ValueError(f'Unexpected cohort: {len(events)} positives')
    for column in ('event_day', 'latitude', 'longitude', 'x', 'y', 'process_type'):
        if events[column].isna().any():
            raise ValueError(f'Missing {column} in cohort')
    events['event_day'] = pd.to_datetime(events.event_day).dt.date
    events['process_class'] = events.process_type.map(process_class)
    counts = events.process_class.value_counts().to_dict()
    expected = {k: v for k, v in cfg['cohort']['subgroups'].items() if k != 'rule'}
    if counts != expected:
        raise ValueError(f'Subgroup counts {counts} != registered {expected}')
    events['episode'] = temporal_episodes(list(events.event_day))
    stanz = date.fromisoformat('2016-07-25')
    events['stanz'] = events.episode == events.loc[events.event_day == stanz, 'episode'].iloc[0]
    cols = ['event_group_id', 'event_day', 'time_quality', 'process_class', 'episode', 'stanz', 'latitude', 'longitude', 'x', 'y']
    return events[cols].sort_values('event_group_id').reset_index(drop=True)


def spartacus(events: pd.DataFrame, cfg: dict) -> tuple[dict, dict]:
    """Daily RR per event (cached raw responses).

    Returns ({event_group_id: (first_label, values, offset_m, lon, lat)}, {event_group_id: exclusion reason}).
    """
    w = cfg['weather']
    start, end = w['request_period']
    out, excluded, step = {}, {}, w['points_per_request']
    for i in range(0, len(events), step):
        chunk = events.iloc[i:i + step]
        params = {'parameters': w['parameter'], 'start': f'{start}T00:00', 'end': f'{end}T00:00',
                  'lat_lon': [f'{r.latitude:.8f},{r.longitude:.8f}' for r in chunk.itertuples()], 'output_format': 'geojson'}
        response = cached_json(API + w['resource'], params)
        stamps = pd.to_datetime(response['timestamps'], utc=True)
        if len(stamps) < 2 or not ((stamps[1:] - stamps[:-1]) == pd.Timedelta(days=1)).all() or (stamps.hour != 0).any():
            raise ValueError('SPARTACUS timestamps are not consecutive UTC-midnight days')
        if len(response['features']) != len(chunk):
            raise ValueError('Point count mismatch')
        for row, feature in zip(chunk.itertuples(), response['features']):
            rr = feature['properties']['parameters'][w['parameter']]
            if rr['unit'] not in ('kg m-2', 'mm'):
                raise ValueError(f"Unexpected RR unit {rr['unit']}")
            cell, offset = nearest([feature], row.x, row.y)
            if all(v is None for v in rr['data']):
                excluded[row.event_group_id] = 'no_spartacus_data_at_cell'     # AMENDMENT_1: cell outside product mask
                continue
            values = check_series([np.nan if v is None else v for v in rr['data']])
            lon, lat = cell['geometry']['coordinates']
            out[row.event_group_id] = (stamps[0].date(), values, offset, lon, lat)
    return out, excluded


def _local_day(ms) -> date:
    # epoch + timedelta: fromtimestamp() rejects pre-1970 values on Windows
    return (EPOCH + timedelta(milliseconds=ms)).astimezone(TZ).date()


def dated_records(cfg: dict) -> tuple[pd.DataFrame, dict]:
    """Inventory records usable for reference-day exclusion, with EPSG:31287 x/y and local day interval."""
    rule = cfg['reference']['documented_event_exclusion']
    features = json.loads(INVENTORY.read_text(encoding='utf-8'))['features']
    rows, counts = [], {'other_process_group': 0, 'no_interval': 0, 'interval_over_31_days': 0, 'used': 0}
    for f in features:
        a = f['attributes']
        if a.get('Prozessgruppe') not in rule['process_groups']:
            counts['other_process_group'] += 1
            continue
        if a.get('Date_Anfan') is None or a.get('Date_End_a') is None or f.get('geometry') is None:
            counts['no_interval'] += 1
            continue
        s, e = _local_day(a['Date_Anfan']), _local_day(a['Date_End_a'])
        if e < s or (e - s).days > 31:
            counts['interval_over_31_days'] += 1
            continue
        x, y = PROJECT.transform(f['geometry']['x'], f['geometry']['y'])
        rows.append((x, y, s, e))
        counts['used'] += 1
    return pd.DataFrame(rows, columns=['x', 'y', 'start', 'end']), counts


def nearby_intervals(records: pd.DataFrame, events: pd.DataFrame, radius_m: float) -> dict:
    """{event_group_id: [(start, end), ...]} for records within radius_m (EPSG:31287 metres)."""
    tree = cKDTree(records[['x', 'y']].to_numpy())
    hits = tree.query_ball_point(events[['x', 'y']].to_numpy(), radius_m)
    return {gid: [(records.start.iat[j], records.end.iat[j]) for j in idx] for gid, idx in zip(events.event_group_id, hits)}
