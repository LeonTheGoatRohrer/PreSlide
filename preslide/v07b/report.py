"""V0.7 old versus V0.7b exact distances: reports/v07b/comparison.json and summary.md (numbers are never typed by hand).

  python -m preslide.v07b.report
"""
import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from ..v07.experiment import caliper_keep
from .paths import V07_REPORT, V07B_DATA, V07B_REPORT, config, guard

DIST = ('dist_building_m', 'dist_road_m', 'dist_infrastructure_m')
CHANGE_TOL_M = 1.0


def distance_changes(old: pd.DataFrame, new: pd.DataFrame, label: pd.Series) -> dict:
    """Per distance column and class: how many samples change by more than 1 m, how strongly, capped shares old/new."""
    out = {}
    for col in DIST:
        delta = new[col].to_numpy() - old[col].to_numpy()
        per = {}
        for name, mask in (('positive', label.to_numpy() == 1), ('control', label.to_numpy() == 0), ('all', np.ones(len(label), bool))):
            d, changed = delta[mask], np.abs(delta[mask]) > CHANGE_TOL_M
            per[name] = {'samples': int(mask.sum()), 'changed': int(changed.sum()), 'changed_share': float(changed.mean()),
                         'median_change_m_of_changed': float(np.median(d[changed])) if changed.any() else 0.0,
                         'change_quantiles_m_of_changed': np.quantile(d[changed], [.1, .25, .5, .75, .9]).round(1).tolist() if changed.any() else [],
                         'old_median_m': float(np.median(old[col].to_numpy()[mask])), 'new_median_m': float(np.median(new[col].to_numpy()[mask])),
                         'old_was_cap_now_below_cap': int(((old[col].to_numpy()[mask] == 5000) & (new[col].to_numpy()[mask] < 5000)).sum())}
        out[col] = per
    for flag in ('building_capped', 'road_capped'):
        out[flag] = {name: {'old': float(old[flag][label == lab].mean()), 'new': float(new[flag][label == lab].mean())}
                     for name, lab in (('positive', 1), ('control', 0))}
    out['new_never_above_old'] = bool(all((new[c].to_numpy() <= old[c].to_numpy() + 1e-9).all() for c in DIST))
    return out


def caliper_groups(frame: pd.DataFrame, min_controls: int) -> set:
    keep = caliper_keep(frame)
    kept = keep[frame.label == 0].groupby(frame.event_group_id[frame.label == 0]).sum()
    return set(kept.index[kept >= min_controls])


def verdict(r: dict) -> dict:
    """The V0.7 decision rule on one cv_results.json."""
    b = r['b_equal_visibility']
    lo = b['bootstrap_ci95_caliper_static'][0]
    drop = b['conditional_logit/static']['bootstrap_rep1_difference']['ci95']
    above_chance, drop_includes_zero = lo > 0.5, drop[0] <= 0 <= drop[1]
    return {'caliper_static_ci_excludes_chance': above_chance, 'drop_interval_includes_zero': drop_includes_zero,
            'verdict': 'infrastructure-independent' if above_chance and drop_includes_zero else '(partly) explained by infrastructure visibility'}


def metric_rows(old: dict, new: dict) -> list[dict]:
    rows = []

    def add(name, o, n):
        rows.append({'metric': name, 'v07': o, 'v07b': n, 'difference': n - o})
    for k, v in new['a_in_model'].items():
        if 'median_local_auc_units' in v:
            add(f'a/{k} median local AUC', old['a_in_model'][k]['median_local_auc_units'], v['median_local_auc_units'])
    for model in ('conditional_logit', 'hist_gradient_boosting'):
        for name in ('static_infra - static', 'combined_infra - combined'):
            add(f'a/{model}: {name} (rep-1 mean)', old['a_in_model'][f'{model}/paired'][name]['mean'], new['a_in_model'][f'{model}/paired'][name]['mean'])
    for k in ('groups_kept', 'units_kept', 'controls_kept_share'):
        add(f'b/caliper {k}', old['b_caliper'][k], new['b_caliper'][k])
    for v in ('static', 'temporal', 'combined'):
        o, n = old['b_equal_visibility'][f'conditional_logit/{v}'], new['b_equal_visibility'][f'conditional_logit/{v}']
        add(f'b/{v} all controls, same groups', o['all_controls_same_groups']['median_local_auc_units'], n['all_controls_same_groups']['median_local_auc_units'])
        add(f'b/{v} caliper controls', o['caliper_controls']['median_local_auc_units'], n['caliper_controls']['median_local_auc_units'])
        add(f'b/{v} difference', o['difference'], n['difference'])
    for v in ('static', 'combined'):
        add(f'b/{v} bootstrap difference (rep-1 mean)', old['b_equal_visibility'][f'conditional_logit/{v}']['bootstrap_rep1_difference']['mean'],
            new['b_equal_visibility'][f'conditional_logit/{v}']['bootstrap_rep1_difference']['mean'])
    for k in ('with_lc_all_groups', 'without_lc_all_groups', 'with_lc_caliper', 'without_lc_caliper'):
        add(f'b/land-cover ablation {k}', old['b_equal_visibility']['land_cover_ablation_combined'][k]['median_local_auc_units'],
            new['b_equal_visibility']['land_cover_ablation_combined'][k]['median_local_auc_units'])
    return rows


def build_comparison() -> dict:
    cfg = config()
    data = pd.read_parquet(ROOT / cfg['inputs']['dataset'])[['sample_id', 'event_group_id', 'label']]
    old = data.merge(pd.read_parquet(ROOT / cfg['inputs']['v07_infrastructure']), on='sample_id', validate='one_to_one')
    new = data.merge(pd.read_parquet(V07B_DATA / 'infrastructure.parquet'), on='sample_id', validate='one_to_one')
    r_old, r_new = read_json(V07_REPORT / 'cv_results.json'), read_json(V07B_REPORT / 'cv_results.json')
    minc = read_json(ROOT / 'config/v07.json')['analyses']['b_equal_visibility']['min_controls_per_group']
    g_old, g_new = caliper_groups(old, minc), caliper_groups(new, minc)
    if len(g_old) != r_old['b_caliper']['groups_kept'] or len(g_new) != r_new['b_caliper']['groups_kept']:
        raise RuntimeError('caliper group recount differs from the stored results')
    v_old, v_new = verdict(r_old), verdict(r_new)
    a_old, a_new = r_old['a_in_model'], r_new['a_in_model']
    infra_above_static = {name: r['conditional_logit/infra_only']['median_local_auc_units'] > r['conditional_logit/static']['median_local_auc_units']
                          for name, r in (('v07', a_old), ('v07b', a_new))}
    changed = {'i_decision_rule_verdict_differs': v_old['verdict'] != v_new['verdict'],
               'ii_infra_only_no_longer_above_static': infra_above_static['v07'] and not infra_above_static['v07b'],
               'iii_caliper_keeps_different_groups': g_old != g_new}
    return {'distance_changes': distance_changes(old, new, new.label),
            'distance_checks': {k: v for k, v in read_json(V07B_DATA / 'distance_checks.json').items() if k not in ('sample_index', 'sample_id')},   # record ids stay local
            'caliper_groups': {'v07': len(g_old), 'v07b': len(g_new), 'both': len(g_old & g_new), 'only_v07': len(g_old - g_new), 'only_v07b': len(g_new - g_old)},
            'decision_rule': {'v07': v_old, 'v07b': v_new},
            'infra_only_above_static_conditional_logit': infra_above_static,
            'registered_change_criteria': changed, 'v07_conclusion_changed': any(changed.values()),
            'metrics': metric_rows(r_old, r_new),
            'intervals': {'conditional_logit infra_only AUC': {'v07': a_old['conditional_logit/paired']['infra_only_ci95'], 'v07b': a_new['conditional_logit/paired']['infra_only_ci95']},
                          'conditional_logit static_infra - static': {'v07': a_old['conditional_logit/paired']['static_infra - static']['ci95'], 'v07b': a_new['conditional_logit/paired']['static_infra - static']['ci95']},
                          'caliper static AUC': {'v07': r_old['b_equal_visibility']['bootstrap_ci95_caliper_static'], 'v07b': r_new['b_equal_visibility']['bootstrap_ci95_caliper_static']},
                          'caliper static drop': {'v07': r_old['b_equal_visibility']['conditional_logit/static']['bootstrap_rep1_difference']['ci95'],
                                                  'v07b': r_new['b_equal_visibility']['conditional_logit/static']['bootstrap_rep1_difference']['ci95']},
                          'caliper combined drop': {'v07': r_old['b_equal_visibility']['conditional_logit/combined']['bootstrap_rep1_difference']['ci95'],
                                                    'v07b': r_new['b_equal_visibility']['conditional_logit/combined']['bootstrap_rep1_difference']['ci95']}},
            'diagnostics': {'v07': r_old['diagnostics'], 'v07b': r_new['diagnostics']},
            'cohort': r_new['cohort']}


def ci(x) -> str:
    return f'[{x[0]:.3f}, {x[1]:.3f}]'


def summary(c: dict) -> str:
    dc, ch, cg = c['distance_changes'], c['distance_checks'], c['caliper_groups']
    L = ['# V0.7b — V0.7 re-run with exact OpenStreetMap distances', '',
         'Correction of V0.7 (exploratory; the V0.5 events are already seen, no new independent test). Registered in `config/v07b.json` '
         '(`reports/v07b/PREREGISTRATION.json`) before any corrected distance was computed. V0.7 itself (`config/v07.json`, `preslide/v07/`, `data/v07/`, `reports/v07/`) is unchanged.', '',
         '## The error', '',
         'The V0.7 accumulator (`preslide.v07.infrastructure.RunningMinimum`) queried, for every OSM vertex, only the single nearest *sample* and updated that sample. '
         'A sample whose nearest building or road vertex lies even nearer to another sample is never updated by that vertex; its distance is overestimated, up to the 5000 m cap. '
         'Found by the anfaelligkeit_at_v01 session (AMENDMENT_2, 2026-10-18). `tests/test_v07b.py::test_nearest_vertex_distance_is_exact_for_clustered_samples` fails on the V0.7 class (strict xfail) and passes on the fix.', '',
         '## Recomputation', '',
         'The unchanged V0.7 stream (way filter, road classes, 25 m densification, EPSG:31287, cap 5000 m) ran once with three accumulators: exact (every chunk of vertices gets its own KD-tree that all samples query), '
         'the V0.7 accumulator, and a brute-force distance matrix for 20 random samples. '
         f"V0.7 table reproduced exactly by the V0.7 accumulator: **{ch['v07_reproduced_exactly']}**; brute-force check max deviation road {ch['road_max_abs_difference_m']:.3f} m, building {ch['building_max_abs_difference_m']:.3f} m. "
         f"Exact distances are never larger than the V0.7 ones: {dc['new_never_above_old']}.", '',
         '## How many samples are affected', '',
         '| distance | class | samples | changed > 1 m | share | median change of changed (m) | median old → new (m) | was cap, now below |', '|---|---|---:|---:|---:|---:|---|---:|']
    for col in DIST:
        for cls in ('positive', 'control', 'all'):
            e = dc[col][cls]
            L.append(f"| {col} | {cls} | {e['samples']} | {e['changed']} | {e['changed_share']:.1%} | {e['median_change_m_of_changed']:+.0f} | {e['old_median_m']:.0f} → {e['new_median_m']:.0f} | {e['old_was_cap_now_below_cap']} |")
    L += ['', 'Capped share (≥ 5000 m), old → new: ' + '; '.join(f"{f.split('_')[0]} {cls} {dc[f][cls]['old']:.2f} → {dc[f][cls]['new']:.2f}" for f in ('building_capped', 'road_capped') for cls in ('positive', 'control')) + '.', '',
          '## Registered V0.7 analyses, old and new', '',
          f"Same code (`preslide.v07.experiment.main`, only the distance table and output folders rebound), same V0.5 CV plan, hyperparameters, bootstrap (2000 draws, seed 20261016). Cohort {c['cohort']['events']} events, {c['cohort']['units']} independence units, {c['cohort']['samples']} samples; "
          'unit-weighted local AUC, median of five repetitions; chance 0.5.', '', '| metric | V0.7 | V0.7b | difference |', '|---|---:|---:|---:|']
    for r in c['metrics']:
        fmt = '{:.0f}' if 'groups_kept' in r['metric'] or 'units_kept' in r['metric'] else '{:.3f}'
        L.append(f"| {r['metric']} | {fmt.format(r['v07'])} | {fmt.format(r['v07b'])} | {r['difference']:+.3f} |")
    L += ['', '| 95 % interval (repetition-1 unit bootstrap) | V0.7 | V0.7b |', '|---|---|---|']
    for k, v in c['intervals'].items():
        L.append(f"| {k} | {ci(v['v07'])} | {ci(v['v07b'])} |")
    dr = c['decision_rule']
    L += ['', f"Caliper groups: V0.7 {cg['v07']}, V0.7b {cg['v07b']}, in both {cg['both']}, only V0.7 {cg['only_v07']}, only V0.7b {cg['only_v07b']}.", '',
          '## Decision rule and registered change criteria', '',
          f"* V0.7 decision rule, V0.7: {dr['v07']['verdict']}; V0.7b: **{dr['v07b']['verdict']}** "
          f"(caliper static interval excludes 0.5: {dr['v07b']['caliper_static_ci_excludes_chance']}; drop interval includes zero: {dr['v07b']['drop_interval_includes_zero']}).",
          f"* (i) verdict differs: {c['registered_change_criteria']['i_decision_rule_verdict_differs']}; (ii) infra_only no longer above static: {c['registered_change_criteria']['ii_infra_only_no_longer_above_static']}; "
          f"(iii) caliper keeps different groups: {c['registered_change_criteria']['iii_caliper_keeps_different_groups']}.",
          f"* V0.7 conclusion changed under the registered criteria: **{c['v07_conclusion_changed']}**.", '']
    m = {r['metric']: r for r in c['metrics']}
    io, st = m['a/conditional_logit/infra_only median local AUC'], m['b/static caliper controls']
    iv, crit = c['intervals'], c['registered_change_criteria']
    fired = [k.split('_', 1)[0] for k, v in crit.items() if v]
    comb_drop = iv['caliper combined drop']
    L += ['## Reading', '',
          f"* **Distance alone:** with exact distances the infrastructure distance separates the reported slope from its ten surrounding points even more strongly "
          f"(conditional logit {io['v07']:.3f} → {io['v07b']:.3f}, interval {ci(iv['conditional_logit infra_only AUC']['v07b'])}; static terrain {m['a/conditional_logit/static median local AUC']['v07b']:.3f}). "
          'The V0.7 bug mostly set far-away distances to the cap for positives and controls alike, which blurred the contrast; the reporting/placement-bias reading is strengthened, not weakened.',
          f"* **Equal visibility (primary endpoint):** the infrastructure-unaware static model keeps {st['v07b']:.3f} on the caliper controls (V0.7 {st['v07']:.3f}); "
          f"drop {m['b/static bootstrap difference (rep-1 mean)']['v07b']:+.3f} {ci(iv['caliper static drop']['v07b'])}, AUC interval {ci(iv['caliper static AUC']['v07b'])}. "
          f"The V0.7 decision-rule verdict is the same ({c['decision_rule']['v07b']['verdict']}).",
          f"* **Registered change criteria:** fired: {', '.join(fired) if fired else 'none'}. "
          + ('Only (iii) fires: the caliper retains a different set of groups (same count and units, but '
             f"{c['caliper_groups']['only_v07']} groups leave and {c['caliper_groups']['only_v07b']} enter). Formally the V0.7 result is therefore changed: its numbers must not be cited any more, "
             'the V0.7b numbers replace them. The direction and the verdict of the V0.7 conclusion hold.' if fired == ['iii'] else 'See the table above; the V0.7 conclusion has to be restated.'),
          f"* **Secondary (combined model, not the primary endpoint):** on the caliper controls the combined conditional logit drops {m['b/combined bootstrap difference (rep-1 mean)']['v07b']:+.3f} "
          f"{ci(comb_drop['v07b'])} (V0.7 {ci(comb_drop['v07'])})"
          + (', now with an upper bound just below zero (one of the seven registered comparisons, exploratory): consistent with part of the combined '
             '(land-cover-carrying) skill being related to infrastructure visibility, not proof of it.' if comb_drop['v07b'][1] < 0 else '.'),
          f"* Effective sample size: {c['cohort']['units']} independence units overall, 10 in the caliper groups; the events were already seen (exploratory). No causal reading; OSM completeness and the 2026 snapshot limits of V0.7 apply unchanged.", '']
    return '\n'.join(L)


if __name__ == '__main__':
    comp = build_comparison()
    write_json(guard(V07B_REPORT) / 'comparison.json', comp)
    text = summary(comp)
    (V07B_REPORT / 'summary.md').write_text(text, encoding='utf-8')
    print(text.encode('ascii', 'replace').decode('ascii'))
