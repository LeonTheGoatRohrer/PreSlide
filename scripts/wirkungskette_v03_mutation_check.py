"""Inject one bug at a time into preslide/wirkungskette/nullreferenz.py, run the guarding tests, restore.

Writes reports/wirkungskette_v03/mutation_tests.json. Every mutation must make at least one test fail."""
import json
import subprocess
import sys
from pathlib import Path

TARGET = Path('preslide/wirkungskette/nullreferenz.py')
TESTS = 'tests/test_wirkungskette_v03.py'
MUT = [
    ('puffer-strikt', "inside = cells[d_event <= buffer_m]", "inside = cells[d_event < buffer_m]"),
    ('inventarabstand-aus', "keep = d_inv >= min_distance_m", "keep = d_inv >= 0"),
    ('inventarabstand-strikt', "keep = d_inv >= min_distance_m", "keep = d_inv > min_distance_m"),
    ('am-punkt-strikt', "int(row['naechstes_objekt_m'][typ] <= half_width_m)", "int(row['naechstes_objekt_m'][typ] < half_width_m)"),
    ('laengstes-fuer-beide', "G.present(row['szenario'][which]['infrastruktur'], [typ])", "G.present(row['szenario']['laengstes']['infrastruktur'], [typ])"),
    ('einheitenanteile-ungewichtet', "shares = [k_hits[list(c)].sum() / k_n[list(c)].sum() for c",
     "shares = [np.mean(k_hits[list(c)] / k_n[list(c)]) for c"),
    ('zeilen-statt-einheiten', "keys = sorted(set(u.tolist()))", "u = np.arange(len(u)).astype(object)\n    keys = list(range(len(u)))"),
    ('seed-ignoriert', "idx = np.random.default_rng(seed).choice(", "idx = np.random.default_rng().choice("),
    ('ohne-sortierung', "ordered = cells.sort_values(['row', 'col']).reset_index(drop=True)", "ordered = cells.reset_index(drop=True)"),
    ('block-100-m', "def block_id(x_m, y_m, block_m=1000.0):", "def block_id(x_m, y_m, block_m=100.0):"),
    ('falsche-gruppe', "'verkehr_1': ('Verkehrsanlagen', 1)", "'verkehr_1': ('Bauwerke', 1)"),
    ('primaerpaarung-vertauscht', "{('verkehr_1', m) for m in METRICS if m.startswith('strasse')}", "{('verkehr_1', m) for m in METRICS if m.startswith('gebaeude')}"),
    ('null-als-ueber', "    if lo > 0:", "    if lo >= 0:"),
    ('differenz-vorzeichen', "'differenz': round(e['anteil'] - r['anteil'], 3)", "'differenz': round(r['anteil'] - e['anteil'], 3)"),
    ('v02-pruefung-aus', "            if r[key] != o[key]:", "            if False:"),
    ('flache-zellen-im-hangrahmen', "        return grid[grid.reason == '']", "        return grid"),
    ('schreibschutz-aus', "    if os.path.basename(path) != 'wirkungskette_v03' or", "    if False and os.path.basename(path) != 'wirkungskette_v03' or"),
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
out = Path('reports/wirkungskette_v03')
out.mkdir(parents=True, exist_ok=True)
(out / 'mutation_tests.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps(rows, indent=1, ensure_ascii=False))
if not all(r['gescheitert'] for r in rows):
    sys.exit('Mindestens eine Mutation wurde von keinem Test erkannt')
