# Current Stage

Session entry point: read `AGENTS.md`, `PROJEKTUEBERBLICK.md` completely, then this file.

2026-10-18: **Integration branch `claude/integration-2026-10-18`** = `origin/main` (V0.9, V0.6–V0.8, Pipeline B, CI) + `claude/fervent-dubinsky-95540c` (local-main commits: satellite_nn_v01 skeleton, neural search plan, hazard-research master prompt; dataset survey; susceptibility_v01/v02) + `claude/wirkungskette-v03` (Prüfgebiete page, wirkungskette_v01, v02 Gegenprobe, v03 null reference) + `claude/extremwetter-v01-9c97b3` + `claude/website-jury-d7408d` (jury web entry, master prompts, project assessment, training plan) + `claude/anfaelligkeit-at-v01` (registration, amendment 1, pipeline, tests; no result) + `claude/clever-satoshi-e4ace7` (Hangkarte hangmap_v01, merged on the user's request; placed as a research page `#/hangkarte` so the jury navigation stays unchanged). Conflicts were only in the state/overview/data-source docs and were resolved without dropping content; frozen artifacts (§45) are byte-identical to `origin/main`.

Not integrated (see Known Problems): `claude/wirkungskette-v02-gebietstest` (run in progress, namespace collision), local-only `reports/mudslide_cascade_v01/`.

The core question is answered for this design: terrain separates above chance, a weather increment is not established anywhere (V0.4 sealed test, V0.5/V0.6, V0.9). Next focus per user: UI work on this common line.

# Verified Working

- **Baseline** (V0–V0.3, dataset `046074ba6f12556c`): `reports/baseline/BASELINE_MANIFEST.json` (95 hashes), write-once archive `archive/v0.3-baseline/` (2 872 files); `scripts/verify_state.py`, `scripts/archive_baseline.py --verify`.
- **V0.4** `preslide/v04/` (writes only `data|models|reports/v04/`): audit → pipeline → partition → experiment admission|develop|freeze|test → report; config read-only, PREREGISTRATION/AMENDMENT_1/FREEZE, single scored test; `scripts/verify_v04.py`.
- **V0.5–V0.9** `preslide/v05/` … `preslide/v09/`, each with own namespace, registration before modelling and `scripts/verify_v0X.py`. V0.9 re-scores all 18 models with max prediction difference 0.0.
- **Pipeline B** `preslide/satellite/` (writes only `data|models|reports/satellite/`, never imported by Pipeline A): eligibility → dataset → contact → baseline → discovery → report; satellite-0.2 validation/review/landscape/baseline-random/embeddings (optional torch).
- **extremwetter_v01** `preslide/extremwetter/` (registered SHA `98e33aa7…`, amendment 1), `/api/extremwetter`, second run bit-identical.
- **wirkungskette_v01–v03** `preslide/wirkungskette/`, `preslide/pruefgebiete/`; `/api/pruefgebiete`, wirkungskette routes; mutation checks 11/11, 13/13, 17/17.
- **susceptibility_v01/v02** `preslide/susceptibility/` (configs read-only; v02 Phase 4 scored once, write-once); mutation checks 30/30 and 52/52; dependency `pyshp`.
- **anfaelligkeit_at_v01** `preslide/anfaelligkeit_at_v01/` (registered, amendment 1, mutation check script); not run.
- **hangmap_v01** `preslide/hangmap/` (frozen V0.5 static model applied to free areas, model SHA checked, writes only `data/hangmap_v01/`), `/api/hangkarte` routes, page `#/hangkarte`, `tests/test_hangmap.py` (17 tests; 3 injected bugs caught), `frontend/tests/hangkarte.test.mjs`.
- **satellite_nn_v01** `preslide/satellite_nn/` skeleton with tests (DRAFT_NOT_REGISTERED).
- **Frontend**: jury entry (Start · Demo · Ergebnisse · Methodik & Grenzen · Forschung) plus research pages under old routes; wording test forbids probability/risk/forecast words on jury pages.
- Verification of this integration (2026-10-18, worktree with junctions to the main checkout's `data/`, `models/`, `.venv/`, `frontend/node_modules`; main checkout not switched because it holds staged work): pytest **571 passed, 7 failed, 4 errors, 0 skipped** (after the Hangkarte merge; 554 before); frontend 31/31 tests, build PASS; Hangkarte browser-checked (example area computed, 375 px without horizontal scroll). Failures: 4 junction-path artefacts (3 × `test_frozen_artifacts_cannot_be_overwritten`, `test_corrupted_checkpoint_is_rejected`) plus the two pre-existing `origin/main` problems listed under Known Problems (`test_manifest_hashes_unchanged`, 4 × `test_stability`). With main-checkout CRLF bytes and the baseline `requirements-lock.txt` temporarily in place: `verify_state`, `verify_v04`, `verify_v06`, `verify_v07`, `verify_v08`, `archive_baseline --verify` PASS; `verify_v09` PASS on the clean tree; `verify_v05` FAIL only because `preslide/v04/*.py` changed on `origin/main`.

# Dataset Status

- V0.4 run `data/v04/run_c6d67a854ba7/`: 500 tier-A candidates → 423 groups / 2 538 samples (27 missing weather, 26 too few controls, 15 slope < 5°, 9 negative rain). Development 123 events / 19 units; sealed test 300 / 11 (Stanz 2016: 243). 22 static + 29 temporal features.
- V0.5 run `data/v05/run_5b86b6475ecb/`: 418 groups / 4 598 samples / 29 units (10 unmatched controls each).
- Pipeline B `data/satellite/tables/`: 129 usable groups / 15 units / 724 samples (2018+, position ≤ 20 m); 386 RANDOM_LANDSCAPE points.
- V0.9 run `data/v09/run_befb8880818e/`: media 24 groups / 14 units, Kärnten 21 / 16, pooled 45 / 30.
- extremwetter_v01: 422 events / 35 episodes (SPARTACUS 1961–2026).
- susceptibility: Gorkha 24 036+24 036, Far-Western Nepal 1 551+1 551, Iburi 3 177+3 177 (v02 samples, NASADEM 30 m).
- Full GeoSphere inventory: 3 416 pure Hangmuren, 2 686 precisely located (basis for anfaelligkeit_at_v01 and the Gebietstest).

# Important Decisions

- Main analysis = tier-1 quality + tier-A date; t0 = conservative lower bound; temporal episodes are the independence units; baseline-linked blocks → development, all others → sealed test (V0.4 amendment 1).
- Primary model conditional logit (own scipy implementation). 10 m DGM rejected (post-dates events). Skadi 1″ over Austria ≈ SRTMGL1 v3 (Feb 2000): provenance, not file date, satisfies the pre-event DEM rule (anfaelligkeit_at_v01 amendment 1, Gebietstest amendment 1).
- V0.9: Kärnten t0 = local midnight 3 days before the reported day (antecedent only); unseen = no shared V0.4 block.
- Pipeline B uses post-event imagery and stays isolated from Pipeline A; candidates stay `UNVERIFIED` until validated.
- Wirkungskette: runout scenarios are literature bands on a D8 route, explicitly unvalidated; wording "Prüfstufe / Szenario / Rangfolge", never probability or risk.
- Namespace rule: every new study gets its own `config/`, `preslide/`, `data|models|reports/` namespace, registered before modelling. Namespace collision found during integration: `wirkungskette_v02` is the Gegenprobe; the Gebietstest moves to `wirkungskette_gebietstest_v01` (its amendment 1).

# Current Results

- V0.4 sealed test (conditional logit, unit-weighted local AUC): combined **0.751 [0.633, 0.866]**, null 95 % 0.629, p = 0.001; static 0.702; temporal 0.604; combined − static +0.049 [−0.003, +0.108] → **no established weather benefit**. Per event 0.668 (static 0.521; Stanz static 0.455). Dev CV: static 0.770, temporal 0.554, combined 0.725. Main predictors roughness, forest (−), settlement land cover (+), TPI (−), possibly reporting bias.
- V0.5 (exploratory): combined 0.851 (0.835–0.863), static 0.865, temporal 0.719, slope rule 0.572; combined − static −0.023 [−0.079, 0.019]. Matched controls on the same cohort 0.705.
- V0.6: combined 0.851 → +hydro 0.838 (−0.013 [−0.029, +0.016]); no paired interval excludes zero.
- V0.7: infrastructure distance alone 0.928 (0.888–0.957); within a factor-2 infrastructure caliper (173 groups, 10 units) static 0.783 (−0.013 [−0.068, +0.031]).
- V0.8: case-crossover temporal 0.818 [0.759, 0.912]; +hydro −0.172 [−0.293, −0.065]. "When" result, not a forecast.
- V0.9 (exploratory; audit gate failed, 14 < 15 units): media static **0.770**, combined 0.752, combined − static −0.019 [−0.121, +0.082]; Kärnten static 0.627, combined 0.552; pooled static 0.694, combined 0.645. One positive boosting/media interval among 72 comparisons.
- Pipeline B: within-group AUC LR 0.79 / HGB 0.80 (permutation null 95 % 0.56, p = 0.01); ring-only shortcut 0.56–0.63; rediscovery 61/129, rank 1 11 after known-positive suppression; top-30 candidates 0 LIKELY, 21 REJECTED, 9 UNVERIFIED (cloud-edge dominated); RANDOM_LANDSCAPE positive-vs-random 0.66 → 0.69 when trained with them; ResNet-18 embeddings 0.53.
- extremwetter_v01 (exploratory, 35 episodes): primary 3-day mean rank 0.587 [0.481, 0.691], p = 0.028 → rule not met; 7/14/30 d 0.60–0.61; share above local Q95 (3 d) 24.6 % [11.8, 38.2] vs 5 %, rate ratio 6.2 [2.5, 11.7]; placebo unremarkable; robust without Stanz.
- wirkungskette: tier 1 holds 3.4 % of Stanz events on 5 % of the area (no concentration). v02 Gegenprobe (24 Gasen damage reports): road in scenario 21–22/22, but 20/22 points already ≤ 25 m from a road. v03 null reference (500 cells): road in longest scenario 0.79 [0.68, 0.88], ≤ 25 m 0.04. Agreement comes from the reported position, not the runout.
- susceptibility_v01: Gorkha ↔ Far-Western Nepal HGB 0.715 vs slope 0.709 (+0.006 [−0.005, 0.017]) → gate not passed. v02: Gorkha → Iburi terrain+PGA 0.826 vs slope+PGA 0.841 (−0.015 [−0.040, 0.009]) → H1 failed, not supported; rain arm not testable.
- mudslide_cascade_v01 pilot (local only, exploratory): local AUC 0.539 [0.406, 0.669] for pure Hangmuren.

# Known Problems

- **Pre-existing on `origin/main`, found during integration (never seen before because the main checkout stayed on the older local `main`):** (a) `requirements-lock.txt` is a frozen baseline-manifest entry but V0.7 (`96352f7`, osmium) changed it and susceptibility added `pyshp`, so `test_manifest_hashes_unchanged` and every verifier's baseline-manifest check fail; (b) the ruff cleanup `b93b937` edited protected original code (`preslide/matching.py`, `pipeline.py`, `weather.py` → 4 `test_stability` errors; `preslide/v04/*.py` → `verify_v05` `v04_untouched` FAIL). No frozen artifact file was edited; the fix (restore the protected bytes, move new pins to a separate lock file) is open.
- Few independent units (11 sealed-test units; Stanz dominance); reporting/placement bias in land-cover and terrain contrasts; coarse CORINE/geology; INCA v1 retirement Dec 2026 (V0.4 responses cached).
- GeoSphere media process labels unreliable (7 of 15 verifiable reports describe flooding); open Austrian sources yield only ~30 unseen units under the V0.4 linkage rule.
- Pipeline B: 2018+ only, 15 units, cloud/haze edges dominate the candidate ranking (whole-patch screening needed), Sentinel-1 not integrated, GDAL segfaults under heavy threading (rerun from cache).
- Worktrees: `data/`, `models/`, `.venv/` are junctions to the main checkout; tracked files are LF in worktrees but CRLF in the main checkout, so baseline/V0.4 hash checks (`verify_state`, `verify_v04`, `test_baseline`, `test_stability`) fail in worktrees and must run on main-checkout bytes.
- Not integrated: `claude/wirkungskette-v02-gebietstest` (pre-registered test on unseen Hangmuren areas; full run unfinished with uncommitted changes in its worktree; must move to `wirkungskette_gebietstest_v01` before merging); `reports/mudslide_cascade_v01/` and `preslide/cascade_pilot/` are staged but uncommitted in the main checkout, so `/api/hangmuren_pilot` returns 503 on a clean checkout; `claude/anfaelligkeit-at-v01` has an uncommitted change to `experiment.py` in its worktree.

# Next 3 Tasks

1. UI work on this integrated line (user's next focus); keep wording/interval tests green and numbers sourced from API bundles.
2. Finish the wirkungskette Gebietstest in its own namespace and merge it; commit or discard the Hangmuren pilot; run anfaelligkeit_at_v01 (pilot 1 → 5 → all areas).
3. Register a time-forward test on events after 2026-10-15 (score once ≥ 15 new units; fix the INCA v1 → v2 transition first). Optional data requests only with the user's go-ahead.
