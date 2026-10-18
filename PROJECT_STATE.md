# Current Stage

Session entry point: read `AGENTS.md`, `PROJEKTUEBERBLICK.md` completely, then this file.

2026-10-18 (Phase 2 done, stopped before sampling): **terrain blocks for Iburi (10, EPSG:32654), Gorkha (168) and Far-Western Nepal (42) in `data/susceptibility_v02/terrain/`.** Found a v01 bug: `terrain.dem_window` merged NASADEM on a lattice starting at the requested bounds, shifting every block by up to 0.5 arc-second (<= 15 m); v01 blocks differ from correctly located ones by 4.1 m elevation / 1.6 deg slope on average (Gorkha, p99 19.7 m / 8.7 deg). v01 left unchanged and documented; v02 snaps the merge to the tile lattice and recomputed all three inventories. Open decision before Phase 3: 2.6 % of the Iburi extent is sea (NASADEM 0 m) -> proposed amendment to exclude background cells <= 0 m.

2026-10-18 (Phase 1 done for the earthquake arm): **v02 earthquake Phase 1 gate met.** Iburi ShakeMap v1 frozen (SHA-256 e1ff18e3...), covers all 1,802 GSI extent vertices. Zenodo old landslides: 129 GSI polygons intersect -> 3,177 Iburi positives; old-landslide bbox leaves 18.6 % of the extent (2 polygons) uncovered (documented limitation). Amendment 2: exclusion buffer 100 m (p90 radius: Gorkha 17.47, FWN 93.54, Iburi 87.11 m). Rain arm still not met. Next: NASADEM tiles for Hokkaido (download needs release) -> Iburi terrain (Phase 2) -> sampling (Phase 3).

2026-10-18 (Phase 1, partial): **Iburi now has an independent extent; Gorkha 20 km sensitivity done (exploratory).** GSI D1-No.991 archive contains its interpretation extent as data (closed ring, 1,357.6 km2, plus 10 cloud-obscured polygons); Amendment 1 switches Iburi to GSI polygons + GSI extent (role development, EPSG:32654), no Iburi sample or model yet. Gorkha ShakeMap v1 frozen (SHA-256 3ffbe249...), PGA at all 48,074 v01 samples. Sensitivity: terrain - slope +0.124 (5 km) vs +0.120 [0.096, 0.142] (20 km) -> not a spatial-proximity artefact; with PGA +0.062 = 50.1 % of the 5 km advantage -> rule 'largely explained by shaking' narrowly not met (borderline). Earthquake Phase 1 gate still needs the Iburi ShakeMap (download not released) and the buffer amendment; rain arm still blocked (RER2023). See `reports/susceptibility_v02/SENSITIVITY_GORKHA_20KM.md`.

2026-10-18 (later): **susceptibility_v02 registered (Phase 0 only, no model).** Trigger-specific terrain models (earthquake: terrain + ShakeMap PGA, Gorkha + Iburi; rain: terrain, Far-Western Nepal + RER2023), leave-one-inventory-out within each trigger, confirmatory tests only on the unseen inventories (Bonferroni over 4), pre-registered 20 km block sensitivity for Gorkha. **Phase 1 gate not met for either trigger:** Iburi and RER2023 have no independent mapping extent (Wenchuan checked, excluded). Next step needs the user: request extents from the authors/providers. See `reports/susceptibility_v02/DECISIONS.md`.

2026-10-18: **susceptibility_v01 stopped at the Phase 4 gate.** Phases 0–3 passed (registration, data incl. Gorkha via user browser download, NASADEM terrain, verified sampling). Leave-one-inventory-out (Gorkha <-> Far-Western Nepal): primary HGB mean AUC 0.715 vs slope-only 0.709, difference +0.006 [-0.005, 0.017] -> gate not passed; no extension (Phases 5-14 not run beyond the registered block CV as diagnosis). See `reports/susceptibility_v01/PHASE4_GATE.md`.

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

1. Interpret V0.4/V0.5 together: terrain/land-cover contrast is strong, weather increment unproven in both designs. Do not tune on either.
2. Independent confirmation needs unseen dependence units: tier-2 media events (separately labelled) and soil/antecedent-moisture pilot per `reports/weiterentwicklung_2026-10-14/KONKRETER_AENDERUNGSPLAN.md` (new version, own protocol).
3. Reporting-bias diagnostics (road/settlement distance with dated sources; Sentinel-2 position check); the V0.5 web section is complete.

## susceptibility_v01 (Stand 18.10.2026, am Phase-4-Gate gestoppt)

- Plan `reports/weiterentwicklung_2026-10-17/ANFAELLIGKEITSSYSTEM_PLAN.md`. Namespace `config/susceptibility_v01.json` (schreibgeschützt), `preslide/susceptibility/`, `data|models|reports/susceptibility_v01/`. Registrierung `reports/susceptibility_v01/PREREGISTRATION.json`, Begründungen `DECISIONS.md`.
- Entscheidungen: DEM NASADEM (SRTM, Feb 2000), Copernicus GLO-30 abgelehnt (2011–2015); PGA USGS ShakeMap nur explorativ; Modell B CHIRPS + ERA5-Land, Gate 7 (≥ 15 datierte Ereignisse) voraussichtlich nicht bestanden; Verhältnis 1:1; Puffer-Regel registriert, Wert offen; Südtirol IFFI versiegelt (Codes 2/5/7, 3.523 Polygone, Lizenz widersprüchlich → CC BY-SA 3.0).
- Phase 1: Gorkha (Nutzer-Download nach ScienceBase-Menschprüfung), Far-Western Nepal, RER2023; Kandidaten Iburi und Wenchuan; 25 NASADEM- und 25 Copernicus-Kacheln (Copernicus je Kachel datiert, nur Dokumentation); Südtirol-Teilmenge versiegelt (3.523 Treffer, nicht geöffnet). Amendment 1: RER2023 ausgesetzt (kein Kartierumriss), Far-Western Nepal nur Positive ab 2001, Puffer 100 m.
- Phase 2: Geländeraster 30 m (Amendment 2), 42 + 168 Blöcke. Phase 3: Gorkha 24.037+24.037 (1.260 Blöcke), Far-Western Nepal 1.557+1.557 (303 Blöcke), Verifikation PASS; Pufferfehler (Vieleck-Näherung, 99,54 m) gefunden und vor jedem Modell behoben.
- Phase 4 (Amendment 3, feste Hyperparameter): Gate nicht bestanden (+0,006 [−0,005; 0,017] gegenüber Neigung). Diagnose: innerhalb Gorkha +0,12 (ein Ereignis, Erschütterungs-Stellvertreter möglich), Far-Western Nepal kein Vorteil; TPI kehrt Vorzeichen zwischen Erdbeben und Monsun um. Details `reports/susceptibility_v01/PHASE4_GATE.md`.
- Tests: `tests/test_susceptibility_v01.py` 52 bestanden; Mutationsprüfung 30/30 erkannt. Neue Abhängigkeit `pyshp`.

## susceptibility_v02 (Stand 18.10.2026, Phase 0 registriert)

- `config/susceptibility_v02.json` (schreibgeschützt, SHA `f6883194…`), `preslide/susceptibility/v02.py` (Regeln, Schreibschutz, Leseverbot für den v01-Südtirol-Ordner), `scripts/register_susceptibility_v02.py`, `reports/susceptibility_v02/` (PREREGISTRATION, DECISIONS, phase0_data_audit, mutation_check).
- Datenlage: Erdbeben nur Gorkha mit Umriss (Iburi: kein Umriss im Datensatz, Ellipsen sind aus Rutschungen abgeleitet; Wege: Autoren oder GSI D1-No.991), Regen nur Far-Western Nepal (RER2023: kein Umriss, keine Gemeindeliste; Weg: A. Corsini/Region). Wenchuan ausgeschlossen.
- Tests `tests/test_susceptibility_v02.py` 31 bestanden; Mutationsprüfung 18/18 erkannt. v01-Tests unverändert 52 bestanden.
- Phase 1 (teilweise): `preslide/susceptibility/v02_phase1.py` (GSI-Prüfung, ShakeMap, bilineare PGA), `v02_sensitivity.py`, `scripts/run_susceptibility_v02.py` (läuft mit `python -I`), `scripts/amend_susceptibility_v02.py` (write-once). Amendment 1: Iburi auf GSI-Polygone + GSI-Interpretationsbereich. Sensitivität Gorkha 20 km explorativ gerechnet (Ergebnis oben). Tests: v01 52, v02 31, `test_susceptibility_v02_pga.py` 24 bestanden, 0 übersprungen; Mutationsprüfung PGA/GSI/Sensitivität 21/21 erkannt.
- Phase 1 Erdbeben abgeschlossen: Iburi-ShakeMap, Altrutschungszählung, Amendment 2 (Puffer 100 m). Tests: v01 52, v02 31, v02_pga 32 bestanden, 0 übersprungen; Mutationsprüfung 27/27.
- Phase 2 abgeschlossen: `preslide/susceptibility/v02_terrain.py` (Kachelraster-Korrektur), 4 NASADEM-Kacheln Hokkaido, Blöcke Iburi/Gorkha/Far-Western Nepal, Vergleich mit v01 (`phase2_terrain_v01_comparison_*.json`). Tests: v01 52, v02 31, v02_pga 32, v02_terrain 9 bestanden, 0 übersprungen; Mutationsprüfung 36/36.
- Nächste Schritte: Entscheidung Meerzellen (Amendment vor der Ziehung) → v02-Ziehung Phase 3 (Seed 301) für Gorkha, Far-Western Nepal, Iburi → PGA an den Stichproben → H1/H2 Erdbeben (Bonferroni über 4 bleibt).

## satellite_nn_v01 (Stand 17.10.2026, M0 teilweise)

- Neuer Namespace `preslide/satellite_nn/`, `config/satellite_nn_v01.json` (Status DRAFT_NOT_REGISTERED), Tests `tests/test_satellite_nn.py` (14 bestanden; Fehlerinjektion für Split-, IoU- und Wolken-Regel getestet, scheiterten wie vorgesehen).
- Implementiert: Kachelung/Mosaik/Objekte, Zustandsmaschine, 1:1-Abgleich, Zulassungsregeln für Pseudo-Labels, Modelle A (U-Net/ResNet-18) und B (LR-ASPP/MobileNetV3), maskierter BCE+Dice-Verlust, Namespace-Schutz.
- CPU-Messung (8 Threads, torch 2.14 CPU): Trainingsschritt Batch 4 × 128 px: A 0,29 s, B 0,21 s → ca. 4-5 min je Epoche auf 3.799 Landslide4Sense-Kacheln.
- NICHT erledigt: keine Daten geladen, kein Training, nichts registriert, kein Ergebnis. Landslide4Sense (CC BY 4.0, TrainData.zip 2,48 GB, md5 408f09247e3dd256458bc2f6e9edbffb, Zenodo 10463239) wartet auf Download-Freigabe; h5py fehlt (nötig für .h5).
- Nächste Schritte: Download freigeben → RGB/Masken-Adapter + Audit (1→5→20) → Design registrieren → A trainieren. Satellitenzweige aus origin/main (46dacb2) sind noch nicht integriert.
