# Current Stage

Session entry point: read `AGENTS.md`, `PROJEKTUEBERBLICK.md` completely, then this file.

2026-10-15 (Umsetzungsplan, main-compatible parts): **P1 infrastructure done** (GitHub Actions CI `.github/workflows/ci.yml`, `local_data` pytest marker, ruff errors-only in `pyproject.toml`, `scripts/register.py` write-once registration + `config/REGISTRATION_TEMPLATE.json`, `scripts/check_json_reports.py`). **V0.6 done** (plan package P3.1, renamed because V0.5 was taken): 23 hydrological rain features (antecedent precipitation index, intensity-duration maxima, wet days, dry spells, rain + snowmelt) on the frozen V0.5 cohort, registered in `config/v06.json` before computing; primary combined_hydro − combined (conditional logit) = −0.013, repetition-1 unit-bootstrap interval [−0.029, +0.016] → **no established benefit**; all four paired comparisons are in `reports/v06/summary.md`. Also done later the same day: **V0.7** (P3.2, OpenStreetMap distance to buildings/roads, 813 MB Geofabrik extract, ODbL) and **V0.8** (P4, time-stratified case-crossover, referents t0 ±28/±56 d, 376 slopes / 23 units). Not done: plan P2 (Pipeline B satellite work lives on branch `claude/preslide-satellite-discovery-cfa1d5`, not merged here), P3.2 reporting-bias covariates (needs an OSM/BEV download, licence + user go-ahead), P4 case-crossover (needs new hourly INCA downloads, ~14 h rate-limited).

2026-10-15: **UI redesign implemented**: three German pages (Projekt / Vorgehen / Ergebnisse), hash routes including legacy bookmarks, progressive disclosure, real terrain hero, separate V0.4/V0.5 comparisons and correctly labelled intervals. No model runs or scientific artifact edits. Local production app verified on port 8000. Concurrent remote branding commit `75ca8b1` merged: visible product name is now **Talwacht**, internal package and frozen artifact names stay `preslide`/PreSlide.

2026-10-14 (evening): **V0.5 complete and verified** (exploratory neighbour-slope ranking vs ten unmatched controls; `reports/v05/`, verification PASS). Before that, the same day: **V0.4 complete and verified** (pre-registered extension, sealed external test scored once). The **V0.3 Baseline** (V0, V0.2, V0.3 on dataset `046074ba6f12556c`) is frozen, unchanged and additionally archived write-once in `archive/v0.3-baseline/` (2 872 files, ZIP SHA-256 `da3a136e…`; `python scripts/archive_baseline.py --verify`). Local, non-commercial research; no public deployment.

# Verified Working

- Baseline: `reports/baseline/BASELINE_MANIFEST.json` (95 hashes) PASS; archive PASS; `scripts/verify_state.py` PASS 0 errors — rechecked after V0.4.
- V0.4 package `preslide/v04/` (writes only `data/v04/`, `models/v04/`, `reports/v04/`; `paths.guard` refuses baseline paths):
  `audit` → `pipeline match|static|context|weather|assemble` → `partition` → `experiment admission|develop|freeze|test` → `report`. Checkpoints carry SHA-256 sidecars; corrupted caches raise.
- Pre-registration `reports/v04/PREREGISTRATION.json` (config SHA `c6d67a85…`, config read-only), amendment 1 (`AMENDMENT_1.json`, before modelling), freeze `FREEZE.json`, single test `test_results.json` (script refuses a second run), `scripts/verify_v04.py` → `reports/v04/verification.json` PASS.
- V0.4 reproduces the 102 baseline candidates and the stored controls of all 60 baseline groups exactly.
- Tests: 106 pytest (incl. 32 date-parser, 21 V0.4 leakage/grouping/CRS/hydrology/model/cache tests) + 5 frontend; build passes; V0.4 web section (07) browser-checked desktop and 375 px. Launch config `preslide-api-v04` (port 8020).

- V0.5 package `preslide/v05/` (writes only `data/v05/`, `models/v05/`, `reports/v05/`; V0.4 caches/tiles read through read-only layers): `pipeline pools|select|static|context|weather|assemble` → `partition proximity|freeze` → `experiment main` → `report`; `scripts/verify_v05.py` PASS (incl. hash snapshot proving V0.4 untouched). 18 tests in `tests/test_v05.py`. Web section 08 (German, map with example groups and all 418 events; `/api/results_v05`, bundle `python -m preslide.v05.web`) browser-checked desktop and 375 px.

- UI verification (2026-10-15): 11 frontend tests, 0 failures/skips; production build PASS. New interval-source test rejected an intentionally wrong model mapping before passing on restored code. Browser checks: desktop 1440 px, mobile 375 px and landscape 812 × 375; navigation/direct links/back/forward, disclosures/keyboard, maps/case selection, weather controls, historical figures/explorer/model table, tooltips/Escape. Isolated local proxy confirmed loading, HTTP 503, and independent retry recovery with real API data. Baseline 95 artifact hashes unchanged; archive verification PASS (2,872 members). No pipeline changes; the merged remote API change only renames its title. Python pipeline tests were not rerun.

- V0.6 package `preslide/v06/` (`pipeline hydro` reads hourly INCA only from the V0.4/V0.5 response caches, no network; `experiment main`; `report`); `scripts/verify_v06.py`; 9 tests in `tests/test_v06.py` (injected bugs in the t0 boundary and block anchoring were caught). In a worktree with `core.autocrlf=true` the baseline-manifest check of `verify_v06.py` fails (CRLF); it passes in the main checkout, so run the final verification there.

# Dataset Status

V0.4 run `data/v04/run_c6d67a854ba7/`: 500 tier-A candidates (day confirmed by narrative + structured interval; 2016–2026) → 423 complete groups / 2 538 samples (27 missing weather, 26 too few controls, 15 slope < 5°, 9 negative rain). Development 123 events / 19 units (all 60 baseline groups); sealed test 300 events / 11 units (Stanz 2016: 243). Features: 22 static (terrain incl. curvature, TRI, TPI, relative position, catchment/TWI; CORINE class; lithology), 29 temporal (INCA 18 + same-day 4 + SPARTACUS 2 + SNOWGRID 5); WINFORE not admitted.

V0.5 run `data/v05/run_5b86b6475ecb/`: 423 positives × 10 unmatched controls (all 423 pools audited; all selected) → 418 groups / 4 598 samples / 29 units (4 negative-rain, 1 DEM-check exclusion).

# Important Decisions

- Main analysis = tier-1 quality + tier-A date only; tiers B/C and media tier 2 counted, not analysed.
- t0 = conservative lower bound (daypart/clock), never after provider start; same-day rain missing (not 0) without time.
- Temporal episodes as independence units (spatio-temporal rejected by dependence check). Baseline-linked blocks → development; all baseline-free blocks → sealed test.
- Amendment 1: location links only for positive-involving overlaps (registered rule left a 4-event test).
- Primary model conditional logit (own scipy implementation, no new dependency). 10 m DGM rejected (post-dates events).

- V0.5: registered in `config/v05.json` (write-once registration), cohort + CV/purge plan frozen before models; primary = purged CV (training units with any sample < 1 km from held-out samples removed). DEM 5 m alignment check failure = technical exclusion (not relaxed).

# Current Results

- Sealed test, primary (conditional logit combined, unit-weighted local AUC): **0.751 [0.633, 0.866]**, null 95 % 0.629, p = 0.001; static 0.702; temporal 0.604. Combined − static +0.049 [−0.003, +0.108]: **no established weather benefit**. Per event: combined 0.668, static 0.521 (Stanz storm static 0.455).
- Development CV: static 0.770, temporal 0.554, combined 0.725 (conditional logit).
- Main predictors: roughness, forest (−), settlement/other land cover (+), TPI (−) — possibly partly reporting bias.

- V0.5 (exploratory, seen events): conditional logit combined 0.851 (0.835–0.863), static 0.865, temporal 0.719, slope rule 0.572; combined − static −0.023 [−0.079, 0.019] → no weather benefit. Matched controls on the same cohort: 0.705. Separation driven by elevation/position + land cover (reporting bias plausible).

- V0.6 (exploratory, seen events, 29 units): conditional logit combined 0.851 → combined+hydro 0.838; boosting 0.798 → 0.807; temporal-only boosting +0.041 [−0.025, +0.097]. None of the four paired intervals excludes zero. Several hydrological features correlate up to |ρ| = 1.00 with V0.5 temporal features (redundant by construction).

- V0.7 (exploratory): distance to buildings/roads alone ranks the reported slope at 0.928 (conditional logit; CI 0.888–0.957) versus static terrain 0.865 → much of the V0.5 separation is visibility/placement (partly built into the design: controls are 0.75–10 km away). Adding the distances to the static model: +0.054 [+0.027, +0.082]. With controls within a factor 2 of the positive's infrastructure distance (173 of 418 groups, 10 units) the unaware static model keeps 0.783 (−0.013 [−0.068, +0.031]); land-cover ablation shrinks from −0.040 (all) to −0.008 (caliper).
- V0.8 (exploratory, 376 slopes, 23 units): case-crossover conditional logit temporal 0.818 (repetition-1 CI [0.759, 0.912]) versus 0.757 for the neighbour design on the same slopes; temporal+hydro 0.755 (paired −0.172 [−0.293, −0.065], more features overfit); boosting 0.744/0.708 (no established difference). Event times are wetter than referents largely because the inventory documents storm episodes; this is a "when" result, not a forecast.

# Known Problems

Few independent units (11 test); Stanz dominance; reporting/placement bias in land-cover and terrain contrasts; coarse CORINE/geology; triggering rain after t0 invisible; INCA v1 retirement Dec 2026 (all V0.4 responses cached).

# Next 3 Tasks

1. Interpret V0.4/V0.5 together: terrain/land-cover contrast is strong, weather increment unproven in both designs. Do not tune on either.
2. Independent confirmation needs unseen dependence units: tier-2 media events (separately labelled) and soil/antecedent-moisture pilot per `reports/weiterentwicklung_2026-10-14/KONKRETER_AENDERUNGSPLAN.md` (new version, own protocol).
3. Reporting-bias diagnostics (road/settlement distance with dated sources; Sentinel-2 position check); the V0.5 web section is complete.
