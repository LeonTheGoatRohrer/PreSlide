"""Read-only Ereignisübersicht für die Prüfgebiete-Seite.

Keine Modellierung und keine Wahrscheinlichkeiten. Die Übersicht zeigt, wo die vorhandenen
Hangmuren und Rutschungen des V0.4-Datensatzes liegen und wie viele davon zu einem zeitlichen
Ereignis (Episode) bzw. einem räumlichen Cluster gehören. Clusterung nutzt die bereits
verwendeten Primitive aus `preslide.v04.units` (Tagesabstand <= 3 Tage, Einzelverkettung).
Die Ausgabe liegt lokal unter data/pruefgebiete_v01/web/ und ist kein Analyseergebnis.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..common import write_json
from ..v04.units import Union, temporal_episodes

CLUSTER_KM = 5
PROCESS_CLASS = {
    'Hangmure': 'Hangmure',
    'Hangmure bis Lockergesteinsrutschung': 'Hangmure gemischt',
    'Hangmure und Lockergesteinsrutschung': 'Hangmure gemischt',
    'Lockergesteinsrutschung': 'Lockergesteinsrutschung',
}
CAVEATS = [
    'Die Punkte sind dokumentierte Ereignisstellen mit Positionsunsicherheit, keine Anrisspolygone.',
    'Ein Cluster oder eine Episode ist nicht automatisch ein unabhängiges Ereignis; mehrere Hänge können zu einem Sturm gehören.',
    'Die Dichte zeigt Meldungen, nicht die tatsächliche Verteilung von Muren; Meldebias ist möglich.',
    'Keine Gefährdungswahrscheinlichkeit und keine Auslaufaussage in dieser Übersicht.',
]


def process_class(text):
    """Map a raw GeoSphere process label to the three analysis classes; unknown labels fail loudly."""
    try:
        return PROCESS_CLASS[str(text)]
    except KeyError as error:
        raise ValueError(f'Unbekannte Prozessbezeichnung: {text!r}') from error


def spatial_clusters(x_m, y_m, cluster_km=CLUSTER_KM):
    """Single-linkage clusters on projected metre coordinates (EPSG:31287 x/y), returned as 1-based ids."""
    n = len(x_m)
    union = Union(list(range(n)))
    if n > 1:
        points = np.column_stack([x_m, y_m])
        for a, b in cKDTree(points).query_pairs(cluster_km * 1000):
            union.union(a, b)
    roots = {}
    return [roots.setdefault(union.find(i), len(roots) + 1) for i in range(n)]


def positives(dataset):
    """One row per positive event group; fails if a group appears twice or a required field is missing."""
    rows = dataset[dataset['label'] == 1].copy()
    if rows['event_group_id'].duplicated().any():
        raise ValueError('Positive Ereignisgruppe kommt mehrfach vor')
    for column in ('event_day', 'x', 'y', 'latitude', 'longitude', 'process_type'):
        if rows[column].isna().any():
            raise ValueError(f'Fehlende Angabe in Spalte {column} bei positiven Ereignissen')
    rows['event_day'] = pd.to_datetime(rows['event_day']).dt.date
    rows['process_class'] = rows['process_type'].map(process_class)
    return rows.reset_index(drop=True)


def build_overview(dataset, source_label):
    """Return the JSON-ready overview for a dataset with one row per sample."""
    events = positives(dataset)
    episode = temporal_episodes(list(events['event_day']))
    events['episode'] = episode
    events['cluster'] = ''
    for name, group in events.groupby('episode', sort=False):
        ids = spatial_clusters(group['x'].to_numpy(), group['y'].to_numpy())
        events.loc[group.index, 'cluster'] = [f'{name}_C{i:02d}' for i in ids]
    clusters = []
    for name, group in events.groupby('cluster', sort=True):
        clusters.append({
            'id': name,
            'episode': group['episode'].iloc[0],
            'n_positive': int(len(group)),
            'n_hangmure': int((group['process_class'] == 'Hangmure').sum()),
            'first_day': min(group['event_day']).isoformat(),
            'last_day': max(group['event_day']).isoformat(),
            'lat': round(float(group['latitude'].mean()), 5),
            'lon': round(float(group['longitude'].mean()), 5),
        })
    clusters.sort(key=lambda c: (-c['n_positive'], c['id']))
    episodes = events.groupby('episode').size().sort_values(ascending=False)
    years = events.assign(year=[d.year for d in events['event_day']]).groupby(['year', 'process_class']).size()
    return {
        'version': 'pruefgebiete_v01',
        'quelle': source_label,
        'zaehlung': {
            'positive_ereignisse': int(len(events)),
            'episoden': int(episodes.size),
            'cluster': int(len(clusters)),
            'hangmuren': int((events['process_class'] == 'Hangmure').sum()),
        },
        'prozessklassen': {k: int(v) for k, v in events['process_class'].value_counts().items()},
        'jahre': [
            {'jahr': int(year), 'klasse': klasse, 'n': int(n)}
            for (year, klasse), n in years.items()
        ],
        'cluster': clusters[:25],
        'punkte': [
            {
                'id': r.event_group_id,
                'lat': round(float(r.latitude), 5),
                'lon': round(float(r.longitude), 5),
                'tag': r.event_day.isoformat(),
                'klasse': r.process_class,
                'cluster': r.cluster,
            }
            for r in events.itertuples()
        ],
        'hinweise': CAVEATS,
    }


def write_overview(dataset_path, out_path):
    """Read the frozen V0.4 dataset read-only and write the local overview bundle."""
    dataset_path = Path(dataset_path)
    dataset = pd.read_parquet(dataset_path)
    overview = build_overview(dataset, source_label=dataset_path.as_posix())
    write_json(out_path, overview)
    return overview
