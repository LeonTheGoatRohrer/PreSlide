"""reports/v04/summary.md and data/v04/web/results.json, generated only from stored V0.4 artifacts.

python -m preslide.v04.report
"""
import json
from collections import Counter

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from .paths import V04_DATA, V04_REPORT, guard
from .pipeline import run_dir, load
from . import models as M

LABEL = {'conditional_logit': 'Bedingte log. Regression', 'logistic_regression': 'Logistische Regression',
         'hist_gradient_boosting': 'Gradient Boosting'}


def f3(x):
    return 'n/a' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.3f}'


def exclusion_table():
    status = read_json(run_dir() / 'status.json')
    reasons = Counter()
    for gid, stages in status.items():
        for stage in ('match', 'weather', 'assemble'):
            s = stages.get(stage)
            if s and s['state'] != 'complete':
                reasons[f"{stage}: {s.get('reason', '').split(':')[0]}"] += 1
                break
    return reasons


def matching_quality(data):
    c = data[data.label == 0]
    return {col: {'median': float(c[col].median()), 'p95': float(c[col].quantile(.95)), 'max': float(c[col].max())}
            for col in ('distance_to_positive_m', 'slope_difference_deg', 'elevation_difference_m', 'aspect_difference_deg')}


def balance(data, cols):
    """Standardized positive-minus-control difference within groups (descriptive)."""
    out = {}
    for c in cols:
        if c not in data:
            continue
        g = data.groupby('event_group_id')
        diff = (data[data.label == 1].set_index('event_group_id')[c] - data[data.label == 0].groupby('event_group_id')[c].mean())
        sd = data[c].std()
        out[c] = float(diff.mean() / sd) if sd and np.isfinite(sd) and diff.notna().any() else None
    return out


def run():
    audit = read_json(V04_REPORT / 'audit_summary.json')
    reg = read_json(V04_REPORT / 'PREREGISTRATION.json')
    part = read_json(V04_REPORT / 'partition_summary.json')
    adm = read_json(V04_REPORT / 'admission.json')
    dev = read_json(V04_REPORT / 'dev_metrics.json')
    test = read_json(V04_REPORT / 'test_results.json') if (V04_REPORT / 'test_results.json').exists() else None
    data = load(run_dir() / 'dataset.parquet')
    ptab = pd.DataFrame(json.loads((V04_DATA / 'partition/partition.json').read_text(encoding='utf-8')))
    excl = exclusion_table()
    mq = matching_quality(data)
    bal = balance(M.add_one_hot(data), M.STATIC + M.temporal_columns(adm['admitted_features']))
    L = ['# PreSlide V0.4 — erweitertes Fall-Kontroll-Experiment', '',
         'Automatisch erzeugt aus gespeicherten Artefakten (`python -m preslide.v04.report`). Getrennt von V0–V0.3; '
         'die eingefrorene V0.3-Baseline ist unverändert.', '',
         f"Präregistrierung: `config/v04.json` SHA-256 `{reg['config_sha256'][:16]}…`, registriert {reg['registered_at'][:19]} UTC, vor jedem Matching-, Wetter- oder Modellergebnis.", '',
         '## Datenbestand', '',
         f"- Kandidaten Stufe 1 mit sicherem Ereignistag (Tier A): **{audit['main_candidates']}** in {audit['main_temporal_episodes']} zeitlichen Episoden; alle 102 V0-Kandidaten reproduziert.",
         f"- Vollständige Gruppen (1 Positiv + 5 Kontrollen, Gelände + Wetter): **{data.event_group_id.nunique()}** ({len(data)} Proben).",
         f"- Zeitqualität der vollständigen Gruppen: {data[data.label == 1].time_quality.value_counts().to_dict()}.",
         f"- Jahre: {data[data.label == 1].event_day.str[:4].value_counts().sort_index().to_dict()}.",
         f"- Bundesländer: {data[data.label == 1].state.value_counts().to_dict()}.", '',
         '### Ausschlüsse nach dem Audit', '', '| Grund | Ereignisse |', '|---|---:|']
    L += [f'| {k} | {v} |' for k, v in excl.most_common()]
    L += ['', 'Nicht im Hauptbestand (Audit): ' + ', '.join(f"{r['events']} × Qualitätsstufe {r['quality_tier']}/{r['date_tier']}" for r in audit['eligible_by_quality_and_date_tier'] if not (r['quality_tier'] == 1 and r['date_tier'] == 'A_narrative_day')) + '.', '',
          '## Unabhängigkeitseinheiten und Aufteilung', '',
          f"Abhängigkeitsprüfung räumlich-zeitlicher Einheiten: {part['dependence_check']['finite_pairs']} Paare, 90. Perzentil der Regenkorrelation "
          f"{f3(part['dependence_check']['p90_pearson_r'])} (Schwelle 0,5) → {'angenommen' if part['dependence_check']['spatiotemporal_units_accepted'] else 'abgelehnt; zeitliche Episoden werden verwendet'}.", '',
          '| Teil | Ereignisse | Einheiten | zeitl. Episoden | Baseline-Ereignisse |', '|---|---:|---:|---:|---:|']
    L += [f"| {k} | {v['events']} | {v['units']} | {v['temporal_episodes']} | {v['baseline_events']} |" for k, v in part['partition'].items()]
    sizes = ptab.groupby('independence_unit').size().sort_values(ascending=False)
    L += ['', f"Größte Einheit: {sizes.iloc[0]} Ereignisse; Einheiten mit 1 Ereignis: {int((sizes == 1).sum())}. Auswertung gewichtet jede Einheit gleich.", '',
          '## Matchingqualität (Kontrollen)', '', '| Größe | Median | 95 % | Max |', '|---|---:|---:|---:|']
    L += [f"| {k} | {v['median']:.1f} | {v['p95']:.1f} | {v['max']:.1f} |" for k, v in mq.items()]
    L += ['', '## Merkmale und Abdeckung', '',
          f"Zugelassene Tagesprodukte (Pilot, ≥ 95 %): {', '.join(k for k, v in adm['products'].items() if v['admitted'])}; nicht zugelassen: "
          f"{', '.join(k for k, v in adm['products'].items() if not v['admitted']) or '—'}.", '',
          '| Merkmal | Proben vorhanden | Gruppen vollständig | standard. Differenz Positiv − Kontrollen |', '|---|---:|---:|---:|']
    for c, v in dev['coverage'].items():
        L.append(f"| {c} | {v['samples_present']:.2f} | {v['groups_complete']:.2f} | {f3(bal.get(c))} |")
    L += ['', '## Entwicklung (gruppierte CV, 5 × 5, nur Entwicklungsbestand)', '',
          f"{dev['development']['events']} Ereignisse, {dev['development']['units']} Einheiten. Median über 5 Wiederholungen (Spannweite).", '',
          '| Modell | Merkmale | lokale AUC (gew.) | Top-1 (gew.) | lokale AP (gew.) | gepoolte AP |', '|---|---|---:|---:|---:|---:|']
    for key, r in dev['results'].items():
        m, v = key.split('/')
        med, lo, hi = r['median'], r['min'], r['max']
        L.append(f"| {LABEL[m]} | {v} | {med['local_auc_weighted']:.3f} ({lo['local_auc_weighted']:.3f}–{hi['local_auc_weighted']:.3f}) | "
                 f"{med['top1_weighted']:.3f} | {med['local_ap_weighted']:.3f} | {med['pooled_ap']:.3f} |")
    n = dev['random_rank_null']
    L += ['', f"Zufallsreferenz (zufälliger Rang, gleiche Gewichte): Mittel {n['mean']:.3f}, 90 %-Band {n['q05']:.3f}–{n['q95']:.3f}. "
          f"Label-Permutation (bedingte log. Regression, 100 Ziehungen): " +
          '; '.join(f"{v}: 90 %-Band {x['q05']:.3f}–{x['q95']:.3f}" for v, x in dev['label_permutation_null'].items()) + '.', '',
          'Gepaarter Einheiten-Bootstrap (Wiederholung 1), lokale AUC:', '']
    for m, b in dev['bootstrap_rep1'].items():
        for k, v in b.items():
            if '_minus_' in k:
                L.append(f"- {LABEL[m]}, {k}: {v['mean']:+.3f} [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}]")
    L += ['', 'Leave-one-state-out (bedingte log. Regression, nur deskriptiv): ' +
          '; '.join(f"{s}: n={r['test_events']}, statisch {r['static']:.2f}, zeitlich {r['temporal']:.2f}, kombiniert {r['combined']:.2f}" for s, r in dev['leave_one_state_out'].items()) + '.', '']
    if test:
        p = test['primary']
        L += ['## Versiegelter externer Test (einmalig ausgewertet)', '',
              f"Bewertet {test['scored_at'][:19]} UTC nach `FREEZE.json`; Prüfungen: {test['freeze_checks']}. "
              f"{test['test']['events']} Ereignisse in {test['test']['units']} unabhängigen Einheiten.", '',
              f"**Primärer Endpunkt** (bedingte log. Regression, kombiniert, gewichtete lokale AUC): **{p['value']:.3f}** "
              f"[95 % {p['ci95'][0]:.3f}–{p['ci95'][1]:.3f}]; Zufall 0,5 (95 %-Quantil der Zufallsreferenz {p['random_rank_null_q95']:.3f}).",
              f"Kombiniert − statisch: {p['combined_minus_static']['mean']:+.3f} [{p['combined_minus_static']['ci95'][0]:+.3f}, {p['combined_minus_static']['ci95'][1]:+.3f}].", '',
              '| Modell | Merkmale | lokale AUC (gew.) | p (≥, Zufall) | Top-1 (gew.) | lokale AP (gew.) | lokale AUC (ungew.) | gepoolte AP |', '|---|---|---:|---:|---:|---:|---:|---:|']
        for key, r in test['results'].items():
            m, v = key.split('/')
            L.append(f"| {LABEL[m]} | {v} | {r['local_auc_weighted']:.3f} | {r['p_upper_vs_random_rank']:.3f} | {r['top1_weighted']:.3f} | "
                     f"{r['local_ap_weighted']:.3f} | {r['local_auc_events']:.3f} | {r['pooled_ap']:.3f} |")
        L += ['', 'Gepaarte Bootstrap-Differenzen (Test):', '']
        for m, b in test['bootstrap'].items():
            for k, v in b.items():
                if '_minus_' in k:
                    L.append(f"- {LABEL[m]}, {k}: {v['mean']:+.3f} [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}]")
        tk = test['time_known_subset'].get('conditional_logit/combined')
        if tk:
            L += ['', f"Teilmenge mit bekannter Tageszeit (Test): {tk['events']} Ereignisse / {tk['units']} Einheiten, kombinierte bed. log. Regression lokale AUC {tk['local_auc_weighted']:.3f}."]
    else:
        L += ['## Versiegelter externer Test', '', 'Noch nicht ausgewertet.']
    freeze = V04_REPORT / 'FREEZE.json'
    if freeze.exists():
        import joblib
        L += ['', '## Worauf sich das finale Modell stützt (bedingte log. Regression, standardisierte Koeffizienten)', '',
              'Auf allen Entwicklungsdaten gefittet; Vorzeichen = Richtung innerhalb der Gruppe. Keine Kausalaussage.', '']
        for variant in ('static', 'combined'):
            path = [k for k in read_json(freeze)['models'] if k.endswith(f'conditional_logit_{variant}.joblib')][0]
            b = joblib.load(ROOT / path)
            coef = pd.Series(b['model'].coef_, index=b['columns']).sort_values(key=abs, ascending=False).head(8)
            L.append(f"- {variant}: " + ', '.join(f'{k} {v:+.2f}' for k, v in coef.items()))
    L += ['', '## Einordnung', '',
          'Kontrollen sind Pseudo-Negative. Werte sind Rangvergleiche innerhalb gematchter Gruppen, keine Rutschungswahrscheinlichkeiten. '
          'Modellgewichte zeigen, worauf sich ein Modell stützt, nicht Ursachen. Ohne eigene räumliche Prüfung wird keine geografische Übertragbarkeit behauptet.',
          'Der Landbedeckungskontrast (Positive seltener im Wald, häufiger auf Grünland und Siedlungs-/Verkehrsflächen) kann physikalisch und durch Meldebias '
          '(an Infrastruktur und Siedlungen werden Ereignisse eher dokumentiert) entstehen; beides lässt sich mit diesen Daten nicht trennen. '
          'Gelände- und Positionsmerkmale am Positiv hängen zudem von der Verortungskonvention der Inventarpunkte ab.', '']
    (V04_REPORT / 'summary.md').write_text('\n'.join(L), encoding='utf-8')
    web = {'version': 'V0.4', 'generated_from': ['reports/v04/dev_metrics.json', 'reports/v04/test_results.json', 'reports/v04/partition_summary.json'],
           'counts': {'candidates': audit['main_candidates'], 'complete_groups': int(data.event_group_id.nunique()),
                      'exclusions': dict(excl), 'partition': part['partition'], 'dependence_check': part['dependence_check']},
           'matching': mq, 'admission': {k: v['admitted'] for k, v in adm['products'].items()},
           'development': {k: v['median'] for k, v in dev['results'].items()}, 'development_null': dev['random_rank_null'],
           'development_permutation_null': dev['label_permutation_null'],
           'test': None if not test else {'primary': test['primary'], 'results': test['results'], 'n': test['test'],
                                          'null': test['random_rank_null']}}
    write_json(guard(V04_DATA / 'web') / 'results.json', web)
    print(f'wrote reports/v04/summary.md ({len(L)} lines)')


if __name__ == '__main__':
    run()
