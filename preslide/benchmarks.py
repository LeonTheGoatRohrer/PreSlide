"""Cross-version benchmark table for the web demo: every stored model run, read only from saved artifacts.

python -m preslide.benchmarks   ->  data/web/benchmarks.json

Nothing is recomputed. Each row says how it was evaluated (test, CV, region holdout), against which controls
(5 matched or 10 unmatched), how many independent units it rests on, and its chance level.
"""
from .common import read_json, write_json
from .sources import ROOT

MODEL = {'logistic_regression': 'Logistische Regression', 'random_forest': 'Random Forest',
         'gradient_boosting': 'Gradient Boosting', 'hist_gradient_boosting': 'Gradient Boosting',
         'conditional_logit': 'Bedingte log. Regression'}
VARIANTS = ('static', 'temporal', 'combined')


def row(run, model, variant, auc, top1=None, auc_range=None, top1_chance=1 / 6):
    return {'run': run, 'model': MODEL[model], 'model_key': model, 'variant': variant, 'local_auc': auc,
            'local_auc_range': auc_range, 'top1': top1, 'top1_chance': top1_chance}


def build():
    web = read_json(ROOT / 'data/web/results.json')
    runs, rows = [], []

    def add_run(**kw):
        runs.append(kw)
        return kw['id']

    # V0 original test (single split, seen afterwards).
    v0 = web['original_test']
    rid = add_run(id='v0_test', version='V0', label='V0 · Originaltest', evaluation='Test (einmal)', controls='5 gematchte',
                  events=v0['split']['test']['events'] if isinstance(v0['split'].get('test'), dict) else 15,
                  units=4, weighting='je Ereignis', interval='–', comparable=True)
    for m in v0['models']:
        rows.append(row(rid, m['model'], m['features'], m['within_group_auc'], m.get('first_place_rate')))
    g = v0['geographic']
    rid = add_run(id='v0_styria', version='V0', label='V0 · Steiermark-Holdout', evaluation='Region ausgelassen', controls='5 gematchte',
                  events=g['test_events'], units=None, weighting='je Ereignis', interval='–', comparable=True)
    for m in g['models']:
        rows.append(row(rid, m['model'], m['features'], m['within_group_auc']))
    # V0.2 stability CV on the original development data.
    s = web['stability_v02']
    rid = add_run(id='v02_cv', version='V0.2', label='V0.2 · Stabilitäts-CV', evaluation='Kreuzvalidierung 4×5', controls='5 gematchte',
                  events=s['events'], units=s['clusters'], weighting='je Ereignis', interval='Spannweite 5 Wiederholungen', comparable=True)
    for m in s['models']:
        a = m['within_group_auc']
        rows.append(row(rid, m['model'], m['features'], a['median'], m['first_place_rate']['median'], [a['min'], a['max']]))
    # V0.4 development CV and sealed test.
    dev = read_json(ROOT / 'reports/v04/dev_metrics.json')
    rid = add_run(id='v04_cv', version='V0.4', label='V0.4 · Entwicklungs-CV', evaluation='Kreuzvalidierung 5×5', controls='5 gematchte',
                  events=dev['development']['events'], units=dev['development']['units'], weighting='je Einheit',
                  interval='Spannweite 5 Wiederholungen', comparable=True)
    for key, r in dev['results'].items():
        m, v = key.split('/')
        rows.append(row(rid, m, v, r['median']['local_auc_weighted'], r['median']['top1_weighted'],
                        [r['min']['local_auc_weighted'], r['max']['local_auc_weighted']]))
    test = read_json(ROOT / 'reports/v04/test_results.json')
    rid = add_run(id='v04_test', version='V0.4', label='V0.4 · Versiegelter Test', evaluation='Test (einmal, versiegelt)', controls='5 gematchte',
                  events=test['test']['events'], units=test['test']['units'], weighting='je Einheit', interval='95 %-Bootstrap',
                  comparable=True)
    for key, r in test['results'].items():
        m, v = key.split('/')
        rows.append(row(rid, m, v, r['local_auc_weighted'], r['top1_weighted'], test['bootstrap'][m][v]['ci95']))
    # V0.5: different, easier task (10 unmatched controls); plus the matched comparison on the same cohort.
    v5 = read_json(ROOT / 'reports/v05/cv_results.json')
    rid = add_run(id='v05_cv', version='V0.5', label='V0.5 · Nachbarhang-CV', evaluation='Kreuzvalidierung 5×5, räumlich bereinigt',
                  controls='10 ungematchte', events=v5['cohort']['events'], units=v5['cohort']['units'], weighting='je Einheit',
                  interval='Spannweite 5 Wiederholungen', comparable=False)
    for key, r in v5['purged'].items():
        m, v = key.split('/')
        rows.append(row(rid, m, v, r['median']['local_auc_units'], r['median']['top1_units'],
                        [r['min']['local_auc_units'], r['max']['local_auc_units']], top1_chance=1 / 11))
    cv = v5['control_variants']
    rid = add_run(id='v05_matched', version='V0.5', label='V0.5 · gleiche Ereignisse, 5 gematchte', evaluation='Kreuzvalidierung, Wdh. 1',
                  controls='5 gematchte', events=cv['cohort_events'], units=cv['cohort_units'], weighting='je Einheit', interval='–',
                  comparable=True)
    for v in ('static', 'combined'):
        r = cv['a_matched_5'][v]
        rows.append(row(rid, 'conditional_logit', v, r['local_auc_units'], r['top1_units']))
    references = [{'run': 'v05_cv', 'label': 'Neigungsregel (ohne Training)', 'local_auc': v5['slope_rule']['local_auc_units'],
                   'top1': v5['slope_rule']['top1_units']}]
    return {'generated_from': ['data/web/results.json (V0, V0.2)', 'reports/v04/dev_metrics.json', 'reports/v04/test_results.json',
                               'reports/v05/cv_results.json'],
            'note': 'Gespeicherte Ergebnisse, nichts neu berechnet. V0.3 ist eine Zufallsreferenz (kein eigenes Modell) und daher nicht als Zeile enthalten.',
            'runs': runs, 'rows': rows, 'references': references}


def main():
    out = build()
    write_json(ROOT / 'data/web/benchmarks.json', out)
    print(f"data/web/benchmarks.json: {len(out['runs'])} runs, {len(out['rows'])} model rows")


if __name__ == '__main__':
    main()
