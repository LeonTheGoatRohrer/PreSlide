# Limitations

- This is an exploratory retrospective matched case-control prototype, not an operational warning system. Classification scores are not annual landslide probabilities. A positive result on one split does not establish reliable precursor detection or causation.
- The detailed event source is labelled Naturgefahren Test and its specific reuse license was not identified. The user authorized local non-commercial research; GeoSphere has not confirmed our interpretations of QUAL_LAGE, QUAL_PROZ, QUAL_MB or event timing. Raw data are not redistributed or exposed through bulk API endpoints.
- Position categories are source-reported. A point with a category upper bound of 100 m may not mark the initiation zone; 30 m terrain matching can change within that radius. The report includes a deterministic offset diagnostic, not an independently validated accuracy distribution.
- A compatible single-day narrative does not prove exact occurrence timing. Ambiguous and multi-day descriptions are excluded. Conservative parsing also discards some potentially usable events.
- Controls are pseudo-negatives: no documented event is not proof of stability. Inventory completeness, road/media exposure and reporting bias remain. A full historical snapshot is used for control exclusion, including later events; this is retrospective selection, not a real-time deployment simulation.
- Control exclusion buffers are point-based; unknown/open-ended uncertainty receives a 2 km proxy, not a guaranteed bound. Failure footprints and geology/land cover are unavailable. Generalized national borders can exclude border-adjacent sites.
- The candidate pool is finite (6,000 per event). Failed matching is reported, not proof that no suitable control exists anywhere. Calipers and separation are unchanged across all events. Some controls may approach the 10 km search radius, weakening the same-terrain-system assumption.
- Skadi object timestamps establish that the product predates the landslide, not the exact acquisition date of each source pixel. Terrain can already contain earlier failures or other changes. Composite DEM resolution and interpolation limit slope/aspect accuracy.
- INCA is a 1 km retrospective analysis using stations, remote sensing, model background and terrain. It cannot resolve every slope and is not independent of topography. Historical operational product versions and calibration are not verified; observational pre-event timestamps alone do not prove operational real-time availability.
- One-hour timestamp envelopes deliberately omit boundary hours: nominal 60-day features retain 1,438 rather than 1,440 hours; 1-day features retain 22 hours. These are guarded-window summaries, not exact calendar-day totals. Local event-day midnight avoids using unknown event-day weather.
- Every retained weather value must be present and plausible. Entire groups with missing values or negative precipitation are excluded; no silent clipping, interpolation or future-data replacement. This strict rule reduces the cohort and can bias the retained regions and years. See RESULTS.md for actual exclusions.
- Event/control groups are kept together, with additional transitive storm and spatial overlap clusters. These are heuristics, not known independent storms. Nearby weather fields and unobserved regional factors can still be correlated. Sample counts overstate independent information.
- Test uncertainty is substantial when few clusters remain. Bootstrap intervals hold fitted models fixed and do not include training uncertainty. Fixed-threshold precision/recall, permutation importance and geographic stress tests can be unstable. All planned models are reported; no tuning against test scores.
- Weather common to all six samples cannot distinguish them. Pooled AUC may reflect differences between event groups. Within-group pairwise AUC and fractional first-place ranking therefore accompany standard metrics. Static matching itself can induce selection artifacts; feature importance is not causal evidence.
- Geology, land cover, soil moisture, snow and Sentinel imagery are not included. This is not evidence that those measurements are unimportant.
- The local web demonstration exposes only five selected, derived example groups and aggregate metrics. It intentionally does not provide the raw inventory or a bulk export of source records. Reproducing exact results requires the locally preserved source snapshots; source endpoints can change.


## V0.2 development diagnostics

Five repeated grouped partitions reuse 45 events in only 16 dependency clusters; they are not independent validation. The largest cluster contains 15 events. Weather benefit is model/metric dependent. Learning curves are non-monotonic; more rows with the same information need not improve generalization. The RF learning curve uses development-selected model family. Correlated windows and small position/state subgroups limit interpretation. Cluster-balanced evaluation does not remove large-cluster training influence. Pooled cross-fitted scores may differ in calibration between folds. Exploratory fixed-model bootstrap intervals omit retraining uncertainty. Full diagnostics and the single next research priority are in reports/stability_v02/summary.md.


## V0.3 null reference

The permutation null makes all six group members exchangeable. True positives are additionally the centre of their control search, so terrain-only deviations from the null can stem from design structure. p-values are empirical (100 draws), uncorrected for the 12 delta and 27 absolute statistics examined, and computed on repeated splits of the same 45 events. A null result at this sample size does not exclude weak weather effects.

## V0.4

- **Few independent units.** 423 groups but only 19 development and 11 test units; the test interval (0.63–0.87) is wide and the weighted metric is driven by several 1–2-event units. Per-event results are lower (0.668 combined) because the Stanz storm (243 events) is weak under the terrain model.
- **Weather benefit unproven.** Combined − static on the test is +0.049 with a 95 % interval touching zero; development shows the opposite sign. No claim that pre-event weather improves the spatial ranking.
- **Reporting bias.** The strongest predictors are land cover (forest −, settlement/traffic and grassland +). Inventory events near infrastructure are more likely to be documented; physics and detection bias cannot be separated. Point placement conventions (e.g. upper scarp in orthophoto mapping) affect TPI/curvature at the positive.
- **Protocol amendment.** Location links were changed once, before modelling, to positive-involving overlaps (AMENDMENT_1). Test controls may lie near development controls (same label).
- **Coarse context data.** CORINE (25 ha MMU, 100 m) and 1:500 000 geology are coarse; 30 m DEM; 10 m DGM rejected because it is not demonstrably pre-event. WINFORE not admitted (pilot coverage 86 %).
- **Time of day.** t0 is a conservative lower bound; the triggering rain after t0 remains invisible. Same-day rain exists only for daypart/clock events (281 of 300 test events, mostly one storm).
- **Concentration.** Steiermark dominates (Stanz); leave-one-state-out results range 0.44–0.93 (descriptive, small n). No geographic transferability claim.
- **Not evaluated:** tier-B/C date tiers, tier-2 media events, Sentinel, ERA5-Land, case-crossover design.

## V0.5

- **Seen events, no new test.** All 423 positives were evaluated in V0.4; the purged CV is exploratory. Repetitions and bootstrap are not independent confirmations; 29 units only.
- **Easier, different task.** Unmatched area-uniform controls make terrain/land-cover contrasts dominant. The high local AUC (0.85) must not be compared with V0.4 (matched: 0.705 on the same cohort) or read as landslide probability.
- **Reporting bias.** Positives are lower and less forested than the background; inventory points cluster near valleys, settlements and roads. Physics and detection probability cannot be separated (road-distance diagnostic not retrieved).
- **Temporal ≠ weather here.** 1 km INCA fields carry elevation and location; the weather-only score partly encodes terrain. No weather benefit over static (−0.023).
- **Retrospective exclusion zones** use the full inventory snapshot, including later events. One group excluded because a control failed the V0.4 5 m DEM alignment check (7.5 m on a 35° slope, sub-cell); the check was not relaxed.
## Pipeline B (satellite)

- Sentinel-2 L2A in the AWS collections starts over Austria in late 2017, so the 2016 Stanz storm (243 events) and the 2017 events have no pre-event imagery; the satellite dataset is dominated by 2018–2024 events and by Styria.
- Cloud cover and snow leave many events without a usable pair within ±180/120 days; winter events are rarely usable, and pairs can be weeks apart, so the detected change is "between two clear dates", not "at the event date". Late-season or multi-month gaps mix harvest, mowing and forestry into the difference even after ring normalisation.
- Small slides (tens of metres) occupy a few 10 m pixels; the 120 m window dilutes them and forest canopy can hide them. A positive without visible change is not evidence against the inventory record.
- Controls share the acquisition pair but remain pseudo-negatives; several storm clusters put other known events inside a control's 960 m ring.
- The two Earth Search collections store reflectance with different offsets and different Sen2Cor baselines (02.x vs 05.x); the per-collection offset was verified empirically and is checked at runtime, but residual radiometric differences between mixed-collection pairs remain (`same_collection` is recorded).
- The held-out rediscovery scan searches only the 2.56 km patch around a known event; it is a localisation test, not evidence that the detector works on unknown regions. Candidate types in the false-positive analysis are heuristics for triage, not labels.
- Sentinel-1 is not yet integrated; the architecture (per-sample grid, per-item patch cache, feature maps) is designed so that SAR change layers can be added as further bands.
- **Cloud and haze edges dominate the candidate ranking (satellite-0.2).** Acquisition pairs are screened for cloud and snow only inside the 960 m window around the source event; the outer part of the 2.56 km patch is recorded but not required, and Sen2Cor misses thin cloud, haze and shadow edges. 87 % of the 30 highest-scoring candidates lie within 100 m of a cloud-like SCL pixel (16 % of the rediscovered known events). Raw-score ranking of candidates is therefore not usable; the top-30 validation found 21 REJECTED (20 cloud/haze/shadow or mowing artefacts, 2 harvested fields, 2 lake surfaces, 1 linear flood/works strip), 9 UNVERIFIED and no LIKELY candidate.
- `after_confirm` is screened at the source event, not at the candidate position: 12 of 30 top candidates could not be assessed for persistence.
- Known-event suppression uses the 423 V0.4 positives with fine positions; coarse-position inventory records (upper bound > 20 m) are not suppressed, so some candidates may still be documented events.
- Baseline C uses ImageNet features of 10 m RGB chips; a within-group AUC near 0.5 says that these generic features do not transfer, not that learned encoders cannot work (no fine-tuning, no multispectral pretrained model tried).
- RANDOM_LANDSCAPE points are generic negatives on the same dates; they contain whatever the landscape does (fields, water, settlements, forestry) and are not matched to the positive's terrain, so a model trained on them answers a different question (landslide vs landscape) than the matched-control baseline (reported slope vs similar slope).
