# Methodology

## Question and scope

Can pre-event environmental measurements distinguish a documented Austrian landslide slope from five nearby, topographically similar slopes without a documented landslide? This is a retrospective matched case-control experiment, not a nationwide susceptibility model, hazard probability or operational warning system.

## Event selection and authorization

Audit config is frozen at 2026-10-14. Primary start 2018 produced 89 candidates; fallback search start 2015 produced 102, actually dated 2017-08-05 through 2026-07-01. Relevant slide/slope-flow process subtypes, mass-movement and process-quality fields, valid structured dates and conservative single-day narratives are required. Position categories must have a source-reported upper bound <=100 m. Exact location/date duplicates are removed. These are unconfirmed source semantics, not independently surveyed accuracy or timing.

The user accepted this audit and authorized local non-commercial research on 2026-10-14. GeoSphere Austria is attributed. The detailed source is labelled Naturgefahren Test and its specific reuse license was not identified. No GeoSphere confirmation is claimed. Raw data are excluded from public repository, API and competition artifacts. Historical pending flags/file names in the frozen audit snapshot do not constitute a current development gate. The experiment assigns POSITIVE labels only after technical validation; all controls remain PSEUDO_NEGATIVE.

## Terrain

Pre-event Mapzen Skadi composite objects are checked individually against event date using their HTTP Last-Modified timestamp. This is an availability check, not a precise survey date. Original WGS84, EGM96 heights and -32768 nodata are verified. Raster windows around each event are transformed bilinearly to a 30 m EPSG:31287 metric grid. Finite elevation, slope and downslope aspect are sampled at each point; slope must be >=5 degrees. Static predictors are elevation, slope, sine and cosine of aspect. A 30 m pixel is not guaranteed to resolve an uncertain event coordinate. Geology and land-cover matching are not included.

## Matched controls

For each event, generate 6,000 deterministic uniform-area candidates in an annulus 750 m to 10 km from the positive (seed derived from event ID and seed 42). Both positives and candidates must lie in the GISCO Austria polygon. Candidates must avoid known slide/flow/unclear-process points in the entire local source snapshot by 250 m plus the reported positional upper bound. Unknown/open-ended uncertainty uses a 2,000 m proxy plus 250 m; this is not an asserted upper bound. Rockfall-only records are not treated as target slides. The full inventory snapshot, including later recorded events, is used solely for conservative control selection, not as predictors; this retrospective selection is not reproducible as a real-time decision.

Frozen calipers: slope difference <=5 degrees, elevation difference <=150 m, circular aspect difference <=45 degrees; candidate slope >=5 degrees. Rank by sum of squared normalized differences plus 0.15*(distance/10000)^2. Greedily select five with >=400 m mutual separation. If fewer than five pass, exclude the entire event without relaxing calipers. All candidates and their matching diagnostics are cached locally. Controls inherit exactly the associated event date. No inventory record does not establish stability.

## Weather and feature windows

INCA historical hourly v1 provides RR and T2M at approximately 1 km. Requested coordinates map to the nearest returned grid cell with offset <=800 m; the actual grid coordinates are preserved. Duplicate cells and within-group identical weather are measured.

Convert the reported date's midnight in Europe/Vienna to UTC. Nominal lookbacks are 1, 3, 7, 14, 30 and 60 elapsed days (each 24h), avoiding DST ambiguity. Because exact accumulation timestamp alignment is not asserted, require the envelope [timestamp-1h,timestamp+1h] to be wholly inside the lookback and strictly before the event-day cutoff. Retained lengths are 22, 70, 166, 334, 718 and 1438 hours. Feature names ending in `Xd` refer to these guarded, shortened windows; they are not complete X-day rainfall totals.

Features per window: retained-hour precipitation sum, maximum hourly precipitation and mean temperature (18 predictors). All expected retained timestamps and values must exist for every sample. Negative RR, RR above 500 mm/h or temperature outside -60..60 C fail quality checks. No interpolation, silent clipping or post-event fill. One failed sample excludes its whole event group. Raw values and exclusion reasons remain available locally.

Hourly analysis is a retrospective product. Its historical calibration/product version cannot be proved operationally available at t0. The experiment tests retrospective pre-event observational signal, not historical real-time deployability.

## Leakage safeguards and evaluation

Only the 4 static and/or 18 temporal columns are eligible predictors. Labels, source fields, dates, coordinates, group IDs, matching scores/differences, distance to the positive and weather-cell IDs are excluded. Standardization is fitted to the training partition only. No imputation is needed.

All positive/control samples stay together. Dependence clusters are transitive unions of events within 3 days anywhere in Austria, positive sites within 2 km regardless of date, and any sample patches within 400 m. These are conservative practical guards, not proven storm identities. Split clusters once with seed 42: 20% test; 25% of remaining clusters validation; remainder train. Because clusters vary in size, sample fractions differ. No tuning or model selection against test outcomes. Hyperparameters are fixed in code, decision threshold 0.5; every planned model/feature combination is reported.

Models: standardized balanced Logistic Regression, balanced Random Forest (200 trees, minimum leaf 3), balanced histogram gradient boosting (150 iterations, 7 leaves, minimum leaf 10, L2=1). Compare static, temporal and combined features. Models fit only the training partition. Validation permutation importance is descriptive and can be unreliable with correlated features and small validation sets.

Report ROC AUC, Average Precision, precision, recall, F1, balanced accuracy, confusion matrix and Brier score. Constant class prevalence gives ROC AUC 0.5 and AP 1/6. Balanced training outputs are case-control scores, not population landslide probabilities. Also report within-event pairwise AUC and fractional top-one rank (ties receive fractional credit), because between-event weather variation can inflate pooled metrics while failing to distinguish local slopes.

Test intervals use 500 cluster bootstrap draws with the fitted model fixed; they describe sampling instability and do not include model-training uncertainty. Few test clusters produce unreliable intervals. No strong predictive claim follows from a favorable single split.

Additional geographic holdout selects the state with the largest event count before inspecting scores. Train on other states after purging shared dependence clusters and any training event with a sample within 20 km of a test sample. Require >=10 train and >=10 test events. Otherwise explicitly report insufficient data. The geographic experiment is supplementary and not a promise of national generalization.

## Reproducibility

Local raw request caches carry exact URL, retrieval UTC and SHA-256. Processed run identity includes configuration, the frozen 102-candidate snapshot and pipeline version. Source snapshot hashes are checked, completed event artifacts have checksums, terrain caches verify checksums and pre-event provenance. Intermediate terrain, pools, sample groups, weather histories, features, exclusions, splits and models persist independently. A failed event does not require repeating successful downloads. See README for commands and RESULTS for executed outcomes.

## V0.4 — pre-registered extension (separate version; V0–V0.3 unchanged)

Registered in `config/v04.json` before any V0.4 control, weather, land-cover, geology or model result existed. SHA-256 of the configuration and the rule code is in `reports/v04/PREREGISTRATION.json`; `preslide.v04.paths.config()` refuses to run if the configuration changes afterwards. All outputs go to `data/v04/`, `models/v04/` and `reports/v04/`; a write guard refuses any path that belongs to the frozen baseline.

**Events.** Same source snapshot, processes, process quality, mass-movement certainty and position class (≤ 100 m) as V0; period 2011-01-01 onwards; no cap per episode. Date rules (`preslide/v04/dates.py`, 32 tests):

- *Day known* (tier A, the only tier in the main analysis): the narrative names exactly one calendar day, equal to the structured day; the provider's structured interval (`Date_Anfan`–`Date_End_a`) lies inside that local day; no uncertainty wording (`oder`, `ev.`, `wahrsch.`, `?`, other days, …).
- *Time lower bound*, separate from the day: daypart starts (Vormittag 06, Mittag 11, Nachmittag 12, Abend 17) or stated event clock times minus 1 h. Upper bounds (`vor 18:26`, `spätestens`) and times of alarms, posts or rain never move t0. t0 is never later than the provider's structured start. Without a bound, t0 = local midnight.
- Two-day windows (tier B), structured-only days (tier C) and media records without quality fields (tier 2) are counted and excluded from the main analysis.

**Units and partition.** Temporal episodes link event days ≤ 3 days apart anywhere in Austria. Spatio-temporal units split an episode at 50 km, but are accepted only if the 90th percentile of the 6-hourly INCA rain correlation between units of the same episode is < 0.5 (weather inputs only). Location links (positives < 2 km, samples < 400 m) are always added. Blocks containing any of the 102 V0.3 candidates are development; all other blocks form the sealed external test (a 1/3 hash rule would have left ≈ 6 test events). Test groups closer than 1 km to development samples are moved to development. The partition is written once, before any model.

**Controls.** V0 matching unchanged (6 000 candidates, 750 m–10 km, calipers 5°/150 m/45° circular, 400 m separation, inventory exclusion buffers, Austria polygon). For the 60 baseline groups, V0.4 reproduces the stored controls exactly. Controls inherit t0.

**Features.** Static: 30 m Skadi elevation, slope, aspect sin/cos; Zevenbergen–Thorne profile/plan curvature, terrain ruggedness, TPI 150/500 m, relative position in 500 m; D8 catchment and TWI after Planchon–Darboux filling on a 15.3 km window — a sample whose upslope area reaches the window edge is missing; CORINE class (vintage before t0); 1:500 000 lithology group. Temporal: INCA rain sum, maximum hour and mean temperature for 1/3/7/14/30/60 days before t0; same-day rain (since midnight, maximum hour, last 3 and 6 admissible hours) only when the time of day is known — otherwise missing, not zero; SPARTACUS 90/180 d rain and SNOWGRID snow state/decrease (admitted after the 20-event pilot); WINFORE not admitted.

**Missing values.** No invented values. In the linear models a feature missing for any sample of a group gives that group no within-group contrast for that feature; gradient boosting uses native missing handling.

**Models and evaluation.** Conditional logistic regression for 1:5 strata (own scipy implementation, L2 = 1, primary), logistic regression and histogram gradient boosting with fixed V0 parameters; static, temporal and combined variants; group weights 1/√(groups in unit); preprocessing fit on training rows only. Development: 5 folds × 5 repetitions over independence units, 100 within-group label permutations (conditional logit), leave-one-state-out. Primary endpoint: unit-weighted within-group AUC of the combined conditional logit on the sealed test, compared with the static variant by paired unit bootstrap (2 000 draws). Chance: 0.5 local AUC, 1/6 top-1, 0.408 within-group AP; random-rank null with the same unit weights. The sealed test is scored once after `reports/v04/FREEZE.json` hashes code, configuration, partition, dataset and models; the scoring script refuses a second run.

## Pipeline B — Sentinel-2 before/after change signature (separate system, 2026-10-14)

**Purpose.** Learn the visible change signature of documented events from satellite imagery and search for undocumented candidates to expand the inventory. Pipeline B intentionally uses post-event imagery; it is an event-detection and label-QA system, not a precursor model. It never feeds Pipeline A: it reads the V0.4 positives and controls read-only and writes only `data/satellite/`, `models/satellite/`, `reports/satellite/` (write guard and import test in `tests/test_satellite.py`).

**Source.** Sentinel-2 L2A surface reflectance COGs on AWS via the Earth Search STAC API (`sentinel-2-c1-l2a` preferred, `sentinel-2-l2a` as fallback); only spatial windows are read (2.56 km × 2.56 km per sample). Reflectance offsets differ between the two collections and are applied per collection after empirical verification, with a runtime plausibility check (`DATA_SOURCES.md`).

**Acquisition selection (no "noon" assumption).** All overpasses from 180 days before to 120 days after the event day are listed. Each candidate is screened locally with the scene-classification layer inside the 320 m core and the 960 m analysis window (cloud, shadow, snow, invalid pixels), plus an NDSI snow test on green/SWIR/NIR, because a fully snow-covered pilot scene carried an SCL snow fraction of only 2 %. The event day itself is never used. `before_primary` is the latest usable acquisition before the event, `after_primary` the earliest usable one after it; `before_reference` and `after_confirm` add an earlier and a later clear observation. Both primaries must be usable at the positive *and* at ≥ 4 of its 5 matched controls on the same overpass (sibling tile allowed), so that every member of a group shares season, snow state and illumination. Pairs spanning more than 90 days of the seasonal cycle are excluded (phenology dominates). Every screened candidate and every exclusion reason is stored.

**Patches.** 10 m UTM grid (zone of the event) snapped to the Sentinel-2 pixel lattice, 256 × 256 px; same-zone items map pixel-to-pixel, others are warped (bilinear reflectance, nearest SCL). Bands B02/B03/B04/B08/B11/B12 and SCL are cached as deflated GeoTIFFs with provenance sidecars. A phase-correlation shift estimate on the NIR band is stored per pair as a co-registration indicator.

**Change features.** NDVI, NBR, BSI, NDWI and brightness are differenced (after − before) on valid pixels (cloud, shadow, snow and NDSI-snow masked in either image). Statistics are box-filtered maps: mean, standard deviation and threshold-exceedance fraction in a 120 m and a 320 m window, the mean in a ring to 960 m, and window-minus-ring contrasts. The contrasts remove scene-wide seasonal, atmospheric and illumination change; the same maps score sliding windows in discovery mode. Before-state NDVI/BSI give land-cover context.

**Negatives.** The 5 matched V0.4 controls of each event on the same acquisitions: pseudo-negatives with no documented event, matched terrain and identical temporal change context. They do not deliberately sample forestry, construction or river change; those appear as peaks in the discovery scans and are triaged in the false-positive analysis.

**Evaluation.** GroupKFold over V0.4 independence units (no unit in both training and test). Within-group AUC (fraction of controls scored below the positive; chance 0.5), top-1 rate, ROC AUC, average precision; a within-group label-permutation null; shortcut checks with ring-only and nuisance-only (timing, cloud/snow fraction) feature sets. The retrospective discovery test trains on all other units, scores every position of the held-out event's patch, ranks local maxima and reports hit rank, localisation error and peaks per km². Non-hit peaks become `satellite_detected_candidate` rows with `validation_status = UNVERIFIED`; nothing is promoted automatically.
