# susceptibility_v02 – Phase 4: bestätigender Test Gorkha → Iburi

**Stand 18.10.2026. Einmal gerechnet, Ausgaben write-once:** `phase4_results.json`, `data/susceptibility_v02/predictions/phase4_predictions.parquet`, `models/susceptibility_v02/phase4_*.joblib`. Iburi ist ab jetzt gesehene Daten. Die Ursachenanalyse (`phase4_cause_analysis.json`) ist explorativ.

## Ergebnis nach der vorab registrierten Regel

| Test | Vergleich auf Iburi | Differenz der AUC | 95 % | 0,625. Perzentil (Bonferroni) | Ergebnis |
|---|---|---|---|---|---|
| **H1-EQ** | Gelände + PGA (Gorkha) − Neigung + PGA | −0,015 | [−0,040; +0,009] | −0,047 | **nicht bestanden** |
| **H2-EQ** | Gelände (Gorkha) − Gelände (Far-Western Nepal) | +0,053 | [+0,031; +0,073] | +0,023 | **bestanden** |
| H1-Regen | – | – | – | – | nicht durchführbar (RER2023 ohne Umriss) |
| H2-Regen | – | – | – | – | nicht durchführbar |

**Schlussregel:** Die Hypothese gilt für einen Auslöser nur, wenn H1 und H2 bestehen. Für Erdbeben ist H1 gescheitert. → **Auslöserspezifische Geländeanfälligkeit ist nicht belegt.** Der Regenarm war nicht testbar. Kein anderes Modell, Merkmal oder Split ersetzt den gescheiterten Test.

Einheiten: Iburi ist ein Ereignis mit 69 5-km-Blöcken (3.177 Positive und 3.177 Hintergrund). Der größte Block hält 11,8 % der Positiven, die Dominanzregel greift also nicht.

## Alle gerechneten Modelle auf Iburi (Training Gorkha; ROC AUC mit 95-%-Block-Bootstrap)

| Modell | AUC | AP (1:1) | Recall in den obersten 20 % | Boyce |
|---|---|---|---|---|
| EQ_TERRAIN_PGA | 0,826 [0,778; 0,869] | 0,779 | 0,678 | −0,49 |
| EQ_TERRAIN | 0,820 [0,764; 0,867] | 0,743 | 0,643 | −0,56 |
| slope_pga_logistic | 0,841 [0,784; 0,891] | 0,811 | 0,711 | 0,84 |
| slope_only | 0,841 [0,797; 0,880] | 0,775 | 0,703 | 0,31 |
| pga_only | 0,681 [0,590; 0,770] | 0,600 | 0,380 | 0,78 |
| EQ_TERRAIN, trainiert auf Far-Western Nepal | 0,767 [0,723; 0,805] | 0,717 | 0,554 | −0,12 |

- **Permutations-Nullreferenz** (500, innerhalb der Blöcke): EQ_TERRAIN_PGA 0,826 gegenüber 95 % Null 0,792; EQ_TERRAIN 0,820 gegenüber 0,787 (beide p = 0,002). Die Modelle trennen über Zufall, aber nicht besser als die Neigung.
- **Sekundär:**
  - Gelände − Neigung: −0,021 [−0,042; −0,004]. Das Geländemodell ist auf Iburi schlechter als die Neigung allein.
  - H4 PGA-Zuwachs: +0,006 [−0,030; +0,045], kein Nutzen belegt.
  - Gelände + PGA − PGA allein: +0,145 [+0,080; +0,212].
- **H3 (Vorzeichen der Hangposition):** TPI-AUC auf Iburi 0,574 [0,531; 0,607] > 0,5. Der Iburi-Teil ist erfüllt und gleichgerichtet mit Gorkha. Der RER2023-Teil ist nicht testbar, H3 bleibt damit unvollständig.
- Die Boyce-Werte der Baumodelle sind negativ, obwohl ihre AUC hoch ist. Das passt zu einer stark gestuften Wertverteilung bei Extrapolation; gedeutet wird das nicht weiter.

## Gegenrichtung Iburi → Gorkha (sekundär, Gorkha in v01 gesehen)

| Modell | AUC (1.262 Blöcke) |
|---|---|
| EQ_TERRAIN_PGA | 0,796 |
| EQ_TERRAIN | **0,502** |
| slope_pga_logistic | 0,855 |
| slope_only | 0,767 |
| pga_only | 0,792 |
| EQ_TERRAIN, trainiert auf Far-Western Nepal | 0,733 |

Alle Kontraste der Gegenrichtung sind negativ außer dem PGA-Zuwachs (+0,295). Das auf Iburi trainierte Geländemodell überträgt auf Gorkha überhaupt nicht.

## Ursachenanalyse (explorativ, nach dem Ergebnis)

- **Wertebereiche überlappen kaum.** Iburi liegt in Hügelland (Höhe der Stichproben im Median 117 m, 99. Perzentil 319 m; Relief im Median 132 m), Gorkha im Hochgebirge (Median 1.874 m, Relief 864 m). Nur 31 % der Iburi-Stichproben liegen im Höhenbereich der Gorkha-Trainingsdaten. Umgekehrt liegen nur 4 % der Gorkha-Stichproben im Höhenbereich von Iburi und 9 % in dessen Reliefbereich. Baummodelle können außerhalb des Trainingsbereichs nicht sinnvoll extrapolieren.
- **Die Neigung überträgt, weil ihre Richtung stabil ist.** Univariate AUC: Gorkha 0,767, Iburi 0,841. Eine logistische Neigungsfunktion braucht keinen überlappenden Wertebereich.
- **PGA trennt auf Iburi schwächer als in Gorkha** (univariat 0,681 gegenüber 0,792). Die ShakeMap von Iburi beruht auf einer Punktquelle, und die PGA-Spanne im Umriss ist eng (log10 1,5–1,8).
- Fazit der Analyse: Das Scheitern von H1 spiegelt vor allem den fehlenden gemeinsamen Geländeraum zweier sehr verschiedener Landschaften. Ob ein Erdbebengelände-Effekt fehlt, lässt sich damit nicht entscheiden. H2 zeigt, dass Erdbebentraining auf Iburi besser trifft als Monsuntraining. Allein ist das keine Bestätigung, und auch dort bleiben beide Modelle unter der Neigung.

## Grenzen

- Ein bestätigendes Testereignis. Positive und Hintergrund stammen aus unterschiedlichen Kartierungen (Iburi: GSI-Luftbildinterpretation, Abriss und Ablagerung gemeinsam kartiert, oberstes Höhendrittel als Ersatz für die Abrisszone).
- PGA ist ein Modellwert.
- 2,6 % des Iburi-Umrisses (Meer) sind vom Hintergrund ausgeschlossen (Amendment 3).
- Die v01-Geländemerkmale waren versetzt (Nachtrag 3); v02 rechnet korrekt.
- Keine Aussage über absolute Gefährdung; Werte sind relative Rangfolgen.
