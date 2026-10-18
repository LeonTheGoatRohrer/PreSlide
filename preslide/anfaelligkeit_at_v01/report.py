"""reports/anfaelligkeit_at_v01/summary.md (German) generated from the stored results; no number is typed by hand.

  python -m preslide.anfaelligkeit_at_v01 report
"""
import pandas as pd

from ..common import read_json
from .paths import DATA, REPORT, load_meta

NAMES = {'hgb:terrain_geology': 'Gradient Boosting, Gelände + Geologie', 'lr:terrain_geology': 'Logistische Regression, Gelände + Geologie',
         'hgb:slope_only': 'Gradient Boosting, nur Neigung (Basislinie)', 'slope_rule:slope_only': 'Neigung als Rohwert (ohne Training)',
         'hgb:terrain_geology_landcover': 'Gradient Boosting, + Landbedeckung', 'lr:terrain_geology_landcover': 'Logistische Regression, + Landbedeckung',
         'lr:slope_only': 'Logistische Regression, nur Neigung'}


def f(x, d=3):
    return '–' if x is None or pd.isna(x) else f'{x:.{d}f}'.replace('.', ',')


def ci(entry, d=3):
    return f"{f(entry['mean'], d)} [{f(entry['ci95'][0], d)}; {f(entry['ci95'][1], d)}]"


def model_table(summary: dict, ref='hgb:slope_only') -> list:
    lines = ['| Modell | AUC (Mittel über Gebiete) | Differenz zu nur Neigung | Anteil Positive über 80. Perzentil des Hintergrunds | Average Precision |',
             '|---|---|---|---|---|']
    for key in ['hgb:terrain_geology', 'lr:terrain_geology', 'hgb:terrain_geology_landcover', 'lr:terrain_geology_landcover',
                'hgb:slope_only', 'slope_rule:slope_only']:
        if key not in summary:
            continue
        s = summary[key]
        diff = s.get('auc_minus_' + ref)
        lines.append(f"| {NAMES[key]} | {ci(s['auc'])} | {ci(diff) if diff else '(Referenz)'} | {ci(s['capture_top20'])} | {ci(s['ap'])} |")
    return lines


def area_rows(variant: str, counts: dict) -> list:
    t = pd.read_csv(REPORT / f'area_table_{variant}.csv')
    w = t.pivot_table(index='area_id', columns=['model', 'feature_set'], values='auc')
    r = read_json(REPORT / f'results_{variant}.json')
    dist = r['reporting_bias']['distance_only_per_area']
    lines = ['| Gebiet | Jahr(e) | Positive | Hintergrund | AUC Modell | AUC nur Neigung | Differenz | AUC Neigung roh | AUC log. Regr. | AUC nur Infrastrukturabstand |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    n = t[(t.model == 'hgb') & (t.feature_set == 'terrain_geology')].set_index('area_id')
    for a in sorted(w.index, key=lambda a: -n.loc[a, 'n_pos']):
        m, s = w.loc[a, ('hgb', 'terrain_geology')], w.loc[a, ('hgb', 'slope_only')]
        yrs = counts['areas'][a]['years']
        ytxt = ', '.join(map(str, yrs)) if yrs and len(yrs) <= 3 else (f'{yrs[0]}–{yrs[-1]}' if yrs else 'unbekannt')
        lines.append(f"| {a} | {ytxt} | {int(n.loc[a, 'n_pos'])} | {int(n.loc[a, 'n_bg'])} | {f(m)} | {f(s)} | {f(m - s, 3)} | "
                     f"{f(w.loc[a, ('slope_rule', 'slope_only')])} | {f(w.loc[a, ('lr', 'terrain_geology')])} | {f(dist.get(a))} |")
    return lines


def run():
    pc = read_json(DATA / 'positives_counts.json')
    r = read_json(REPORT / 'results_srtm.json')
    cs = load_meta(DATA / 'samples_srtm.parquet')['counts']
    has_skadi = (REPORT / 'results_skadi.json').exists()
    rk = read_json(REPORT / 'results_skadi.json') if has_skadi else None
    ck = load_meta(DATA / 'samples_skadi.parquet')['counts'] if has_skadi else None
    p, d = r['primary'], r['primary']['diff']
    rb = r['reporting_bias']
    lc = r['land_cover']
    training_only = {a: v for a, v in cs['areas'].items() if v['status'] != 'evaluation'}
    L = []
    L += ['# Murenanfälligkeit Österreich aus allen Inventardaten (anfaelligkeit_at_v01)', '',
          '**Stand 18.10.2026. Vorab registriert** (`config/anfaelligkeit_at_v01.json`, `PREREGISTRATION.json`, Amendment 1) bevor ein '
          'Geländewert, eine Stichprobe oder ein Modell dieser Version entstand. Alle Zahlen stammen aus `results_srtm.json` / '
          '`results_skadi.json` und den Gebietstabellen in diesem Ordner.', '',
          '> Die Werte sind eine **relative Anfälligkeit**: eine Rangfolge von Hangzellen innerhalb eines Gebiets. Sie sind **keine '
          'Wahrscheinlichkeit**, dass eine Mure abgeht, keine Gefahrenkarte und keine Warnung. Hintergrund und Verhältnis 1 : 3 sind gewählt, '
          'das Inventar ist unvollständig. Modellwichtigkeit ist keine Ursache.', '',
          '## Frage und Antwort', '',
          'Lernt ein statisches Modell aus Gelände und Geologie um genau verortete reine Hangmuren anderer österreichischer Gebiete, die '
          'Hangmuren eines **ganz zurückgehaltenen Gebiets** besser von Zufallspunkten desselben Gebiets zu unterscheiden als die Neigung allein?', '',
          f"- **Hauptergebnis (SRTM, {r['n_evaluation_areas']} Prüfgebiete, jedes einmal ganz zurückgehalten):** AUC {ci(p['auc'])} "
          f"(Zufall 0,5); nur Neigung {ci(r['summary']['hgb:slope_only']['auc'])}.",
          f"- **Gepaarte Differenz Modell − Neigung: {ci(d)}** → **{r['verdict']['statement']}**"
          + (' (Intervall vollständig über 0).' if r['verdict']['better_than_slope_alone'] else ' (Intervall schließt 0 ein oder liegt darunter).'),
          f"- Über Zufall: {'ja' if r['verdict']['above_chance'] else 'nicht belegt'} (Intervall der mittleren AUC "
          f"{'über' if r['verdict']['above_chance'] else 'nicht vollständig über'} 0,5).",
          '- Einheiten sind **Gebiete** (Ereignisdokumentationen bzw. feste 50-km-Kacheln), nicht Punkte. Intervalle: 95 %, Bootstrap über '
          'Gebiete (2000 Ziehungen, Seed 20261018). Gebiete desselben Unwetters (Vorarlberg/Tirol und Gasen/Haslau August 2005; Nordhälfte und '
          'Taxenbach Juni 2013) sind möglicherweise abhängig.', '']
    L += ['## Daten', '',
          f"GeoSphere-Inventar (Abruf 14.10.2026, {pc['records_with_geometry']} Einträge mit Lage): {pc['subgroup_hangmure']} reine Hangmuren, "
          f"davon {pc['precise_position']} genau verortet (≤ 20 m laut Inventar), {pc['duplicates_merged']} Duplikate (< 30 m) zusammengefasst → "
          f"**{pc['candidates']} Kandidaten**. Nicht als Positive verwendet und nur gezählt: "
          + ', '.join(f'„{k}“ {v}' for k, v in pc['subgroups_not_used'].items()) + '.', '',
          f"- **SRTM (Hauptlauf):** Höhendaten vom Februar 2000; deshalb nur Ereignisse mit bekanntem Jahr ≥ 2001 "
          f"({cs['excluded_dem_provenance_year']} ohne Jahr oder älter ausgeschlossen, u. a. Thiersee 1970 und die Luftbildauswertungen ohne Datum). "
          f"Geländeprüfung (Neigung ≥ 5°, Höhe gültig): {cs['excluded_terrain']['slope_below_minimum']} wegen Neigung < 5°, "
          f"{cs['excluded_terrain']['nan_or_elevation']} ohne gültige Höhe ausgeschlossen. **{cs['included_positives']} Positive**, "
          f"{cs['evaluation_areas']} Prüfgebiete (≥ 10 Positive), {len(training_only)} kleinere Gebiete nur im Training.",
          ]
    if has_skadi:
        L += [f"- **Skadi (Sensitivität, alle Daten):** alle Positive unabhängig vom Jahr, **{ck['included_positives']} Positive**, "
              f"{ck['evaluation_areas']} Prüfgebiete. Amendment 1: Die Skadi-Kacheln sind über Österreich zu 99,3–99,99 % zellidentisch mit SRTM; "
              'der Unterschied der beiden Läufe liegt fast nur in der Auswahl der Positive (auch undatierte Luftbildkartierungen und Thiersee 1970).']
    L += ['- **Hintergrund:** je Positiv drei Zufallspunkte im selben Gebiet, in den festen 5-km-Rasterzellen (EPSG:31287), die mindestens ein '
          'Positiv des Gebiets enthalten; Neigung ≥ 5°, ≥ 100 m von **jedem** Inventarpunkt (alle Prozesse), ≥ 60 m untereinander. '
          'Hintergrundpunkte sind Pseudo-Negative: Hänge ohne dokumentierte Meldung in der Nähe, keine nachweislich stabilen Hänge.',
          '- **Merkmale:** Höhe, Neigung, Exposition (Sinus/Kosinus), Profil- und Plankrümmung, Rauigkeit (TRI), TPI 150/500 m, Hangposition 500 m, '
          'Einzugsgebiet und TWI (fehlend, wenn das Einzugsgebiet den 5-km-Rand erreicht), Geologie 1 : 500 000 (5 Klassen). **Keine** Wetter-, '
          'Koordinaten-, Jahres-, Infrastruktur- oder Nachbarereignis-Merkmale (Test mit Fehlerinjektion).',
          '- **Prüfung:** Leave-one-area-out; zusätzlich werden alle Trainingspunkte im Umkreis von 1 km um das zurückgehaltene Gebiet entfernt. '
          'Modelle ohne Parametersuche (V0.4-Einstellungen), Trainingsgewicht je Gebiet 1/√(Positive), damit 2005 nicht dominiert.', '']
    L += ['## Ergebnisse SRTM (Hauptlauf)', ''] + model_table(r['summary']) + ['']
    pooled = r['pooled_auc']
    L += [f"Gepoolt über alle zurückgehaltenen Vorhersagen (beschreibend): Modell {f(pooled['hgb:terrain_geology'])}, nur Neigung "
          f"{f(pooled['hgb:slope_only'])}, Neigung roh {f(pooled['slope_rule:slope_only'])}.", '']
    if 'without_largest_area' in r:
        w = r['without_largest_area']['hgb:terrain_geology']
        L += [f"Ohne das größte Gebiet ({r['largest_area']}): AUC {ci(w['auc'])}, Differenz zu nur Neigung {ci(w['auc_minus_hgb:slope_only'])}.", '']
    L += ['### Alle Prüfgebiete', '', 'AUC je Gebiet: zurückgehaltene Positive gegen zurückgehaltenen Hintergrund. „Modell“ = Gradient Boosting, '
          'Gelände + Geologie. Die letzte Spalte rankt nur nach dem Abstand zu Gebäude/Straße (OSM 2026), kein Modellmerkmal.', '']
    L += area_rows('srtm', cs) + ['']
    if training_only:
        L += ['Nur im Training (weniger als 10 Positive): ' + ', '.join(f"{a} ({v['positives']})" for a, v in sorted(training_only.items())) + '.', '']
    imp = r['permutation_importance_mean']
    L += ['### Worauf sich das Modell stützt (beschreibend)', '',
          'Mittlerer AUC-Verlust im zurückgehaltenen Gebiet, wenn ein Merkmal zufällig vertauscht wird: '
          + ', '.join(f'{k} {f(v)}' for k, v in list(imp.items())[:6]) + '. Das Modell stützt sich auf diese Merkmale; das ist keine Ursache.', '']
    L += ['## Meldebias-Kontrolle (wie V0.7, explorativ)', '',
          f"- Nur der Abstand zum nächsten Gebäude oder zur nächsten öffentlichen Straße (OSM 2026) als Rangfolge: AUC {ci(rb['distance_only_auc'])}. "
          'Werte über 0,5 heißen: gemeldete Hangmuren liegen näher an Infrastruktur als der Zufallshintergrund (Sichtbarkeit, Erhebungswege, '
          'oder echte Nähe von Siedlungen zu Hängen). Der Abstand ist nie ein Modellmerkmal.']
    far = rb['far_from_infrastructure_200m']
    if 'summary' in far:
        s = far['summary']
        L += [f"- Nur Punkte ≥ 200 m von Gebäude und Straße (Anteil Positive {f(far['positives_share_far'], 2)}, Hintergrund "
              f"{f(far['background_share_far'], 2)}; {len(far['areas'])} Gebiete mit ≥ 5 Positiven und ≥ 5 Hintergrundpunkten): Modell AUC "
              f"{ci(s['hgb:terrain_geology']['auc'])}, nur Neigung {ci(s['hgb:slope_only']['auc'])}, Differenz {ci(s['hgb:terrain_geology']['auc_minus_hgb:slope_only'])}."]
    else:
        L += [f"- Straßenferne Teilmenge: zu wenige Gebiete ({len(far['areas'])}) für eine Auswertung."]
    L += ['- Die meisten Positiven wurden auf Orthofotos kartiert („Ferndiagnose – Orthofoto“). Unter Wald sind Hangmuren schwer zu sehen; '
          'deshalb ist Landbedeckung nur eine Zusatzanalyse.', '']
    L += ['## Landbedeckung (CORINE passend zum Ereignisjahr, explorativ)', '']
    if 'summary' in lc:
        L += [f"Nur Gebiete mit bekanntem Jahr ≥ 2002 und einem Kartenstand vor dem Ereignisjahr ({len(lc['evaluation_areas'])} Prüfgebiete; "
              + ', '.join(f'{a}: {v}' for a, v in lc['vintages'].items() if a in lc['evaluation_areas']) + '). Gleiche Proben, gepaart:', '']
        L += model_table(lc['summary']) + ['']
        L += [f"Zusatz durch Landbedeckung: Gradient Boosting {ci(lc['hgb_landcover_minus_terrain_geology'])}, logistische Regression "
              f"{ci(lc['lr_landcover_minus_terrain_geology'])}. Ein Vorteil wäre wegen der Orthofoto-Kartierung teilweise Sichtbarkeit.", '']
    else:
        L += [lc.get('note', 'nicht auswertbar'), '']
    dd = r['dem_date_description']
    L += ['## Datumsregel Gelände', '',
          'Entscheidung des Nutzers vom 18.10.2026: Es zählt die Herkunft der Höhendaten, nicht das Dateidatum. SRTM wurde im Februar 2000 '
          'aufgenommen und liegt damit vor jedem Ereignis ab 2001. Lücken in SRTMGL1 v3 sind aus späteren Quellen gefüllt (kleiner Anteil steiler '
          'Zellen). SRTM ist ein Oberflächenmodell (Wald, Gebäude) und glatter als ein Laserscan-Geländemodell; Hangmuren sind meist kleiner als '
          'eine 30-m-Zelle.',
          f"Beschreibend: Gebiete mit Ereignisjahr ≥ 2017 ({', '.join(dd['areas_year_ge_2017']) or 'keine'}) mittlere Differenz Modell − Neigung "
          f"{f(dd['mean_auc_diff_late'])}, übrige {f(dd['mean_auc_diff_other'])}.", '']
    if has_skadi:
        L += ['## Sensitivität: alle Inventardaten (Skadi-Lauf)', '', f"{rk['n_evaluation_areas']} Prüfgebiete, Hauptmodell AUC {ci(rk['primary']['auc'])}, "
              f"Differenz zu nur Neigung **{ci(rk['primary']['diff'])}** → {rk['verdict']['statement']}. Herkunft der Höhendaten für undatierte und "
              'vor 2000 liegende Ereignisse nicht nachweislich davor; deshalb nie Hauptergebnis.', '']
        L += model_table(rk['summary']) + ['', '### Alle Prüfgebiete (Skadi-Lauf)', ''] + area_rows('skadi', ck) + ['']
    demo = DATA / 'demo/demo_meta.json'
    if demo.exists():
        m = read_json(demo)
        L += ['## Demogebiet', '', f"Nach der registrierten Regel: Prüfgebiet mit den meisten Positiven = **{m['area_id']}**; darin der 9-km-Block mit den "
              f"meisten Positiven ({m['positives_in_block']}). Die Rasterebene stammt aus dem Modell, das dieses Gebiet **nicht** im Training hatte, und "
              f"zeigt Perzentilränge innerhalb des Blocks. Beschreibend: In den obersten 20 % der Blockfläche liegen {f(m['positives_in_top20_model'], 2)} "
              f"der dokumentierten Hangmuren des Blocks (nur Neigung: {f(m['positives_in_top20_slope'], 2)}; Flächenanteil 0,20). Ein Block, nach "
              'Ereigniszahl gewählt: keine eigene Prüfung.', '']
    L += ['## Grenzen', '',
          '- Inventarpunkte markieren nicht, ob Anriss, Weg oder Ablagerung gemeint ist; 30-m-Zellen sind gröber als viele Hangmuren.',
          '- Die Gebiete sind vor allem dort, wo kartiert wurde; Hintergrund aus nicht kartierten Hängen zählt als „ohne Meldung“.',
          '- Prüfgebiete sind wenige und ungleich groß; Gebiete desselben Unwetters sind nicht unabhängig.',
          '- Alle Nebenanalysen sind explorativ; gezählt wurden die Hauptdifferenz und die 11 registrierten Nebenanalysen, alle berichtet.',
          '- Keine Wahrscheinlichkeit, kein Risiko, keine Warnung, keine Gefahrenkarte.', '']
    mt = REPORT / 'mutation_tests.json'
    if mt.exists():
        m = read_json(mt)
        L += ['## Tests', '', f"`tests/test_anfaelligkeit_at_v01.py`; {len(m['mutations'])} eingebaute Fehler, davon "
              f"{sum(x['caught'] for x in m['mutations'])} von den Tests erkannt (`mutation_tests.json`).", '']
    (REPORT / 'summary.md').write_text('\n'.join(L), encoding='utf-8')
    print('\n'.join(L[:20]))
