# False-positive analysis (held-out discovery scans)

Every peak above the score threshold that is not the known event is a candidate detection with `validation_status = UNVERIFIED`. Types below are coarse heuristics from the change signature (before-state NDVI, local NDVI/NDWI/brightness contrast) to guide manual inspection; they are not labels.

Candidates: 1484

| heuristic type | count | median score | median distance to nearest known event (m) |
|---|---:|---:|---:|
| change_on_bare_or_built_surface (construction, roads, quarry) | 9 | 6.574 | 821 |
| local_brightening (bare soil, snow remnant, cloud edge) | 3 | 5.552 | 904 |
| other_or_weak | 1265 | 1.894 | 618 |
| vegetation_loss_in_dense_vegetation (forestry or possible undocumented slide) | 146 | 9.345 | 486 |
| vegetation_loss_in_grass_or_crop (harvest, mowing or possible slide) | 33 | 9.030 | 710 |
| water_or_wetness_change | 28 | 19.182 | 504 |

578 candidates lie within 500 m of a known inventory event other than the search centre (possible additional source areas of the same storm, or the same slide at a different pixel).

Next validation steps (none performed automatically): inspect `after_confirm` imagery for persistence, check Sentinel-1 backscatter change, compare with later inventory updates and orthophotos.
