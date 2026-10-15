# Candidate validation (Pipeline B, satellite-0.3)

Top 30 physical candidates of the held-out discovery scan by detector score, after removing every peak within 160 m of any of the 423 known V0.4 positives and collapsing detections of the same location from overlapping search patches (within 160 m) into one candidate. 1039 UNVERIFIED detections → 645 physical candidates (0 detections dropped near known positives).

Whole-patch cloud screening (satellite-0.3): every pixel within 100 m of a cloud-like SCL pixel (classes [2, 3, 7, 8, 9, 10, 11]) or an NDSI-snow pixel in either image is masked, and a position is scored only if its core keeps >= 90% and its ring >= 80% valid pixels; the same mask is applied to the (before_primary, after_confirm) pair, so after_confirm is screened at the candidate position.

## Persistence test

For every candidate the same change features are recomputed on the pair (before_primary, after_confirm), where after_confirm is the earliest acquisition usable at the source event at least 20 days after after_primary. The held-out detector of the candidate's independence unit (never trained on it) scores both pairs at the candidate pixel. Rule (config/satellite.json, validation.rule): declared before any after_confirm patch was fetched: a candidate persists if the same change features recomputed on (before_primary, after_confirm) still give log-odds > 0 at the candidate pixel and the main contrast feature keeps its sign with >= min_retained_contrast of its primary magnitude; a confirm pair with cloud/snow/nodata at the candidate (valid fractions below the minima) is not assessable. Statuses: LIKELY only if persists AND the visual review notes a slide-like scar; REJECTED only with a named non-slide cause (land use, water) or a transient artefact that did not persist; otherwise UNVERIFIED.

| quantity | value |
|---|---:|
| candidates | 30 |
| persistence assessable (confirm pair valid at the candidate) | 25 |
| not assessable (cloud, snow or nodata at the candidate in after_confirm) | 5 |
| change persists | 10 |
| change does not persist | 15 |
| median days event → after_confirm | 31 |

## Status

LIKELY needs persistence AND a slide-like scar in the visual review; REJECTED needs a named non-slide cause (land use, water) or a transient artefact that did not persist; everything else stays UNVERIFIED. No candidate is added to any inventory or to Pipeline A.

| status | count |
|---|---:|
| REJECTED | 27 |
| UNVERIFIED | 3 |

Reviewer summary: With the 100 m buffer the extreme cloud-edge scores are gone (top score 26.5 instead of 316) and the list is no longer dominated by cloud borders: 6 of 30 are clouds or haze that Sen2Cor did not classify at all (no SCL cloud-like pixel within 100 m, so the buffer cannot act), 2 are winter brightness patches, 10 are harvested, ploughed or mown fields with straight boundaries, 6 are linear brightening along valley-floor roads/streams through settlements after the June and September 2024 storms (flood deposits or works, not slope scars), 5 are brightness changes inside built-up areas, 1 is ambiguous. No slide-like scar on a slope in any of the 30.

## Candidates

Columns: heuristic type from the change signature (triage only); d(known) = distance to the nearest known V0.4 positive; n = detections of this location from overlapping patches; score = held-out log-odds on the primary pair / on the confirm pair; retained = confirm/primary ratio of the main contrast feature; confirm peak = rank of a confirm-pair peak within 160 m (— none).

| label | type | d(known) m | n | days (before / after / confirm) | score primary | score confirm | main feature | retained | confirm cloud m | assessable | persists | confirm peak | verdict | status | note |
|---|---|---:|---:|---|---:|---:|---|---:|---:|---|---|---:|---|---|---|
| KAND-01 | water_or_wetness_change | 973 | 3 | 2024-08-17..2024-09-21 / +30 d | 26.5 | 8.5 | d_ndwi_contrast | 0.98 | 300 | yes | yes | 1 | non_slide_land_use | REJECTED | bright polygon field with straight edges in after_primary, brown bare soil in confirm (+30 d): harvested and ploughed crop field, persists but is agriculture (same field as satellite-0.2 KAND-14) |
| KAND-02 | local_brightening | 1113 | 2 | 2026-05-29..2026-06-25 / +30 d | 24.9 | 2.6 | d_ndvi_small_contrast | -0.26 | 466 | yes | no | 3 | transient_artifact | REJECTED | white cloud with a bluish edge directly over the candidate in after_primary, not classified by SCL at all (no cloud-like pixel within 100 m, buffer could not act); confirm (+30 d) shows the fields unchanged, score 2.6, not persistent |
| KAND-03 | vegetation_loss_in_grass_or_crop | 186 | 1 | 2026-01-04..2026-02-25 / +49 d | 20.2 | 11.2 | d_ndvi_small_contrast | 0.19 | > patch | yes | no | 1 | transient_artifact | REJECTED | winter pair (January/February 2026) in a built-up area; a whitish patch and thin haze over the settlement at the candidate in after_primary (snow remnant or bright surface), gone in confirm (March); not persistent (same location as satellite-0.2 KAND-23) |
| KAND-04 | vegetation_loss_in_dense_vegetation | 357 | 3 | 2024-08-17..2024-09-21 / +30 d | 20.0 | — | d_ndvi_small_contrast | 0.88 | 201 | no | no | — | non_slide_land_use | REJECTED | bright rectangular field strip with straight edges in after_primary, brown ploughed field in confirm: harvested crop field (same field as satellite-0.2 KAND-24); confirm not assessable at the candidate (core 89 % valid) but the cause is visible |
| KAND-05 | vegetation_loss_in_dense_vegetation | 987 | 2 | 2023-07-31..2023-08-08 / +28 d | 19.5 | -1.6 | d_ndvi_small_contrast | -0.21 | 305 | yes | no | — | transient_artifact | REJECTED | broad bluish-white haze veil with a rainbow fringe over the candidate in after_primary, unclassified by SCL; confirm (+28 d) forest unchanged, score negative |
| KAND-06 | vegetation_loss_in_grass_or_crop | 580 | 1 | 2026-05-29..2026-06-20 / +31 d | 18.2 | 15.2 | d_ndvi_small_contrast | 0.80 | > patch | yes | yes | — | non_slide_land_use | REJECTED | field at the candidate turns pale in after_primary and bare brown in confirm; the confirm dNDVI shows field-sized red and blue blocks with straight boundaries all around: crop rotation/harvest, persists but is agriculture |
| KAND-07 | vegetation_loss_in_dense_vegetation | 773 | 2 | 2024-08-07..2024-09-21 / +31 d | 17.5 | — | d_ndvi_small_contrast | 0.58 | 292 | no | no | — | non_slide_land_use | REJECTED | elongated bright field with straight edges next to a farmstead in after_primary, brown ploughed in confirm: harvested crop field; confirm ring too cloudy for the persistence rule, cause visible |
| KAND-08 | vegetation_loss_in_dense_vegetation | 512 | 3 | 2024-06-18..2024-08-07 / +71 d | 17.0 | — | d_ndvi_small_contrast | — | 30 | no | no | — | ambiguous | UNVERIFIED | soft-edged white blob over the village centre at the candidate in after_primary, cloud-like but unclassified; after_confirm is cloud-covered at the position (30 m to a cloud-like pixel), nothing assessable; stays UNVERIFIED |
| KAND-09 | other_or_weak | 701 | 1 | 2023-07-29..2023-08-13 / +29 d | 14.8 | 6.4 | d_brightness_contrast | 0.61 | 516 | yes | yes | 1 | non_slide_land_use | REJECTED | pale brown field polygon next to forest in before_primary becomes bright beige bare surface in after_primary and stays so in confirm (+29 d): harvested field, persists but is agriculture |
| KAND-10 | other_or_weak | 659 | 1 | 2026-01-04..2026-02-25 / +49 d | 14.5 | 6.1 | d_brightness_contrast | -0.48 | > patch | yes | no | — | transient_artifact | REJECTED | winter pair in a built-up area with ploughed fields; a bright patch at the candidate in after_primary (snow remnant or wet roof) is gone in confirm; brightness contrast reversed, not persistent |
| KAND-11 | vegetation_loss_in_dense_vegetation | 549 | 1 | 2020-08-20..2020-08-25 / +31 d | 14.5 | 0.5 | d_ndvi_small_contrast | 0.17 | > patch | yes | no | 8 | transient_artifact | REJECTED | small white cloud puff directly over the candidate in after_primary, unclassified by SCL; confirm (+31 d) forest unchanged, score 0.5, not persistent |
| KAND-12 | vegetation_loss_in_dense_vegetation | 688 | 1 | 2024-06-18..2024-08-07 / +71 d | 13.9 | 4.2 | d_ndvi_small_contrast | 0.18 | 555 | yes | no | 2 | water_change | REJECTED | candidate on the row of houses along the valley-floor road; after the June 2024 storm the whole strip along road and stream through the settlement is brighter (dNDVI red along the strip, still in confirm): flood deposit or works along the channel, linear through the settlement, not a slope scar; main contrast not retained (0.18) |
| KAND-13 | water_or_wetness_change | 523 | 1 | 2024-08-17..2024-09-21 / +31 d | 13.7 | 6.6 | d_ndwi_contrast | 0.34 | 1100 | yes | no | 4 | water_change | REJECTED | bright linear strip ~30 m wide following the stream/road diagonally through the village in after_primary (September 2024 flood), still visible in confirm: sediment-covered channel or linear works, not a slope failure (same strip as satellite-0.2 KAND-17) |
| KAND-14 | vegetation_loss_in_dense_vegetation | 875 | 1 | 2026-05-29..2026-06-25 / +30 d | 12.5 | — | d_ndvi_small_contrast | — | 0 | no | no | — | ambiguous | UNVERIFIED | field-sized brownish patch with a straight lower edge at the candidate, next to a bright gravel/working area in dark forest; looks like cultivation but after_confirm is fully cloud-covered at the position; needs later imagery, stays UNVERIFIED |
| KAND-15 | vegetation_loss_in_dense_vegetation | 287 | 3 | 2024-06-18..2024-08-07 / +71 d | 12.2 | 5.7 | d_ndvi_small_contrast | 0.24 | 444 | yes | no | 3 | water_change | REJECTED | brightening along the built strip and road on the valley floor after the June 2024 storm, linear through the settlement with a bright gravel-like surface along the stream, still bright in confirm (+71 d): flood deposit or channel works, not a slope scar |
| KAND-16 | local_brightening | 881 | 1 | 2025-07-20..2025-07-30 / +23 d | 11.4 | 2.6 | d_brightness_contrast | 0.69 | 778 | yes | yes | 1 | non_slide_land_use | REJECTED | rectangular field with straight boundaries: bare brown in before_primary, pale grey in after_primary (with a bluish haze fringe) and pale bare in confirm; field surface state, persists but is agriculture |
| KAND-17 | vegetation_loss_in_dense_vegetation | 640 | 1 | 2026-05-29..2026-06-20 / +31 d | 11.1 | 14.1 | d_ndvi_small_contrast | 1.08 | > patch | yes | yes | — | non_slide_land_use | REJECTED | pale field at the candidate turns brownish bare in after_primary and confirm; the confirm dNDVI shows large red and blue field blocks with straight boundaries: crop rotation, persists but is agriculture |
| KAND-18 | vegetation_loss_in_dense_vegetation | 726 | 2 | 2024-06-18..2024-08-07 / +71 d | 11.1 | — | d_ndvi_small_contrast | 1.18 | 202 | no | no | — | water_change | REJECTED | same valley-floor strip as KAND-15/27/28 (June 2024 storm): bright linear surface along the stream/road through the settlement in after_primary and confirm, not a slope scar; confirm core 87 % valid, not assessable by the rule, cause visible |
| KAND-19 | vegetation_loss_in_dense_vegetation | 830 | 2 | 2023-07-31..2023-08-08 / +28 d | 11.1 | -2.2 | d_ndvi_small_contrast | -0.08 | 1344 | yes | no | — | transient_artifact | REJECTED | large bluish-white thin cloud veil across the upper half of after_primary covering the candidate, unclassified by SCL; confirm forest and fields unchanged, score negative |
| KAND-20 | other_or_weak | 271 | 1 | 2024-09-11..2024-09-23 / +41 d | 10.9 | 7.6 | d_brightness_contrast | -0.97 | 596 | yes | no | 1 | transient_artifact | REJECTED | candidate on houses of a village along a road; mottled brightness differences of roofs and roads between the two acquisitions, nothing on a slope; contrast reversed in confirm, not persistent |
| KAND-21 | vegetation_loss_in_dense_vegetation | 270 | 1 | 2026-04-29..2026-05-24 / +48 d | 10.1 | 5.2 | d_ndvi_small_contrast | 0.65 | 395 | yes | yes | 4 | non_slide_land_use | REJECTED | one strip of a striped field turns bright beige in after_primary (harvest/mowing) and stays bare in confirm, straight edges on both sides: agriculture, persists |
| KAND-22 | vegetation_loss_in_grass_or_crop | 710 | 3 | 2024-08-17..2024-09-21 / +30 d | 9.9 | 4.3 | d_ndvi_small_contrast | 0.66 | 306 | yes | yes | 3 | water_change | REJECTED | curved bright line through the settlement in after_primary (September 2024 flood period) following the stream/road, still visible in confirm: flood deposit along the channel, linear, not a slope failure |
| KAND-23 | vegetation_loss_in_grass_or_crop | 479 | 1 | 2023-07-09..2023-08-13 / +28 d | 9.8 | 5.5 | d_ndvi_small_contrast | 0.99 | 332 | yes | yes | 1 | non_slide_land_use | REJECTED | compact pale patch ~60 m across inside the village next to buildings and a road, appears in after_primary and persists in confirm: bare ground or construction in the built-up area, no slope scar |
| KAND-24 | vegetation_loss_in_dense_vegetation | 255 | 1 | 2020-08-13..2020-09-22 / +61 d | 9.5 | 0.2 | d_ndvi_small_contrast | -0.17 | 484 | yes | no | — | transient_artifact | REJECTED | white/bluish cloud puff directly over the candidate in after_primary, unclassified by SCL; confirm (+61 d, October) forest unchanged, score 0.2, not persistent |
| KAND-25 | other_or_weak | 454 | 1 | 2026-01-04..2026-02-25 / +49 d | 9.5 | 8.1 | d_brightness_contrast | 0.50 | > patch | yes | yes | — | ambiguous | UNVERIFIED | winter pair in a built-up area with apartment blocks; no visible surface change at the candidate in any panel, the brightness contrast persists without a visible cause (low sun, roofs, remnant snow); stays UNVERIFIED |
| KAND-26 | change_on_bare_or_built_surface | 408 | 1 | 2026-01-04..2026-02-25 / +49 d | 9.4 | 8.3 | d_brightness_contrast | 0.03 | > patch | yes | no | 6 | transient_artifact | REJECTED | winter pair, same built-up area as KAND-25; no visible change at the candidate, brightness contrast gone in confirm (retained 0.03), not persistent |
| KAND-27 | vegetation_loss_in_dense_vegetation | 392 | 2 | 2024-06-18..2024-08-07 / +71 d | 9.4 | 6.3 | d_ndvi_small_contrast | 0.48 | 332 | yes | no | 4 | water_change | REJECTED | same valley-floor strip as KAND-15/18/28 after the June 2024 storm: bright linear surface along the stream and road, persists in confirm; linear channel feature, not a slope scar |
| KAND-28 | vegetation_loss_in_dense_vegetation | 187 | 2 | 2024-06-18..2024-08-07 / +71 d | 9.3 | 6.7 | d_ndvi_small_contrast | 0.57 | 528 | yes | yes | 1 | water_change | REJECTED | same valley-floor strip as KAND-15/18/27: bright linear surface along stream and road through the settlement in after_primary and confirm; flood deposit or works, not a slope scar |
| KAND-29 | water_or_wetness_change | 340 | 3 | 2024-08-17..2024-09-21 / +30 d | 9.3 | 0.1 | d_ndwi_contrast | 0.08 | 452 | yes | no | — | non_slide_land_use | REJECTED | straight-edged pale field strips and a road at the candidate in after_primary; field pattern changes (mowing/harvest), not persistent in confirm; agriculture |
| KAND-30 | vegetation_loss_in_dense_vegetation | 804 | 1 | 2023-07-19..2023-08-13 / +28 d | 9.1 | -0.2 | d_ndvi_small_contrast | -0.08 | 2098 | yes | no | 4 | non_slide_land_use | REJECTED | bright beige polygon with straight edges at the candidate in after_primary (mown or harvested meadow), green again in confirm (+28 d), score negative; agriculture |

## Cloud proximity of the candidates

Distance from each candidate pixel to the nearest cloud-like scene-classification pixel (SCL 2, 3, 7, 8, 9, 10, 11) in before_primary or after_primary (`cloud_proximity.json`). discovery scan with a 100 m buffer around every cloud-like SCL / NDSI-snow pixel of either image (whole patch) and position gating by valid core/ring fraction

With the 100 m buffer no scored position can lie within 100 m of such a pixel by construction; the larger radii show how strongly the remaining ranking still clusters near cloud-like pixels.

| set | n | within 100 m | within 200 m | within 300 m |
|---|---:|---:|---:|---:|
| all candidates | 1039 | 0% | 1% | 15% |
| top 30 by score | 30 | 0% | 0% | 13% |
| top 100 by score | 100 | 0% | 0% | 16% |
| top 300 by score | 300 | 0% | 1% | 15% |
| rank-1 candidates per search | 117 | 0% | 0% | 15% |
| rediscovered known events (reference) | 40 | 0% | 2% | 18% |

Reference satellite-0.2 (no buffer, `cloud_proximity_satellite02.json`):

| set | n | within 100 m | within 300 m |
|---|---:|---:|---:|
| all candidates | 1416 | 18% | 39% |
| top 30 by score | 30 | 87% | 87% |
| top 100 by score | 100 | 76% | 82% |
| rank-1 candidates per search | 118 | 38% | 53% |
| rediscovered known events (reference) | 61 | 16% | 39% |

## Visual review

Contact sheets `reports/satellite/contact_sheets/candidates_01..05.png`: RGB before_primary, after_primary, after_confirm and ΔNDVI for both pairs, 640 m window, cross = candidate pixel, box = 120 m small window. The reviewer's verdicts and notes are in `reports/satellite/candidate_review.json` (one entry per label; a verdict without a note changes nothing).

## Interpretation and limits

- The top of the score list is dominated by extreme log-odds (the logistic detector extrapolates far outside its training range for water, river-bank and harvest changes); a high score is not evidence of a landslide.
- Persistence separates transient changes (mowing, harvest, moisture, cloud edge) from lasting surface change; a lasting change can still be a clear-cut, construction or a river-bed shift, which only the visual review and later orthophotos or inventories can resolve.
- after_confirm is selected by usability at the source event; at the candidate itself it is screened with the buffered mask, and a candidate whose own core/ring fall below the validation minima is reported as not assessable rather than scored.
- A buffer around SCL-classified pixels removes cloud borders that Sen2Cor partly classifies; haze or thin cloud that SCL misses entirely is not buffered and can still produce candidates, which only the visual review catches.
- Candidates are UNVERIFIED by default; LIKELY is a hypothesis for field or orthophoto checking, not a documented event, and nothing here is written to the Pipeline A event tables (write guard).
