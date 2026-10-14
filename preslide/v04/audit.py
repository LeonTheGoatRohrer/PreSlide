"""V0.4 audit: candidate snapshot, recorded exclusions, episodes and the pre-modelling partition.

Run: python -m preslide.v04.audit   (reads only the local raw snapshot; writes data/v04/ and reports/v04/)
"""
import hashlib
import json
from collections import Counter

import pandas as pd

from ..audit import load_inventory, plausible_coordinates, position_bounds, position_passes
from ..common import read_json, write_json
from ..sources import ROOT, LAYERS
from ..terrain import PROJECT
from .dates import classify_date
from .paths import CONFIG, V04_DATA, V04_REPORT, guard
from .units import temporal_episodes, spatiotemporal_units, blocks, partition

BASELINE_CANDIDATES = ROOT / 'data/interim/quality_candidates_pending_source_clearance.json'


def screen(feature, inc):
    """Non-date criteria. Returns (tier, failures); tier 1 = V0 quality fields, tier 2 = media without quality."""
    a = feature['attributes']
    day = a.get('Ereignisdatum_validFrom') or ''
    checks = {
        'accepted_process': a.get('Prozessgruppe') in inc['process_groups'] and a.get('Prozessuntergruppe') in inc['process_subgroups'],
        'in_period': isinstance(day, str) and inc['period'][0] <= day[:10] <= inc['period'][1],
        'coordinates_plausible': plausible_coordinates(feature.get('geometry')),
        'position_quality': position_passes(a.get('QUAL_LAGE'), inc['max_position_upper_bound_m']),
    }
    tier1 = a.get('QUAL_PROZ') in inc['process_quality'] and a.get('QUAL_MB') in inc['mass_movement_quality']
    tier2 = a.get('QUAL_PROZ') == 'keine Information' and a.get('QUAL_MB') == 'keine Information'
    failures = [k for k, v in checks.items() if not v]
    if not (tier1 or tier2):
        failures.append('process_or_mass_movement_quality')
    return (1 if tier1 else 2 if tier2 else None), failures


def config_km(config):
    return int(config['episodes']['spatiotemporal_unit'].split('<= ')[1].split(' km')[0])


def run():
    config = read_json(CONFIG)
    inc = config['inclusion']
    features, source_sha = load_inventory('geosphere_natural_hazards')
    baseline = {r['event_id']: r for r in read_json(BASELINE_CANDIDATES)}
    records, exclusions = [], []
    reasons = Counter()
    for f in features:
        a = f['attributes']
        if a.get('Prozessgruppe') not in inc['process_groups']:
            continue                                   # other processes are out of scope, not 'excluded events'
        tier, failures = screen(f, inc)
        date = classify_date(a)
        base = {'event_id': a['nameOfEvent'], 'object_id': a['OBJECTID'], 'quality_tier': tier,
                'date_text_original': a.get('processTimeOrPeriodInfo'), **date}
        if failures:
            exclusions.append({**base, 'stage': 'audit', 'reason': failures[0], 'all_failures': failures})
            reasons[failures[0]] += 1
            continue
        g = f['geometry']
        x, y = PROJECT.transform(g['x'], g['y'])
        base.update(longitude=g['x'], latitude=g['y'], x=x, y=y, state=a.get('Bundesland'),
                    process_type_original=a['Prozessuntergruppe'], process_group_original=a['Prozessgruppe'],
                    position_accuracy_original=a['QUAL_LAGE'], position_accuracy_upper_m=position_bounds(a['QUAL_LAGE'])[1],
                    process_quality_original=a.get('QUAL_PROZ'), survey_method=(a.get('ERHEB_MET_agg') or '').strip(),
                    in_v03_baseline_candidates=a['nameOfEvent'] in baseline and baseline[a['nameOfEvent']]['original_source_id'] == a['OBJECTID'],
                    source='GeoSphere Austria / Naturgefahren (Test)', source_url=LAYERS['geosphere_natural_hazards'])
        records.append(base)
    frame = pd.DataFrame(records)
    tier_counts = frame.groupby(['quality_tier', 'date_tier']).size().rename('events').reset_index().to_dict('records')
    is_main = (frame.quality_tier == 1) & (frame.date_tier == config['dates']['primary_tier'].split(':')[0])
    for r in frame[~is_main].to_dict('records'):
        why = 'tier2_media_not_in_main_analysis' if r['quality_tier'] == 2 else (
              'secondary_date_tier_not_in_main_analysis' if r['date_tier'] != 'excluded' else r['date_reason'])
        exclusions.append({**r, 'stage': 'audit', 'reason': why})
    main = frame[is_main].copy()
    # Exact coordinate/day duplicates cannot be independent positives (V0 rule); keep the first source record.
    dup = main.duplicated(['longitude', 'latitude', 'event_day'])
    for r in main[dup].to_dict('records'):
        exclusions.append({**r, 'stage': 'audit', 'reason': 'exact_location_day_duplicate'})
    main = main[~dup].copy()
    if main.event_id.duplicated().any():
        raise ValueError('Duplicate event_id in main candidate set')
    main['t0_utc'] = pd.to_datetime(main.t0_local, utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    main = main.sort_values(['event_day', 'event_id']).reset_index(drop=True)
    days = [pd.Timestamp(d).date() for d in main.event_day]
    main['temporal_episode'] = temporal_episodes(days)
    main['st_unit'] = spatiotemporal_units(main, config_km(config))
    # Provisional blocks for both unit definitions; the dependence check (after INCA) selects one.
    for kind, column in (('te', 'temporal_episode'), ('st', 'st_unit')):
        main[f'block_{kind}'] = blocks(main, column)
        main[f'provisional_partition_{kind}'] = partition(main, f'block_{kind}')
    missing_base = set(b for b, r in baseline.items()) - set(main.event_id)
    if missing_base:
        raise ValueError(f'Baseline candidates not reproduced by V0.4 rules: {sorted(missing_base)[:5]}')
    out = V04_DATA / 'audit'
    guard(out)
    main.to_json(out / 'candidates.json', orient='records', force_ascii=False, indent=1)
    write_json(out / 'audit_exclusions.json', [{k: (None if isinstance(v, float) and v != v else v) for k, v in e.items()} for e in exclusions])
    summary = {
        'source_sha256': source_sha, 'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        'records_in_process_groups': int(len(records) + sum(1 for e in exclusions if e['stage'] == 'audit' and e['reason'] in
                                         ('accepted_process', 'in_period', 'coordinates_plausible', 'position_quality', 'process_or_mass_movement_quality'))),
        'audit_exclusion_first_reason': dict(reasons),
        'eligible_by_quality_and_date_tier': tier_counts,
        'main_candidates': int(len(main)), 'main_distinct_days': int(main.event_day.nunique()),
        'main_temporal_episodes': int(main.temporal_episode.nunique()), 'main_spatiotemporal_units': int(main.st_unit.nunique()),
        'main_time_quality': main.time_quality.value_counts().to_dict(),
        'main_by_year': main.event_day.str[:4].value_counts().sort_index().to_dict(),
        'main_by_state': main.state.value_counts().to_dict(),
        'largest_temporal_episodes': main.temporal_episode.value_counts().head(8).to_dict(),
        'baseline_candidates_reproduced': int(main.in_v03_baseline_candidates.sum()),
        'provisional': {kind: {'blocks': int(main[f'block_{kind}'].nunique()),
                               'events': main[f'provisional_partition_{kind}'].value_counts().to_dict(),
                               'blocks_by_partition': main.groupby(f'provisional_partition_{kind}')[f'block_{kind}'].nunique().to_dict()}
                        for kind in ('te', 'st')},
    }
    write_json(V04_REPORT / 'audit_summary.json', summary)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return main, summary


if __name__ == '__main__':
    run()
