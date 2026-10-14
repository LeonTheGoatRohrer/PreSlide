# PreSlide V0.5 — Nachbarhang-Rangfolge: ergänzter Plan und vorab festzulegende Regeln

Stand: 14.10.2026. **Überarbeiteter Entwurf, keine Präregistrierung und kein gestartetes Experiment.** Der Nutzer hat die Begutachtung und Ergänzung des Plans autorisiert. Die Implementierung und das Einfrieren einer ausführbaren Konfiguration sind damit noch nicht gestartet.

Der übermittelte Entwurf endet bei der Überschrift von Abschnitt 5 und verweist auf einen dort noch fehlenden Abschnitt 6. Dieses Dokument übernimmt die Grundidee und vervollständigt die Regeln. Vor Umsetzung werden sämtliche Regeln als `config/v05.json` eingefroren (SHA-256 in `reports/v05/PREREGISTRATION.json`), bevor neue V0.5-Kontrollen, Merkmale oder Modelle berechnet werden. Geprüft wurden bisher nur bereits vorhandene V0.4-Artefakte und der Code.

## 1. Forschungsfrage und tatsächliche Aussage

> Kann ein Modell anhand von Informationen vor dem konservativen Ereigniszeitpunkt t0 den dokumentiert betroffenen Hang höher bewerten als zehn flächengleichmäßig ausgewählte, ungematchte Hangstandorte in seiner Umgebung (750 m bis 10 km)?

V0–V0.4 fragen nach dem lokalen Unterschied gegenüber auf Neigung, Höhe und Exposition gematchten Kontrollen. V0.5 untersucht den Unterschied gegenüber einer breiteren örtlichen Hintergrundverteilung. Damit dürfen statische Geländeunterschiede stärker zur Rangfolge beitragen. Die Hauptfrage nach dem Zusatznutzen zeitlicher Umweltinformation bleibt durch den Vergleich statisch versus kombiniert sichtbar.

**Die beiden Aufgaben sind unterschiedlich schwierig. Eine höhere V0.5-AUC ist kein Nachweis eines besseren Modells für die V0.4-Frage.** Zehn Kontrollen vergrößern die Hintergrundstichprobe, nicht die Zahl unabhängiger Ereignisse.

Das Anwendungsbild „Welche Nachbarhänge sind nach einer gerade beobachteten Mure auffällig?“ ist eine mögliche zukünftige Nutzungsidee. Dieses Experiment bewertet zunächst den bereits dokumentierten Positivhang im Vergleich zum Hintergrund. Es prüft weder, welche weiteren Nachbarhänge später rutschen, noch eine Warnfrist nach der ersten Mure. Dafür wären zusätzliche Folgeereignis-/Nicht-Ereignisbeobachtungen und eine andere zeitliche Bewertung notwendig.

Der Modellwert dient als relativer Rang. Die Kontrollen sind Pseudo-Negative ohne dokumentierte Rutschung. Elf ausgewählte Punkte sind keine vollständige Rangkarte aller Hänge oder Hangflächen. Eine künftige Flächenanwendung braucht eine gesonderte Raster-/Hangflächenprüfung.

## 2. Eingefrorener Ereignisbestand und Status der bisherigen Tests

- Positive und t0 werden exakt aus `data/v04/run_c6d67a854ba7/dataset.parquet` übernommen: 423 Ereignisse, bisher 2.538 Proben.
- Verifizierte Datensatz-SHA-256: `ea6950102f2e437c3aebbdfe12f91b20b81a6e41ef59120474d4351c9e1077a2`.
- Abhängigkeitseinheiten werden aus `data/v04/partition/partition.json` übernommen; SHA-256 `6daa4be3c63d675d962d31ccc66c98d0e98a816c7148afa9afba5a5d94baf9e1`.
- Diese Partition enthält 30 Abhängigkeitseinheiten: ehemals 19 Entwicklung und elf Test. Die alten Kennzeichnungen bleiben als Herkunftsmetadaten erhalten.
- Keine neuen Positiven, keine nachträglichen Datums- oder Positionskorrekturen innerhalb dieses Experiments. Technische Ausfälle werden mit Stufe und Grund protokolliert, nicht ersetzt.
- Alle bisherigen V0.4-Testresultate wurden bereits betrachtet. Eine neue Aufteilung oder neue Kontrollen machen dieselben Positiven nicht wieder zu einem ungesehenen Test.

**Folge: V0.5 ist auf diesem Bestand eine explorative, gruppiert kreuzvalidierte Studie.** Alle 423 Ereignisse können dafür verwendet werden. Es gibt innerhalb dieser Studie keinen neuen „versiegelten externen Test“. Der alte V0.4-Test bleibt ein historischer Test für V0.4; eine dortige V0.5-Auswertung wäre nur eine Zusatzdiagnose auf gesehenen Daten. Eine spätere unabhängige Bestätigung braucht tatsächlich ungesehene Abhängigkeitseinheiten und ein eigenes Protokoll.

Eine nominal vollständige V0.5-Tabelle hätte 423 × 11 = 4.653 Proben. Das ist eine Planungszahl vor technischen Ausschlüssen, kein fertiger Datensatz. Die Zahl der Abhängigkeitseinheiten steigt dadurch nicht.

## 3. Kontrollen: ungematchte Umgebungshänge

| Regel | Festlegung |
|---|---|
| Ausgangspunkt | Vorhandener Pool je Ereignis mit 6.000 flächengleichmäßig gezogenen Punkten im Ring 750 m bis 10 km; `data/v04/cache/control_pools/<event_id>.parquet` |
| Auditstand | Für alle 423 Ereignisse existiert ein Pool; ein geprüfter Pool enthält die erwarteten 6.000 Zeilen und Auswahlinformationen. Vollständige Poolprüfung erfolgt vor Nutzung. |
| Zulässigkeit | `inside_austria`, `inventory_clear`, endliche plausible Geländegrundwerte (Höhe 0–4.500 m, endliche Exposition/Neigung), Neigung mindestens 5° |
| Kein Gelände-Matching | Keine Differenzgrenzen zu Höhe, Neigung oder Exposition des Positivs; `passes_calipers` und `matching_score` werden vollständig ignoriert |
| Zahl | Genau zehn Kontrollen je Ereignis |
| Abstand | Mindestens 400 m zwischen gewählten Kontrollen, in EPSG:31287-Metern |
| Zeit | Jede Kontrolle erbt das unveränderte t0 und die Zeitqualität des Positivs |
| Ausfall | Weniger als zehn wählbare Kontrollen: gesamte Ereignisgruppe ausgeschlossen, keine Regeländerung |

**Exakte Zufallsregel:** Poolpunkte erhalten eine stabile ID aus der ursprünglichen Zeilenposition des gehashten Pools. Sortierung vor Ziehung nach dieser ID. Seed = Integer aus den ersten 16 Hex-Zeichen von SHA-256 der UTF-8-Zeichenfolge `<event_id>|v05`. Generator = NumPy `Generator(PCG64(seed))`, NumPy-Version wird gespeichert. Eine einzige Permutation der zulässigen Punkte; in dieser Reihenfolge wählen, wenn die 400-m-Regel erfüllt ist. Bei zehn Punkten stoppen. Kein zweiter Seed und kein weiterer Pool, wenn es nicht reicht.

Pooldatei, DEM-/Inventar-/Grenzprovenienz, Filter, ausgewählte Pool-IDs, Koordinaten, Seed und Softwarestand werden dokumentiert. Die alten Pools haben nicht dieselbe individuelle Sidecar-Prüfung wie die verarbeiteten Tabellen: Vor Nutzung daher SHA-256-Manifest, Schema-/CRS-/Zeilenprüfung und Plausibilitätstest erstellen. Der gespeicherte `inventory_clear`-Wert darf nur bei nachgewiesen unveränderter Inventar-/Bufferkonfiguration wiederverwendet werden, sonst mit derselben registrierten Regel erneut prüfen.

Die Auswahl ist nach den vorab festgelegten Zulässigkeitsfiltern zufällig. Die Behauptung „nie abhängig von Merkmalswerten“ wäre unzutreffend: Neigung und gültige Geländegrundwerte sind ausdrücklich Filter. Es findet aber keine Auswahl nach Modellwert, Matching-Güte, Wetterkontrast oder Ergebnis statt.

Nach Auswahl werden die zehn Kontrollen eingefroren. Ein späterer Wetterausfall darf nicht zu einer neuen, günstigeren Kontrollziehung führen. Die ganze Gruppe fällt nach der registrierten Missing-Regel aus. Keine nachträgliche Kontrolle-Nachwahl.

Die vorhandenen Ausschlusszonen beruhen auf dem gesamten Inventarsnapshot, einschließlich späterer Ereignisse. Sie sind eine retrospektive Auswahlregel; die Auswertung ist deshalb keine Simulation eines damals live verfügbaren Kontrollinventars. Diese Einschränkung wird ausdrücklich berichtet.

## 4. Merkmale, zeitliche Zulässigkeit und fehlende Werte

**Statisch: 22 Merkmale, exakt wie V0.4.** Höhe, Neigung, Exposition sin/cos, Profil-/Plankrümmung, TRI, TPI 150/500 m, relative Lage 500 m, log10 Einzugsgebiet, TWI, fünf CORINE-Klassen und fünf Lithologiegruppen.

**Zeitlich: 29 Merkmale, exakt wie V0.4.** INCA-Summe, maximale Stunde und mittlere Temperatur für 1/3/7/14/30/60 Tage (18); Regen seit Mitternacht, maximale Stunde seit Mitternacht sowie letzte drei/sechs zulässige Stunden (4); SPARTACUS 90/180 Tage (2); SNOWGRID letzter SWE, Schneehöhe und SWE-Abnahme 3/7/14 Tage (5).

**Übernommene Wechselwirkungen, nur bedingte logistische Regression kombiniert:** `log1p(rain_sum_3d) × slope`, `log1p(rain_sum_30d) × log10_catchment_m2`, `log1p(rain_sum_3d) × profile_curvature`. Damit kombiniert 54 Spalten; Gradient Boosting kombiniert 51. Keine neuen Interaktionen nach Ergebnisansicht.

Die Berechnung wird für Positive und Kontrollen identisch angewandt. Bestehende Positive dürfen aus geprüften V0.4-Checkpoints übernommen werden; eine repräsentative kleine Stichprobe wird auf identische Berechnungsdefinition geprüft. Neue Kontrollen erhalten dieselben Rasterfenster-, Rand-/nodata-, CRS- und Zeitregeln. Metadaten „am Fensterrand“ oder „Punktrolle“ werden keine Prädiktoren.

**Zeitregeln:** Stündliche INCA-Werte nur, wenn ihr vollständiger konservativer ±1-h-Umschlag vor t0 und innerhalb des registrierten Fensters liegt. Tagesprodukte nur mit vollständig beendetem Bezugsintervall vor t0. Ereignistagregen ohne bekannte Tageszeit fehlt; er ist nicht 0 mm. Die bestehenden nominalen Fenster und Randstundenregeln werden nicht nachjustiert.

**Kartenstand:** CORINE-Referenz-/Aufnahmezeit und tatsächliche Produktverfügbarkeit getrennt dokumentieren. Ein Aufnahmejahr beweist nicht automatisch eine Veröffentlichung vor t0. Der vorhandene V0.4-Vintage-Filter wird übernommen und seine Grenzen berichtet; ungesicherte historische Live-Verfügbarkeit wird nicht behauptet. DEM-Prä-Ereignisprüfung wie V0.4. Geologie ohne nachträgliche Rutschablagerungsmerkmale.

**Missing-Regeln:** Vollständige plausible INCA-Kernhistorien aller elf Proben sind Pflicht; andernfalls gesamte Gruppe ausgeschlossen. Für die bereits zugelassenen ergänzenden Merkmale dieselbe V0.4-Regel: lineares Modell setzt bei einem fehlenden Wert das betreffende Merkmal für die ganze Elfergruppe auf den Trainingsmittelwert, dann Standardisierung; Gradient Boosting nutzt native Missing-Behandlung. Kein erfundener Messwert. Datenabdeckung vor/nach Gruppenausschluss und je Quelle/Klasse wird berichtet. Missing-Regeln sind fest, keine erneute Quellenzulassung nach Resultaten.

**Explizite Prädiktor-Allowlist:** Nur die genannten Merkmalsnamen werden übergeben. Verboten sind Entfernung zum Positiv, x/y, Länge/Breite, `distance_to_positive_m`, Matching-Score/-Differenzen, `passes_calipers`, IDs, Dateipfade, Quellen-/Erhebungs-/Qualitäts-/Partitionsfelder, Straßenabstand und Informationen nach t0. Standort und Datum dürfen zur Datenbeschaffung und Prüfung verwendet werden, gelangen aber nicht als direkte Merkmale ins Modell. Auch abgeleitete „Abstand zum Zentrum“-Variablen sind verboten.

Die Mitte des Suchrings ist systematisch die Positivposition. Merkmale dürfen diesen Konstruktionsunterschied nicht kodieren. Abschneiden von Rasterfenstern, nodata und zentrale versus randnahe Positionen werden als mögliche indirekte Hinweise geprüft.

Neue Bodentextur, Bodenfeuchte, feinere Geologie oder Satellitenmerkmale gehören nicht in dieses Experiment. Der kontrollierte Unterschied soll zunächst die Kontrollauswahl sein. Zusätzliche Umweltinformationen benötigen danach eine eigene festgelegte Erweiterung.

## 5. Modelle, Aufteilungen und räumliche Überschneidungen

### 5.1 Festgelegte Referenzen und Modelle

- Zufallsrang als analytische Referenz.
- Regelreferenz „höhere Neigung = höherer Rang“, ohne Parameterfit. Sie zeigt, wie viel das aufgehobene Neigungs-Matching allein erleichtert.
- Primärmodell: bedingte logistische Regression, L2 = 1, Trainingsstandardisierung.
- Sekundärmodell: Histogram Gradient Boosting mit den V0.4-Werten: 150 Iterationen, sieben Blätter, mindestens zehn Proben je Blatt, L2 = 1, `class_weight=balanced`, Seed 42.
- Für beide Modellfamilien: statisch, zeitlich, kombiniert. Keine Parameter-/Seed-Suche und keine Merkmalsauswahl.
- Trainingsgewicht je Ereignis wie V0.4: `1/sqrt(n)` mit n = Anzahl Ereignisse seiner ursprünglichen Abhängigkeitseinheit im jeweiligen Training. Nach räumlicher Entfernung neu anhand des tatsächlichen Trainings zählen.
- Eine fehlgeschlagene Optimierung ist ein Fehler; nicht konvergierte lineare Modelle dürfen keine berichteten Vorhersagen liefern.

### 5.2 Gruppierte äußere Kreuzvalidierung

Fünf Folds × fünf feste Wiederholungen mit Seeds 11, 23, 37, 51, 71. Ursprüngliche V0.4-Abhängigkeitseinheiten bleiben ungeteilt; auf dem nach den registrierten Ausfällen verfügbaren Bestand werden sortierte Einheiten deterministisch permutiert und auf fünf Folds verteilt. Alle sechs Modellvarianten verwenden dieselben äußeren Fold-Zuordnungen und dieselbe Kohorte. Keine Fold-Auswahl nach Ergebnissen. Jede retained Probe erhält je Wiederholung eine Vorhersage aus einem Modell, das ihre Einheit nicht trainiert hat.

### 5.3 Neue Kontrollen können neue Nähe erzeugen

Die ursprünglichen Einheiten schützen nicht automatisch gegen Überschneidungen der neu gezogenen Kontrollen. Deshalb nach Kontroll-Freeze, vor Merkmals-/Modellberechnung, einen zusätzlichen räumlichen Audit durchführen. Positive-positive, positive-control und control-control getrennt zählen. Gleiche Pseudo-Negativlabels beseitigen keine räumliche Abhängigkeit.

**Primäre Validierung mit räumlicher Bereinigung:** Für jeden äußeren Fold alle Trainings-Abhängigkeitseinheiten entfernen, sobald irgendeine ihrer Proben unter 1.000 m von irgendeiner gehaltenen Probe liegt, unabhängig von der Klasse. Alle elf Punkte einer Ereignisgruppe und alle Ereignisse einer betroffenen Ursprungseinheit bleiben zusammen. Keine Kontrolle wird deswegen neu ausgewählt. Gehaltene Gruppen bleiben vollständig erhalten.

Prüfpunkt: Je Training mindestens fünf ursprüngliche Einheiten und 20 Ereignisgruppen sowie beide Klassen. Ist ein Fold nicht durchführbar, kein Ersatzseed, keine kleinere Distanz und kein heimlicher Wechsel auf ungepurgte Ergebnisse. Pipeline meldet den registrierten Plan als nicht vollständig durchführbar; gegebenenfalls ist vor Modellierung eine ausdrücklich dokumentierte neue Planversion nötig.

Zusätzlich ungepurgte gruppierte CV mit exakt denselben äußeren Folds als klar gekennzeichnete Sensitivität berechnen; diese ersetzt die primäre räumlich bereinigte Auswertung nicht. Ausmaß des Trainingsverlusts pro Fold, minimale Restabstände und Ergebnisse beider Verfahren berichten. Eine Näheprüfung allein beweist keine vollständige geographische Unabhängigkeit.

Vorverarbeitung, Mittelwerte, Skalen und jede gelernte Größe werden erst nach Bereinigung am tatsächlichen Fold-Training angepasst. Für Schlussmodelle auf allen Daten gelten die gleichen festgelegten Merkmale; deren Trainingsresultate gelten nicht als Validierungsleistung.

## 6. Meldebias und Hintergrundverteilung

Ein flächengleichmäßig ausgewählter Hintergrund enthält wahrscheinlich andere Landbedeckung und Geländeformen als gemeldete Rutschpunkte. Das kann physikalische Unterschiede und Meldebias zugleich verstärken.

Pflichtdiagnosen vor Interpretation:

1. Positiv-/Kontrollverteilungen von Neigung, Höhe, Exposition, CORINE und Lithologie; Kontrollentfernung nach 0,75–2, 2–5 und 5–10 km. Keine nachträgliche Auswahl anhand dieser Verteilungen.
2. Original-Erhebungsmethode, Region, Jahr und Positionskategorie der Positiven als reine Auswertungsmetadaten. Ereignis- und Einheitenzahl je Teilmenge angeben.
3. Feste zusätzliche Ablation der kombinierten bedingten Regression ohne die fünf Landbedeckungsspalten, nur Wiederholung 1. Gleiche Folds/Kohorte und Bereinigung. Differenzen beschreiben, nicht daraus ein neues Primärmodell auswählen.
4. Straßen-/Siedlungsnähe nur als optionale externe Bias-Diagnose, falls zeitlich geeignete Daten mit belegter Herkunft vorhanden sind. Sie bleibt aus sämtlichen Modellvarianten heraus. Moderne Straßenkarten nicht als damaligen Stand ausgeben; kein zusätzlicher Datenabruf, der V0.5 blockiert.
5. Stanz-Einheit getrennt ausweisen und gewichtete Auswertung mit/ohne diese Einheit aus denselben vorliegenden Vorhersagen berichten. Kein Entfernen aus der Hauptanalyse und keine neue Trainingsauswahl aufgrund des Resultats.

Kein Befund trennt ohne zusätzliche Daten automatisch Meldewahrscheinlichkeit von tatsächlicher Instabilität. Flächengleichmäßige Punkte entsprechen einer flächengewichteten Hintergrundstichprobe, keiner gleichen Gewichtung realer einzelner Hangkörper.

## 7. Rangkennzahlen, Zufallsreferenz und Unsicherheit

**Primärer Endpunkt:** über ursprüngliche Abhängigkeitseinheiten gleich gewichtete mittlere lokale AUC der kombinierten bedingten logistischen Regression. Bericht: Median und Spannweite der fünf Wiederholungen; jede Einheit zählt innerhalb einer Wiederholung gleich, Ereignisse innerhalb der Einheit ebenfalls gleich.

**Vorab festgelegter Hauptvergleich:** kombiniert minus statisch, gleiches lineares Modell, identische Gruppen/Folds/Bereinigung. Kein bloßer Vergleich mit Zufall als Nachweis des Wetternutzens.

Weitere Kennzahlen: Top-1, Top-3, mittlerer Rang, Mean Reciprocal Rank (MRR), lokale AUC bei gleicher Ereignisgewichtung, Ergebnisse je Ursprungseinheit und Quelle/Region. Gepoolte Average Precision nur ergänzend; gruppennormalisierte Scores sind keine zwischen Gebieten kalibrierten Wahrscheinlichkeiten.

Bei genau einem Positiv und zehn Kontrollen, ohne Scoregleichstände:

- Lokale AUC: `(Anzahl niedriger bewerteter Kontrollen + 0,5 × Anzahl Gleichstände)/10`, Zufallsreferenz 0,5.
- Top-1: Zufallsreferenz `1/11 = 0,090909…`.
- Top-3: Zufallsreferenz `3/11 = 0,272727…`.
- Zufalls-MRR: `(1 + 1/2 + … + 1/11)/11 = 0,274534…`.
- Klassenanteil für gepoolte AP: `1/11`, nur als Prävalenzreferenz; nicht mit Zufalls-MRR verwechseln.

**Gleichstände:** Kein Vorteil durch „Positiv steht in Zeile 1“. Für Top-k zufällige Auflösung eines Tie-Blocks analytisch mitteln: mit a sicher höher bewerteten Kontrollen und t gleich bewerteten Kontrollen ist Top-k `clip((k-a)/(t+1), 0, 1)`. Mittlerer Rang `1+a+t/2`. MRR ist der Mittelwert von `1/(1+a+j)` für j = 0,…,t, nicht der Kehrwert des mittleren Rangs. Ein vollständig konstantes Modell muss deshalb exakt die genannten Zufallswerte erreichen.

95-%-Bootstrapintervalle und gepaarte Differenzen: 2.000 Ziehungen ursprünglicher Abhängigkeitseinheiten, Seed 20261014, einmal auf den Out-of-fold-Vorhersagen der festen Wiederholung 1. Modelle bleiben dabei fixiert. Wiederholungen sind keine fünf unabhängigen Experimente. Intervalle enthalten keine vollständige Retrainingsunsicherheit; verbleibende Abhängigkeit zwischen Einheiten und die bereits explorierte Kohorte begrenzen ihre Aussage.

Kein bestätigender p-Wert aus unabhängig gezogenen Zufallsrängen je Ereignis: Ereignisse innerhalb einer Einheit sind abhängig. Analytische Zufallskennzahlen sind Referenzen, kein exakter Hypothesentest. Eine Label-Permutation würde zusätzlich Austauschbarkeit zwischen Positiv und konstruierten Kontrollen voraussetzen; sie wird daher hier nicht als bestätigender Signifikanznachweis vorgeschrieben.

Keine Accuracy als primäre Kennzahl: Immer „Kontrolle“ liefert bei 1:10 bereits 90,9 % ohne erkannte Rutschung. Keine nach Testbefunden optimierte Klassifikationsschwelle und keine absolute Rutschungswahrscheinlichkeit behaupten.

## 8. Vergleich mit V0.4 und Einfluss der Kontrollzahl

Die gespeicherten V0.4-Werte bleiben historische Ergebnisse und werden unverändert daneben erklärt. Unterschiedliche Kontrollpopulationen und fünf versus zehn Kontrollen machen Top-1 direkt unvergleichbar; lokale AUC verwendet ebenfalls einen anderen Hintergrund.

Eine begrenzte neue Diagnose trennt diese Effekte: auf der gemeinsamen verfügbaren Kohorte drei Kontrollvarianten betrachten — fünf originale gematchte Kontrollen; die ersten fünf der eingefrorenen ungematchten Zehnerfolge; alle zehn ungematchten Kontrollen. Nur bedingte Regression, statisch und kombiniert, feste Wiederholung 1. Gleiche äußere Ursprungseinheiten; für die räumliche Trainingsbereinigung die Vereinigung der Proben aller drei Kontrollvarianten verwenden, damit jedes Vergleichstraining dieselben Einheiten enthält. Einheiten mit fehlenden Gruppen fallen aus allen drei Diagnosen heraus.

Originale Kontrollpunkte bleiben unangetastet. Neu trainierte Diagnosemodelle werden ausschließlich unter V0.5 gespeichert. Diese Diagnose beantwortet, wie der Hintergrund die Aufgabe verändert, und ist keine erneute unabhängige Bestätigung der ursprünglichen Resultate. Keine Auswahl der besten Variante als neuer Haupterfolg.

## 9. Konkrete technische Änderungen bei späterer Umsetzung

| Neue Datei/Komponente | Zweck |
|---|---|
| `preslide/v05/paths.py` | Schreibschutz und ausschließlich neue Ausgaben unter `data/v05`, `models/v05`, `reports/v05`; eigener config-/Manifest-Check |
| `controls.py` | Ungefilterten V0.4-Pool lesen, Allowlist für Zulässigkeit, Seed/Permutation/Abstände und Auswahlmanifest |
| `pipeline.py` | Positive übernehmen, neue Kontrollen identisch anreichern, komplette Gruppen prüfen, technische Ausfälle checkpointen |
| `partition.py` | Alte Abhängigkeitseinheiten übernehmen, identische CV-Folds speichern, neue Nähe prüfen und Trainingsbereinigung persistieren |
| `models.py` | Zwei festgelegte Modellfamilien, Vorverarbeitung nur am Training, Konvergenzprüfung, explizite Feature-Allowlist |
| `metrics.py` | Beliebiges festgelegtes k statt hartkodierter fünf Kontrollen; lokale AUC, Top-k und korrekte Tie-/MRR-Regeln |
| `experiment.py` | Feste CV, Referenzen, begrenzte Diagnosen, gespeicherte Out-of-fold-Vorhersagen und Modelle |
| `report.py` | Deutschsprachiger explorativer Bericht, Kohortenverluste, Bias-Diagnosen und getrennte historische Vergleiche |

Wichtig: `preslide/v04/models.py::group_ranks` prüft derzeit exakt fünf Kontrollen und teilt durch fünf; `random_rank_null` verwendet sechs mögliche Ränge. Diese Funktionen dürfen nicht unverändert für 1:10 verwendet werden. Eine neue V0.5-Metrikimplementierung ist nötig; keine Änderung am eingefrorenen V0.4-Code.

Auch globale Pfadvariablen aus V0.4 nicht durch Import-Nebenwirkungen umbiegen. Reine geprüfte Berechnungsfunktionen nur nutzen, wenn sie ausschließlich die ausdrücklich übergebenen Daten behandeln. Pfadgebundene Wrapper für neue Ausgaben separat schreiben. Bestehende Rohantworten/Tiles nur lesen; neue Anfragen und Resultate getrennt speichern. Keine neuen Bibliotheken oder GPU-Annahmen erforderlich.

Nominal 150 Haupttrainings (2 Modelle × 3 Varianten × 5 Folds × 5 Wiederholungen), dazu begrenzte registrierte Diagnosen. Aufwand der Umweltbeschaffung zunächst messen: 4.653 Proben sind ungefähr 1,83-mal so viele Tabellenzeilen wie V0.4, der tatsächliche Downloadbedarf hängt aber von bereits vorhandenen Punkten, Rasterzellen und Datumscaches ab. Keine Behauptung einer bereits gemessenen Laufzeit.

## 10. Tests und Reihenfolge

Pflichtprüfungen:

- Genau ein Positiv und zehn unterschiedliche Kontrollen; t0 identisch; 400-m-Trennung, Ring, Staatsgrenze und Ausschlussbuffer korrekt.
- Deterministische Auswahl bei identischem Pool/Manifest; geänderte Eingabeprüfsumme wird nicht still akzeptiert.
- Änderung von Matching-Spalten darf die Auswahl nicht beeinflussen. Filter-/Labelmetadaten niemals als Prädiktor.
- Keine Stunde/kein Tagesintervall nach t0; konservative t0-Untergrenze erhalten; unbekannte Tageszeit bleibt fehlend.
- CRS/Einheiten, nodata, Einzugsgebietsrand und gleiche Berechnung für Positive/Kontrollen.
- Ursprüngliche Ereignis- und Abhängigkeitseinheiten nie geteilt; räumliche Bereinigung berücksichtigt auch control-control; ganze Einheiten werden entfernt.
- Jede retained Probe je Wiederholung genau eine Out-of-fold-Vorhersage; niemals im zugehörigen Training. Skalierung nur aus tatsächlichem Fold-Training.
- Rangmetrik bei eindeutig erstem/letztem Positiv, teilweisen und vollständigen Gleichständen für k = 5 und k = 10. Konstante Scores liefern Chance, unabhängig von Zeilenreihenfolge.
- Konvergenz und Feature-Allowlist; keine IDs, Entfernung oder Punktrolle im Modell.
- V0.4-Datensatz, Partition, Modelle und Baseline-Prüfsummen vor und nach V0.5 identisch.

Ablauf: Freigabe des ergänzten Protokolls → Präregistrierung und Quellen-/Codeprovenienz → 1 Ereignis → 5 → 20 → reine Kontroll-/Näheprüfung aller 423 Kandidaten ohne Modelle → Durchführbarkeitsprüfung der festgelegten CV → Umweltmerkmale vollständig aufbauen → alle tatsächlichen Ausfälle/CV-Mappings einfrieren → ein Basismodell als technischer Pilot → festgelegte Hauptanalyse → Bericht.

Die technische Pilotgruppe wird deterministisch aus Event-IDs gewählt, nicht nach leichtem Modellresultat. Pilotmetriken sind keine wissenschaftlichen Ergebnisse. Bei wissenschaftlich relevanten Planänderungen Originalregistrierung behalten und vor Modellierung eine datierte Änderung mit Grund festhalten; nach Modellresultaten nur eine neue Experimentversion.

## 11. Erwartung und nächste unabhängige Bestätigung

Dieses Experiment gewinnt keine neuen unabhängigen Entwicklungsgruppen und keine neuen physikalischen Messgrößen. Es prüft, ob die vorhandenen Informationen gegenüber dem breiteren lokalen Hintergrund besser trennen. Eine hohe AUC kann vor allem Gelände-/Landbedeckungsunterschiede abbilden und muss gegen die Neigungsreferenz und Meldebias-Diagnosen bestehen.

Eine belastbare nächste Erweiterung sollte zusätzliche ungesehene Episoden und geprüfte Boden-/Vorfeuchtedaten gewinnen; sie kann an diesen explorativen Erkenntnissen anknüpfen, benötigt aber einen echten neuen Test. Ein bestimmter Grenzwert wie AUC 0,80 wird weder versprochen noch zur nachträglichen Auswahl verwendet.

Hintergrund zur Bedeutung räumlicher Validierung und Bodeninformationen: Rüther et al. (2026), https://nhess.copernicus.org/articles/26/4675/2026/ . Die Studie berichtet, dass zufällige CV gegenüber räumlicher CV optimistische Resultate liefern kann; ihre Kennzahlen werden nicht auf PreSlide übertragen.

## 12. Vor Umsetzung zu bestätigender Gesamtumfang

Der Ergänzungsvorschlag legt fest: vorhandene 423 Positive, zehn ungematchte Kontrollen, vorhandene Umweltmerkmale, explorative gruppierte CV mit zusätzlicher räumlicher Trainingsbereinigung, zwei feste Modellfamilien und die genannten begrenzten Diagnosen. Keine neue unabhängige Testbehauptung und kein Folge-Rutschungswarnversprechen.

Die Umsetzung dieses Gesamtumfangs ist ein eigener nächster Auftrag. Dieser Plan ist vollständig reviewbar, aber bewusst noch nicht als ausführbare Konfiguration registriert.
