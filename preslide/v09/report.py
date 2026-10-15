"""reports/v09/summary.md from the stored V0.9 JSON results (no computation of new numbers).

  python -m preslide.v09.report
"""
from collections import Counter

from ..common import read_json
from .experiment import COHORTS, RESULT, run_dir
from .paths import V09_REPORT, config as load_config

MODELS = ('conditional_logit', 'logistic_regression', 'hist_gradient_boosting')
VARIANTS = ('static', 'temporal', 'combined')


def exclusion_counts():
    status = read_json(run_dir() / 'status.json')
    out = Counter()
    for stages in status.values():
        for stage, s in stages.items():
            if s['state'] in ('excluded', 'incomplete'):
                reason = s.get('reason', '').split(':')[0]
                out[f'{stage}: {reason}'] += 1
    return dict(sorted(out.items()))


def ci(x):
    return f"[{x[0]:+.3f}, {x[1]:+.3f}]"


def main():
    cfg = load_config()
    cohort = read_json(V09_REPORT / 'cohort_summary.json')['counts']
    audit = read_json(V09_REPORT / 'process_audit_summary.json')
    part = read_json(V09_REPORT / 'partition_summary.json')
    res = read_json(RESULT)
    p = res['primary']
    lines = [
        '# V0.9 — unseen media and Kärnten episodes, single scoring of the V0.4 recipe',
        '',
        f"Registered in `config/v09.json` (SHA-256 `{read_json(V09_REPORT / 'PREREGISTRATION.json')['config_sha256'][:12]}…`) before "
        'cohort selection, process audit, matching, retrieval and any model fit. Scored once '
        f"({res['scored_at'][:19]} UTC) after `reports/v09/FREEZE.json`. Status: {cfg['status']}.",
        '',
        '## Primary result',
        '',
        f"Media cohort, conditional logit, V0.4 recipe refit on all 423 V0.4 groups: combined "
        f"{p['combined']['local_auc_weighted']:.3f}, static {p['static']['local_auc_weighted']:.3f} "
        f"(unit-weighted within-group AUC, chance 0.5; {p['combined']['events']} events, {p['media_units']} independence units).",
        f"Paired combined − static: {p['combined_minus_static']['mean']:+.3f} {ci(p['combined_minus_static']['ci95'])}.",
        f"Process-audit gate passed: {p['quality_gate_passes']}; at least "
        f"{cfg['evaluation']['minimum_units_for_confirmatory_claim']} units: {p['media_units'] >= cfg['evaluation']['minimum_units_for_confirmatory_claim']}.",
        f"**Verdict (registered decision rule): {p['verdict']}.**",
        '',
        '## Cohort flow',
        '',
        '| Step | Media | Kärnten |',
        '|---|---:|---:|',
        f"| Source records in scope | {cohort['media_rows']} (tier 2, day tier A) | 1 038 slide-type 2011+ before dedup (see cohort_summary) |",
        f"| Excluded before blocks | {cohort['media_process_conflict_other_source']} process conflict, "
        f"{cohort['media_exact_location_day_duplicate']} duplicates | "
        + ', '.join(f'{v} {k}' for k, v in cohort['kaernten_excluded'].items()) + ' |',
        f"| Candidates | {cohort['media_candidates']} | {cohort['kaernten_candidates']} |",
        f"| In a block with a seen V0.4 event | {cohort['media_in_seen_block']} | {cohort['kaernten_in_seen_block']} |",
        f"| Eligible unseen (blocks) | {cohort['media_eligible_unseen']} ({cohort['media_eligible_blocks']}) | "
        f"{cohort['kaernten_eligible_unseen']} ({cohort['kaernten_eligible_blocks']}) |",
        f"| Process audit excluded (other process / date conflict) | {len(audit['excluded'])} | – |",
    ]
    by = part['by_cohort']
    lines += [f"| Analysed groups (independence units) | {by.get('media', {}).get('groups', 0)} ({by.get('media', {}).get('units', 0)}) | "
              f"{by.get('kaernten', {}).get('groups', 0)} ({by.get('kaernten', {}).get('units', 0)}) |", '']
    lines += ['Pipeline exclusions by stage and reason (both cohorts): ' +
              ', '.join(f'{k} {v}' for k, v in exclusion_counts().items()) + '.',
              f"Groups removed by the 1 km seen-location purge: {len(part['purged_seen_location'])}. Pooled units: {part['pooled_units']}.", '',
              f"Process audit ({audit['events']} media events): {audit['gate']['counts']}; verifiable n = {audit['gate']['n_verifiable']}, "
              f"other process k = {audit['gate']['k_other_process']}, Wilson 95 % upper bound {audit['gate']['wilson_upper_95']:.3f}.", '']
    lines += ['## All registered comparisons', '',
              'Unit-weighted within-group AUC (chance 0.5), all 72 values; p = upper-tail share of the random-rank null.', '',
              '| Model set | Cohort | Model | static | temporal | combined | combined − static [95 %] | events / units |',
              '|---|---|---|---:|---:|---:|---|---|']
    for ms in ('refit_all', 'frozen_v04_dev'):
        for c in COHORTS:
            for m in MODELS:
                key = f'{ms}/{c}/{m}'
                if f'{key}/static' not in res['results']:
                    continue
                r = {v: res['results'][f'{key}/{v}'] for v in VARIANTS}
                d = res['bootstrap'][key]['combined_minus_static']
                lines.append(f"| {ms} | {c} | {m} | " + ' | '.join(f"{r[v]['local_auc_weighted']:.3f} (p {r[v]['p_upper_vs_random_rank']:.3f})"
                                                                for v in VARIANTS)
                             + f" | {d['mean']:+.3f} {ci(d['ci95'])} | {r['static']['events']} / {r['static']['units']} |")
    lines += ['', '## Secondary analyses (refit_all, conditional logit, media)', '']
    for k, v in res['secondary'].items():
        if isinstance(v, dict):
            lines.append(f"* {k}: static {v['local_auc_weighted']['static']:.3f}, combined {v['local_auc_weighted']['combined']:.3f}, "
                         f"combined − static {v['combined_minus_static']['mean']:+.3f} {ci(v['combined_minus_static']['ci95'])} "
                         f"({v['events']} events, {v['units']} units)" + (f"; removed {v['removed_unit']}" if 'removed_unit' in v else ''))
        else:
            lines.append(f'* {k}: {v}')
    lines += ['', '## Reading', '',
              '* Effective sample size is the number of independence units, not the number of rows or events.',
              '* Media positions come from GeoSphere\'s evaluation of online reports (20–100 m class); the process label was '
              'checked against public reports for every analysed media event, but reports cluster near roads and houses, so '
              'land-cover and terrain contrasts can still carry reporting bias.',
              '* The Kärnten cohort uses t0 three days before the reported day (no verified day precision): it tests '
              'antecedent conditions only and cannot see trigger rain. Its positions have no accuracy field.',
              '* All 72 values are reported; only the primary comparison carries the registered decision rule. Everything '
              'else is exploratory.', '']
    (V09_REPORT / 'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines[:20]))


if __name__ == '__main__':
    main()
