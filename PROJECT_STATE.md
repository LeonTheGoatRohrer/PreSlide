# Current Stage

Session entry point: read `AGENTS.md`, `PROJEKTUEBERBLICK.md` completely, then this file.

2026-10-17 (later): **Executed exploratory two-stage pilot**, isolated under `data/`, `models/`, `reports/mudslide_cascade_v01/`. Context conditional logit: 102 source-classified Hangmure groups, 19 units, purged grouped CV; local AUC 0.539 [0.406, 0.669], no established selection signal. Real RGB-only U-Net/ResNet-18 trained on 192 Landslide4Sense image/mask pairs, 64 technical development pairs, 8 epochs CPU; development Dice 0.512 (source spatial independence unknown). Separate Austrian transfer after quality exclusions: 14 groups / 5 units, image AUC 0.615 [0.430, 0.825], context+image 0.685 [0.525, 0.845], paired difference +0.070 [-0.120, +0.260]: no established gate benefit. Inventory/control labels are weak image labels, no verified new mudslides or calibrated hazard probabilities. User explicitly authorized general-landslide pretraining with separate Hangmure checking. Entry: `python -m preslide.cascade_pilot.report`; see aggregate report. The private context registration contains episode IDs and stays local; a public hash-only registration summary is supplied.

2026-10-17: **Planning only:** concrete single-image neural detector/verifier and controlled self-training plan in `reports/weiterentwicklung_2026-10-17/NEURONALE_MURENSUCHE_PLAN.md`. Proposed namespace `satellite_nn_v01`; no implementation, registration, dataset download or new training. Model agreement remains a pseudo-label; specific mudslide classification requires subtype labels beyond Landslide4Sense. Existing satellite/V0.6–V0.9 work is on separate local branches, not merged here; the plan identifies reusable files and verification limits.

2026-10-15: **UI redesign implemented**: three German pages (Projekt / Vorgehen / Ergebnisse), hash routes including legacy bookmarks, progressive disclosure, real terrain hero, separate V0.4/V0.5 comparisons and correctly labelled intervals. No model runs or scientific artifact edits. Local production app verified on port 8000. Concurrent remote branding commit `75ca8b1` merged: visible product name is now **Talwacht**, internal package and frozen artifact names stay `preslide`/PreSlide.

2026-10-15 (later): **Content/layout pass on the three pages** (plan: `reports/weiterentwicklung_2026-10-14/UI_UEBERARBEITUNG_PLAN.md`): Kurzfassung cards, key-figure strip from API, idea diagram, sticky in-page navigation (`SectionNav.vue`), pipeline strip, real example visible by default, results hero with Hauptstudie/Ergänzungsstudie switch, plain study names. Frontend only; 11 tests + build pass, browser-checked 1280 px and 375 px. No numbers or artifacts changed.

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

# Known Problems

Few independent units (11 test); Stanz dominance; reporting/placement bias in land-cover and terrain contrasts; coarse CORINE/geology; triggering rain after t0 invisible; INCA v1 retirement Dec 2026 (all V0.4 responses cached).

# Next 3 Tasks

1. New image-search priority: independently annotate visible Austrian scars and true confounders, retaining UNKNOWN. A source event point is not a scar mask; do not promote the new predictions into training truth.
2. Keep context filtering optional: the 102-group context pilot and 14-group image-transfer comparison establish no reliable gate benefit. Detailed surrounding land-cover fractions and actual soil data are still absent; any new design gets a new namespace before training.
3. Preserve all frozen results and interpret them together: weather increment remains unproven; geographic confirmation needs unseen dependence units. Existing V0.5 UI is complete; no further model/threshold/seed search on seen results.

## satellite_nn_v01 (Stand 17.10.2026, M0 teilweise)

- Neuer Namespace `preslide/satellite_nn/`, `config/satellite_nn_v01.json` (Status DRAFT_NOT_REGISTERED), Tests `tests/test_satellite_nn.py` (14 bestanden; Fehlerinjektion für Split-, IoU- und Wolken-Regel getestet, scheiterten wie vorgesehen).
- Implementiert: Kachelung/Mosaik/Objekte, Zustandsmaschine, 1:1-Abgleich, Zulassungsregeln für Pseudo-Labels, Modelle A (U-Net/ResNet-18) und B (LR-ASPP/MobileNetV3), maskierter BCE+Dice-Verlust, Namespace-Schutz.
- CPU-Messung (8 Threads, torch 2.14 CPU): Trainingsschritt Batch 4 × 128 px: A 0,29 s, B 0,21 s → ca. 4-5 min je Epoche auf 3.799 Landslide4Sense-Kacheln.
- NICHT erledigt: keine Daten geladen, kein Training, nichts registriert, kein Ergebnis. Landslide4Sense (CC BY 4.0, TrainData.zip 2,48 GB, md5 408f09247e3dd256458bc2f6e9edbffb, Zenodo 10463239) wartet auf Download-Freigabe; h5py fehlt (nötig für .h5).
- Nächste Schritte: Download freigeben → RGB/Masken-Adapter + Audit (1→5→20) → Design registrieren → A trainieren. Satellitenzweige aus origin/main (46dacb2) sind noch nicht integriert.
