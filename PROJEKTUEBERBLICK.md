# Talwacht — Ziel, Projektstand und Orientierung

**Stand: 18. Oktober 2026 (nach V0.5, Prüfgebiete-Grundgerüst und Jury-Einstieg). Diese Datei zu Beginn jeder Session vollständig lesen.**

**Planungsergänzung 17.10.2026:** Auf Nutzerauftrag liegt ein konkreter Plan für eine Einzelbildsuche mit zwei neuronalen Netzen und kontrolliertem Weiterlernen unter `reports/weiterentwicklung_2026-10-17/NEURONALE_MURENSUCHE_PLAN.md`. Noch keine Umsetzung oder neuen Ergebnisse. Der Plan berücksichtigt die bislang separat entwickelten Satellitenzweige; reine Murenerkennung erfordert zusätzliche Prozesslabels, Modellübereinstimmung allein ergibt nur ein Pseudo-Label.
Danach `PROJECT_STATE.md` für den technischen Arbeitsstand lesen. Bei Widersprüchen die gespeicherten Artefakte prüfen; keine Ergebnisse erfinden oder historische Experimente überschreiben.

## Was ist Talwacht?

Talwacht ist ein wissenschaftlicher Machine-Learning-Forschungsprototyp für Österreich. Er untersucht:

> Können Umweltinformationen aus der Zeit vor einem dokumentierten Hangrutschungsereignis den betroffenen Hang von nahe gelegenen, topographisch ähnlichen Kontrollhängen unterscheiden, wenn alle Hänge zum selben Zeitpunkt betrachtet werden?

Die entscheidende Zusatzfrage lautet: **Bringt Wetter aus der Vorgeschichte einen wiederholbaren Nutzen gegenüber Geländedaten allein?**

Das Ziel ist ein vollständiges, reproduzierbares und wissenschaftlich belastbares Experiment. Eine hohe AUC ist kein Selbstzweck. Schwache oder widersprüchliche Ergebnisse sind gültige Forschungsergebnisse und dürfen nicht verborgen werden.

Talwacht ist derzeit **kein Warnsystem**, keine österreichweite Gefahrenkarte und kein Modell für die reale Wahrscheinlichkeit einer Rutschung. Die Modellwerte sind Vergleichswerte eines retrospektiven Fall-Kontroll-Experiments. Modellwichtigkeit bedeutet keine Kausalität.

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

## V0.5: Nachbarhang-Rangfolge gegen zehn ungematchte Umgebungshänge (14.10.2026, abgeschlossen, explorativ)

Plan `reports/weiterentwicklung_2026-10-14/V05_NACHBARHANG_PLAN.md`, Regeln vorab in `config/v05.json` registriert, Kohorte und CV-Zuordnung vor jedem Modell eingefroren. Andere, leichtere Frage als V0.4: der gemeldete Hang gegen zehn flächengleichmäßige, **nicht gematchte** Punkte 750 m–10 km um ihn. Alle Ereignisse waren in V0.4 schon gesehen → gruppierte, räumlich bereinigte Kreuzvalidierung, **kein neuer Test**.

- 418 Gruppen, 4 598 Proben, 29 Einheiten; alle neu berechneten Positiven identisch mit V0.4; V0.4 nachweislich unverändert.
- Bedingte logistische Regression kombiniert: lokale AUC **0,851** (0,835–0,863); statisch 0,865; Wetter allein 0,719; Neigungsregel 0,572; Zufall 0,5.
- **Kein Wetterzusatznutzen** (kombiniert − statisch −0,023 [−0,079; +0,019]). Wetter allein ist hier teils ein Stellvertreter für Höhe/Lage.
- Mit den fünf gematchten Kontrollen auf derselben Kohorte nur 0,705: Die hohe V0.5-Trennung beruht auf Höhe/Lage und Landbedeckung — vermutlich teilweise Meldebias.

Bericht: `reports/v05/summary.md`; Nachweis: `reports/v05/verification.json` (PASS).

## Webdemonstration: Jury-Einstieg und Forschungsbereich (18.10.2026)

Auf ausdrücklichen Nutzerauftrag vom 18.10.2026 ersetzt ein Jury-Einstieg die bisherige Startseite. Hauptnavigation: **Start** (`#/start`, Problem, Wirkungskette Prüfpunkt → Auslauf → Infrastruktur, drei Kernzahlen, sichtbare Grenze, belegte Quellen) · **Demo** (`#/pruefgebiete`) · **Ergebnisse** kurz (`#/befunde`: V0.4-Test mit Intervall, Gelände gegen Wetter, Schwäche bei reinen Hangmuren, Extremwetter-Abschnitt) · **Methodik & Grenzen** (`#/methodik`) · **Forschung** (`#/forschung`). Die drei bisherigen Seiten Projekt, Vorgehen und Ergebnisse bleiben inhaltlich unverändert als Forschungsbereich unter ihren alten Adressen (`#/projekt`, `#/vorgehen`, `#/ergebnisse/...`); alte Lesezeichen führen weiter zum selben Inhalt.

Modellkennzahlen kommen nur aus den API-Bündeln (`/api/results_v04`, `/api/benchmarks`, `/api/pruefgebiete`, `/api/hangmuren_pilot`, `/api/extremwetter`), immer mit Intervall. Für Modellwerte gelten die Begriffe Prüfstufe, Rangfolge, Szenario; ein Wortlauttest verhindert Wahrscheinlichkeits-, Risiko- und Vorhersagewörter auf den Jury-Seiten. Aussagen zum Problem sind mit überprüfbaren Quellen belegt (GeoSphere Austria/Nature 2025, BMLUK, Schlögl et al. 2021 als Gegenbefund).

### Vorherige Fassung: drei Seiten (15.10.2026)

Die lokale Oberfläche führt über **Projekt → Vorgehen → Ergebnisse**. Direkte Routen: `/#/projekt`, `/#/vorgehen`, `/#/ergebnisse`; alte Abschnittslinks werden weiter zugeordnet. Der Einstieg erklärt den retrospektiven Prototyp, die Vorgehensseite zeigt die Schrittfolge und das reale Baseline-Beispiel, die Ergebnisse trennen V0.4-Test und explorative V0.5. Karten, Wetterkurven, Modellvergleiche und historische Analysen bleiben in aufklappbaren Bereichen erreichbar.

Kennzahlen und Intervalle kommen aus den vorhandenen API-Bündeln. V0.5-Wiederholungsspannen sind ausdrücklich keine Konfidenzintervalle; das Bootstrap-Intervall der ersten Wiederholung wird separat gezeigt. Keine wissenschaftlichen Artefakte oder Modelle wurden verändert.

## Genau eine nächste wissenschaftliche Priorität

**Den in V0.4 gefundenen Gelände- und Landbedeckungseffekt gegen Meldebias absichern und mehr unabhängige Episoden gewinnen** (z. B. getrennt gekennzeichnete Medienereignisse, vorab registriertes Case-Crossover-Design oder Satellitenprüfung der Positionen). Jede Erweiterung ist eine neue Version; der V0.4-Test ist jetzt gesehen und darf keine Auswahl mehr steuern.

## Feste Regeln für weitere Sessions

- Nur reale Daten; niemals erfundene Messwerte, Ersatzereignisse oder Kennzahlen.
- Keine Zukunftsinformation in Merkmalen; keine Trennung zusammengehöriger Ereignis- oder Abhängigkeitsgruppen.
- Skalierung und andere gelernte Vorverarbeitung nur am jeweiligen Training anpassen.
- Keine Auswahl nach beobachteten Testresultaten, keine Seed-Suche, kein Nachjustieren der Kontrollen.
- Neue Experimente getrennt versionieren; bei nachgewiesenem Fehler Original erhalten, Fehler dokumentieren und neuen Stand erzeugen.
- Caches und gültige Checkpoints verwenden. Wetter, Gelände und fertige Modellläufe nicht unnötig neu berechnen.
- Struktur der Oberfläche seit 18.10.2026 (Nutzerauftrag): Jury-Einstieg (Start, Demo, Ergebnisse kurz, Methodik & Grenzen) plus Forschungsbereich mit den drei bisherigen Seiten Projekt, Vorgehen, Ergebnisse. Diese drei Seiten inhaltlich erhalten und unter ihren alten Adressen erreichbar halten; weitere grundlegende Umgestaltungen nur auf Auftrag.
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
| `config/v05.json`, `reports/v05/`, `preslide/v05/` | V0.5: Registrierung, Kohorten-Freeze, CV-Ergebnisse, Bericht, Verifikation |
| `config/v04.json`, `reports/v04/` | V0.4: Präregistrierung, Änderung 1, Freeze, Test, Bericht, Verifikation |
| `preslide/v04/` | V0.4-Code (Audit, Datumsregeln, Pipeline, Modelle, Auswertung) |
| `config/stability_v02.json` | Vorab eingefrorener Auswertungsplan |
| `data/analysis/stability_v02/` | Lokale Vorhersagen, Modelle, Splits, Checkpoints und Originalprüfsummen |
| `data/processed/046074ba6f12556c/` | Eingefrorener Originalbestand; nicht überschreiben |
| `METHODOLOGY.md` | Ursprüngliche wissenschaftliche Methodik |
| `DATA_SOURCES.md` | Quellen, Auflösung, Herkunft und Nutzungsgrenzen |
| `RESULTS.md` / `LIMITATIONS.md` | Historische Ergebnisse/Grenzen mit getrennten Ergänzungen |
| `README.md` | Einrichtung und Ausführung |

## Pflege dieser Datei

Nach einem wesentlichen Meilenstein den tatsächlichen Stand und die offenen Punkte aktualisieren. Abgeschlossene Arbeit nicht erneut als offen aufführen. Kennzahlen immer gegen gespeicherte Ergebnisse prüfen; dieser Überblick ersetzt keine Ergebnistabelle. Detailprotokolle gehören nicht hierher.
