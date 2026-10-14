# Current Stage

Session entry point: read `PROJEKTUEBERBLICK.md` completely, then this file; mandatory in `AGENTS.md`. The German overview records the goal, completed versions, limits and next scientific priority.

2026-10-14: **V0 experiment, V0.2 stability/diagnostics and V0.3 null reference are complete, re-verified and frozen as `PreSlide V0.3 Baseline`** (`reports/baseline/`: `BASELINE_MANIFEST.json` with 95 hashed artifacts, `BASELINE_STATUS.md`, event-level `error_analysis.md`). The German web demo shows all three experiments separately, with a central tooltip system and a per-event explorer. Local, non-commercial research use; no public deployment or raw-data redistribution. Full audit: `reports/current_state_audit.md`.

# Verified Working

- Pipeline audit → filtering → terrain (30 m, EPSG:31287) → matched controls → INCA weather → 22 predictors → frozen grouped split → 9 models → Steiermark holdout. `scripts/verify_state.py` independently recomputes the dataset invariants (groups, t0, calipers, circular aspect, separation, CRS, pre-t0 windows, dependence rule). It reproduces every stored test metric from saved predictions *and* saved models, and every V0.2 metric from primary predictions. Result: PASS, 0 errors.
- V0.2 (development only, 45 events / 16 clusters, seeds 11/23/37/51/71 × 4 folds): 180/180 primary fits, all diagnostics A–I present. A peer session's `python -m preslide.stability_verify` → `reports/stability_v02/verification.json` PASS.
- V0.2 completion check: all 440 stored fits / 29,700 predictions reproduced; original artifacts unchanged and original test excluded. Seven scientific figures integrated into the web view; desktop/mobile layout checked. Report regeneration preserves later version sections as well as original documentation bytes.
- V0.3 null reference (`python -m preslide.null_reference`): 100 within-group label permutations on frozen folds; the identity draw reproduces V0.2 exactly.
- `python -m preslide.results_bundle` → `data/web/results.json`, served by `/api/results`. All UI metrics come from artifacts. The bundle sits outside the protected run directory, because the V0.2 manifest hashes every file under `data/processed/<id>/`.
- `python -m preslide.baseline` → event diagnostics for all 60 events from saved predictions only (dev ranks equal V0.2 `event_results` exactly; test AUC/AP recomputed exactly). It verifies the manifest.
- Overwrite guard: `assert_not_frozen()`; `python -m preslide experiment|evaluate` refuse while the baseline is frozen. Baseline readers are pinned via `baseline.pointer()`, not `latest.json`. `pipeline.py`/`evaluation.py` are deliberately unchanged, because V0.2 hash-protects their source.
- UI: `frontend/src/metricDefinitions.js` (central German texts with value-dependent, conservative readings), one `InfoTip.vue` (hover, focus, tap, Esc; bottom sheet < 600 px), "So lesen Sie die Ergebnisse", the five-controls explanation, `EventExplorer.vue` (section 05, de-identified, values from `/api/results`).
- 53 pytest + 5 frontend (`npm test`) tests pass. Build passes; browser-checked at desktop and 375 px with no console errors. Start: `scripts/start.ps1` (port 8000) or uvicorn on any port. Note: an older server process may still hold port 8000 without `/api/results`; restart it.

- 2026-10-14 feature availability audit (`reports/feature_audit_v04/README.md`, `scripts/feature_audit_v04.py`): no training, label-free statistics only, 5 dev groups. Within-group contrast is substantial only for local static data: 30 m curvature/TPI/TWI/stream distance, WorldCover/GFC forest, OSM roads, geology. It is low for SPARTACUS (≈ 0.15 variance share), INCA-derived API/max rain (≈ 0.02) and SPEI (≈ 0). HRL TCD service is down; DGM 10 m needs approval for a 1.94 GB download. The shortlist of 15 is proposed for a next version (V0.4 config already registered; unchanged).

# Dataset Status

102 candidates → 60 complete groups (17 missing weather, 13 insufficient controls, 9 negative precipitation, 3 slope < 5°). 360 samples, 20 dependence clusters (largest 15 events), 29 distinct dates, 2017-08-05 … 2026-06-13, 28/60 in Steiermark. Run `data/processed/046074ba6f12556c/` (frozen; do not overwrite).

# Experiment Status

| Experiment | Status |
| --- | --- |
| Original frozen test (15 events / 4 clusters) | complete, reproduced; already seen, no longer blind |
| Steiermark holdout | complete |
| V0.2 stability + diagnostics | complete and verified |
| V0.3 null reference | complete |

# Current Verified Results

- Original test: RF combined within-group AUC 0.747, AP 0.253; LR combined AP 0.202 (chance 0.167). This is not reproduced in development.
- V0.2 development (median of 5): within-group AUC 0.42–0.59 and AP 0.159–0.190 across all 9 variants. Weather does not repeatedly improve over terrain (LR worse in 5/5).
- V0.3: no variant with weather is distinguishable from the label-permutation null (all p ≥ 0.28). The nominal RF weather gain comes from a below-null terrain baseline. The null 90 % band for local AUC is ≈ 0.41–0.60, so the study is powered only for strong effects.
- Learning curves are flat near chance. Weather inputs do differ between positive and controls (0/300 share a 1 km cell).

# Known Scientific Limitations

Pseudo-negatives and inventory bias; source position categories unverified (23/45 development events cross the 5° caliper under offsets); 1 km weather; few independent storm episodes; complete-case weather exclusions; no geology, land cover, soil moisture or snow. Licence of the detailed source unidentified (local use only; GeoSphere attribution kept).

# Known Technical Issues

- INCA v1 retirement announced for Dec 2026; the raw cache preserves this run.
- Fixed: pilot `experiment --limit` previously had the baseline identity and could overwrite `status.json`, `evaluation_dataset.parquet`, models and `reports/experiment/metrics.json`. It is now refused.
- A larger dataset needs a versioned runner writing `reports/experiments/<id>/` (not yet implemented). Network failures abort the run, which then resumes from checkpoints.
- A concurrent peer session ("Parameterberechnung im Projekt") edited `api.py`, `App.vue`, `stability_*` and tests on 2026-10-14. The changes were compatible and the suite passes. Coordinate before parallel edits.

# Next 3 Priorities

Detailed V0.4+ strategy (data counts, new sources, compute, satellite assessment, phases): `IMPROVEMENT_PLAN.md`. Key counts (2026-10-14): 971 otherwise-eligible events fail only the single-day narrative rule; a pre-registered daypart/clock-time date rule plus a 20-events-per-episode cap gives ≈ 414 candidates in ≈ 60 episodes (V0: 102 / 31). Awaiting user approval of the relaxed date rule.

0. Under the frozen V0 criteria the source has exactly 102 candidates, and all are used. More data needs pre-registered V0.4 inclusion criteria or another source. Dry-run the audit to count events, then implement the versioned runner (1 → 5 → 20 → full). Mind the INCA v1 retirement (December 2026).
1. Pre-register and collect an independent external evaluation set: new storm episodes with verified positions, scored once with the frozen models and protocols.
2. Only as a new versioned experiment, add one diagnostically motivated information source: antecedent soil moisture/snowmelt (e.g. ERA5-Land) or better event positions. No tuning on existing test data.
3. Competition narrative: present the matched same-time design and the null-calibrated negative result as the contribution, with limitations intact.
