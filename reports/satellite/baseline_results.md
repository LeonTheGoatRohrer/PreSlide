# Satellite change baselines (event-held-out)

724 samples, 129 groups, 15 independence units. GroupKFold over independence units (5 folds, 3 fold shuffles); scores are out-of-fold. Within-group AUC = fraction of the 5 controls scored below their positive (chance 0.5); top-1 = positive ranked first (chance 0.167).

| feature set / model | ROC AUC | AP | within-group AUC | unit-weighted | top-1 | mean rank |
|---|---:|---:|---:|---:|---:|---:|
| change_features/logistic_regression | 0.757 | 0.359 | 0.788 | 0.858 | 0.563 | 1.97 |
| change_features/hist_gradient_boosting | 0.780 | 0.478 | 0.799 | 0.866 | 0.592 | 1.95 |
| ring_only_shortcut/logistic_regression | 0.553 | 0.202 | 0.561 | 0.618 | 0.235 | 3.03 |
| ring_only_shortcut/hist_gradient_boosting | 0.621 | 0.239 | 0.628 | 0.557 | 0.326 | 2.74 |
| nuisance_only_shortcut/logistic_regression | 0.473 | 0.189 | 0.489 | 0.503 | 0.132 | 3.35 |
| nuisance_only_shortcut/hist_gradient_boosting | 0.588 | 0.238 | 0.589 | 0.549 | 0.109 | 2.90 |
| contrast_only/logistic_regression | 0.656 | 0.302 | 0.671 | 0.623 | 0.413 | 2.54 |
| contrast_only/hist_gradient_boosting | 0.754 | 0.459 | 0.758 | 0.824 | 0.468 | 2.11 |

Within-group label permutation null (100 draws, logistic regression, change features): null mean 0.501, null 95th percentile 0.560, observed 0.788, upper p = 0.010.

`ring_only_shortcut` uses only scene-wide change around the sample (should stay near chance if the model learns local change); `nuisance_only_shortcut` uses acquisition timing and cloud/snow fractions, which are identical within a group except for local cloud/snow, so it must stay at chance for the within-group metrics. Held-out values away from 0.5 mean the feature set carries structure that transfers between independence units: above 0.5 for ring-only means the surroundings of positives change differently from the surroundings of controls (storm clusters put neighbouring slides into the ring; land cover around reported slopes differs), which the detector may exploit; below 0.5 with few units is small-sample reversal. Both are reported, not corrected. The contrast-only set was not pre-registered as primary; its advantage is noted, not selected on.

## Logistic-regression coefficients (standardised, full data; predictive association, not causation)

| feature | coefficient |
|---|---:|
| d_ndvi_core_std | +1.819 |
| d_nbr_small_contrast | +1.362 |
| d_ndwi_small_contrast | +1.206 |
| d_nbr_ring_frac | -1.201 |
| d_nbr_core_std | -1.155 |
| d_nbr_core_frac | -0.972 |
| d_ndwi_contrast | -0.877 |
| d_ndvi_small_contrast | -0.826 |
| d_bsi_ring_frac | +0.814 |
| before_ndvi_contrast | -0.641 |
| d_bsi_core_frac | +0.617 |
| d_bsi_core_std | +0.611 |
| before_bsi_contrast | -0.599 |
| d_bsi_small_contrast | -0.563 |
| d_nbr_ring_mean | -0.539 |
