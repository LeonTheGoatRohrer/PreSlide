# Held-out rediscovery of known events

For each independence unit a logistic_regression detector is trained on all other units, then every position of the 2560 m patch around each held-out event is scored (sliding windows), local maxima at least 320 m apart are ranked, and a hit is a peak within 160 m of the reported position. Since satellite-0.2, peaks within 160 m of any OTHER known V0.4 positive (423 events) are removed from the ranking before scoring: they are documented events, not false peaks and not candidates (the search centre keeps priority).

| quantity | controls only (satellite-0.2, suppression) | stage 5 (no suppression, same model) |
|---|---:|---:|
| held-out events | 129 | 129 |
| independence units | 15 | 15 |
| searched area per event (km²) | 2.56 | 2.56 |
| rediscovered at rank 1 | 11 | 8 |
| rediscovered within top 3 | 28 | 27 |
| rediscovered within top 5 | 38 | 37 |
| rediscovered at any rank | 61 | 61 |
| median hit rank | 4.0 | 4.0 |
| median localisation error (m) | 70 | 70 |
| false peaks ranked above the hit (mean) | 7.70 | 8.09 |
| peaks per km² (mean) | 4.49 | 4.70 |
| peaks removed at other known positives (total) | 70 | — |
| events with another known positive inside the patch | 94 | — |

Chance reference (controls only): a random peak order gives P(rank 1) = 1/peaks per event; mean 1/peaks = 0.110.

The search region is centred on the known event, so this is a localisation test inside a small area, not an unknown-region scan. Peaks that are not the known event are candidate detections for the false-positive analysis; they are NOT labelled as landslides. Candidate validation (persistence, visual review, cloud proximity): `candidate_validation.md`.
