"""V0.5 cohort, outer CV folds over the V0.4 independence units, fold-level spatial purge and proximity audit.

  python -m preslide.v05.partition proximity   # after control freeze, before features: all frozen selections
  python -m preslide.v05.partition freeze      # after assemble, before any model: cohort + CV plan (write-once)
"""
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..common import read_json, write_json
from ..sources import ROOT
from .paths import V05_DATA, V05_REPORT, V04_PARTITION, CONFIG, config as load_config, guard, sha
from . import pipeline as P

CV_DIR = V05_DATA / 'cv'


def v04_units():
    part = pd.DataFrame(json.loads(V04_PARTITION.read_text(encoding='utf-8')))
    return part.set_index('event_group_id')


def folds(unit_ids, seed, k):
    ids = np.array(sorted(set(unit_ids)))
    return [sorted(f.tolist()) for f in np.array_split(np.random.default_rng(seed).permutation(ids), k)]


def purge(samples, held_units, distance_m):
    """Training units with any sample (any class) closer than distance_m to any held-out sample.

    samples: frame with x, y, independence_unit (all samples that define proximity)."""
    held = samples[samples.independence_unit.isin(held_units)]
    train = samples[~samples.independence_unit.isin(held_units)]
    tree = cKDTree(held[['x', 'y']].to_numpy())
    d, _ = tree.query(train[['x', 'y']].to_numpy(), k=1)
    near = train[d < distance_m]
    remaining = train[~train.independence_unit.isin(set(near.independence_unit))]
    min_remaining = float(tree.query(remaining[['x', 'y']].to_numpy(), k=1)[0].min()) if len(remaining) else None
    return sorted(set(near.independence_unit)), min_remaining


def cv_plan(samples, cfg, distance_m=None):
    """Folds for every repetition plus the purge for every fold; samples carry independence_unit and label."""
    cv = cfg['cross_validation']
    distance_m = distance_m or 1000
    groups = samples.drop_duplicates('event_group_id')[['event_group_id', 'independence_unit']]
    plan, feasible = [], True
    for rep, seed in enumerate(cv['repetitions_seeds'], 1):
        for fold, held in enumerate(folds(groups.independence_unit, seed, cv['folds']), 1):
            purged, min_remaining = purge(samples, held, distance_m)
            train_units = sorted(set(groups.independence_unit) - set(held) - set(purged))
            train_groups = groups[groups.independence_unit.isin(train_units)]
            ok = len(train_units) >= 5 and len(train_groups) >= 20
            feasible &= ok
            plan.append({'repetition': rep, 'seed': seed, 'fold': fold, 'held_units': held,
                         'held_groups': int(groups.independence_unit.isin(held).sum()),
                         'purged_units': purged, 'purged_groups': int(groups.independence_unit.isin(purged).sum()),
                         'train_units': train_units, 'train_groups': int(len(train_groups)),
                         'unpurged_train_groups': int((~groups.independence_unit.isin(held)).sum()),
                         'min_train_to_held_distance_m': min_remaining, 'feasible': ok})
    return plan, bool(feasible)


def pair_counts(samples, distance_m):
    """Cross-group sample pairs closer than distance_m by type, and how many cross independence units."""
    xy = samples[['x', 'y']].to_numpy()
    g, u, lab = samples.event_group_id.to_numpy(), samples.independence_unit.to_numpy(), samples.label.to_numpy()
    out = {t: {'pairs': 0, 'cross_unit_pairs': 0} for t in ('positive_positive', 'positive_control', 'control_control')}
    for a, b in cKDTree(xy).query_pairs(distance_m):
        if g[a] == g[b]:
            continue
        t = ['control_control', 'positive_control', 'positive_positive'][lab[a] + lab[b]]
        out[t]['pairs'] += 1
        out[t]['cross_unit_pairs'] += int(u[a] != u[b])
    return out


def frozen_selection():
    rows = [s for _, s in P.frozen_samples(0)]
    data = pd.concat(rows, ignore_index=True)
    return data.assign(independence_unit=data.event_group_id.map(v04_units().independence_unit))


def proximity():
    """Control/proximity audit of all frozen selections and CV feasibility (no features, no models)."""
    cfg = load_config()
    data = frozen_selection()
    status = P.read_status()
    excluded = {e: s['select'].get('reason') for e, s in status.items() if s.get('select', {}).get('state') == 'excluded'}
    plan, feasible = cv_plan(data, cfg)
    ctrl = data[data.label == 0]
    summary = {'selected_groups': int(data.event_group_id.nunique()), 'excluded_at_selection': excluded,
               'units': int(data.independence_unit.nunique()),
               'pairs_lt_1000m': pair_counts(data, 1000), 'pairs_lt_400m': pair_counts(data, 400),
               'control_distance_bins': {b: int(n) for b, n in pd.cut(ctrl.distance_to_positive_m, [750, 2000, 5000, 10000],
                                                                      labels=['0.75-2km', '2-5km', '5-10km'], include_lowest=True).value_counts().sort_index().items()},
               'cv_feasible_on_full_selection': feasible,
               'cv_folds': [{k: v for k, v in f.items() if k not in ('held_units', 'train_units', 'purged_units')} |
                            {'held_units': len(f['held_units']), 'purged_units': len(f['purged_units']), 'train_units': len(f['train_units'])}
                            for f in plan],
               'note': 'Feasibility on all frozen selections before environmental exclusions; the binding CV plan is frozen after assembly.'}
    write_json(guard(V05_REPORT) / 'proximity_audit.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'cv_folds'}, indent=1))
    print('min train groups per fold:', min(f['train_groups'] for f in plan), 'min train units:', min(len(f['train_units']) for f in plan))
    return summary


def freeze():
    """Write-once cohort and CV plan on the assembled dataset (before any model)."""
    target = CV_DIR / 'cv_plan.json'
    if target.exists():
        sys.exit(f'{target} exists (write-once)')
    cfg = load_config()
    dataset = P.run_dir() / 'dataset.parquet'
    data = P.load(dataset)
    data = data.assign(independence_unit=data.event_group_id.map(v04_units().independence_unit))
    if data.independence_unit.isna().any():
        raise RuntimeError('Group without V0.4 independence unit')
    plan, feasible = cv_plan(data, cfg)
    # Control-variant diagnostic: purge on the union of V0.4 matched controls and V0.5 unmatched controls.
    v04 = P.v04_dataset()
    v04 = v04[v04.event_group_id.isin(set(data.event_group_id))]
    union = pd.concat([data[['event_group_id', 'x', 'y', 'label']], v04.loc[v04.label == 0, ['event_group_id', 'x', 'y', 'label']]])
    union = union.assign(independence_unit=union.event_group_id.map(v04_units().independence_unit))
    union_plan, union_feasible = cv_plan(union, cfg)
    guard(CV_DIR)
    write_json(target, {'primary': plan, 'control_variants_union': [f for f in union_plan if f['repetition'] == 1]})
    status = P.read_status()
    record = {'frozen_at': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha(CONFIG),
              'dataset_sha256': sha(dataset), 'cv_plan_sha256': sha(target),
              'cohort': {'events': int(data.event_group_id.nunique()), 'units': int(data.independence_unit.nunique()),
                         'samples': int(len(data))},
              'exclusions': {e: {k: v for k, v in s.items() if v['state'] != 'complete'} for e, s in status.items()
                             if any(v['state'] != 'complete' for v in s.values())},
              'cv_feasible': feasible, 'control_variant_purge_feasible': union_feasible,
              'code_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / 'preslide/v05').glob('*.py'))},
              'statement': 'Cohort, exclusions and outer CV/purge mappings are fixed before any V0.5 model is fit.'}
    write_json(guard(V05_REPORT) / 'COHORT_FREEZE.json', record)
    print(json.dumps({k: v for k, v in record.items() if k not in ('code_sha256', 'exclusions')}, indent=1))
    print('excluded groups:', len(record['exclusions']), 'min purged train groups:', min(f['train_groups'] for f in plan))
    if not feasible:
        print('WARNING: the registered purged CV is not fully feasible; report it as such (no substitute rule).')
    return record


if __name__ == '__main__':
    {'proximity': proximity, 'freeze': freeze}[sys.argv[1]]()
