# susceptibility_v01 – Phase 4: Gate nicht bestanden, Ursachenanalyse

**Stand: 18.10.2026.** Grundlage: `phase4_loio_results.json` (registriertes Primärdesign, einmal gerechnet), `phase5_blockcv_results.json` (registriertes Sekundärdesign, nach dem Gate als Diagnose gerechnet), `phase4_cause_analysis.json` (explorativ). Alle Werte sind Rangmaße einer Presence-Background-Stichprobe im Verhältnis 1 : 1, keine Wahrscheinlichkeiten. Intervalle: Block-Bootstrap über 5-km-Blöcke (2.000 Wiederholungen).

## Gate

Registrierte Regel (Amendment 3): Untergrenze des 95-%-Intervalls von [mittlere AUC (Primärmodell) − mittlere AUC (Neigung allein)] über die beiden Hold-out-Inventare > 0.

| | Wert |
|---|---|
| Primärmodell Histogram Gradient Boosting, mittlere AUC | 0,715 [0,702; 0,729] |
| Neigung allein, mittlere AUC | 0,709 [0,696; 0,722] |
| **Differenz** | **+0,006 [−0,005; +0,017]** |
| **Gate** | **nicht bestanden** |

Das Modell liegt in beiden Richtungen deutlich über Zufall (Permutationsnull innerhalb der Blöcke, p = 0,002), aber nicht belegbar über der Neigung allein.

## Ergebnisse je Richtung (Leave-one-inventory-out)

| Test-Inventar (trainiert auf) | unabhängige Einheiten | Neigung allein | Primärmodell | Differenz [95 %] |
|---|---:|---:|---:|---:|
| Far-Western Nepal (Gorkha) | 303 Blöcke, 1.557 + 1.557 | 0,657 | 0,680 | +0,023 [+0,002; +0,042] |
| Gorkha (Far-Western Nepal) | 1.260 Blöcke, 24.037 + 24.037 | 0,761 | 0,751 | −0,010 [−0,021; +0,001] |

Alle gerechneten Vergleiche (7 Bewertungen × 2 Richtungen = 14) stehen in `phase4_loio_results.json`. Explorativ und ausdrücklich **nicht** als Ersatz für das Primärmodell: Der Random Forest erreicht im Mittel 0,728 (in beiden Richtungen +0,02 über der Neigung). Er war nicht als Primärmodell registriert; ein Wechsel nach Ansicht der Ergebnisse wäre Modellauswahl am Test.

Höhe allein ist in beiden Richtungen schlechter als Zufall oder kaum besser (0,471 und 0,564). Die Höhenverteilung der Rutschungen ist zwischen den Regionen nicht übertragbar.

## Ursachenanalyse (explorativ)

1. **Innerhalb eines Inventars trägt das Gelände mehr als die Neigung, zwischen den Inventaren kaum.** Räumliche Block-Kreuzvalidierung (5 Falten, 5-km-Blöcke, 1 km Abstand):
   - Gorkha: Modell 0,881 gegenüber Neigung 0,759, Differenz +0,122 [0,111; 0,134].
   - Far-Western Nepal: 0,677 gegenüber 0,655, Differenz +0,022 [−0,001; +0,044], kein belegter Vorteil.

   Der Gorkha-Wert stammt aus **einem** Erdbeben. Die Rutschungen bündeln sich dort im Bereich starker Erschütterung, auf größerer Skala als die 5-km-Blöcke. Das Modell kann also auch lernen, *wo* die Erschütterung stark war (über Höhe und Relief), statt allgemeine Anfälligkeit. Dafür spricht, dass Höhe in der Gorkha-Permutationswichtigkeit weit oben steht, während Höhe allein zwischen den Regionen nicht trägt.
2. **Die Hangposition kehrt ihr Vorzeichen um.** Gorkha-Anrissflächen liegen kammnäher (TPI-Median +7,3 m, univariate AUC 0,568), die Monsunrutschungen in Far-Western Nepal hangabwärts (−4,6 m, AUC 0,461). Der Feuchteindex TWI trennt in Gorkha deutlich (AUC 0,347, also trockenere, konvexe Lagen), in Far-Western Nepal kaum (0,455). Das passt zum bekannten Unterschied zwischen erdbebenbedingten Rutschungen (topographische Verstärkung an Graten) und regenbedingten Rutschungen (Hangfuß, Wasser). Ein über die Auslöser gemeinsames Geländemodell überträgt daher im Wesentlichen nur die Neigung und die Rauigkeit (TRI: univariate AUC 0,656 bzw. 0,768 in beiden Regionen gleichsinnig).
3. **Positive sind unterschiedlich definiert.** Gorkha liefert Anrissflächen, Far-Western Nepal nur Gesamtpolygone (Ersatzregel: oberstes Höhendrittel). Nach Amendment 1 bleiben in Far-Western Nepal nur 1.557 datierte Positive, überwiegend große Rutschungen (Median 7.263 m²).
4. **Die Verteilungen verschieben sich.** Positive sind in Gorkha steiler (Median 38,2° gegenüber 33,5°) und liegen in höherem Relief (974 m gegenüber 794 m je km). Der Hintergrund ist dagegen in beiden Regionen ähnlich.
5. **Kein Hinweis auf einen technischen Fehler.** Die Neigungs-Baseline liefert in beiden Richtungen plausible Werte und dieselbe Orientierung. Die Stichprobenverifikation (Puffer, Abstand, Umriss, Neulauf identisch) ist bestanden. 30 eingebaute Fehler werden von den Tests erkannt.

## Konsequenz nach Plan

- **Kein Ausbau.** Die Phasen 6–14 (Quality/Diversity, Modell B, Raster, API, Karte, Nachbarschaftstest, Laufweg, Erklärbarkeit) wurden **nicht** ausgeführt; die Oberfläche bleibt unverändert. Die Ergebnisse oben sind die vollständige Auswertung von susceptibility_v01.
- Metriken, Splits, Seeds, Filter und Primärmodell bleiben unverändert. Die Phase-4-Ergebnisse sind gesehen. Jede neue Variante (zum Beispiel getrennte Modelle je Auslöser, PGA als Merkmal für Gorkha, weitere Regeninventare) ist eine **neue Version** mit eigener Vorregistrierung.
- Modell-B-Gate (Phase 7) wurde nicht formal geprüft. Nach der Vorregistrierung wäre es ohnehin nicht bestanden worden: Mit Gorkha liegt genau ein tagesgenau datiertes Ereignis vor, Far-Western Nepal hat nur Jahresdaten.
- Südtirol bleibt versiegelt; Phase 15 braucht ein eingefrorenes Modell, das dieses Gate bestanden hat, und die ausdrückliche Freigabe.

## Mögliche nächste Versionen (Entscheidung des Nutzers)

1. **Auslöserspezifische Modelle** mit vorab registrierter Hypothese (Erdbeben: Gelände + PGA; Regen: Gelände). Dazu braucht es je Auslöser mindestens zwei Inventare: Regen mit RER2023, sobald ein Kartierumriss vorliegt; Erdbeben mit Iburi (Kandidat geladen).
2. **RER2023-Umriss anfragen** (Autoren oder Region Emilia-Romagna). Damit gäbe es ein zweites Regeninventar außerhalb Nepals.
3. **Bewertung des Erschütterungs-Stellvertreters:** In Gorkha die Block-CV mit größeren Blöcken (zum Beispiel 20 km) als vorab registrierte Sensitivität. Damit ließe sich prüfen, wie viel des +0,12-Vorteils räumliche Nähe ist.
