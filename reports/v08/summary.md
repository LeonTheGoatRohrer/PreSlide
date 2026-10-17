# V0.8 — time-stratified case-crossover at the reported slope (exploratory)

Each stratum is one reported slope: its event time against up to four referent times (t0 ±28 d, ±56 d at the same clock time) at the identical coordinate. 376 of 418 V0.5 slopes had at least 3 usable referents; 23 independence units (effective sample size; one unit holds the 2016 Stanz storm with 221 slopes). Registered in `config/v08.json` before any referent weather was requested. Terrain, land cover, elevation and infrastructure visibility are identical within a stratum and cancel, so this design removes the reporting-placement confounders of V0.4/V0.5; it answers *when*, not *where*.

Referents by outcome: {'complete': 1505, 'inventory_event_near_referent': 91, 'weather_failed:missing_weather_values': 76}. Inventory records without a usable date (cannot block referents): 5966 of 21429.

## Unit-weighted local AUC (median of 5 repetitions; chance 0.5)

| Model / variant | local AUC | range | repetition-1 unit-bootstrap 95 % interval |
|---|---:|---|---|
| conditional_logit/temporal | 0.818 | 0.802–0.886 | [+0.759, +0.912] |
| conditional_logit/temporal_hydro | 0.755 | 0.667–0.784 | [+0.524, +0.793] |
| conditional_logit/hydro_only | 0.587 | 0.567–0.640 | [+0.433, +0.712] |
| hist_gradient_boosting/temporal | 0.744 | 0.686–0.765 | [+0.593, +0.818] |
| hist_gradient_boosting/temporal_hydro | 0.708 | 0.689–0.740 | [+0.572, +0.826] |
| hist_gradient_boosting/hydro_only | 0.655 | 0.602–0.679 | [+0.530, +0.771] |

| Paired difference (repetition-1 unit bootstrap) | mean | 95 % interval | verdict |
|---|---:|---|---|
| conditional_logit: temporal_hydro - temporal | -0.172 | [-0.293, -0.065] | interval excludes zero |
| hist_gradient_boosting: temporal_hydro - temporal | -0.003 | [-0.116, +0.106] | no established difference |

## Diagnostics

* Without the largest unit: 0.819 (155 slopes, 22 units).
* By time quality of the event (conditional logit, temporal): clock 0.771 (35 events, 14 units); day 0.875 (67 events, 16 units); daypart 0.894 (274 events, 8 units). For time quality `day` the same-day rain features are missing, so skill there comes from the history before the event day.
* By referent side: before 0.824; after 0.822.
* Neighbour-slope (spatial) design on the same slopes, conditional logit: temporal 0.757, temporal+hydro 0.736 (V0.5/V0.6 stored predictions).

## Reading

Decision rule (registered): weather is informative about *when* a reported slope fails only if the primary interval excludes 0.5; the hydrological features are an added benefit only if the paired interval excludes zero. A large part of the contrast is expected by construction: the inventory records landslides mainly in documented heavy-rain episodes, so event times are wetter than arbitrary referent times 4–8 weeks away, and temperature windows partly encode season. The result therefore shows that documented failure times are distinguishable from ordinary times, not that rain forecasts a failure on a given slope. More hydrological features on 376 strata can overfit (conditional logit), which the paired comparison shows. Limits: a case-crossover answers 'when', not 'where'; event times are conservative lower bounds, so the true failure may be later and the pre-t0 rain of the same day is missing for unknown time of day; inventory entries are not a complete record of failures at the referent times (referents are pseudo-negative times); INCA is 1 km
