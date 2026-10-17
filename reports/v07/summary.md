# V0.7 — reporting-bias control with OpenStreetMap infrastructure distances (exploratory)

Cohort: frozen V0.5 cohort, 418 events, 29 independence units, 4598 samples. Registered in `config/v07.json` before any distance was computed. Source: OpenStreetMap contributors via Geofabrik GmbH, `austria-261014.osm.pbf` (812,633,484 bytes), ODbL 1.0, attribution '(c) OpenStreetMap contributors'; local non-commercial research use only. Snapshot 2026-10-14 for events from 2016: snapshot of 2026-10-14; events date from 2016 onwards. Buildings and public roads are largely persistent but new construction after an event can make the distance too short; this bias is shared by positives and controls and is stated, not corrected. Effective sample size = 29 independence units; exploratory, no new independent test.

## (a) Infrastructure distance in the model (unit-weighted local AUC, median of 5 repetitions; chance 0.5)

| Model / variant | local AUC | range |
|---|---:|---|
| conditional_logit/static | 0.865 | 0.858–0.877 |
| conditional_logit/combined | 0.851 | 0.835–0.863 |
| conditional_logit/infra_only | 0.928 | 0.924–0.930 |
| conditional_logit/static_infra | 0.912 | 0.901–0.929 |
| conditional_logit/combined_infra | 0.901 | 0.891–0.916 |
| hist_gradient_boosting/static | 0.794 | 0.782–0.804 |
| hist_gradient_boosting/combined | 0.798 | 0.791–0.829 |
| hist_gradient_boosting/infra_only | 0.892 | 0.880–0.898 |
| hist_gradient_boosting/static_infra | 0.914 | 0.887–0.927 |
| hist_gradient_boosting/combined_infra | 0.914 | 0.904–0.921 |

| Paired difference (repetition-1 unit bootstrap) | mean | 95 % interval |
|---|---:|---|
| conditional_logit: static_infra - static | +0.054 | [+0.027, +0.082] |
| conditional_logit: combined_infra - combined | +0.057 | [+0.026, +0.091] |
| conditional_logit: infra_only AUC interval | – | [+0.888, +0.957] |
| hist_gradient_boosting: static_infra - static | +0.139 | [+0.074, +0.215] |
| hist_gradient_boosting: combined_infra - combined | +0.115 | [+0.059, +0.188] |
| hist_gradient_boosting: infra_only AUC interval | – | [+0.852, +0.927] |

## (b) Equal visibility: controls within a factor 2 of the positive in distance to infrastructure

Caliper keeps 173 of 418 groups (10 units) with at least 3 retained controls; 31% of all controls are inside the caliper. Stored V0.5 out-of-fold scores (models without infrastructure features) are re-ranked among the retained controls.

| Conditional logit variant | all controls, same groups | caliper controls | difference |
|---|---:|---:|---:|
| static | 0.796 | 0.783 | -0.013 |
| temporal | 0.640 | 0.618 | -0.022 |
| combined | 0.805 | 0.782 | -0.024 |
| bootstrap static difference (repetition 1) | – | – | -0.017 [-0.068, +0.031] |
| bootstrap combined difference (repetition 1) | – | – | -0.067 [-0.172, +0.005] |

Caliper static AUC bootstrap interval: [+0.679, +0.888].

Land-cover ablation (conditional logit combined, median local AUC):

| | with land cover | without land cover |
|---|---:|---:|
| all retained groups | 0.805 | 0.766 |
| caliper controls | 0.782 | 0.774 |

## Diagnostics

* Capped (>= 5000 m) shares, positive / control: building 0.45 / 0.47, road 0.39 / 0.54.
* Spearman correlation of dist_infrastructure_m: elevation +0.46, lc_forest +0.46, lc_grass_shrub -0.28, lc_agriculture -0.27, lc_open_bare +0.02, lc_artificial_water_other -0.19.

## Reading

Distance to infrastructure alone ranks the reported slope above its ten surrounding points about as well as, or better than, terrain and land cover. This is what reporting/placement bias predicts, and it is also partly built into the design: the controls lie 0.75–10 km around the reported slope and so are on average farther from roads and buildings. The caliper analysis removes that contrast in the retained groups; the unaware terrain models keep most of their skill there, but those groups are only a minority of the data and units and the intervals are wide. Nothing here shows that terrain or land cover cause landslides or that the retained skill is free of reporting effects: the test only equalises distance to mapped infrastructure. Limits: OSM completeness varies and improves over time; remote sites may be mapped later than their neighbours; absence of nearby infrastructure is not absence of reports; no causal reading
