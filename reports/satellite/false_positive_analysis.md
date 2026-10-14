# False-positive analysis (held-out discovery scans)

Every peak above the score threshold that is not the known event is a candidate detection with `validation_status = UNVERIFIED`. Types below are coarse heuristics from the change signature (before-state NDVI, local NDVI/NDWI/brightness contrast) to guide manual inspection; they are not labels.

Candidates: 102

| heuristic type | count | median score | median distance to nearest known event (m) |
|---|---:|---:|---:|
| change_on_bare_or_built_surface (construction, roads, quarry) | 1 | 7.045 | 363 |
| other_or_weak | 74 | 2.904 | 710 |
| vegetation_loss_in_dense_vegetation (forestry or possible undocumented slide) | 14 | 11.362 | 632 |
| vegetation_loss_in_grass_or_crop (harvest, mowing or possible slide) | 10 | 10.596 | 556 |
| water_or_wetness_change | 3 | 33.805 | 856 |

24 candidates lie within 500 m of a known inventory event other than the search centre (possible additional source areas of the same storm, or the same slide at a different pixel).

Next validation steps (none performed automatically): inspect `after_confirm` imagery for persistence, check Sentinel-1 backscatter change, compare with later inventory updates and orthophotos.
