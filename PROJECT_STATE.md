# Current Stage

Session entry point: read `AGENTS.md`, `PROJEKTUEBERBLICK.md` completely, then this file.

2026-10-18 (abends): **Gebietstest der Prüfstufen** (`wirkungskette_gebietstest_v01`, registriert als wirkungskette_v02, Branch `claude/wirkungskette-v02-gebietstest`): vorab registriert, einmal ausgewertet, eingefroren (`reports/wirkungskette_gebietstest_v01/FREEZE.json`). 5 ungesehene Kampagnen 2005–2015 (Vorarlberg/Tirol 2005, Nordhälfte 2013, Sellrain 2015, Gasen/Haslau 2005, Klingfurth 2009), Gebiete = LAU-2021-Gemeinden mit ≥ 5 genau verorteten reinen Hangmuren, SRTM 2000, CORINE nach Jahr. Primär (obere 20 %, Gebiete gleich gewichtet): V0.4-Gelände 45,8 % [27,5; 64,1], Neigung 22,9 % [9,3; 40,8], Zufall 20 %; Differenz +22,9 Pp. [+12,7; +30,5]. Nur 5 Einheiten; die Gebiete sind jetzt gesehen. Amendment 1: Skadi über Österreich = praktisch SRTMGL1 (99,5–99,8 % zellgleich). Zweites Demogebiet Mittelberg 2005 mit Gebietswähler in API/UI. 65 Pytest, 6/6 Mutationen erkannt.

2026-10-18 (später): **Wirkungskette v01** (Branch `claude/wirkungskette-v01-f4836f`, nicht in main): Namespace `preslide/wirkungskette/`, `config/wirkungskette_v01.json`, Demogebiet Stanz 25.07.2016 (versiegelter, gesehener Test, nur Demonstration). Prüfpunkte = eingefrorenes V0.4-Statikmodell (nur Entwicklungsdaten) auf 90-m-Zellen, Stufen relativ zum Umkreis 1–10 km; Auslauf = D8 auf gefülltem 30-m-DEM, Reichweiten 45/467 m (Hürlimann et al. 2015) und Energielinie 11°/7° mit 15 m/s (Horton et al. 2013), 50-m-Korridor; Exposition gegen OSM (heutiger Stand). Auslauf unvalidiert (keine Referenzen im Inventar). Explorativ: Stufe 1 enthält 3,4 % der Stanz-Ereignisse bei 5 % Fläche (Hangmuren 1,8 %), also keine Konzentration. Tests: 38 Pytest (11/11 Mutationen erkannt) + 7 neue Frontend-Tests; volle Suite im Worktree 214 bestanden, 11 Ausfälle nur in Baseline/Stabilität/V0.4-Checkpoint durch fehlende lokale Dateien und Junction-Pfade (in Hauptkopie zu wiederholen); Browser Desktop und 375 px geprüft. Bericht `reports/wirkungskette_v01/summary.md`, Audit `AUDIT.md`. Hangkarte-Branch nicht übernommen (V0.5-Modell wäre in Stanz in-sample); Rasterlogik/Abfragen portiert.

2026-10-18: **Prüfgebiete-Grundgerüst** (4. Seite `#/pruefgebiete`, bewusst gegen die 3-Seiten-Regel, auf ausdrücklichen Auftrag): read-only Ereignisübersicht `preslide/pruefgebiete/` aus dem eingefrorenen V0.4-Lauf (`python -m preslide.pruefgebiete` → `data/pruefgebiete_v01/web/overview.json`, `/api/pruefgebiete`). Zeigt Zählungen, Episoden (3-Tage-Regel), 5-km-Cluster und Karte. Keine Modelle, keine Wahrscheinlichkeiten, keine Fließwege; drei Platzhalterfelder für spätere Ergebnisse. 11 Pytest-Tests (Mutationsprüfung: Clusterschwelle verletzt → 2 Tests scheitern); Frontend-Tests 11 bestanden, Build bestanden, Browser geprüft (Karte, 375 px ohne Seitenüberlauf). Befund: der dichteste Cluster (25.07.2016, 243 Ereignisse, Stanz) ist ein einzelner Sturm; Dichte ist daher keine Zahl unabhängiger Beobachtungen.
Offen: Der Branch `claude/clever-satoshi-e4ace7` enthält eine eigene „Hangkarte“ (hangmap_v01), nicht in dieser Linie; Zusammenführung nicht entschieden. `reports/mudslide_cascade_v01/` (Pilot, Umgebungsvorauswahl für Hangmuren: lokale AUC 0,539, kein Nutzen belegt) liegt nur lokal und ist nicht committet.

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

## satellite_nn_v01 (Stand 17.10.2026, M0 teilweise)

- Neuer Namespace `preslide/satellite_nn/`, `config/satellite_nn_v01.json` (Status DRAFT_NOT_REGISTERED), Tests `tests/test_satellite_nn.py` (14 bestanden; Fehlerinjektion für Split-, IoU- und Wolken-Regel getestet, scheiterten wie vorgesehen).
- Implementiert: Kachelung/Mosaik/Objekte, Zustandsmaschine, 1:1-Abgleich, Zulassungsregeln für Pseudo-Labels, Modelle A (U-Net/ResNet-18) und B (LR-ASPP/MobileNetV3), maskierter BCE+Dice-Verlust, Namespace-Schutz.
- CPU-Messung (8 Threads, torch 2.14 CPU): Trainingsschritt Batch 4 × 128 px: A 0,29 s, B 0,21 s → ca. 4-5 min je Epoche auf 3.799 Landslide4Sense-Kacheln.
- NICHT erledigt: keine Daten geladen, kein Training, nichts registriert, kein Ergebnis. Landslide4Sense (CC BY 4.0, TrainData.zip 2,48 GB, md5 408f09247e3dd256458bc2f6e9edbffb, Zenodo 10463239) wartet auf Download-Freigabe; h5py fehlt (nötig für .h5).
- Nächste Schritte: Download freigeben → RGB/Masken-Adapter + Audit (1→5→20) → Design registrieren → A trainieren. Satellitenzweige aus origin/main (46dacb2) sind noch nicht integriert.
