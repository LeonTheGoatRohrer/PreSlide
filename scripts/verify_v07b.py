"""Verify the completed V0.7b run: registration, V0.7 untouched, distance checks, CV integrity, report consistency."""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.v05.paths import sha  # noqa: E402
from preslide.v07b import experiment as E  # noqa: E402
from preslide.v07b.paths import V07B_DATA, V07B_REPORT, config  # noqa: E402


def main() -> int:
    cfg = config()                                     # raises if the config or any registered input (incl. data/v07 tables, PBF) changed
    reg = json.loads((V07B_REPORT / 'PREREGISTRATION.json').read_text(encoding='utf-8'))
    res = json.loads((V07B_REPORT / 'cv_results.json').read_text(encoding='utf-8'))
    comp = json.loads((V07B_REPORT / 'comparison.json').read_text(encoding='utf-8'))
    dist_checks = json.loads((V07B_DATA / 'distance_checks.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / cfg['inputs']['cv_plan']).read_text(encoding='utf-8'))['primary']
    with E.bound():
        data, _ = E.E.prepare()
    oof = pd.read_parquet(V07B_DATA / 'analysis/oof_infra.parquet')
    unit = data.set_index('sample_id').independence_unit
    leak = 0
    for f in plan:
        o = oof[(oof.repetition == f['repetition']) & (oof.fold == f['fold'])]
        leak += int(bool(set(o.sample_id.map(unit)) - set(f['held_units'])) or bool(set(f['train_units']) & set(f['held_units'])))
    once = oof.groupby(['model', 'variant', 'repetition']).sample_id.agg(lambda s: s.is_unique and len(s) == len(data)).all()
    old = pd.read_parquet(ROOT / cfg['inputs']['v07_infrastructure']).set_index('sample_id')
    new = data.set_index('sample_id')
    cap = 5000
    v07_untouched = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'config/v07.json', 'preslide/v07', 'reports/v07', 'scripts/verify_v07.py'], cwd=ROOT).returncode == 0
    checks = {
        'config_matches_registration': sha(ROOT / 'config/v07b.json') == reg['config_sha256'],
        'registered_inputs_unchanged_incl_v07_tables': all(sha(ROOT / p) == h for p, h in reg['input_sha256'].items()),
        'v07_code_config_reports_unchanged_in_git': v07_untouched,
        'results_record_v07b_config': res['inputs']['v07b_config_sha256'] == reg['config_sha256'],
        'results_use_registered_v07_analysis_plan': res['inputs']['config_sha256'] == sha(ROOT / 'config/v07.json'),
        'infrastructure_table_matches_results': sha(V07B_DATA / 'infrastructure.parquet') == res['inputs']['infrastructure_sha256'],
        'oof_matches_results': sha(V07B_DATA / 'analysis/oof_infra.parquet') == res['inputs']['oof_infra_sha256'],
        'v07_accumulator_reproduced_v07_table_exactly': dist_checks.get('v07_reproduced_exactly') is True,
        'brute_force_check_within_0_01_m': dist_checks['brute_force_ok'] is True,
        'exact_distances_never_above_v07': bool(all((new[c] <= old.loc[new.index, c] + 1e-9).all() for c in ('dist_road_m', 'dist_building_m'))),
        'distances_in_range_and_cap_flags_consistent': bool(((new.dist_road_m >= 0) & (new.dist_road_m <= cap) & (new.dist_building_m >= 0) & (new.dist_building_m <= cap)).all()
                                                           and ((new.dist_road_m == cap) == new.road_capped).all() and ((new.dist_building_m == cap) == new.building_capped).all()),
        'held_out_units_never_trained': leak == 0,
        'one_oof_prediction_per_sample_and_repetition': bool(once),
        'comparison_uses_these_results': comp['caliper_groups']['v07b'] == res['b_caliper']['groups_kept'],
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks}
    (V07B_REPORT / 'verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
