"""Verify the completed V0.8 run: registration, frozen inputs, case-crossover dataset structure, CV integrity."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.baseline import verify_manifest  # noqa: E402
from preslide.v05.paths import sha  # noqa: E402
from preslide.v08 import experiment as E  # noqa: E402
from preslide.v08.paths import V08_DATA, V08_REPORT, config  # noqa: E402


def main() -> int:
    cfg = config()
    reg = json.loads((ROOT / 'reports/v08/PREREGISTRATION.json').read_text(encoding='utf-8'))
    res = json.loads((V08_REPORT / 'cv_results.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / 'data/v05/cv/cv_plan.json').read_text(encoding='utf-8'))['primary']
    data = E.prepare()
    oof = pd.read_parquet(V08_DATA / 'analysis/oof.parquet')
    unit = data.set_index('sample_id').independence_unit
    leak = 0
    for f in plan:
        o = oof[(oof.repetition == f['repetition']) & (oof.fold == f['fold'])]
        held = set(o.sample_id.map(unit))
        leak += int(bool(held - set(f['held_units'])) or bool(set(f['train_units']) & set(f['held_units'])))
    once = oof.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data)).all()
    refs = data[data.label == 0]
    pos = data[data.label == 1].set_index('event_group_id')
    checks = {
        'config_matches_registration': sha(ROOT / 'config/v08.json') == reg['config_sha256'],
        'registration_inputs_unchanged': all(sha(ROOT / p) == h for p, h in reg['input_sha256'].items()),
        'results_use_registered_config': res['inputs']['config_sha256'] == reg['config_sha256'],
        'dataset_matches_results': sha(V08_DATA / 'dataset.parquet') == res['inputs']['dataset_sha256'],
        'oof_matches_results': sha(V08_DATA / 'analysis/oof.parquet') == res['inputs']['oof_sha256'],
        'every_group_one_positive_and_3_to_4_referents': bool(data.groupby('event_group_id').label.sum().eq(1).all() and refs.groupby('event_group_id').size().between(cfg['design']['min_referents_per_group'], 4).all()),
        'referent_offsets_are_registered': set(refs.offset_days) <= set(cfg['design']['referent_offsets_days']),
        'referents_share_the_slope_coordinates': bool(((refs.x.to_numpy() == pos.loc[refs.event_group_id].x.to_numpy()) & (refs.y.to_numpy() == pos.loc[refs.event_group_id].y.to_numpy())).all()),
        'no_missing_temporal_or_hydro_values_in_complete_rows': bool(data[cfg['features']['hydro']].notna().all().all()),
        'held_out_units_never_trained': leak == 0,
        'one_oof_prediction_per_sample_and_repetition': bool(once),
        'four_comparisons_registered': cfg['comparisons_counted'] == 4,
        'baseline_manifest_in_this_checkout': verify_manifest()['status'] == 'PASS',   # CRLF checkouts (autocrlf) fail this; run in the main checkout
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks}
    (V08_REPORT / 'verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
