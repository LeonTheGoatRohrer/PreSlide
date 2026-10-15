"""Write reports/v08/summary.md from the stored reports/v08/cv_results.json (numbers are never typed by hand)."""
from ..common import read_json
from .paths import V08_DATA, V08_REPORT, config, guard


def ci(x) -> str:
    return f'[{x[0]:+.3f}, {x[1]:+.3f}]'


def build() -> str:
    cfg = config()
    r = read_json(V08_REPORT / 'cv_results.json')
    plan = read_json(V08_DATA / 'referent_plan.json')
    ds = read_json(V08_DATA / 'dataset.json')
    c, d = r['cohort'], r['diagnostics']
    L = ['# V0.8 — time-stratified case-crossover at the reported slope (exploratory)', '',
         f"Each stratum is one reported slope: its event time against up to four referent times (t0 ±28 d, ±56 d at the same clock time) at the identical coordinate. "
         f"{c['events']} of {ds['groups_total']} V0.5 slopes had at least {cfg['design']['min_referents_per_group']} usable referents; {c['units']} independence units "
         f"(effective sample size; one unit holds the 2016 Stanz storm with {d['events_in_largest_unit']} slopes). Registered in `config/v08.json` before any referent weather was requested. "
         "Terrain, land cover, elevation and infrastructure visibility are identical within a stratum and cancel, so this design removes the reporting-placement confounders of V0.4/V0.5; it answers *when*, not *where*.", '',
         f"Referents by outcome: {ds['referents_by_status']}. Inventory records without a usable date (cannot block referents): {plan['inventory_records_without_usable_date']} of {plan['inventory_records_considered']}.", '',
         '## Unit-weighted local AUC (median of 5 repetitions; chance 0.5)', '',
         '| Model / variant | local AUC | range | repetition-1 unit-bootstrap 95 % interval |', '|---|---:|---|---|']
    for k, v in r['variants'].items():
        L.append(f"| {k} | {v['median_local_auc_units']:.3f} | {v['range'][0]:.3f}–{v['range'][1]:.3f} | {ci(v['ci95_rep1'])} |")
    L += ['', '| Paired difference (repetition-1 unit bootstrap) | mean | 95 % interval | verdict |', '|---|---:|---|---|']
    for k, p in r['paired'].items():
        verdict = 'interval above zero (better)' if p['ci95'][0] > 0 else 'interval below zero (worse)' if p['ci95'][1] < 0 else 'no established difference'
        L.append(f"| {k} | {p['mean']:+.3f} | {ci(p['ci95'])} | {verdict} |")
    ref = r['neighbour_slope_reference_same_groups']
    L += ['', '## Diagnostics', '',
          f"* Without the largest unit: {d['without_largest_unit']['median_local_auc_units']:.3f} ({d['without_largest_unit']['events']} slopes, {d['without_largest_unit']['units']} units).",
          '* By time quality of the event (conditional logit, temporal): ' + '; '.join(f"{k} {v['median_local_auc_units']:.3f} ({v['events']} events, {v['units']} units)" for k, v in d['by_time_quality'].items()) + '. '
          'For time quality `day` the same-day rain features are missing, so skill there comes from the history before the event day.',
          '* By referent side: ' + '; '.join(f"{k} {v['median_local_auc_units']:.3f}" for k, v in d['by_referent_side'].items()) + '.',
          f"* Neighbour-slope (spatial) design on the same slopes, conditional logit: temporal {ref['v05_temporal']['median_local_auc_units']:.3f}, temporal+hydro {ref['v06_temporal_hydro']['median_local_auc_units']:.3f} (V0.5/V0.6 stored predictions).",
          '', '## Reading', '',
          'Decision rule (registered): weather is informative about *when* a reported slope fails only if the primary interval excludes 0.5; the hydrological features are an added benefit only if the paired interval excludes zero. '
          'A large part of the contrast is expected by construction: the inventory records landslides mainly in documented heavy-rain episodes, so event times are wetter than arbitrary referent times 4–8 weeks away, '
          'and temperature windows partly encode season. The result therefore shows that documented failure times are distinguishable from ordinary times, not that rain forecasts a failure on a given slope. '
          'More hydrological features on 376 strata can overfit (conditional logit), which the paired comparison shows. '
          f"Limits: {cfg['interpretation_limits']}", '']
    return '\n'.join(L)


if __name__ == '__main__':
    (guard(V08_REPORT) / 'summary.md').write_text(build(), encoding='utf-8')
    print(build())
