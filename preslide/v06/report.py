"""Write reports/v06/summary.md from the stored reports/v06/cv_results.json (numbers are never typed by hand)."""
from ..common import read_json
from .experiment import PRIMARY
from .paths import V06_REPORT, config, guard


def fmt(x: float) -> str:
    return f'{x:+.3f}'


def build() -> str:
    cfg = config()
    r = read_json(V06_REPORT / 'cv_results.json')
    c = r['cohort']
    lines = ['# V0.6 — hydrological rain features (exploratory)', '',
             f"Cohort: frozen V0.5 cohort, {c['events']} events, {c['units']} independence units, {c['samples']} samples "
             f"(one reported slope against ten unmatched surrounding slopes). Registered in `config/v06.json` before any feature was computed. "
             f"Grouped, spatially purged cross-validation on events already seen in V0.4/V0.5: **exploratory, no new independent test**. "
             f"Effective sample size = {c['units']} independence units (temporal episodes), not {c['events']} events.", '',
             '## Unit-weighted local AUC (median over 5 repetitions; chance 0.5)', '',
             '| Model / variant | local AUC | range over repetitions | top-1 | MRR |', '|---|---:|---|---:|---:|']
    for name, v in sorted(r['variants'].items()):
        lo, hi = v['range_local_auc_units']
        lines.append(f"| {name} | {v['median_local_auc_units']:.3f} | {lo:.3f}–{hi:.3f} | {v['median_top1_units']:.3f} | {v['median_mrr_units']:.3f} |")
    lines += ['', f"## Paired differences ({r['paired_comparisons_counted']} comparisons, all reported)", '',
              '| Comparison | median over repetitions | repetition-1 unit bootstrap 95 % interval | verdict |', '|---|---:|---|---|']
    for name, v in r['paired'].items():
        lo, hi = v['bootstrap_rep1']['ci95']
        verdict = 'interval excludes zero' if lo > 0 or hi < 0 else 'no established benefit'
        lines.append(f"| {name}{' (primary)' if name == PRIMARY else ''} | {fmt(v['median'])} | [{fmt(lo)}, {fmt(hi)}] | {verdict} |")
    nl = r['without_largest_unit_conditional_logit']
    lines += ['', '## Sensitivity and redundancy', '',
              f"* Conditional logit without the largest unit ({nl['unit']}): " +
              '; '.join(f"{k} {fmt(v['median'])}" for k, v in nl.items() if k != 'unit') + '.',
              f"* Highest absolute Spearman correlation of a hydrological feature with a V0.5 temporal feature: "
              f"{max(r['max_abs_spearman_with_v05_temporal'].values()):.2f} "
              f"(median over features {sorted(r['max_abs_spearman_with_v05_temporal'].values())[len(r['max_abs_spearman_with_v05_temporal']) // 2]:.2f}).",
              '', '## Reading', '',
              'Decision rule (registered): a hydrological benefit counts as established only if the paired interval excludes zero. '
              'The bootstrap resamples the independence units of the first repetition; the repetitions reuse the same events and are not independent confirmations. '
              'Feature importance is predictive, not causal. INCA is a 1 km hourly product and rain after t0 on the event day is invisible. '
              f"Limits: {cfg['interpretation_limits']}", '']
    return '\n'.join(lines)


if __name__ == '__main__':
    (guard(V06_REPORT) / 'summary.md').write_text(build(), encoding='utf-8')
    print(build())
