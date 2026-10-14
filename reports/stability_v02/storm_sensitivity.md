# Storm/dependency influence — exploratory

45 events; 16 frozen dependency clusters. Largest cluster: 15 events (33.3%); effective equal-event cluster count 1/sum(shares²) = 6.39. Clusters are conservative time/spatial unions, not verified meteorological storm identities.

Primary event-weighted metrics remain unchanged. Diagnostic sample weights give every dependency cluster total weight one; within-event metrics are averaged first by cluster, then across clusters. This changes evaluation influence only. Large clusters may still affect model training. A supplementary leave-one-cluster-out evaluation of fixed mean OOF predictions is local; it is not a retrained leave-storm-out experiment.

| model | method | average_precision_delta | within_group_auc_delta |
| --- | --- | --- | --- |
| gradient_boosting | dependency_balanced | 0.0029 | 0.0340 |
| gradient_boosting | event_weighted | -0.0059 | 0.0400 |
| logistic_regression | dependency_balanced | -0.0264 | -0.1096 |
| logistic_regression | event_weighted | -0.0235 | -0.0622 |
| random_forest | dependency_balanced | 0.0255 | 0.0948 |
| random_forest | event_weighted | -0.0013 | 0.1356 |

Five repeated partitions reuse the same events; they are not five independent storm samples. See all repetitions in storm_deltas.csv.
