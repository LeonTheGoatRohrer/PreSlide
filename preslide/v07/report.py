"""Write reports/v07/summary.md from the stored reports/v07/cv_results.json (numbers are never typed by hand)."""
from ..common import read_json
from .paths import V07_REPORT, config, guard


def ci(x) -> str:
    return f'[{x[0]:+.3f}, {x[1]:+.3f}]'


def build() -> str:
    cfg = config()
    r = read_json(V07_REPORT / 'cv_results.json')
    c, a, b, bc, d = r['cohort'], r['a_in_model'], r['b_equal_visibility'], r['b_caliper'], r['diagnostics']
    L = ['# V0.7 — reporting-bias control with OpenStreetMap infrastructure distances (exploratory)', '',
         f"Cohort: frozen V0.5 cohort, {c['events']} events, {c['units']} independence units, {c['samples']} samples. Registered in `config/v07.json` before any distance was computed. "
         f"Source: {cfg['source']['provider']}, `{cfg['source']['file']}` ({cfg['source']['size_bytes']:,} bytes), {cfg['source']['licence']}. "
         f"Snapshot 2026-10-14 for events from 2016: {cfg['source']['temporal_caveat']}. Effective sample size = {c['units']} independence units; exploratory, no new independent test.", '',
         '## (a) Infrastructure distance in the model (unit-weighted local AUC, median of 5 repetitions; chance 0.5)', '',
         '| Model / variant | local AUC | range |', '|---|---:|---|']
    for k, v in a.items():
        if 'median_local_auc_units' in v:
            L.append(f"| {k} | {v['median_local_auc_units']:.3f} | {v['range'][0]:.3f}–{v['range'][1]:.3f} |")
    L += ['', '| Paired difference (repetition-1 unit bootstrap) | mean | 95 % interval |', '|---|---:|---|']
    for model in ('conditional_logit', 'hist_gradient_boosting'):
        for name in ('static_infra - static', 'combined_infra - combined'):
            p = a[f'{model}/paired'][name]
            L.append(f"| {model}: {name} | {p['mean']:+.3f} | {ci(p['ci95'])} |")
        L.append(f"| {model}: infra_only AUC interval | – | {ci(a[f'{model}/paired']['infra_only_ci95'])} |")
    L += ['', '## (b) Equal visibility: controls within a factor 2 of the positive in distance to infrastructure', '',
          f"Caliper keeps {bc['groups_kept']} of {bc['groups_total']} groups ({bc['units_kept']} units) with at least {cfg['analyses']['b_equal_visibility']['min_controls_per_group']} retained controls; "
          f"{bc['controls_kept_share']:.0%} of all controls are inside the caliper. Stored V0.5 out-of-fold scores (models without infrastructure features) are re-ranked among the retained controls.", '',
          '| Conditional logit variant | all controls, same groups | caliper controls | difference |', '|---|---:|---:|---:|']
    for v in ('static', 'temporal', 'combined'):
        e = b[f'conditional_logit/{v}']
        L.append(f"| {v} | {e['all_controls_same_groups']['median_local_auc_units']:.3f} | {e['caliper_controls']['median_local_auc_units']:.3f} | {e['difference']:+.3f} |")
    for v in ('static', 'combined'):
        e = b[f'conditional_logit/{v}']['bootstrap_rep1_difference']
        L.append(f"| bootstrap {v} difference (repetition 1) | – | – | {e['mean']:+.3f} {ci(e['ci95'])} |")
    abl = b['land_cover_ablation_combined']
    L += ['', f"Caliper static AUC bootstrap interval: {ci(b['bootstrap_ci95_caliper_static'])}.",
          '', 'Land-cover ablation (conditional logit combined, median local AUC):', '',
          '| | with land cover | without land cover |', '|---|---:|---:|',
          f"| all retained groups | {abl['with_lc_all_groups']['median_local_auc_units']:.3f} | {abl['without_lc_all_groups']['median_local_auc_units']:.3f} |",
          f"| caliper controls | {abl['with_lc_caliper']['median_local_auc_units']:.3f} | {abl['without_lc_caliper']['median_local_auc_units']:.3f} |",
          '', '## Diagnostics', '',
          f"* Capped (>= {cfg['infrastructure']['distance_cap_m']} m) shares, positive / control: building {d['capped_share']['building_capped']['positive']:.2f} / {d['capped_share']['building_capped']['control']:.2f}, "
          f"road {d['capped_share']['road_capped']['positive']:.2f} / {d['capped_share']['road_capped']['control']:.2f}.",
          '* Spearman correlation of dist_infrastructure_m: ' + ', '.join(f'{k} {v:+.2f}' for k, v in d['spearman_dist_infrastructure'].items()) + '.',
          '', '## Reading', '',
          'Distance to infrastructure alone ranks the reported slope above its ten surrounding points about as well as, or better than, terrain and land cover. '
          'This is what reporting/placement bias predicts, and it is also partly built into the design: the controls lie 0.75–10 km around the reported slope and so are on average farther from roads and buildings. '
          'The caliper analysis removes that contrast in the retained groups; the unaware terrain models keep most of their skill there, but those groups are only a minority of the data and units and the intervals are wide. '
          'Nothing here shows that terrain or land cover cause landslides or that the retained skill is free of reporting effects: the test only equalises distance to mapped infrastructure. '
          f"Limits: {cfg['interpretation_limits']}", '']
    return '\n'.join(L)


if __name__ == '__main__':
    (guard(V07_REPORT) / 'summary.md').write_text(build(), encoding='utf-8')
    print(build())
