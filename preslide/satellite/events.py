"""Read-only access to the V0.4 positives, their matched controls and independence units (Pipeline A artefacts)."""
import json

import pandas as pd

from ..sources import ROOT
from .paths import config

EVENT_COLUMNS = ['event_group_id', 'event_day', 't0_utc', 'time_quality', 'state', 'source_position_upper_m',
                 'process_type', 'sample_id', 'label', 'sample_type', 'longitude', 'latitude', 'elevation', 'slope', 'aspect',
                 'distance_to_positive_m', 'land_cover_class', 'inventory_clear']


def load_samples():
    """All V0.4 samples (positives + controls) with their independence unit and partition."""
    cfg = config()['source']
    data = pd.read_parquet(ROOT / cfg['events'].split(' ')[0])[EVENT_COLUMNS]
    part = pd.DataFrame(json.loads((ROOT / cfg['partition'].split(' ')[0]).read_text(encoding='utf-8')))
    data = data.merge(part[['event_group_id', 'independence_unit', 'temporal_episode', 'partition']], on='event_group_id', how='left')
    if data['independence_unit'].isna().any():
        raise RuntimeError('V0.4 partition does not cover every event group')
    return data


def positives(samples=None):
    s = load_samples() if samples is None else samples
    return s[s['label'] == 1].sort_values('event_day').reset_index(drop=True)


def controls_of(samples, event_group_id):
    return samples[(samples['event_group_id'] == event_group_id) & (samples['label'] == 0)].reset_index(drop=True)


def representative_order(pos):
    """Spread the first events over different independence units, years and states so small pilots are diverse."""
    seen, first, rest = set(), [], []
    for _, row in pos.sort_values(['event_day']).iterrows():
        key = row['independence_unit']
        (rest if key in seen else first).append(row)
        seen.add(key)
    return pd.DataFrame(first + rest).reset_index(drop=True)
