"""Dependence check of spatio-temporal units and the frozen development/test partition (before any model).

python -m preslide.v04.partition
"""
import hashlib
import itertools
import json

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from .paths import V04_DATA, V04_REPORT, config as load_config, guard
from .pipeline import run_dir, load
from . import units

OUT = V04_DATA / 'partition'


def rain6h(positive_ids):
    frames = [load(p) for p in sorted((run_dir() / 'weather').glob('rain6h_*.parquet'))]
    f = pd.concat([x for x in frames if x is not None], ignore_index=True).drop_duplicates(['sample_id', 'timestamp'])
    return f[f.sample_id.isin(positive_ids)]


def dependence_check(events, series):
    """Correlation of unit-mean 6-hourly rain over the 14 days before the earlier unit t0, per unit pair in one episode."""
    events = events.assign(positive=events.event_group_id + '_positive')
    pivot = series.pivot_table(index='timestamp', columns='sample_id', values='rain_6h')
    rows = []
    for te, g in events.groupby('temporal_episode'):
        unit_ids = sorted(g.st_unit.unique())
        for a, b in itertools.combinations(unit_ids, 2):
            ga, gb = g[g.st_unit == a], g[g.st_unit == b]
            end = min(pd.Timestamp(ga.t0_utc.min()), pd.Timestamp(gb.t0_utc.min()))
            window = pivot[(pivot.index >= end - pd.Timedelta(days=14)) & (pivot.index + pd.Timedelta(hours=6) <= end)]
            sa = window[[c for c in ga.positive if c in window]].mean(axis=1)
            sb = window[[c for c in gb.positive if c in window]].mean(axis=1)
            ok = sa.notna() & sb.notna()
            r = float(np.corrcoef(sa[ok], sb[ok])[0, 1]) if ok.sum() >= 20 and sa[ok].std() > 0 and sb[ok].std() > 0 else np.nan
            rows.append({'temporal_episode': te, 'unit_a': a, 'unit_b': b, 'values': int(ok.sum()), 'pearson_r': r,
                         'distance_km': float(np.min(np.hypot(ga.x.to_numpy()[:, None] - gb.x.to_numpy()[None], ga.y.to_numpy()[:, None] - gb.y.to_numpy()[None])) / 1000)})
    return pd.DataFrame(rows)


def run(pilot=False):
    out_dir = OUT.with_name('partition_pilot') if pilot else OUT
    cfg = load_config()
    data = load(run_dir() / 'dataset.parquet')
    if data is None:
        raise RuntimeError('Assemble the dataset first')
    cand = pd.DataFrame(json.loads((V04_DATA / 'audit/candidates.json').read_text(encoding='utf-8')))
    cand = cand[cand.event_id.isin(set(data.event_group_id))].copy()
    cand['event_group_id'] = cand.event_id
    # Recompute units on the analysed events (excluded events cannot link anything).
    cand['temporal_episode'] = units.temporal_episodes([pd.Timestamp(d).date() for d in cand.event_day])
    cand['st_unit'] = units.spatiotemporal_units(cand, 50)
    check = dependence_check(cand, rain6h(set(cand.event_group_id + '_positive')))
    finite = check.pearson_r.dropna()
    p90 = float(np.quantile(finite, .9)) if len(finite) else None
    accept = p90 is not None and p90 < 0.5
    unit_col = 'st_unit' if accept else 'temporal_episode'
    index_of = {g: i for i, g in zip(cand.index, cand.event_group_id)}
    overlap = {(index_of[a], index_of[b]) for a, b in units.sample_pairs_between_groups(data, cfg['matching']['control_separation_m'])}
    cand['independence_unit'] = units.blocks(cand, unit_col, extra_pairs=overlap)
    cand['partition'] = units.partition(cand, 'independence_unit')
    # Spatial purge: a test group with any sample < 1 km from a development sample moves to development.
    moved = []
    while True:
        side = data.event_group_id.map(cand.set_index('event_group_id').partition)
        near = units.sample_pairs_between_groups(data, 1000)
        cross = {a if side[data.event_group_id == a].iloc[0] == 'sealed_test' else b
                 for a, b in near if cand.set_index('event_group_id').partition[a] != cand.set_index('event_group_id').partition[b]}
        if not cross:
            break
        blocks_to_move = set(cand.loc[cand.event_group_id.isin(cross), 'independence_unit'])
        moved += sorted(blocks_to_move)
        cand.loc[cand.independence_unit.isin(blocks_to_move), 'partition'] = 'development'
    units.check_partition(cand, 'independence_unit', 'partition')
    table = cand[['event_group_id', 'event_day', 'temporal_episode', 'st_unit', 'independence_unit', 'partition',
                  'in_v03_baseline_candidates', 'state', 'time_quality']].sort_values('event_group_id')
    guard(out_dir)
    text = table.to_json(orient='records', indent=1, force_ascii=False)
    target = out_dir / 'partition.json'
    if target.exists() and target.read_text(encoding='utf-8') != text:
        raise RuntimeError('partition.json is frozen and differs from the recomputed partition')
    target.write_text(text, encoding='utf-8')
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    check.to_csv(out_dir / 'dependence_check.csv', index=False)
    summary = {'dependence_check': {'pairs': int(len(check)), 'finite_pairs': int(len(finite)), 'p90_pearson_r': p90,
                                    'median_pearson_r': float(finite.median()) if len(finite) else None,
                                    'threshold': 0.5, 'spatiotemporal_units_accepted': bool(accept)},
               'independence_unit_definition': unit_col + ' + location links (positives < 2 km, samples < 400 m)',
               'units': int(table.independence_unit.nunique()), 'moved_to_development_by_1km_purge': moved,
               'partition': {p: {'events': int(len(g)), 'units': int(g.independence_unit.nunique()),
                                 'temporal_episodes': int(g.temporal_episode.nunique()),
                                 'baseline_events': int(g.in_v03_baseline_candidates.sum())} for p, g in table.groupby('partition')},
               'partition_sha256': digest, 'dataset_sha256': read_json((run_dir() / 'dataset.parquet').with_suffix('.json'))['sha256']}
    write_json(out_dir / 'partition_summary.json', summary)
    if not pilot:
        write_json(V04_REPORT / 'partition_summary.json', summary)
    print(json.dumps(summary, indent=1))
    return table, summary


if __name__ == '__main__':
    import sys
    run(pilot='--pilot' in sys.argv)
