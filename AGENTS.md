# AGENTS.md — PreSlide

## Purpose

This repository contains **PreSlide**, a scientific machine-learning research prototype investigating whether pre-event environmental patterns can distinguish slopes that later experience a documented landslide from nearby, topographically similar control slopes.

The current development deadline is extremely short.

Optimize for:

> **the strongest complete, reproducible, scientifically defensible prototype achievable within the available time and compute budget.**

Do not optimize for architectural complexity.

---

# 1. Core Working Principles

When working in this repository:

1. Work autonomously.
2. Prefer implementation over discussion.
3. Verify code by actually running it.
4. Fix failures before moving on.
5. Do not repeatedly reconsider settled project decisions.
6. Do not overengineer.
7. Preserve scientific validity above convenience.
8. Use real data only.
9. Never fabricate results.
10. Keep the project runnable on ordinary laptop hardware.

When a reasonable engineering decision does not materially affect scientific validity, make the decision yourself.

Ask the user only when a genuine blocker requires user input.

---

# 2. Resource and Context Efficiency

Codex/agent usage is limited.

Use reasoning, context, compute, network requests, and user interactions efficiently without reducing correctness.

## Avoid unnecessary work

Do not:

- repeatedly read the entire repository;
- repeatedly analyze already-settled architecture;
- regenerate large files for tiny changes;
- rerun expensive pipelines unnecessarily;
- redownload unchanged datasets;
- produce long progress explanations;
- create speculative infrastructure;
- perform broad refactors without a concrete need.

Prefer targeted file searches and targeted edits.

Read only the files/sections needed for the current task.

---

# 3. Work in Autonomous Batches

Do not stop after every small action.

Prefer:

```text
inspect
→ decide
→ implement
→ run
→ inspect output
→ debug
→ retest
→ checkpoint
→ continue
```

Routine implementation choices do not require user confirmation.

Only interrupt the user when progress genuinely cannot continue safely or correctly.

---

# 4. Fail Fast Before Scaling

Never run a large operation before validating the pipeline on a small sample.

Required pattern:

```text
1 event
→ verify

3–5 events
→ verify end-to-end

small batch
→ verify

full dataset
→ run
```

Examples:

Before downloading weather for 200 events, successfully retrieve and process weather for several real events.

Before generating 1,000 controls, verify matching quality for several positives.

Before nationwide raster processing, test a small geographic window.

Before training every model, successfully train one baseline.

---

# 5. Cache Everything Expensive

Avoid repeated external requests and processing.

Cache where practical:

- raw landslide inventories;
- API responses;
- DEM/raster tiles;
- terrain features;
- weather data;
- control candidates;
- selected controls;
- processed features;
- train/test splits;
- trained models;
- evaluation results.

Before an expensive operation, check whether a valid cached artifact already exists.

Never invalidate caches unnecessarily.

---

# 6. Checkpoint the Pipeline

Persist intermediate results.

Preferred pipeline:

```text
raw events
    ↓
filtered events
    ↓
quality-approved positives
    ↓
terrain-enriched positives
    ↓
control candidates
    ↓
matched controls
    ↓
environmental time series
    ↓
ML feature dataset
    ↓
train/validation/test groups
    ↓
models
    ↓
evaluation
```

A failure late in the pipeline must not require restarting from raw data.

---

# 7. PROJECT_STATE.md

Maintain a concise `PROJECT_STATE.md`.

It exists so future agent sessions do not need to reconstruct the entire project history.

Update it after meaningful milestones, not every tiny change.

It should contain approximately:

```markdown
# Current Stage

# Verified Working

# Dataset Status

# Important Decisions

# Current Results

# Known Problems

# Next 3 Tasks
```

Keep it concise.

Do not use it as a detailed development diary.

Session startup is defined once, in section 43.

Do not redo completed work unless evidence indicates it is incorrect.

---

# 8. Scientific Question

The central research question is:

> Can environmental information from the period preceding a documented landslide distinguish the affected slope from nearby, topographically similar slopes without a documented landslide during the same time period?

Keep implementation decisions aligned with this question.

Do not silently transform the project into generic landslide susceptibility mapping.

Static susceptibility is useful as a baseline, but the main research interest is whether **temporal pre-event information adds predictive signal**.

---

# 9. Current V0 Scope

Unless a task explicitly changes these decisions, treat them as settled.

These are the original V0 targets. Later versions (V0.2–V0.4) deliberately extended them
(more events, wider period, conditional logit, sealed test). The authoritative current scope
and numbers are in `PROJECT_STATE.md` and `METHODOLOGY.md`; where they differ from the
numbers below, those files win. Section 45 governs what may not be changed.

## Geographic scope

Austria.

## Primary event period

Start with:

```text
2018 → latest reliable data
```

If too few high-quality events exist, expand backwards toward approximately 2015.

Document any expansion.

## Target positives

Approximately:

```text
100–200 documented events
```

Quality is more important than reaching a specific number.

## Event types

Use relevant landslide processes such as:

```text
Gleiten
Fließen
Rutschung
```

Do not mix unrelated gravitational processes such as rockfall into the positive class.

## Controls

Approximately:

```text
5 local matched controls per positive event
```

## Historical window

```text
60 days before event
```

with aggregations such as:

```text
1d
3d
7d
14d
30d
60d
```

## V0 ML

Prefer:

```text
Logistic Regression
Random Forest
XGBoost / equivalent gradient boosting
```

Do not introduce deep learning unless later evidence provides a compelling reason.

## V0 satellite usage

Sentinel imagery is **not required for V0 training**.

Do not allow satellite processing to block the first working prototype.

---

# 10. Control / Negative Sampling Is Critical

Negative sampling is one of the central scientific contributions of this project.

Do not use arbitrary random points across Austria as the primary controls.

For each positive event, search locally for slopes resembling the positive slope.

Prefer similarity in:

- slope angle;
- aspect;
- elevation;
- geology where available;
- land cover where available;
- terrain characteristics where practical;
- geographic proximity.

Controls should ideally come from the same:

- mountain;
- valley;
- local terrain system;
- or close surrounding area.

Generate a larger candidate pool and select the best matches.

---

# 11. Controls Are Pseudo-Negatives

Absence from a landslide inventory does not prove that no landslide occurred.

Therefore controls should be interpreted as:

> nearby matched slopes with no documented landslide during the relevant event period.

Do not call them absolutely confirmed stable slopes unless evidence supports that claim.

Internally support concepts such as:

```text
POSITIVE
CONTROL / PSEUDO_NEGATIVE
UNKNOWN
```

Later satellite validation may improve control confidence.

---

# 12. Same-Time Rule

Every control inherits the event date of its corresponding positive event.

If:

```text
positive event t0 = 2022-08-05
```

then its controls must also be evaluated relative to:

```text
t0 = 2022-08-05
```

The historical feature window must cover the same dates.

This is required to control for regional weather and seasonal conditions.

---

# 13. No Future Leakage

This rule is absolute.

When predicting an event at `t0`, features may only use information available before `t0`.

Never use:

- post-event weather;
- post-event terrain modifications;
- post-event satellite information;
- reports generated because the landslide occurred;
- features derived from future observations.

Feature windows should conceptually use:

```text
[t0 - history_window, t0)
```

Add tests protecting this rule.

---

# 14. Group Leakage Prevention

Every positive event and its controls form one event group.

Example:

```text
EVENT_0042

positive
control_01
control_02
control_03
control_04
control_05
```

The entire group must belong to the same:

```text
train
OR validation
OR test
```

Never split controls from their corresponding positive event across dataset partitions.

Use grouped splitting.

Add tests for this.

---

# 15. Spatial Leakage

Nearby events may also be strongly correlated.

When evaluating model performance, consider geographic dependence.

If data quantity permits, perform a harder geographic holdout evaluation where an entire region is excluded from training.

Do not claim geographic generalization based only on a random sample split.

---

# 16. Static vs Temporal Signal

Whenever practical, compare at least:

### Static model

Terrain/geology/land-cover features only.

### Temporal model

Temporal environmental features.

### Combined model

Static + temporal.

The important scientific question is whether temporal pre-event information improves performance beyond static susceptibility.

This comparison is more important than maximizing one headline metric.

---

# 17. Data Quality Before Quantity

Never weaken quality criteria merely to reach 200 positives.

Inspect:

- coordinate quality;
- position uncertainty;
- date accuracy;
- process classification;
- missing environmental data;
- source reliability.

If only 80 excellent events exist, prefer them over 200 unreliable events.

Document exclusions.

---

# 18. Position Accuracy

Treat event coordinates as measurements with uncertainty.

Do not assume every point represents the exact landslide location.

Analyze positional accuracy where provided.

Use a configurable quality threshold.

A provisional value around:

```text
250 m
```

may be investigated, but the final threshold should be informed by the real data distribution.

Do not hide unknown positional accuracy.

---

# 19. Terrain and CRS Correctness

Geospatial correctness is critical.

Always verify:

- coordinate reference systems;
- units;
- reprojection;
- raster resolution;
- nodata handling;
- coordinate order;
- distance calculations.

Do not calculate metre distances directly from latitude/longitude using naive Euclidean geometry.

Use an appropriate projected CRS or geodesic calculation.

Add targeted tests.

---

# 20. Aspect Is Circular

Aspect must be treated as circular data.

For example:

```text
359° and 1°
```

differ by:

```text
2°
```

not 358°.

Use circular angular distance when matching controls or engineering aspect-related features.

---

# 21. Avoid Duplicate Controls

Do not select five points that effectively represent the same location.

Controls should have reasonable minimum spatial separation.

Avoid:

- duplicates;
- near-duplicates;
- overlapping patches;
- points inside exclusion buffers around known events.

---

# 22. External Data Sources

Prefer authoritative/open scientific sources.

Priority examples include:

- GeoSphere Austria;
- Austrian government/open-data portals;
- Copernicus;
- ERA5 / ERA5-Land;
- authoritative DEM/geology/land-cover sources.

Verify APIs and schemas instead of assuming them.

Record provenance.

Never fabricate unavailable fields.

---

# 23. Data Provenance

Maintain `DATA_SOURCES.md`.

For every external dataset record:

- provider;
- dataset;
- endpoint/URL;
- retrieval date;
- relevant license information;
- important processing steps;
- known limitations.

Scientific reproducibility matters.

---

# 24. Laptop Constraints

Assume development hardware approximately:

```text
HP laptop
AMD Ryzen 7 5000 Series
integrated AMD Radeon graphics
unknown RAM
```

Therefore:

- CPU-first;
- no CUDA dependency;
- no dedicated GPU assumption;
- avoid loading nationwide rasters fully into RAM;
- process raster windows/tiles;
- use chunking;
- cache aggressively;
- prefer efficient formats.

Do not design V0 around GPU compute.

---

# 25. Efficient File Formats

Prefer:

```text
Parquet
GeoParquet
GeoJSON where interoperability is useful
GeoTIFF / COG for raster data
JSON for metrics/configuration
joblib/native formats for models
```

Avoid repeatedly parsing huge CSV files when better formats are available.

---

# 26. Testing Priority

Tests should focus first on scientifically dangerous failures.

Highest-priority tests:

1. no future-data leakage;
2. event groups remain intact across splits;
3. controls inherit correct event date;
4. exclusion buffers work;
5. CRS/distance calculations are correct;
6. aspect distance is circular;
7. controls are sufficiently separated;
8. terrain extraction returns plausible values;
9. cached data is not silently mismatched to configuration.

A beautiful UI with an invalid dataset is a failed project.

## Test quality rules

- Every new safety test (leakage, grouping, CRS, date, cache) must be shown to **fail on a
  deliberately injected bug** (e.g. move one control to another split, include `t0` in the
  window, swap lat/lon) before it is trusted. A test that cannot fail protects nothing.
- Test the boundaries: window end exactly at `t0`, a group of size 1, aspect 359°/1°,
  antimeridian-free but UTM-zone-edge coordinates, empty/NaN weather, duplicate IDs.
- Synthetic fixtures are allowed in unit tests only; they must be built in the test and never
  written into `data/` or `reports/`.
- Prefer property-style assertions (invariants over whole tables: "no group spans two
  partitions", "all feature timestamps < t0") over spot checks of single rows.
- A bug fix comes with a regression test that fails before and passes after the fix.
- Skipped tests are a warning, not a pass. Report the skip count; never describe a run with
  data-dependent skips as "all tests pass".
- Seeds are fixed and recorded; results that change between two identical runs are a bug.

---

# 27. Evaluation

Do not use raw accuracy as the primary success metric.

Report appropriate metrics such as:

- ROC AUC;
- PR AUC / Average Precision;
- Precision;
- Recall;
- F1;
- balanced accuracy;
- confusion matrix.

Remember the approximate 1:5 class ratio.

Compare against simple baselines.

---

# 28. Interpretability

Where practical, provide:

- tree feature importance;
- permutation importance;
- SHAP if it can be added without destabilizing the project.

Use scientifically careful wording.

Say:

> the model relied strongly on feature X

not:

> feature X causes landslides.

Correlation/predictive importance is not causation.

---

# 29. Do Not Chase Metrics

A high AUC is not the primary objective.

Never:

- leak data;
- cherry-pick splits;
- remove difficult samples solely to improve scores;
- tune against the test set;
- misrepresent controls;
- hide poor experiments.

A scientifically valid AUC of 0.62 is more valuable than an invalid AUC of 0.95.

---

# 30. Frontend Priority

The frontend is important for demonstrating the project, but comes after the scientific pipeline.

Stack:

```text
Vue 3
Vite
MapLibre or comparable open mapping solution
```

Backend:

```text
Python
FastAPI
```

UI language:

```text
German
```

Internal code/identifiers/documentation may primarily use English.

Do not spend significant time polishing the frontend until:

```text
real events
→ real controls
→ real features
→ working model
→ real evaluation
```

exist.

---

# 31. Web Demo Purpose

The web application should make the methodology understandable.

Prioritize visualizing:

- positive events;
- their five controls;
- geographic relationship;
- matching quality;
- event dates;
- relevant terrain properties;
- 60-day environmental history;
- model metrics;
- feature importance;
- static vs temporal comparison.

The map should help explain the experiment rather than merely look impressive.

---

# 32. Satellite Future Work

Sentinel integration is planned but should not block V0.

Future order:

```text
V1 → Sentinel-1
V2 → Sentinel-2
V3 → before/after landslide detector
```

A future landslide detector may be used to validate pseudo-negative controls.

Keep architecture reasonably extensible for this, but do not build unused abstractions now.

---

# 33. Infrastructure Future Work

A future stage may overlay predicted hazard with:

- buildings;
- roads;
- railways;
- critical infrastructure.

This is primarily a GIS problem.

Do not force machine learning into components where deterministic geospatial analysis is more appropriate.

---

# 34. Documentation

Keep documentation centralized.

Preferred files:

```text
README.md
AGENTS.md
PROJECT_STATE.md
DATA_SOURCES.md
METHODOLOGY.md
RESULTS.md
LIMITATIONS.md
```

Do not duplicate long explanations across all files.

---

# 35. Progress Reporting

Keep routine progress reports concise.

Good:

```text
DONE
- GeoSphere endpoint verified
- 137 usable events after filtering
- DEM extraction verified on 5 events

CURRENT
- local control matching

NEXT
- validate 25 controls
- retrieve weather
- build first feature table
```

Avoid long essays about routine implementation.

Spend effort on implementation.

---

# 36. When to Use Deep Reasoning

Reserve expensive/deep reasoning primarily for:

- dataset validity;
- control sampling;
- statistical design;
- temporal leakage;
- spatial leakage;
- geospatial transformations;
- surprising model behavior;
- conflicting data sources;
- difficult bugs;
- major architecture decisions.

Routine implementation should not trigger a complete reconsideration of the project.

---

# 37. Stop Optimizing Finished Components

Once a component is:

```text
working
tested
scientifically defensible
reproducible
```

move on.

Do not endlessly optimize it unless later evidence shows a real problem.

---

# 38. Priority Order

Unless the current task explicitly says otherwise, prioritize:

```text
1. Data availability audit
2. Clean positive events
3. Local matched controls
4. Terrain features
5. Temporal environmental features
6. End-to-end dataset
7. Baseline model
8. Leakage-safe evaluation
9. Better model
10. Scientific analysis
11. API
12. Map/frontend
13. Documentation/polish
14. Optional extensions
```

Never reverse this order merely because frontend work is easier.

---

# 39. Deadline Strategy

The project has only a few days available.

The end-to-end pipeline (5-event pilot → 102 → 423 positives, model, sealed test) already
exists and is verified. The "get one experiment working" phase is **finished**; do not rebuild it.

For any new version or data expansion keep the same discipline:

```text
pilot (1 → 5 → 20 events) → verify → full run
```

Do not discover fundamental pipeline problems only after processing the full dataset.
Unfinished experimental work is not allowed to endanger the frozen results (section 45).

---

# 40. Genuine Blockers

Contact the user when:

- required credentials are unavailable;
- a required source cannot legally/practically be used;
- no scientifically useful event data can be obtained;
- event counts are dramatically below expectations;
- an unavoidable decision fundamentally changes the research question;
- continuing would risk invalidating the project.

Do not contact the user for:

- naming;
- formatting;
- equivalent library choices;
- routine dependency decisions;
- minor UI choices;
- ordinary bugs that can be debugged autonomously.

---

# 41. Never Fake Progress

Never replace missing real functionality with fake/demo data without making it unmistakably explicit.

Do not silently use:

- synthetic events;
- fake coordinates;
- fake API responses;
- invented weather;
- invented model metrics.

If something does not work, report it and find the best legitimate alternative.

---

# 42. Definition of Done for V0

A strong V0 contains:

- real Austrian landslide events;
- documented filtering;
- local matched controls;
- real terrain features;
- real pre-event environmental data;
- reproducible feature engineering;
- no known future leakage;
- group-safe evaluation;
- baseline ML;
- real metrics;
- matching-quality analysis;
- interactive geographic demonstration;
- clear limitations;
- reproducible setup.

Everything beyond this is secondary until these requirements work.

---

# 43. Session Startup Procedure

At the beginning of any substantial agent session:

1. Read `AGENTS.md`.
2. Read `PROJEKTUEBERBLICK.md` completely. This is mandatory at the start of every session, including short sessions.
3. Read `PROJECT_STATE.md` if present.
4. Check repository status/current implementation.
5. Identify the current bottleneck.
6. Inspect only files relevant to that bottleneck.
7. Continue from the existing verified state.

Do not reconstruct the entire project from scratch.

---

# 44. Session Completion Procedure

After substantial work:

1. run relevant tests;
2. verify produced artifacts;
3. update `PROJECT_STATE.md`;
   also update `PROJEKTUEBERBLICK.md` when a milestone changes the overall status, conclusions or remaining work;
4. record important new scientific/engineering decisions;
5. identify remaining blockers;
6. leave the repository in a runnable state whenever possible.

Do not leave undocumented half-migrations or broken intermediate architecture.

---

# 45. Frozen Artifacts and the Sealed Test

These are write-once. Never edit, regenerate, "fix" or re-score them:

- the V0.3 baseline (`reports/baseline/BASELINE_MANIFEST.json` hashes, `archive/v0.3-baseline/`);
- `reports/v04/PREREGISTRATION.json`, `AMENDMENT_*.json`, `FREEZE.json`, the read-only `config/v04.json`;
- the sealed V0.4 test result `reports/v04/test_results.json`. The sealed test has been scored
  once; it is now **seen data**. Never tune, select features, filter events or choose models
  with it. Any later analysis on those events is exploratory and must be labelled so.

New work goes into a **new version namespace** (own `data/`, `models/`, `reports/` subfolder
and config), registered *before* modelling. Changes to a registered design are amendments
made before any model sees the data, written down with the reason, never silent edits.

Do not "improve" a number by re-running with a new split, new seed or new filter after seeing
results. If a result looks wrong, find the bug and document it; do not shop for a better run.

# 46. Verification Commands (run before claiming "done")

```text
.\.venv\Scripts\python -m pytest -q                  # all Python tests; read the skip/error counts
cd frontend; npm test; npm run build                 # UI wording tests + production build
.\.venv\Scripts\python scripts/verify_state.py       # baseline invariants
.\.venv\Scripts\python scripts/verify_v04.py         # V0.4 invariants
.\.venv\Scripts\python scripts/archive_baseline.py --verify
```

- Only run what the change touches, but any change in `preslide/` that affects data, features,
  splits or metrics requires pytest plus the matching verify script.
- `data/`, `models/` and `.venv/` are gitignored and exist only in the main checkout. In a git
  worktree they are missing: data-dependent tests then error or skip and the verify scripts
  cannot run. Use the main checkout's `.venv` for a quick run, but do not report
  data-dependent checks as passed from a worktree; say they were not run, or run them in the
  main checkout.
- Report failures with the actual output. Do not mark a check as passing from memory of an
  earlier run.
- Windows/PowerShell is the primary shell: use `.venv\Scripts\python`, forward-slash-safe
  paths, no bash-only syntax in committed scripts.

# 47. Code Quality Bar

- Reuse before writing: search `preslide/` (`common.py`, `preslide/v04/*`) for an existing
  helper (distance, CRS transform, circular distance, checkpoint IO, hashing) before adding a
  new one. One implementation of each scientific primitive; tests cover that one.
- Checkpoint IO goes through the existing hashed-sidecar helpers. Do not write ad-hoc
  `to_parquet` / `json.dump` into cached pipeline directories.
- Fail loudly on scientific preconditions (missing weather, NaN in a required feature,
  unexpected CRS, empty control pool). Never silently fill, clip or drop; if rows are dropped,
  count them by reason and write the counts to the report (see `admission.json`).
- Type-hint public functions that handle time windows, CRS or splits; name units in
  identifiers (`distance_m`, `window_days`, `t0_utc`). Use timezone-aware timestamps and say
  which timezone.
- Configuration lives in `config/*.json`; no magic numbers for thresholds, buffers, windows or
  seeds inside code. A config change must change the cache/run identity hash.
- No new dependency without need; if added, update `requirements-lock.txt` and say why.
- Keep functions small and pure where possible (pure function + thin IO wrapper) so that
  leakage and grouping logic is unit-testable without data.
- Do not leave dead code, commented-out experiments or one-off probe scripts in `preslide/`
  (put throwaway probes in `scripts/`, clearly named, or in the scratchpad).

# 48. Statistical Claims

- Effective sample size is the number of **independent units** (temporal episodes / blocks),
  not the number of rows or events. Always state it next to any metric.
- Every headline metric comes with an uncertainty interval from a resampling scheme that
  respects those units, plus the null reference (permutation or equivalent) when one exists.
- A difference between models (e.g. combined vs. static) is a *paired* quantity with its own
  interval. "Better" is only claimed if that interval excludes zero; otherwise write
  "no established benefit".
- Count every comparison that was looked at; do not report only the best one. Exploratory
  results are labelled exploratory.
- Watch for single-cluster dominance (one storm, one region) and report results with that
  cluster removed when it holds a large share of events.
- Inventory data carries reporting and placement bias (roads, settlements, forests). Before
  interpreting a predictor as environmental signal, state whether it may be a reporting
  artefact.

# 49. Git Workflow

- Commit each verified milestone with a clear message; push as the user's standing rule says
  (commit and push every milestone). Do not commit generated data, models, record-level
  tables or secrets (see `.gitignore`); never use `--no-verify`.
- Do not rewrite or force-push history that contains frozen artifacts.
- Never commit in a state where tests that passed before now fail without saying so.

---

# 50. Final Decision Rule

When choosing between:

> sophisticated but unfinished

and

> simpler but complete and scientifically valid

choose the second.

When choosing between:

> impressive metric obtained through questionable methodology

and

> weaker metric obtained through defensible methodology

choose the second.

When choosing between:

> more agent work

and

> reusing a verified existing result

reuse the verified result.

The goal is not to maximize code volume, model complexity, agent activity, or benchmark scores.

The goal is to produce a **credible scientific machine-learning prototype that actually works**.
