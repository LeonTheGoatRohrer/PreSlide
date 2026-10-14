# PreSlide — Ziel, Projektstand und Orientierung

**Stand: 14. Oktober 2026 (nach V0.4). Diese Datei zu Beginn jeder Session vollständig lesen.**
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

## V0.2: Stabilitätsanalyse

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

## V0.4: erweitertes Experiment mit versiegeltem Test (14.10.2026, abgeschlossen)

Vorab registriert (`config/v04.json`, Prüfsumme in `reports/v04/PREREGISTRATION.json`), getrennt von der Baseline gespeichert (`data/v04/`, `models/v04/`, `reports/v04/`). Die Baseline wurde vorher zusätzlich schreibgeschützt archiviert (`archive/v0.3-baseline/`) und ist nachweislich unverändert.

- **Ereignisse:** alle Ereignisse ab 2011 mit gesichertem Tag (Freitext und Strukturintervall stimmen überein), ohne Obergrenze je Sturm. Tag bekannt und Uhrzeit bekannt werden getrennt geführt; t0 ist immer eine konservative Untergrenze. 500 Kandidaten → **423 vollständige Gruppen**. Medienereignisse ohne Qualitätsfelder sowie Zwei-Tages- und Nur-Strukturdaten wurden gezählt, aber nicht verwendet.
- **Merkmale:** neu Krümmung, Rauigkeit, Hangposition, Einzugsgebiet/TWI (mit Randprüfung), CORINE-Landbedeckung (Kartenstand vor t0), Geologie 1:500 000, INCA-Regen am Ereignistag vor t0, SPARTACUS 90/180 Tage, SNOWGRID. WINFORE und das 10-m-DGM wurden nach Prüfung nicht verwendet.
- **Aufteilung:** Stürme mit Baseline-Ereignis → Entwicklung (123 Ereignisse, 19 Einheiten); alle übrigen Stürme → versiegelter Test (300 Ereignisse, 11 Einheiten). Eine dokumentierte Protokolländerung vor der Modellierung war nötig, weil die registrierte Verknüpfungsregel den Test auf 4 Ereignisse reduziert hätte.
- **Ergebnis (Test, genau einmal):** bedingte logistische Regression, Gelände + Wetter: gewichtete lokale AUC **0,751** [0,633–0,866], deutlich über Zufall (0,5; p = 0,001). Gelände allein 0,702, Wetter allein 0,604. **Der Zusatznutzen des Wetters (+0,049 [−0,003; +0,108]) ist nicht belegt.** Pro Ereignis gerechnet ist das Ergebnis schwächer (0,668), weil der große Stanz-Sturm (243 Ereignisse) anders reagiert.
- **Wichtigste Einschränkung:** Das Modell stützt sich vor allem auf Landbedeckung (weniger Wald, mehr Grünland und Siedlungs-/Verkehrsflächen am betroffenen Hang) und lokale Geländeform. Ein Teil davon kann Meldebias sein. Nur 11 unabhängige Testeinheiten.

Berichte: `reports/v04/summary.md`; Nachweis: `reports/v04/verification.json` (PASS). Weboberfläche: Abschnitt 07, getrennt von den alten Ergebnissen.

## Pipeline B: Satellitenbilder vor und nach bekannten Ereignissen (14.10.2026, Stufe 3 verifiziert)

Ein **getrenntes System** (`preslide/satellite/`, Ausgaben nur unter `data/satellite/`, `reports/satellite/`), das Sentinel-2-Aufnahmen vor und nach dokumentierten Ereignissen vergleicht, um die sichtbare Veränderungssignatur zu lernen und später undokumentierte Kandidaten zu finden. Es verwendet absichtlich Nachher-Bilder und darf **niemals** in das Vorhersagemodell (Abschnitte oben, „Pipeline A“) einfließen; Tests sichern die Trennung.

- Aufnahmen werden nicht „zur Mittagszeit“ abgefragt, sondern aus allen Überflügen (180 Tage vorher, 120 Tage nachher) die zeitlich nächsten gewählt, die **lokal** im Ausschnitt wolken-, schatten- und schneefrei sind (Szenenklassifikation plus NDSI-Schneetest, weil eine komplett verschneite Szene nur 2 % Schnee meldete). Ereignis und mindestens vier seiner fünf Kontrollhänge müssen auf demselben Überflug brauchbar sein; der Ereignistag wird nie verwendet; Paare mit mehr als 90 Tagen Jahreszeitabstand sind ausgeschlossen.
- Radiometrie: Die beiden Earth-Search-Sammlungen speichern den Reflexionsoffset unterschiedlich (c1 mit, alt ohne), obwohl die Metadaten dasselbe behaupten; empirisch geprüft, Laufzeitkontrolle eingebaut.
- Stufe 3 (20 geprüfte Ereignisse ab 2018 mit Position ≤ 20 m): **14 brauchbare Gruppen, 12 unabhängige Einheiten, 79 Proben**. Kontaktbögen wurden gesichtet: Vorher/Nachher decken sich, bei mehreren Ereignissen ist der Vegetationsverlust genau an der gemeldeten Position sichtbar.
- Erste Basislinie (Ereignis gegen seine Kontrollen, Einheiten nie im Training): lokale AUC 0,68–0,74 (Zufall 0,5; Permutations-p ≈ 0,06). Wiederentdeckung im 2,56-km-Ausschnitt: 7 von 14 innerhalb 160 m gefunden, 5 davon unter den ersten drei, Ortsfehler median 71 m, 3 Kandidaten je km². **Hinweis, kein Nachweis**: nur 12 Einheiten, kleines Suchgebiet um das bekannte Ereignis.
- 102 Treffer außerhalb bekannter Positionen sind **satellitengestützte Kandidaten, nicht unabhängig bestätigt** (`validation_status = UNVERIFIED`); keiner wird automatisch zum Ereignis. Berichte: `reports/satellite/`.
- Offen: Lauf über alle 137 Ereignisse ab 2018 (gestartet), Sichtung der Kandidaten, Sentinel-1, kleine Suche in unbekanntem Gebiet.

## Genau eine nächste wissenschaftliche Priorität

**Den in V0.4 gefundenen Gelände- und Landbedeckungseffekt gegen Meldebias absichern und mehr unabhängige Episoden gewinnen** (z. B. getrennt gekennzeichnete Medienereignisse, vorab registriertes Case-Crossover-Design oder Satellitenprüfung der Positionen). Jede Erweiterung ist eine neue Version; der V0.4-Test ist jetzt gesehen und darf keine Auswahl mehr steuern.

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
| `archive/v0.3-baseline/` | Schreibgeschützte Kopie aller Baseline-Ausgaben mit Prüfsummen |
| `config/v04.json`, `reports/v04/` | V0.4: Präregistrierung, Änderung 1, Freeze, Test, Bericht, Verifikation |
| `preslide/v04/` | V0.4-Code (Audit, Datumsregeln, Pipeline, Modelle, Auswertung) |
| `config/satellite.json`, `preslide/satellite/`, `reports/satellite/` | Pipeline B: Satelliten-Vorher/Nachher, Kandidatensuche (getrennt von Pipeline A) |
| `config/stability_v02.json` | Vorab eingefrorener Auswertungsplan |
| `data/analysis/stability_v02/` | Lokale Vorhersagen, Modelle, Splits, Checkpoints und Originalprüfsummen |
| `data/processed/046074ba6f12556c/` | Eingefrorener Originalbestand; nicht überschreiben |
| `METHODOLOGY.md` | Ursprüngliche wissenschaftliche Methodik |
| `DATA_SOURCES.md` | Quellen, Auflösung, Herkunft und Nutzungsgrenzen |
| `RESULTS.md` / `LIMITATIONS.md` | Historische Ergebnisse/Grenzen mit getrennten Ergänzungen |
| `README.md` | Einrichtung und Ausführung |

## Pflege dieser Datei

Nach einem wesentlichen Meilenstein den tatsächlichen Stand und die offenen Punkte aktualisieren. Abgeschlossene Arbeit nicht erneut als offen aufführen. Kennzahlen immer gegen gespeicherte Ergebnisse prüfen; dieser Überblick ersetzt keine Ergebnistabelle. Detailprotokolle gehören nicht hierher.
