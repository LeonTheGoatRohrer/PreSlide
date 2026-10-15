"""Verify the completed V0.7 run: registration, frozen inputs, source file, distance table, CV integrity."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.baseline import verify_manifest  # noqa: E402
from preslide.v05.paths import sha  # noqa: E402
from preslide.v07 import experiment as E  # noqa: E402
from preslide.v07.paths import V07_DATA, V07_REPORT, config  # noqa: E402


def main() -> int:
    cfg = config()
    reg = json.loads((ROOT / 'reports/v07/PREREGISTRATION.json').read_text(encoding='utf-8'))
    res = json.loads((V07_REPORT / 'cv_results.json').read_text(encoding='utf-8'))
    source = json.loads((V07_DATA / 'source.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / 'data/v05/cv/cv_plan.json').read_text(encoding='utf-8'))['primary']
    data, _ = E.prepare()
    oof = pd.read_parquet(V07_DATA / 'analysis/oof_infra.parquet')
    unit = data.set_index('sample_id').independence_unit
    leak = 0
    for f in plan:
        o = oof[(oof.repetition == f['repetition']) & (oof.fold == f['fold'])]
        held = set(o.sample_id.map(unit))
        leak += int(bool(held - set(f['held_units'])) or bool(set(f['train_units']) & set(f['held_units'])) or bool(set(f['purged_units']) & set(f['train_units'])))
    once = oof.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data)).all()
    cap = cfg['infrastructure']['distance_cap_m']
    d = data
    checks = {
        'config_matches_registration': sha(ROOT / 'config/v07.json') == reg['config_sha256'],
        'registration_inputs_unchanged': all(sha(ROOT / p) == h for p, h in reg['input_sha256'].items()),
        'results_use_registered_config': res['inputs']['config_sha256'] == reg['config_sha256'],
        'infrastructure_table_matches_results': sha(V07_DATA / 'infrastructure.parquet') == res['inputs']['infrastructure_sha256'],
        'oof_matches_results': sha(V07_DATA / 'analysis/oof_infra.parquet') == res['inputs']['oof_infra_sha256'],
        'source_size_matches_registration': source['bytes'] == cfg['source']['size_bytes'],
        'source_sha_unchanged_on_disk': sha(V07_DATA / 'source' / cfg['source']['file']) == source['sha256'],
        'distances_in_range_and_cap_flags_consistent': bool(((d.dist_road_m >= 0) & (d.dist_road_m <= cap) & (d.dist_building_m >= 0) & (d.dist_building_m <= cap)).all()
                                                           and ((d.dist_road_m == cap) == d.road_capped).all() and ((d.dist_building_m == cap) == d.building_capped).all()),
        'held_out_units_never_trained_or_purged_reused': leak == 0,
        'one_oof_prediction_per_sample_and_repetition': bool(once),
        'seven_comparisons_registered': cfg['comparisons_counted'] == 7,
        'baseline_manifest_in_this_checkout': verify_manifest()['status'] == 'PASS',   # CRLF checkouts (autocrlf) fail this; run in the main checkout
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks}
    (V07_REPORT / 'verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
