"""wirkungskette_v02: qualitative cross-check of the unvalidated v01 runout scenarios against inventory damage fields.

Registered in config/wirkungskette_v02.json before any chain output was computed. The v01 chain runs unchanged with the
inventory point as release point. Output: 2x2 tables (damage field ja/nein x infrastructure in scenario ja/nein); no hit
rate is claimed, because the inventory does not say whether the point marks release, path, deposit or damage site.
"""
import os

import numpy as np
import pandas as pd
from shapely import STRtree
from shapely.geometry import Point

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT
from . import analysis, core
from . import build as B
from .audit import inventory
from .paths import config_sha

CONFIG = ROOT / 'config/wirkungskette_v02.json'
REPORT = ROOT / 'reports/wirkungskette_v02'
CONTEXT_TYPES = ('strasse', 'gebaeude')


def config():
    return read_json(CONFIG)


def report_dir():
    """Create and return reports/wirkungskette_v02; nothing else is written by this module."""
    path = os.path.abspath(REPORT)
    if os.path.basename(path) != 'wirkungskette_v02' or os.path.abspath(ROOT / 'reports') != os.path.dirname(path):
        raise RuntimeError(f'wirkungskette_v02 may only write under reports/wirkungskette_v02: {path}')
    os.makedirs(path, exist_ok=True)
    return REPORT


# ---------- pure parts ----------

def select_events(frame, cx_m, cy_m, ev_cfg, dem_last_modified_utc, years=None):
    """Apply the registered selection in order; return (selected events, excluded counts by reason).

    Distances are metres in EPSG:31287. Event start Date_Anfan is epoch milliseconds (UTC) and must lie strictly after
    the DEM object date. `years` (EREIGNIS_J) restricts to the primary set; None keeps every year after the DEM."""
    x, y = PROJECT.transform(frame.lon.to_numpy(), frame.lat.to_numpy())
    f = frame.assign(x_m=x, y_m=y, distance_m=core.distance_m(x, y, cx_m, cy_m),
                     t_start_utc=pd.to_datetime(frame.Date_Anfan, unit='ms', utc=True))
    rules = [('ausserhalb_umkreis', lambda d: d.distance_m <= ev_cfg['radius_m']),
             ('schadensdetail_leer', lambda d: d[ev_cfg['damage_fields_required']].notna().all(axis=1)),
             ('ereignis_nicht_nach_dem', lambda d: d.t_start_utc > pd.Timestamp(dem_last_modified_utc)),
             ('jahr_nicht_im_primaerset', lambda d: d.EREIGNIS_J.isin(years) if years is not None else pd.Series(True, d.index)),
             ('prozess_ausgeschlossen', lambda d: ~d.Prozessgruppe.isin(ev_cfg['process_groups_excluded'])),
             ('lage_ungenauer_als_100m', lambda d: d.QUAL_LAGE.isin(ev_cfg['position_classes_allowed']))]
    excluded = {}
    for reason, rule in rules:
        keep = rule(f).to_numpy(bool)
        excluded[reason] = int((~keep).sum())
        f = f[keep]
    if f.nameOfEvent.duplicated().any():
        raise ValueError('Doppelte Ereignis-IDs in der Auswahl')
    for field in ev_cfg['damage_fields_required']:
        if not f[field].isin([0, 1]).all():
            raise ValueError(f'Schadensfeld {field} enthält Werte außer 0/1')
    return f.sort_values('nameOfEvent').reset_index(drop=True), excluded


def shortest_and_longest(scenarios):
    """Scenarios with the smallest and largest stop index along the route (ties: same corridor, first in config order)."""
    return min(scenarios, key=lambda s: s['stopp_index']), max(scenarios, key=lambda s: s['stopp_index'])


def present(infrastructure_counts, types):
    """True if at least one feature of any of `types` intersects the scenario corridor."""
    return any(infrastructure_counts[t]['anzahl'] > 0 for t in types)


def table_2x2(damage, hit):
    """Counts of damage field (ja/nein) against infrastructure in scenario (ja/nein). Both inputs strictly 0/1."""
    d, h = np.asarray(damage, float), np.asarray(hit, float)
    if d.ndim != 1 or d.shape != h.shape:
        raise ValueError('Schadensfeld und Treffer müssen gleich lange Vektoren sein')
    if not (np.isin(d, [0, 1]).all() and np.isin(h, [0, 1]).all()):
        raise ValueError('Nur 0/1 zulässig (keine fehlenden Werte)')
    d, h = d.astype(bool), h.astype(bool)
    return {'schaden_ja_szenario_ja': int((d & h).sum()), 'schaden_ja_szenario_nein': int((d & ~h).sum()),
            'schaden_nein_szenario_ja': int((~d & h).sum()), 'schaden_nein_szenario_nein': int((~d & ~h).sum()),
            'n': int(d.size)}


def tables(rows, comparison):
    """All registered tables for one event set: per table id and per scenario (kuerzestes/laengstes)."""
    out = {}
    for spec in comparison['primary_tables'] + comparison['secondary_tables']:
        damage = [r['schaden'][spec['damage_field']] for r in rows]
        out[spec['id']] = {'bezeichnung': spec['label'], 'rang': 'primaer' if spec in comparison['primary_tables'] else 'sekundaer',
                           'schadensfeld': spec['damage_field'], 'infrastruktur': spec['infrastructure_types']}
        for which in ('kuerzestes', 'laengstes'):
            hit = [int(present(r['szenario'][which]['infrastruktur'], spec['infrastructure_types'])) for r in rows]
            out[spec['id']][which] = table_2x2(damage, hit)
    return out


# ---------- data-dependent parts ----------

def dem_last_modified(radius_max_m):
    meta = read_json(B.paths(radius_max_m)['terrain'].with_name('terrain.npz.meta.json'))
    dates = {s['object_last_modified'] for s in meta['dem_sources']}
    if len(dates) != 1:
        raise ValueError(f'Erwartet genau eine DEM-Kachel, gefunden: {sorted(dates)}')
    return pd.Timestamp(dates.pop())


def nearest_m(w):
    """Function giving the distance (m) from a point to the nearest feature of each context type."""
    trees = {}
    for t in CONTEXT_TYPES:
        geoms = [f['geometry'] for f in w['features'] if f['typ'] == t]
        trees[t] = (STRtree(geoms), geoms)

    def dist(x_m, y_m):
        p = Point(x_m, y_m)
        return {t: round(float(geoms[int(tree.nearest(p))].distance(p)), 1) for t, (tree, geoms) in trees.items()}
    return dist


def event_row(w, ev, dist):
    ch = analysis.scenario_chain(w, {'id': ev.nameOfEvent, 'x': float(ev.x_m), 'y': float(ev.y_m)})
    short, long_ = shortest_and_longest(ch['szenarien'])
    keep = ('id', 'status', 'laenge_m', 'infrastruktur')
    return {'id': ev.nameOfEvent, 'datum': ev.Ereignisdatum, 'beginn_utc': ev.t_start_utc.isoformat(), 'jahr': int(ev.EREIGNIS_J),
            'gemeinde': ev.GEMEINDE, 'kampagne': None if pd.isna(ev.RegKatE_ID) else ev.RegKatE_ID,
            'prozess': f'{ev.Prozessgruppe} / {ev.Prozessuntergruppe}', 'lage': ev.QUAL_LAGE,
            'abstand_zentrum_m': round(float(ev.distance_m), 1),
            'schaden': {'Verkehrsanlagen': int(ev.Verkehrsanlagen), 'Bauwerke': int(ev.Bauwerke)},
            'route_ende': ch['route']['ende'], 'route_laenge_m': ch['route']['laenge_m'],
            'einzugsgebiet_unvollstaendig': ch['anriss']['einzugsgebiet_unvollstaendig'],
            'szenario': {'kuerzestes': {k: short[k] for k in keep}, 'laengstes': {k: long_[k] for k in keep}},
            'alle_szenarien': [{k: s[k] for k in keep} for s in ch['szenarien']],
            'naechstes_objekt_m': dist(float(ev.x_m), float(ev.y_m))}


def run():
    cfg = config()
    ev_cfg, cmp_cfg = cfg['events'], cfg['comparison']
    radius_max_m = float(cfg['chain']['window_radius_max_m'])
    w = analysis.window(radius_max_m)
    dem_utc = dem_last_modified(radius_max_m)
    if dem_utc != pd.Timestamp(ev_cfg['dem_object_last_modified_utc']):
        raise ValueError(f'DEM-Objektdatum {dem_utc} weicht von der Registrierung ab')
    d = w['cfg']['demo']
    cx, cy = PROJECT.transform(d['centre_longitude'], d['centre_latitude'])
    raw = inventory()
    dist = nearest_m(w)
    half_width_m = w['cfg']['runout']['corridor']['width_m'] / 2
    cache, sets = {}, {}
    for name, years in (('primaer', ev_cfg['primary_years']), ('sekundaer', None)):
        sel, excluded = select_events(raw, cx, cy, ev_cfg, dem_utc, years)
        rows = []
        for ev in sel.itertuples():
            if ev.nameOfEvent not in cache:
                cache[ev.nameOfEvent] = event_row(w, ev, dist)
            rows.append(cache[ev.nameOfEvent])
        sets[name] = {'ausgeschlossen_nach_grund': excluded, 'ereignisse': len(rows),
                      'nach_jahr': pd.Series([r['jahr'] for r in rows]).value_counts().sort_index().to_dict() if rows else {},
                      'nach_kampagne': pd.Series([r['kampagne'] or f"ohne Kampagne {r['datum'][:7]}" for r in rows]).value_counts().to_dict() if rows else {},
                      'kontext': context_counts(rows, half_width_m),
                      'tabellen': tables(rows, cmp_cfg), 'zeilen': rows}
    out = {'version': cfg['version'], 'registrierung': 'config/wirkungskette_v02.json',
           'identitaet': {'konfiguration_v01_sha256': config_sha(), 'kette': cfg['chain']['function'],
                          'dem_objektdatum_utc': dem_utc.isoformat()},
           'korridor_halbbreite_m': half_width_m, 'sets': sets}
    write_json(report_dir() / 'gegenprobe.json', out)
    text = render(out, cfg)
    bad = core.BANNED.findall(text)
    if bad:
        raise RuntimeError(f'Unzulässige Formulierung im Bericht: {bad[:3]}')
    (REPORT / 'gegenprobe.md').write_bytes(text.encode('utf-8'))
    return out


def context_counts(rows, half_width_m):
    """How often the nearest road/building already lies within the corridor half-width of the inventory point."""
    out = {}
    for field, typ in (('Verkehrsanlagen', 'strasse'), ('Bauwerke', 'gebaeude')):
        for value in (1, 0):
            sub = [r for r in rows if r['schaden'][field] == value]
            out[f'{field}_{value}_{typ}_am_punkt'] = {'n': len(sub), 'innerhalb_halbbreite': sum(r['naechstes_objekt_m'][typ] <= half_width_m for r in sub)}
    return out


# ---------- report ----------

def _table_md(t):
    return ('| | im Szenario ja | im Szenario nein |\n|---|---:|---:|\n'
            f"| Schadensfeld ja | {t['schaden_ja_szenario_ja']} | {t['schaden_ja_szenario_nein']} |\n"
            f"| Schadensfeld nein | {t['schaden_nein_szenario_ja']} | {t['schaden_nein_szenario_nein']} |\n")


def findings(st, half_width_m):
    """Result sentences for one event set, filled only from its counts (no hand-copied numbers)."""
    v, b = st['tabellen']['verkehr_strasse'], st['tabellen']['bauwerke_gebaeude']
    kv1, kv0, kb1 = (st['kontext'][k] for k in ('Verkehrsanlagen_1_strasse_am_punkt', 'Verkehrsanlagen_0_strasse_am_punkt',
                                                 'Bauwerke_1_gebaeude_am_punkt'))
    energy_zero = sum(r['szenario']['kuerzestes']['laenge_m'] == 0 for r in st['zeilen'])
    pos = pd.Series([r['lage'] for r in st['zeilen']]).value_counts().to_dict()

    def ja(t):
        return t['schaden_ja_szenario_ja'] + t['schaden_ja_szenario_nein']

    def nein(t):
        return t['schaden_nein_szenario_ja'] + t['schaden_nein_szenario_nein']
    return [
        '## Ergebnis (Primärset, qualitativ)', '',
        f"- **Verkehrsanlagen gegen Straße.** {ja(v['kuerzestes'])} von {v['kuerzestes']['n']} Ereignissen haben Verkehrsanlagen = 1. "
        f"Bei {v['kuerzestes']['schaden_ja_szenario_ja']} davon liegt eine Straße im kürzesten, bei {v['laengstes']['schaden_ja_szenario_ja']} im längsten Szenario. "
        f"Aber bei {kv1['innerhalb_halbbreite']} dieser {kv1['n']} Ereignisse liegt die nächste Straße schon höchstens {half_width_m:g} m vom Inventarpunkt entfernt. "
        'Die Übereinstimmung entsteht also am Startpunkt, nicht entlang des Auslaufs. Das passt dazu, dass die Punkte an der '
        'Straße oder am Schadensort gesetzt sein könnten; über die Reichweite des Szenarios sagt es nichts.',
        f"- Die Gegengruppe (Verkehrsanlagen = 0) hat nur {nein(v['kuerzestes'])} Ereignisse "
        f"({kv0['innerhalb_halbbreite']} davon mit Straße am Punkt; im längsten Szenario {v['laengstes']['schaden_nein_szenario_ja']} mit Straße). "
        'Damit kann die Tabelle nicht zwischen Ereignissen mit und ohne Straßenschaden unterscheiden.',
        f"- **Bauwerke gegen Gebäude.** {ja(b['kuerzestes'])} Ereignisse mit Bauwerke = 1: Gebäude im kürzesten Szenario bei "
        f"{b['kuerzestes']['schaden_ja_szenario_ja']}, im längsten bei {b['laengstes']['schaden_ja_szenario_ja']} "
        f"({kb1['innerhalb_halbbreite']} davon mit Gebäude schon am Punkt). {nein(b['kuerzestes'])} Ereignisse mit Bauwerke = 0: "
        f"Gebäude im kürzesten Szenario bei {b['kuerzestes']['schaden_nein_szenario_ja']}, im längsten bei {b['laengstes']['schaden_nein_szenario_ja']}. "
        'Das längste Szenario überdeckt also auch dort Gebäude, wo keine Gebäudeschäden gemeldet sind. Überlagerung ist keine '
        'Schadensaussage (Volumen, Schutzbauten, Bauweise fehlen), und das längste Szenario ist als obere Reichweite gedacht.',
        f"- **Kein Widerspruch, aber auch keine Bestätigung.** Im längsten Szenario gibt es {v['laengstes']['schaden_ja_szenario_nein']} "
        f"Straßenschäden und {b['laengstes']['schaden_ja_szenario_nein']} Gebäudeschäden ohne entsprechendes Objekt im Korridor. "
        'Weil die meisten Punkte schon an der Anlage liegen, ist dieses Fehlen von Widersprüchen nahezu zwangsläufig und keine Validierung des Auslaufs.',
        f"- Bei {energy_zero} Ereignissen endet das 11°-Energielinien-Szenario schon an der Startzelle (Länge 0 m): Das Gelände fällt dort zur nächsten "
        'Abwärtszelle flacher als 11° ab. Das spricht eher für eine Lage auf Straße oder Talboden als für einen Anriss im steilen Hang.',
        f"- Lagegenauigkeit der Punkte: {pos}. Die Unsicherheit von 20–100 m ist größer als die halbe Korridorbreite von {half_width_m:g} m.",
        '- Nicht berechnet, weil nicht registriert: eine Nullreferenz, wie oft ein beliebiger Hangpunkt derselben Gegend eine Straße '
        'im Korridor hätte. Ohne sie lässt sich nicht sagen, ob die Übereinstimmung über die Straßendichte hinausgeht.', '']


def render(out, cfg):
    p, s = out['sets']['primaer'], out['sets']['sekundaer']
    hw = out['korridor_halbbreite_m']
    lines = ['# Wirkungskette v02 – Gegenprobe des Auslaufszenarios mit Schadensmeldungen', '',
             f"Stand {cfg['created_on']}. Erzeugt von `python -m preslide.wirkungskette gegenprobe` aus der Registrierung "
             '`config/wirkungskette_v02.json` (vor jeder Kettenberechnung für diese Ereignisse festgelegt und committet). '
             'Zahlen: `gegenprobe.json`. Explorativ; nichts wurde an den Ergebnissen angepasst.', '',
             '## Wichtigste Einschränkung zuerst', '',
             'Das Inventar sagt nicht, ob ein Punkt den Anriss, die Transportbahn, die Ablagerung oder den Schadensort markiert. '
             'Hier wird der Punkt als Anriss gesetzt, weil die Kette einen Startpunkt braucht. Liegt der Punkt in Wahrheit am '
             'Schadensort, enthält schon der Korridor um den Startpunkt die beschädigte Anlage, und die Übereinstimmung sagt '
             'nichts über den Auslauf. **Deshalb wird keine Trefferquote behauptet.** Die Tabellen zeigen nur, ob Szenario und '
             'Schadensmeldung qualitativ zusammenpassen oder sich widersprechen.', '',
             '## Auswahl', '',
             f"Inventar im 10-km-Umkreis des Demozentrums, beide Schadensdetailfelder gesetzt, Ereignisbeginn nach dem DEM-Objektdatum "
             f"({out['identitaet']['dem_objektdatum_utc'][:10]}), keine Sturzprozesse, Lagegenauigkeit höchstens 100 m.", '',
             '| Ausschlussgrund (in dieser Reihenfolge) | Primärset 2017/2018 | Sekundärset alle Jahre nach DEM |', '|---|---:|---:|']
    for reason in p['ausgeschlossen_nach_grund']:
        lines.append(f"| {reason} | {p['ausgeschlossen_nach_grund'][reason]} | {s['ausgeschlossen_nach_grund'][reason]} |")
    lines += [f"| **verbleibend** | **{p['ereignisse']}** | **{s['ereignisse']}** |", '',
              f"Primärset nach Jahr: {p['nach_jahr']}; nach Kampagne: {p['nach_kampagne']}.", '',
              f"Sekundärset nach Jahr: {s['nach_jahr']}.", '',
              'Unabhängige Einheiten: Die Ereignisse eines Tages und eines Gebiets hängen voneinander ab (gleicher Niederschlag, '
              'oft gleiche Straße). Das Primärset besteht im Wesentlichen aus den Gasen-Kampagnen Juni und September 2018 plus '
              'einem Ereignis 2017, also etwa drei unabhängigen Einheiten, nicht so vielen wie Zeilen.', '']
    lines += findings(p, hw)
    for set_name, title, st in (('primaer', 'Primärset (2017/2018)', p), ('sekundaer', 'Sekundärset (alle Jahre nach dem DEM, gekennzeichnet sekundär)', s)):
        lines += [f'## {title}', '']
        for tid, t in st['tabellen'].items():
            lines += [f"### {t['bezeichnung']} ({t['rang']})", '',
                      f"Schadensfeld `{t['schadensfeld']}`; Infrastruktur im Szenario = OSM-Typ {', '.join(t['infrastruktur'])} schneidet den Korridor.", '',
                      'Kürzestes Szenario:', '', _table_md(t['kuerzestes']), 'Längstes Szenario:', '', _table_md(t['laengstes'])]
        lines += ['### Kontext: Objekt schon am Punkt', '',
                  f'Wie oft die nächste Straße bzw. das nächste Gebäude höchstens {hw:g} m (halbe Korridorbreite) vom Inventarpunkt entfernt '
                  'ist, also schon der Startkorridor sie enthält:', '',
                  '| Gruppe | Ereignisse | Objekt am Punkt |', '|---|---:|---:|']
        for k, v in st['kontext'].items():
            lines.append(f"| {k} | {v['n']} | {v['innerhalb_halbbreite']} |")
        lines += ['']
    lines += ['## Ereignisse des Primärsets', '',
              '| ID | Datum | Prozess | Lage | V | B | Route | kürzestes | längstes | Str. kurz/lang | Geb. kurz/lang | nächste Str./Geb. (m) |',
              '|---|---|---|---|---:|---:|---|---|---|---|---|---|']
    for r in p['zeilen']:
        k, lg = r['szenario']['kuerzestes'], r['szenario']['laengstes']
        lines.append(f"| {r['id']} | {r['datum']} | {r['prozess'].split(' / ')[1]} | {r['lage'].split('(')[-1].rstrip(')')} | "
                     f"{r['schaden']['Verkehrsanlagen']} | {r['schaden']['Bauwerke']} | {r['route_ende']} | "
                     f"{k['id']} {k['laenge_m']:g} m ({k['status']}) | {lg['id']} {lg['laenge_m']:g} m ({lg['status']}) | "
                     f"{k['infrastruktur']['strasse']['anzahl']}/{lg['infrastruktur']['strasse']['anzahl']} | "
                     f"{k['infrastruktur']['gebaeude']['anzahl']}/{lg['infrastruktur']['gebaeude']['anzahl']} | "
                     f"{r['naechstes_objekt_m']['strasse']:g} / {r['naechstes_objekt_m']['gebaeude']:g} |")
    lines += ['', 'V = Verkehrsanlagen, B = Bauwerke (1 = im Inventar gesetzt). Str./Geb. = Anzahl OSM-Objekte im Korridor.', '',
              '## Weitere Grenzen', '']
    lines += ['- Punktbezug unbekannt: Der Inventarpunkt kann Anriss, Transportbahn, Ablagerung oder Schadensort markieren.',
              '- OpenStreetMap ist der heutige Stand (2026), nicht der zum Ereignis; Objekte können jünger oder neu gebaut sein.',
              '- Das DEM-Objektdatum 26.04.2016 ist ein Upload-Datum; die zugrunde liegende Vermessung ist älter.',
              '- Verkehrsanlagen = 1 bei fast allen ausgewählten Ereignissen; die Nein-Zeile ist sehr klein.']
    lines += ['- Lagegenauigkeit 20–100 m bei den meisten Ereignissen ist größer als die halbe Korridorbreite; ein Treffer oder Fehlen '
              'kann allein an der Punktlage liegen.',
              '- Szenarien, Korridor und Infrastrukturtypen stammen unverändert aus `config/wirkungskette_v01.json` '
              f"(SHA-256 {out['identitaet']['konfiguration_v01_sha256'][:12]}…).",
              '- Gezählte Tabellen: 12 (2 primäre und 1 sekundäre Gegenüberstellung × kürzestes/längstes Szenario × Primär-/Sekundärset); '
              'alle sind oben berichtet.', '']
    return '\n'.join(lines)
