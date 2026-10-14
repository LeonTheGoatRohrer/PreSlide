# PreSlide V0.3 Baseline — status summary (2026-10-14)

All statements below were checked in this session against saved artifacts, by running tests and the independent verification. Nothing was retrained.

## Does the pipeline work end-to-end?

**Yes, for the frozen baseline run.** It was not re-executed from raw data in this session, because re-running would overwrite frozen artifacts. Instead every stage's stored output was independently re-checked.

| Stage | Status | Evidence |
|---|---|---|
| Landslide source data | VERIFIED WORKING | Cached snapshot and exclusion inventory hash-frozen; audit report reproduces 102 candidates |
| Filtering → accepted events | VERIFIED WORKING | `status.json`: 60 complete; 17 missing weather, 13 insufficient controls, 9 negative precipitation, 3 slope < 5° |
| Terrain extraction | VERIFIED WORKING | `verify_state.py`: CRS round trip < 1 m, plausible ranges, unit aspect vectors |
| Control generation / matching | VERIFIED WORKING | Calipers, 750 m–10 km annulus, ≥ 400 m separation, exclusion buffers, circular aspect and stored distances recomputed |
| Weather retrieval | VERIFIED WORKING | Every last timestamp is before t0, 1,438 h per sample, nested sums, grid cell ≤ 800 m; V0.2 recomputed all 270 development vectors from the raw cache |
| Temporal features | VERIFIED WORKING | Same checks; 18 features, finite, non-constant |
| ML dataset | VERIFIED WORKING | 360 rows, exactly 1 positive + 5 controls per group, identical t0, unique IDs/coordinates, label ↔ type consistent |
| Grouped splitting | VERIFIED WORKING | No event group or dependence cluster crosses partitions; dependence rule re-checked pairwise; V0.2 folds keep clusters intact |
| Model training | VERIFIED WORKING | Saved models re-predict the saved test predictions exactly; class order [0, 1]; training IDs match the train partition |
| Out-of-training predictions | VERIFIED WORKING | V0.2: 180/180 fits, each trained on the exact complement of its fold; event ranks recomputed here match `event_results.parquet` exactly |
| Metrics | VERIFIED WORKING | ROC AUC/AP recomputed from saved predictions equal `metrics.json` (difference 0) |
| Diagnostics | VERIFIED WORKING | V0.2 diagnostics A–I present; new event-level diagnostics for all 60 events |
| Reports | VERIFIED WORKING | `reports/verification/independent_checks.json` PASS, 0 errors |
| API | VERIFIED WORKING | `tests/test_api.py` (5 tests, incl. de-identification of the new explorer); live server checked |
| Frontend | VERIFIED WORKING | `npm run build` passes; browser-checked desktop and 375 px; no console errors; `npm test` 5/5 |
| Re-running pipeline/evaluation on new data | PARTIAL | Blocked on purpose for the baseline identity; versioned runner for a new dataset not yet implemented (see below) |

## Exact current dataset (from artifacts; matches PROJECT_STATE.md)

| Quantity | Value |
|---|---|
| Accepted candidates | 102 |
| Complete ML events (positives) | 60 |
| Controls | 300 (exactly 5 per event) |
| Samples | 360 |
| Dependence clusters | 20 (largest 15 events); 29 distinct event dates |
| Static / temporal features | 4 / 18 |
| Event dates | 2017-08-05 … 2026-06-13 |
| Excluded | 42 (17 missing weather, 13 insufficient controls, 9 negative precipitation, 3 slope < 5°) |
| Original split | train 19 events / 12 clusters · validation 26 / 4 · test 15 / 4 |

## Scientific correctness checks

- **Labels:** exactly one positive per group, 5 controls, positive class = 1 in every saved model.
- **Time:** controls inherit t0; all weather ends before local midnight of the event day (one guard hour at each window edge).
- **Groups:** no event group or cluster leaks across original partitions or V0.2 folds; the original test is absent from V0.2/V0.3.
- **Preprocessing:** the only learned preprocessing (StandardScaler) sits inside the LR pipeline and is fitted on training data only. There is no tuning, feature selection or threshold search.
- **Geography:** EPSG:31287 metric distances, lon/lat order verified by round trip, circular aspect, no duplicate controls, buffers respected.
- **Metrics:** recomputed from saved predictions.

**No genuine scientific error was found.** No corrected experiment version was needed.

## Errors fixed in this session (technical, no results changed)

1. **Overwrite hazard (verified).** `python -m preslide experiment --limit N` produces the same identity as the baseline. It would have overwritten the frozen run's `status.json`, then `evaluate` would have overwritten `evaluation_dataset.parquet`, `test_predictions.parquet`, models and `reports/experiment/metrics.json`. Both commands now refuse while the baseline is frozen.
2. **Pointer drift.** `verify_state.py`, `results_bundle`, `demo` and the completed-experiment tests followed `latest.json`. They are now pinned to the baseline.
3. The UI hard-coded "1.438" in one footnote. It is now read from the bundle.

## Are results reproducible?

Yes, within the frozen artifacts: stored metrics are reproduced from saved predictions and saved models (`verify_state.py`), and V0.2's 29,700 predictions were reproduced from the saved models (`stability_v02/verification.json`). Inputs, outputs, configs, software versions and code are hashed in `BASELINE_MANIFEST.json` (status PASS). Full re-execution from raw data would additionally depend on the cached raw responses. INCA v1 is announced to retire in December 2026, and the local raw cache preserves this run.

## Can individual model errors be inspected?

Yes:

- `event_diagnostics.csv` has one row per event (60). It includes the positive's rank and controls beaten for 3 models × 3 feature sets, the rank range over repetitions, scores, the margin to the best control, the weather rank change, matching distances and scores, weather distinguishability, the shared-cell count, the positional category and offset sensitivity, and the dependence cluster.
- `sample_scores.csv` has every slope's out-of-training score per variant.
- `error_analysis.md` gives rank distributions against chance, weather improved/worsened counts, the worst and best events, exploratory correlations with data quality, and per-cluster ranks.
- In the web UI, "05 — Einzelne Ereignisse" lets you sort and filter all 60 events (worst/best, weather improved/worsened, coarse position, weakest matching, near-identical weather). It shows the six slopes, their scores, rank, controls beaten and quality indicators.

Key observations (exploratory): development mean ranks are 3.09–4.03 against the chance value of 3.5. No data-quality property correlates noticeably with poor ranks (|Spearman ρ| ≤ 0.16, nominal p ≥ 0.29). In 17/60 events the positive and its controls have nearly identical weather (median standardised difference < 0.05).

## Known scientific limitations (verified; not errors)

The no-signal-beyond-null result (V0.3), the small number of independent clusters, pseudo-negative controls, unverified source position categories, 1 km weather resolution, complete-case weather exclusions, and the unidentified licence of the detailed source. See `LIMITATIONS.md`.

## Is the experiment safely frozen?

Yes: **PreSlide V0.3 Baseline**, `reports/baseline/BASELINE_MANIFEST.json`, verification PASS, guarded by `assert_not_frozen`, CLI refusal and `tests/test_baseline.py`.

## Ready for a substantially larger dataset?

**READY WITH MINOR ISSUES — but the binding constraint is data, not code.**

Technically in place: raw HTTP, terrain, control-pool and per-event checkpoints are cached and checksum-verified. Matching is deterministic (seed from event ID + config). Exclusions are logged with reasons, the run is resumable, and there is one weather request per event. A new config or candidate snapshot yields a new dataset identity, and the baseline cannot be overwritten.

Remaining issues before a larger run:

1. **No more events under the frozen criteria.** The audit's sequential filter leaves exactly 102 candidates for 2015+, and all are used. The steepest losses are process confidence (380 → 108) and single-day dates (2,120 → 700). More data therefore requires a pre-registered change of inclusion criteria (e.g. earlier years, date tolerance, verified positions) or another inventory. That is a scientific decision, not a scaling step.
2. **No versioned runner yet.** `pipeline.py`/`evaluation.py` write fixed baseline paths and are hash-protected. A new version needs a small runner that writes `reports/experiments/<id>/` (≈ 100 lines, reusing existing functions).
3. A network failure aborts the run (status is saved and the run resumes from checkpoints), rather than logging a retryable failure per event.
4. INCA v1 retirement (December 2026) is a deadline for retrieving any additional pre-event weather from the same product.

## Next step

Pre-register the V0.4 inclusion criteria and the independent evaluation set (which additional events, which date/position tolerance, which test episodes), and dry-run the audit to count how many events they yield. Only then implement the versioned runner and run 1 → 5 → 20 events. Do this before the INCA v1 retirement.
