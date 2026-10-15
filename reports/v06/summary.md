# V0.6 — hydrological rain features (exploratory)

Cohort: frozen V0.5 cohort, 418 events, 29 independence units, 4598 samples (one reported slope against ten unmatched surrounding slopes). Registered in `config/v06.json` before any feature was computed. Grouped, spatially purged cross-validation on events already seen in V0.4/V0.5: **exploratory, no new independent test**. Effective sample size = 29 independence units (temporal episodes), not 418 events.

## Unit-weighted local AUC (median over 5 repetitions; chance 0.5)

| Model / variant | local AUC | range over repetitions | top-1 | MRR |
|---|---:|---|---:|---:|
| conditional_logit/combined | 0.851 | 0.835–0.863 | 0.413 | 0.629 |
| conditional_logit/combined_hydro | 0.838 | 0.821–0.846 | 0.417 | 0.617 |
| conditional_logit/hydro_only | 0.495 | 0.450–0.503 | 0.036 | 0.229 |
| conditional_logit/static | 0.865 | 0.858–0.877 | 0.375 | 0.606 |
| conditional_logit/temporal | 0.719 | 0.702–0.727 | 0.287 | 0.484 |
| conditional_logit/temporal_hydro | 0.702 | 0.667–0.714 | 0.234 | 0.455 |
| hist_gradient_boosting/combined | 0.798 | 0.791–0.829 | 0.397 | 0.573 |
| hist_gradient_boosting/combined_hydro | 0.807 | 0.792–0.834 | 0.395 | 0.584 |
| hist_gradient_boosting/hydro_only | 0.530 | 0.506–0.587 | 0.139 | 0.304 |
| hist_gradient_boosting/static | 0.794 | 0.782–0.804 | 0.376 | 0.566 |
| hist_gradient_boosting/temporal | 0.658 | 0.632–0.678 | 0.187 | 0.380 |
| hist_gradient_boosting/temporal_hydro | 0.693 | 0.671–0.712 | 0.296 | 0.471 |

## Paired differences (4 comparisons, all reported)

| Comparison | median over repetitions | repetition-1 unit bootstrap 95 % interval | verdict |
|---|---:|---|---|
| conditional_logit: temporal_hydro - temporal | -0.017 | [-0.059, +0.041] | no established benefit |
| conditional_logit: combined_hydro - combined (primary) | -0.013 | [-0.029, +0.016] | no established benefit |
| hist_gradient_boosting: temporal_hydro - temporal | +0.041 | [-0.025, +0.097] | no established benefit |
| hist_gradient_boosting: combined_hydro - combined | +0.010 | [-0.005, +0.071] | no established benefit |

## Sensitivity and redundancy

* Conditional logit without the largest unit (B_2016-07-25_1200667_001): temporal_hydro - temporal -0.015; combined_hydro - combined -0.011.
* Highest absolute Spearman correlation of a hydrological feature with a V0.5 temporal feature: 1.00 (median over features 0.67).

## Reading

Decision rule (registered): a hydrological benefit counts as established only if the paired interval excludes zero. The bootstrap resamples the independence units of the first repetition; the repetitions reuse the same events and are not independent confirmations. Feature importance is predictive, not causal. INCA is a 1 km hourly product and rain after t0 on the event day is invisible. Limits: predictive importance is not causation; INCA 1 km hourly rain is a coarse proxy of slope-scale rainfall; rain after t0 on the event day is invisible; events already seen in V0.4/V0.5 so results are exploratory
