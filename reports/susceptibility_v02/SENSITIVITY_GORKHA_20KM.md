# susceptibility_v02 – Sensitivität Gorkha mit 20-km-Blöcken (explorativ)

**Stand 18.10.2026. Explorativ: Gorkha ist in v01 gesehen. Vorab registriert (`config/susceptibility_v02.json`, `sensitivity_gorkha_20km`), kein Gate, keine Bestätigung.** Zahlen: `sensitivity_gorkha_20km.json`; Vorhersagen (write-once) `data/susceptibility_v02/predictions/sensitivity_gorkha_oof.parquet`.

## Frage

Wie viel des v01-Vorteils des Geländemodells gegenüber der Neigung innerhalb Gorkhas beruht auf räumlicher Nähe zur Zone starker Erschütterung, und wie viel erklärt die modellierte Erschütterung (PGA)?

## Daten und Vorgehen (exakt wie registriert)

- Stichproben: v01-Gorkha, 24.037 Positive + 24.037 Hintergrund, nur gelesen (Prüfsumme `b1454897…` verifiziert).
- PGA: USGS-ShakeMap `us20002926`, Produkt atlas, Version 1, process_timestamp 2020-06-03T05:37:03, `grid.xml` SHA-256 `3ffbe249…`. log10(PGA in % g), PGA bilinear am 30-m-Zellmittelpunkt (EPSG:32645 → WGS84). 0 Zellen außerhalb des Gitters; der ganze Kartierumriss liegt im Gitter. Die Gitterweite wird aus den Eckkoordinaten berechnet. Der Kopfwert 0,0167° ist gerundet und hätte am Gitterrand etwa 2 km Versatz erzeugt; ein Test deckt das ab.
- Räumliche Block-CV mit 5 Falten, Seed 302, und 1 km Purge; einmal mit 5-km-Blöcken, einmal mit 20-km-Blöcken. Code und Stichproben sind identisch, der Vergleich ist also gepaart.
- Modelle (Hyperparameter aus v01 Amendment 3):
  - EQ_TERRAIN: HGB auf 12 Geländemerkmalen.
  - EQ_TERRAIN_PGA: zusätzlich log10 PGA.
  - slope_only: logistische Regression auf der Neigung.
  - slope_pga_logistic: logistische Regression auf Neigung und PGA.
- Bootstrap über die jeweiligen Blöcke, 2.000 Ziehungen, Seed 303.
- Mindestens-25-Blöcke-Regel: Positive liegen in 575 der 5-km-Blöcke und in 76 der 20-km-Blöcke. Beide Intervalle gelten damit als stabil. Kein Block hält mehr als 20 % der Positiven (größter 20-km-Block: 14,7 %).

## Ergebnisse (ROC AUC, 95-%-Block-Bootstrap)

| Modell | 5-km-Blöcke | 20-km-Blöcke |
|---|---|---|
| EQ_TERRAIN | 0,881 [0,869; 0,892] | 0,876 [0,850; 0,897] |
| EQ_TERRAIN_PGA | 0,928 [0,920; 0,935] | 0,922 [0,905; 0,937] |
| slope_only | 0,757 [0,744; 0,768] | 0,756 [0,730; 0,782] |
| slope_pga_logistic | 0,865 [0,856; 0,875] | 0,867 [0,841; 0,889] |
| **EQ_TERRAIN − slope_only** | **+0,124 [0,113; 0,136]** | **+0,120 [0,096; 0,142]** |
| **EQ_TERRAIN_PGA − slope_pga_logistic** | **+0,062 [0,055; 0,069]** | **+0,055 [0,041; 0,071]** |

Unabhängige Einheiten: Es handelt sich um ein einziges Erdbeben. Die Blöcke sind räumliche Resampling-Einheiten (1.260 bzw. 100 Blöcke mit Proben), keine unabhängigen Ereignisse.

## Vorab festgelegte Deutung, angewendet

1. **Räumliche Nähe:** Die 20-km-Differenz beträgt +0,120. Das sind 97 % der 5-km-Differenz (+0,124) und liegt damit nicht unter der Hälfte. Ihr 95-%-Intervall [0,096; 0,142] schließt die Null nicht ein. → Nach der Regel beruht der Gorkha-Vorteil **nicht** zu einem großen Teil auf räumlicher Nähe. Größere Blöcke verkleinern ihn kaum.
2. **Modellierte Erschütterung:** Mit PGA beträgt der Vorteil bei 5-km-Blöcken +0,062. Das sind 50,1 % des Vorteils ohne PGA. Die registrierte Schwelle „weniger als die Hälfte“ wird damit **knapp nicht erreicht**, die Regel ist formal nicht erfüllt. Sachlich ist das ein Grenzfall: PGA halbiert den Geländevorteil fast genau. Er bleibt aber klar über null (Intervall [0,055; 0,069]). Weder „weitgehend durch Erschütterung erklärt“ noch „durch Erschütterung kaum erklärt“ ist eine belastbare Lesart. Für die Schwelle wurde kein Intervall registriert; es wird keines nachgeschoben.

Zusätzlich, nicht Teil der Regel: Werden die 20-km-Blöcke für beide CVs gemeinsam gezogen, ergibt sich d20 − d5/2 = +0,058 [0,045; 0,070].

## Was das bedeutet und was nicht

- Der Gelände-über-Neigung-Vorteil innerhalb Gorkhas ist gegen größere räumliche Blöcke robust. Etwa die Hälfte davon fängt die modellierte Erschütterung auf. Gelände + PGA trennt innerhalb Gorkhas am besten (0,928).
- Das ist **keine Übertragbarkeit**. v01 zeigte, dass das Gelände zwischen den Inventaren nicht über die Neigung hinaus überträgt. Innerhalb eines Ereignisses können Gelände und PGA weiterhin ereignisspezifische Muster lernen, zum Beispiel Lithologie- oder Hangfußstellvertreter und die Geometrie der Bruchzone. Die bestätigende Prüfung bleibt Gorkha → Iburi (H1/H2).
- PGA ist ein Modellwert (Stationen und Bodenbewegungsmodelle, Version 1 von 2020) und keine Messung am Hang. Ein Teil seines Beitrags kann ebenfalls räumliche Lage abbilden.
- Alle gerechneten Vergleiche stehen oben: 4 Modelle × 2 Blockgrößen, 2 Differenzen je Blockgröße, die beiden Regelprüfungen und die zusätzliche gepaarte Größe. Es wurde nichts weggelassen, nichts nach Ansicht geändert und nichts erneut gerechnet. Der Pilotlauf (50 Ziehungen, ohne Ausgabe) lieferte dieselben Punktwerte.

## Schutztests

`tests/test_susceptibility_v02_pga.py` (24 Tests) prüft:

- Gitterreihenfolge und Gitterweite.
- Bilineare Interpolation an Ebenen und Knoten, NaN außerhalb des Gitters.
- UTM-45N-Orientierung, PGA-Einheiten, log10 ohne Auffüllen.
- GSI-Ebenenrollen, Umriss nur aus einem geschlossenen Ring.
- 20-km-Blöcke schachteln 5-km-Blöcke, ganze Blöcke je Falte, Purge-Anzahl gegen Brute-Force.
- Modelle und Hyperparameter wie registriert, Deutungsregel einschließlich Grenzfall.

`scripts/mutation_check_susceptibility_v02_pga.py` baut 21 Fehler einzeln ein. Jeder lässt Tests scheitern (`mutation_check_pga.json`, PASS).
