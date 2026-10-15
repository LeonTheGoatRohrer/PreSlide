# PreSlide V0

A working local scientific prototype: can pre-event weather distinguish a documented Austrian landslide slope from five nearby topographically matched pseudo-negative slopes?

**Executed:** 102 candidates checked; **60 complete positive events + 300 controls**, real pre-event terrain, real guarded 60-day INCA histories, 3 model families x 3 feature sets, grouped evaluation and geographic holdout. German Vue/MapLibre/FastAPI demonstration. See [RESULTS.md](RESULTS.md).

The result is exploratory: temporal features help some models on the grouped test, but only four test clusters remain and geographic transfer is inconsistent. No robust precursor-detection or operational warning claim is made.

## Open the local demo

After setup, from the repository root:

```powershell
.\scripts\start.ps1
```

Open http://127.0.0.1:8000. The server binds to loopback only. Stop it with Ctrl+C. The baseline example and title image use locally generated terrain imagery; the V0.5 map additionally loads OpenStreetMap tiles and shows a fallback message if they are unavailable. It exposes allowlisted baseline and V0.5 example groups and aggregate results; there is no raw inventory download or bulk source-record endpoint.

## Setup

Python 3.11 and Node.js 22.14 were used. Python dependency versions are frozen in `requirements-lock.txt`; frontend versions in `frontend/package-lock.json`. CPU-only; no CUDA/GPU dependency. System curl is required for source retrieval.

Windows:

```powershell
.\scripts\setup.ps1
```

Equivalent steps on another platform:

```text
python -m venv .venv
# Activate .venv using your platform's activation command.
python -m pip install -r requirements-lock.txt
cd frontend
npm ci --ignore-scripts
npm run build
cd ..
```

The Windows setup exports the current Windows trusted certificate store for Python/npm when needed. Certificates stay local under ignored `data/runtime`; TLS verification is never disabled. No global certificate or npm configuration is changed.

## Reproduce from the local snapshots

The snapshots are intentionally not part of the public deliverable. On this machine they already exist, so do not redownload them.

**Frozen baseline (2026-10-14):** dataset `046074ba6f12556c` and all V0/V0.2/V0.3 results are frozen as *PreSlide V0.3 Baseline* (`reports/baseline/`). `experiment` and `evaluate` now refuse to run while the baseline manifest exists, because they write fixed paths of that run. The commands below document how the baseline was produced; a larger dataset must be a new versioned experiment (see `reports/baseline/README.md`).

```powershell
.\.venv\Scripts\python -m preslide.baseline              # event diagnostics + error analysis; verifies the manifest
.\.venv\Scripts\python -c "from preslide.baseline import verify_manifest; print(verify_manifest()['status'])"
cd frontend; npm test                                      # wording/reference tests for the UI explanations
```

Historical baseline commands (run from the root with the virtual environment Python):

```powershell
.\.venv\Scripts\python -m preslide audit
.\.venv\Scripts\python -m preslide experiment --limit 1
.\.venv\Scripts\python -m preslide experiment --limit 5
.\.venv\Scripts\python -m preslide experiment --limit 20
.\.venv\Scripts\python -m preslide evaluate
.\.venv\Scripts\python -m preslide experiment --limit 102
.\.venv\Scripts\python -m preslide evaluate
.\.venv\Scripts\python scripts/report_results.py
.\.venv\Scripts\python -m preslide.demo
.\.venv\Scripts\python -m pytest -q
```

Development-only analyses on the frozen dataset (checkpointed, never touch the original test):

```powershell
.\.venv\Scripts\python -m preslide.stability --pilot      # then --primary, --diagnostics
.\.venv\Scripts\python -m preslide.stability_analysis --base   # then --importance --pilot, --importance, --final
.\.venv\Scripts\python -m preslide.null_reference        # V0.3 null reference, 100 draws, resumable
.\.venv\Scripts\python scripts/verify_state.py           # independent re-verification -> reports/verification/
.\.venv\Scripts\python -m preslide.results_bundle        # aggregate web bundle from saved artifacts
```

V0.2 integrity: `stability_analysis --base` writes `reports/stability_v02/pipeline_audit.json`; `python -m preslide.stability_verify` writes `reports/stability_v02/verification.json`.

The five spatially distributed initial cases yielded three complete groups; expanding the pilot to 20 candidates yielded nine complete groups and the first Logistic Regression comparison. Only then was the full 102-candidate pipeline run. Small-run scores are explicitly smoke tests, not substantive research results.

`experiment` resumes completed event checkpoints. Raw requests, terrain tiles, local rasters, control pools, matched samples, weather, feature tables, exclusions, splits and models are cached independently. If a source snapshot changes, checksum checks fail rather than mixing inputs. The latest processed pointer is local `data/processed/latest.json`. Baseline consumers (`verify_state.py`, `results_bundle`, `demo`, tests) are now pinned to the frozen identity via `preslide.baseline.pointer()` and no longer follow that pointer.

To obtain your own public-source snapshot when none exists:

```text
python -m preslide download
python scripts/inspect_alternatives.py
python -m preslide audit
```

The three GeoSphere layers and WLV audit alternative are retrieved read-only. A changed live source may no longer yield exactly 102 candidates; the experiment deliberately stops for a new audit instead of silently substituting a different cohort. Availability of the INCA v1 endpoint after its announced December 2026 retirement is not guaranteed. Existing cached responses remain usable.

## Scientific design

- 6,000 local candidates per event; five controls selected with fixed slope, aspect, elevation and separation rules.
- Pre-event DEM availability checked per source tile. Metric CRS and circular aspect calculations tested.
- Real hourly INCA precipitation and temperature. Same event date for all six samples; no event-day weather. Conservative timestamp envelopes retain 1,438 hours in the nominal 60-day window.
- Strict complete-case groups. Excluded: 13 insufficient matches, 17 missing weather, 9 negative precipitation, 3 low-slope positives. No silent clipping or imputation.
- Positive/control groups plus practical storm/spatial dependence clusters remain intact across partitions.
- Logistic Regression, Random Forest and histogram gradient boosting; static, temporal and combined features. Fixed hyperparameters and threshold, no test-set tuning.
- Aggregate metrics, within-group rankings, test bootstrap intervals, validation permutation importance and a purged Steiermark holdout.

## Source attribution and publication boundary

**© GeoSphere Austria.** The detailed event source is labelled **Naturgefahren Test**. Its specific reuse license was not identified during the audit. QUAL_LAGE is treated as a source-reported positional category, not verified survey accuracy. Quality and event-timing interpretations are not officially confirmed.

On 2026-10-14 the user accepted the audit and authorized local non-commercial scientific/competition prototype development with the 102 candidates. GeoSphere clarification is optional and is not a development prerequisite. This does not create a provider license. The draft clarification request remains unsent.

`data/`, `models/`, `.venv/`, `node_modules/` and built frontend assets are ignored. **Do not include raw source snapshots, full normalized record tables or model artifacts in public/competition archives.** Use the allowlisted `python scripts/package_deliverable.py` exporter for a code/documentation/aggregate-results package. It intentionally excludes all raw and record-level data and the local demo bundle. Reproduction on another computer needs independently obtained source snapshots.

Event and weather sources have separate license statuses. INCA is CC BY 4.0; this does not license the Test event inventory. Terrain attribution: Mapzen, © offene Daten Österreichs – DGM Österreich, EU-DEM/Copernicus and USGS. See [DATA_SOURCES.md](DATA_SOURCES.md).

## Project map

**Start every session by reading [PROJEKTUEBERBLICK.md](PROJEKTUEBERBLICK.md), then [PROJECT_STATE.md](PROJECT_STATE.md).** The German overview explains the research goal, completed experiments, scientific limits and next priority. This reading order is mandatory in `AGENTS.md`.

- `preslide/`: audit, terrain, matching, weather, features, evaluation, limited demo API.
- `config/`: frozen audit and experiment settings.
- `tests/`: scientifically dangerous invariants and API exposure checks. Unit fixtures are synthetic and never enter research artifacts; API integration tests require the real local demo bundle.
- `reports/experiment/`: aggregate metrics and scientific figures only.
- `reports/stability_v02/`, `reports/null_v03/`, `reports/verification/`: development stability analysis, null reference, independent re-verification.
- `reports/current_state_audit.md`: verified current state of every pipeline stage.
- `PROJECT_STATE.md`: current verified milestone.
- `METHODOLOGY.md`, `RESULTS.md`, `LIMITATIONS.md`: experiment design, outcomes and boundaries.

The German demo has three direct, browser-history-safe routes: `/#/projekt`, `/#/vorgehen`, and `/#/ergebnisse`. Scientific examples and historical analyses remain accessible in expandable panels. The overview reads existing aggregate API bundles; it does not trigger modelling.

Frontend development: start the API, then `npm run dev` in `frontend`. Vite proxies `/api` to loopback port 8000. Production preview: build frontend, then restart the local API so it mounts `frontend/dist`.

## V0.4 (pre-registered extension, separate outputs)

```powershell
.\.venv\Scripts\python scripts\archive_baseline.py --verify      # baseline archive intact
.\.venv\Scripts\python -m preslide.v04.audit                      # candidates, exclusions, episodes
.\.venv\Scripts\python -m preslide.v04.pipeline match --limit 0   # then static, context, weather --resource inca|spartacus-v2-1d-1km|snowgrid_cl-v2-1d-1km, assemble
.\.venv\Scripts\python -m preslide.v04.partition                  # dependence check + frozen partition
.\.venv\Scripts\python -m preslide.v04.experiment develop         # development CV (freeze/test are one-time steps, already done)
.\.venv\Scripts\python -m preslide.v04.report                     # reports/v04/summary.md, data/v04/web/results.json
.\.venv\Scripts\python scripts\verify_v04.py                      # PASS/FAIL of the completed run
```

All steps reuse verified checkpoints and cached API responses (`data/v04/cache/`). `--limit 1|5|20` runs pilots. The sealed test has been scored; `experiment test` refuses to run again. See `METHODOLOGY.md` (V0.4), `RESULTS.md`, `LIMITATIONS.md`, `reports/v04/`.

## V0.5 (exploratory neighbour-slope ranking, separate outputs)

```powershell
.\.venv\Scripts\python -m preslide.v05.pipeline pools                 # audit of the V0.4 control pools
.\.venv\Scripts\python -m preslide.v05.pipeline select --limit 0      # frozen 10 unmatched controls per event
.\.venv\Scripts\python -m preslide.v05.partition proximity            # proximity audit + CV feasibility
.\.venv\Scripts\python -m preslide.v05.pipeline static --limit 0      # then context, weather --resource inca|spartacus-v2-1d-1km|snowgrid_cl-v2-1d-1km, assemble --limit 0
.\.venv\Scripts\python -m preslide.v05.partition freeze               # cohort + CV/purge plan (write-once)
.\.venv\Scripts\python -m preslide.v05.experiment main                # registered analysis
.\.venv\Scripts\python -m preslide.v05.report                         # reports/v05/summary.md
.\.venv\Scripts\python -m preslide.v05.web                            # bundle for web section 08 (/api/results_v05)
.\.venv\Scripts\python scripts\verify_v05.py                          # PASS/FAIL
```

`--limit 1|5|20` runs pilots. V0.5 has no sealed test (all events seen in V0.4). See `METHODOLOGY.md` (V0.5), `reports/v05/`.
