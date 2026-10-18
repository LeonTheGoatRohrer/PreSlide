"""Invariants of anfaelligkeit_at_v01: `python scripts/verify_anfaelligkeit_at_v01.py` -> reports/anfaelligkeit_at_v01/verification.json"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preslide.anfaelligkeit_at_v01 import experiment  # noqa: E402
from preslide.anfaelligkeit_at_v01.paths import DATA, MODELS, REPORT, config, load  # noqa: E402

checks = {}


def check(name, ok, detail=''):
    checks[name] = {'pass': bool(ok), 'detail': detail}


cfg = config()          # raises if the config or the registered inventory changed after registration
check('registration_config_and_inventory_unchanged', True)
for variant in ('srtm', 'skadi'):
    r = json.loads((REPORT / f'results_{variant}.json').read_text(encoding='utf-8'))
    data = experiment.assemble(variant)
    pred = load(DATA / f'predictions_{variant}.parquet')
    table = experiment.per_area(pred)
    stored = load(DATA / f'area_table_{variant}.parquet')
    m = table.merge(stored, on=['area_id', 'model', 'feature_set'], suffixes=('', '_s'))
    check(f'{variant}_area_metrics_recomputed', len(m) == len(stored) and np.allclose(m.auc, m.auc_s),
          f'{len(m)} rows, max |diff| {float(np.abs(m.auc - m.auc_s).max()):.2e}')
    s = experiment.summarise(table, cfg)
    check(f'{variant}_primary_recomputed', abs(s['hgb:terrain_geology']['auc_minus_hgb:slope_only']['mean'] - r['primary']['diff']['mean']) < 1e-12)
    ids = data.groupby('area_id').sample_id.apply(set)
    ok = all(set(pred[pred.area_id == a].sample_id) == ids[a] for a in r['evaluation_areas'])
    check(f'{variant}_each_area_scored_completely', ok)
    leak = []
    for a, train, test in experiment.folds(data, r['evaluation_areas'], cfg['evaluation']['spatial_purge_m']):
        if a in set(train.area_id) or len(train) != r['fold_info'][a]['train_samples']:
            leak.append(a)
    check(f'{variant}_held_out_area_never_in_training', not leak, str(leak))
    feats = [c for cols in experiment.FEATURE_SETS.values() for c in cols]
    experiment.check_features(feats)
    check(f'{variant}_no_forbidden_features', True)
    lab = data.groupby('area_id').label.agg(['sum', 'count'])
    check(f'{variant}_background_ratio_1_to_3', bool((lab['count'] == 4 * lab['sum']).all()))
demo = joblib.load(MODELS / 'srtm/demo_fold.joblib')
meta = json.loads((DATA / 'demo/demo_meta.json').read_text(encoding='utf-8'))
check('demo_layer_from_fold_without_demo_area', demo['held_out_area'] == meta['area_id'] ==
      json.loads((REPORT / 'results_srtm.json').read_text(encoding='utf-8'))['largest_area'])
mut = json.loads((REPORT / 'mutation_tests.json').read_text(encoding='utf-8'))
check('mutation_tests_all_caught', mut['all_caught'] and mut['clean_tests_pass'], f"{len(mut['mutations'])} mutations")
out = {'all_pass': all(c['pass'] for c in checks.values()), 'checks': checks}
(REPORT / 'verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out, indent=1))
sys.exit(0 if out['all_pass'] else 1)
