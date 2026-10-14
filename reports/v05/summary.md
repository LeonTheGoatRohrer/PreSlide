# PreSlide V0.5 — Nachbarhang-Rangfolge gegen zehn ungematchte Umgebungshänge

**Explorative, gruppiert kreuzvalidierte Studie auf bereits gesehenen Ereignissen. Kein neuer unabhängiger Test.** Plan: `reports/weiterentwicklung_2026-10-14/V05_NACHBARHANG_PLAN.md`; eingefrorene Regeln: `config/v05.json` (Präregistrierung `reports/v05/PREREGISTRATION.json`); Kohorte und CV-Zuordnung vor jedem Modell eingefroren (`reports/v05/COHORT_FREEZE.json`). Alle Zahlen stammen aus `reports/v05/cv_results.json`.

## Fragestellung

Kann ein Modell mit Information vor t0 den dokumentiert betroffenen Hang höher einordnen als zehn flächengleichmäßig gezogene, **nicht** nach Gelände gematchte Hangpunkte 750 m–10 km um ihn? Das ist eine andere, leichtere Aufgabe als in V0–V0.4 (gematchte Kontrollen). Eine höhere V0.5-AUC ist kein besseres Modell für die V0.4-Frage. Kontrollen sind Pseudo-Negative ohne dokumentierte Rutschung; Modellwerte sind relative Ränge, keine Rutschungswahrscheinlichkeiten.

## Bestand

- Positive: 423 V0.4-Ereignisse (unverändertes t0). Pools: 423 geprüft, alle Ringpunkte exakt aus dem V0.4-Seed reproduziert; Inventar- und Grenzflags durch Neuberechnung bestätigt (Abweichungen: 0 / 0).
- Kontrollauswahl: 423 von 423 Ereignissen mit zehn wählbaren Kontrollen (Ausschlüsse bei der Auswahl: 0).
- Nach Umweltdaten: **418 Ereignisgruppen, 4598 Proben, 29 Abhängigkeitseinheiten** (V0.4-Einheiten). Ausschlüsse: weather: implausible_weather_values 4, static: static_matching_elevation_check 1.
- Kontrollabstand zum Positiv: 0,75–2 km 62, 2–5 km 919, 5–10 km 3199 (flächengleichmäßig).
- Nähe-Audit (< 1 km, verschiedene Gruppen): positiv–positiv 11571 (einheitsübergreifend 0), positiv–Kontrolle 698 (78), Kontrolle–Kontrolle 57570 (5939). Deshalb räumliche Trainingsbereinigung je Fold.

Räumlich bereinigte CV: 5 Folds × 5 Wiederholungen. Durchführbar: **ja**. Trainingsgruppen nach Bereinigung je Fold 36–405 (ungepurgt 113–412), Trainingseinheiten 15–22, minimaler Restabstand Training–Prüfung 1.053 km.

## Primärer Endpunkt

Bedingte logistische Regression, kombiniert, räumlich bereinigte CV, über Einheiten gleich gewichtete lokale AUC: **Median 0.851** (Spannweite der fünf Wiederholungen 0.835–0.863; Bootstrap Wiederholung 1 [0.762; 0.897]). Zufall 0,5; Neigungsregel ohne Fit 0.572.

**Hauptvergleich kombiniert − statisch:** je Wiederholung -0.023, -0.016, -0.022, -0.003, -0.020; Bootstrap (Wdh. 1) -0.023 [-0.079; 0.019], Anteil > 0: 0.186.

## Alle Modelle (räumlich bereinigt; Median über 5 Wiederholungen, Einheiten gleich gewichtet)

| Modell | Merkmale | lokale AUC | Top-1 | Top-3 | mittl. Rang | MRR | lokale AUC je Ereignis | gepoolte AP |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Bedingte log. Regression | kombiniert | 0.851 | 0.413 | 0.784 | 2.49 | 0.629 | 0.783 | 0.198 |
| Bedingte log. Regression | Gelände/Landbedeckung/Geologie | 0.865 | 0.375 | 0.845 | 2.35 | 0.606 | 0.690 | 0.159 |
| Bedingte log. Regression | Wetter | 0.719 | 0.287 | 0.578 | 3.81 | 0.484 | 0.753 | 0.175 |
| Gradient Boosting | kombiniert | 0.798 | 0.397 | 0.715 | 3.02 | 0.573 | 0.790 | 0.232 |
| Gradient Boosting | Gelände/Landbedeckung/Geologie | 0.794 | 0.376 | 0.681 | 3.06 | 0.566 | 0.707 | 0.186 |
| Gradient Boosting | Wetter | 0.658 | 0.187 | 0.461 | 4.42 | 0.380 | 0.649 | 0.113 |
| Referenz | Neigung höher = höherer Rang | 0.572 | 0.158 | 0.258 | 5.28 | 0.324 | 0.548 | 0.092 |
| Zufall | analytisch | 0.500 | 0.091 | 0.273 | 6.00 | 0.275 | 0.500 | 0.091 |

Ungepurgte Sensitivität (gleiche Folds, ersetzt die Hauptauswertung nicht): Bedingte log. Regression kombiniert 0.863; Bedingte log. Regression Gelände/Landbedeckung/Geologie 0.873; Bedingte log. Regression Wetter 0.726; Gradient Boosting kombiniert 0.836; Gradient Boosting Gelände/Landbedeckung/Geologie 0.837; Gradient Boosting Wetter 0.707.

Gepaarte Bootstrapdifferenzen (Wdh. 1, 2000 Einheiten-Ziehungen, lokale AUC): Bedingte log. Regression: kombiniert − statisch -0.023 [-0.079; 0.019], statisch − Neigungsregel 0.286; Gradient Boosting: kombiniert − statisch 0.016 [-0.061; 0.095], statisch − Neigungsregel 0.217.

## Diagnosen (registriert, explorativ)

- **Ohne Landbedeckung** (bed. Regression kombiniert, Wdh. 1): 0.812 statt 0.835 (Differenz -0.023).
- **Stanz-Einheit** (243 Ereignisse, `B_2016-07-25_1200667_001`), kombiniert: alle 0.835, ohne Stanz 0.836, nur Stanz 0.797; statisch ohne Stanz 0.866.
- **Kontrollvarianten** (gemeinsame Kohorte 418 Ereignisse, 29 Einheiten, Wdh. 1, gleiche Bereinigung):
  - 5 gematchte V0.4-Kontrollen: statisch 0.705, kombiniert 0.685 (Δ -0.020); Top-1 kombiniert 0.313 (Zufall 0.167).
  - erste 5 ungematchte: statisch 0.864, kombiniert 0.834 (Δ -0.030); Top-1 kombiniert 0.605 (Zufall 0.167).
  - 10 ungematchte: statisch 0.862, kombiniert 0.832 (Δ -0.031); Top-1 kombiniert 0.368 (Zufall 0.091).
- **Verteilungen** Positiv vs. Kontrolle: Neigung Median 20.3° vs. 19.2°; Höhe 869 vs. 1054 m; Wald 0.471 vs. 0.764; Grünland/Strauch 0.292 vs. 0.143; Siedlung/Wasser/Sonstiges 0.048 vs. 0.016.
- **Indirekte Hinweise:** abgeschnittenes Einzugsgebiet Positiv 0.002 vs. Kontrolle 0.000; fehlende Werte (Anteil) log10_catchment_m2 0.002/0.000, twi 0.002/0.000, geo_carbonate 0.000/0.001, geo_clastic_rock 0.000/0.001, geo_unconsolidated 0.000/0.001, geo_low_grade_metamorphic 0.000/0.001, geo_crystalline_other 0.000/0.001, rain_since_midnight 0.199/0.199, rain_max_hour_since_midnight 0.199/0.199, rain_3h_before_t0 0.208/0.208, rain_6h_before_t0 0.222/0.222, spartacus_rr_90d 0.002/0.005, spartacus_rr_180d 0.002/0.005, swe_last 0.002/0.005, snow_depth_last 0.002/0.005, swe_melt_3d 0.002/0.005, swe_melt_7d 0.002/0.005, swe_melt_14d 0.002/0.005. Diese Flags sind keine Prädiktoren.
- **Teilmengen nach Erhebungsart** (kombiniert, Wdh. 1): Auswertung WebInfo: 0.770 (27 Ereignisse/10 Einheiten); Auswertung WebInfo; Auswertung Einzeldokument: 0.813 (69 Ereignisse/18 Einheiten); Ferndiagnose - SatOpt; Gelaendeerhebung - Detaildiagnose: 0.700 (2 Ereignisse/1 Einheiten); Ferndiagnose - SatOpt; Gelaendeerhebung - Detaildiagnose; Auswertung WebInfo: 0.950 (2 Ereignisse/1 Einheiten); Ferndiagnose - SatOpt; Gelaendeerhebung - Ferndiagnose: 0.850 (2 Ereignisse/1 Einheiten); Ferndiagnose - SatOpt; Gelaendeerhebung - Ferndiagnose; Auswertung WebInfo: 0.967 (3 Ereignisse/1 Einheiten); Gelaendeerhebung - Detaildiagnose: 0.814 (257 Ereignisse/6 Einheiten); Gelaendeerhebung - Detaildiagnose; Ferndiagnose - perspekt. Luftbilder: 0.800 (10 Ereignisse/1 Einheiten); Gelaendeerhebung - Detaildiagnose; Auswertung WebInfo; Auswertung Einzeldokument: 0.750 (2 Ereignisse/1 Einheiten); Gelaendeerhebung - Detaildiagnose; Auswertung muendlicher Mitteilung: 0.929 (7 Ereignisse/1 Einheiten); Gelaendeerhebung - Ferndiagnose: 0.833 (9 Ereignisse/2 Einheiten); Gelaendeerhebung - Ferndiagnose; Auswertung muendlicher Mitteilung: 0.500 (1 Ereignisse/1 Einheiten); Gelaendeerhebung - Grobdiagnose: 0.759 (27 Ereignisse/4 Einheiten).
- **Nach Positionskategorie:** Lage genau (5-20m): 0.809 (58/16); Lage relativ genau (20-100m): 0.783 (46/16); Lage sehr genau / sehr sicher (0-5m): 0.814 (314/8).
- Straßen-/Siedlungsnähe: nicht abgerufen (optional, hätte V0.5 blockiert; moderne Karten wären kein damaliger Stand).

**Woran sich das kombinierte lineare Modell auf allen Daten am stärksten stützt** (standardisierte Koeffizienten; keine Validierungsleistung, keine Kausalität): elevation -1.32, rain_max_hour_3d -1.02, rain_sum_30d +0.90, twi -0.73, log1p_rain_sum_3d_x_slope +0.70, rain_sum_7d +0.64, temperature_mean_1d +0.62, rain_sum_14d +0.60.

## Einordnung

**Kein belegter Wetterzusatznutzen:** Beim Primärmodell ist kombiniert − statisch in allen fünf Wiederholungen negativ (Bootstrap-Intervall schließt 0 ein); beim Gradient Boosting leicht positiv mit Intervall um 0. Die Wetter-allein-Variante liegt deutlich über Zufall, ist hier aber **kein reines Wettersignal**: Positive liegen im Median 186 m tiefer als die Kontrollen, und INCA-Temperatur und -Niederschlag sind höhen- und lageabhängig (1-km-Raster, Kontrollen meist 5–10 km entfernt). Sie kodieren daher teilweise Gelände und Lage.

**Die Trennung stützt sich auf Höhe/Lage und Landbedeckung, nicht auf Steilheit:** Die Neigungsregel liegt nur bei 0.572; gemeldete Hänge liegen tiefer und seltener im Wald als der flächengleichmäßige Hintergrund. Mit gematchten Kontrollen (Variante a) erreicht dieselbe Modellklasse auf derselben Kohorte nur 0.705. Der V0.5-Wert misst damit vor allem, wie stark sich gemeldete Hänge vom lokalen Hintergrund unterscheiden — ein Gemisch aus Anfälligkeit und Erfassungswahrscheinlichkeit (Talnähe, Siedlungen, Straßen).

Die Werte beantworten nur, wie gut vorhandene Information den gemeldeten Hang von einer breiteren lokalen Hintergrundverteilung trennt. Sie enthalten Gelände- und Landbedeckungsunterschiede, die teilweise Meldebias (Erfassung an Straßen/Siedlungen, im Offenland) sein können. Der Wetterzusatznutzen ist nur über den Vergleich kombiniert − statisch zu beurteilen, nicht über den Abstand zum Zufall. Dieselben Ereignisse wurden in V0.4 bereits betrachtet; Wiederholungen und Bootstrap sind keine unabhängigen Bestätigungen. Eine Bestätigung braucht ungesehene Abhängigkeitseinheiten und ein eigenes Protokoll.

Ausschlusszonen beruhen auf dem gesamten Inventarstand (auch späteren Ereignissen): retrospektive Auswahlregel, keine Simulation eines damals verfügbaren Inventars. CORINE-Vintage-Regel wie V0.4; tatsächliche historische Verfügbarkeit nicht belegt.
