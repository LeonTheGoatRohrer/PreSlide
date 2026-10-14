# Positional uncertainty — exploratory

Accepted source upper-bound categories (5, 20, 100 m) are unchanged and are not independently surveyed accuracy. Sizes are stated for each model/variant; repeated evaluations do not create additional events. Differences may be confounded with region, storm, date and process. No performance-driven quality-threshold changes.

| model | features | source_position_upper_m | events | clusters | mean_positive_rank | mean_controls_beaten | mean_weather_rank_delta | mean_slope_mismatch | mean_distance_m |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gradient_boosting | combined | 5 | 5 | 3 | 4.2400 | 1.7600 | -0.4600 | 1.5649 | 5489.3155 |
| gradient_boosting | combined | 20 | 21 | 11 | 3.5048 | 2.4571 | -0.0571 | 1.1899 | 6393.3285 |
| gradient_boosting | combined | 100 | 19 | 7 | 3.5000 | 2.4526 | 0.4053 | 1.2690 | 6121.3105 |
| logistic_regression | combined | 5 | 5 | 3 | 3.4800 | 2.5200 | -1.4800 | 1.5649 | 5489.3155 |
| logistic_regression | combined | 20 | 21 | 11 | 3.6381 | 2.3619 | -0.3714 | 1.1899 | 6393.3285 |
| logistic_regression | combined | 100 | 19 | 7 | 3.0842 | 2.9158 | 0.0947 | 1.2690 | 6121.3105 |
| random_forest | combined | 5 | 5 | 3 | 4.8400 | 1.1600 | -0.3600 | 1.5649 | 5489.3155 |
| random_forest | combined | 20 | 21 | 11 | 3.3143 | 2.6857 | 0.2238 | 1.1899 | 6393.3285 |
| random_forest | combined | 100 | 19 | 7 | 3.4105 | 2.5895 | 0.9263 | 1.2690 | 6121.3105 |

Original offset diagnostic, restricted to development events:

| source_category_upper_m | events | median_slope_range | events_exceeding_5deg |
| --- | --- | --- | --- |
| 5 | 5 | 0.0000 | 0 |
| 20 | 21 | 4.9989 | 6 |
| 100 | 19 | 21.0496 | 17 |

Feature-wise weather differences by category are in position_weather_differences.csv. A category association cannot establish that positional error caused poor performance. Small subgroups cannot support a reliable material-effect estimate.
