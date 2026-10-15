# Generic hard negatives: RANDOM_LANDSCAPE

386 random points for 129 of 129 events (3 per event, 1.5–8 km from the positive, outside the V0.4 exclusion radius of every inventory event floored at 400 m, inside Austria, same before/after acquisitions as the positive, same local cloud/snow rules, no terrain matching). Distance to the positive: median 6132 m; to the nearest inventory record: min 404 m. Random points per event: 2: 1, 3: 128.

Same unit-held-out folds (5 folds × 3 shuffles) and the same change features as the main baseline. Metrics on the matched controls keep their definition (within-group AUC = fraction of controls below the positive) so the two trainings are comparable; positive-vs-random AUC = fraction of the event's random points scored below its positive (chance 0.5); top-1 = positive first among controls + random points.

| model / training negatives | within-group AUC (controls) | unit-weighted | top-1 (controls) | positive vs random AUC | top-1 vs all | random mean p | control mean p | positive mean p | random above median positive |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| logistic_regression/trained_controls_only | 0.785 | 0.852 | 0.556 | 0.665 | 0.357 | 0.425 | 0.354 | 0.601 | 0.258 |
| logistic_regression/trained_with_random_landscape | 0.741 | 0.776 | 0.506 | 0.692 | 0.344 | 0.390 | 0.356 | 0.547 | 0.266 |
| hist_gradient_boosting/trained_controls_only | 0.800 | 0.863 | 0.607 | 0.764 | 0.465 | 0.152 | 0.131 | 0.426 | 0.174 |
| hist_gradient_boosting/trained_with_random_landscape | 0.785 | 0.871 | 0.543 | 0.767 | 0.439 | 0.106 | 0.102 | 0.366 | 0.110 |

Chance: within-group AUC 0.5, positive-vs-random AUC 0.5, top-1 vs all 0.117.

Result: the controls-only detectors already separate positives from random landscape (LR 0.66, HGB 0.76), less well than from matched controls (0.78 / 0.80): generic landscape change scores higher than a matched slope on the same dates. Adding the random points to training moves positive-vs-random to 0.69 / 0.77 and the control metric to 0.74 / 0.79; with 15 independence units and three fold shuffles these differences are within the fold-to-fold spread (per-seed values in the JSON) — no established benefit, a small cost for the linear model on matched controls.

Reading: `trained_controls_only` scores the random points with a model that never saw any; if ordinary landscape receives event-like scores, the detector has learned "reported slope vs matched slope" rather than "landslide vs landscape". `trained_with_random_landscape` adds them as label 0; a drop in the control metrics would mean the hard negatives cost discrimination among matched slopes, a rise in positive-vs-random that they help against generic change. Held-out rediscovery with the hard-negative detector: `heldout_discovery_results.md` (third column, if run).

## Logistic-regression coefficients with random landscape (standardised, full data; association, not causation)

| feature | coefficient |
|---|---:|
| d_nbr_core_std | -1.494 |
| d_ndwi_small_contrast | +1.337 |
| before_bsi_core_mean | +1.276 |
| d_bsi_core_std | +1.149 |
| d_nbr_ring_frac | -1.043 |
| d_nbr_small_contrast | +0.979 |
| before_ndvi_core_mean | +0.936 |
| d_bsi_small_contrast | -0.914 |
| d_ndvi_core_std | +0.879 |
| d_nbr_core_frac | -0.852 |
| d_bsi_contrast | +0.828 |
| before_ndvi_contrast | -0.796 |
| d_ndwi_contrast | -0.786 |
| d_nbr_ring_mean | -0.709 |
| before_bsi_contrast | -0.635 |
