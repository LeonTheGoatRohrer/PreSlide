"""Prove the susceptibility_v02 safety tests can fail: disable one rule at a time, run the tests, restore.

python scripts/mutation_check_susceptibility_v02.py   (writes reports/susceptibility_v02/mutation_check.json)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ['tests/test_susceptibility_v02.py']
SOURCE = 'preslide/susceptibility/v02.py'
MUTANTS = [
    ('other trigger allowed in arm', "elif d['trigger_class'] != trigger:", "elif False:"),
    ('sealed/excluded allowed in arm', "elif d['role'] not in (USABLE, 'pending_extent'):", "elif False:"),
    ('seen confirmatory test allowed', "elif datasets[test].get('seen_in_v01', True):", "elif False:"),
    ('extent not required', "if ext.get('status') != EXTENT_OK or not str(ext.get('source') or '').strip():", "if False:"),
    ('licence verification ignored', "if not d.get('license_verified_at_original'):", "if False:"),
    ('DEM same day allowed', "if not dem_end < date.fromisoformat(first):", "if not dem_end <= date.fromisoformat(first):"),
    ('single inventory allowed', "if len(members) < 2:", "if len(members) < 1:"),
    ('ShakeMap not required', "if m in datasets and not datasets[m].get('shakemap_event_id'):", "if False:"),
    ('sealed registration not required', "if not blind:", "if False:"),
    ('multiplicity not checked', "if n_tests != 4 or f'0.025/{n_tests}' not in cfg['evaluation']['multiplicity']:", "if False:"),
    ('Bonferroni ignored', "return 100 * 0.025 / n", "return 100 * 0.025"),
    ('training includes held-out', "out = [m for m in arm['inventories'] if m != held_out]", "out = list(arm['inventories'])"),
    ('training role not checked', "        if d['role'] != USABLE:\n            raise ValueError(f'{m} has role", "        if False:\n            raise ValueError(f'{m} has role"),
    ('training trigger not checked', "if d['trigger_class'] != trigger:\n            raise", "if False:\n            raise"),
    ('cross-trigger uses own trigger', "other = next(t for t in TRIGGERS if t != own)", "other = own"),
    ('config hash not checked', "if Path(registration).exists() and text_sha(path)", "if False and text_sha(path)"),
    ('guard allows any path', "if not any(path == r or r in path.parents for r in roots):", "if False:"),
    ('sealed folder readable', "if path == sealed or sealed in path.parents:", "if False:"),
]


def run_tests():
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *TESTS], cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]


def main():
    code, line = run_tests()
    if code != 0:
        sys.exit(f'unmutated tests fail: {line}')
    path = ROOT / SOURCE
    original = path.read_bytes()
    results = []
    try:
        for name, old, new in MUTANTS:
            text = original.decode('utf-8')
            if text.count(old) != 1:
                sys.exit(f'pattern for {name!r} not found exactly once')
            path.write_bytes(text.replace(old, new).encode('utf-8'))
            code, line = run_tests()
            results.append({'file': SOURCE, 'mutant': name, 'tests_failed': code != 0, 'summary': line})
            path.write_bytes(original)
    finally:
        path.write_bytes(original)
    out = {'baseline_summary': run_tests()[1], 'mutants': results,
           'status': 'PASS' if all(r['tests_failed'] for r in results) else 'FAIL'}
    report = ROOT / 'reports/susceptibility_v02'
    report.mkdir(parents=True, exist_ok=True)
    name = 'mutation_check_latest.json' if (report / 'PREREGISTRATION.json').exists() else 'mutation_check.json'
    (report / name).write_bytes(json.dumps(out, indent=1).encode('utf-8') + b'\n')
    print(json.dumps({'status': out['status'], 'n': len(results),
                      'survivors': [r['mutant'] for r in results if not r['tests_failed']]}, indent=1))


if __name__ == '__main__':
    main()
