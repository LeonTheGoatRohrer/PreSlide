"""Inject each dangerous bug into anfaelligkeit_at_v01 and show that its safety test fails (AGENTS.md section 26).

  .venv/Scripts/python scripts/anfaelligkeit_at_v01_mutation_check.py

Every source file is restored afterwards; results go to reports/anfaelligkeit_at_v01/mutation_tests.json.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = 'preslide/anfaelligkeit_at_v01/'
TESTS = 'tests/test_anfaelligkeit_at_v01.py::'
MUTATIONS = [
    ('spatial purge disabled', PKG + 'experiment.py', 'return train[d > radius_m]', 'return train', 'test_held_out_area_never_in_training_and_purged'),
    ('half of the held-out area leaks into training', PKG + 'experiment.py', "test = data[data.area_id == a]\n",
     "test = data[data.area_id == a].iloc[::2]\n", 'test_held_out_area_never_in_training_and_purged'),
    ('infrastructure distance allowed as feature', PKG + 'experiment.py', "'dist_', ", '', 'test_no_features_from_neighbouring_events_or_reporting'),
    ('inventory-count feature allowed', PKG + 'experiment.py', "'inventory', ", '', 'test_no_features_from_neighbouring_events_or_reporting'),
    ('feature whitelist not enforced in training', PKG + 'experiment.py', '        check_features(cols)\n        hgb', '        hgb',
     'test_score_models_refuses_a_leaking_feature_set'),
    ('aspect as linear degrees', PKG + 'terrain.py', "'aspect_sin': np.sin(a), 'aspect_cos': np.cos(a)",
     "'aspect_sin': aspect / 360.0, 'aspect_cos': aspect / 360.0", 'test_aspect_features_are_circular'),
    ('lon/lat swapped before projecting', PKG + 'inventory.py', 'PROJECT.transform(np.asarray(lon, float), np.asarray(lat, float))',
     'PROJECT.transform(np.asarray(lat, float), np.asarray(lon, float))', 'test_projected_distances_match_geodesic'),
    ('inventory buffer ignored', PKG + 'inventory.py', 'return d > self.r', 'return d > 0', 'test_background_buffer_separation_and_region'),
    ('background separation ignored', PKG + 'inventory.py', 'elif sep.near(x[i], y[i]):', 'elif False:', 'test_background_buffer_separation_and_region'),
    ('block cache identity not checked', PKG + 'terrain.py', "if meta['identity'] != identity:", 'if False:', 'test_block_cache_identity_and_checksum'),
    ('block cache checksum not checked', PKG + 'terrain.py', "if sha(path) != meta['sha256']:", 'if False:', 'test_block_cache_identity_and_checksum'),
    ('block identity ignores the DEM variant', PKG + 'terrain.py', "digest({'variant': variant, ", "digest({", 'test_block_cache_identity_and_checksum'),
    ('SRTM admits year-2000 events', PKG + 'inventory.py', 'years.fillna(0) >= 2001', 'years.fillna(0) >= 2000', 'test_dem_provenance_year_rule'),
    ('CORINE vintage after the event', PKG + 'context.py', 'if year <= 2007:', 'if year <= 2008:', 'test_corine_vintage_strictly_before_event_year'),
    ('duplicates not merged', PKG + 'inventory.py', '        if not index.near(x, y):\n            index.add(x, y)\n            keep[i] = True',
     '        if True:\n            index.add(x, y)\n            keep[i] = True', 'test_deduplication_and_priority'),
    ('missing geology coded as zero', PKG + 'context.py', 'out[classes.isna()] = np.nan', 'pass', 'test_missing_class_is_missing_not_zero'),
]


def run_test(test: str) -> int:
    return subprocess.run([sys.executable, '-m', 'pytest', '-q', '-x', '-p', 'no:cacheprovider', TESTS + test], cwd=ROOT,
                          capture_output=True, text=True).returncode


def main():
    results = []
    for name, rel, old, new, test in MUTATIONS:
        path = ROOT / rel
        source = path.read_text(encoding='utf-8')
        if source.count(old) != 1:
            raise SystemExit(f'mutation anchor not unique in {rel}: {old!r}')
        try:
            path.write_text(source.replace(old, new), encoding='utf-8')
            code = run_test(test)
        finally:
            path.write_text(source, encoding='utf-8')
        results.append({'mutation': name, 'file': rel, 'test': test, 'caught': code != 0})
        print(f"{'CAUGHT' if code else 'MISSED'}  {name}  ({test})", flush=True)
    clean = {t: run_test(t) == 0 for t in sorted({m[4] for m in MUTATIONS})}
    out = {'run_at_utc': datetime.now(timezone.utc).isoformat(), 'all_caught': all(r['caught'] for r in results),
           'clean_tests_pass': all(clean.values()), 'mutations': results, 'clean_runs': clean}
    (ROOT / 'reports/anfaelligkeit_at_v01/mutation_tests.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    if not (out['all_caught'] and out['clean_tests_pass']):
        raise SystemExit('a mutation was missed or a clean test failed')


if __name__ == '__main__':
    main()
