# Satellite dataset summary (Pipeline B)

Configuration `config/satellite.json` version satellite-0.1. Source positives: V0.4 run (read only). Pipeline B uses post-event imagery and is isolated from the precursor model (Pipeline A); see tests/test_satellite.py.

## Eligibility

| Events screened (2018+ positives) | 59 |
|---|---:|
| usable (before + after pair found) | 14 |
| excluded: position_coarse | 39 |
| excluded: seasonal_gap_gt_90d | 4 |
| excluded: no_usable_before_pair_for_group | 1 |
| excluded: too_few_controls_on_both_acquisitions | 1 |

## Acquisition timing of usable pairs

| quantity | median | min | max |
|---|---:|---:|---:|
| days before event (before_primary) | -12 | -29 | -1 |
| days after event (after_primary) | 12 | 4 | 56 |
| candidates screened per event | 18 | 8 | 59 |
| before patch cloud fraction | 0.000 | 0.000 | 0.140 |
| after patch cloud fraction | 0.000 | 0.000 | 0.080 |
| before snow fraction | 0.000 | 0.000 | 0.000 |
| after snow fraction | 0.000 | 0.000 | 0.000 |

Usable events by year: {'2018': 4, '2020': 1, '2022': 1, '2023': 2, '2024': 2, '2025': 1, '2026': 3}
by state: {'Steiermark': 7, 'Vorarlberg': 2, 'Niederoesterreich': 2, 'Oberoesterreich': 1, 'Tirol': 1, 'Burgenland': 1}
by process: {'Lockergesteinsrutschung': 7, 'Hangmure': 4, 'Hangmure bis Lockergesteinsrutschung': 3}
independence units: 12

## Training table

| samples | 79 |
|---|---:|
| groups (1 positive + 4-5 controls on the same acquisitions) | 14 |
| groups with all 5 controls | 9 |
| independence units | 12 |
| incomplete groups dropped | 0 |
| sample failures | 0 |
| patches with estimated co-registration shift > 1.0 px | 0 |

Patch: 2560 m × 2560 m at 10 m (256 px); windows small 120 m, core 320 m, ring to 960 m.
Positives by V0.4 partition: {'development': 10, 'sealed_test': 4} (the V0.4 sealed test is not a Pipeline B test; Pipeline B uses its own unit holdout).

Negatives are the matched V0.4 controls (pseudo-negatives: no documented event, matched terrain, same acquisitions). They are hard negatives for terrain and for scene-wide temporal change, but they do not deliberately sample forestry, construction or river change; those false-positive types are examined in the discovery scan instead.

Contact sheets (anonymised labels SAT-xx): `reports/satellite/contact_sheets/`; the label ↔ event mapping is local only.
