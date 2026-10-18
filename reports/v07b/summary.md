# V0.7b — V0.7 re-run with exact OpenStreetMap distances

Correction of V0.7 (exploratory; the V0.5 events are already seen, no new independent test). Registered in `config/v07b.json` (`reports/v07b/PREREGISTRATION.json`) before any corrected distance was computed. V0.7 itself (`config/v07.json`, `preslide/v07/`, `data/v07/`, `reports/v07/`) is unchanged.

## The error

The V0.7 accumulator (`preslide.v07.infrastructure.RunningMinimum`) queried, for every OSM vertex, only the single nearest *sample* and updated that sample. A sample whose nearest building or road vertex lies even nearer to another sample is never updated by that vertex; its distance is overestimated, up to the 5000 m cap. Found by the anfaelligkeit_at_v01 session (AMENDMENT_2, 2026-10-18). `tests/test_v07b.py::test_nearest_vertex_distance_is_exact_for_clustered_samples` fails on the V0.7 class (strict xfail) and passes on the fix.

## Recomputation

The unchanged V0.7 stream (way filter, road classes, 25 m densification, EPSG:31287, cap 5000 m) ran once with three accumulators: exact (every chunk of vertices gets its own KD-tree that all samples query), the V0.7 accumulator, and a brute-force distance matrix for 20 random samples. V0.7 table reproduced exactly by the V0.7 accumulator: **True**; brute-force check max deviation road 0.000 m, building 0.000 m. Exact distances are never larger than the V0.7 ones: True.

## How many samples are affected

| distance | class | samples | changed > 1 m | share | median change of changed (m) | median old → new (m) | was cap, now below |
|---|---|---:|---:|---:|---:|---|---:|
| dist_building_m | positive | 418 | 224 | 53.6% | -4722 | 213 → 117 | 187 |
| dist_building_m | control | 4180 | 2241 | 53.6% | -4602 | 904 → 277 | 1981 |
| dist_building_m | all | 4598 | 2465 | 53.6% | -4616 | 854 → 260 | 2168 |
| dist_road_m | positive | 418 | 199 | 47.6% | -4670 | 91 → 72 | 162 |
| dist_road_m | control | 4180 | 2560 | 61.2% | -4045 | 5000 → 505 | 2255 |
| dist_road_m | all | 4598 | 2759 | 60.0% | -4093 | 5000 → 425 | 2417 |
| dist_infrastructure_m | positive | 418 | 184 | 44.0% | -4735 | 71 → 57 | 146 |
| dist_infrastructure_m | control | 4180 | 2092 | 50.0% | -4601 | 578 → 244 | 1807 |
| dist_infrastructure_m | all | 4598 | 2276 | 49.5% | -4615 | 523 → 226 | 1953 |

Capped share (≥ 5000 m), old → new: building positive 0.45 → 0.00; building control 0.47 → 0.00; road positive 0.39 → 0.00; road control 0.54 → 0.00.

## Registered V0.7 analyses, old and new

Same code (`preslide.v07.experiment.main`, only the distance table and output folders rebound), same V0.5 CV plan, hyperparameters, bootstrap (2000 draws, seed 20261016). Cohort 418 events, 29 independence units, 4598 samples; unit-weighted local AUC, median of five repetitions; chance 0.5.

| metric | V0.7 | V0.7b | difference |
|---|---:|---:|---:|
| a/conditional_logit/static median local AUC | 0.865 | 0.865 | +0.000 |
| a/conditional_logit/combined median local AUC | 0.851 | 0.851 | +0.000 |
| a/conditional_logit/infra_only median local AUC | 0.928 | 0.946 | +0.017 |
| a/conditional_logit/static_infra median local AUC | 0.912 | 0.926 | +0.015 |
| a/conditional_logit/combined_infra median local AUC | 0.901 | 0.916 | +0.015 |
| a/hist_gradient_boosting/static median local AUC | 0.794 | 0.794 | +0.000 |
| a/hist_gradient_boosting/combined median local AUC | 0.798 | 0.798 | +0.000 |
| a/hist_gradient_boosting/infra_only median local AUC | 0.892 | 0.919 | +0.027 |
| a/hist_gradient_boosting/static_infra median local AUC | 0.914 | 0.909 | -0.005 |
| a/hist_gradient_boosting/combined_infra median local AUC | 0.914 | 0.926 | +0.012 |
| a/conditional_logit: static_infra - static (rep-1 mean) | 0.054 | 0.072 | +0.018 |
| a/conditional_logit: combined_infra - combined (rep-1 mean) | 0.057 | 0.080 | +0.023 |
| a/hist_gradient_boosting: static_infra - static (rep-1 mean) | 0.139 | 0.145 | +0.006 |
| a/hist_gradient_boosting: combined_infra - combined (rep-1 mean) | 0.115 | 0.135 | +0.021 |
| b/caliper groups_kept | 173 | 174 | +1.000 |
| b/caliper units_kept | 10 | 10 | +0.000 |
| b/caliper controls_kept_share | 0.308 | 0.266 | -0.042 |
| b/static all controls, same groups | 0.796 | 0.783 | -0.013 |
| b/static caliper controls | 0.783 | 0.762 | -0.021 |
| b/static difference | -0.013 | -0.021 | -0.008 |
| b/temporal all controls, same groups | 0.640 | 0.644 | +0.005 |
| b/temporal caliper controls | 0.618 | 0.622 | +0.004 |
| b/temporal difference | -0.022 | -0.022 | -0.000 |
| b/combined all controls, same groups | 0.805 | 0.796 | -0.009 |
| b/combined caliper controls | 0.782 | 0.755 | -0.027 |
| b/combined difference | -0.024 | -0.042 | -0.018 |
| b/static bootstrap difference (rep-1 mean) | -0.017 | -0.021 | -0.004 |
| b/combined bootstrap difference (rep-1 mean) | -0.067 | -0.084 | -0.018 |
| b/land-cover ablation with_lc_all_groups | 0.805 | 0.796 | -0.009 |
| b/land-cover ablation without_lc_all_groups | 0.766 | 0.762 | -0.004 |
| b/land-cover ablation with_lc_caliper | 0.782 | 0.755 | -0.027 |
| b/land-cover ablation without_lc_caliper | 0.774 | 0.760 | -0.015 |

| 95 % interval (repetition-1 unit bootstrap) | V0.7 | V0.7b |
|---|---|---|
| conditional_logit infra_only AUC | [0.888, 0.957] | [0.918, 0.967] |
| conditional_logit static_infra - static | [0.027, 0.082] | [0.041, 0.103] |
| caliper static AUC | [0.679, 0.888] | [0.665, 0.873] |
| caliper static drop | [-0.068, 0.031] | [-0.069, 0.026] |
| caliper combined drop | [-0.172, 0.005] | [-0.192, -0.002] |

Caliper groups: V0.7 173, V0.7b 174, in both 149, only V0.7 24, only V0.7b 25.

## Decision rule and registered change criteria

* V0.7 decision rule, V0.7: infrastructure-independent; V0.7b: **infrastructure-independent** (caliper static interval excludes 0.5: True; drop interval includes zero: True).
* (i) verdict differs: False; (ii) infra_only no longer above static: False; (iii) caliper keeps different groups: True.
* V0.7 conclusion changed under the registered criteria: **True**.

## Reading

* **Distance alone:** with exact distances the infrastructure distance separates the reported slope from its ten surrounding points even more strongly (conditional logit 0.928 → 0.946, interval [0.918, 0.967]; static terrain 0.865). The V0.7 bug mostly set far-away distances to the cap for positives and controls alike, which blurred the contrast; the reporting/placement-bias reading is strengthened, not weakened.
* **Equal visibility (primary endpoint):** the infrastructure-unaware static model keeps 0.762 on the caliper controls (V0.7 0.783); drop -0.021 [-0.069, 0.026], AUC interval [0.665, 0.873]. The V0.7 decision-rule verdict is the same (infrastructure-independent).
* **Registered change criteria:** fired: iii. Only (iii) fires: the caliper retains a different set of groups (same count and units, but 24 groups leave and 25 enter). Formally the V0.7 result is therefore changed: its numbers must not be cited any more, the V0.7b numbers replace them. The direction and the verdict of the V0.7 conclusion hold.
* **Secondary (combined model, not the primary endpoint):** on the caliper controls the combined conditional logit drops -0.084 [-0.192, -0.002] (V0.7 [-0.172, 0.005]), now with an upper bound just below zero (one of the seven registered comparisons, exploratory): consistent with part of the combined (land-cover-carrying) skill being related to infrastructure visibility, not proof of it.
* Effective sample size: 29 independence units overall, 10 in the caliper groups; the events were already seen (exploratory). No causal reading; OSM completeness and the 2026 snapshot limits of V0.7 apply unchanged.
