# Pipeline B — satellite-0.4 (normalised change, persistence, filters; exploratory)

Registered in `config/satellite_0_4.json` before any result was computed. Cohort: 129 events with matched controls (724 samples), 15 independence units (effective sample size; event-held-out folds). Reference and confirm acquisitions were found for 82% / 87% of the samples (positives: 100% / 100%; controls: 78% / 85%); missing values stay NaN.

## Event-held-out baselines (mean of 3 seeds)

| feature set / model | within-group AUC (unit-weighted) | top-1 rate |
|---|---:|---:|
| change_features/logistic_regression | 0.858 | 0.563 |
| change_features/hist_gradient_boosting | 0.866 | 0.592 |
| change_norm/logistic_regression | 0.860 | 0.553 |
| change_norm/hist_gradient_boosting | 0.923 | 0.664 |
| norm_only/logistic_regression | 0.752 | 0.499 |
| norm_only/hist_gradient_boosting | 0.833 | 0.517 |
| persistence_only/logistic_regression | 0.610 | 0.295 |
| persistence_only/hist_gradient_boosting | 0.634 | 0.297 |

| paired difference vs change_features (unit bootstrap) | mean | 95 % interval | verdict |
|---|---:|---|---|
| change_norm - change_features / logistic_regression | +0.002 | [-0.018, +0.018] | no established difference |
| norm_only - change_features / logistic_regression | -0.107 | [-0.266, +0.017] | no established difference |
| persistence_only - change_features / logistic_regression | -0.248 | [-0.415, -0.111] | interval below zero |
| change_norm - change_features / hist_gradient_boosting | +0.057 | [+0.001, +0.117] | interval above zero |
| norm_only - change_features / hist_gradient_boosting | -0.034 | [-0.111, +0.042] | no established difference |
| persistence_only - change_features / hist_gradient_boosting | -0.233 | [-0.346, -0.131] | interval below zero |

## Held-out rediscovery (logistic regression, hit radius 160 m)

satellite-0.2 reference (`heldout_discovery_results.json`): 28 of 129 events within the first three candidates, 4.49 candidates per km².

| feature set / filter | found any rank | top-1 | top-3 | top-5 | candidates per km² |
|---|---:|---:|---:|---:|---:|
| change_features/all_filters | 47 | 12 | 36 (28%) | 44 | 2.69 |
| change_features/cloud_buffer_only | 49 | 7 | 28 (22%) | 37 | 3.71 |
| change_features/no_filter | 61 | 11 | 28 (22%) | 38 | 4.49 |
| change_features/terrain_water_only | 58 | 16 | 36 (28%) | 50 | 3.26 |
| change_norm/all_filters | 41 | 11 | 26 (20%) | 33 | 2.75 |
| change_norm/cloud_buffer_only | 43 | 7 | 22 (17%) | 31 | 3.79 |
| change_norm/no_filter | 56 | 9 | 20 (16%) | 32 | 4.65 |
| change_norm/terrain_water_only | 52 | 13 | 29 (22%) | 35 | 3.37 |

Stage 6 (unknown-region scan): condition `executed only if satellite-0.4 reaches, with the all-filters variant, >= 50 % of the 129 events found within 160 m among the first three candidates AND <= 2 candidates per km2; otherwise not executed and reported as not reached` — best all-filters variant 28% top-3, 2.69 candidates per km² → **not reached; not executed**.

## Position refinement proposals (not applied)

20 rediscovered events with persistent change. Median shift 67 m (range 12–241 m). By source position class:

| source upper bound (m) | events | median shift (m) | shift > 50 m |
|---:|---:|---:|---:|
| 5 | 14 | 94 | 10 |
| 20 | 6 | 39 | 2 |

10 events in the ≤ 5 m class shift by more than 50 m. Under the registered check this questions the centroid definition (large change masks that include harvest or shadow) and the source, not an automatic overwrite: **no position was changed**, Pipeline A is untouched.

## Reading

Terrain/water and cloud-buffer filters are the useful part: they raise the first-three hits and cut false candidates. Normalised change and persistence features show no consistent benefit for the linear detector and a borderline paired gain for gradient boosting in the baseline; they did not improve the rediscovery. Limits: 15 independence units; Sentinel-2 revisit and cloud cover limit the pairs; the documented position is itself uncertain (<= 20 m class); candidates are not landslide labels; harvest, construction and forestry mimic scars
