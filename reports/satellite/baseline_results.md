# Satellite change baselines (event-held-out)

79 samples, 14 groups, 12 independence units. GroupKFold over independence units (5 folds, 3 fold shuffles); scores are out-of-fold. Within-group AUC = fraction of the 5 controls scored below their positive (chance 0.5); top-1 = positive ranked first (chance 0.167).

| feature set / model | ROC AUC | AP | within-group AUC | unit-weighted | top-1 | mean rank |
|---|---:|---:|---:|---:|---:|---:|
| change_features/logistic_regression | 0.716 | 0.481 | 0.679 | 0.650 | 0.524 | 2.50 |
| change_features/hist_gradient_boosting | 0.708 | 0.411 | 0.693 | 0.692 | 0.429 | 2.38 |
| ring_only_shortcut/logistic_regression | 0.263 | 0.125 | 0.187 | 0.177 | 0.024 | 4.81 |
| ring_only_shortcut/hist_gradient_boosting | 0.347 | 0.167 | 0.312 | 0.267 | 0.071 | 4.20 |
| nuisance_only_shortcut/logistic_regression | 0.291 | 0.127 | 0.357 | 0.328 | 0.048 | 3.98 |
| nuisance_only_shortcut/hist_gradient_boosting | 0.537 | 0.189 | 0.604 | 0.632 | 0.024 | 2.87 |
| contrast_only/logistic_regression | 0.762 | 0.463 | 0.742 | 0.712 | 0.500 | 2.19 |
| contrast_only/hist_gradient_boosting | 0.714 | 0.357 | 0.703 | 0.703 | 0.548 | 2.37 |

Within-group label permutation null (100 draws, logistic regression, change features): null mean 0.492, null 95th percentile 0.658, observed 0.679, upper p = 0.059.

`ring_only_shortcut` uses only scene-wide change around the sample (should stay near chance if the model learns local change); `nuisance_only_shortcut` uses acquisition timing and cloud/snow fractions, which are identical within a group except for local cloud/snow, so it must stay at chance for the within-group metrics. Held-out values far below 0.5 mean the feature set carries no transferable positive signal; a systematic reversal with few independence units is small-sample instability and is reported, not corrected. The contrast-only set was not pre-registered as primary; its advantage is noted, not selected on.

## Logistic-regression coefficients (standardised, full data; predictive association, not causation)

| feature | coefficient |
|---|---:|
| d_brightness_small_frac | +1.315 |
| d_brightness_ring_mean | -0.912 |
| d_ndvi_core_frac | -0.736 |
| d_brightness_contrast | +0.718 |
| d_ndwi_small_contrast | +0.682 |
| d_brightness_core_std | -0.643 |
| d_ndvi_frac_contrast | -0.620 |
| d_ndvi_small_frac | +0.619 |
| before_bsi_contrast | -0.574 |
| d_brightness_frac_contrast | +0.563 |
| before_ndvi_contrast | -0.548 |
| d_nbr_core_std | +0.540 |
| d_ndvi_small_contrast | -0.531 |
| before_bsi_core_mean | +0.528 |
| d_bsi_ring_mean | -0.520 |
