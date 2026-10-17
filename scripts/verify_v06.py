"""Verify the completed V0.6 run: registration, frozen V0.5 inputs, CV integrity, hydro features recomputed, baseline untouched."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.baseline import verify_manifest  # noqa: E402
from preslide.v05.paths import sha  # noqa: E402
from preslide.v06 import experiment as E  # noqa: E402
from preslide.v06 import pipeline as P  # noqa: E402
from preslide.v06.paths import V06_DATA, V06_REPORT, config  # noqa: E402


def main() -> int:
    cfg = config()
    reg = json.loads((ROOT / 'reports/v06/PREREGISTRATION.json').read_text(encoding='utf-8'))
    res = json.loads((V06_REPORT / 'cv_results.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / 'data/v05/cv/cv_plan.json').read_text(encoding='utf-8'))['primary']
    data, _ = E.prepare()
    oof = pd.read_parquet(V06_DATA / 'analysis/oof_purged.parquet')
    unit = data.set_index('sample_id').independence_unit
    leak = 0
    for f in plan:
        o = oof[(oof.repetition == f['repetition']) & (oof.fold == f['fold'])]
        held = set(o.sample_id.map(unit))
        leak += int(bool(held - set(f['held_units'])) or bool(set(f['train_units']) & set(f['held_units'])) or
                    bool(set(f['purged_units']) & set(f['train_units'])))
    once = oof.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data)).all()
    recomputed = P.stage_hydro(limit=3)                       # independent recomputation from the response caches
    stored = pd.read_parquet(V06_DATA / 'hydro.parquet').set_index('sample_id').loc[recomputed.sample_id]
    same = bool(((recomputed.set_index('sample_id')[stored.columns].fillna(-1e9) - stored.fillna(-1e9)).abs().max().max()) < 1e-9)
    future_cols = [c for c in cfg['hydrology']['features'] if any(s in c for s in ('since_midnight', 'last_used'))]
    checks = {
        'config_matches_registration': sha(ROOT / 'config/v06.json') == reg['config_sha256'],
        'registration_inputs_unchanged': all(sha(ROOT / p) == h for p, h in reg['input_sha256'].items()),
        'results_use_registered_config': res['inputs']['config_sha256'] == reg['config_sha256'],
        'oof_file_matches_results': sha(V06_DATA / 'analysis/oof_purged.parquet') == res['inputs']['oof_sha256'],
        'held_out_units_never_trained_or_purged_reused': leak == 0,
        'one_oof_prediction_per_sample_and_repetition': bool(once),
        'hydro_features_recomputed_identically': same,
        'hydro_columns_are_exactly_the_registered_list': sorted(pd.read_parquet(V06_DATA / 'hydro.parquet').columns[1:]) == sorted(cfg['hydrology']['features']),
        'no_same_day_columns': not future_cols,
        'four_comparisons_reported': res['paired_comparisons_counted'] == cfg['comparisons_counted'],
        'baseline_manifest_in_this_checkout': verify_manifest()['status'] == 'PASS',   # CRLF checkouts (autocrlf) fail this; run in the main checkout
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks, 'oof_sha256': hashlib.sha256((V06_DATA / 'analysis/oof_purged.parquet').read_bytes()).hexdigest()}
    (V06_REPORT / 'verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
