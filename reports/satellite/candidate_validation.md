# Candidate validation (Pipeline B, satellite-0.2)

Top 30 physical candidates of the held-out discovery scan by detector score, after removing every peak within 160 m of any of the 423 known V0.4 positives and collapsing detections of the same location from overlapping search patches (within 160 m) into one candidate. 1416 UNVERIFIED detections → 830 physical candidates (0 detections dropped near known positives).

## Persistence test

For every candidate the same change features are recomputed on the pair (before_primary, after_confirm), where after_confirm is the earliest acquisition usable at the source event at least 20 days after after_primary. The held-out detector of the candidate's independence unit (never trained on it) scores both pairs at the candidate pixel. Rule (config/satellite.json, validation.rule): declared before any after_confirm patch was fetched: a candidate persists if the same change features recomputed on (before_primary, after_confirm) still give log-odds > 0 at the candidate pixel and the main contrast feature keeps its sign with >= min_retained_contrast of its primary magnitude; a confirm pair with cloud/snow/nodata at the candidate (valid fractions below the minima) is not assessable. Statuses: LIKELY only if persists AND the visual review notes a slide-like scar; REJECTED only with a named non-slide cause (land use, water) or a transient artefact that did not persist; otherwise UNVERIFIED.

| quantity | value |
|---|---:|
| candidates | 30 |
| persistence assessable (confirm pair valid at the candidate) | 18 |
| not assessable (cloud, snow or nodata at the candidate in after_confirm) | 12 |
| change persists | 3 |
| change does not persist | 15 |
| median days event → after_confirm | 30 |

## Status

LIKELY needs persistence AND a slide-like scar in the visual review; REJECTED needs a named non-slide cause (land use, water) or a transient artefact that did not persist; everything else stays UNVERIFIED. No candidate is added to any inventory or to Pipeline A.

| status | count |
|---|---:|
| REJECTED | 21 |
| UNVERIFIED | 9 |

## Candidates

Columns: heuristic type from the change signature (triage only); d(known) = distance to the nearest known V0.4 positive; n = detections of this location from overlapping patches; score = held-out log-odds on the primary pair / on the confirm pair; retained = confirm/primary ratio of the main contrast feature; confirm peak = rank of a confirm-pair peak within 160 m (— none).

| label | type | d(known) m | n | days (before / after / confirm) | score primary | score confirm | main feature | retained | assessable | persists | confirm peak | verdict | status | note |
|---|---|---:|---:|---|---:|---:|---|---:|---|---|---:|---|---|---|
| KAND-01 | water_or_wetness_change | 335 | 1 | 2018-09-13..2018-09-20 / +29 d | 316.1 | 0.8 | d_ndwi_contrast | 0.18 | yes | no | — | transient_artifact | REJECTED | after_primary fully cloud-covered at the candidate (white), dNDVI red only along the cloud-mask edge; confirm (+29 d) shows the same meadow unchanged |
| KAND-02 | vegetation_loss_in_dense_vegetation | 1037 | 1 | 2024-07-08..2024-08-07 / +41 d | 239.8 | 61.0 | d_ndvi_small_contrast | 0.01 | no | no | 2 | transient_artifact | UNVERIFIED | before_primary carries a bluish haze veil over the candidate, after and confirm show undisturbed dark forest; the apparent NDVI loss is the haze in the before image. Persistence not assessable (before pixels masked), so status stays UNVERIFIED |
| KAND-03 | other_or_weak | 1043 | 3 | 2022-08-09..2022-08-29 / +60 d | 158.5 | -0.7 | d_brightness_contrast | -0.45 | yes | no | 20 | transient_artifact | REJECTED | candidate sits at the edge of a cloud in after_primary (white area to the right); confirm (+60 d) shows meadows and the farm building unchanged |
| KAND-04 | vegetation_loss_in_dense_vegetation | 658 | 1 | 2025-07-23..2025-07-30 / +24 d | 125.3 | 112.2 | d_ndvi_small_contrast | -1.15 | no | no | 1 | transient_artifact | UNVERIFIED | thin cloud over the upper half of before_primary (blue dNDVI ring around a masked cloud); after and confirm show unchanged forest. Not assessable, stays UNVERIFIED |
| KAND-05 | vegetation_loss_in_dense_vegetation | 1000 | 1 | 2023-06-29..2023-07-07 / +22 d | 68.4 | -2.2 | d_ndvi_small_contrast | -0.01 | yes | no | — | transient_artifact | REJECTED | dark cloud shadow over the forest at the candidate in after_primary; confirm (+22 d) forest unchanged, score negative |
| KAND-06 | water_or_wetness_change | 571 | 2 | 2023-07-31..2023-08-08 / +28 d | 66.3 | -0.7 | d_ndwi_contrast | -0.06 | yes | no | — | transient_artifact | REJECTED | after_primary hazy/cloudy at the candidate; confirm shows the farm buildings and fields unchanged |
| KAND-07 | other_or_weak | 318 | 1 | 2025-07-20..2025-07-30 / +23 d | 60.1 | -0.8 | d_bsi_small_contrast | -0.01 | yes | no | — | transient_artifact | REJECTED | white cloud over the candidate in after_primary; confirm shows the farmstead unchanged |
| KAND-08 | other_or_weak | 699 | 3 | 2022-08-09..2022-08-29 / +60 d | 48.9 | -1.3 | d_brightness_contrast | 46.52 | yes | no | — | transient_artifact | REJECTED | after_primary is in deep shadow/very dark at the candidate (illumination), confirm (+60 d, October) shows the meadow strip in forest unchanged apart from autumn colours |
| KAND-09 | other_or_weak | 889 | 1 | 2024-07-08..2024-08-07 / +41 d | 41.4 | -11.8 | d_bsi_small_contrast | 0.73 | no | no | 3 | transient_artifact | UNVERIFIED | before_primary hazy (thin cloud veil) over the candidate; after and confirm show forest and settlement unchanged. Not assessable, stays UNVERIFIED |
| KAND-10 | vegetation_loss_in_grass_or_crop | 632 | 1 | 2024-07-08..2024-08-07 / +41 d | 34.6 | -10.0 | d_ndvi_small_contrast | 0.07 | no | no | 4 | transient_artifact | UNVERIFIED | cloud in before_primary at the candidate; after and confirm forest unchanged. Not assessable, stays UNVERIFIED |
| KAND-11 | vegetation_loss_in_dense_vegetation | 725 | 4 | 2024-08-10..2024-08-15 / +23 d | 33.7 | -1.1 | d_ndvi_small_contrast | -0.04 | yes | no | — | transient_artifact | REJECTED | meadows around the candidate turned bright yellow-green in after_primary (mowing/hay, illumination); the small pond at the forest edge in the window is unchanged in confirm |
| KAND-12 | vegetation_loss_in_grass_or_crop | 794 | 2 | 2026-05-29..2026-06-25 / +30 d | 33.2 | 3.2 | d_ndvi_small_contrast | -0.58 | no | no | 8 | transient_artifact | UNVERIFIED | cloud over the candidate in after_primary and again in after_confirm; nothing can be assessed, stays UNVERIFIED |
| KAND-13 | other_or_weak | 635 | 2 | 2023-07-31..2023-08-13 / +28 d | 32.7 | 44.9 | d_brightness_contrast | 0.61 | no | no | 1 | non_slide_land_use | REJECTED | a rectangular brown field with straight boundaries appears SE of the candidate in after_primary and is still bare in confirm: harvested/ploughed field, not a slope failure |
| KAND-14 | water_or_wetness_change | 973 | 3 | 2024-08-17..2024-09-21 / +30 d | 26.5 | 8.6 | d_ndwi_contrast | 0.99 | yes | yes | 1 | non_slide_land_use | REJECTED | bright rectangular field with straight edges in after_primary, brown bare soil in confirm (+30 d): harvested and ploughed crop field, persists but is agriculture |
| KAND-15 | vegetation_loss_in_dense_vegetation | 1069 | 1 | 2025-07-19..2025-08-05 / +33 d | 24.9 | 1.7 | d_ndvi_small_contrast | 0.32 | yes | no | 6 | transient_artifact | REJECTED | unmasked thin cloud with a rainbow fringe over the candidate in after_primary; confirm shows the fields unchanged |
| KAND-16 | local_brightening | 1113 | 2 | 2026-05-29..2026-06-25 / +30 d | 24.9 | 2.7 | d_ndvi_small_contrast | -0.31 | yes | no | 10 | transient_artifact | REJECTED | white cloud over the candidate in after_primary; confirm shows the meadow unchanged |
| KAND-17 | water_or_wetness_change | 607 | 1 | 2024-08-17..2024-09-21 / +31 d | 23.9 | 19.5 | d_ndwi_contrast | 0.90 | yes | yes | 1 | water_change | REJECTED | a bright linear strip ~30 m wide following a stream/road diagonally through the village appears in after_primary (September 2024 flood period) and persists in confirm: sediment-covered torrent channel or linear works, linear through a settlement, not a slope failure |
| KAND-18 | water_or_wetness_change | 245 | 3 | 2018-09-13..2018-09-20 / +29 d | 23.2 | 5.2 | d_ndwi_contrast | 0.45 | yes | no | 6 | transient_artifact | REJECTED | cloud over the candidate in after_primary; confirm hazy but the meadow is unchanged |
| KAND-19 | vegetation_loss_in_dense_vegetation | 814 | 1 | 2023-07-31..2023-08-13 / +25 d | 22.7 | 0.3 | d_ndvi_small_contrast | 0.08 | no | no | 2 | transient_artifact | UNVERIFIED | cloud over the candidate in before_primary; after and confirm show agricultural fields unchanged. Not assessable, stays UNVERIFIED |
| KAND-20 | vegetation_loss_in_dense_vegetation | 853 | 1 | 2024-07-08..2024-08-07 / +41 d | 22.6 | 12.8 | d_ndvi_small_contrast | 0.43 | no | no | — | transient_artifact | UNVERIFIED | cloud in before_primary; after and confirm show dark forest with a forest road unchanged. Not assessable, stays UNVERIFIED |
| KAND-21 | water_or_wetness_change | 390 | 10 | 2018-09-13..2018-09-20 / +29 d | 21.1 | -0.7 | d_ndwi_contrast | -0.38 | yes | no | — | transient_artifact | REJECTED | after_primary completely cloud-covered; confirm shows meadow and forest edge unchanged |
| KAND-22 | vegetation_loss_in_grass_or_crop | 812 | 1 | 2022-08-14..2022-08-29 / +100 d | 20.4 | 7.4 | d_ndvi_small_contrast | -0.28 | no | no | 1 | water_change | REJECTED | candidate lies on the open water of a lake near the shore; lake-surface reflectance change, no slope |
| KAND-23 | vegetation_loss_in_grass_or_crop | 179 | 1 | 2026-01-04..2026-02-25 / +49 d | 20.2 | 12.1 | d_ndvi_small_contrast | 0.22 | yes | no | 3 | transient_artifact | REJECTED | winter pair (January/February 2026) in a built-up area; a bright patch at the candidate in after_primary (snow remnant or bright surface) is gone in confirm (March) |
| KAND-24 | vegetation_loss_in_dense_vegetation | 357 | 3 | 2024-08-17..2024-09-21 / +30 d | 20.0 | 4.9 | d_ndvi_small_contrast | 0.85 | yes | yes | — | non_slide_land_use | REJECTED | bright rectangular strip with straight edges in after_primary, brown ploughed field in confirm: harvested crop field, persists but is agriculture |
| KAND-25 | other_or_weak | 825 | 1 | 2024-07-08..2024-08-07 / +41 d | 19.4 | -0.5 | d_bsi_small_contrast | 0.74 | no | no | 1 | transient_artifact | UNVERIFIED | haze/thin cloud in before_primary; after and confirm show forest unchanged. Not assessable, stays UNVERIFIED |
| KAND-26 | water_or_wetness_change | 611 | 1 | 2026-05-29..2026-06-25 / +30 d | 19.3 | -1.3 | d_ndwi_contrast | -0.04 | no | no | — | ambiguous | UNVERIFIED | greyish-blue mottled blob ~150 m across inside closed forest in after_primary, haze-like but could be a canopy disturbance; after_confirm is cloudy at the position. Needs later imagery |
| KAND-27 | water_or_wetness_change | 736 | 8 | 2018-09-13..2018-09-20 / +29 d | 19.0 | -0.2 | d_ndwi_contrast | -0.48 | yes | no | — | transient_artifact | REJECTED | after_primary completely cloud-covered at the candidate; confirm shows meadows unchanged |
| KAND-28 | vegetation_loss_in_dense_vegetation | 987 | 2 | 2023-07-31..2023-08-08 / +28 d | 18.8 | -1.9 | d_ndvi_small_contrast | -0.25 | yes | no | — | transient_artifact | REJECTED | haze streaks over the candidate in after_primary; the small dark pond/wet spot in the window is unchanged in confirm |
| KAND-29 | vegetation_loss_in_dense_vegetation | 783 | 1 | 2018-09-13..2018-09-20 / +29 d | 18.7 | -0.1 | d_ndvi_small_contrast | -0.45 | yes | no | — | transient_artifact | REJECTED | cloud over the candidate in after_primary; confirm shows the meadow at the forest edge unchanged |
| KAND-30 | vegetation_loss_in_grass_or_crop | 643 | 1 | 2022-08-14..2022-08-29 / +100 d | 18.7 | 14.5 | d_ndvi_small_contrast | 0.51 | no | no | 2 | water_change | REJECTED | candidate lies on the open water of a lake near the shore; no slope |

## Cloud proximity of the candidates

Distance from each candidate pixel to the nearest cloud-like scene-classification pixel (SCL 2, 3, 7, 8, 9, 10, 11) in before_primary or after_primary (`cloud_proximity.json`). Pairs are screened for cloud and snow only in the 960 m window around the source event; the outer part of the 2.56 km patch is recorded but not required, and Sen2Cor misses thin cloud and haze edges.

| set | n | within 100 m of a cloud-like pixel | within 300 m |
|---|---:|---:|---:|
| all candidates | 1416 | 18% | 39% |
| top 30 by score | 30 | 87% | 87% |
| top 100 by score | 100 | 76% | 82% |
| top 300 by score | 300 | 48% | 63% |
| rank-1 candidates per search | 118 | 38% | 53% |
| rediscovered known events (reference) | 61 | 16% | 39% |

The score ranking is dominated by cloud and haze edges: the detector was trained on cloud-free windows and extrapolates to extreme log-odds at unmasked cloud borders. Candidate ranking by raw score is therefore not usable until the discovery scan screens the whole patch (or masks a buffer around every cloud-like pixel); this is the first change for the next Pipeline B version, registered before re-running.

## Visual review

Contact sheets `reports/satellite/contact_sheets/candidates_01..05.png`: RGB before_primary, after_primary, after_confirm and ΔNDVI for both pairs, 640 m window, cross = candidate pixel, box = 120 m small window. The reviewer's verdicts and notes are in `reports/satellite/candidate_review.json` (one entry per label; a verdict without a note changes nothing).

## Interpretation and limits

- The top of the score list is dominated by extreme log-odds (the logistic detector extrapolates far outside its training range for water, river-bank and harvest changes); a high score is not evidence of a landslide.
- Persistence separates transient changes (mowing, harvest, moisture, cloud edge) from lasting surface change; a lasting change can still be a clear-cut, construction or a river-bed shift, which only the visual review and later orthophotos or inventories can resolve.
- after_confirm was screened for cloud and snow at the source event, not at the candidate; candidates with cloud at their own position are reported as not assessable rather than scored.
- Candidates are UNVERIFIED by default; LIKELY is a hypothesis for field or orthophoto checking, not a documented event, and nothing here is written to the Pipeline A event tables (write guard).
