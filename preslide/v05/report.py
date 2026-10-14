"""reports/v05/summary.md, generated only from stored V0.5 artifacts.

python -m preslide.v05.report
"""
from collections import Counter

import numpy as np

from ..common import read_json
from .paths import V05_DATA, V05_REPORT

NAME = {'conditional_logit': 'Bedingte log. Regression', 'hist_gradient_boosting': 'Gradient Boosting'}
VAR = {'static': 'Gelände/Landbedeckung/Geologie', 'temporal': 'Wetter', 'combined': 'kombiniert'}


def f3(x):
    return 'n/a' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.3f}'


def ci(v):
    return f'[{f3(v[0])}; {f3(v[1])}]'


def exclusion_counts(freeze):
    c = Counter()
    for stages in freeze['exclusions'].values():
        for stage, s in stages.items():
            c[f"{stage}: {s.get('reason', '').split(':')[0]}"] += 1
            break
    return c


def main():
    r = read_json(V05_REPORT / 'cv_results.json')
    fr = read_json(V05_REPORT / 'COHORT_FREEZE.json')
    prox = read_json(V05_REPORT / 'proximity_audit.json')
    pool = read_json(V05_DATA / 'pool_audit/pool_audit.json')
    p = r['primary']
    ch = r['chance']
    L = []
    w = L.append
    w('# PreSlide V0.5 — Nachbarhang-Rangfolge gegen zehn ungematchte Umgebungshänge\n')
    w('**Explorative, gruppiert kreuzvalidierte Studie auf bereits gesehenen Ereignissen. Kein neuer unabhängiger Test.** '
      'Plan: `reports/weiterentwicklung_2026-10-14/V05_NACHBARHANG_PLAN.md`; eingefrorene Regeln: `config/v05.json` '
      '(Präregistrierung `reports/v05/PREREGISTRATION.json`); Kohorte und CV-Zuordnung vor jedem Modell eingefroren '
      '(`reports/v05/COHORT_FREEZE.json`). Alle Zahlen stammen aus `reports/v05/cv_results.json`.\n')
    w('## Fragestellung\n')
    w('Kann ein Modell mit Information vor t0 den dokumentiert betroffenen Hang höher einordnen als zehn flächengleichmäßig '
      'gezogene, **nicht** nach Gelände gematchte Hangpunkte 750 m–10 km um ihn? Das ist eine andere, leichtere Aufgabe als in '
      'V0–V0.4 (gematchte Kontrollen). Eine höhere V0.5-AUC ist kein besseres Modell für die V0.4-Frage. Kontrollen sind '
      'Pseudo-Negative ohne dokumentierte Rutschung; Modellwerte sind relative Ränge, keine Rutschungswahrscheinlichkeiten.\n')
    w('## Bestand\n')
    w(f"- Positive: 423 V0.4-Ereignisse (unverändertes t0). Pools: {pool['pools']} geprüft, alle Ringpunkte exakt aus dem "
      f"V0.4-Seed reproduziert; Inventar- und Grenzflags durch Neuberechnung bestätigt (Abweichungen: "
      f"{pool['flag_mismatch_total']['inventory_clear']} / {pool['flag_mismatch_total']['inside_austria']}).")
    w(f"- Kontrollauswahl: {prox['selected_groups']} von 423 Ereignissen mit zehn wählbaren Kontrollen "
      f"(Ausschlüsse bei der Auswahl: {len(prox['excluded_at_selection'])}).")
    w(f"- Nach Umweltdaten: **{fr['cohort']['events']} Ereignisgruppen, {fr['cohort']['samples']} Proben, "
      f"{fr['cohort']['units']} Abhängigkeitseinheiten** (V0.4-Einheiten). Ausschlüsse: "
      + ', '.join(f'{k} {v}' for k, v in exclusion_counts(fr).items()) + '.')
    d = r['distributions']['control_distance_bins']
    w(f"- Kontrollabstand zum Positiv: 0,75–2 km {d['0.75-2km']}, 2–5 km {d['2-5km']}, 5–10 km {d['5-10km']} (flächengleichmäßig).")
    pc = prox['pairs_lt_1000m']
    w(f"- Nähe-Audit (< 1 km, verschiedene Gruppen): positiv–positiv {pc['positive_positive']['pairs']} "
      f"(einheitsübergreifend {pc['positive_positive']['cross_unit_pairs']}), positiv–Kontrolle {pc['positive_control']['pairs']} "
      f"({pc['positive_control']['cross_unit_pairs']}), Kontrolle–Kontrolle {pc['control_control']['pairs']} "
      f"({pc['control_control']['cross_unit_pairs']}). Deshalb räumliche Trainingsbereinigung je Fold.\n")
    folds = r['folds']
    w(f"Räumlich bereinigte CV: 5 Folds × 5 Wiederholungen. Durchführbar: **{'ja' if r['cv_feasible'] else 'NEIN'}**. "
      f"Trainingsgruppen nach Bereinigung je Fold {min(f['train_groups'] for f in folds)}–{max(f['train_groups'] for f in folds)} "
      f"(ungepurgt {min(f['unpurged_train_groups'] for f in folds)}–{max(f['unpurged_train_groups'] for f in folds)}), "
      f"Trainingseinheiten {min(f['train_units'] for f in folds)}–{max(f['train_units'] for f in folds)}, minimaler Restabstand "
      f"Training–Prüfung {f3(min(f['min_train_to_held_distance_m'] for f in folds) / 1000)} km.\n")
    w('## Primärer Endpunkt\n')
    w(f"Bedingte logistische Regression, kombiniert, räumlich bereinigte CV, über Einheiten gleich gewichtete lokale AUC: "
      f"**Median {f3(p['median'])}** (Spannweite der fünf Wiederholungen {f3(p['range'][0])}–{f3(p['range'][1])}; "
      f"Bootstrap Wiederholung 1 {ci(p['ci95_rep1'])}). Zufall 0,5; Neigungsregel ohne Fit {f3(p['slope_rule'])}.\n")
    d = p['combined_minus_static_rep1_bootstrap']
    w(f"**Hauptvergleich kombiniert − statisch:** je Wiederholung " + ', '.join(f3(x) for x in p['combined_minus_static_per_repetition'])
      + f"; Bootstrap (Wdh. 1) {f3(d['mean'])} {ci(d['ci95'])}, Anteil > 0: {f3(d['share_above_zero'])}.\n")
    w('## Alle Modelle (räumlich bereinigt; Median über 5 Wiederholungen, Einheiten gleich gewichtet)\n')
    w('| Modell | Merkmale | lokale AUC | Top-1 | Top-3 | mittl. Rang | MRR | lokale AUC je Ereignis | gepoolte AP |')
    w('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    for key, v in r['purged'].items():
        m, var = key.split('/')
        x = v['median']
        w(f"| {NAME[m]} | {VAR[var]} | {f3(x['local_auc_units'])} | {f3(x['top1_units'])} | {f3(x['top3_units'])} | "
          f"{x['mean_rank_units']:.2f} | {f3(x['mrr_units'])} | {f3(x['local_auc_events'])} | {f3(x['pooled_ap'])} |")
    s = r['slope_rule']
    w(f"| Referenz | Neigung höher = höherer Rang | {f3(s['local_auc_units'])} | {f3(s['top1_units'])} | {f3(s['top3_units'])} | "
      f"{s['mean_rank_units']:.2f} | {f3(s['mrr_units'])} | {f3(s['local_auc_events'])} | {f3(s['pooled_ap'])} |")
    w(f"| Zufall | analytisch | 0.500 | {f3(ch['top1'])} | {f3(ch['top3'])} | {ch['mean_rank']:.2f} | {f3(ch['mrr'])} | 0.500 | {f3(ch['pooled_ap_prevalence'])} |\n")
    w('Ungepurgte Sensitivität (gleiche Folds, ersetzt die Hauptauswertung nicht): ' + '; '.join(
        f"{NAME[k.split('/')[0]]} {VAR[k.split('/')[1]]} {f3(v['median']['local_auc_units'])}" for k, v in r['unpurged_sensitivity'].items()) + '.\n')
    b = r['bootstrap_rep1']
    w('Gepaarte Bootstrapdifferenzen (Wdh. 1, 2000 Einheiten-Ziehungen, lokale AUC): ' + '; '.join(
        f"{NAME[m]}: kombiniert − statisch {f3(b[m]['local_auc']['combined_minus_static']['mean'])} {ci(b[m]['local_auc']['combined_minus_static']['ci95'])}, "
        f"statisch − Neigungsregel {f3(-b[m]['local_auc']['slope_rule_minus_static']['mean'])}"
        for m in b) + '.\n')
    w('## Diagnosen (registriert, explorativ)\n')
    a = r['land_cover_ablation_rep1']
    w(f"- **Ohne Landbedeckung** (bed. Regression kombiniert, Wdh. 1): {f3(a['without_land_cover']['local_auc_units'])} statt "
      f"{f3(a['with_land_cover']['local_auc_units'])} (Differenz {f3(a['difference_local_auc_units'])}).")
    st = r['stanz_conditional_logit_rep1']
    w(f"- **Stanz-Einheit** ({st['events']} Ereignisse, `{st['unit']}`), kombiniert: alle {f3(st['combined']['all']['local_auc_units'])}, "
      f"ohne Stanz {f3(st['combined']['without_stanz']['local_auc_units'])}, nur Stanz {f3(st['combined']['stanz_only']['local_auc_units'])}; "
      f"statisch ohne Stanz {f3(st['static']['without_stanz']['local_auc_units'])}.")
    cv = r['control_variants']
    w(f"- **Kontrollvarianten** (gemeinsame Kohorte {cv['cohort_events']} Ereignisse, {cv['cohort_units']} Einheiten, Wdh. 1, gleiche Bereinigung):")
    for key, label in (('a_matched_5', '5 gematchte V0.4-Kontrollen'), ('b_unmatched_first_5', 'erste 5 ungematchte'), ('c_unmatched_10', '10 ungematchte')):
        x = cv[key]
        w(f"  - {label}: statisch {f3(x['static']['local_auc_units'])}, kombiniert {f3(x['combined']['local_auc_units'])} "
          f"(Δ {f3(x['combined_minus_static_local_auc_units'])}); Top-1 kombiniert {f3(x['combined']['top1_units'])} (Zufall {f3(x['chance']['top1'])}).")
    dist = r['distributions']
    lc = dist['categorical']['land_cover_class']
    w('- **Verteilungen** Positiv vs. Kontrolle: Neigung Median ' + f"{dist['numeric']['slope']['positive']['50%']:.1f}° vs. {dist['numeric']['slope']['control']['50%']:.1f}°; "
      f"Höhe {dist['numeric']['elevation']['positive']['50%']:.0f} vs. {dist['numeric']['elevation']['control']['50%']:.0f} m; Wald "
      f"{f3(lc['positive'].get('lc_forest', 0))} vs. {f3(lc['control'].get('lc_forest', 0))}; Grünland/Strauch {f3(lc['positive'].get('lc_grass_shrub', 0))} vs. "
      f"{f3(lc['control'].get('lc_grass_shrub', 0))}; Siedlung/Wasser/Sonstiges {f3(lc['positive'].get('lc_artificial_water_other', 0))} vs. "
      f"{f3(lc['control'].get('lc_artificial_water_other', 0))}.")
    ic = r['indirect_cues']
    w(f"- **Indirekte Hinweise:** abgeschnittenes Einzugsgebiet Positiv {f3(ic['catchment_truncated']['positive'])} vs. Kontrolle "
      f"{f3(ic['catchment_truncated']['control'])}; fehlende Werte (Anteil) " + ', '.join(
          f"{k} {f3(v['positive'])}/{f3(v['control'])}" for k, v in ic['missing_share'].items()) + '. Diese Flags sind keine Prädiktoren.')
    sub = r['subsets_conditional_logit_combined_rep1']
    w('- **Teilmengen nach Erhebungsart** (kombiniert, Wdh. 1): ' + '; '.join(
        f"{' '.join(k.split())}: {f3(v['local_auc_events'])} ({v['events']} Ereignisse/{v['units']} Einheiten)" for k, v in sub['survey_method'].items()) + '.')
    w('- **Nach Positionskategorie:** ' + '; '.join(
        f"{k}: {f3(v['local_auc_events'])} ({v['events']}/{v['units']})" for k, v in sub['position_category'].items()) + '.')
    w('- Straßen-/Siedlungsnähe: nicht abgerufen (optional, hätte V0.5 blockiert; moderne Karten wären kein damaliger Stand).\n')
    coef = r['conditional_logit_coefficients_all_data']['combined']
    top = list(coef.items())[:8]
    w('**Woran sich das kombinierte lineare Modell auf allen Daten am stärksten stützt** (standardisierte Koeffizienten; '
      'keine Validierungsleistung, keine Kausalität): ' + ', '.join(f'{k} {v:+.2f}' for k, v in top) + '.\n')
    w('## Einordnung\n')
    num = r['distributions']['numeric']
    w(f"**Kein belegter Wetterzusatznutzen:** Beim Primärmodell ist kombiniert − statisch in allen fünf Wiederholungen negativ "
      f"(Bootstrap-Intervall schließt 0 ein); beim Gradient Boosting leicht positiv mit Intervall um 0. Die Wetter-allein-Variante "
      f"liegt deutlich über Zufall, ist hier aber **kein reines Wettersignal**: Positive liegen im Median "
      f"{num['elevation']['control']['50%'] - num['elevation']['positive']['50%']:.0f} m tiefer als die Kontrollen, und INCA-Temperatur "
      f"und -Niederschlag sind höhen- und lageabhängig (1-km-Raster, Kontrollen meist 5–10 km entfernt). Sie kodieren daher teilweise "
      f"Gelände und Lage.\n")
    w(f"**Die Trennung stützt sich auf Höhe/Lage und Landbedeckung, nicht auf Steilheit:** Die Neigungsregel liegt nur bei "
      f"{f3(r['slope_rule']['local_auc_units'])}; gemeldete Hänge liegen tiefer und seltener im Wald als der flächengleichmäßige "
      f"Hintergrund. Mit gematchten Kontrollen (Variante a) erreicht dieselbe Modellklasse auf derselben Kohorte nur "
      f"{f3(cv['a_matched_5']['static']['local_auc_units'])}. Der V0.5-Wert misst damit vor allem, wie stark sich gemeldete Hänge "
      f"vom lokalen Hintergrund unterscheiden — ein Gemisch aus Anfälligkeit und Erfassungswahrscheinlichkeit (Talnähe, Siedlungen, "
      f"Straßen).\n")
    w('Die Werte beantworten nur, wie gut vorhandene Information den gemeldeten Hang von einer breiteren lokalen Hintergrundverteilung '
      'trennt. Sie enthalten Gelände- und Landbedeckungsunterschiede, die teilweise Meldebias (Erfassung an Straßen/Siedlungen, im '
      'Offenland) sein können. Der Wetterzusatznutzen ist nur über den Vergleich kombiniert − statisch zu beurteilen, nicht über den '
      'Abstand zum Zufall. Dieselben Ereignisse wurden in V0.4 bereits betrachtet; Wiederholungen und Bootstrap sind keine '
      'unabhängigen Bestätigungen. Eine Bestätigung braucht ungesehene Abhängigkeitseinheiten und ein eigenes Protokoll.\n')
    w('Ausschlusszonen beruhen auf dem gesamten Inventarstand (auch späteren Ereignissen): retrospektive Auswahlregel, keine Simulation '
      'eines damals verfügbaren Inventars. CORINE-Vintage-Regel wie V0.4; tatsächliche historische Verfügbarkeit nicht belegt.\n')
    (V05_REPORT / 'summary.md').write_text('\n'.join(L), encoding='utf-8')
    print(f'reports/v05/summary.md: {len(L)} lines')


if __name__ == '__main__':
    main()
