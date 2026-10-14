# Weather distinguishability — development only

Source: [GeoSphere INCA v1](https://data.hub.geosphere.at/dataset/inca-v1-1h-1km), verified 2026-10-14: 1 km × 1 km, hourly, UTC; EPSG:31287; CC BY 4.0. Terrain enters the weather analysis, so weather is not independent of terrain.

Nominal 1/3/7/14/30/60-day windows retain 22/70/166/334/718/1438 hours. “Nearly equal” means absolute difference ≤1% of that feature’s development SD; this descriptive scaling is never used for model preprocessing. A group is nearly equal for a feature if at least four of its five controls meet that threshold. Zero-rain short windows can be naturally identical.

| events | weather_features | same_positive_control_cell_pairs | total_pairs | events_nearly_equal_at_least_16_of_18_features | events_all_features_exactly_identical |
| --- | --- | --- | --- | --- | --- |
| 45 | 18 | 0 | 225 | 0 | 0 |

| feature | events | median_range | median_std | median_abs_difference | median_normalized_difference | groups_four_or_more_controls_nearly_equal |
| --- | --- | --- | --- | --- | --- | --- |
| rain_max_hour_14d | 45 | 5.1380 | 1.9217 | 2.1404 | 0.3401 | 1 |
| rain_max_hour_1d | 45 | 1.1010 | 0.3699 | 0.4206 | 0.0687 | 12 |
| rain_max_hour_30d | 45 | 6.6410 | 2.4574 | 2.6102 | 0.3521 | 0 |
| rain_max_hour_3d | 45 | 2.1260 | 0.7223 | 0.9702 | 0.1611 | 6 |
| rain_max_hour_60d | 45 | 9.1130 | 3.0568 | 4.0334 | 0.4295 | 0 |
| rain_max_hour_7d | 45 | 3.6470 | 1.2362 | 1.3434 | 0.2252 | 1 |
| rain_sum_14d | 45 | 20.3640 | 7.4222 | 9.6332 | 0.1020 | 1 |
| rain_sum_1d | 45 | 3.6650 | 1.2499 | 1.4122 | 0.0343 | 13 |
| rain_sum_30d | 45 | 37.2570 | 13.2097 | 16.4768 | 0.1579 | 0 |
| rain_sum_3d | 45 | 11.5180 | 3.7310 | 4.1120 | 0.0495 | 5 |
| rain_sum_60d | 45 | 58.2280 | 19.8699 | 20.8708 | 0.1748 | 0 |
| rain_sum_7d | 45 | 17.5960 | 6.0205 | 6.9854 | 0.0756 | 3 |
| temperature_mean_14d | 45 | 0.9534 | 0.3406 | 0.4926 | 0.0720 | 0 |
| temperature_mean_1d | 45 | 1.0295 | 0.3665 | 0.4502 | 0.0652 | 0 |
| temperature_mean_30d | 45 | 0.9420 | 0.3478 | 0.4639 | 0.0669 | 0 |
| temperature_mean_3d | 45 | 0.9257 | 0.3504 | 0.4381 | 0.0640 | 0 |
| temperature_mean_60d | 45 | 0.9647 | 0.3256 | 0.4457 | 0.0644 | 0 |
| temperature_mean_7d | 45 | 0.9065 | 0.3442 | 0.4645 | 0.0696 | 0 |

All event-level cases are in the local-only `weather_by_event.csv` and `weather_distinguishability.csv`; all state/year/distance strata are reported. Spatial variation establishes distinguishability of inputs, not useful predictive signal. Near identity can reflect dry weather or spatial smoothing; it does not prove weather is irrelevant. Different grid cells do not establish slope-scale fidelity. This analysis cannot identify whether an unresolved physical precursor exists below 1 km.
