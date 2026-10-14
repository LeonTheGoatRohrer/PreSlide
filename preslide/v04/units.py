"""Independence units, dependence blocks and the development/test rule (config/v04.json: episodes, partition)."""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


class Union:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def temporal_episodes(days):
    """Single linkage over local event days with gap <= 3 days; label = episode start day."""
    label, current, previous, start = {}, 0, None, None
    for d in sorted(set(days)):
        if previous is None or (d - previous).days > 3:
            current, start = current + 1, d
        label[d] = f'TE{current:03d}_{start.isoformat()}'
        previous = d
    return [label[d] for d in days]


def spatiotemporal_units(events, km=50):
    """Within each temporal episode, single linkage of positives at <= km (metric EPSG:31287 x/y)."""
    out = pd.Series(index=events.index, dtype=object)
    for te, g in events.groupby('temporal_episode'):
        u = Union(list(g.index))
        for a, b in cKDTree(g[['x', 'y']].to_numpy()).query_pairs(km * 1000):
            u.union(g.index[a], g.index[b])
        roots = sorted({u.find(i) for i in g.index})
        for i in g.index:
            out[i] = f'{te}_S{roots.index(u.find(i)) + 1:02d}'
    return out


def blocks(events, unit_column, positive_link_m=2000, extra_pairs=()):
    """Union of independence units, positives < positive_link_m on any date and extra (index, index) pairs."""
    u = Union(list(events.index))
    for _, g in events.groupby(unit_column):
        for i in g.index[1:]:
            u.union(g.index[0], i)
    xy = events[['x', 'y']].to_numpy()
    for a, b in cKDTree(xy).query_pairs(positive_link_m):
        u.union(events.index[a], events.index[b])
    for a, b in extra_pairs:
        u.union(a, b)
    root = pd.Series({i: u.find(i) for i in events.index})
    first = events.groupby(root).event_day.min()
    anchor = events.groupby(root).event_id.min()
    return root.map(lambda r: f'B_{first[r]}_{anchor[r]}')


def partition(events, block_column):
    """Blocks containing a V0.3 baseline candidate -> development; all baseline-free blocks -> sealed test."""
    has_base = events.groupby(block_column).in_v03_baseline_candidates.any()
    side = events[block_column].map(lambda b: 'development' if has_base[b] else 'sealed_test')
    check_partition(events.assign(_p=side), block_column, '_p')
    return side


def check_partition(frame, block_column, partition_column):
    if frame.groupby(block_column)[partition_column].nunique().max() != 1:
        raise ValueError(f'{block_column} crosses partitions')


def sample_pairs_between_groups(samples, distance_m, positive_involved=False):
    """Group-id pairs with any samples of different groups closer than distance_m.

    positive_involved=True (V0.4 amendment 1) keeps only pairs in which at least one of the two samples is a
    positive: control-control overlaps carry identical labels and therefore no label leakage."""
    xy = samples[['x', 'y']].to_numpy()
    groups = samples.event_group_id.to_numpy()
    labels = samples.label.to_numpy() if positive_involved else None
    pairs = set()
    for a, b in cKDTree(xy).query_pairs(distance_m):
        if groups[a] != groups[b] and (not positive_involved or labels[a] == 1 or labels[b] == 1):
            pairs.add(tuple(sorted((groups[a], groups[b]))))
    return pairs


def unit_weights(groups_to_units):
    """1/sqrt(n) per group with n = number of groups in its unit (training weights)."""
    counts = groups_to_units.value_counts()
    return groups_to_units.map(lambda u: 1 / np.sqrt(counts[u]))
