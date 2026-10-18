# Talwacht — Ziel, Projektstand und Orientierung

**Stand: 15. Oktober 2026 (nach V0.9; V0.6–V0.8 und Pipeline B eingemergt). Diese Datei zu Beginn jeder Session vollständig lesen.**

**Planungsergänzung 17.10.2026:** Auf Nutzerauftrag liegt ein konkreter Plan für eine Einzelbildsuche mit zwei neuronalen Netzen und kontrolliertem Weiterlernen unter `reports/weiterentwicklung_2026-10-17/NEURONALE_MURENSUCHE_PLAN.md`. Noch keine Umsetzung oder neuen Ergebnisse. Der Plan berücksichtigt die bislang separat entwickelten Satellitenzweige; reine Murenerkennung erfordert zusätzliche Prozesslabels, Modellübereinstimmung allein ergibt nur ein Pseudo-Label.
**Anfälligkeitssystem 18.10.2026:** Der Plan `reports/weiterentwicklung_2026-10-17/ANFAELLIGKEITSSYSTEM_PLAN.md` wurde als Version `susceptibility_v01` vorregistriert und bis Phase 4 umgesetzt (Gorkha und Far-Western Nepal als Entwicklung, RER2023 mangels Kartierumriss ausgesetzt, Südtirol versiegelt). **Das Phase-4-Gate ist nicht bestanden:** Ein reines Geländemodell überträgt zwischen Erdbeben- und Monsunrutschungen nicht belegbar mehr als die Neigung allein (+0,006 AUC [−0,005; +0,017]). Kein Ausbau, keine Karte. Details: `reports/susceptibility_v01/PHASE4_GATE.md`.
**Anfälligkeit v02 18.10.2026:** Als neue Version `susceptibility_v02` vorregistriert (nur Phase 0, kein Modell): getrennte Modelle je Auslöser (Erdbeben: Gelände + PGA aus USGS-ShakeMap; Regen: Gelände), bestätigend nur auf den in v01 ungesehenen Inventaren Iburi und RER2023. **Die Datenlage trägt das Design derzeit nicht:** Für beide fehlt ein unabhängiger Kartierumriss; ein Umriss aus den Rutschungen wird nicht konstruiert. Weiter geht es erst, wenn Autoren oder Anbieter einen Umriss liefern. Details: `reports/susceptibility_v02/DECISIONS.md`.
**Anfälligkeit v02, Phase 1 (18.10.2026, teilweise):** Für Iburi liegt jetzt ein unabhängiger Kartierumriss vor: Das GSI-Archiv D1-No.991 enthält seinen Interpretationsbereich als Daten (1.358 km²). Amendment 1 stellt Iburi auf GSI-Polygone und -Umriss um, noch ohne Stichprobe oder Modell. Die vorab registrierte Gorkha-Sensitivität (explorativ) zeigt: Der Gelände-über-Neigung-Vorteil innerhalb Gorkhas hält auch mit 20-km-Blöcken (+0,120 statt +0,124), ist also kein Effekt räumlicher Nähe. Die modellierte Erschütterung (PGA) halbiert ihn fast genau (50,1 %, Grenzfall der Regel). Das ist keine Übertragbarkeit. Inzwischen ist das **Phase-1-Gate für den Erdbebenarm erfüllt** (Iburi-ShakeMap deckt den Umriss, 3.177 Iburi-Positive nach der Altrutschungsregel, Puffer 100 m per Amendment 2). Der Regenarm wartet weiter auf einen RER2023-Umriss. Phase 2 ist abgeschlossen: Geländeblöcke für Iburi, Gorkha und Far-Western Nepal liegen vor. Dabei wurde ein Fehler im v01-Code gefunden: Jeder DEM-Block war um bis zu etwa 15 m verschoben. Das macht die v01-Merkmale leicht unscharf (Gorkha: Neigung im Mittel 1,6° anders), ist aber kein Informationsleck. v01 bleibt unverändert und dokumentiert, v02 rechnet korrekt. Meerzellen werden per Amendment 3 vom Hintergrund ausgeschlossen. Phase 3 ist abgeschlossen: Stichproben für Iburi (3.177 Positive), Gorkha (24.036) und Far-Western Nepal (1.551) sind gezogen und geprüft. Ein Pufferfehler der Geometriebibliothek (Abstand 99,7 statt 100 m) wurde vor jedem Modell gefunden und behoben. **Phase 4 (bestätigender Test, einmal gerechnet): nicht belegt.** Auf Iburi ist das in Gorkha trainierte Gelände- + PGA-Modell nicht besser als Neigung + PGA (0,826 gegenüber 0,841; H1 gescheitert). Erdbebentraining schlägt zwar Monsuntraining (H2 bestanden), aber beide liegen unter der Neigung allein. Der Regenarm war mangels Umriss nicht testbar. Explorative Ursache: Hochgebirge und Hügelland haben kaum gemeinsame Geländewerte. Details: `reports/susceptibility_v02/PHASE4_RESULTS.md`. v02 ist abgeschlossen; Iburi ist jetzt gesehen. Details: `reports/susceptibility_v02/SENSITIVITY_GORKHA_20KM.md`.
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

## V0.6: hydrologische Regenmerkmale (15.10.2026, abgeschlossen, explorativ)

Aus den bereits zwischengespeicherten stündlichen INCA-Reihen wurden 23 Merkmale berechnet (Vorregen-Index mit Halbwertszeit 3 und 14 Tagen, stärkste 3/6/12/24/72-Stunden-Regensummen samt Zeitpunkt, Nasstage, Trockenperioden, Regen plus Schneeschmelze); registriert in `config/v06.json` vor der Berechnung, gleiche 418 Gruppen, gleiche gesperrte CV-Aufteilung wie V0.5. **Kein belegter Zusatznutzen**: bedingte logistische Regression kombiniert 0,851 → 0,838 (Differenz −0,013, Intervall [−0,029; +0,016]); Gradient Boosting +0,010 [−0,005; +0,071]. Bericht `reports/v06/summary.md`. Infrastruktur: GitHub-CI, Registrierungsskript.

## V0.7: Meldebias-Kontrolle mit OpenStreetMap (15.10.2026, abgeschlossen, explorativ)

Abstand jeder Probe zum nächsten Gebäude und zur nächsten öffentlichen Straße (OSM-Auszug Österreich, Geofabrik, ODbL, Stand 14.10.2026; `config/v07.json`, vorab registriert). Der Abstand allein trennt den gemeldeten Hang von den zehn Umgebungspunkten mit lokaler AUC **0,928** (Gelände allein 0,865): ein großer Teil der V0.5-Trennung ist Sichtbarkeit/Platzierung, zum Teil auch durch das Design (Kontrollen liegen 0,75–10 km entfernt). Werden nur Kontrollen mit ähnlichem Infrastrukturabstand (Faktor 2) behalten (173 von 418 Gruppen, 10 Einheiten), behält das infrastrukturunkundige Geländemodell 0,783 (−0,013, Intervall [−0,068; +0,031]). Bericht `reports/v07/summary.md`.

## V0.8: Case-Crossover am selben Hang (15.10.2026, abgeschlossen, explorativ)

Ereigniszeit gegen vier Referenzzeiten (±28/±56 Tage, gleiche Uhrzeit) am identischen Hang; Gelände, Landbedeckung und Infrastrukturabstand kürzen sich heraus. 376 Hänge, 23 Einheiten. Bedingte logistische Regression mit INCA-Fenstern: lokale AUC **0,818** (Intervall [0,759; 0,912]); Hydrologie-Merkmale verschlechtern sie (−0,172 [−0,293; −0,065]). Das ist ein „Wann“-Ergebnis: Ereigniszeiten sind nasser als gewöhnliche Zeiten, auch weil das Inventar Starkregenepisoden dokumentiert; es ist keine Vorhersage. Bericht `reports/v08/summary.md`.

## V0.9: ungesehene Episoden aus Medienereignissen und dem Kärntner Ereigniskataster (15.10.2026, abgeschlossen, explorativ)

Vorab registriert (`config/v09.json`), bevor eine V0.9-Auswahl, Prüfung, Datenabfrage oder Modellanpassung lief. Zwei neue Quellen von Ereignissen, die noch kein Talwacht-Modell gesehen hat: GeoSphere-Medienereignisse (bisher nur gezählt) und der Kärntner Ereigniskataster (CC BY 4.0, ohne Positionsgenauigkeit, Tagesdatum nicht verlässlich; deshalb t0 drei Tage vor dem gemeldeten Tag, nur Vorbedingungen). Ungesehen heißt: kein gemeinsamer Abhängigkeitsblock mit einem V0.4-Ereignis. Das V0.4-Rezept wurde einmal auf allen 423 V0.4-Gruppen trainiert und dann genau einmal bewertet.

- **Prozessprüfung der 40 ungesehenen Medienereignisse an öffentlichen Meldungen:** 8 Rutschungen bestätigt, 7 andere Prozesse (meist Hochwasser), 1 unklar, 24 nicht auffindbar. Das registrierte Qualitätskriterium ist verfehlt; die Medienkennzeichnung ist für sich nicht verlässlich.
- **Bestand:** Medien 24 Gruppen / 14 Einheiten, Kärnten 21 / 16, zusammen 45 / 30. Viele Kandidaten fallen weg, weil sie über Tagesketten mit gesehenen V0.4-Stürmen verbunden sind.
- **Ergebnis (explorativ):** Medien: Gelände allein **0,770** (deutlich über Zufall), Gelände + Wetter 0,752, **Wetterzusatznutzen −0,019 [−0,121; +0,082]**. Kärnten und gemeinsam ebenfalls kein Nutzen. Von 72 Vergleichen zeigt nur Gradient Boosting bei den Medien einen positiven Zusatznutzen mit Intervall über null; bei so vielen Vergleichen ist das kein Beleg.
- Bericht `reports/v09/summary.md`, Nachweis `reports/v09/verification.json` (PASS). Rohdaten, Meldungs-URLs und Probenvorhersagen bleiben lokal.
## Extremwetter am Ereignisort: Case-Crossover (18.10.2026, explorativ)

V0.4 vergleicht Hänge am selben Tag und kann daher nicht zeigen, ob Extremwetter **mehr** Ereignisse auslöst. `extremwetter_v01` vergleicht deshalb denselben Ort an verschiedenen Tagen: SPARTACUS-Tagesregen vor dem Ereignis gegen dieselben Kalendertage (±15) der Jahre 1991–2025. Das Design wurde vor jedem Ergebnis registriert (`config/extremwetter_v01.json`); die Primärfenster enden um 07:00 des Vortags.

- 422 Ereignisse, **35 unabhängige Episoden**. Alle waren schon gesehen, daher **explorativ**.
- Extrem nasse Fenster sind stark überrepräsentiert: 3 Tage über dem örtlichen 95. Perzentil in **24,6 %** der Episoden statt 5 %. Ratenverhältnis 6,2 [2,5; 11,7]. Das bleibt so ohne den Stanz-Sturm und mit anderen Referenzzeiträumen; der Placebotest ist unauffällig.
- Der vorab festgelegte Mittelwerttest (3 Tage: 0,587 [0,481; 0,691]) ist **knapp nicht erfüllt**. Grund sind zwei Muster: tagelanger Vorregen oder Gewitter erst am Ereignistag, das das strikte Fenster nicht sieht.
- Meldebias (vollständigere Erfassung nach Unwettern) kann den Zusammenhang verstärken. Es ist ein Zusammenhang, keine Kausalität.
- Ein Bestätigungsplan für neue Sturmepisoden ist vorab eingefroren, aber noch nicht ausgeführt.

Bericht: `reports/extremwetter_v01/summary.md`; Web-API `GET /api/extremwetter`.

## Webdemonstration: Jury-Einstieg und Forschungsbereich (18.10.2026)

Auf ausdrücklichen Nutzerauftrag vom 18.10.2026 ersetzt ein Jury-Einstieg die bisherige Startseite. Hauptnavigation: **Start** (`#/start`, Problem, Wirkungskette Prüfpunkt → Auslauf → Infrastruktur, drei Kernzahlen, sichtbare Grenze, belegte Quellen) · **Demo** (`#/pruefgebiete`) · **Ergebnisse** kurz (`#/befunde`: V0.4-Test mit Intervall, Gelände gegen Wetter, Schwäche bei reinen Hangmuren, Extremwetter-Abschnitt) · **Methodik & Grenzen** (`#/methodik`) · **Forschung** (`#/forschung`). Die drei bisherigen Seiten Projekt, Vorgehen und Ergebnisse bleiben inhaltlich unverändert als Forschungsbereich unter ihren alten Adressen (`#/projekt`, `#/vorgehen`, `#/ergebnisse/...`); alte Lesezeichen führen weiter zum selben Inhalt.

Modellkennzahlen kommen nur aus den API-Bündeln (`/api/results_v04`, `/api/benchmarks`, `/api/pruefgebiete`, `/api/hangmuren_pilot`, `/api/extremwetter`), immer mit Intervall. Für Modellwerte gelten die Begriffe Prüfstufe, Rangfolge, Szenario; ein Wortlauttest verhindert Wahrscheinlichkeits-, Risiko- und Vorhersagewörter auf den Jury-Seiten. Aussagen zum Problem sind mit überprüfbaren Quellen belegt (GeoSphere Austria/Nature 2025, BMLUK, Schlögl et al. 2021 als Gegenbefund).

### Vorherige Fassung: drei Seiten (15.10.2026)

Die lokale Oberfläche führt über **Projekt → Vorgehen → Ergebnisse**. Direkte Routen: `/#/projekt`, `/#/vorgehen`, `/#/ergebnisse`; alte Abschnittslinks werden weiter zugeordnet. Der Einstieg erklärt den retrospektiven Prototyp, die Vorgehensseite zeigt die Schrittfolge und das reale Baseline-Beispiel, die Ergebnisse trennen V0.4-Test und explorative V0.5. Karten, Wetterkurven, Modellvergleiche und historische Analysen bleiben in aufklappbaren Bereichen erreichbar.

Kennzahlen und Intervalle kommen aus den vorhandenen API-Bündeln. V0.5-Wiederholungsspannen sind ausdrücklich keine Konfidenzintervalle; das Bootstrap-Intervall der ersten Wiederholung wird separat gezeigt. Keine wissenschaftlichen Artefakte oder Modelle wurden verändert.
## Pipeline B: Satellitenbilder vor und nach bekannten Ereignissen (15.10.2026, Stufe 5 auf allen geeigneten Ereignissen; satellite-0.2 Kandidatenprüfung)

Ein **getrenntes System** (`preslide/satellite/`, Ausgaben nur unter `data/satellite/`, `reports/satellite/`), das Sentinel-2-Aufnahmen vor und nach dokumentierten Ereignissen vergleicht, um die sichtbare Veränderungssignatur zu lernen und später undokumentierte Kandidaten zu finden. Es verwendet absichtlich Nachher-Bilder und darf **niemals** in das Vorhersagemodell (Abschnitte oben, „Pipeline A“) einfließen; Tests sichern die Trennung.

- Aufnahmen werden nicht „zur Mittagszeit“ abgefragt, sondern aus allen Überflügen (180 Tage vorher, 120 Tage nachher) die zeitlich nächsten gewählt, die **lokal** im Ausschnitt wolken-, schatten- und schneefrei sind (Szenenklassifikation plus NDSI-Schneetest, weil eine komplett verschneite Szene nur 2 % Schnee meldete). Ereignis und mindestens vier seiner fünf Kontrollhänge müssen auf demselben Überflug brauchbar sein; der Ereignistag wird nie verwendet; Paare mit mehr als 90 Tagen Jahreszeitabstand sind ausgeschlossen.
- Radiometrie: Die beiden Earth-Search-Sammlungen speichern den Reflexionsoffset unterschiedlich (c1 mit, alt ohne), obwohl die Metadaten dasselbe behaupten; empirisch geprüft, Laufzeitkontrolle eingebaut.
- Alle 137 Ereignisse ab 2018 mit Position ≤ 20 m geprüft: **129 brauchbare Gruppen, 15 unabhängige Einheiten, 724 Proben** (Median 9 Tage vor und 9 Tage nach dem Ereignis). Kontaktbögen (22) stichprobenartig gesichtet: Vorher/Nachher decken sich, bei vielen Ereignissen ist der Vegetationsverlust genau an der gemeldeten Position sichtbar, bei kleinen Rutschungen nicht.
- Basislinie (Ereignis gegen seine Kontrollen, Einheiten nie im Training): lokale AUC **0,79–0,80** (Zufall 0,5; Permutationsnull 95 % 0,56, p = 0,01; Top-1 0,56–0,59 gegen 0,18). Abkürzungstest „nur Umgebung“ liegt bei 0,56–0,63: Die Umgebung gemeldeter Hänge verändert sich anders als die von Kontrollen (Sturmcluster, Landbedeckung); das kann das Modell mitnutzen.
- Wiederentdeckung im 2,56-km-Ausschnitt (Modell hat die Episode nie gesehen): 61 von 129 innerhalb 160 m gefunden, 8 auf Rang 1, 27 unter den ersten drei, Ortsfehler median 70 m, 4,7 Kandidaten je km². Zufällige Reihenfolge der Kandidaten ergäbe Rang 1 bei etwa 11 % der gefundenen Ereignisse. **Die Unterscheidung Ereignis gegen Kontrolle ist deutlich; die Ortung im offenen Ausschnitt ist nur mäßig besser als Zufall.**
- 1 484 Treffer außerhalb der Suchposition sind **satellitengestützte Kandidaten, nicht unabhängig bestätigt** (`validation_status = UNVERIFIED`), 578 davon nahe anderer bekannter Ereignisse; keiner wird automatisch zum Ereignis. Berichte: `reports/satellite/`, Weboberfläche Abschnitt 08.
- **satellite-0.2 (15.10.2026):** Treffer im Umkreis von 160 m um ein *anderes* bekanntes V0.4-Ereignis werden aus der Rangliste entfernt (dokumentierte Ereignisse, keine Fehlalarme); Rang-1-Wiederentdeckung steigt von 8 auf 11 von 129, 70 solche Treffer entfernt.
- **Kandidatenprüfung:** Die 30 höchstbewerteten Kandidaten (mehr als 160 m von allen 423 V0.4-Ereignissen entfernt, Mehrfachtreffer derselben Stelle zusammengefasst) wurden auf Persistenz in einer späteren Aufnahme (`after_confirm`, Regel vorab festgelegt) geprüft und auf Kontaktbögen gesichtet: **kein Kandidat LIKELY, 21 REJECTED, 9 UNVERIFIED.** 20 von 30 sind Wolken-, Dunst- oder Schattenränder in einem der beiden Bilder (die Paare werden nur im 960-m-Fenster um das Quellereignis auf Wolken geprüft, Sen2Cor erkennt dünne Wolkenränder nicht), dazu 2 abgeerntete Felder, 2 Seeflächen, 1 linearer Hochwasser-/Baustreifen. 87% der Top 30 liegen innerhalb von 100 m eines wolkenartigen SCL-Pixels, bei den wiederentdeckten bekannten Ereignissen sind es 16%. **Die Rangfolge nach Rohscore ist derzeit nicht brauchbar;** die nächste Version muss den gesamten Ausschnitt auf Wolken prüfen.
- **Harte Zufallsnegative (RANDOM_LANDSCAPE):** 386 Zufallspunkte 1,5–8 km um die Ereignisse, außerhalb der V0.4-Ausschlussradien (mindestens 400 m), auf denselben Aufnahmen, ohne Geländematching. Der nur mit Kontrollen trainierte Detektor bewertet sie im Mittel mit p = 0.43 (Kontrollen 0.35, Ereignisse 0.60); Ereignis gegen Zufallspunkt AUC 0.66. Mit ihnen trainiert: 0.69 (lokale AUC gegen Kontrollen 0.78 → 0.74); Wiederentdeckung damit 63/129, Rang 1 8, 4.8 Kandidaten je km².
- **Baseline C** (eingefrorener ResNet-18 mit ImageNet-Gewichten, CPU, optionales torch): lokale AUC 0.53 – generische Bildmerkmale übertragen sich nicht; die handgemachten Indexkontraste (0,79–0,80) bleiben.
- Offen: Wolkenprüfung über den gesamten Ausschnitt (erste Änderung für satellite-0.3), erneute Kandidatenprüfung, Sentinel-1 (kein terrainkorrigiertes Produkt auf Earth Search), kleine Suche in unbekanntem Gebiet.

## Wirkungskette (18.10.2026, Demonstration, Branch claude/wirkungskette-v01-f4836f)

Die Prüfgebiete-Seite zeigt für das Demogebiet Stanz (25.07.2016) die Kette relative Prüfpunkte → Auslaufszenario → Infrastruktur im Szenario. Prüfpunkte kommen aus dem eingefrorenen V0.4-Geländemodell, relativ zu einem Umkreis von 1–10 km. Der Auslauf ist eine deterministische D8-Route mit vier Literatur-Reichweiten und ausdrücklich **unvalidiert**, weil das Inventar keine Auslaufgeometrien enthält. Die Infrastruktur stammt aus OpenStreetMap. Explorativ konzentrieren die Prüfstufen die dokumentierten Stanz-Ereignisse nicht (Stufe 1: 3,4 % der Ereignisse bei 5 % Fläche). Keine Eintritts- oder Schadensaussage, keine kombinierte Stufe. Details: `reports/wirkungskette_v01/summary.md`.

Gegenprobe v02 (vorab registriert): Mit 24 Schadensmeldungen aus Gasen 2017/2018 als Startpunkt passen Szenario und Meldung qualitativ zusammen (Straße im Szenario bei 21–22 von 22 Straßenschäden), aber 20 dieser Punkte liegen schon höchstens 25 m neben einer Straße. Die Übereinstimmung entsteht also am Punkt selbst; den Auslauf bestätigt sie nicht. Ohne Angabe, ob ein Punkt Anriss oder Schadensort ist, bleibt der Auslauf unvalidiert. Details: `reports/wirkungskette_v02/gegenprobe.md`.

Nullreferenz v03 (vorab registriert): Hangpunkte derselben Gegend ohne Inventareintrag haben im längsten Szenario ebenfalls meist eine Straße (79 %), aber nur 4 % liegen höchstens 25 m neben einer Straße, gegenüber 20 von 22 Schadenspunkten. Der Unterschied liegt also in der Lage der gemeldeten Punkte an der Straße, nicht im Auslauf. Mit nur 2–3 unabhängigen Ereigniseinheiten ist das eine Beschreibung, kein Befund. Details: `reports/wirkungskette_v03/nullreferenz.md`.

## Genau eine nächste wissenschaftliche Priorität

**Die Wetterfrage ist für dieses Design und die 1-km-Auflösung beantwortet: Ein Wetterzusatznutzen ist in keiner Variante belegt (V0.4-Test, V0.5/V0.6, V0.9 auf ungesehenen Episoden), der Gelände- und Landbedeckungseffekt wiederholt sich.** Mehr saubere unabhängige Einheiten liefert nur noch ein vorwärts gerichteter Test mit Ereignissen nach dem 15.10.2026 (jetzt registrieren, bewerten ab 15 neuen Einheiten; INCA v1 endet im Dezember 2026, der Übergang auf INCA v2 muss vorher festgelegt werden). Anfragen an Datenhalter (WLV-Kataster, Kärnten, Südtirol) nur nach Freigabe des Nutzers.

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
| `config/v09.json`, `reports/v09/`, `preslide/v09/` | V0.9: Registrierung, Prozessprüfung, ungesehene Episoden, einmalige Bewertung, Verifikation |
| `config/v05.json`, `reports/v05/`, `preslide/v05/` | V0.5: Registrierung, Kohorten-Freeze, CV-Ergebnisse, Bericht, Verifikation |
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
