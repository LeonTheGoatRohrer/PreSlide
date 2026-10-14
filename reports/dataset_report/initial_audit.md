# PreSlide — Austrian Landslide Data Audit

Generated: 2026-10-14T10:09:07.720439+00:00

## Decision

**Audit accepted; local non-commercial research authorized by the user.** The detailed source is labelled `Naturgefahren Test`; its specific reuse license remains unidentified. Provider clarification is not a prerequisite. Do not redistribute raw data. This report covers the audit stage; current experiment results are separate.

## Verified source counts

| Source | Records | Finding |
|---|---:|---|
| GeoSphere standard mass-movement service | 9441 | All positions declared 50–2000 m; none demonstrated ≤250 m |
| GeoSphere INSPIRE Media | 8640 | CC BY 4.0; individual accuracy not exposed |
| GeoSphere Naturgefahren (Test) | 25609 | Individual 0–5 / 5–20 / 20–100 / 100–1000 / >1000 m classes |
| WLV, Rutschung category | 1742 | 166 dated 2018+; accuracy and date precision absent |

## Standard service: process and period audit

Gleit-/Fliessprozess records (all years): 5912.
2018+ with valid structured day: 1575; 2015+: 2336.
Both periods yield zero records with a demonstrated positional upper bound ≤250 m. The lower bound 50 m is not an individual accuracy estimate.

## Detailed source: sequential quality filter

| Step | 2018+ | 2015+ sensitivity |
|---|---:|---:|
| accepted_process | 11247 | 11247 |
| in_period | 1533 | 2120 |
| single_reported_day | 637 | 700 |
| coordinates_plausible | 637 | 700 |
| position_quality | 360 | 380 |
| process_confidence | 95 | 108 |
| certain_mass_movement | 89 | 102 |
| Exact coordinate/date deduplicated candidates | 89 | 102 |

Selected start: 2015-01-01; expanded: True. Candidate date range: ['2017-08-05', '2026-07-01'].

The 100 m threshold is chosen at an actual category boundary. A 250 m threshold cannot distinguish the 100–1000 m class and therefore admits no additional confirmed records. These are source-reported bounds, not independently surveyed error estimates.

Structured dates are checked against the narrative. For example, `12. oder 13. Juni 2018` is excluded even when the structured field says `2018-06-13`. Unparsed narratives remain excluded. Single-day reporting does not guarantee independently verified timing.

Candidates occupy 45 distinct dates; largest same-date clusters: [('2017-08-05', 13), ('2018-06-04', 8), ('2022-08-19', 6), ('2023-08-05', 6), ('2024-06-08', 5)]. These are not independent storms. Future evaluation must group storm/spatial clusters as well as each positive/control group.

## Candidate distributions (before terrain/weather validation)

### By year

| Category | Count |
|---|---:|
| 2017 | 13 |
| 2018 | 9 |
| 2019 | 1 |
| 2022 | 8 |
| 2023 | 37 |
| 2024 | 26 |
| 2025 | 4 |
| 2026 | 4 |

### By state

| Category | Count |
|---|---:|
| Burgenland | 3 |
| Kaernten | 12 |
| Niederoesterreich | 7 |
| Oberoesterreich | 4 |
| Salzburg | 8 |
| Steiermark | 48 |
| Tirol | 12 |
| Vorarlberg | 7 |
| Wien | 1 |

### By process

| Category | Count |
|---|---:|
| Hangmure | 34 |
| Hangmure bis Lockergesteinsrutschung | 9 |
| Lockergesteinsrutschung | 59 |

### By positional upper bound (m)

| Category | Count |
|---|---:|
| 100 | 35 |
| 20 | 40 |
| 5 | 27 |

## Position uncertainty across all records

Cumulative counts with a demonstrated source-reported upper bound. An interval crossing a threshold is not counted as passing it.

| Maximum upper bound (m) | Standard service | Detailed service |
|---|---:|---:|
| ≤25 | 0 | 12589 |
| ≤50 | 0 | 12589 |
| ≤100 | 0 | 16468 |
| ≤250 | 0 | 16468 |
| ≤500 | 0 | 16468 |

Detailed original categories:

| Reported class | Count |
|---|---:|
| Lage genau (5-20m) | 4330 |
| Lage relativ genau (20-100m) | 3879 |
| Lage sehr genau / sehr sicher (0-5m) | 8259 |
| Lage sehr ungenau (>1000m) | 2766 |
| Lage ungenau (100-1000m) | 6373 |
| unknown | 2 |

## Reproducibility and limits

Run `python -m preslide audit`. Raw responses, retrieval timestamps, URLs and SHA-256 hashes are cached under `data/raw/http/`. Configuration is `config/audit.json`; all record-level exclusion reasons are in `data/interim/event_exclusion_decisions.json`. Counts above are computed from downloaded records.

The sources overlap and must not be summed. Candidate locations pass an Austrian bounding-box plausibility check; precise country-boundary and slope verification remain outstanding. Exact duplicates are removed; spatial/storm clustering remains to be done before evaluation.

No individual accuracy is invented for INSPIRE or WLV. No ISO timestamp is automatically treated as evidence of exact timing. Unknown quality is separate from confirmed poor quality. Meteorological completeness is not yet evaluated.

The audit snapshot retains historical UNKNOWN/training_approved=false flags. The separately authorized experiment validates terrain, matching and weather before assigning research labels. See PROJECT_STATE.md and RESULTS.md for current implementation and scores.

## Required next step

Continue the authorized scientific experiment: verify a small real-data run, then scale with leakage-safe evaluation. Optional clarification remains documented but is not a gate. No raw competition redistribution is authorized.

Source endpoints and licensing evidence: see DATA_SOURCES.md.
