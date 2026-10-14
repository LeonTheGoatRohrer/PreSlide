# Feature data-availability audit (candidate features after V0.3)

Run date: 2026-10-14. Script: `scripts/feature_audit_v04.py --data-root <checkout with data/>`. Per-sample values and the
HTTP response cache are local only, in `data/feature_audit_v04/`. This directory holds one aggregate CSV per source (plus a local-only `_meta.json`),
`all_sources.csv` and `run_status.json`.

**Scope and safeguards.**
- **No model training or evaluation.** No original-test or Steiermark result was opened.
- **No label-dependent statistic was computed.** Every number below treats the six slopes of a group symmetrically: within-group spread versus spread of group means. Positive and controls are never compared. The shortlist is therefore not selected on outcome.
- **The frozen baseline was only read** (`data/processed/046074ba6f12556c/`). Nothing was written under baseline or V0.4 paths.
- **Download budget.** Every raster was read in windows via HTTP range requests, with 10–50 MB per source and an 11 MB windowed read of the 8.5 GB SoilGrids-2017 file. Nothing above 1 GB was downloaded.

**Events.** There are 5 development groups (train/validation, never test), each with 1 positive and 5 controls, so 30 slopes. They were chosen deterministically by SHA-256 of `event_group_id`, with distinct dependence clusters and dates:

| group | event month | state | split |
|---|---|---|---|
| G1 | 2022-12 | Tirol | train |
| G2 | 2023-05 | Steiermark | validation |
| G3 | 2023-08 | Kärnten | train |
| G4 | 2024-01 | Tirol | train |
| G5 | 2022-08 | Vorarlberg | validation |

Event IDs, exact dates and query metadata (`selected_events.csv`, `*_meta.json`) stay local and are git-ignored, like the other record-level baseline tables.

The INCA-derived features (C) need no network, so they were also computed for all 45 development groups (`inca_derived_dev45.csv`).

**Statistic.**
- `within_group_std` is the pooled standard deviation of the six slopes around their group mean.
- `between_group_std` is the standard deviation of the group means.
- `within_share` = within² / (within² + between²).

Only the within-group part can help the matched same-t0 design. With 5 groups, the between-group figure is very noisy, so the ratios are descriptive orientation, not estimates. For categorical maps the integer code is arbitrary; use `mean_distinct_values_per_group` and `groups_all_identical` instead.

## Result per source

| Source | Accessible | Resolution / CRS | Licence | Temporal validity vs t0 | Within-group contrast (5 groups) |
|---|---|---|---|---|---|
| **Terrain from cached 30 m Skadi composite**: curvature, TPI, TWI, catchment, distance to stream | yes, cached tiles | 1″ HGT resampled to 30 m, EPSG:31287, nodata −32768. DEM check vs. stored elevation: max 0.76 m | composite (Austrian DGM CC BY 3.0 AT, EU-DEM, USGS) | tile Last-Modified 2016 < every t0 | **high**: within_share 0.77–0.93 for curvature, TPI150, TWI, log catchment, stream distance. Roughness only 0.04, because it follows the matched slope |
| **DGM Österreich 10 m** (`ogd-10m-at.zip`) | **not downloaded** | one deflate-compressed GeoTIFF (`dhm_at_lamb_10m_2018.tif`, 1.96 GB) in a 1.94 GB zip; no range/window access is possible | OGD CC BY 4.0 | object Last-Modified 2019-06-18. Pre-event only for t0 > 2019-06-18 (48/60 baseline events); no per-cell acquisition date | not measured. **Needs user confirmation (> 1 GB)** |
| **GeoSphere geology 1:200 000 / 1:100 000 (Vbg)** | yes, ArcGIS REST point query | vector; Stmk, OÖ, Sbg, NÖ (1:200k) and Vbg (1:100k). **No Tirol/Kärnten** | CC BY 4.0 ©GeoSphere (iteminfo) | static map | 2 of 5 groups covered (18/30 missing); 3–4 distinct units per covered group. **One sample falls on a mapped mass-movement unit** ("Bergsturzmasse … in Massenbewegung mit Abrisskante"): target-proxy risk |
| **GeoSphere geology 1:500 000** (already in V0.4) | yes | vector, all Austria | CC BY 4.0 | static | 2–4 distinct units per group; no group uniform |
| **SoilGrids 2.0 clay/sand** (0–5, 15–30, 30–60 cm) | yes, ISRIC REST point API (~5 req/min). GDAL `/vsicurl` fails the local TLS chain, so the script uses Python range reads | 250 m, Homolosine (ESRI:54052); mapped g/kg × 10 → % | CC BY 4.0 ISRIC | static model output | **low**: within_share 0.08–0.23 (within std ≈ 1.4–2.9 %-points) |
| **SoilGrids 2017 depth to bedrock (BDTICM)** | yes, windowed range read of an 8.5 GB file (11 MB fetched) | 250 m (0.00208°), EPSG:4326, nodata −32768, int32 cm, row-strip layout | CC BY 4.0 ISRIC | static (2017) | within std 240 cm vs. between 155 cm (share 0.70). Known weak skill in the Alps; 250 m model noise may explain much of this |
| **ESA WorldCover 10 m** v100 2020 / v200 2021 | yes, public COG on AWS, windowed reads (10 MB) | 0.0000833° (~10 m), EPSG:4326, nodata 0 | CC BY 4.0 ESA | **map year must be < event year**. 2021 map is pre-event for 47/60 baseline events; earlier events could show their own scar | **high**: 2–3 classes per group (trees 17, grassland 9, built-up 4 of 30). Tree share in a 50 m patch has within_share 0.62–0.73. 2020/2021 classes agree for 93 %; part of the change is the algorithm change |
| **Copernicus HRL Tree Cover Density 2018** | **no (today)**: EEA ImageServer `getSamples`/`identify`/`exportImage` all returned "General function failure" | 10 m, EPSG:3857 (service metadata) | Copernicus Land, free with attribution | ref. year 2018 → t0 ≥ 2020 | not measured |
| **Global Forest Change v1.12** (treecover2000, lossyear) | yes, GCS GeoTIFF, windowed reads (50 MB) | 0.00025° (~30 m), EPSG:4326, no nodata tag, row strips | CC BY 4.0 (Hansen/UMD/Google/USGS/NASA) | only loss years **strictly before** the event year. 0 of 30 slopes had loss in or after the event year | treecover2000 within_share 0.68. Loss-before share (150 m patch) 0.60, but zero in most slopes (2 groups all zero) |
| **OSM roads as of t0** | yes, Overpass attic `[date:"t0−1s"]`. Main server returned 504 under load; one group was answered by the kumi.systems mirror, whose attic support was not independently verified | vector → EPSG:31287 | **ODbL 1.0** (share-alike for derived databases) | DB state before t0, so no post-event repair roads; past mapping completeness varies | distance to any way within_share 0.84; distance to road (excluding paths/tracks) 0.49; way density 250 m 0.51 |
| **SPARTACUS v2 daily RR 90/180 d** | yes, GeoSphere Data Hub (240 req/h) | 1 km daily | CC BY 4.0 | day D (07 CET D → 07 CET D+1) treated as valid at D+1 06:00 UTC, used only if < t0. **Last used day = event day − 2; it ends 16–17 h before t0** for all 30 slopes | moderate: within_share 0.12–0.16 (within std 62–82 mm). Driven by orographic gradients across ≤10 km and ≤150 m elevation |
| **SNOWGRID-CL v2** SWE, depth, SWE decrease 3/7/14 d | yes | 1 km daily | CC BY 4.0 | same conservative rule (valid D+1 06:00 UTC) | only winter groups non-zero (3 groups all identical = zero snow). In the January Tirol group SWE ranges 0–212 mm among the six slopes (elevation-driven) |
| **WINFORE v2 SPEI30/90** | yes (V0.4 pilot coverage 86 %, not admitted there) | 1 km daily | CC BY 4.0 | same rule | **≈ none**: within_share 0.003–0.007 |
| **(C) INCA-derived**: API k = 0.9, max 24/72 h rain, frost-thaw days, wet days | yes, cached baseline responses only | 1 km hourly | CC BY 4.0 | identical to the frozen baseline: T ± 1 h inside [t0 − 60 d, t0). Asserted: last hour + 1 h < t0 | **low**: within_share 0.01–0.02 (45 groups) for API and max rain. Frost-thaw days identical across all six slopes in 32–36/45 groups. Wet days 0.09 |

## Interpretation

1. **Only locally varying static information gives real within-group contrast.** These are the slope-form terrain derivatives, land/forest cover, OSM infrastructure and, partly, geology. This matches the expectation from IMPROVEMENT_PLAN §1. Caveat: the high within-group variance of 30 m curvature/TPI is partly *noise*. Source positions carry up to 100 m uncertainty, and 23/45 development events change slope by > 5° under position offsets. A position-robust form should be pre-registered, e.g. a focal mean over a 50–100 m radius instead of the single cell.
2. **Coarse temporal products (1 km) barely vary inside a group.** SPEI ≈ 0, INCA API/max-rain ≈ 1–2 %, SPARTACUS ≈ 12–16 %. Their within-group differences are mostly elevation and orography, i.e. partly redundant with the matched static terrain. As argued by the parent plan, they belong mainly in a **case-crossover design** (same slope, other dates). There the full between-date variance becomes usable.
3. **Leakage-sensitive products need a vintage rule, not just availability.** This applies to WorldCover (scar visible on post-event maps), HRL TCD, the DGM 10 m and GFC loss in the event year. Mapped mass-movement units in the 1:100k/1:200k geology are a target proxy and must be excluded or kept as a separately reported flag.
4. **SoilGrids texture is mainly a between-group signal.** It adds little within groups at 250 m.

## Relation to `config/v04.json`

`config/v04.json` is **already pre-registered** (hash in `reports/v04/PREREGISTRATION.json`, guarded by `preslide/v04/paths.config()`). It already contains:
- curvature, TPI, relative position, catchment and TWI (30 m);
- CORINE land cover;
- geology 1:500k;
- SPARTACUS RR 90/180 d and SNOWGRID.

It was **not modified**. Changing it would invalidate the registration. The shortlist below is therefore a proposal for the *next* version (e.g. `config/v05.json`), or for V0.4 only if the user explicitly decides to re-register.

## Proposed pre-registration shortlist (≤ 15, not frozen)

These were chosen without labels, from accessibility, temporal validity and within-group contrast only. ✱ = not in `config/v04.json`.

| # | Feature | Source | Design role | Rule to pre-register |
|---|---|---|---|---|
| 1 | plan curvature, 50 m focal mean | DEM (10 m if confirmed, else 30 m) | spatial | position-robust focal mean ✱(form) |
| 2 | profile curvature, 50 m focal mean | DEM | spatial | as 1 |
| 3 | TPI 150 m | DEM | spatial | — |
| 4 | TWI (D8, truncated catchment → missing) | DEM | spatial | as V0.4 |
| 5 | ✱ distance to stream (upslope area ≥ 0.1 km²) | DEM | spatial | channel threshold fixed in advance |
| 6 | ✱ forest share 150 m = GFC treecover2000 ≥ 30 % minus loss before event year | GFC v1.12 | spatial | loss year < event year only |
| 7 | ✱ forest loss before event year, 150 m share | GFC v1.12 | spatial | same |
| 8 | ✱ WorldCover 2021 tree share 50 m | ESA WorldCover | spatial | **missing unless event year ≥ 2022**; report the missingness pattern |
| 9 | lithology group (5 classes) | GeoSphere 1:500k | spatial | as V0.4; mass-movement units never a class |
| 10 | ✱ sand 15–30 cm | SoilGrids 2.0 | mostly between | — |
| 11 | ✱ depth to bedrock | SoilGrids 2017 | spatial (low reliability) | exploratory, report separately |
| 12 | ✱ distance to road (excluding paths/tracks) | OSM attic at t0 − 1 s | spatial | primary Overpass server only (attic verified) |
| 13 | SPARTACUS RR 90 d | GeoSphere | temporal / case-crossover | last day ≤ event day − 2 |
| 14 | SWE decrease 7 d | SNOWGRID | temporal / case-crossover | same; 0 outside snow season is a real value |
| 15 | ✱ antecedent precipitation index k = 0.9, 60 d | INCA (cached) | temporal / case-crossover | baseline hour admissibility |

Not recommended:
- SPEI30/90: no within-group contrast and 86 % coverage.
- Clay: redundant with sand.
- TRI roughness: tracks the matched slope.
- WorldCover classes as one-hot: categorical, and vintage-limited.
- HRL TCD: service down today.
- Geology 1:200k: no Tirol/Kärnten, and contains mass-movement units.
- Frost-thaw days: identical within 71–80 % of groups; keep for case-crossover only.

## Open decisions for the user

- **DGM 10 m download (1.94 GB)**: approve or not. If approved, the vintage rule t0 > 2019-06-18 excludes 12/60 baseline events and most 2011–2018 V0.4 events. An alternative worth checking first is the BEV ALS DTM tiles with per-flight acquisition dates.
- **OSM is ODbL**: derived feature tables are local only. Publishing them would trigger share-alike obligations.
- **Whether to re-register** a feature set (V0.5) rather than alter the registered V0.4.
