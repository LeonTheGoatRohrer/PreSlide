"""Prove the susceptibility_v02 PGA / GSI / sensitivity / terrain tests can fail: inject one bug at a time, run the tests, restore.

python scripts/mutation_check_susceptibility_v02_pga.py   (writes reports/susceptibility_v02/mutation_check_pga.json)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ['tests/test_susceptibility_v02_pga.py', 'tests/test_susceptibility_v02_terrain.py']
P1 = 'preslide/susceptibility/v02_phase1.py'
SE = 'preslide/susceptibility/v02_sensitivity.py'
TE = 'preslide/susceptibility/v02_terrain.py'
MUTANTS = [
    (P1, 'grid spacing from rounded header', "dlon, dlat = (lon[0, -1] - lon0) / (nlon - 1), (lat_top - lat[-1, 0]) / (nlat - 1)",
     "dlon, dlat = float(spec['nominal_lon_spacing']), float(spec['nominal_lat_spacing'])"),
    (P1, 'lattice order check disabled', "if not (dlon > 0 and dlat > 0 and", "if False and (dlon > 0 and dlat > 0 and"),
    (P1, 'corner check disabled', "if any(abs(v - float(spec[k])) > tol_deg for v, k in corners):", "if False:"),
    (P1, 'rows counted from the south', "fr = (lat_top - lat) / dlat", "fr = (lat - lat_top) / dlat"),
    (P1, 'half-cell offset', "fc = (lon - lon0) / dlon", "fc = (lon - lon0) / dlon + 0.5"),
    (P1, 'lon/lat swapped in interpolation', "fc = (lon - lon0) / dlon\n    fr = (lat_top - lat) / dlat",
     "fc = (lat - lon0) / dlon\n    fr = (lat_top - lon) / dlat"),
    (P1, 'outside grid clamped instead of NaN', "ok = (fc >= 0) & (fc <= nc - 1) & (fr >= 0) & (fr <= nr - 1)",
     "fc, fr = np.clip(fc, 0, nc - 1), np.clip(fr, 0, nr - 1)\n    ok = np.isfinite(fc)"),
    (P1, 'easting/northing swapped', "return t.transform(np.asarray(x, float), np.asarray(y, float))",
     "return t.transform(np.asarray(y, float), np.asarray(x, float))"),
    (P1, 'axis order not forced', "t = Transformer.from_crs(CRS.from_user_input(crs), CRS.from_epsg(4326), always_xy=True)",
     "t = Transformer.from_crs(CRS.from_user_input(crs), CRS.from_epsg(4326))"),
    (P1, 'non-positive PGA filled with 0', "out = np.full(p.shape, np.nan)", "out = np.zeros(p.shape)"),
    (P1, 'PGA units not checked', "if units.strip().lower() not in ('pctg', '%g'):", "if False:"),
    (P1, 'open extent line accepted', "if tuple(line_coords[0]) != tuple(line_coords[-1]) or not line.is_ring:", "if False:"),
    (P1, 'GSI role by suffix match', "return GSI_ROLES.get(Path(name).name.split('_')[-1])",
     "return next((v for k, v in GSI_ROLES.items() if Path(name).name.endswith(k)), None)"),
    (P1, 'cp932 member names not decoded', "return info.filename.encode('cp437').decode('cp932')", "return info.filename"),
    (P1, 'buffer not rounded up', "value = max(floor_m, math.ceil(round(top, 9) / step_m) * step_m)",
     "value = max(floor_m, round(top / step_m) * step_m)"),
    (P1, 'buffer floor dropped', "value = max(floor_m, math.ceil(", "value = max(0, math.ceil("),
    (P1, 'buffer cap not flagged', "return (min(value, cap_m), value > cap_m)", "return (min(value, cap_m), False)"),
    (P1, 'buffer from mean not maximum', "top = max(p90_by_inventory.values())",
     "top = sum(p90_by_inventory.values()) / len(p90_by_inventory)"),
    (P1, 'radius from area without pi', "np.sqrt(np.asarray(areas_m2, float) / np.pi)", "np.sqrt(np.asarray(areas_m2, float))"),
    (P1, 'touching old landslides ignored', "predicate='intersects'", "predicate='contains_properly'"),
    (TE, 'merge bounds not snapped', "bounds = snap_to_lattice((lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad), ref.c, ref.f, res)",
     "bounds = (lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad)"),
    (TE, 'snap rounds inward', "x0 + math.floor((west - x0) / res) * res", "x0 + math.ceil((west - x0) / res) * res"),
    (TE, 'tile checksum not verified', "if file_digest(f, 'sha256') != read_json(folder / 'provenance.json')['files'][0]['sha256']:",
     "if False:"),
    (TE, 'terrain parameters not checked', "if t[k] != v or f'{k} {v:g}' not in rule:", "if False:"),
    (TE, 'disjoint blocks kept', "for b in block_grid(extent.bounds, t['block_core_m'], res_m) if shapely.box(*b[2:]).intersects(extent)]",
     "for b in block_grid(extent.bounds, t['block_core_m'], res_m)]"),
    (TE, 'window shape swapped', "shape = (round((top - bottom) / res_m), round((right - left) / res_m))",
     "shape = (round((right - left) / res_m), round((top - bottom) / res_m))"),
    (TE, 'unsupported inventory accepted', "if dataset not in SUPPORTED:", "if False:"),
    (TE, 'v01 inventories downloadable', "if dataset not in NEW_INVENTORIES:\n        raise ValueError(f'{dataset}: v01 tiles",
     "if False:\n        raise ValueError(f'{dataset}: v01 tiles"),
    (TE, 'wrong central meridian', "(6 * zone - 183)", "(6 * zone - 180)"),
    (SE, 'PGA in terrain-only model', "'EQ_TERRAIN': ('hist_gradient_boosting', terrain),",
     "'EQ_TERRAIN': ('hist_gradient_boosting', terrain + [PGA]),"),
    (SE, 'block index truncated not floored', "int(math.floor(a / size_m))", "int(a / size_m)"),
    (SE, 'hyperparameter check disabled',
     "        raise RuntimeError('v02 hyperparameters differ from susceptibility_v01 Amendment 3')", "        pass"),
    (SE, 'purge skipped', "train = purge(d[folds != f], test, purge_m)", "train = d[folds != f]"),
    (SE, 'interval clause dropped from rule', "proximity = bool(d20_point < 0.5 * d5 or (d20_interval[0] <= 0 <= d20_interval[1]))",
     "proximity = bool(d20_point < 0.5 * d5)"),
    (SE, 'half boundary inclusive', "shaking = bool(dpga5 < 0.5 * d5)", "shaking = bool(dpga5 <= 0.5 * d5)"),
    (SE, 'design constants changed', "'purge_m': 1000,", "'purge_m': 500,"),
]


def run_tests():
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *TESTS], cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]


def main():
    code, line = run_tests()
    if code != 0:
        sys.exit(f'unmutated tests fail: {line}')
    originals = {f: (ROOT / f).read_bytes() for f in {m[0] for m in MUTANTS}}
    results = []
    try:
        for source, name, old, new in MUTANTS:
            text = originals[source].decode('utf-8')
            if text.count(old) != 1:
                sys.exit(f'pattern for {name!r} not found exactly once')
            (ROOT / source).write_bytes(text.replace(old, new).encode('utf-8'))
            code, line = run_tests()
            results.append({'file': source, 'mutant': name, 'tests_failed': code != 0, 'summary': line})
            (ROOT / source).write_bytes(originals[source])
    finally:
        for f, b in originals.items():
            (ROOT / f).write_bytes(b)
    out = {'baseline_summary': run_tests()[1], 'mutants': results,
           'status': 'PASS' if all(r['tests_failed'] for r in results) else 'FAIL'}
    (ROOT / 'reports/susceptibility_v02/mutation_check_pga.json').write_bytes(json.dumps(out, indent=1).encode('utf-8') + b'\n')
    print(json.dumps({'status': out['status'], 'n': len(results),
                      'survivors': [r['mutant'] for r in results if not r['tests_failed']]}, indent=1))


if __name__ == '__main__':
    main()
