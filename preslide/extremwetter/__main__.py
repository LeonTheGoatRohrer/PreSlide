"""python -m preslide.extremwetter pilot N | run | report

pilot N : first N cohort events (first request chunk), prints data checks; writes nothing but the HTTP cache.
run     : all events; writes data/extremwetter_v01/run_<config sha12>/ and reports/extremwetter_v01/comparisons.json.
report  : figures, summary.md and the web bundle from the stored comparisons.
"""
import sys

import numpy as np

from ..v05.paths import sha
from . import analysis as A
from .data import cohort, dated_records, nearby_intervals, spartacus
from .paths import CONFIG, config


def prepare(limit=None):
    cfg = config()
    events = cohort(cfg)
    if limit is not None:
        # fetch whole request chunks so the pilot responses are the same cached URLs as the full run
        step = cfg['weather']['points_per_request']
        series = spartacus(events.iloc[:-(-limit // step) * step], cfg)
        events = events.iloc[:limit].reset_index(drop=True)
    else:
        series = spartacus(events, cfg)
    records, counts = dated_records(cfg)
    intervals = nearby_intervals(records, events, cfg['reference']['documented_event_exclusion']['radius_m'])
    return cfg, events, series, records, counts, intervals


def pilot(n):
    cfg, events, series, _, counts, intervals = prepare(n)
    m = A.build(events, series, intervals, cfg)
    primary = (cfg['exposure']['primary_window_days'], cfg['exposure']['window_end']['primary']['last_label_offset_days'])
    scores, _, _ = A.event_scores(m, primary, tuple(cfg['reference']['years']['primary']), cfg['reference']['minimum_reference_windows'])
    print('inventory records', counts)
    for i, row in enumerate(events.itertuples()):
        first, values, offset, lon, lat = series[row.event_group_id]
        print(f'{row.event_group_id} {row.event_day} {row.process_class:24s} {row.episode} offset={offset:.0f}m '
              f'series={first}+{len(values)}d nearby_records={len(intervals[row.event_group_id])} '
              f'inv_excluded={int(m.inventory_excluded[i].sum())} n_ref={scores["n_ref"][i]} '
              f'case3d={m.cases[primary][i]:.1f} ref3d_median={np.nanmedian(m.refs[primary][i][m.allowed[i]]):.1f} '
              f'PR={scores["pr"][i]:.3f}')


def run():
    from ..common import write_json
    from .paths import DATA, REPORT, V04_DATASET, guard
    cfg, events, series, _, counts, intervals = prepare()
    m = A.build(events, series, intervals, cfg)
    out = guard(DATA / f'run_{sha(CONFIG)[:12]}')
    rows, event_tables = [], {}
    for s in A.settings(cfg, events):
        row, scores = A.evaluate(m, events, s['combo'], s['years'], s['subset'], s['weighting'], cfg)
        rows.append({'setting': s['setting'], **row})
        event_tables[(s['combo'], s['years'])] = scores
        print(f"{s['setting']:32s} k={s['combo'][0]:2d} end={s['combo'][1]:3d} PR={row['mean_pr']:.3f} "
              f"[{row['mean_pr_ci95'][0]:.3f},{row['mean_pr_ci95'][1]:.3f}] p={row['p_one_sided']:.4f} "
              f"q95={row['share_q95']:.3f} n_ep={row['n_episodes']}")
    # Holm over the five primary windows
    prim = {r['window_days']: r['p_one_sided'] for r in rows if r['setting'] == 'primary'}
    adjusted = A.D.holm(prim)
    for r in rows:
        if r['setting'] == 'primary':
            r['p_holm_primary_windows'] = adjusted[r['window_days']]
    offsets = np.array([series[g][2] for g in events.event_group_id])
    meta = {
        'config_sha256': sha(CONFIG), 'v04_dataset_sha256': sha(V04_DATASET),
        'n_events': int(len(events)), 'n_episodes': int(events.episode.nunique()),
        'episode_sizes': events.episode.value_counts().to_dict(),
        'grid_offset_m': {'max': float(offsets.max()), 'median': float(np.median(offsets))},
        'distinct_grid_cells': int(len({(series[g][3], series[g][4]) for g in events.event_group_id})),
        'inventory_records': counts,
        'inventory_excluded_anchor_share_primary_years': float(
            m.inventory_excluded[:, (m.years >= 1991) & (m.years <= 2025)].mean()),
        'events_with_any_inventory_exclusion': int(m.inventory_excluded.any(axis=(1, 2)).sum()),
        'process_classes': events.process_class.value_counts().to_dict(),
        'stanz_events': int(events.stanz.sum()),
    }
    write_json(guard(REPORT) / 'comparisons.json', {'version': 'extremwetter_v01', 'exploratory': True, 'meta': meta, 'rows': rows})
    # local record-level checkpoint (gitignored data/): primary per-event scores for figures
    import pandas as pd
    from ..v05.pipeline import save
    primary = (cfg['exposure']['primary_window_days'], cfg['exposure']['window_end']['primary']['last_label_offset_days'])
    frame = events[['event_group_id', 'event_day', 'process_class', 'episode', 'stanz']].copy()
    for k in cfg['exposure']['windows_days']:
        for end in (-2, -1, 0):
            sc = event_tables[((k, end), tuple(cfg['reference']['years']['primary']))]
            frame[f'pr_{k}d_end{end}'] = sc['pr']
            frame[f'case_{k}d_end{end}'] = m.cases[(k, end)]
    frame['n_ref_primary'] = event_tables[(primary, tuple(cfg['reference']['years']['primary']))]['n_ref']
    frame['event_day'] = pd.to_datetime(frame.event_day)
    save(frame, out / 'event_scores.parquet', {'config_sha256': sha(CONFIG)})


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'pilot':
        pilot(int(sys.argv[2]))
    elif command == 'run':
        run()
    elif command == 'report':
        from .report import main
        main()
    else:
        raise SystemExit(__doc__)
