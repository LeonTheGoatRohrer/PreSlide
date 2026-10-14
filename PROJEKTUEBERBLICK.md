# PreSlide — Ziel, Projektstand und Orientierung

**Stand: 14. Oktober 2026. Diese Datei zu Beginn jeder Session vollständig lesen.**
Danach `PROJECT_STATE.md` für den technischen Arbeitsstand lesen. Bei Widersprüchen die gespeicherten Artefakte prüfen; keine Ergebnisse erfinden oder historische Experimente überschreiben.

## Was ist PreSlide?

PreSlide ist ein wissenschaftlicher Machine-Learning-Forschungsprototyp für Österreich. Er untersucht:

> Können Umweltinformationen aus der Zeit vor einem dokumentierten Hangrutschungsereignis den betroffenen Hang von nahe gelegenen, topographisch ähnlichen Kontrollhängen unterscheiden, wenn alle Hänge zum selben Zeitpunkt betrachtet werden?

Die entscheidende Zusatzfrage lautet: **Bringt Wetter aus der Vorgeschichte einen wiederholbaren Nutzen gegenüber Geländedaten allein?**

Das Ziel ist ein vollständiges, reproduzierbares und wissenschaftlich belastbares Experiment. Eine hohe AUC ist kein Selbstzweck. Schwache oder widersprüchliche Ergebnisse sind gültige Forschungsergebnisse und dürfen nicht verborgen werden.

PreSlide ist derzeit **kein Warnsystem**, keine österreichweite Gefahrenkarte und kein Modell für die reale Wahrscheinlichkeit einer Rutschung. Die Modellwerte sind Vergleichswerte eines retrospektiven Fall-Kontroll-Experiments. Modellwichtigkeit bedeutet keine Kausalität.

## Was bereits funktioniert

- Reale österreichische Ereignisse aus GeoSphere Austria, mit dokumentierter Prüfung von Datum, Prozess und Positionskategorie.
- Lokale Auswahl von fünf topographisch ähnlichen Kontrollen je Ereignis.
- Reale Geländedaten und Wetterhistorien vor dem Ereignistag.
- Reproduzierbare Merkmalsberechnung, gespeicherte Zwischenschritte, Prüfsummen und lokal zwischengespeicherte Rohantworten.
- Drei Modellfamilien: logistische Regression, Random Forest und Histogram Gradient Boosting.
- Jeweils Gelände allein, Wetter allein und Gelände plus Wetter.
- Gruppensichere Auswertung und eine deutsche lokale Webdemonstration mit Karte, fünf abgeleiteten Beispielgruppen, Wetterverläufen und Originalergebnissen.

Technik: Python/FastAPI, Vue 3/Vite/MapLibre; CPU-Betrieb auf dem Laptop. Start: `scripts/start.ps1`, üblicherweise auf `http://127.0.0.1:8000`. Eine frühere laufende Prozess-ID ist kein Nachweis, dass der Dienst aktuell läuft.

## Datenbestand und Bedeutung der Kontrollen

Der eingefrorene Lauf `046074ba6f12556c` enthält **60 vollständige Ereignisse und 300 Kontrollen**, insgesamt 360 Proben. Ausgangspunkt waren 102 Kandidaten. Tatsächliche Ereignisjahre: 2017–2026; die ursprüngliche Suche ab 2018 wurde dokumentiert bis 2015 erweitert.

Ausschlüsse: 13 Ereignisse mit zu wenigen passenden Kontrollen, 17 mit fehlenden Wetterdaten, 9 mit unplausiblen/negativen Niederschlagswerten und 3 mit zu geringer DEM-Neigung. Kriterien wurden nicht für bessere Kennzahlen gelockert.

Kontrollen sind **Pseudo-Negative**: Hänge ohne dokumentiertes Ereignis, keine nachweislich stabilen Hänge. Jede Kontrolle übernimmt den Ereignistag ihres zugehörigen positiven Hangs.

Kontrollauswahl: 6.000 Kandidaten pro Ereignis, 750 m bis 10 km Abstand, höchstens 5° Neigungs-, 150 m Höhen- und 45° zirkulärer Expositionsunterschied; mindestens 400 m Abstand zwischen Kontrollen. Ausschlussbereiche um bekannte Inventarereignisse werden eingehalten.

Gelände: 30-m-Raster; Höhe, Neigung sowie Sinus und Kosinus der Exposition. Wetter: GeoSphere INCA v1, ungefähr 1 km und eine Stunde. 18 Merkmale aus Niederschlagssumme, maximalem Stundenregen und mittlerer Temperatur für nominal 1/3/7/14/30/60 Tage. Konservative Randstundenregeln lassen im 60-Tage-Fenster 1.438 Stunden übrig. Keine Messung vom Ereignistag oder danach wird als Wettermerkmal verwendet.

## Originalexperiment V0: eingefroren und bereits betrachtet

| Teilmenge | Ereignisse | Abhängigkeitsgruppen | Proben |
|---|---:|---:|---:|
| Training | 19 | 12 | 114 |
| Validierung | 26 | 4 | 156 |
| Test | 15 | 4 | 90 |

Ereignisse und ihre Kontrollen bleiben zusammen. Zusätzliche Abhängigkeitsgruppen verbinden zeitlich nahe Ereignisse, räumlich nahe positive Hänge und überlappende Proben. Diese Gruppen sind konservative Hilfskonstruktionen, keine nachgewiesen unabhängigen Sturmidentitäten.

Original-Test und separater Steiermark-Test wurden bereits angesehen. **Sie dürfen nicht zur Auswahl neuer Merkmale, Modelle, Parameter, Schwellen oder günstiger Analysen genutzt werden.** Originaldatensatz, Zuordnungen, Matching, Modelle, Berichte und Testvorhersagen bleiben unverändert. Historische Resultate stehen in `reports/experiment/metrics.json` und im ursprünglichen Abschnitt von `RESULTS.md`.

## V0.2: aktueller Forschungsstand

Der V0.1-Stabilitätsplan wurde im Chat „Build PreSlide V0 prototype“ gefunden. Seine Vorgaben sind mit den Zusatzdiagnosen in `config/stability_v02.json` eingefroren.

Für die neue Untersuchung werden ausschließlich ursprüngliches Training und Validierung verwendet: **45 Ereignisse, 225 Kontrollen, 270 Proben, 16 bestehende Abhängigkeitsgruppen**. Der ursprüngliche Test ist ausgeschlossen. Die alten Gruppen werden nicht neu berechnet.

Berechnet und gespeichert:

- Vier Folds × fünf feste Wiederholungen (Seeds 11, 23, 37, 51, 71).
- Drei Modellfamilien × drei Merkmalsvarianten: **180 Haupttrainings**.
- Genau eine Vorhersage außerhalb des eigenen Gruppentrainings je Probe, Variante und Wiederholung.
- Paarvergleiche mit fünf Kontrollen, Ereignisränge und Wetter-Rangänderungen.
- Wetterunterschiede innerhalb von Ereignisgruppen; Auswertungen nach Merkmal, Bundesland, Jahr und Entfernung.
- Explorative feste Wetterfenster, drei vorab festgelegte Wetter-Gelände-Interaktionen, gruppierte Lernkurven und Merkmalsstabilität.
- Einfluss großer Abhängigkeitsgruppen, Matchingqualität und Positionsunsicherheit.
- Sieben wissenschaftliche Abbildungen und maschinenlesbare Berichtstabellen.

Alle 270 Entwicklungs-Wettervektoren wurden aus den lokalen ursprünglichen Wetterantworten nachgerechnet; dabei wurden keine Abweichungen gefunden. Originalartefakte sind durch Prüfsummen gesichert.

### Was die Ergebnisse bislang aussagen

**Ein robuster allgemeiner Wetternutzen ist nicht belegt.** Beim Random Forest verbessert Wetter die lokale Rangfolge in vier von fünf Wiederholungen, die Average Precision jedoch nur in zwei. Bei logistischer Regression verschlechtert sich die mittlere lokale AUC in allen fünf Wiederholungen. Modell und Bewertungsmaß liefern unterschiedliche Antworten.

Die Lernkurven steigen nicht durchgehend mit mehr Trainingsgruppen. Keine der 45 Gruppen hat über alle 18 Wettermerkmale identische Werte. Das schließt eine allgemeine versehentliche Gleichsetzung der Wetterdaten aus, beweist aber keine ausreichende Hangauflösung des 1-km-Produkts.

Die größte Abhängigkeitsgruppe umfasst 15 von 45 Entwicklungsereignissen. Der lokale Random-Forest-Vorteil verschwindet bei gleicher Bewertungsgewichtung der Gruppen nicht vollständig. Die vorhandene Positionsverschiebungsdiagnose verändert bei 23 von 45 Ereignissen die Neigung um mehr als 5°. Positionskategorien sind nicht unabhängig bestätigte Vermessungsgenauigkeiten.

Fünf Wiederholungen derselben Daten sind **keine fünf unabhängigen Bestätigungen**. Alle Zusatzdiagnosen bleiben explorativ. Die ausführlichen Antworten auf zehn wissenschaftliche Fragen stehen in `reports/stability_v02/summary.md`; Berichtszahlen werden aus gespeicherten Ergebnissen erzeugt.

### Abschluss und Verifikation

V0.2 ist abgeschlossen: **180 Haupttrainings und 260 ergänzende Trainings** sind gespeichert. Alle **29.700 gespeicherten Vorhersagen** wurden mit den jeweiligen gespeicherten Modellen reproduziert. Die Prüfungen bestätigen unveränderte Originalartefakte, ausschließlich am Training angepasste Vorverarbeitung, identische äußere Aufteilungen und keinen ursprünglichen Testfall in den neuen Trainings. Nachweis: `reports/stability_v02/verification.json` (PASS).

**43 Tests bestehen**, die Weboberfläche lässt sich bauen und wurde im Browser geprüft. Die deutsche Ergebnisansicht trennt Originaltest, Steiermark, V0.2-Stabilität und Diagnosen; die sieben V0.2-Abbildungen sind auswählbar. Es wurde nichts öffentlich bereitgestellt.

## V0.3: ergänzende Zufallsreferenz

Eine parallel entstandene, separat dokumentierte Analyse vergleicht die Ergebnisse mit 100 zufälligen Vertauschungen der Positivzuordnung innerhalb jeder Sechsergruppe. Sie verwendet denselben Entwicklungsbestand und dieselben eingefrorenen Aufteilungen. Der unvertauschte Kontrolllauf reproduziert V0.2; die Berichte liegen unter `reports/null_v03/` und `reports/current_state_audit.md`.

Die Wettervarianten zeigen darin keine überzeugende Abweichung von der Zufallsreferenz (berichtete obere empirische p-Werte mindestens 0,28). Das ist **kein Beweis, dass Wetter keinen Einfluss hat**. Die kleine Zahl unabhängiger Episoden, Matchingstruktur und explorative Mehrfachvergleiche begrenzen die Aussage. Ein Gewinn gegenüber einer schwachen Gelände-Baseline ist nicht gleichbedeutend mit verlässlicher Leistung oberhalb Zufall.

## Eingefrorene Baseline (14.10.2026)

Alle bisherigen Ergebnisse auf Datensatz `046074ba6f12556c` sind als **PreSlide V0.3 Baseline** eingefroren: `reports/baseline/BASELINE_MANIFEST.json` (95 Prüfsummen, Merkmale, Modelle, Softwarestände), Statusbericht `reports/baseline/BASELINE_STATUS.md` und Fehleranalyse je Ereignis `reports/baseline/error_analysis.md`. Bei der Prüfung wurde kein wissenschaftlicher Fehler gefunden. Behoben wurde eine Überschreibgefahr: Pilotläufe hätten die Baseline-Dateien überschrieben und werden jetzt verweigert. Die Weboberfläche erklärt alle Kennzahlen über ein zentrales Tooltip-System und enthält einen Ereignis-Explorer (Rang, geschlagene Kontrollen, Wettereinfluss je Ereignis).

Unter den bisherigen Qualitätskriterien enthält die Quelle genau die 102 bereits genutzten Kandidaten. Mehr Daten erfordern eine neue, vorab festgelegte Version (V0.4) mit geänderten Einschlusskriterien oder einer weiteren Quelle, außerdem einen versionierten Lauf, der die Baseline nicht überschreibt.

## Genau eine nächste wissenschaftliche Priorität

**Zusätzliche unabhängige Wetter- und Ereignisepisoden mit verifizierten Ereignispositionen als vorab festgelegten externen Prüfbestand gewinnen.**

Damit soll die Aussage unabhängig überprüft werden. Mehr Zeilen oder ein komplexeres Modell versprechen aufgrund der bisherigen Ergebnisse keine automatische Verbesserung. Bestehende schwierige Ereignisse werden nicht entfernt.

## Feste Regeln für weitere Sessions

- Nur reale Daten; niemals erfundene Messwerte, Ersatzereignisse oder Kennzahlen.
- Keine Zukunftsinformation in Merkmalen; keine Trennung zusammengehöriger Ereignis- oder Abhängigkeitsgruppen.
- Skalierung und andere gelernte Vorverarbeitung nur am jeweiligen Training anpassen.
- Keine Auswahl nach beobachteten Testresultaten, keine Seed-Suche, kein Nachjustieren der Kontrollen.
- Neue Experimente getrennt versionieren; bei nachgewiesenem Fehler Original erhalten, Fehler dokumentieren und neuen Stand erzeugen.
- Caches und gültige Checkpoints verwenden. Wetter, Gelände und fertige Modellläufe nicht unnötig neu berechnen.
- Keine Umgestaltung der gesamten Oberfläche und keine unnötige Architekturänderung.
- Rohdaten und Probenvorhersagen bleiben lokal. Die GeoSphere-Testquelle hat keine geklärte spezifische Weiterverwendungslizenz; lokale nicht kommerzielle Forschung ist vom Nutzer autorisiert, keine Anbieterbestätigung wird behauptet.
- Passende vorhandene Skills dürfen gemäß aktueller ausdrücklicher Nutzeranweisung ohne erneute Nachfrage verwendet werden. Das ist keine pauschale Erlaubnis für Veröffentlichung oder externe Kommunikation.

## Wo finde ich was?

| Datei/Verzeichnis | Zweck |
|---|---|
| `AGENTS.md` | Verbindliche Arbeits- und Wissenschaftsregeln |
| `PROJEKTUEBERBLICK.md` | Diese fachliche Orientierung; vor jeder Session lesen |
| `PROJECT_STATE.md` | Kompakter technischer Stand und nächste Aufgaben |
| `reports/stability_v02/summary.md` | Vollständige V0.2-Schlussfolgerung und Abbildungen |
| `reports/stability_v02/verification.json` | Prüfung aller 440 V0.2-Trainings und ihrer gespeicherten Vorhersagen |
| `reports/null_v03/summary.md` | Getrennte explorative Zufallsreferenz |
| `reports/current_state_audit.md` | Ergänzender Gesamtcheck des aktuellen Projektbestands |
| `reports/baseline/` | Eingefrorene V0.3-Baseline: Manifest, Status, Fehleranalyse je Ereignis |
| `config/stability_v02.json` | Vorab eingefrorener Auswertungsplan |
| `data/analysis/stability_v02/` | Lokale Vorhersagen, Modelle, Splits, Checkpoints und Originalprüfsummen |
| `data/processed/046074ba6f12556c/` | Eingefrorener Originalbestand; nicht überschreiben |
| `METHODOLOGY.md` | Ursprüngliche wissenschaftliche Methodik |
| `DATA_SOURCES.md` | Quellen, Auflösung, Herkunft und Nutzungsgrenzen |
| `RESULTS.md` / `LIMITATIONS.md` | Historische Ergebnisse/Grenzen mit getrennten Ergänzungen |
| `README.md` | Einrichtung und Ausführung |

## Pflege dieser Datei

Nach einem wesentlichen Meilenstein den tatsächlichen Stand und die offenen Punkte aktualisieren. Abgeschlossene Arbeit nicht erneut als offen aufführen. Kennzahlen immer gegen gespeicherte Ergebnisse prüfen; dieser Überblick ersetzt keine Ergebnistabelle. Detailprotokolle gehören nicht hierher.
