# PreSlide — Current-State Audit (2026-10-14)

Verified from the repository itself: saved artifacts, recomputed metrics, executed tests. Independent checks: `scripts/verify_state.py` → `reports/verification/independent_checks.json` (status PASS, 0 errors). Numbers below come from that file, `reports/null_v03/null_summary.csv` or the cited CSVs.

## Repository

| Component | Path | Status |
| --- | --- | --- |
| Source audit / filtering | `preslide/audit.py`, `sources.py`, `config/audit.json` | VERIFIED WORKING (cached snapshot, 102 accepted candidates) |
| Terrain (30 m, EPSG:31287) | `preslide/terrain.py` | VERIFIED WORKING (ranges plausible, CRS round trip ≤0.58 m; positives exact, controls carry rounded lon/lat) |
| Matching | `preslide/matching.py` | VERIFIED WORKING (calipers, annulus, separation, circular aspect recomputed) |
| Weather (INCA 1 km/1 h) | `preslide/weather.py` | VERIFIED WORKING (all windows end ≥2 h before local event-day midnight; all 270 development vectors recomputed from raw cache in V0.2 audit) |
| Dataset / grouping | `preslide/pipeline.py`, `evaluation.py` | VERIFIED WORKING |
| Original experiment (9 models, frozen split, Steiermark) | `preslide/evaluation.py`, `reports/experiment/` | VERIFIED WORKING; all stored test metrics reproduced from saved predictions **and** by re-predicting with saved models |
| V0.1/V0.2 stability + diagnostics | `preslide/stability*.py`, `reports/stability_v02/` | COMPLETE AND VERIFIED (180/180 primary fits, 120 ablation, 120 learning, 20 interaction) |
| V0.3 null reference (new) | `preslide/null_reference.py`, `config/null_v03.json`, `reports/null_v03/` | COMPLETE AND VERIFIED (identity draw reproduces V0.2 to 2e-16; 100 permutation draws) |
| Web results bundle (new) | `preslide/results_bundle.py` → `data/web/results.json` | VERIFIED WORKING |
| FastAPI | `preslide/api.py` | VERIFIED WORKING (health, summary, cases, new `/api/results`; raw records not exposed — tested) |
| Vue/Vite/MapLibre UI | `frontend/` | VERIFIED WORKING (build passes, browser-checked, no console errors) |
| Tests | `tests/` | 43 passed; see below |

## Dataset (identity `046074ba6f12556c`)

- 102 accepted candidates (fallback search from 2015; actual dates 2017-08-05 … 2026-06-13).
- Outcomes: 60 complete; 17 missing weather; 13 insufficient controls; 9 negative INCA precipitation; 3 positive DEM slope < 5°.
- 60 positives + 300 pseudo-negative controls = 360 samples; exactly 6 per group, same t0, unique samples/coordinates.
- 20 dependence clusters; sizes 15, 8, 5, 5, 4, 4, 3, 2, 2, 2 and ten singletons. 29 distinct event dates.
- Years: 2017 4 · 2018 8 · 2019 1 · 2022 7 · 2023 23 · 2024 14 · 2026 3.
- States: Steiermark 28 · Salzburg 7 · Niederösterreich 6 · Vorarlberg 5 · Kärnten 5 · Tirol 4 · Oberösterreich 3 · Burgenland 2.
- Process: Lockergesteinsrutschung 32 · Hangmure 21 · Hangmure bis Lockergesteinsrutschung 7.
- Source position category (upper bound): 5 m 17 · 20 m 21 · 100 m 22.
- Matching (controls): distance 849–9,958 m (median 6,122 m); |Δslope| median 0.96°; |Δelevation| median 28 m; circular Δaspect median 8.5°; min control separation 403 m; min distance from any control to any dataset positive 346 m.
- Weather: 0/300 controls share the positive's 1 km INCA cell; 1,438 retained hours per sample.
- Predictors: 22 = 4 static (elevation, slope, aspect sin/cos) + 18 temporal (rain sum, max hourly rain, mean temperature × 1/3/7/14/30/60 d).

## Splits

- Original frozen split: train 19 events / 12 clusters · validation 26 / 4 · test 15 / 4. No event group or cluster crosses partitions; dependence rule (≤3 d or <2 km, plus 400 m overlap) re-checked pairwise.
- Model parameters are fixed constants; no hyperparameter search, feature selection or threshold tuning exists, so validation/test cannot have influenced them. Scaling is inside the LR pipeline (fitted on training only; asserted in V0.2).
- V0.2: development only (45 events / 16 clusters / 270 samples), seeds 11/23/37/51/71 × 4 grouped folds; original test absent; every fit's training IDs are the exact complement of its held-out fold.

## Experiments

| Experiment | Independence | Status |
| --- | --- | --- |
| Original frozen test (15 events, 4 clusters) | Independent once; seen in earlier reports, so later work is not blind to it | Complete, reproduced |
| Steiermark geographic holdout (28 test / 24 train events) | Overlaps original development and test cohorts | Complete, reproduced from metrics.json |
| V0.2 development stability | Development only; repeated splits of the same 45 events | Complete and verified |
| V0.2 diagnostics (pairwise ranking, weather distinguishability, window ablation, learning curve, feature stability, storm, matching, position, interactions) | Exploratory | All VERIFIED (artifacts present, recomputable) |
| V0.3 null reference | Exploratory, predeclared in `config/null_v03.json` before fitting | Complete |

## Verified results

Original test (reproduced): best within-group AUC RF combined 0.747 (AP 0.253, ROC 0.615); RF temporal AP 0.314; LR combined ROC 0.517 / AP 0.202. Chance AP 0.167. RF/GB recall at 0.5 is 0 — threshold metrics carry no signal.

V0.2 development (median of 5 repetitions, pooled OOF): within-group AUC LR 0.591 / 0.462 / 0.507 (static / temporal / combined), RF 0.416 / 0.524 / 0.524, GB 0.449 / 0.507 / 0.489. AP everywhere 0.159–0.190 vs chance 0.167. The original-test RF value (0.747) is not reproduced in development.

V0.3 null reference (100 within-group label permutations, same folds/models): no variant with weather features is distinguishable from the null on AP, ROC AUC or within-group AUC (all p_upper ≥ 0.28). Null 90 % band for within-group AUC ≈ 0.41–0.60. RF terrain→combined Δ local AUC +0.136 is nominally extreme (p = 0.04), but RF terrain-only is *below* the null (0.416, p_lower 0.07) while RF combined is null-typical (0.524). It is 1 of 12 delta tests. LR terrain-only is nominally above the null (ROC 0.521, p = 0.03), consistent with residual matching structure. Details: `reports/null_v03/summary.md`.

Answers to the core questions:
1. Does weather repeatedly improve over terrain? No. LR worsens in 5/5 repetitions on local AUC; RF/GB AP deltas are about zero.
2. Does weather improve local ranking of the actual landslide? Not distinguishably from the null for any model.
3. Are weather values different between nearby slopes? Yes: 0/300 pairs share a 1 km cell, with non-trivial within-group spread (rain_sum_30d median abs. difference 16 mm). Whether 1 km resolves slope-scale forcing is unknown.
4. Stable across dependency groups? No; results depend on model and metric. 16 development clusters; the largest holds 15/45 events.
5. Do a few storms dominate? Weight concentration is strong (one cluster = 33 %). Dependency-balanced re-weighting does not remove the RF delta, but that delta is itself not distinguishable from the null.
6. Would more data help? The learning curves are flat near chance (LR AP 0.174→0.164, RF 0.179→0.178 from 25 % to 100 % of training groups). More rows with the same features are unlikely to help by themselves. The wide null band shows more *independent* storm episodes are needed for power to detect a moderate effect.

## Tests

`pytest`: 43 passed, 0 failed, 0 skipped (one Starlette/httpx deprecation warning). This includes tests added this session (null reference, `/api/results`) and by a concurrent peer session (stability figures, public bundle ties). Covered: future leakage, group/cluster leakage, control dates, CRS, distances, circular aspect, duplicates/separation, real exclusion buffers, feature windows, LR preprocessing isolation, checkpoint/config hash consistency, API exposure. The V0.2 protected-artifact manifest caught a new file placed inside the frozen run directory during this session; the file was moved to `data/web/`, so the guard works as intended.

## Backend / Frontend

- API reads only generated artifacts. New `/api/results` serves `data/web/results.json` (aggregates and demo-case ranks; no source IDs or coordinates — tested).
- Before this session the UI showed only original-test/Steiermark numbers. It omitted V0.2 even though the V0.2 report claimed the API served it, and it hard-coded "102" and "1.438". Fixed: separate tabs (original test · Steiermark · Stability V0.2 with null reference · Diagnostics), per-case out-of-training ranking (controls beaten), German design explanation, values from the bundle.

## Scientific risks

1. No variant's development performance is distinguishable from the label-permutation null; the only nominally extreme statistic (RF terrain→combined delta) comes from a below-null terrain baseline.
2. The original test (4 clusters) is too small. Its favourable RF values are not reproduced in development and should be presented as chance-compatible.
3. Pseudo-negatives, inventory/reporting bias, positional uncertainty (23/45 development events cross the 5° slope caliper under source-radius offsets), 1 km weather resolution.
4. One cluster holds 15/45 development events; 29 distinct dates in total. Effective independent sample size is small.
5. Strict complete-case weather rule removes 26/102 candidates (regional/temporal bias possible).

## Technical risks

- INCA v1 retirement announced for December 2026; local raw cache preserves this run.
- `latest.json` pointer is overwritten by smaller pilot runs (documented in README).
- Raw-data licence for the detailed event source is unidentified (documented; local use only).

## Remaining work (prioritised)

1. Independent, pre-registered external evaluation set: new storm episodes with verified positions. Do not tune on existing test.
2. Information-gap features justified by the diagnostics (soil moisture / antecedent wetness at ≤1 km, snowmelt) only as a new versioned experiment.
3. Competition narrative: present the matched design and null-calibrated negative result as the contribution.
