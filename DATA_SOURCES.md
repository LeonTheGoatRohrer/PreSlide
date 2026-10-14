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

## Pipeline B (satellite discovery, 2026-10-14): Sentinel-2 L2A via Earth Search

- Provider: ESA/Copernicus Sentinel-2 Level-2A surface reflectance, hosted as cloud-optimised GeoTIFFs on AWS (`sentinel-cogs` bucket, Element 84), catalogued by the Earth Search STAC API.
- Endpoints: `https://earth-search.aws.element84.com/v1/search` (collections `sentinel-2-c1-l2a`, preferred, and `sentinel-2-l2a`); assets `https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/...` and `.../sentinel-s2-c1-l2a/...`. Public, no credentials; TLS verified with the exported Windows CA bundle (`GDAL_CURL_CA_BUNDLE`).
- Licence: Copernicus Sentinel data, free and open under the Legal Notice on the use of Copernicus Sentinel Data and Service Information (attribution "Contains modified Copernicus Sentinel data [year]"). The Earth Search catalogue is provided by Element 84.
- Retrieval: 2026-10-14 onwards; every STAC response is cached with URL, UTC time and SHA-256 under `data/satellite/cache/stac/`; every patch GeoTIFF has a JSON sidecar with item id, acquisition time, platform, processing baseline, asset URLs, scale/offset, grid and SHA-256 (`data/satellite/samples/<sample_id>/patches/`).
- Processing: bands B02/B03/B04/B08 (10 m), B11/B12 (20 m) and SCL (20 m) are read as server-side spatial windows only (2.56 km × 2.56 km per sample) and warped onto a 10 m UTM grid snapped to the Sentinel-2 pixel lattice. Reflectance = DN × 1e-4 + offset with offset −0.1 for `sentinel-2-c1-l2a` (COGs store the BOA_ADD_OFFSET; vegetation green DN ≈ 1400) and 0 for `sentinel-2-l2a` (Earth Search stores these COGs without the offset for every processing baseline, vegetation green DN ≈ 250–750, although `raster:bands` advertises −0.1 in both collections; verified empirically on 2026-10-14 on 15 pilot acquisitions, and a runtime check refuses an acquisition whose SCL-vegetation green median leaves [0.01, 0.2]). DN 0 is nodata. Local cloud/shadow (SCL 3, 8, 9, 10), snow (11) and invalid (0, 1) fractions are computed inside the patch; scene-level cloud percentages are never used for selection.
- Coverage limitation: L2A over Austria is available from 2017-10 in these collections, so the 2016 Stanz storm and the 2017 events have no pre-event L2A imagery. The Collection-1 reprocessing (`sentinel-2-c1-l2a`) is incomplete before late 2018; the original `sentinel-2-l2a` items (older Sen2Cor baselines 02.07–02.08) are used there and the baseline is recorded per patch.
- Pipeline B deliberately uses post-event imagery. It is isolated from the precursor model (Pipeline A); see `preslide/satellite/__init__.py` and `tests/test_satellite.py`.
