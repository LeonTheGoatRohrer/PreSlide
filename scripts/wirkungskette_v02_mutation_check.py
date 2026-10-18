"""Inject one bug at a time into preslide/wirkungskette/gegenprobe.py, run the guarding tests, restore.

Writes reports/wirkungskette_v02/mutation_tests.json. Every mutation must make at least one test fail."""
import json
import subprocess
import sys
from pathlib import Path

TARGET = Path('preslide/wirkungskette/gegenprobe.py')
TESTS = 'tests/test_wirkungskette_v02.py'
MUT = [
    ('zellen-vertauscht', "'schaden_ja_szenario_nein': int((d & ~h).sum())", "'schaden_ja_szenario_nein': int((~d & h).sum())"),
    ('nan-als-nein', "    if not (np.isin(d, [0, 1]).all() and np.isin(h, [0, 1]).all()):", "    d, h = np.nan_to_num(d), np.nan_to_num(h)\n    if not (np.isin(d, [0, 1]).all() and np.isin(h, [0, 1]).all()):"),
    ('laengstes-ist-kuerzestes', "min(scenarios, key=lambda s: s['stopp_index']), max(scenarios, key=lambda s: s['stopp_index'])",
     "min(scenarios, key=lambda s: s['stopp_index']), min(scenarios, key=lambda s: s['stopp_index'])"),
    ('szenario-nach-konfigreihenfolge', "min(scenarios, key=lambda s: s['stopp_index']), max(scenarios, key=lambda s: s['stopp_index'])",
     "scenarios[0], scenarios[1]"),
    ('treffer-ab-null', "infrastructure_counts[t]['anzahl'] > 0", "infrastructure_counts[t]['anzahl'] >= 0"),
    ('dem-datum-einschliesslich', "d.t_start_utc > pd.Timestamp(dem_last_modified_utc)", "d.t_start_utc >= pd.Timestamp(dem_last_modified_utc)"),
    ('ohne-lagefilter', "lambda d: d.QUAL_LAGE.isin(ev_cfg['position_classes_allowed'])", "lambda d: pd.Series(True, d.index)"),
    ('ohne-jahresfilter', "d.EREIGNIS_J.isin(years) if years is not None", "pd.Series(True, d.index) if years is not None"),
    ('schadensdetail-leer-erlaubt', "d[ev_cfg['damage_fields_required']].notna().all(axis=1)", "d[ev_cfg['damage_fields_required']].notna().any(axis=1)"),
    ('umkreis-in-grad', "distance_m=core.distance_m(x, y, cx_m, cy_m)", "distance_m=core.distance_m(x, y, cx_m, cy_m) / 111_000"),
    ('doppelte-ids-erlaubt', "    if f.nameOfEvent.duplicated().any():", "    if False:"),
    ('falsches-schadensfeld', "damage = [r['schaden'][spec['damage_field']] for r in rows]", "damage = [r['schaden']['Bauwerke'] for r in rows]"),
    ('schreibschutz-aus', "    if os.path.basename(path) != 'wirkungskette_v02' or", "    if False and os.path.basename(path) != 'wirkungskette_v02' or"),
]

rows = []
orig = TARGET.read_bytes()
try:
    for name, old, new in MUT:
        text = orig.decode('utf-8')
        assert text.count(old) == 1, name
        TARGET.write_bytes(text.replace(old, new, 1).encode('utf-8'))
        r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', TESTS], capture_output=True, text=True)
        last = [line for line in r.stdout.splitlines() if 'passed' in line or 'failed' in line or 'error' in line][-1:]
        rows.append({'mutation': name, 'ergebnis': last[0] if last else r.stdout[-200:], 'gescheitert': r.returncode != 0})
        TARGET.write_bytes(orig)
finally:
    TARGET.write_bytes(orig)
out = Path('reports/wirkungskette_v02')
out.mkdir(parents=True, exist_ok=True)
(out / 'mutation_tests.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps(rows, indent=1, ensure_ascii=False))
if not all(r['gescheitert'] for r in rows):
    sys.exit('Mindestens eine Mutation wurde von keinem Test erkannt')
