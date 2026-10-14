# Feature stability — exploratory

Combined models, all 20 held-out folds. Three deterministic permutations per feature per fold. The primary shuffle stays within each six-slope event; global row permutation is secondary and can create implausible combinations. Four fold importances are equally averaged per repetition; median/range across five repetitions. These are descriptive, not confidence intervals. An AP drop >0.005 is a predeclared descriptive threshold, not significance.

LR coefficients refer to training-standardized variables; sign consistency is shown without treating magnitude as AP. RF native impurity importance is secondary. Histogram boosting has no public native impurity importance; SHAP was not added. Correlated cumulative windows share signal and individual permutation can underestimate their joint contribution. Importance in weak models does not establish physical irrelevance.

See [scikit-learn permutation guidance](https://scikit-learn.org/stable/modules/permutation_importance.html). All features and both permutation methods remain in CSVs; figures show all 22 features.
