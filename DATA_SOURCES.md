# Data sources

Audit retrieval date: 2026-10-14. Exact UTC times, requests and hashes are in `data/raw/http/*.meta.json`. Access was read-only, using public endpoints without authentication. Dataset access does not itself establish reuse rights.

## GeoSphere Austria — Gravitative Massenbewegungen

- Endpoint: https://gis.geosphere.at/maps/rest/services/naturgefahren/Gravitative_Massenbewegungen/MapServer/0
- Metadata: https://gis.geosphere.at/maps/rest/services/naturgefahren/Gravitative_Massenbewegungen/MapServer/info/iteminfo
- 9,441 downloaded records; exported from original Web Mercator to WGS84 by the service (`outSR=4326`). The actual response CRS is validated.
- Fields include process group, source wording, event date, state and positional accuracy.
- All records use `50-2000m` or its spacing variant, at reference scale 1:100,000. No individual ≤250 m estimate can be inferred.
- Attribution names GeoSphere Austria. This item's license field is empty; the related INSPIRE license must not automatically be extended to other services.

## GeoSphere Austria — INSPIRE NZ ObservedEvent Media

- Endpoint: https://gis.geosphere.at/maps/rest/services/inspire/NZ_ObservedEvent_Media/MapServer/0
- Licensing evidence: https://gis.geosphere.at/maps/rest/services/inspire/NZ_ObservedEvent_Media/MapServer/info/iteminfo
- **Explicit CC BY 4.0**, © GeoSphere Austria.
- 8,640 downloaded records, already in WGS84. Media/literature inventory; incomplete and heterogeneous.
- Does not expose individual position-quality classes. Dataset metadata describes heterogeneous 15–500 m positioning, which cannot identify the accuracy of a particular event.
- Lifecycle timestamps are not event dates. `validFrom` and `validTo` require interval interpretation, not blind conversion to an exact occurrence date.
- Shares event identifiers with other GeoSphere sources. Counts cannot be added; shared IDs do not license additional fields from another service.

## GeoSphere Austria — Naturgefahren (Test)

- Endpoint: https://gis.geosphere.at/maps/rest/services/naturgefahren/Naturgefahren/MapServer/0
- Service metadata: https://gis.geosphere.at/maps/rest/services/naturgefahren/Naturgefahren/MapServer/info/iteminfo
- Portal metadata: https://gis.geosphere.at/portal/sharing/rest/content/items/fe326d3a35f1496282a8793c8189ac3b?f=pjson
- Public portal item owned by GeoSphere_Austria; snippet is **Naturgefahren Test**. `licenseInfo`, description and attribution are empty/null. FeatureServer metadata likewise has no license statement.
- 25,609 downloaded records. Detailed fields: `QUAL_LAGE`, `QUAL_MB`, `QUAL_PROZ`, process group/subgroup, date components, date narrative and state.
- Source-reported accuracy categories: 0–5, 5–20, 20–100, 100–1000, >1000 m. Preserve interval bounds, do not invent point accuracy values.
- **Specific reuse license unidentified; release/quality semantics not officially confirmed.** On 2026-10-14 the user authorized local non-commercial scientific/competition prototype development using these candidates. This is user authorization, not GeoSphere approval or a newly inferred license. Provider clarification is optional, not a prerequisite. Raw data remain local, ignored and excluded from competition/public artifacts.
- This service includes additional administrative/observer fields. They are excluded from normalized candidate exports and are never predictors. Do not infer release permission from undocumented numeric `WEB_ON`/`WEITERGABE` values.
- Processing: conservative process whitelist, full calendar day plus compatible narrative, bounding-box check, upper-bound position filter, process confidence, confirmed mass-movement classification, exact position/day deduplication. Full audit decisions preserved.

## BMLUK / Wildbach- und Lawinenverbauung — WLV Ereignisse

- Collection discovery: https://gis.lfrz.gv.at/api/geodata/i000901/ogc/features/v1/collections?f=application%2Fjson
- Items: https://gis.lfrz.gv.at/api/geodata/i000901/ogc/features/v1/collections/i000901:wlv_ereignisse/items
- OGD catalog listing: https://www.data.gv.at/katalog/en/dataset/?_organization_limit=0&license_id=cc-by-40&organization=bml
- The catalog lists WLV Ereignisse under CC BY 4.0. No individual accuracy or date-precision field appears in the inspected GeoJSON schema.
- Queried `nameofevent LIKE 'Rutschung%'` with cql-text, cached 1,742 records, validated distinct feature IDs and expected record count. WGS84 longitude/latitude order from CRS84 collection metadata.
- 166 calendar-valid dates from 2018 through the configured cutoff. An earlier coarse string comparison counted 167; the final audit uses validated calendar dates and an explicit end date.
- Hazard intensity (`qualitativevalue`) is **not** confidence or positional accuracy. Unknown dates and date precision must not be filled in. A timestamp ending in January 1 is not proof of day-level accuracy.
- This source currently does not remove the scientific position/date-quality blocker.

## Scientific alternatives inspected (metadata/literature only)

- Knevels et al., *Assessing uncertainties in landslide susceptibility predictions in a changing environment (Styrian Basin, Austria)*: https://nhess.copernicus.org/articles/23/205/2023/
  Uses 2009 and 2014 inventories and regional heavy-rainfall episodes. Outside the settled 2015+ fallback; changing to these episodes would require an explicit change of scope and a suitable storm-level evaluation. Not downloaded or used.
- Maraun et al. dataset: https://zenodo.org/records/6036814 — associated climate/land-use experiment archive. Metadata reviewed; not presumed to be an immediately compatible dated event inventory. Not downloaded or used.

## Additional predictors not acquired

Land cover, geology, soil moisture and snow are not included in this V0. Terrain, precipitation and temperature are documented below. No absent field is imputed as a real observation.

## Mapzen / Tilezen Skadi elevation tiles

- Provider/catalog: https://registry.opendata.aws/terrain-tiles/
- Format: https://github.com/tilezen/joerd/blob/master/docs/formats.md
- Attribution: https://github.com/tilezen/joerd/blob/master/docs/attribution.md
- Objects: `https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat}/N{lat}E{lon}.hgt.gz`.
- Retrieved 2026-10-14; exact URLs, HTTP Last-Modified, retrieval UTC and SHA-256 in `data/raw/terrain/*.json`. Every object's Last-Modified must precede its event. Cached checksums are verified. Object timestamps prove product availability before the event, not exact per-pixel survey dates.
- 1 arc-second HGT, WGS84 geographic coordinates, EGM96 vertical datum, -32768 nodata. Composite source, not assumed to be pure SRTM. Local windows are reprojected bilinearly to EPSG:31287 at 30 m; metric gradients yield slope and circular aspect. No nationwide raster loaded.
- Attribution: Mapzen; © offene Daten Österreichs – Digitales Geländemodell (DGM) Österreich; EU-DEM produced using Copernicus data funded by the European Union; USGS SRTM/GMTED. Source-specific terms apply (Austrian DGM CC BY 3.0 AT, EU-DEM Copernicus conditions, USGS public-domain data); retain the provider's attribution guidance. No new blanket license is assigned to the composite.

## GeoSphere Austria — INCA historical hourly v1, 1 km

- Dataset: https://data.hub.geosphere.at/dataset/inca-v1-1h-1km
- API: https://dataset.api.hub.geosphere.at/v1/timeseries/historical/inca-v1-1h-1km
- Metadata: https://dataset.api.hub.geosphere.at/v1/timeseries/historical/inca-v1-1h-1km/metadata
- Documentation: https://dataset.api.hub.geosphere.at/v1/docs/user-guide/resource.html
- CC BY 4.0, © GeoSphere Austria; hourly UTC, EPSG:31287 grid, approximately 1 km. This license applies to INCA, not the detailed landslide inventory.
- RR: hourly precipitation, kg m-2 (numerically mm). T2M: near-surface temperature, degree_Celsius. Archive starts 2011-03-15. Observational analyses integrate stations, remote sensing, weather models and terrain; this is a retrospective archive, not proof of the exact operational product available historically.
- Retrieved 2026-10-14. Raw responses and exact query/hash/time manifests in local `data/raw/http`. Requests use one event date and its six requested locations. Returned grid coordinates are preserved, nearest-cell offset checked (<=800 m), duplicate grid cells counted. No fabricated station observations.
- Local event-day midnight converted to UTC. Timestamp uncertainty handled using [timestamp - 1h, timestamp + 1h]; the whole envelope must lie within the nominal lookback and strictly before cutoff. Therefore 1/3/7/14/30/60-day summaries retain 22/70/166/334/718/1438 hours, respectively. Boundary hours are deliberately omitted, not estimated.
- Missing, negative precipitation or physically implausible values cause whole-group exclusion. Small negative historical RR values were actually observed; their cause is not asserted, values are not silently clipped. Completeness is required across the retained window for all six members.
- v1 retirement announced for December 2026; v2 starts October 2026 and cannot silently substitute the historical archive. Existing snapshots remain reproducible locally.

## Eurostat / GISCO — Austria country polygon

- Index: https://gisco-services.ec.europa.eu/distribution/v2/nuts/nuts-2016-units.html
- Geometry: https://gisco-services.ec.europa.eu/distribution/v2/nuts/distribution/AT-region-01m-4326-2016.geojson
- © EuroGeographics for the administrative boundaries; Eurostat/GISCO dissemination conditions apply. Used locally for the national eligibility mask, not as an ML predictor. Retrieved 2026-10-14, cached URL/timestamp/hash.
- Generalized 1:1 million polygon; it is not cadastral border precision. Both positives and candidate controls must be inside; border-adjacent exclusions are possible.

## V0.4 additions (retrieved 2026-10-14; cached under `data/v04/cache/`, record-level data local only)

| Provider / dataset | Endpoint | Licence | Use in V0.4 | Temporal rule / limitation |
|---|---|---|---|---|
| GeoSphere Austria, INCA v1 1 h 1 km (`inca-v1-1h-1km`) | `dataset.api.hub.geosphere.at/v1/timeseries/historical/inca-v1-1h-1km` | GeoSphere Data Hub terms, CC BY 4.0 attribution | RR, T2M; 1–60 d windows anchored at t0, same-day rain | value at T used only if T + 1 h < t0 (interval may end or start at T). Archive 2011-03-15 → today; retirement announced Dec 2026 |
| GeoSphere Austria, SPARTACUS v2 1 d 1 km | `…/spartacus-v2-1d-1km` | CC BY 4.0 | RR 90/180 d | metadata: RR of day D = 07:00 CET D → 07:00 CET D+1; used only if D+1 06:00 UTC < t0 |
| GeoSphere Austria, SNOWGRID-CL v2 1 d 1 km | `…/snowgrid_cl-v2-1d-1km` | CC BY 4.0 | SWE, snow depth, SWE decrease 3/7/14 d | exact output time not documented; treated conservatively like RR (valid D+1 06:00 UTC) |
| GeoSphere Austria, WINFORE v2 1 d 1 km | `…/winfore-v2-1d-1km` | CC BY 4.0 | **not admitted** | 20-event pilot coverage of SPEI30/90 was 86 % < 95 % pre-registered threshold |
| Copernicus CORINE Land Cover 2012 / 2018 (EEA) | `image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012/MapServer/0`, `…/CLC2018_LAEA/MapServer/0` (point queries) | Copernicus Land, free and open with attribution | 5 land-cover classes | CLC2018 (imagery 2017–18) only if t0 ≥ 2019-01-01, else CLC2012 (imagery 2011–12). 25 ha minimum mapping unit: small slides are not visible, local contrasts are coarse |
| GeoSphere Austria, INSPIRE GeologicUnit 1:500 000 | `gis.geosphere.at/maps/rest/services/inspire/GE_GeologicUnit_500k/MapServer/0` (whole layer, 4 107 polygons) | ©GeoSphere Austria / CC BY 4.0 | 5 lithology groups | no mass-movement deposit classes (checked); 1:500 000 positional accuracy is hundreds of metres |
| Mapzen/AWS Skadi 1″ composite (unchanged V0 source) | `elevation-tiles-prod.s3.amazonaws.com/skadi/` | see Skadi entry above | curvature, roughness, TPI, relative position, catchment, TWI | object Last-Modified (Apr 2016) must precede t0 |
| BEV/geoland DGM Österreich 10 m | `gis.ktn.gv.at/OGD/Geographie_Planung/ogd-10m-at.zip` (1.94 GB, HTTP Last-Modified 2019-06-18) | OGD (not downloaded) | **rejected** | object date postdates about half of the events and no per-cell acquisition date was found, so it is not demonstrably pre-event |

## V0.5 (2026-10-14)

No new data source. V0.5 queries the same V0.4 endpoints (INCA v1, SPARTACUS v2, SNOWGRID-CL v2, CORINE 2012/2018, GeoSphere geology 1:500 000) for the ten new unmatched control points per event; new responses are cached under `data/v05/cache/http/`, existing baseline/V0.4 responses and DEM tiles are only read. Control points come from the existing V0.4 pools (`data/v04/cache/control_pools/`, audited, see `data/v05/pool_audit/`).

## susceptibility_v01 (2026-10-17; registration `reports/susceptibility_v01/PREREGISTRATION.json`)

Raw files under `data/susceptibility_v01/raw/<dataset>/` with `provenance.json` (URL, size, md5, SHA-256, archive members). Aggregate audits (no record-level rows) in `reports/susceptibility_v01/phase1_audit_*.json`. Metadata probes in `reports/susceptibility_v01/phase0_evidence.json`.

| Dataset | Provider / original record | Licence (checked at the original) | CRS (from `.prj`) | Retrieved | Status |
|---|---|---|---|---|---|
| Far-Western Nepal multi-temporal inventory | Zenodo concept DOI 10.5281/zenodo.4290099, version 10.5281/zenodo.4290100, `LandslideInventory_FarWesternNepal.zip` 24,112,492 B, md5 `faf80509173373ce9a4774a87dcb214e` | CC BY 4.0 (Zenodo record) | WGS 84 / UTM 44N (EPSG:32644) | 2026-10-17 | downloaded, md5 verified |
| RER2023 Emilia-Romagna May 2023 | Zenodo 10.5281/zenodo.13742643, `RER2023_V1.rar` 43,630,642 B, md5 `3f17160d5e160b21cba86d6a696ae867`; article ESSD 17, 1055 (2025) | CC BY 4.0 (Zenodo record) | RDN2008 / UTM 32N (EPSG:7791) | 2026-10-17 | downloaded, md5 verified; **no mapping-extent file** |
| Gorkha 2015 (Roback, Zekkos, Clark et al.) | USGS data release DOI 10.5066/F7DZ06F9 (ScienceBase item 582c74fbe4b04d580bd377e8) | CC0 1.0 ("Rights: This work is marked with CC0 1.0 Universal", USGS data page) | not yet read | not retrieved | ScienceBase shows a Cloudflare human check; not bypassed |
| IFFI Südtirol (sealed blind test) | Autonome Provinz Bozen, WFS `https://geoservices1.civis.bz.it/geoserver/p_bz-Geology/ows`, layer `IdroGEO-Landslides-Events-Areas` (WFS 2.0.0, SHAPE-ZIP/JSON) | **conflicting:** open-data portal record "Eventi di frana" `license_id: cc-zero`; embedded metadata `access_constraints` CC BY-SA 3.0. Stricter reading (CC BY-SA 3.0) applies | EPSG:25832 (default CRS) | metadata only | 10,463 polygons; fields ID, UUID, CODE, TYPE_*, INSTITUTION_IT, MOVEMENT_*, SHAPE; **no date field**; lineage "field survey and photo-interpretation"; reference date 2022-05-01. Geometry not downloaded |
| NASADEM HGT v001 (DEM) | Microsoft Planetary Computer STAC `nasadem`, anonymous SAS token | Planetary Computer links LP DAAC policy titled "Public Domain"; NASA page itself not reachable (HTTP 403) | geographic, 1 arc-second, EGM96 | decided, not retrieved | SRTM flown 11–22 Feb 2000 (USGS EROS SRTM page). Void fill from other sources of unrecorded date; hosted copy has only the `elevation` asset (no source-flag layer) |
| Copernicus DEM GLO-30 | Copernicus Data Space | free licence, attribution DLR/Airbus/EU | EGM2008 | rejected for training | "Data were acquired by the TanDEM-X mission between 2011 and 2015" |
| USGS ShakeMap Gorkha | event us20002926, `grid.xml` 14,875,206 B, `raster.zip` 9,598,084 B | USGS public domain [not re-read] | geographic grid | decided, not retrieved | exploratory PGA variant for earthquake inventories only |
| CHIRPS v2.0 daily 0.05° | UCSB CHC `data.chc.ucsb.edu` | not yet read at the original | geographic | decided, not retrieved | Model B only after Gate 7 |
| ERA5-Land soil moisture | Open-Meteo archive API | Open-Meteo terms not yet read | ~0.1° | decided, not retrieved | Model B only after Gate 7 |

Known limitations from the audits: Far-Western Nepal dates are annual and automatic (83 % accuracy per record description); the dated-point layer reaches back to 1992, i.e. before the DEM acquisition. The point layer has 25,679 features while the record text says 25,639. RER2023 polygons are small (median 479 m²; 71 % below one 30 m cell) and include debris flows (`ClassNew` DF1/DF2) and earth flows (EF).

### susceptibility_v01 additions (2026-10-17, later)

- **Gorkha 2015**: `Roback_Nepal_final_files.zip`, 129,058,612 B (listed 123.08 MB), downloaded by the user in an external browser after the ScienceBase human check (no scripted bypass). ScienceBase lists no checksum; md5 `71ee37d7b211788277da5a9af5dcbe5d`, SHA-256 `0b80c2cc…c8ae9` recorded in `data/susceptibility_v01/raw/gorkha_2015/provenance.json`. Layers Full (24,915), Source (24,795), MappingExtent (1 polygon, 28,345 km²), ObscuredAreas (456), ImageQuality (2); CRS WGS 84 / UTM 45N (EPSG:32645). FGDC metadata `MapData_Landslides_Gorkha.xml`: use constraints "None", mapping 2015-04-26 to 2015-06-15; 12 polygons attributed to the 12 May aftershock.
- **Iburi 2018** (candidate, not registered): Zenodo 2577300, `Iburi landslide dataset.zip` 2,969,898 B, md5 verified, CC BY 4.0. Contains landslide inventory, old/reactivated landslides, AMeDAS stations, ellipses.
- **Wenchuan multi-temporal, Fan et al.** (candidate, registry only): Zenodo concept 1405489 → version 1484667, five files (35.6 MB) md5 verified, CC BY 4.0. Yearly mapping layers 2005–2018, debris-flow catchments, rain gauges.
- **NASADEM** tiles (22, 318 MB): Planetary Computer, item fetched by id; the anonymous SAS token is used for transfer only and never stored. No server checksum (Azure returns none); size checked, SHA-256 recorded per tile.
- **Copernicus GLO-30** tiles (22, 901 MB): `copernicus-dem-30m.s3.amazonaws.com`, DEM + per-tile XML + filling mask (FLM); md5 verified against the single-part S3 ETag. Per-tile TanDEM-X acquisition period from the XML `temporalCoverage`; per-tile usability in `reports/susceptibility_v01/dem_tile_usability.json`: all 12 Gorkha tiles end by 2014-09-13 (before 2015-04-25) → usable for Gorkha; all 4 Far-Western Nepal tiles end 2014-08/09 → not usable for landslides dated before 2015. Filling-mask pixels come from other sources with unrecorded dates. Copernicus remains a documented alternative; the registered primary DEM is NASADEM.
- **IFFI Südtirol sealed snapshot**: WFS SHAPE-ZIP with `CQL_FILTER=MOVEMENT_CODE IN (2,5,7)`, 3,523 server hits (= registration), 2,139,013 B, SHA-256 `fb540804…6f090`, stored read-only under `data/susceptibility_v01/sealed/`; manifest `reports/susceptibility_v01/SEALED_SUEDTIROL.json`. Not opened.
- Block margins of the eastern Gorkha blocks extend past 87° E; NASADEM and Copernicus tiles n26–n28 e087 were added (DEM fetch pads the extent by 0.1°). Totals: 25 NASADEM tiles, 25 Copernicus tiles.

## susceptibility_v02 (2026-10-18; registration `reports/susceptibility_v02/PREREGISTRATION.json`)

No new download. v02 reads the v01 raw files (Gorkha, Far-Western Nepal, RER2023, Iburi candidate) read-only; layer-level evidence in `reports/susceptibility_v02/phase0_data_audit.json`.

- **Iburi 2018** (Zenodo 2577300, CC BY 4.0, published 2019-02-25, Zhang/Li/Wang/Iio, Shimane University): `landslide_inventory.shp` 5,625 polygons, JGD2000 / UTM 54N (EPSG:3100); `old_landslides.shp` 1,649 and `reactivated_landslides.shp` 110 (EPSG:4612); 4 AMeDAS points; 3 standard-deviational ellipses (statistic of the landslides, not an extent). DBF code page `ANSI 932` (read as cp932). **No mapping extent** in the record.
- **GSI D1-No.991** (Iburi slope-failure/deposit map, aerial photos 6-11 Sep 2018, GeoJSON ZIP 1.1 MB, `https://www.gsi.go.jp/BOUSAI/H30-hokkaidoiburi-east-earthquake-index.html`; GSI content terms with attribution): possible Iburi source only if its archive contains an interpretation extent; not downloaded.
- **USGS ShakeMap Iburi**: event `us2000h8ty` (M 6.6 mww, 2018-09-05 18:07:59 UTC), product `atlas` v1 (updateTime 1594401324136), `grid.xml` 14,484,026 B; Gorkha `us20002926` `atlas` v1 (updateTime 1594162031303), `grid.xml` 14,875,206 B. Metadata only; not retrieved.
- **RER2023 extent**: ESSD 17, 1055 (2025) states segmentation by municipal boundaries and > 6,000 km² but publishes neither the municipality list nor an extent file; corresponding author A. Corsini (UNIMORE). The Region's INSPIRE layer of safeguard areas after May 2023 is derived from the landslides and is not an extent.
- **Wenchuan (Fan et al. 2019)**: `DF_Catchments.shp` (252 debris-flow catchments, ids like `B45`, 1,686 km²) does not link to the integer CIDs 1-43 of the landslide layers; the 42 mapped catchments are not published → excluded from v02.
