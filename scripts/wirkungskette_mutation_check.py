"""Inject one bug at a time into preslide/wirkungskette, run the guarding tests, restore. Prints a table."""
import subprocess, sys, json
from pathlib import Path
MUT = [
 ('radius', 'core.py', "if not math.isfinite(radius_m) or not r['min'] <= radius_m <= r['max']:", "if not math.isfinite(radius_m) or not r['min'] <= radius_m <= 2 * r['max']:", 'radius'),
 ('grad-distanz', 'core.py', "    if x.size and (np.nanmax(np.abs(x)) < 1000 or np.nanmax(np.abs(y)) < 1000):", "    if False:", 'degree'),
 ('d8-steigt', 'core.py', "            if drop > best:", "            if drop > best or (nxt is not None and drop > -0.5 and drop < best and False) or (drop < 0 and nxt is None and np.isfinite(ns)):", 'd8_route_descends or end_reasons'),
 ('nodata-als-rand', 'core.py', "            return np.array(path_r), np.array(path_c), 'nodata'", "            return np.array(path_r), np.array(path_c), 'rand'", 'end_reasons'),
 ('rand-als-stopp', 'core.py', "    return {'stop_index': len(z) - 1, 'status': _unfinished(route_end), 'energy_height_m': (z + h).tolist()}", "    return {'stop_index': len(z) - 1, 'status': 'gestoppt', 'energy_height_m': (z + h).tolist()}", 'border_exit'),
 ('energie-ohne-deckel', 'core.py', "        h[i] = min(h[i - 1] + (z[i - 1] - z[i]) - (s[i] - s[i - 1]) * tan_a, cap)", "        h[i] = h[i - 1] + (z[i - 1] - z[i]) - (s[i] - s[i - 1]) * tan_a", 'energy_line_stops'),
 ('korridor-volle-breite', 'core.py', "    return geom.buffer(width_m / 2)", "    return geom.buffer(width_m)", 'corridor_counts'),
 ('verbotene-woerter', 'core.py', "BANNED = re.compile(r'wahrscheinlich|risiko|risk|probab|gefährd|gefaehrd', re.IGNORECASE)", "BANNED = re.compile(r'xyzxyz', re.IGNORECASE)", 'banned_words'),
 ('cache-identitaet', 'store.py', "    if meta['identity'] != identity:", "    if False:", 'checkpoint_refuses'),
 ('identitaet-ohne-terrain', 'build.py', "    return store.identity({'demo': cfg['demo'], 'terrain': cfg['terrain'], 'radius_max_m': float(radius_max_m), 'algorithm': 1})", "    return store.identity({'demo': cfg['demo'], 'radius_max_m': float(radius_max_m), 'algorithm': 1})", 'relevant_config_change'),
 ('stufen-absolut', 'core.py', "    frac[order] = (np.arange(n) + 1) / n", "    frac[order] = (np.arange(n) + 1) / n\n    frac = np.clip(1 - (score - score.min()) / (np.ptp(score) + 1e-12), 1e-9, 1)", 'review_classes'),
]
rows = []
for name, f, old, new, k in MUT:
    p = Path('preslide/wirkungskette') / f
    orig = p.read_bytes()
    t = orig.decode('utf-8')
    assert old in t, name
    p.write_bytes(t.replace(old, new, 1).encode('utf-8'))
    try:
        r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests/test_wirkungskette.py', '-k', k], capture_output=True, text=True)
        last = [l for l in r.stdout.splitlines() if 'passed' in l or 'failed' in l or 'error' in l][-1:]
        rows.append({'mutation': name, 'tests': k, 'ergebnis': last[0] if last else r.stdout[-200:], 'gescheitert': r.returncode != 0})
    finally:
        p.write_bytes(orig)
print(json.dumps(rows, indent=1, ensure_ascii=False))
