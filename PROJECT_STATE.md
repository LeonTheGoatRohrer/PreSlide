# Current Stage

Session entry point: read `AGENTS.md`, `PROJEKTUEBERBLICK.md` completely, then this file.

2026-10-14: **V0.4 complete and verified** (pre-registered extension, sealed external test scored once). The **V0.3 Baseline** (V0, V0.2, V0.3 on dataset `046074ba6f12556c`) is frozen, unchanged and additionally archived write-once in `archive/v0.3-baseline/` (2 872 files, ZIP SHA-256 `da3a136e…`; `python scripts/archive_baseline.py --verify`). Local, non-commercial research; no public deployment.

2026-10-15: **Pipeline B (satellite discovery) implemented and run through Stage 5 on all eligible events**: 137 fine-position events 2018+ screened, 129 usable groups / 724 samples / 15 independence units, event-held-out baselines, held-out rediscovery scan, UNVERIFIED candidate inventory. Pipeline B uses post-event imagery and is isolated from Pipeline A. Stage 6 (unknown-region scan) and candidate validation not started.

# Verified Working

- Baseline: `reports/baseline/BASELINE_MANIFEST.json` (95 hashes) PASS; archive PASS; `scripts/verify_state.py` PASS 0 errors — rechecked after V0.4.
- V0.4 package `preslide/v04/` (writes only `data/v04/`, `models/v04/`, `reports/v04/`; `paths.guard` refuses baseline paths):
  `audit` → `pipeline match|static|context|weather|assemble` → `partition` → `experiment admission|develop|freeze|test` → `report`. Checkpoints carry SHA-256 sidecars; corrupted caches raise.
- Pre-registration `reports/v04/PREREGISTRATION.json` (config SHA `c6d67a85…`, config read-only), amendment 1 (`AMENDMENT_1.json`, before modelling), freeze `FREEZE.json`, single test `test_results.json` (script refuses a second run), `scripts/verify_v04.py` → `reports/v04/verification.json` PASS.
- V0.4 reproduces the 102 baseline candidates and the stored controls of all 60 baseline groups exactly.
- Tests: 106 pytest (incl. 32 date-parser, 21 V0.4 leakage/grouping/CRS/hydrology/model/cache tests) + 5 frontend; build passes; V0.4 web section (07) browser-checked desktop and 375 px. Launch config `preslide-api-v04` (port 8020).

- Pipeline B `preslide/satellite/` (writes only `data/satellite/`, `models/satellite/`, `reports/satellite/`; `paths.guard` refuses everything else, junction-safe):
  `eligibility` → `dataset` → `contact` → `baseline` → `discovery` → `report`, each cached (STAC responses, SCL quicklooks, patch GeoTIFFs with SHA-256 sidecars, per-sample feature JSON). 17 tests in `tests/test_satellite.py` (Pipeline A never imports Pipeline B; V0.4 table has no satellite columns; before strictly before / after strictly after the event day; local cloud/snow screening; group-level pair rule; NDSI snow; seasonal gap; grid snapped to the S2 lattice; phase-correlation shift; collection-dependent reflectance offset; box-filter features; unit holdout). API `/api/satellite`, web section 08 (German), contact sheets inspected visually (3 sheets, 14 events).
- Pre-existing tests `test_baseline.py`/`test_stability.py` fail only inside the git worktree (CRLF checkout, local-only files); they pass in the main checkout.

# Dataset Status

V0.4 run `data/v04/run_c6d67a854ba7/`: 500 tier-A candidates (day confirmed by narrative + structured interval; 2016–2026) → 423 complete groups / 2 538 samples (27 missing weather, 26 too few controls, 15 slope < 5°, 9 negative rain). Development 123 events / 19 units (all 60 baseline groups); sealed test 300 events / 11 units (Stanz 2016: 243). Features: 22 static (terrain incl. curvature, TRI, TPI, relative position, catchment/TWI; CORINE class; lithology), 29 temporal (INCA 18 + same-day 4 + SPARTACUS 2 + SNOWGRID 5); WINFORE not admitted.

Pipeline B (`data/satellite/tables/`): 176 positives 2018+ listed, 129 usable groups / 15 independence units / 724 samples (79 groups with all 5 controls, 50 with 4). Exclusions recorded: 39 position > 20 m, 5 seasonal gap > 90 d, 2 too few controls on both acquisitions, 1 no usable before pair. Usable pairs: median 9 d before / 9 d after the event (max 40 / 61). No L2A before 2017-10, so the 2016 Stanz storm and 2017 events are out. Patches: ~1 500 cached 2.56 km GeoTIFF pairs under `data/satellite/samples/`.

# Important Decisions

- Main analysis = tier-1 quality + tier-A date only; tiers B/C and media tier 2 counted, not analysed.
- t0 = conservative lower bound (daypart/clock), never after provider start; same-day rain missing (not 0) without time.
- Temporal episodes as independence units (spatio-temporal rejected by dependence check). Baseline-linked blocks → development; all baseline-free blocks → sealed test.
- Amendment 1: location links only for positive-involving overlaps (registered rule left a 4-event test).
- Primary model conditional logit (own scipy implementation, no new dependency). 10 m DGM rejected (post-dates events).

- Pipeline B: Earth Search Sentinel-2 L2A (c1 preferred); reflectance offset −0.1 only for `sentinel-2-c1-l2a`, 0 for `sentinel-2-l2a` (verified on vegetation DN; runtime plausibility check). Usability judged locally in the 320 m core and 960 m window (SCL + NDSI), never from scene cloud cover. before/after primaries must be usable at the positive and ≥ 4 controls on the same overpass; event day never used; pairs > 90 DOY apart excluded. Negatives = matched V0.4 controls on the same acquisitions. Candidates stay `satellite_detected_candidate` / `UNVERIFIED`.

# Current Results

- Sealed test, primary (conditional logit combined, unit-weighted local AUC): **0.751 [0.633, 0.866]**, null 95 % 0.629, p = 0.001; static 0.702; temporal 0.604. Combined − static +0.049 [−0.003, +0.108]: **no established weather benefit**. Per event: combined 0.668, static 0.521 (Stanz storm static 0.455).
- Development CV: static 0.770, temporal 0.554, combined 0.725 (conditional logit).
- Main predictors: roughness, forest (−), settlement/other land cover (+), TPI (−) — possibly partly reporting bias.

- Pipeline B, all eligible events (129 groups, 15 units, unit-held-out GroupKFold, 3 fold shuffles): within-group AUC change features LR **0.79** / HGB **0.80** (unit-weighted 0.86; top-1 0.56–0.59 vs chance 0.18; permutation null 95 % 0.56, p = 0.01); contrast-only 0.67 / 0.76; shortcut sets ring-only 0.56–0.63 (surroundings of positives change differently: storm clusters, land cover) and nuisance-only 0.49–0.59. Held-out rediscovery inside the 2.56 km patch (LR, log-odds peaks ≥ 320 m apart, hit = within 160 m): 61/129 found at any rank, 8 at rank 1, 27 in the top 3, 37 in the top 5, median localisation error 70 m, 4.7 peaks/km², 8 false peaks above the hit on average; random peak order would give rank 1 for ≈ 0.11 of detected events. Patch-level discrimination is clear; open-area localisation is only modestly better than random ranking. 1 484 UNVERIFIED candidates (`reports/satellite/candidate_inventory.csv`, local), 578 within 500 m of another known event. Stage 3 pilot (14 groups) gave 0.68–0.74 / 7 of 14 rediscovered.

# Known Problems

Few independent units (11 test); Stanz dominance; reporting/placement bias in land-cover and terrain contrasts; coarse CORINE/geology; triggering rain after t0 invisible; INCA v1 retirement Dec 2026 (all V0.4 responses cached).

Pipeline B: only 2018+ events and few independence units (15, Styria-dominated); storm clusters put neighbouring slides into rings and candidate lists; small slides dilute in 10 m pixels; many weak peaks in the open scan (4.7/km²); candidate types are heuristics, no candidate validated; GDAL segfaults under heavy threading (dataset stage runs with 2 workers and restarts from cache); Sentinel-1 not integrated (no RTC on Earth Search).

# Next 3 Tasks

Planning-only audit (2026-10-14): `reports/weiterentwicklung_2026-10-14/` contains the proposed changes and reproducible candidate counts. Adding 323 tier-2/A media records yields 823 candidates / 110 temporal episodes / 66 provisional positive-linked blocks (before matching and environmental QA); not 66 verified development units or a national maximum. Adding 79 tier-1/C records yields 64 provisional blocks because links merge. No new experiment implemented or scored.

User's alternative V0.5 plan reviewed and extended in `reports/weiterentwicklung_2026-10-14/V05_NACHBARHANG_PLAN.md`: existing 423 positives, ten unmatched local controls, exploratory grouped CV (the old test is seen), fold-level spatial purge and 1:10 ranking metrics. All 423 cached pools exist; source dataset hash verified. Draft only: no V0.5 config, registration, new controls, features or models created.

1. Interpret/present V0.4 honestly: terrain + land-cover signal replicated on a sealed test; weather increment unproven. Do not retune on the test.
2. A new version (V0.5) would need more independent episodes: tier-2 media events as separately labelled data, tiers B/C, or a pre-registered case-crossover design (user decision).
3. Optional QA: Sentinel-2 check of positive positions/controls and of the land-cover/reporting-bias question.

Pipeline B next: (a) candidate validation: persistence in `after_confirm` imagery, manual review of the top-ranked candidates per heuristic type, cross-check with later inventory updates (none promoted without independent evidence); (b) better localisation: pretrained-encoder embeddings or a small change-detection model, generic hard negatives (clear-cuts, fields, construction) sampled away from known events, buffer discovery peaks against all known positives; (c) Stage 6 unknown-region scan on one Styrian storm footprint, Sentinel-1 RTC as extra bands.
