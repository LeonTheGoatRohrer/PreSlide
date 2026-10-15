# Satellite dataset summary (Pipeline B)

Configuration `config/satellite.json` version satellite-0.1. Source positives: V0.4 run (read only). Pipeline B uses post-event imagery and is isolated from the precursor model (Pipeline A); see tests/test_satellite.py.

## Eligibility

| Events screened (2018+ positives) | 176 |
|---|---:|
| usable (before + after pair found) | 129 |
| excluded: position_coarse | 39 |
| excluded: seasonal_gap_gt_90d | 5 |
| excluded: too_few_controls_on_both_acquisitions | 2 |
| excluded: no_usable_before_pair_for_group | 1 |

## Acquisition timing of usable pairs

| quantity | median | min | max |
|---|---:|---:|---:|
| days before event (before_primary) | -9 | -40 | -1 |
| days after event (after_primary) | 9 | 1 | 61 |
| candidates screened per event | 14 | 4 | 59 |
| before patch cloud fraction | 0.000 | 0.000 | 0.322 |
| after patch cloud fraction | 0.000 | 0.000 | 0.187 |
| before snow fraction | 0.000 | 0.000 | 0.000 |
| after snow fraction | 0.000 | 0.000 | 0.000 |

Usable events by year: {'2018': 21, '2020': 26, '2022': 11, '2023': 23, '2024': 37, '2025': 7, '2026': 4}
by state: {'Steiermark': 78, 'Niederoesterreich': 18, 'Vorarlberg': 14, 'Salzburg': 8, 'Kaernten': 6, 'Oberoesterreich': 2, 'Burgenland': 2, 'Tirol': 1}
by process: {'Lockergesteinsrutschung': 84, 'Hangmure': 26, 'Hangmure bis Lockergesteinsrutschung': 16, 'Hangmure und Lockergesteinsrutschung': 3}
independence units: 15

## Training table

| samples | 724 |
|---|---:|
| groups (1 positive + 4-5 controls on the same acquisitions) | 129 |
| groups with all 5 controls | 79 |
| independence units | 15 |
| incomplete groups dropped | 0 |
| sample failures | 0 |
| patches with estimated co-registration shift > 1.0 px | 0 |

Patch: 2560 m × 2560 m at 10 m (256 px); windows small 120 m, core 320 m, ring to 960 m.
Positives by V0.4 partition: {'development': 78, 'sealed_test': 51} (the V0.4 sealed test is not a Pipeline B test; Pipeline B uses its own unit holdout).

Negatives are the matched V0.4 controls (pseudo-negatives: no documented event, matched terrain, same acquisitions). They are hard negatives for terrain and for scene-wide temporal change, but they do not deliberately sample forestry, construction or river change; those false-positive types are examined in the discovery scan instead.

Contact sheets (anonymised labels SAT-xx): `reports/satellite/contact_sheets/`; the label ↔ event mapping is local only.
