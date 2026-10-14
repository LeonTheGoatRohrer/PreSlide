# Held-out rediscovery of known events

For each independence unit a logistic_regression detector is trained on all other units, then every position of the 2560 m patch around each held-out event is scored (sliding windows), local maxima at least 320 m apart are ranked, and a hit is a peak within 160 m of the reported position.

| quantity | value |
|---|---:|
| held-out events | 14 |
| independence units | 12 |
| searched area per event (km²) | 2.56 |
| rediscovered at rank 1 | 0 |
| rediscovered within top 3 | 5 |
| rediscovered within top 5 | 5 |
| rediscovered at any rank | 7 |
| median hit rank | 2.0 |
| median localisation error (m) | 71 |
| false peaks ranked above the hit (mean) | 6.29 |
| peaks per km² (mean) | 3.04 |

Chance reference: a random peak order gives P(rank 1) = 1/peaks per event; mean 1/peaks = 0.225.

The search region is centred on the known event, so this is a localisation test inside a small area, not an unknown-region scan. Peaks that are not the known event are candidate detections for the false-positive analysis; they are NOT labelled as landslides.
