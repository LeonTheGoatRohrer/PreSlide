# PreSlide V0.4 — erweitertes Fall-Kontroll-Experiment

Automatisch erzeugt aus gespeicherten Artefakten (`python -m preslide.v04.report`). Getrennt von V0–V0.3; die eingefrorene V0.3-Baseline ist unverändert.

Präregistrierung: `config/v04.json` SHA-256 `c6d67a854ba78b2b…`, registriert 2026-10-14T13:23:40 UTC, vor jedem Matching-, Wetter- oder Modellergebnis.

## Datenbestand

- Kandidaten Stufe 1 mit sicherem Ereignistag (Tier A): **500** in 48 zeitlichen Episoden; alle 102 V0-Kandidaten reproduziert.
- Vollständige Gruppen (1 Positiv + 5 Kontrollen, Gelände + Wetter): **423** (2538 Proben).
- Zeitqualität der vollständigen Gruppen: {'daypart': 299, 'day': 84, 'clock': 40}.
- Jahre: {'2016': 243, '2017': 4, '2018': 24, '2019': 1, '2020': 26, '2022': 15, '2023': 47, '2024': 50, '2025': 7, '2026': 6}.
- Bundesländer: {'Steiermark': 342, 'Niederoesterreich': 24, 'Vorarlberg': 17, 'Salzburg': 13, 'Kaernten': 11, 'Tirol': 7, 'Oberoesterreich': 5, 'Burgenland': 4}.

### Ausschlüsse nach dem Audit

| Grund | Ereignisse |
|---|---:|
| weather: missing_weather_values | 27 |
| match: insufficient_controls | 26 |
| match: positive_dem_slope_below_minimum | 15 |
| weather: implausible_weather_values | 9 |

Nicht im Hauptbestand (Audit): 222 × Qualitätsstufe 1/B_two_day_window, 79 × Qualitätsstufe 1/C_structured_day_only, 409 × Qualitätsstufe 1/excluded, 323 × Qualitätsstufe 2/A_narrative_day, 15 × Qualitätsstufe 2/B_two_day_window, 65 × Qualitätsstufe 2/excluded.

## Unabhängigkeitseinheiten und Aufteilung

Abhängigkeitsprüfung räumlich-zeitlicher Einheiten: 14 Paare, 90. Perzentil der Regenkorrelation 0.636 (Schwelle 0,5) → abgelehnt; zeitliche Episoden werden verwendet.

| Teil | Ereignisse | Einheiten | zeitl. Episoden | Baseline-Ereignisse |
|---|---:|---:|---:|---:|
| development | 123 | 19 | 24 | 60 |
| sealed_test | 300 | 11 | 12 | 0 |

Größte Einheit: 243 Ereignisse; Einheiten mit 1 Ereignis: 15. Auswertung gewichtet jede Einheit gleich.

## Matchingqualität (Kontrollen)

| Größe | Median | 95 % | Max |
|---|---:|---:|---:|
| distance_to_positive_m | 5725.4 | 9573.4 | 9999.9 |
| slope_difference_deg | 0.9 | 2.6 | 5.0 |
| elevation_difference_m | 28.8 | 88.1 | 149.4 |
| aspect_difference_deg | 8.7 | 24.6 | 44.2 |

## Merkmale und Abdeckung

Zugelassene Tagesprodukte (Pilot, ≥ 95 %): spartacus-v2-1d-1km, snowgrid_cl-v2-1d-1km; nicht zugelassen: winfore-v2-1d-1km.

| Merkmal | Proben vorhanden | Gruppen vollständig | standard. Differenz Positiv − Kontrollen |
|---|---:|---:|---:|
| elevation | 1.00 | 1.00 | -0.033 |
| slope | 1.00 | 1.00 | 0.017 |
| aspect_sin | 1.00 | 1.00 | 0.011 |
| aspect_cos | 1.00 | 1.00 | -0.005 |
| profile_curvature | 1.00 | 1.00 | -0.248 |
| plan_curvature | 1.00 | 1.00 | 0.373 |
| roughness_tri | 1.00 | 1.00 | 0.046 |
| tpi_150m | 1.00 | 1.00 | -0.421 |
| tpi_500m | 1.00 | 1.00 | -0.367 |
| relative_position_500m | 1.00 | 1.00 | -0.159 |
| log10_catchment_m2 | 1.00 | 0.98 | 0.351 |
| twi | 1.00 | 0.98 | 0.320 |
| lc_forest | 1.00 | 1.00 | -0.468 |
| lc_grass_shrub | 1.00 | 1.00 | 0.281 |
| lc_agriculture | 1.00 | 1.00 | 0.245 |
| lc_open_bare | 1.00 | 1.00 | -0.034 |
| lc_artificial_water_other | 1.00 | 1.00 | 0.211 |
| geo_carbonate | 1.00 | 0.98 | -0.171 |
| geo_clastic_rock | 1.00 | 0.98 | -0.046 |
| geo_unconsolidated | 1.00 | 0.98 | 0.028 |
| geo_low_grade_metamorphic | 1.00 | 0.98 | 0.976 |
| geo_crystalline_other | 1.00 | 0.98 | -0.678 |
| rain_sum_1d | 1.00 | 1.00 | -0.042 |
| rain_max_hour_1d | 1.00 | 1.00 | -0.258 |
| temperature_mean_1d | 1.00 | 1.00 | 0.014 |
| rain_sum_3d | 1.00 | 1.00 | 0.003 |
| rain_max_hour_3d | 1.00 | 1.00 | -0.410 |
| temperature_mean_3d | 1.00 | 1.00 | 0.010 |
| rain_sum_7d | 1.00 | 1.00 | 0.079 |
| rain_max_hour_7d | 1.00 | 1.00 | 0.261 |
| temperature_mean_7d | 1.00 | 1.00 | 0.012 |
| rain_sum_14d | 1.00 | 1.00 | 0.099 |
| rain_max_hour_14d | 1.00 | 1.00 | -0.336 |
| temperature_mean_14d | 1.00 | 1.00 | 0.013 |
| rain_sum_30d | 1.00 | 1.00 | 0.105 |
| rain_max_hour_30d | 1.00 | 1.00 | -0.503 |
| temperature_mean_30d | 1.00 | 1.00 | 0.016 |
| rain_sum_60d | 1.00 | 1.00 | 0.027 |
| rain_max_hour_60d | 1.00 | 1.00 | -0.572 |
| temperature_mean_60d | 1.00 | 1.00 | 0.015 |
| rain_since_midnight | 0.45 | 0.45 | 0.030 |
| rain_max_hour_since_midnight | 0.45 | 0.45 | -0.031 |
| rain_3h_before_t0 | 0.41 | 0.41 | 0.040 |
| rain_6h_before_t0 | 0.37 | 0.37 | 0.023 |
| spartacus_rr_90d | 0.99 | 0.93 | -0.055 |
| spartacus_rr_180d | 0.99 | 0.93 | -0.055 |
| swe_last | 0.99 | 0.93 | -0.021 |
| snow_depth_last | 0.99 | 0.93 | -0.017 |
| swe_melt_3d | 0.99 | 0.93 | 0.013 |
| swe_melt_7d | 0.99 | 0.93 | 0.019 |
| swe_melt_14d | 0.99 | 0.93 | -0.009 |

## Entwicklung (gruppierte CV, 5 × 5, nur Entwicklungsbestand)

123 Ereignisse, 19 Einheiten. Median über 5 Wiederholungen (Spannweite).

| Modell | Merkmale | lokale AUC (gew.) | Top-1 (gew.) | lokale AP (gew.) | gepoolte AP |
|---|---|---:|---:|---:|---:|
| Bedingte log. Regression | static | 0.770 (0.732–0.785) | 0.493 | 0.668 | 0.319 |
| Bedingte log. Regression | temporal | 0.554 (0.529–0.570) | 0.236 | 0.467 | 0.190 |
| Bedingte log. Regression | combined | 0.725 (0.682–0.744) | 0.381 | 0.602 | 0.289 |
| Logistische Regression | static | 0.762 (0.752–0.773) | 0.499 | 0.668 | 0.279 |
| Logistische Regression | temporal | 0.484 (0.472–0.548) | 0.175 | 0.410 | 0.175 |
| Logistische Regression | combined | 0.725 (0.718–0.748) | 0.425 | 0.614 | 0.231 |
| Gradient Boosting | static | 0.687 (0.670–0.717) | 0.361 | 0.572 | 0.273 |
| Gradient Boosting | temporal | 0.461 (0.392–0.506) | 0.137 | 0.371 | 0.166 |
| Gradient Boosting | combined | 0.630 (0.599–0.643) | 0.332 | 0.541 | 0.266 |

Zufallsreferenz (zufälliger Rang, gleiche Gewichte): Mittel 0.501, 90 %-Band 0.399–0.603. Label-Permutation (bedingte log. Regression, 100 Ziehungen): static: 90 %-Band 0.353–0.636; temporal: 90 %-Band 0.392–0.625; combined: 90 %-Band 0.378–0.628.

Gepaarter Einheiten-Bootstrap (Wiederholung 1), lokale AUC:

- Bedingte log. Regression, static_minus_temporal: +0.229 [+0.066, +0.407]
- Bedingte log. Regression, static_minus_combined: +0.061 [-0.006, +0.150]
- Bedingte log. Regression, temporal_minus_combined: -0.168 [-0.338, -0.015]
- Logistische Regression, static_minus_temporal: +0.210 [+0.042, +0.382]
- Logistische Regression, static_minus_combined: +0.045 [-0.001, +0.100]
- Logistische Regression, temporal_minus_combined: -0.165 [-0.335, -0.005]
- Gradient Boosting, static_minus_temporal: +0.175 [-0.005, +0.336]
- Gradient Boosting, static_minus_combined: +0.054 [-0.047, +0.154]
- Gradient Boosting, temporal_minus_combined: -0.121 [-0.253, +0.026]

Leave-one-state-out (bedingte log. Regression, nur deskriptiv): Kaernten: n=9, statisch 0.44, zeitlich 0.50, kombiniert 0.49; Niederoesterreich: n=23, statisch 0.88, zeitlich 0.45, kombiniert 0.87; Oberoesterreich: n=4, statisch 0.93, zeitlich 0.47, kombiniert 0.87; Salzburg: n=7, statisch 0.60, zeitlich 0.47, kombiniert 0.48; Steiermark: n=54, statisch 0.80, zeitlich 0.63, kombiniert 0.81; Tirol: n=5, statisch 0.76, zeitlich 0.56, kombiniert 0.60; Vorarlberg: n=17, statisch 0.49, zeitlich 0.69, kombiniert 0.54.

## Versiegelter externer Test (einmalig ausgewertet)

Bewertet 2026-10-14T15:39:41 UTC nach `FREEZE.json`; Prüfungen: {'config': True, 'partition': True, 'dataset': True, 'code': True, 'models': True}. 300 Ereignisse in 11 unabhängigen Einheiten.

**Primärer Endpunkt** (bedingte log. Regression, kombiniert, gewichtete lokale AUC): **0.751** [95 % 0.633–0.866]; Zufall 0,5 (95 %-Quantil der Zufallsreferenz 0.629).
Kombiniert − statisch: +0.049 [-0.003, +0.108].

| Modell | Merkmale | lokale AUC (gew.) | p (≥, Zufall) | Top-1 (gew.) | lokale AP (gew.) | lokale AUC (ungew.) | gepoolte AP |
|---|---|---:|---:|---:|---:|---:|---:|
| Bedingte log. Regression | static | 0.702 | 0.004 | 0.366 | 0.579 | 0.521 | 0.210 |
| Bedingte log. Regression | temporal | 0.604 | 0.100 | 0.157 | 0.445 | 0.566 | 0.205 |
| Bedingte log. Regression | combined | 0.751 | 0.001 | 0.373 | 0.604 | 0.668 | 0.285 |
| Logistische Regression | static | 0.702 | 0.004 | 0.384 | 0.583 | 0.593 | 0.222 |
| Logistische Regression | temporal | 0.667 | 0.016 | 0.250 | 0.500 | 0.587 | 0.189 |
| Logistische Regression | combined | 0.719 | 0.002 | 0.288 | 0.562 | 0.639 | 0.224 |
| Gradient Boosting | static | 0.580 | 0.163 | 0.245 | 0.484 | 0.585 | 0.217 |
| Gradient Boosting | temporal | 0.622 | 0.060 | 0.303 | 0.512 | 0.323 | 0.124 |
| Gradient Boosting | combined | 0.616 | 0.074 | 0.346 | 0.536 | 0.627 | 0.222 |

Gepaarte Bootstrap-Differenzen (Test):

- Bedingte log. Regression, static_minus_temporal: +0.099 [-0.079, +0.270]
- Bedingte log. Regression, static_minus_combined: -0.049 [-0.108, +0.003]
- Bedingte log. Regression, temporal_minus_combined: -0.147 [-0.285, +0.002]
- Logistische Regression, static_minus_temporal: +0.036 [-0.130, +0.209]
- Logistische Regression, static_minus_combined: -0.017 [-0.071, +0.042]
- Logistische Regression, temporal_minus_combined: -0.053 [-0.204, +0.092]
- Gradient Boosting, static_minus_temporal: -0.041 [-0.257, +0.165]
- Gradient Boosting, static_minus_combined: -0.035 [-0.131, +0.073]
- Gradient Boosting, temporal_minus_combined: +0.006 [-0.181, +0.204]

Teilmenge mit bekannter Tageszeit (Test): 281 Ereignisse / 6 Einheiten, kombinierte bed. log. Regression lokale AUC 0.831.

## Worauf sich das finale Modell stützt (bedingte log. Regression, standardisierte Koeffizienten)

Auf allen Entwicklungsdaten gefittet; Vorzeichen = Richtung innerhalb der Gruppe. Keine Kausalaussage.

- static: roughness_tri +0.87, lc_forest -0.69, lc_artificial_water_other +0.66, tpi_150m -0.58, lc_grass_shrub +0.34, elevation -0.32, geo_carbonate -0.31, geo_unconsolidated +0.23
- combined: roughness_tri +0.77, lc_forest -0.69, rain_max_hour_3d -0.68, lc_artificial_water_other +0.66, rain_sum_7d +0.65, rain_3h_before_t0 +0.56, tpi_150m -0.53, log1p_rain_sum_30d_x_log10_catchment_m2 +0.51

## Einordnung

Kontrollen sind Pseudo-Negative. Werte sind Rangvergleiche innerhalb gematchter Gruppen, keine Rutschungswahrscheinlichkeiten. Modellgewichte zeigen, worauf sich ein Modell stützt, nicht Ursachen. Ohne eigene räumliche Prüfung wird keine geografische Übertragbarkeit behauptet.
Der Landbedeckungskontrast (Positive seltener im Wald, häufiger auf Grünland und Siedlungs-/Verkehrsflächen) kann physikalisch und durch Meldebias (an Infrastruktur und Siedlungen werden Ereignisse eher dokumentiert) entstehen; beides lässt sich mit diesen Daten nicht trennen. Gelände- und Positionsmerkmale am Positiv hängen zudem von der Verortungskonvention der Inventarpunkte ab.
