# False-positive analysis (held-out discovery scans)

Every peak above the score threshold that is not the known event is a candidate detection with `validation_status = UNVERIFIED`. Types below are coarse heuristics from the change signature (before-state NDVI, local NDVI/NDWI/brightness contrast) to guide manual inspection; they are not labels. Peaks within the suppression radius of another known V0.4 positive are not listed (documented events).

Candidates: 1416

| heuristic type | count | median score | median distance to nearest known V0.4 positive (m) |
|---|---:|---:|---:|
| change_on_bare_or_built_surface (construction, roads, quarry) | 9 | 6.574 | 821 |
| local_brightening (bare soil, snow remnant, cloud edge) | 3 | 5.552 | 904 |
| other_or_weak | 1205 | 1.877 | 621 |
| vegetation_loss_in_dense_vegetation (forestry or possible undocumented slide) | 138 | 9.332 | 515 |
| vegetation_loss_in_grass_or_crop (harvest, mowing or possible slide) | 33 | 9.030 | 710 |
| water_or_wetness_change | 28 | 19.182 | 504 |

521 candidates lie within 500 m of a known V0.4 positive other than the search centre (possible additional source areas of the same storm, or the same slide at a different pixel).

Validation of the top candidates (persistence in `after_confirm`, visual review): `candidate_validation.md`.
