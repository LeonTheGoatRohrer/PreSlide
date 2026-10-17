# V0.9 — unseen media and Kärnten episodes, single scoring of the V0.4 recipe

Registered in `config/v09.json` (SHA-256 `befb8880818e…`) before cohort selection, process audit, matching, retrieval and any model fit. Scored once (2026-10-15T13:51:28 UTC) after `reports/v09/FREEZE.json`. Status: confirmatory for the primary endpoint (media cohort, refit V0.4 recipe, combined minus static); every other comparison is secondary and labelled exploratory.

## Primary result

Media cohort, conditional logit, V0.4 recipe refit on all 423 V0.4 groups: combined 0.752, static 0.770 (unit-weighted within-group AUC, chance 0.5; 24 events, 14 independence units).
Paired combined − static: -0.019 [-0.121, +0.082].
Process-audit gate passed: False; at least 15 units: False.
**Verdict (registered decision rule): exploratory only (gate or unit minimum not met): interval includes zero.**

## Cohort flow

| Step | Media | Kärnten |
|---|---:|---:|
| Source records in scope | 323 (tier 2, day tier A) | 1 038 slide-type 2011+ before dedup (see cohort_summary) |
| Excluded before blocks | 6 process conflict, 0 duplicates | 1133 outside_period, 611 process_not_registered_slide_token, 19 no_valid_day, 14 exact_location_day_duplicate, 356 already_in_geosphere |
| Candidates | 317 | 656 |
| In a block with a seen V0.4 event | 277 | 609 |
| Eligible unseen (blocks) | 40 (22) | 47 (33) |
| Process audit excluded (other process / date conflict) | 7 | – |
| Analysed groups (independence units) | 24 (14) | 21 (16) |

Pipeline exclusions by stage and reason (both cohorts): match: insufficient_controls 7, match: positive_dem_slope_below_minimum 4, match: terrain_source_not_demonstrably_pre_event 21, weather: implausible_weather_values 1.
Groups removed by the 1 km seen-location purge: 2. Pooled units: 30.

Process audit (40 media events): {'other_process': 7, 'not_found': 24, 'slide_confirmed': 8, 'ambiguous': 1}; verifiable n = 15, other process k = 7, Wilson 95 % upper bound 0.699.

## All registered comparisons

Unit-weighted within-group AUC (chance 0.5), all 72 values; p = upper-tail share of the random-rank null.

| Model set | Cohort | Model | static | temporal | combined | combined − static [95 %] | events / units |
|---|---|---|---:|---:|---:|---|---|
| refit_all | media | conditional_logit | 0.770 (p 0.000) | 0.460 (p 0.698) | 0.752 (p 0.001) | -0.019 [-0.121, +0.082] | 24 / 14 |
| refit_all | media | logistic_regression | 0.754 (p 0.001) | 0.415 (p 0.855) | 0.781 (p 0.000) | +0.026 [-0.030, +0.100] | 24 / 14 |
| refit_all | media | hist_gradient_boosting | 0.608 (p 0.097) | 0.662 (p 0.025) | 0.731 (p 0.002) | +0.124 [+0.037, +0.214] | 24 / 14 |
| refit_all | media_slide_confirmed | conditional_logit | 0.833 (p 0.015) | 0.867 (p 0.007) | 0.933 (p 0.002) | +0.101 [-0.000, +0.200] | 5 / 3 |
| refit_all | media_slide_confirmed | logistic_regression | 0.800 (p 0.039) | 0.933 (p 0.002) | 0.867 (p 0.007) | +0.068 [-0.000, +0.100] | 5 / 3 |
| refit_all | media_slide_confirmed | hist_gradient_boosting | 0.767 (p 0.063) | 0.667 (p 0.187) | 0.867 (p 0.007) | +0.099 [-0.100, +0.400] | 5 / 3 |
| refit_all | kaernten | conditional_logit | 0.627 (p 0.057) | 0.400 (p 0.902) | 0.552 (p 0.265) | -0.076 [-0.156, -0.000] | 21 / 16 |
| refit_all | kaernten | logistic_regression | 0.635 (p 0.046) | 0.350 (p 0.974) | 0.610 (p 0.083) | -0.025 [-0.075, +0.012] | 21 / 16 |
| refit_all | kaernten | hist_gradient_boosting | 0.585 (p 0.147) | 0.415 (p 0.864) | 0.629 (p 0.052) | +0.045 [-0.144, +0.238] | 21 / 16 |
| refit_all | pooled | conditional_logit | 0.694 (p 0.000) | 0.428 (p 0.901) | 0.645 (p 0.005) | -0.048 [-0.112, +0.014] | 45 / 30 |
| refit_all | pooled | logistic_regression | 0.691 (p 0.000) | 0.380 (p 0.983) | 0.690 (p 0.000) | -0.000 [-0.040, +0.040] | 45 / 30 |
| refit_all | pooled | hist_gradient_boosting | 0.596 (p 0.047) | 0.530 (p 0.301) | 0.677 (p 0.001) | +0.082 [-0.030, +0.195] | 45 / 30 |
| frozen_v04_dev | media | conditional_logit | 0.748 (p 0.001) | 0.459 (p 0.702) | 0.696 (p 0.008) | -0.053 [-0.152, +0.012] | 24 / 14 |
| frozen_v04_dev | media | logistic_regression | 0.755 (p 0.001) | 0.576 (p 0.188) | 0.712 (p 0.004) | -0.043 [-0.114, +0.029] | 24 / 14 |
| frozen_v04_dev | media | hist_gradient_boosting | 0.637 (p 0.050) | 0.537 (p 0.335) | 0.639 (p 0.046) | +0.003 [-0.055, +0.061] | 24 / 14 |
| frozen_v04_dev | media_slide_confirmed | conditional_logit | 0.900 (p 0.004) | 0.667 (p 0.187) | 0.933 (p 0.002) | +0.033 [-0.000, +0.100] | 5 / 3 |
| frozen_v04_dev | media_slide_confirmed | logistic_regression | 0.867 (p 0.007) | 0.733 (p 0.066) | 0.867 (p 0.007) | -0.000 [-0.000, -0.000] | 5 / 3 |
| frozen_v04_dev | media_slide_confirmed | hist_gradient_boosting | 0.800 (p 0.039) | 0.633 (p 0.187) | 0.867 (p 0.007) | +0.069 [-0.000, +0.200] | 5 / 3 |
| frozen_v04_dev | kaernten | conditional_logit | 0.688 (p 0.009) | 0.469 (p 0.660) | 0.662 (p 0.021) | -0.024 [-0.088, +0.031] | 21 / 16 |
| frozen_v04_dev | kaernten | logistic_regression | 0.692 (p 0.008) | 0.335 (p 0.983) | 0.704 (p 0.004) | +0.013 [-0.050, +0.075] | 21 / 16 |
| frozen_v04_dev | kaernten | hist_gradient_boosting | 0.627 (p 0.057) | 0.533 (p 0.344) | 0.650 (p 0.029) | +0.024 [-0.073, +0.131] | 21 / 16 |
| frozen_v04_dev | pooled | conditional_logit | 0.716 (p 0.000) | 0.464 (p 0.735) | 0.678 (p 0.001) | -0.038 [-0.092, +0.010] | 45 / 30 |
| frozen_v04_dev | pooled | logistic_regression | 0.721 (p 0.000) | 0.447 (p 0.821) | 0.708 (p 0.000) | -0.013 [-0.060, +0.033] | 45 / 30 |
| frozen_v04_dev | pooled | hist_gradient_boosting | 0.632 (p 0.010) | 0.535 (p 0.272) | 0.645 (p 0.006) | +0.013 [-0.044, +0.076] | 45 / 30 |

## Secondary analyses (refit_all, conditional logit, media)

* media_without_largest_unit: static 0.762, combined 0.746, combined − static -0.016 [-0.123, +0.092] (17 events, 13 units); removed B_2019-06-20_1307405_001
* media_time_known: static 0.678, combined 0.644, combined − static -0.032 [-0.178, +0.122] (11 events, 9 units)
* controls_within_250m_of_wlv_or_kaernten_slide: 0 by construction: these records are matching exclusions with radius 250 m (config matching.additional_exclusions)

## Reading

* Effective sample size is the number of independence units, not the number of rows or events.
* Media positions come from GeoSphere's evaluation of online reports (20–100 m class); the process label was checked against public reports for every analysed media event, but reports cluster near roads and houses, so land-cover and terrain contrasts can still carry reporting bias.
* The Kärnten cohort uses t0 three days before the reported day (no verified day precision): it tests antecedent conditions only and cannot see trigger rain. Its positions have no accuracy field.
* All 72 values are reported; only the primary comparison carries the registered decision rule. Everything else is exploratory.
