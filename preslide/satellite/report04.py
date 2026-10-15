"""Write reports/satellite/satellite_0_4_summary.md from the stored satellite-0.4 results (numbers are never typed by hand)."""
import pandas as pd

from ..common import read_json
from .change04 import config04
from .paths import SAT_DATA, SAT_REPORT, guard


def build() -> str:
    cfg = config04()
    base = read_json(SAT_REPORT / 'baseline_0_4.json')
    disc = read_json(SAT_REPORT / 'discovery_0_4.json')['summary']
    status = read_json(SAT_DATA / 'tables/dataset_norm_status.json')
    ref = pd.read_parquet(SAT_DATA / 'tables/position_refinement.parquet')
    ref0 = read_json(SAT_REPORT / 'heldout_discovery_results.json')
    d = base['dataset']
    L = ['# Pipeline B — satellite-0.4 (normalised change, persistence, filters; exploratory)', '',
         f"Registered in `config/satellite_0_4.json` before any result was computed. Cohort: {d['groups']} events with matched controls ({d['rows']} samples), {d['units']} independence units "
         f"(effective sample size; event-held-out folds). Reference and confirm acquisitions were found for {status['reference_ok_share']:.0%} / {status['confirm_ok_share']:.0%} of the samples "
         f"(positives: {status['reference_by_label']['1']:.0%} / {status['confirm_by_label']['1']:.0%}; controls: {status['reference_by_label']['0']:.0%} / {status['confirm_by_label']['0']:.0%}); missing values stay NaN.", '',
         '## Event-held-out baselines (mean of 3 seeds)', '', '| feature set / model | within-group AUC (unit-weighted) | top-1 rate |', '|---|---:|---:|']
    for k, v in base['models'].items():
        L.append(f"| {k} | {v['within_group_auc_unit_weighted']:.3f} | {v['top1_rate']:.3f} |")
    L += ['', '| paired difference vs change_features (unit bootstrap) | mean | 95 % interval | verdict |', '|---|---:|---|---|']
    for k, v in base['paired'].items():
        lo, hi = v['ci95']
        verdict = 'interval above zero' if lo > 0 else 'interval below zero' if hi < 0 else 'no established difference'
        L.append(f"| {k} | {v['mean_unit_weighted']:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {verdict} |")
    L += ['', '## Held-out rediscovery (logistic regression, hit radius 160 m)', '',
          f"satellite-0.2 reference (`heldout_discovery_results.json`): {ref0['detected_top3']} of {ref0['events']} events within the first three candidates, {ref0['peaks_per_km2_mean']:.2f} candidates per km².", '',
          '| feature set / filter | found any rank | top-1 | top-3 | top-5 | candidates per km² |', '|---|---:|---:|---:|---:|---:|']
    for k, v in disc.items():
        L.append(f"| {k} | {v['found_any_rank']} | {v['found_top1']} | {v['found_top3']} ({v['share_top3']:.0%}) | {v['found_top5']} | {v['peaks_per_km2_mean']:.2f} |")
    best = disc['change_features/all_filters']
    thr = cfg['stage6_unknown_region']['condition']
    reached = best['share_top3'] >= 0.5 and best['peaks_per_km2_mean'] <= 2
    L += ['', f"Stage 6 (unknown-region scan): condition `{thr}` — best all-filters variant {best['share_top3']:.0%} top-3, {best['peaks_per_km2_mean']:.2f} candidates per km² → "
          f"**{'reached' if reached else 'not reached; not executed'}**.", '',
          '## Position refinement proposals (not applied)', '',
          f"{len(ref)} rediscovered events with persistent change. Median shift {ref['shift_m'].median():.0f} m (range {ref['shift_m'].min():.0f}–{ref['shift_m'].max():.0f} m). By source position class:", '',
          '| source upper bound (m) | events | median shift (m) | shift > 50 m |', '|---:|---:|---:|---:|']
    for cls, g in ref.groupby('source_position_upper_m'):
        L.append(f"| {cls} | {len(g)} | {g['shift_m'].median():.0f} | {int((g['shift_m'] > 50).sum())} |")
    flagged = ref[(ref['source_position_upper_m'] <= 5) & (ref['shift_m'] > 50)]
    L += ['', f"{len(flagged)} events in the ≤ 5 m class shift by more than 50 m. Under the registered check this questions the centroid definition (large change masks that include harvest or shadow) and the source, not an automatic overwrite: **no position was changed**, Pipeline A is untouched.", '',
          '## Reading', '',
          f"Terrain/water and cloud-buffer filters are the useful part: they raise the first-three hits and cut false candidates. Normalised change and persistence features show no consistent benefit for the linear detector and a borderline paired gain for gradient boosting in the baseline; they did not improve the rediscovery. "
          f"Limits: {cfg['interpretation_limits']}", '']
    return '\n'.join(L)


if __name__ == '__main__':
    (guard(SAT_REPORT) / 'satellite_0_4_summary.md').write_text(build(), encoding='utf-8')
    print('written')
