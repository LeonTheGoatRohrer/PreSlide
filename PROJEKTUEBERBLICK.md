# Talwacht — Ziel, Projektstand und Orientierung

**Stand: 18. Oktober 2026 (Integrationsstand: `origin/main` mit V0.6–V0.9 und Pipeline B, dazu Anfälligkeit international, Wirkungskette v01–v03, Extremwetter, Jury-Website, Hangkarte, Satelliten-NN-Gerüst und die Registrierung `anfaelligkeit_at_v01`). Diese Datei zu Beginn jeder Session vollständig lesen.**
Danach `PROJECT_STATE.md` für den technischen Arbeitsstand lesen. Bei Widersprüchen die gespeicherten Artefakte prüfen; keine Ergebnisse erfinden oder historische Experimente überschreiben.

## Was ist Talwacht?

Talwacht ist ein wissenschaftlicher Machine-Learning-Forschungsprototyp für Österreich (internes Paket weiterhin `preslide`). Die Kernfrage:

> Können Umweltinformationen aus der Zeit vor einem dokumentierten Hangrutschungsereignis den betroffenen Hang von nahe gelegenen, topographisch ähnlichen Kontrollhängen unterscheiden, wenn alle Hänge zum selben Zeitpunkt betrachtet werden?

Zusatzfrage: **Bringt Wetter aus der Vorgeschichte einen wiederholbaren Nutzen gegenüber Geländedaten allein?**

Talwacht ist **kein Warnsystem**, keine Gefahrenkarte und kein Modell für die reale Wahrscheinlichkeit einer Rutschung. Modellwerte sind Rangfolgen eines retrospektiven Fall-Kontroll-Designs. Modellwichtigkeit bedeutet keine Kausalität. Schwache Ergebnisse sind gültige Ergebnisse.

## Kernbefund

- **Gelände trennt deutlich über Zufall.** Versiegelter V0.4-Test: Gelände + Wetter 0,751 [0,633; 0,866], Gelände allein 0,702, 11 unabhängige Testeinheiten. Auf ungesehenen Episoden (V0.9, Medien) Gelände allein 0,770.
- **Ein Wetterzusatznutzen ist in keiner Variante belegt** (V0.4-Test, V0.5/V0.6, V0.9). Die Wetterfrage gilt für dieses Design und die 1-km-Auflösung als beantwortet.
- **Ein Teil des Signals ist Meldebias:** Der Abstand zu Straßen und Gebäuden allein trennt im V0.5-Design mit 0,928 (V0.7).
- **Zeitlich** sind Ereigniszeiten nasser als gewöhnliche Zeiten am selben Ort (V0.8, Extremwetter): ein „Wann“-Zusammenhang, keine Vorhersage.

## Daten und Kontrollen

- Ereignisse aus dem GeoSphere-Austria-Inventar mit geprüftem Datum, Prozess und Lagekategorie. V0/Baseline: 60 Gruppen; **V0.4: 500 Kandidaten → 423 vollständige Gruppen** (Entwicklung 123 Ereignisse/19 Einheiten, versiegelter Test 300/11; Stanz 2016 allein 243).
- Je Ereignis fünf lokal gematchte Kontrollen (750 m–10 km, Neigung ±5°, Höhe ±150 m, Exposition zirkulär ±45°, ≥ 400 m Abstand untereinander, Ausschlusspuffer um bekannte Ereignisse). Kontrollen sind **Pseudo-Negative** und übernehmen den Ereignistag.
- Gelände 30 m (Skadi-Kacheln; über Österreich praktisch identisch mit SRTMGL1 v3, Aufnahme Februar 2000), CORINE-Landbedeckung (Kartenstand vor t0), Geologie 1:500 000. Wetter INCA v1 (1 km, stündlich), SPARTACUS, SNOWGRID; Merkmale nur aus `[t0 − Fenster, t0)`.
- Unabhängige Einheiten sind zeitliche Episoden, nicht Zeilen oder Ereignisse.

## Pipeline A: Experimente zur Kernfrage

| Version | Frage / Design | Ergebnis | Status | Bericht |
|---|---|---|---|---|
| V0 | 60 Gruppen, Train/Val/Test | Original- und Steiermark-Test bereits gesehen | eingefroren | `RESULTS.md`, `reports/experiment/` |
| V0.2 | Stabilität: 4 Folds × 5 Seeds, 180 + 260 Trainings | kein robuster Wetternutzen; Modelle und Maße widersprechen sich | eingefroren | `reports/stability_v02/summary.md` |
| V0.3 | Zufallsreferenz (100 Vertauschungen) | Wetter nicht von Zufall unterscheidbar (p ≥ 0,28) | eingefroren | `reports/null_v03/summary.md` |
| Baseline | V0–V0.3 auf `046074ba6f12556c` | 95 Prüfsummen, Archiv `archive/v0.3-baseline/` | **eingefroren (§45)** | `reports/baseline/` |
| V0.4 | vorregistriert, 423 Gruppen, versiegelter Test einmal bewertet | kombiniert 0,751 [0,633; 0,866], statisch 0,702, Wetter 0,604; Zusatz +0,049 [−0,003; +0,108] **nicht belegt**; pro Ereignis 0,668 | **abgeschlossen, Test gesehen (§45)** | `reports/v04/summary.md` |
| V0.5 | gemeldeter Hang gegen 10 ungematchte Umgebungspunkte, CV | kombiniert 0,851, statisch 0,865; Zusatz −0,023 [−0,079; +0,019] | explorativ | `reports/v05/summary.md` |
| V0.6 | 23 hydrologische Regenmerkmale | 0,851 → 0,838 (−0,013 [−0,029; +0,016]) | explorativ | `reports/v06/summary.md` |
| V0.7 | Meldebias: Abstand zu Straßen/Gebäuden (OSM) | Abstand allein 0,928; mit Infrastruktur-Caliper Gelände 0,783 | explorativ | `reports/v07/summary.md` |
| V0.8 | Case-Crossover am selben Hang (±28/±56 Tage) | 0,818 [0,759; 0,912]; „Wann“-Befund | explorativ | `reports/v08/summary.md` |
| V0.9 | ungesehene Episoden (Medien, Kärnten), einmal bewertet | Medien: Gelände 0,770, kombiniert 0,752, Zusatz −0,019 [−0,121; +0,082]; Prozessprüfung der Medien gescheitert | explorativ | `reports/v09/summary.md` |

Nachweise: `reports/*/verification.json` (PASS). V0.4 wurde vor dem Test einmal geändert (Amendment 1, dokumentiert); V0.9-Ergebnisse sind wegen verfehlter Prozessprüfung und 14 < 15 Einheiten explorativ.

## Weitere Untersuchungslinien

**Extremwetter am Ereignisort (`extremwetter_v01`, explorativ).** Derselbe Ort an verschiedenen Tagen (SPARTACUS, Referenz ±15 Kalendertage 1991–2025). 422 Ereignisse, 35 Episoden, alle gesehen. 3 Tage über dem örtlichen 95. Perzentil in 24,6 % der Episoden statt 5 % (Ratenverhältnis 6,2 [2,5; 11,7]); der vorab festgelegte Mittelwerttest (0,587 [0,481; 0,691]) ist knapp nicht erfüllt. Zusammenhang, keine Ursache; Meldebias nicht trennbar. Bestätigungsplan eingefroren, nicht ausgeführt. `reports/extremwetter_v01/summary.md`, API `/api/extremwetter`.

**Wirkungskette Prüfpunkt → Auslauf → Infrastruktur (`wirkungskette_v01`–`v03`, Demonstration).** Demogebiet Stanz (25.07.2016, gesehener Test). Prüfstufen aus dem eingefrorenen V0.4-Geländemodell, relativ im Umkreis 1–10 km; Auslauf als D8-Route mit Literatur-Reichweiten, **unvalidiert**; Infrastruktur aus OSM (heutiger Stand). Die Prüfstufen bündeln die Stanz-Ereignisse nicht (Stufe 1: 3,4 % der Ereignisse auf 5 % der Fläche). v02-Gegenprobe an 24 Schadensmeldungen (Gasen): Straße im Szenario bei 21–22 von 22, aber 20 Punkte liegen schon ≤ 25 m neben einer Straße. v03-Nullreferenz: Hangpunkte ohne Meldung haben im längsten Szenario ebenfalls meist eine Straße (79 %), aber nur 4 % liegen ≤ 25 m daneben. Die Übereinstimmung entsteht an der Meldeposition, nicht im Auslauf; 2–3 Einheiten, beschreibend. `reports/wirkungskette_v01|v02|v03/`.

**Pipeline B: Sentinel-2 vorher/nachher (getrennt von Pipeline A, nutzt absichtlich Nachher-Bilder).** 129 Gruppen, 15 Einheiten: Ereignis gegen Kontrolle lokale AUC 0,79–0,80 (Permutationsnull 0,56). Ortung im offenen 2,56-km-Ausschnitt nur mäßig besser als Zufall (61/129 gefunden, 11 auf Rang 1 nach satellite-0.2). Von den 30 bestbewerteten neuen Kandidaten ist keiner bestätigt (21 verworfen, meist Wolken-/Dunstränder). Nächster Schritt satellite-0.3: Wolkenprüfung über den ganzen Ausschnitt. `reports/satellite/`.

**Anfälligkeit international (`susceptibility_v01`, `v02`, abgeschlossen).** Polygoninventare aus Nepal (Gorkha 2015, Far-Western Nepal), Japan (Iburi 2018), Italien (RER2023). v01: Gelände überträgt zwischen Regionen nicht besser als die Neigung allein (+0,006 [−0,005; +0,017]), Gate nicht bestanden. v02 (je Auslöser): auf Iburi Gelände + PGA 0,826 gegen Neigung + PGA 0,841, **nicht belegt**; Regenarm mangels Kartierumriss nicht testbar; Iburi ist jetzt gesehen. Ein v01-Fehler (DEM-Blöcke bis 15 m verschoben) wurde dokumentiert, v01 bleibt unverändert. `reports/susceptibility_v01/PHASE4_GATE.md`, `reports/susceptibility_v02/PHASE4_RESULTS.md`.

**Hangkarte (`hangmap_v01`, Anwendung, keine neue Studie).** Seite `#/hangkarte` im Forschungsbereich: Das eingefrorene V0.5-Modell (nur Gelände, Landbedeckung, Geologie) bewertet Hangzellen in einem frei gewählten Gebiet auf einer 3D-Ansicht; angezeigt werden nur relative Anteile innerhalb einer Vergleichsgruppe (Summe 100 %). Keine Eintrittswahrscheinlichkeit, keine Gefahrenkarte. Die hohe V0.5-Trennung ist teils Meldebias (mit gematchten Kontrollen nur 0,705), die Anteile hängen stark an der Landbedeckung. In Stanz wäre das V0.5-Modell in-sample. Optionale INCA-Regenebene ist getrennt und kein Modelleingang. `reports/hangmap_v01/summary.md`.

**Hang-Check (`hangcheck_v01`, Anwendung, keine neue Studie).** Seite `#/hangcheck` in der Hauptnavigation: Ort wählen (Gemeindesuche offline, Kartenklick, eigener Standort), Schalter „Starkregen oder Unwetter erwartet“; die Karte markiert die auffälligsten Hänge im Umkreis 1–3 km (Prüfstufe 1 = oberste 5 %, Prüfstufe 2 = nächste 15 %) und fünf Prüfpunkte „Hier zuerst hinschauen“. Eingefrorenes V0.4-Geländemodell, kein Wetter, der Schalter ändert die Einstufung nicht. Nicht markiert heißt nicht sicher; keine Warnung; Siedlungsflächen heben die Einstufung (möglicher Meldeeffekt). Optional je Prüfpunkt ein möglicher Fließweg (Szenario, ungeprüft; Reichweiten 45 m und 467 m aus der Literatur) mit Straßen und Gebäuden laut heutigem OpenStreetMap-Stand; Prüfpunkte an Straßen haben fast immer Straßen im Szenario. Beispiele und zwölf Talorte sind vorberechnet (`python -m preslide.hangcheck prewarm`).

**Hangmuren-Anfälligkeit Österreich (`anfaelligkeit_at_v01`, registriert, noch kein Ergebnis).** Vorregistriert: statisches Modell für genau verortete reine Hangmuren, Leave-one-area-out gegen Neigung allein (Plan `reports/weiterentwicklung_2026-10-18/TRAININGSPLAN_ALLE_INVENTARDATEN.md`). Amendment 1: Skadi über Österreich ist praktisch SRTMGL1. Pipeline und Sicherheitstests sind integriert, das Experiment ist nicht gelaufen.

**Neuronale Murensuche (`satellite_nn_v01`, nur Gerüst).** Kachelung, Entscheidungslogik, Modelle A/B und Tests; keine Daten, kein Training, nicht registriert. Plan `reports/weiterentwicklung_2026-10-17/NEURONALE_MURENSUCHE_PLAN.md`; Landslide4Sense-Download wartet auf Freigabe.

**Hangmuren-Pilot (`mudslide_cascade_v01`, explorativ, nicht im Repository).** Gelände trennt reine Hangmuren kaum (lokale AUC 0,539 [0,406; 0,669]). Der Bericht liegt nur lokal; `/api/hangmuren_pilot` liefert ohne ihn 503.

## Was nicht geht

Eine Wahrscheinlichkeit, dass an einem bestimmten Hang eine Mure abgeht, kann das Projekt nicht liefern: Das Design ergibt Rangfolgen, keine Häufigkeiten; das Inventar enthält nur Punkte (Anriss, Weg oder Ablagerung unbekannt); ein Wetternutzen bei 1 km ist nicht belegt; der Auslauf ist nicht prüfbar. Warnung, Gefahrenkarte oder Schadensvorhersage sind nicht belegt. Begründung: `reports/weiterentwicklung_2026-10-18/PROJEKTBEWERTUNG_VOR_ZUSAMMENFUEHRUNG.md`.

## Webdemonstration (Jury-Einstieg seit 18.10.2026)

Python/FastAPI, Vue 3/Vite/MapLibre, CPU-Betrieb; Start `scripts/start.ps1` (üblich `http://127.0.0.1:8000`). Hauptnavigation: **Start** (`#/start`) · **Hang-Check** (`#/hangcheck`, Ort wählen und Starkregen-Ansicht, eingefrorenes V0.4-Geländemodell) · **Demo** (`#/pruefgebiete`, Ereignisübersicht und Wirkungskette) · **Ergebnisse** kurz (`#/befunde`, inkl. Extremwetter und Hangmuren-Pilot) · **Methodik & Grenzen** (`#/methodik`) · **Forschung** (`#/forschung`). Die früheren Seiten Projekt, Vorgehen und Ergebnisse bleiben inhaltlich unverändert als Forschungsbereich unter ihren alten Adressen; dort liegt auch die Hangkarte (`#/hangkarte`). Kennzahlen kommen nur aus den API-Bündeln, immer mit Intervall; ein Wortlauttest verhindert Wahrscheinlichkeits-, Risiko- und Vorhersagewörter auf den Jury-Seiten. Meisterprompt für die geplante Überarbeitung: `reports/weiterentwicklung_2026-10-18/MEISTERPROMPT_JURY_WEBSITE.md`.

## Noch nicht integriert

- `claude/wirkungskette-v02-gebietstest`: vorregistrierter Test der Prüfstufen an ungesehenen Hangmuren-Gebieten (Vorarlberg/Tirol 2005 u. a.), Pilot und Amendment 1 vorhanden, Volllauf nicht abgeschlossen. Kollidiert im Namensraum mit der v02-Gegenprobe; laut Amendment 1 zieht er nach dem Volllauf nach `wirkungskette_gebietstest_v01` um.
- `reports/mudslide_cascade_v01/` und der zugehörige Code liegen nur lokal (uncommittet).

## Nächste Prioritäten

1. **UI-Arbeit** auf diesem gemeinsamen Stand (Nutzerwunsch), mit den bestehenden Wortlaut- und Intervallregeln.
2. Schutzprüfungen reparieren: Auf `origin/main` wurden geschützte Dateien geändert (`requirements-lock.txt` durch V0.7, Original-Code durch die Ruff-Bereinigung `b93b937`), deshalb scheitern Baseline-Manifest-, Stabilitäts- und V0.5-Integritätsprüfung. Kein eingefrorenes Ergebnis ist betroffen; die geschützten Bytes müssen wiederhergestellt werden. Danach den Gebietstest der Prüfstufen abschließen und integrieren (Namensraumumzug laut Amendment 1).
3. Vorwärts gerichteter Test mit Ereignissen nach dem 15.10.2026 vorab registrieren (bewerten ab 15 neuen Einheiten; Übergang INCA v1 → v2 vor Dezember 2026 festlegen). Anfragen an Datenhalter nur nach Freigabe des Nutzers.

## Feste Regeln für weitere Sessions

- Nur reale Daten; niemals erfundene Messwerte, Ersatzereignisse oder Kennzahlen.
- Keine Zukunftsinformation in Merkmalen; keine Trennung zusammengehöriger Ereignis- oder Abhängigkeitsgruppen.
- Gelernte Vorverarbeitung nur am jeweiligen Training anpassen; keine Auswahl nach gesehenen Testergebnissen, keine Seed-Suche, kein Nachjustieren der Kontrollen.
- Neue Experimente in eigenem Namensraum, vor der Modellierung registrieren; Änderungen als Amendment mit Grund. Eingefrorene Artefakte (AGENTS.md §45) nie ändern.
- Caches und gültige Checkpoints verwenden; Wetter, Gelände und fertige Läufe nicht unnötig neu berechnen.
- Oberfläche: Jury-Einstieg plus Forschungsbereich (Projekt, Vorgehen, Ergebnisse im Detail, Hangkarte); die Forschungsseiten unter ihren alten Adressen erhalten; grundlegende Umgestaltungen nur auf Auftrag.
- Rohdaten und Probenvorhersagen bleiben lokal. Die GeoSphere-Quelle hat keine geklärte spezifische Weiterverwendungslizenz; lokale nicht kommerzielle Forschung ist vom Nutzer autorisiert.
- Passende vorhandene Skills dürfen ohne erneute Nachfrage verwendet werden; das ist keine Erlaubnis für Veröffentlichung oder externe Kommunikation.

## Wo finde ich was?

| Datei/Verzeichnis | Zweck |
|---|---|
| `AGENTS.md` | Verbindliche Arbeits- und Wissenschaftsregeln |
| `PROJECT_STATE.md` | Kompakter technischer Stand und nächste Aufgaben |
| `reports/baseline/`, `archive/v0.3-baseline/` | Eingefrorene V0.3-Baseline mit Prüfsummen |
| `config/v04.json`, `reports/v04/`, `preslide/v04/` | V0.4: Präregistrierung, Freeze, versiegelter Test |
| `config/v05.json` … `config/v09.json`, `reports/v05/` … `reports/v09/`, `preslide/v05/` … `preslide/v09/` | V0.5–V0.9 |
| `config/satellite.json`, `preslide/satellite/`, `reports/satellite/` | Pipeline B |
| `config/extremwetter_v01.json`, `preslide/extremwetter/`, `reports/extremwetter_v01/` | Extremwetter |
| `config/wirkungskette_v0*.json`, `preslide/wirkungskette/`, `reports/wirkungskette_v0*/` | Wirkungskette v01–v03 |
| `preslide/pruefgebiete/` | Ereignisübersicht für die Demo-Seite |
| `config/susceptibility_v0*.json`, `preslide/susceptibility/`, `reports/susceptibility_v0*/` | Anfälligkeit international |
| `config/anfaelligkeit_at_v01.json`, `preslide/anfaelligkeit_at_v01/`, `reports/anfaelligkeit_at_v01/` | Hangmuren-Anfälligkeit Österreich (registriert) |
| `config/satellite_nn_v01.json`, `preslide/satellite_nn/` | Neuronale Murensuche (Gerüst) |
| `config/hangmap_v01.json`, `preslide/hangmap/`, `reports/hangmap_v01/` | Hangkarte (3D, relative Anteile, V0.5-Modell) |
| `config/hangcheck_v01.json`, `preslide/hangcheck/`, `frontend/src/HangCheckPage.vue` | Hang-Check (Prüfstufen im Umkreis, V0.4-Geländemodell, kein Wetter) |
| `reports/weiterentwicklung_2026-10-1*/` | Pläne, Meisterprompts, Projektbewertung |
| `METHODOLOGY.md`, `DATA_SOURCES.md`, `RESULTS.md`, `LIMITATIONS.md`, `README.md` | Methodik, Quellen, historische Ergebnisse, Grenzen, Einrichtung |

## Pflege dieser Datei

Nach einem wesentlichen Meilenstein den Stand und die offenen Punkte aktualisieren. Abgeschlossenes nicht erneut als offen aufführen. Kennzahlen gegen gespeicherte Ergebnisse prüfen; Details gehören in die Berichte, nicht hierher.
