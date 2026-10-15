"""Verify satellite-0.4: registration, frozen inputs, table coverage, reproduction of the satellite-0.2 reference, isolation."""
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.baseline import verify_manifest  # noqa: E402
from preslide.satellite.change04 import NORM_FEATURES, PERSIST_FEATURES, config04  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    cfg = config04()
    reg = json.loads((ROOT / 'reports/satellite_0_4/PREREGISTRATION.json').read_text(encoding='utf-8'))
    tables = ROOT / 'data/satellite/tables'
    ds, dn = pd.read_parquet(tables / 'dataset.parquet'), pd.read_parquet(tables / 'dataset_norm.parquet')
    disc = json.loads((ROOT / 'reports/satellite/discovery_0_4.json').read_text(encoding='utf-8'))['summary']
    ref0 = json.loads((ROOT / 'reports/satellite/heldout_discovery_results.json').read_text(encoding='utf-8'))
    base = json.loads((ROOT / 'reports/satellite/baseline_0_4.json').read_text(encoding='utf-8'))
    rf = pd.read_parquet(tables / 'position_refinement.parquet')
    offenders = []
    for p in (ROOT / 'preslide').rglob('*.py'):
        rel = p.relative_to(ROOT / 'preslide').as_posix()
        if not rel.startswith('satellite/') and re.search(r'(from|import)\s+(\.|preslide\.)?satellite', p.read_text(encoding='utf-8')):
            offenders.append(rel)
    v04 = pd.read_parquet(ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet')
    no_filter = disc['change_features/no_filter']
    checks = {
        'config_matches_registration': sha(ROOT / 'config/satellite_0_4.json') == reg['config_sha256'],
        'registration_inputs_unchanged': all(sha(ROOT / p) == h for p, h in reg['input_sha256'].items()),
        'norm_table_covers_dataset_exactly': set(dn.sample_id) == set(ds.sample_id) and len(dn) == len(ds),
        'registered_feature_counts': len(NORM_FEATURES) == 12 and len(PERSIST_FEATURES) == 8 and all(c in dn for c in NORM_FEATURES + PERSIST_FEATURES),
        'every_positive_has_reference_and_confirm_or_reason': bool(dn[dn.label == 1].norm_reference.notna().all() and dn[dn.label == 1].norm_confirm.notna().all()),
        'no_filter_reproduces_satellite_0_2_reference': (no_filter['found_top3'], no_filter['found_any_rank'], round(no_filter['peaks_per_km2_mean'], 6)) ==
                                                         (ref0['detected_top3'], ref0['detected_any_rank'], round(ref0['peaks_per_km2_mean'], 6)),
        'discovery_covers_all_events_and_units': all(v['events'] == ref0['events'] and v['units'] == ref0['independence_units'] for v in disc.values()),
        'six_comparisons_reported': len(base['paired']) == cfg['comparisons_counted'],
        'refinement_is_a_proposal_only': bool(set(rf.source) == {'satellite_scar_centroid'} and v04.label.sum() == 423),
        'pipeline_a_does_not_import_pipeline_b': not offenders,
        'baseline_manifest_in_this_checkout': verify_manifest()['status'] == 'PASS',   # CRLF checkouts (autocrlf) fail this; run in the main checkout
    }
    status = 'PASS' if all(checks.values()) else 'FAIL'
    out = {'status': status, 'checks': checks, 'importing_modules_outside_satellite': offenders}
    (ROOT / 'reports/satellite_0_4/verification.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps(out, indent=1))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
