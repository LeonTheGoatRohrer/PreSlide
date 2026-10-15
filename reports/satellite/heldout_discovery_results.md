# Held-out rediscovery of known events

For each independence unit a logistic_regression detector is trained on all other units, then every position of the 2560 m patch around each held-out event is scored (sliding windows), local maxima at least 320 m apart are ranked, and a hit is a peak within 160 m of the reported position. Since satellite-0.2, peaks within 160 m of any OTHER known V0.4 positive (423 events) are removed from the ranking before scoring: they are documented events, not false peaks and not candidates (the search centre keeps priority).

Since satellite-0.3 the whole patch is cloud-screened: every pixel within 100 m of a cloud-like SCL pixel (classes [2, 3, 7, 8, 9, 10, 11]) or an NDSI-snow pixel in either image is removed from the valid mask, and a position is scored only if its 320 m core keeps >= 90% and its ring >= 80% valid pixels. The detector and the training table are unchanged (trained without the buffer; `training_buffer_diagnostic.json` records what the buffer would have removed from the training windows). The searched area is therefore smaller than the nominal patch; an event whose own centre is not scorable cannot be rediscovered.

| quantity | controls only (satellite-0.3, 100 m cloud buffer, suppression) | satellite-0.2 (no buffer, suppression, same model) | stage 5 (no suppression, no buffer) | controls + RANDOM_LANDSCAPE (satellite-0.2, no buffer) |
|---|---:|---:|---:|---:|
| held-out events | 129 | 129 | 129 | 129 |
| independence units | 15 | 15 | 15 | 15 |
| searched area per event (km²) | 2.56 | 2.56 | 2.56 | 2.56 |
| rediscovered at rank 1 | 7 | 11 | 8 | 8 |
| rediscovered within top 3 | 22 | 28 | 27 | 24 |
| rediscovered within top 5 | 27 | 38 | 37 | 36 |
| rediscovered at any rank | 40 | 61 | 61 | 63 |
| median hit rank | 3.0 | 4.0 | 4.0 | 5.0 |
| median localisation error (m) | 70 | 70 | 70 | 92 |
| false peaks ranked above the hit (mean) | 5.97 | 7.70 | 8.09 | 8.47 |
| peaks per km² (mean) | 3.27 | 4.49 | 4.70 | 4.79 |
| peaks removed at other known positives (total) | 31 | 70 | — | 88 |
| events with another known positive inside the patch | 94 | 94 | — | 94 |
| cloud buffer (m) | 100 | 0 | 0 | 0 |
| patch fraction removed by the buffer (mean) | 0.109 | — | — | — |
| scorable positions inside the margin (mean) | 0.678 | — | — | — |
| scorable area per event (km², mean) | 1.74 | — | — | — |
| peaks per scorable km² (pooled over events) | 4.82 | — | — | — |
| events whose centre is not scorable | 45 | — | — | — |
| rediscovered at any rank, centre scorable only (conditional) | 38 of 84 | — | — | — |
| rediscovered at rank 1, centre scorable only (conditional) | 7 of 84 | — | — | — |

Training-window diagnostic (724 training samples, features NOT recomputed): with the buffer the valid core fraction would be median 1.000 (min 0.000), the ring fraction median 0.965 (min 0.093); 459 samples would lose at least one window pixel and 191 (45 positives) would not pass the discovery position rule. The detector scores buffered maps with features learned on unbuffered windows; this mismatch is reported, not corrected.

Chance reference (controls only): a random peak order gives P(rank 1) = 1/peaks per event; mean 1/peaks = 0.199.

The search region is centred on the known event, so this is a localisation test inside a small area, not an unknown-region scan. Peaks that are not the known event are candidate detections for the false-positive analysis; they are NOT labelled as landslides. Candidate validation (persistence, visual review, cloud proximity): `candidate_validation.md`.
