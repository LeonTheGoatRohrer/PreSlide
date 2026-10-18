"""Prüfgebiete-Übersicht: Klassen, Episoden- und Clustergrenzen, Zählungen.

Synthetische Frames sind nur Testfixtures; sie werden nie in data/ oder reports/ geschrieben.
"""
from datetime import date, timedelta

import pandas as pd
import pytest

from preslide.pruefgebiete.overview import build_overview, process_class, spatial_clusters, temporal_episodes


def positive_rows(specs):
    """specs: (group_id, day ISO, x_m, y_m, process_type). Latitude/longitude are placeholders."""
    rows = []
    for group_id, day, x, y, process in specs:
        rows.append({
            'event_group_id': group_id, 'label': 1, 'event_day': day, 'x': float(x), 'y': float(y),
            'latitude': 47.0, 'longitude': 15.0, 'process_type': process,
        })
    return pd.DataFrame(rows)


def test_process_labels_map_to_three_classes_and_unknown_fails():
    assert process_class('Hangmure') == 'Hangmure'
    assert process_class('Hangmure bis Lockergesteinsrutschung') == 'Hangmure gemischt'
    assert process_class('Hangmure und Lockergesteinsrutschung') == 'Hangmure gemischt'
    assert process_class('Lockergesteinsrutschung') == 'Lockergesteinsrutschung'
    with pytest.raises(ValueError):
        process_class('Steinschlag')


@pytest.mark.parametrize('gap_days, same_episode', [(0, True), (3, True), (4, False)])
def test_temporal_gap_boundary(gap_days, same_episode):
    start = date(2020, 8, 1)
    labels = temporal_episodes([start, start + timedelta(days=gap_days)])
    assert (labels[0] == labels[1]) is same_episode


@pytest.mark.parametrize('distance_m, same_cluster', [(4000, True), (5000, True), (6000, False)])
def test_spatial_cluster_boundary(distance_m, same_cluster):
    ids = spatial_clusters([0.0, float(distance_m)], [0.0, 0.0], cluster_km=5)
    assert (ids[0] == ids[1]) is same_cluster


def test_single_event_is_its_own_cluster():
    assert spatial_clusters([123.0], [456.0]) == [1]


def test_duplicate_positive_group_fails():
    frame = positive_rows([('A', '2020-08-01', 0, 0, 'Hangmure'), ('A', '2020-08-01', 10, 0, 'Hangmure')])
    with pytest.raises(ValueError):
        build_overview(frame, source_label='synthetic')


def test_missing_coordinate_fails():
    frame = positive_rows([('A', '2020-08-01', 0, 0, 'Hangmure')])
    frame.loc[0, 'x'] = float('nan')
    with pytest.raises(ValueError):
        build_overview(frame, source_label='synthetic')


def test_overview_counts_and_nesting_are_consistent():
    frame = positive_rows([
        ('A', '2020-08-01', 0, 0, 'Hangmure'),
        ('B', '2020-08-02', 1000, 0, 'Lockergesteinsrutschung'),
        ('C', '2020-08-02', 50000, 0, 'Hangmure bis Lockergesteinsrutschung'),
        ('D', '2021-05-01', 0, 0, 'Hangmure'),
    ])
    overview = build_overview(frame, source_label='synthetic')
    counts = overview['zaehlung']
    assert counts['positive_ereignisse'] == 4
    assert sum(c['n_positive'] for c in overview['cluster']) == 4
    assert sum(c['n_hangmure'] for c in overview['cluster']) == counts['hangmuren'] == 2
    points = {p['id']: p for p in overview['punkte']}
    assert len(points) == 4
    cluster_ids = {c['id'] for c in overview['cluster']}
    assert all(p['cluster'] in cluster_ids for p in points.values())
    assert points['A']['cluster'] == points['B']['cluster']  # 1 km apart, one day apart: same episode and cluster
    assert points['C']['cluster'] != points['B']['cluster']  # same episode, but 50 km apart
    assert points['D']['cluster'] != points['A']['cluster']  # same place, but a different episode
