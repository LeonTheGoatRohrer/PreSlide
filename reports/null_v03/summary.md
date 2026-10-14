# PreSlide V0.3 — Null reference for the development stability analysis

Exploratory, predeclared in `config/null_v03.json` before any null fit. Development cohort only: 45 events, 270 samples, 16 dependence clusters. Frozen V0.2 folds (seeds 11/23/37/51/71 × 4), unchanged models and features. The original test and Steiermark were not used.

**Method.** In each draw, one of the six members of every event group is chosen at random and labelled pseudo-positive. The same draw is applied to all 9 model/feature variants and all 5 repetitions. Statistics are then computed exactly as in V0.2: pooled out-of-fold per repetition, median over repetitions, deltas per repetition and then medianed. Draw 0 uses the true labels and reproduces `reports/stability_v02/stability_metrics.csv` (max difference 2e-16). 100 draws. Empirical one-sided p = (1 + #null ≥ observed) / 101. All rows are in `null_summary.csv`.

**Why it was needed.** The independent re-verification found Random Forest terrain-only within-group AUC below 0.5 in every repetition. The V0.2 "RF weather gain" was measured against that baseline. Matched, grouped CV with ~45 events does not centre exactly at 0.5 for every model, and its spread is wide, so 0.5 is not an adequate reference.

## Main results (observed · null median [5 %, 95 %] · p_upper)

| Model | Weather only, within-group AUC | Terrain + weather, within-group AUC | Δ within-group AUC (combined − terrain) | Δ AP (combined − terrain) |
| --- | --- | --- | --- | --- |
| Logistic Regression | 0.462 · 0.506 [0.420, 0.587] · 0.77 | 0.507 · 0.502 [0.413, 0.578] · 0.48 | −0.062 · −0.004 [−0.111, 0.111] · 0.82 | −0.023 · 0.001 [−0.025, 0.033] · 0.94 |
| Random Forest | 0.524 · 0.502 [0.418, 0.603] · 0.32 | 0.524 · 0.511 [0.426, 0.605] · 0.43 | +0.136 · 0.012 [−0.080, 0.116] · **0.04** | −0.001 · 0.004 [−0.039, 0.031] · 0.58 |
| Gradient Boosting | 0.507 · 0.487 [0.431, 0.587] · 0.40 | 0.489 · 0.504 [0.424, 0.591] · 0.66 | +0.040 · 0.003 [−0.076, 0.072] · 0.19 | −0.006 · 0.001 [−0.029, 0.025] · 0.66 |

Terrain only, within-group AUC: LR 0.591 (null 95 % 0.605, p_upper 0.09) · RF 0.416 (null 5 % 0.413, p_lower 0.07) · GB 0.449 (p_lower 0.13). LR terrain-only ROC AUC 0.521 (p_upper 0.03).

## Interpretation

1. **No weather-containing variant performs distinguishably from the null.** This holds for any model on AP, ROC AUC or local ranking. All temporal and combined values lie inside the null's 90 % band.
2. **The RF weather delta is a baseline effect.** +0.136 is nominally extreme (p = 0.04; temporal−terrain p = 0.03). It arises because RF terrain-only ranks the true positive *below* the null (0.416), while RF with weather is null-typical (0.524). Of 12 delta statistics, 2 RF ones fall at p ≈ 0.03–0.04. None would survive a multiplicity correction. It is not evidence that weather lifts ranking above chance.
3. **Terrain-only results deviate in both directions, as expected from design structure.** True positives, unlike permuted pseudo-positives, are the centre of their own caliper/annulus search (config caveat). LR terrain-only sits high (fits the V0.2 matching diagnostic: poorer matching ↔ better LR rank); RF/GB terrain-only sit low. These deviations reflect the matched design, not landslide information.
4. **Power.** At this size the null 90 % band for within-group AUC spans ≈ 0.41–0.60. Only a strong local effect (true within-group AUC well above ~0.6) would be detectable. A weak but real weather effect cannot be excluded.

**Strongest defensible statement:** In 45 development events, adding 1 km INCA rainfall/temperature summaries to matched terrain gives no performance distinguishable from a label-permutation null, for any of three model families. The experiment cannot exclude weak effects. Together with the flat V0.2 learning curves, this points to limited information in the current features and limited power from few independent storm episodes, rather than to model choice.
