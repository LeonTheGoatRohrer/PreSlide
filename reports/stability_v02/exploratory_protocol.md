# Predeclared exploratory diagnostics

Weather ablation: Logistic Regression, weather-only and terrain+weather, all 20 frozen folds; immediate 1–3d, short 7–14d, antecedent 30–60d, full. Existing cumulative features remain unchanged: these are cumulative lookbacks, not disjoint time segments. Full uses saved primary predictions; no window is selected for test evaluation.

Learning curves: Logistic Regression plus random_forest (highest development median combined AP among the two fixed tree families; see local selection checkpoint). Nested 25/50/75/100% of each fold’s 12 training dependency groups = 3/6/9/12 groups; four untouched evaluation groups per fold. All five seeds. 100% means all outer-training groups, not all 16 development groups. OOF metrics pool the four folds per repetition; fractions use identical held-out events. Tree selection uses these same development results, so its curve is exploratory and selection-biased. No precise future-data performance extrapolation.

Interactions: LR combined plus exactly rain_sum_3d×slope, rain_sum_30d×slope and rain_sum_7d×elevation. Products use physical units before training-only standardization; main effects retained. No original test/Steiermark scoring. Tree models already encode implicit nonlinear interactions.

All 4 windows, all 4 fractions, all repetitions and the interaction comparator are reported, irrespective of result.
