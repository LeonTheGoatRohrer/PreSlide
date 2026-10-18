"""Prove the susceptibility_v01 safety tests can fail: disable one guard at a time, run the tests, restore.

python scripts/mutation_check_susceptibility.py   (writes reports/susceptibility_v01/mutation_check.json)
Each mutant must make at least one test fail; the source file is always restored.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ['tests/test_susceptibility_v01.py']
MUTANTS = {
    'preslide/susceptibility/registry.py': [
        ('sealed flags not checked', "if d.get(flag) is not False:", "if False:"),
        ('sealed dataset allowed in an arm', "elif datasets[m]['role'] != 'development':", "elif False:"),
        ('DEM date rule off', "if first and date.fromisoformat", "if False and date.fromisoformat"),
        ('DEM rule off by one day (>=)', "date.fromisoformat(cfg['dem']['acquisition_end']) > date.fromisoformat(first)",
         "date.fromisoformat(cfg['dem']['acquisition_end']) > date.fromisoformat(first).replace(year=9999)"),
        ('amendment may overwrite', "if node[leaf] is not None:", "if False:"),
        ('training_datasets returns sealed', "out = [m for m in members if datasets[m]['role'] == 'development']", "out = list(members)"),
    ],
    'preslide/susceptibility/paths.py': [
        ('config hash not checked', "if Path(registration).exists() and text_sha(path)", "if False and text_sha(path)"),
        ('amendment sidecar not checked', "if not side.exists() or side.read_text", "if False and side.read_text"),
        ('guard allows any path', "if not any(path == r or r in path.parents for r in roots):", "if False:"),
    ],
    'preslide/susceptibility/inventory.py': [
        ('archive members not checked', "    if bad:\n        raise RuntimeError(f'unsafe", "    if False:\n        raise RuntimeError(f'unsafe"),
        ('degree areas not projected', "    if to_m:\n        fixed", "    if False:\n        fixed"),
        ('UTM zone from latitude', "zone = int((lon + 180) // 6) + 1", "zone = int((lat + 180) // 6) + 1"),
    ],
    'preslide/susceptibility/terrain.py': [
        ('DEM date rule allows same day', "not cfg['dem']['acquisition_end'] < first", "not cfg['dem']['acquisition_end'] <= first"),
        ('grid origin swapped', "dst_transform=from_origin(left, top, res_m, res_m)", "dst_transform=from_origin(top, left, res_m, res_m)"),
        ('aspect sin/cos swapped', "'aspect_sin': np.sin(np.deg2rad(aspect))", "'aspect_sin': np.cos(np.deg2rad(aspect))"),
        ('truncated catchment kept', "'log10_catchment_m2': np.where(edge, np.nan, np.log10(area))", "'log10_catchment_m2': np.log10(area)"),
        ('block checksum not verified', "if file_digest(path, 'sha256') != meta['sha256']:", "if False:"),
    ],
    'preslide/susceptibility/sampling.py': [
        ('buffer not applied', "shapely.buffer(np.array(known, dtype=object), circumscribed, quad_segs=quad_segs)", "shapely.buffer(np.array(known, dtype=object), 0, quad_segs=quad_segs)"),
        ('buffer chord error', "circumscribed = buffer_m / math.cos(math.pi / (4 * quad_segs))", "circumscribed = buffer_m"),
        ('obscured areas ignored', "    if obscured:\n        zone = shapely.union", "    if False:\n        zone = shapely.union"),
        ('min separation ignored', "            if too_close(xi, yi, tree,", "            if False and too_close(xi, yi, tree,"),
        ('extent not checked', "inside = shapely.contains_xy(allowed, x, y)\n        x, y", "inside = np.ones(len(x), bool)\n        x, y"),
        ('top third ignored', "top = z >= np.quantile(z, 2 / 3)", "top = z >= np.quantile(z, 0)"),
        ('small polygon dropped', "return float(cell_centre(p.x, cell)), float(cell_centre(p.y, cell)), 'containing_cell'",
         "return None, None, 'containing_cell'"),
    ],
    'preslide/susceptibility/evaluate.py': [
        ('held-out inventory in training', "return data[data.dataset != held], data[data.dataset == held]", "return data, data[data.dataset == held]"),
        ('blocks split across folds', "return np.array([fold_of[b] for b in blocks])", "return np.arange(len(blocks)) % k"),
        ('no purge', "return train[d >= gap_m]", "return train"),
        ('bootstrap ignores blocks', "return counts[:, codes]", "return rng.integers(0, 3, size=(n, len(codes)))"),
        ('Boyce ratio inverted', "ratio.append(np.mean((pres >= lo) & (pres <= hi)) / e)", "ratio.append(e / max(np.mean((pres >= lo) & (pres <= hi)), 1e-9))"),
    ],
}


def run_tests():
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *TESTS], cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]


def main():
    code, line = run_tests()
    if code != 0:
        sys.exit(f'unmutated tests fail: {line}')
    results = []
    for rel, mutants in MUTANTS.items():
        path = ROOT / rel
        original = path.read_bytes()
        try:
            for name, old, new in mutants:
                text = original.decode('utf-8')
                if text.count(old) != 1:
                    sys.exit(f'{rel}: pattern for {name!r} not found exactly once')
                path.write_bytes(text.replace(old, new).encode('utf-8'))
                code, line = run_tests()
                results.append({'file': rel, 'mutant': name, 'tests_failed': code != 0, 'summary': line})
                path.write_bytes(original)
        finally:
            path.write_bytes(original)
    out = {'baseline_summary': run_tests()[1], 'mutants': results,
           'status': 'PASS' if all(r['tests_failed'] for r in results) else 'FAIL'}
    report = ROOT / 'reports/susceptibility_v01'
    report.mkdir(parents=True, exist_ok=True)
    # The copy hashed at registration stays untouched; later reruns write a separate file.
    name = 'mutation_check_latest.json' if (report / 'PREREGISTRATION.json').exists() else 'mutation_check.json'
    (report / name).write_bytes(json.dumps(out, indent=1).encode('utf-8') + b'\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
