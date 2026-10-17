"""V0.9 models, independence units, freeze and the single scoring.

  python -m preslide.v09.experiment refit       # V0.4 recipe on all 423 V0.4 groups (before any V0.9 feature table)
  python -m preslide.v09.experiment partition   # seen-location purge + independence units (no labels or scores used)
  python -m preslide.v09.experiment freeze      # hashes of everything that determines the score
  python -m preslide.v09.experiment score       # exactly once; refuses to run twice
"""
import json
import sys
from datetime import datetime, timezone

import joblib
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from ..v04 import models as M
from ..v04 import units
from ..v04.experiment import columns, train_weights
from ..v04.pipeline import load
from .paths import CONFIG, REGISTRATION, V09_DATA, V09_MODELS, V09_REPORT, config as load_config, guard, sha

V04_DATASET = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'
V04_PARTITION = ROOT / 'data/v04/partition/partition.json'
REFIT_DIR = V09_MODELS / 'refit_all'
UNITS = V09_DATA / 'partition/units.json'
FREEZE = V09_REPORT / 'FREEZE.json'
RESULT = V09_REPORT / 'test_results.json'
COHORTS = ('media', 'media_slide_confirmed', 'kaernten', 'pooled')


def v04_config():
    return read_json(ROOT / 'config/v04.json')        # parsed content; byte hash differs between checkouts (line ends)


def admitted(cfg):
    listed = cfg['features']['admitted_daily_features']
    if listed != read_json(ROOT / 'reports/v04/admission.json')['admitted_features']:
        raise RuntimeError('Registered admitted features differ from the V0.4 admission')
    return listed


def with_derived(data):
    data = M.add_one_hot(data)
    inter = M.interaction_columns(data)
    return pd.concat([data, inter], axis=1), list(inter.columns)


def v04_training_table():
    data = load(V04_DATASET)
    if data is None:
        raise RuntimeError('V0.4 dataset missing')
    part = pd.DataFrame(read_json(V04_PARTITION))[['event_group_id', 'independence_unit']]
    data = data.merge(part, on='event_group_id', how='inner', validate='many_to_one')
    if data.event_group_id.nunique() != 423:
        raise RuntimeError('Expected the 423 V0.4 groups')
    return with_derived(data)


# ---------- refit ----------

def refit():
    cfg = load_config()
    out = guard(REFIT_DIR)
    if (out / 'manifest.json').exists():
        sys.exit('refit_all models exist; they are fitted once.')
    data, inter = v04_training_table()
    w = train_weights(data)
    saved = {}
    for model in M.MODELS:
        for variant in M.VARIANTS:
            cols = columns(variant, model, inter, admitted(cfg))
            _, bundle = M.fit_predict(model, data, data.head(6), cols, w, v04_config()['models'])
            path = out / f'{model}_{variant}.joblib'
            joblib.dump({**bundle, 'columns': cols, 'training_groups': sorted(data.event_group_id.unique())}, path)
            saved[path.relative_to(ROOT).as_posix()] = sha(path)
    write_json(out / 'manifest.json', {'fitted_at': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha(CONFIG),
                                       'training': {'groups': int(data.event_group_id.nunique()), 'samples': int(len(data)),
                                                    'units': int(data.independence_unit.nunique())},
                                       'v04_dataset_sha256': sha(V04_DATASET), 'models': saved})
    print(json.dumps(saved, indent=1))


# ---------- independence units ----------

def seen_location_groups(v09, v04, distance_m):
    """V0.9 groups with a positive-involving sample pair < distance_m to any V0.4 sample."""
    if set(v09.event_group_id) & set(v04.event_group_id):
        raise ValueError('V0.9 and V0.4 group ids overlap')
    cols = ['event_group_id', 'x', 'y', 'label']
    both = pd.concat([v09[cols], v04[cols]], ignore_index=True)
    mine = set(v09.event_group_id)
    pairs = units.sample_pairs_between_groups(both, distance_m, positive_involved=True)
    return {a if a in mine else b for a, b in pairs if (a in mine) != (b in mine)}


def unit_table(samples, positive_link_m, link_m):
    """Temporal episode + positives < positive_link_m + positive-involving sample pairs < link_m (V0.4 amendment 1)."""
    pos = samples[samples.label == 1][['event_group_id', 'event_day', 'x', 'y']].copy()
    pos = pos.rename(columns={'event_group_id': 'event_id'}).reset_index(drop=True)
    pos['temporal_episode'] = units.temporal_episodes([pd.Timestamp(d).date() for d in pos.event_day])
    index_of = {g: i for i, g in enumerate(pos.event_id)}
    overlap = {(index_of[a], index_of[b]) for a, b in units.sample_pairs_between_groups(samples, link_m, positive_involved=True)}
    pos['unit'] = units.blocks(pos, 'temporal_episode', positive_link_m=positive_link_m, extra_pairs=overlap)
    return pos.set_index('event_id')[['temporal_episode', 'unit']]


def run_dir():
    return V09_DATA / f'run_{sha(CONFIG)[:12]}'


def partition():
    cfg = load_config()
    p = cfg['partition']
    data = load(run_dir() / 'dataset.parquet')
    if data is None:
        raise RuntimeError('Assemble the full V0.9 dataset first')
    v04 = load(V04_DATASET)
    purged = seen_location_groups(data, v04, p['spatial_purge_m'])
    kept = data[~data.event_group_id.isin(purged)]
    rows = []
    sep = cfg['matching']['control_separation_m']
    for cohort in ('media', 'kaernten'):
        part = kept[kept.cohort == cohort]
        if len(part):
            rows.append(unit_table(part, p['positive_link_m'], sep).add_prefix('cohort_').assign(cohort=cohort))
    table = pd.concat(rows)
    pooled = unit_table(kept, p['positive_link_m'], sep).add_prefix('pooled_')
    table = table.join(pooled).reset_index(names='event_group_id').sort_values('event_group_id')
    target = guard(UNITS.parent) / UNITS.name
    text = table.to_json(orient='records', indent=1, force_ascii=False)
    if target.exists() and target.read_text(encoding='utf-8') != text:
        raise RuntimeError('units.json is frozen and differs from the recomputed table')
    target.write_text(text, encoding='utf-8')
    summary = {'purged_seen_location': sorted(purged), 'groups': int(len(table)),
               'by_cohort': {c: {'groups': int(len(g)), 'units': int(g.cohort_unit.nunique()),
                                 'temporal_episodes': int(g.cohort_temporal_episode.nunique())} for c, g in table.groupby('cohort')},
               'pooled_units': int(table.pooled_unit.nunique()), 'units_sha256': sha(target)}
    write_json(V09_REPORT / 'partition_summary.json', summary)
    print(json.dumps(summary, indent=1))


# ---------- freeze and score ----------

def code_hashes():
    files = sorted((ROOT / 'preslide/v09').glob('*.py')) + sorted((ROOT / 'preslide/v04').glob('*.py'))
    return {f.relative_to(ROOT).as_posix(): sha(f) for f in files}


def freeze():
    if FREEZE.exists():
        sys.exit('FREEZE.json exists; V0.9 is already frozen.')
    cfg = load_config()
    for rel, h in cfg['frozen_v04_models'].items():
        if sha(ROOT / rel) != h:
            raise RuntimeError(f'Frozen V0.4 model changed: {rel}')
    manifest = read_json(REFIT_DIR / 'manifest.json')
    for rel, h in manifest['models'].items():
        if sha(ROOT / rel) != h:
            raise RuntimeError(f'Refit model changed: {rel}')
    record = {'frozen_at': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha(CONFIG),
              'registration_sha256': sha(REGISTRATION), 'dataset_sha256': sha(run_dir() / 'dataset.parquet'),
              'units_sha256': sha(UNITS), 'process_audit_sha256': sha(V09_DATA / 'audit/process_audit.json'),
              'candidates_sha256': sha(V09_DATA / 'audit/candidates.json'), 'refit_models': manifest['models'],
              'frozen_v04_models': cfg['frozen_v04_models'], 'code_sha256': code_hashes(),
              'statement': 'All V0.9 data, units, models and code are fixed. The test is scored once after this point.'}
    write_json(FREEZE, record)
    print(json.dumps({k: v for k, v in record.items() if k not in ('code_sha256',)}, indent=1))


def scores(bundle, model, rows):
    X = rows[bundle['columns']]
    if model == 'conditional_logit':
        return M.group_softmax(bundle['model'].decision_function(bundle['preprocessor'].transform(X, rows.event_group_id)),
                               rows.event_group_id)
    if model == 'logistic_regression':
        return bundle['model'].predict_proba(bundle['preprocessor'].transform(X, rows.event_group_id))[:, 1]
    return bundle['model'].predict_proba(X.to_numpy(float))[:, 1]


def cohort_rows(table, cohort):
    if cohort == 'pooled':
        return table, table.drop_duplicates('event_group_id').set_index('event_group_id').pooled_unit
    base = table[table.cohort == ('media' if cohort.startswith('media') else cohort)]
    if cohort == 'media_slide_confirmed':
        base = base[base.slide_confirmed.astype(bool)]
    return base, base.drop_duplicates('event_group_id').set_index('event_group_id').cohort_unit


def model_sets(cfg):
    out = {'refit_all': read_json(REFIT_DIR / 'manifest.json')['models'], 'frozen_v04_dev': cfg['frozen_v04_models']}
    return {name: {tuple(p.split('/')[-1][:-7].rsplit('_', 1)): p for p in paths} for name, paths in out.items()}


def score():
    if RESULT.exists():
        sys.exit('The V0.9 test was already scored; it is never scored twice.')
    cfg = load_config()
    f = read_json(FREEZE)
    checks = {'config': sha(CONFIG) == f['config_sha256'], 'dataset': sha(run_dir() / 'dataset.parquet') == f['dataset_sha256'],
              'units': sha(UNITS) == f['units_sha256'], 'audit': sha(V09_DATA / 'audit/process_audit.json') == f['process_audit_sha256'],
              'code': code_hashes() == f['code_sha256'],
              'models': all(sha(ROOT / p) == h for p, h in {**f['refit_models'], **f['frozen_v04_models']}.items())}
    if not all(checks.values()):
        raise RuntimeError(f'Frozen state changed: {checks}')
    data, _ = with_derived(load(run_dir() / 'dataset.parquet'))
    u = pd.DataFrame(read_json(UNITS))
    table = data.merge(u[['event_group_id', 'cohort_unit', 'pooled_unit']], on='event_group_id', how='inner').reset_index(drop=True)
    ev, boot = cfg['evaluation'], cfg['evaluation']['bootstrap']
    result = {'scored_at': datetime.now(timezone.utc).isoformat(), 'freeze_checks': checks, 'results': {}, 'bootstrap': {}}
    predictions = []
    for set_name, paths in model_sets(cfg).items():
        bundles = {k: joblib.load(ROOT / p) for k, p in paths.items()}
        all_scores = {k: scores(b, k[0], table) for k, b in bundles.items()}
        for (model, variant), s in all_scores.items():
            predictions.append(pd.DataFrame({'sample_id': table.sample_id, 'model_set': set_name, 'model': model,
                                             'variant': variant, 'score': s}))
        for cohort in COHORTS:
            rows, gu = cohort_rows(table, cohort)
            if rows.empty:
                continue
            idx = rows.index.to_numpy()
            null = M.random_rank_null(gu)
            for model in M.MODELS:
                ranks = {v: M.group_ranks(rows, all_scores[(model, v)][idx]) for v in M.VARIANTS}
                for v, r in ranks.items():
                    key = f'{set_name}/{cohort}/{model}/{v}'
                    result['results'][key] = {**M.summarize(r, gu), 'pooled_ap': M.pooled_ap(rows, all_scores[(model, v)][idx]),
                                              'p_upper_vs_random_rank': float((null['samples'] >= M.summarize(r, gu)['local_auc_weighted']).mean())}
                b = M.bootstrap(ranks, gu, boot['draws'], boot['seed'])
                b['combined_minus_static'] = {'mean': -b['static_minus_combined']['mean'],
                                              'ci95': [-b['static_minus_combined']['ci95'][1], -b['static_minus_combined']['ci95'][0]]}
                result['bootstrap'][f'{set_name}/{cohort}/{model}'] = b
            result.setdefault('random_rank_null', {})[cohort] = {k: v for k, v in null.items() if k != 'samples'}
    result['secondary'] = secondary(table, model_sets(cfg)['refit_all'], cfg)
    gate = read_json(V09_REPORT / 'process_audit_summary.json')['gate']
    media_units = int(cohort_rows(table, 'media')[1].nunique())
    d = result['bootstrap']['refit_all/media/conditional_logit']['combined_minus_static']
    established = d['ci95'][0] > 0
    confirmatory = gate['passes'] and media_units >= ev['minimum_units_for_confirmatory_claim']
    result['primary'] = {'endpoint': cfg['primary_endpoint'], 'combined_minus_static': d,
                         'combined': result['results']['refit_all/media/conditional_logit/combined'],
                         'static': result['results']['refit_all/media/conditional_logit/static'],
                         'media_units': media_units, 'quality_gate_passes': gate['passes'],
                         'confirmatory': confirmatory,
                         'verdict': ('weather benefit established' if established and confirmatory else
                                     'no established weather benefit' if confirmatory else
                                     'exploratory only (gate or unit minimum not met): ' +
                                     ('interval excludes zero' if established else 'interval includes zero'))}
    out = guard(V09_DATA / 'analysis')
    pd.concat(predictions).to_parquet(out / 'test_predictions.parquet', index=False)
    write_json(RESULT, result)
    print(json.dumps(result['primary'], indent=1))


def secondary(table, refit_paths, cfg):
    """Registered secondary analyses on the primary model set (refit_all, conditional logit)."""
    boot = cfg['evaluation']['bootstrap']
    rows, gu = cohort_rows(table, 'media')
    b = {v: joblib.load(ROOT / refit_paths[('conditional_logit', v)]) for v in M.VARIANTS}
    out = {}

    def run(subset, units_):
        r = {v: M.group_ranks(subset, scores(b[v], 'conditional_logit', subset)) for v in M.VARIANTS}
        res = {v: M.summarize(x, units_) for v, x in r.items()}
        bs = M.bootstrap(r, units_, boot['draws'], boot['seed'])
        return {'local_auc_weighted': {v: res[v]['local_auc_weighted'] for v in res}, 'events': res['static']['events'],
                'units': res['static']['units'],
                'combined_minus_static': {'mean': -bs['static_minus_combined']['mean'],
                                          'ci95': [-bs['static_minus_combined']['ci95'][1], -bs['static_minus_combined']['ci95'][0]]}}
    if gu.nunique() > 1:
        largest = gu.value_counts().index[0]
        keep = gu[gu != largest]
        sub = rows[rows.event_group_id.isin(keep.index)].reset_index(drop=True)
        out['media_without_largest_unit'] = {'removed_unit': largest, **run(sub, keep)}
    tk = rows[rows.time_quality.isin(['daypart', 'clock'])].event_group_id.unique()
    if len(tk):
        sub = rows[rows.event_group_id.isin(tk)].reset_index(drop=True)
        out['media_time_known'] = run(sub, gu[gu.index.isin(tk)])
    out['controls_within_250m_of_wlv_or_kaernten_slide'] = ('0 by construction: these records are matching exclusions '
                                                           'with radius 250 m (config matching.additional_exclusions)')
    return out


if __name__ == '__main__':
    step = sys.argv[1]
    {'refit': refit, 'partition': partition, 'freeze': freeze, 'score': score}[step]()
