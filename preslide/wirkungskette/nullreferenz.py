"""wirkungskette_v03: null reference for the v02 Gegenprobe.

Registered in config/wirkungskette_v03.json before any reference point was sampled. Question: how often would a slope
point near the v02 events that is NOT an inventory event have a road or building in the shortest/longest unchanged v01
runout scenario, or within 25 m of the point? Same chain, same hit rule, same context rule as v02. Exploratory; no hit
rate, no validation. Event intervals respect the ~3 independent units (exact cluster bootstrap); reference intervals use
a 1 km block bootstrap.
"""
import itertools
import math
import os

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.ops import unary_union

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT
from . import analysis, core
from . import gegenprobe as G
from .audit import inventory
from .paths import config_sha

CONFIG = ROOT / 'config/wirkungskette_v03.json'
REPORT = ROOT / 'reports/wirkungskette_v03'
V02_NUMBERS = ROOT / 'reports/wirkungskette_v02/gegenprobe.json'
METRICS = ('strasse_kuerzestes', 'strasse_laengstes', 'strasse_am_punkt', 'gebaeude_kuerzestes', 'gebaeude_laengstes', 'gebaeude_am_punkt')
GROUPS = {'verkehr_1': ('Verkehrsanlagen', 1), 'bauwerke_1': ('Bauwerke', 1), 'alle': None}
MAX_EXACT_UNITS = 7


def config():
    return read_json(CONFIG)


def report_dir():
    """Create and return reports/wirkungskette_v03; nothing else is written by this module."""
    path = os.path.abspath(REPORT)
    if os.path.basename(path) != 'wirkungskette_v03' or os.path.abspath(ROOT / 'reports') != os.path.dirname(path):
        raise RuntimeError(f'wirkungskette_v03 may only write under reports/wirkungskette_v03: {path}')
    os.makedirs(path, exist_ok=True)
    return REPORT


# ---------- pure parts: area, eligibility, sampling ----------

def area_geometry(event_x_m, event_y_m, buffer_m, window_cx_m, window_cy_m, window_radius_m):
    """Amended reference area (amendment 1): union of `buffer_m` buffers around the events, and its part inside the window."""
    core.assert_projected(event_x_m, event_y_m)
    union = unary_union([Point(float(a), float(b)).buffer(buffer_m, 64) for a, b in zip(event_x_m, event_y_m)])
    inside = union.intersection(Point(window_cx_m, window_cy_m).buffer(window_radius_m, 256))
    return {'flaeche_km2': round(union.area / 1e6, 2), 'im_fenster_km2': round(inside.area / 1e6, 2),
            'anteil_ausserhalb_fenster': round(1 - inside.area / union.area, 3)}


def frame_cells(cells, frame_id):
    """Grid cells of one registered frame: 'bewertbar' (reason == '') or 'alle_rasterzellen' (any reason)."""
    grid = cells[cells.kind == 'grid']
    if frame_id == 'bewertbar':
        return grid[grid.reason == '']
    if frame_id == 'alle_rasterzellen':
        return grid
    raise ValueError(f'Unbekannter Referenzrahmen: {frame_id}')


def _nearest_m(px_m, py_m, qx_m, qy_m):
    """Distance (m) from each query point to the nearest of the points (KD-tree on EPSG:31287 metres)."""
    if len(px_m) == 0:
        raise ValueError('Leere Punktmenge: Abstand nicht prüfbar')
    core.assert_projected(px_m, py_m)
    tree = cKDTree(np.column_stack([np.asarray(px_m, float), np.asarray(py_m, float)]))
    return tree.query(np.column_stack([np.asarray(qx_m, float), np.asarray(qy_m, float)]), k=1)[0]


def eligible(cells, event_x_m, event_y_m, buffer_m, inventory_x_m, inventory_y_m, min_distance_m):
    """Cells within `buffer_m` of at least one event and at least `min_distance_m` from every inventory point.

    All coordinates are metres in EPSG:31287. Returns the cells and counts by reason."""
    d_event = _nearest_m(event_x_m, event_y_m, cells.x.to_numpy(), cells.y.to_numpy())
    inside = cells[d_event <= buffer_m]
    d_inv = _nearest_m(inventory_x_m, inventory_y_m, inside.x.to_numpy(), inside.y.to_numpy())
    keep = d_inv >= min_distance_m
    out = inside[keep].assign(inventar_abstand_m=d_inv[keep])
    counts = {'zellen_im_rahmen': int(len(cells)), 'im_gebiet': int(len(inside)),
              'zu_nah_am_inventar': int((~keep).sum()), 'zulaessig': int(len(out))}
    return out, counts


def sample(cells, n, seed):
    """Fixed-seed draw without replacement from cells sorted by (row, col); all cells if fewer than n."""
    ordered = cells.sort_values(['row', 'col']).reset_index(drop=True)
    if ordered[['row', 'col']].duplicated().any():
        raise ValueError('Doppelte Rasterzellen im Referenzrahmen')
    if len(ordered) <= n:
        return ordered
    idx = np.random.default_rng(seed).choice(len(ordered), size=n, replace=False)
    return ordered.iloc[np.sort(idx)].reset_index(drop=True)


def block_id(x_m, y_m, block_m=1000.0):
    """1 km x 1 km block key in EPSG:31287."""
    core.assert_projected(x_m, y_m)
    return [f'{int(math.floor(a / block_m))}_{int(math.floor(b / block_m))}' for a, b in zip(x_m, y_m)]


# ---------- pure parts: metrics ----------

def point_metrics(row, half_width_m):
    """Six registered 0/1 metrics from a row with 'szenario' (kuerzestes/laengstes infrastructure) and 'naechstes_objekt_m'."""
    out = {}
    for typ in ('strasse', 'gebaeude'):
        for which in ('kuerzestes', 'laengstes'):
            out[f'{typ}_{which}'] = int(G.present(row['szenario'][which]['infrastruktur'], [typ]))
        out[f'{typ}_am_punkt'] = int(row['naechstes_objekt_m'][typ] <= half_width_m)
    return out


def group_mask(rows, group):
    spec = GROUPS[group]
    if spec is None:
        return [True] * len(rows)
    field, value = spec
    return [r['schaden'][field] == value for r in rows]


# ---------- pure parts: resampling ----------

def _check_binary(hits):
    h = np.asarray(hits, float)
    if h.ndim != 1 or not np.isin(h, [0, 1]).all():
        raise ValueError('Treffer müssen ein 0/1-Vektor ohne fehlende Werte sein')
    return h


def weighted_quantile(values, weights, q):
    """Smallest value whose cumulative weight reaches q (inverted CDF of a discrete distribution)."""
    v, w = np.asarray(values, float), np.asarray(weights, float)
    order = np.argsort(v, kind='stable')
    v, cw = v[order], np.cumsum(w[order]) / w.sum()
    return float(v[np.searchsorted(cw, q - 1e-12, side='left')])


def unit_totals(hits, units):
    """Per-unit (hits, n) in sorted unit order."""
    h = _check_binary(hits)
    u = np.asarray(units, object)
    if u.shape != h.shape:
        raise ValueError('Treffer und Einheiten müssen gleich lang sein')
    keys = sorted(set(u.tolist()))
    return keys, np.array([h[u == k].sum() for k in keys]), np.array([(u == k).sum() for k in keys], float)


def cluster_bootstrap_exact(hits, units):
    """All k^k ordered resamples of the k units with equal weight; share = pooled hits / pooled n."""
    keys, k_hits, k_n = unit_totals(hits, units)
    k = len(keys)
    if k == 0:
        raise ValueError('Keine Einheiten')
    if k > MAX_EXACT_UNITS:
        raise ValueError(f'Exakte Aufzählung nur bis {MAX_EXACT_UNITS} Einheiten')
    shares = [k_hits[list(c)].sum() / k_n[list(c)].sum() for c in itertools.product(range(k), repeat=k)]
    return np.array(shares)


def cluster_interval(hits, units):
    shares = cluster_bootstrap_exact(hits, units)
    w = np.ones(len(shares))
    return {'einheiten': len(set(units)), 'resamples': int(len(shares)),
            'intervall_95': [round(weighted_quantile(shares, w, 0.025), 3), round(weighted_quantile(shares, w, 0.975), 3)],
            'min_max': [round(float(shares.min()), 3), round(float(shares.max()), 3)]}


def block_draws(hits, blocks, draws, rng):
    """Block bootstrap shares: resample blocks with replacement, pooled hits / pooled n."""
    _, b_hits, b_n = unit_totals(hits, blocks)
    idx = rng.integers(0, len(b_n), size=(draws, len(b_n)))
    return b_hits[idx].sum(axis=1) / b_n[idx].sum(axis=1)


def cluster_draws(hits, units, draws, rng):
    """Random cluster bootstrap shares (used for the joint difference draws)."""
    _, k_hits, k_n = unit_totals(hits, units)
    idx = rng.integers(0, len(k_n), size=(draws, len(k_n)))
    return k_hits[idx].sum(axis=1) / k_n[idx].sum(axis=1)


def percentile_interval(draws):
    return [round(float(np.quantile(draws, 0.025)), 3), round(float(np.quantile(draws, 0.975)), 3)]


def wording(interval):
    lo, hi = interval
    if lo > 0:
        return 'über der Nullreferenz'
    if hi < 0:
        return 'unter der Nullreferenz'
    return 'nicht von der Nullreferenz unterscheidbar'


def share(hits):
    h = _check_binary(hits)
    return {'treffer': int(h.sum()), 'n': int(h.size), 'anteil': round(float(h.mean()), 3) if h.size else None}


def comparisons(event_rows, ref_frames, cfg):
    """All registered comparisons (24): event share, reference share, difference with intervals and wording."""
    draws, seed = 2000, cfg['reference']['seed']
    primary_pairs = {('verkehr_1', m) for m in METRICS if m.startswith('strasse')} | {('bauwerke_1', m) for m in METRICS if m.startswith('gebaeude')}
    specs = []
    for frame in ref_frames:
        for group, metric in sorted(primary_pairs, key=lambda p: METRICS.index(p[1])):
            specs.append((frame, group, metric, 'primaer' if frame == 'bewertbar' else 'sekundaer'))
    for frame in ref_frames:
        specs += [(frame, 'alle', m, 'sekundaer') for m in METRICS]
    if len(specs) != cfg['comparisons']['comparisons_counted']:
        raise ValueError(f'{len(specs)} Vergleiche statt der registrierten {cfg["comparisons"]["comparisons_counted"]}')
    out = []
    for i, (frame, group, metric, rank) in enumerate(specs):
        mask = group_mask(event_rows, group)
        ev = [r for r, m in zip(event_rows, mask) if m]
        e_hits = [r['metriken'][metric] for r in ev]
        e_units = [r['einheit'] for r in ev]
        refs = ref_frames[frame]
        r_hits = [r['metriken'][metric] for r in refs]
        r_blocks = [r['block'] for r in refs]
        rng = np.random.default_rng([seed, i])
        r_boot = block_draws(r_hits, r_blocks, draws, rng)
        rng_d = np.random.default_rng([seed + 1, i])
        diff = cluster_draws(e_hits, e_units, draws, rng_d) - block_draws(r_hits, r_blocks, draws, rng_d)
        e, r = share(e_hits), share(r_hits)
        d_int = percentile_interval(diff)
        out.append({'rang': rank, 'rahmen': frame, 'gruppe': group, 'metrik': metric,
                    'ereignisse': {**e, **cluster_interval(e_hits, e_units)},
                    'referenz': {**r, 'bloecke': len(set(r_blocks)), 'intervall_95': percentile_interval(r_boot)},
                    'differenz': round(e['anteil'] - r['anteil'], 3), 'differenz_intervall_95': d_int,
                    'einordnung': wording(d_int)})
    return out


# ---------- data-dependent parts ----------

def _unit(ev):
    return ev.RegKatE_ID if not pd.isna(ev.RegKatE_ID) else f'ohne Kampagne {ev.Ereignisdatum[:7]}'


def check_against_v02(rows, v02):
    """Recomputed event rows must equal the committed v02 numbers (ids, scenario counts, nearest objects)."""
    if v02['identitaet']['konfiguration_v01_sha256'] != config_sha():
        raise ValueError('v01-Konfiguration weicht vom v02-Bericht ab')
    old = {r['id']: r for r in v02['sets']['primaer']['zeilen']}
    if sorted(old) != sorted(r['id'] for r in rows):
        raise ValueError('Primärset weicht vom v02-Bericht ab')
    for r in rows:
        o = old[r['id']]
        for key in ('szenario', 'naechstes_objekt_m', 'schaden'):
            if r[key] != o[key]:
                raise ValueError(f'Ereignis {r["id"]}: {key} weicht vom v02-Bericht ab')


def event_rows(w, raw, cx, cy, v02_cfg, dem_utc, half_width_m):
    ev_cfg = v02_cfg['events']
    sel, _ = G.select_events(raw, cx, cy, ev_cfg, dem_utc, ev_cfg['primary_years'])
    dist = G.nearest_m(w)
    rows = []
    for ev in sel.itertuples():
        r = G.event_row(w, ev, dist)
        rows.append({**r, 'x_m': float(ev.x_m), 'y_m': float(ev.y_m), 'einheit': _unit(ev), 'metriken': point_metrics(r, half_width_m)})
    return rows, dist


def reference_row(w, cell, i, dist, half_width_m):
    ch = analysis.scenario_chain(w, {'id': f'R{i + 1}', 'x': float(cell.x), 'y': float(cell.y)})
    short, long_ = G.shortest_and_longest(ch['szenarien'])
    keep = ('id', 'status', 'laenge_m', 'infrastruktur')
    r = {'id': f'R{i + 1}', 'row': int(cell.row), 'col': int(cell.col), 'lage': [round(float(cell.longitude), 6), round(float(cell.latitude), 6)],
         'neigung_grad': round(float(cell.slope), 1), 'grund': cell.reason, 'inventar_abstand_m': round(float(cell.inventar_abstand_m), 1),
         'route_ende': ch['route']['ende'],
         'szenario': {'kuerzestes': {k: short[k] for k in keep}, 'laengstes': {k: long_[k] for k in keep}},
         'naechstes_objekt_m': dist(float(cell.x), float(cell.y))}
    r['metriken'] = point_metrics(r, half_width_m)
    return r


def run(limit=None):
    """Full registered run; `limit` (pilot only) caps the reference points per frame and writes nothing."""
    cfg = config()
    v02_cfg = G.config()
    ref = cfg['reference']
    radius_max_m = float(cfg['chain']['window_radius_max_m'])
    w = analysis.window(radius_max_m)
    dem_utc = G.dem_last_modified(radius_max_m)
    d = w['cfg']['demo']
    sx, sy = PROJECT.transform(d['centre_longitude'], d['centre_latitude'])
    half_width_m = w['cfg']['runout']['corridor']['width_m'] / 2
    raw = inventory()
    events, dist = event_rows(w, raw, sx, sy, v02_cfg, dem_utc, half_width_m)
    check_against_v02(events, read_json(V02_NUMBERS))
    ex, ey = [e['x_m'] for e in events], [e['y_m'] for e in events]
    buffer_m = float(ref['area_amended']['buffer_m'])
    ix, iy = PROJECT.transform(raw.lon.to_numpy(), raw.lat.to_numpy())
    frames, selection = {}, {}
    for fr in ref['frames']:
        cells, counts = eligible(frame_cells(w['cells'], fr['id']), ex, ey, buffer_m, ix, iy, ref['exclusion']['min_distance_m'])
        drawn = sample(cells, ref['sample_size'], ref['seed'])
        if limit is not None:
            drawn = drawn.head(limit)
        blocks = block_id(drawn.x.to_numpy(), drawn.y.to_numpy())
        rows = []
        for i, cell in enumerate(drawn.itertuples()):
            r = reference_row(w, cell, i, dist, half_width_m)
            r['block'] = blocks[i]
            rows.append(r)
        frames[fr['id']] = rows
        selection[fr['id']] = {**counts, 'gezogen': len(rows), 'bloecke': len(set(blocks)),
                               'nach_grund': drawn.reason.replace('', 'bewertbar').value_counts().to_dict(),
                               'route_ende': pd.Series([r['route_ende'] for r in rows]).value_counts().to_dict(),
                               'kuerzestes_laenge_0_m': sum(r['szenario']['kuerzestes']['laenge_m'] == 0 for r in rows),
                               'median_naechste_strasse_m': round(float(np.median([r['naechstes_objekt_m']['strasse'] for r in rows])), 1),
                               'median_naechstes_gebaeude_m': round(float(np.median([r['naechstes_objekt_m']['gebaeude'] for r in rows])), 1)}
    out = {'version': cfg['version'], 'registrierung': 'config/wirkungskette_v03.json', 'explorativ': True,
           'identitaet': {'konfiguration_v01_sha256': config_sha(), 'kette': cfg['chain']['function'],
                          'v02_zahlen': 'reports/wirkungskette_v02/gegenprobe.json (nachgerechnet und gleich)'},
           'korridor_halbbreite_m': half_width_m,
           'gebiet': {'regel': 'Änderung 1: Zellen höchstens Puffer vom nächsten Primärereignis', 'puffer_m': buffer_m,
                      **area_geometry(ex, ey, buffer_m, sx, sy, radius_max_m)},
           'ereignisse': {'n': len(events), 'einheiten': pd.Series([e['einheit'] for e in events]).value_counts().to_dict(),
                          'median_naechste_strasse_m': round(float(np.median([e['naechstes_objekt_m']['strasse'] for e in events])), 1),
                          'median_naechstes_gebaeude_m': round(float(np.median([e['naechstes_objekt_m']['gebaeude'] for e in events])), 1),
                          'zeilen': [{'id': e['id'], 'einheit': e['einheit'], 'schaden': e['schaden'], 'metriken': e['metriken']} for e in events]},
           'referenz': selection, 'vergleiche': comparisons(events, frames, cfg),
           'referenz_zeilen': frames}
    if limit is not None:
        return out
    write_json(report_dir() / 'nullreferenz.json', out)
    text = render(out, cfg)
    bad = core.BANNED.findall(text)
    if bad:
        raise RuntimeError(f'Unzulässige Formulierung im Bericht: {bad[:3]}')
    (REPORT / 'nullreferenz.md').write_bytes(text.encode('utf-8'))
    return out


# ---------- report ----------

METRIC_DE = {'strasse_kuerzestes': 'Straße im kürzesten Szenario', 'strasse_laengstes': 'Straße im längsten Szenario',
             'strasse_am_punkt': 'Straße ≤ 25 m vom Punkt', 'gebaeude_kuerzestes': 'Gebäude im kürzesten Szenario',
             'gebaeude_laengstes': 'Gebäude im längsten Szenario', 'gebaeude_am_punkt': 'Gebäude ≤ 25 m vom Punkt'}
GROUP_DE = {'verkehr_1': 'Verkehrsanlagen = 1', 'bauwerke_1': 'Bauwerke = 1', 'alle': 'alle Primärereignisse'}
FRAME_DE = {'bewertbar': 'bewertbare Hangzellen', 'alle_rasterzellen': 'alle Rasterzellen'}


def _iv(v):
    return f'[{v[0]:.2f}; {v[1]:.2f}]'


def _comparison_table(rows):
    lines = ['| Merkmal | Ereignisgruppe | Ereignisse | Referenz | Differenz | Einordnung |', '|---|---|---|---|---|---|']
    for c in rows:
        e, r = c['ereignisse'], c['referenz']
        lines.append(f"| {METRIC_DE[c['metrik']]} | {GROUP_DE[c['gruppe']]} | {e['treffer']}/{e['n']} = {e['anteil']:.2f} {_iv(e['intervall_95'])} | "
                     f"{r['treffer']}/{r['n']} = {r['anteil']:.2f} {_iv(r['intervall_95'])} | {c['differenz']:+.2f} {_iv(c['differenz_intervall_95'])} | {c['einordnung']} |")
    return lines + ['']


def findings(out):
    """Result sentences from the primary comparisons only (no hand-copied numbers)."""
    p = {c['metrik']: c for c in out['vergleiche'] if c['rang'] == 'primaer'}
    s = {(c['rahmen'], c['gruppe'], c['metrik']): c for c in out['vergleiche']}
    hw = out['korridor_halbbreite_m']

    def f(c, side):
        x = c[side]
        return f"{x['treffer']}/{x['n']} ({x['anteil']:.2f})"
    sl, sp, gl, gp = p['strasse_laengstes'], p['strasse_am_punkt'], p['gebaeude_laengstes'], p['gebaeude_am_punkt']
    ev_v = [e['metriken'] for e, m in zip(out['ereignisse']['zeilen'], group_mask(out['ereignisse']['zeilen'], 'verkehr_1')) if m]
    at_point = [e for e in ev_v if e['strasse_am_punkt']]
    off_point = [e for e in ev_v if not e['strasse_am_punkt']]
    a_sl = s[('alle_rasterzellen', 'verkehr_1', 'strasse_laengstes')]
    a_sp = s[('alle_rasterzellen', 'verkehr_1', 'strasse_am_punkt')]
    above = 'über der Nullreferenz'
    long_text = ('Die Übereinstimmung im längsten Szenario geht in diesen Einheiten über das hinaus, was Hangpunkte derselben Gegend zeigen.'
                 if sl['einordnung'] == above else
                 'Die Übereinstimmung im längsten Szenario ist damit nicht mehr als das, was Hangpunkte derselben Gegend ohnehin zeigen.')
    point_text = ('Die Inventarpunkte liegen in diesen Einheiten öfter direkt an einer Straße als Hangpunkte derselben Gegend. Das passt zu Punkten, '
                  'die an der Straße oder am Schadensort gesetzt wurden (Meldebezug), und sagt nichts über die Reichweite des Auslaufs.'
                  if sp['einordnung'] == above else
                  'Die Straßennähe der Inventarpunkte ist von der der Hangpunkte derselben Gegend nicht zu trennen.')
    return [
        '## Ergebnis (explorativ)', '',
        f"- **Straße im längsten Szenario.** Ereignisse mit Verkehrsanlagen = 1: {f(sl, 'ereignisse')}; bewertbare Referenz-Hangzellen: "
        f"{f(sl, 'referenz')}, Intervall {_iv(sl['referenz']['intervall_95'])}. Differenz {sl['differenz']:+.2f} {_iv(sl['differenz_intervall_95'])}: "
        f"{sl['einordnung']}. {long_text} Aufgeschlüsselt (beschreibend, kein eigener Vergleich): {sum(e['strasse_laengstes'] for e in at_point)} der "
        f"{len(at_point)} Ereignisse mit Straße am Punkt und {sum(e['strasse_laengstes'] for e in off_point)} der {len(off_point)} ohne Straße am Punkt "
        'haben eine Straße im längsten Szenario. Der Überschuss gegenüber der Referenz kommt damit aus den Ereignissen mit Straße schon am Punkt; '
        'über den Auslauf der Ereignisse ohne Straße am Punkt sagt der Vergleich bei so wenigen Fällen nichts.',
        f"- **Straße höchstens {hw:g} m vom Punkt.** Ereignisse: {f(sp, 'ereignisse')}; Referenz: {f(sp, 'referenz')}. "
        f"Differenz {sp['differenz']:+.2f} {_iv(sp['differenz_intervall_95'])}: {sp['einordnung']}. {point_text}",
        f"- Mit allen Rasterzellen (auch flache Talbodenzellen) als Referenz: Straße im längsten Szenario {f(a_sl, 'referenz')} "
        f"({a_sl['einordnung']}), Straße am Punkt {f(a_sp, 'referenz')} ({a_sp['einordnung']}).",
        f"- **Gebäude.** Ereignisse mit Bauwerke = 1: im längsten Szenario {f(gl, 'ereignisse')}, Referenz {f(gl, 'referenz')} "
        f"({gl['einordnung']}); Gebäude am Punkt {f(gp, 'ereignisse')} gegen {f(gp, 'referenz')} ({gp['einordnung']}). Nur {gl['ereignisse']['n']} Ereignisse.",
        f"- Die Ereignisintervalle beruhen auf sehr wenigen unabhängigen Einheiten: Verkehrsanlagen = 1 auf {sl['ereignisse']['einheiten']} "
        f"({sl['ereignisse']['resamples']} exakte Resamples), Bauwerke = 1 auf {gl['ereignisse']['einheiten']}, alle Primärereignisse auf "
        f"{len(out['ereignisse']['einheiten'])}. Die Intervalle sind grob und unterschätzen die Unsicherheit; wo alle Einheiten denselben Anteil haben, "
        'fällt das Intervall auf einen Punkt zusammen. Die Einordnung „über der Nullreferenz“ beschreibt daher nur diese Einheiten und ist kein belastbarer Befund.',
        '- Keine Trefferquote, keine Validierung des Auslaufs: Dass ein Szenario eine Straße überdeckt, heißt nicht, dass sie beschädigt würde, '
        'und Referenzzellen sind nur nicht im Inventar, nicht nachweislich stabil.', '']


def render(out, cfg):
    g, ref = out['gebiet'], out['referenz']
    hw = out['korridor_halbbreite_m']
    lines = ['# Wirkungskette v03 – Nullreferenz zur v02-Gegenprobe', '',
             f"Stand {cfg['created_on']}. Erzeugt von `python -m preslide.wirkungskette nullreferenz` aus der Registrierung "
             '`config/wirkungskette_v03.json` (vor dem Ziehen der Referenzpunkte festgelegt und committet). Zahlen: `nullreferenz.json`. '
             '**Explorativ.** Keine Trefferquote, keine Validierung; nichts wurde an den Ergebnissen angepasst.', '',
             '## Frage', '',
             'v02 fand: Bei 22/22 Ereignissen mit Verkehrsanlagen = 1 liegt eine Straße im längsten Auslaufszenario, bei 20/22 aber schon '
             f'höchstens {hw:g} m vom Inventarpunkt. Ohne Vergleich bleibt offen, ob das mehr ist als die Straßendichte der Gegend. '
             'Hier läuft dieselbe unveränderte v01-Kette (gleiche Szenarien, gleicher Korridor, gleiche Trefferregel, gleiche 25-m-Regel) '
             'für Hangpunkte derselben Gegend, die keine Inventarereignisse sind.', '',
             '## Referenzpunkte', '',
             f"- Gebiet (Änderung 1, vor jeder Auswertung festgehalten): Zellen höchstens {g['puffer_m']:g} m vom nächsten der "
             f"{out['ereignisse']['n']} v02-Primärereignisse, {g['flaeche_km2']:g} km², davon {g['im_fenster_km2']:g} km² im 10-km-Rechenfenster "
             f"(Anteil außerhalb {g['anteil_ausserhalb_fenster']:.0%}, dort gibt es keine Zellen). Die ursprünglich registrierte Regel "
             '(Kreis um den Schwerpunkt) ergab 7,4 km Radius, weil zwei Breitenauer Ereignisse 6–8 km westlich der Gasener Gruppe liegen; '
             'das wäre ein Drittel des Fensters gewesen, nicht dieselbe Gegend.',
             f"- Mindestabstand {cfg['reference']['exclusion']['min_distance_m']} m zu jedem Inventarpunkt (alle Prozesse, Jahre, Lageklassen).",
             f"- {cfg['reference']['sample_size']} Zellen je Rahmen, fester Seed {cfg['reference']['seed']}, ohne Zurücklegen.", '',
             '| Rahmen | Zellen im Gebiet | zu nah am Inventar | zulässig | gezogen | 1-km-Blöcke |', '|---|---:|---:|---:|---:|---:|']
    for fid, st in ref.items():
        lines.append(f"| {FRAME_DE[fid]} | {st['im_gebiet']} | {st['zu_nah_am_inventar']} | {st['zulaessig']} | {st['gezogen']} | {st['bloecke']} |")
    lines += ['', 'Unabhängige Einheiten der Ereignisse: ' + ', '.join(f'{k} ({v})' for k, v in out['ereignisse']['einheiten'].items()) + '.', '']
    lines += findings(out)
    lines += ['## Primäre Vergleiche (Referenz: bewertbare Hangzellen)', '',
              'Ereignisintervall: exakter Cluster-Bootstrap über die unabhängigen Einheiten. Referenzintervall: Block-Bootstrap über '
              '1-km-Blöcke (2000 Ziehungen). Differenz: Ereignisanteil minus Referenzanteil, gemeinsame Ziehungen. 95-%-Perzentilintervalle.', '']
    lines += _comparison_table([c for c in out['vergleiche'] if c['rang'] == 'primaer'])
    lines += ['## Sekundäre Vergleiche', '']
    for fid in ref:
        lines += [f'### Referenz: {FRAME_DE[fid]}', '']
        lines += _comparison_table([c for c in out['vergleiche'] if c['rang'] == 'sekundaer' and c['rahmen'] == fid])
    lines += ['## Beschreibung der Referenzpunkte', '',
              '| Rahmen | Routenende | kürzestes Szenario 0 m | Median nächste Straße (m) | Median nächstes Gebäude (m) |', '|---|---|---:|---:|---:|']
    for fid, st in ref.items():
        lines.append(f"| {FRAME_DE[fid]} | {', '.join(f'{k} {v}' for k, v in st['route_ende'].items())} | {st['kuerzestes_laenge_0_m']} | {st['median_naechste_strasse_m']:g} | {st['median_naechstes_gebaeude_m']:g} |")
    lines += [f"| Primärereignisse (v02) | – | – | {out['ereignisse']['median_naechste_strasse_m']:g} | {out['ereignisse']['median_naechstes_gebaeude_m']:g} |", '',
              '## Grenzen', '',
              '- Punktbezug unbekannt: Inventarpunkte können am Schadensort liegen, Referenzzellen sind Zellanker im Hang. Genau dieser Unterschied kann die Differenz erklären.',
              '- OpenStreetMap ist der heutige Stand (2026).',
              '- Drei unabhängige Ereigniseinheiten; jedes Intervall daraus ist grob.',
              '- Das Gebiet ist aus den Ereignislagen abgeleitet; es beschreibt die Infrastrukturdichte um diese Ereignisse, nicht in Österreich.',
              '- Referenzzellen sind nicht nachweislich stabil, nur nicht im Inventar (Pseudo-Negative).',
              f"- Gezählte Vergleiche: {len(out['vergleiche'])} (6 primär, 18 sekundär); alle sind oben berichtet.",
              f"- Kette und Regeln unverändert aus `config/wirkungskette_v01.json` (SHA-256 {out['identitaet']['konfiguration_v01_sha256'][:12]}…); "
              'v02-Ereigniszeilen wurden nachgerechnet und stimmen mit `reports/wirkungskette_v02/gegenprobe.json` überein.', '']
    return '\n'.join(lines)
