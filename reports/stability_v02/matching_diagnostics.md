# Matching quality vs performance — exploratory

Per-event mean mismatch across five controls, circular aspect distance, distance in EPSG:31287 metres, and original matching score. Outcomes are averaged over five held-out predictions before association: 45 events, not 225 independent repetitions. Rank delta = terrain rank − combined rank, positive means improvement. For positive rank, negative correlation means more success with worse matching; for rank delta, positive correlation means more weather benefit with worse matching. Scores are case-control scores, not risk.

| model | matching_measure | outcome | spearman_rho | events | clusters |
| --- | --- | --- | --- | --- | --- |
| gradient_boosting | slope_difference_deg | positive_rank | -0.0153 | 45 | 16 |
| gradient_boosting | slope_difference_deg | weather_rank_delta | 0.0898 | 45 | 16 |
| gradient_boosting | elevation_difference_m | positive_rank | -0.1855 | 45 | 16 |
| gradient_boosting | elevation_difference_m | weather_rank_delta | 0.2899 | 45 | 16 |
| gradient_boosting | aspect_difference_deg | positive_rank | -0.0313 | 45 | 16 |
| gradient_boosting | aspect_difference_deg | weather_rank_delta | 0.1176 | 45 | 16 |
| gradient_boosting | distance_to_positive_m | positive_rank | 0.1174 | 45 | 16 |
| gradient_boosting | distance_to_positive_m | weather_rank_delta | 0.0369 | 45 | 16 |
| gradient_boosting | matching_score | positive_rank | -0.0769 | 45 | 16 |
| gradient_boosting | matching_score | weather_rank_delta | 0.1313 | 45 | 16 |
| logistic_regression | slope_difference_deg | positive_rank | -0.3751 | 45 | 16 |
| logistic_regression | slope_difference_deg | weather_rank_delta | -0.0449 | 45 | 16 |
| logistic_regression | elevation_difference_m | positive_rank | -0.3213 | 45 | 16 |
| logistic_regression | elevation_difference_m | weather_rank_delta | 0.0442 | 45 | 16 |
| logistic_regression | aspect_difference_deg | positive_rank | -0.2357 | 45 | 16 |
| logistic_regression | aspect_difference_deg | weather_rank_delta | 0.1251 | 45 | 16 |
| logistic_regression | distance_to_positive_m | positive_rank | -0.1776 | 45 | 16 |
| logistic_regression | distance_to_positive_m | weather_rank_delta | 0.1997 | 45 | 16 |
| logistic_regression | matching_score | positive_rank | -0.4071 | 45 | 16 |
| logistic_regression | matching_score | weather_rank_delta | 0.0813 | 45 | 16 |
| random_forest | slope_difference_deg | positive_rank | 0.1422 | 45 | 16 |
| random_forest | slope_difference_deg | weather_rank_delta | -0.1193 | 45 | 16 |
| random_forest | elevation_difference_m | positive_rank | -0.1222 | 45 | 16 |
| random_forest | elevation_difference_m | weather_rank_delta | 0.1804 | 45 | 16 |
| random_forest | aspect_difference_deg | positive_rank | 0.1434 | 45 | 16 |
| random_forest | aspect_difference_deg | weather_rank_delta | -0.1012 | 45 | 16 |
| random_forest | distance_to_positive_m | positive_rank | 0.1042 | 45 | 16 |
| random_forest | distance_to_positive_m | weather_rank_delta | -0.0059 | 45 | 16 |
| random_forest | matching_score | positive_rank | 0.0911 | 45 | 16 |
| random_forest | matching_score | weather_rank_delta | -0.0634 | 45 | 16 |

All variants and outcomes remain in matching_correlations.csv. Correlations are descriptive and cluster dependent; no multiple-testing significance or causal claim. No event is removed and no controls are rematched. Small associations cannot exclude selection artifacts; same-location terrain matching omits geology and soils.
