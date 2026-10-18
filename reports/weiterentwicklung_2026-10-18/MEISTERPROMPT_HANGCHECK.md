# Meisterprompt: „Hang-Check bei Starkregen“ (`hangcheck_v01`)

Diesen Text vollständig als Auftrag in eine neue Session geben. Er ist so vorbereitet, dass die Session ohne
Rückfragen durcharbeiten kann. Entscheidungen in Abschnitt 3 sind gefallen und werden nicht neu diskutiert.

---

## 0. Auftrag in einem Satz

Baue in Talwacht eine neue Seite **„Hang-Check“**: Man wählt seinen Ort, setzt den Schalter **„Starkregen oder
Unwetter erwartet“**, und die Karte markiert die Hänge im Umkreis, die man **zuerst ansehen** sollte, dazu
optional mögliche Fließwege und Straßen/Gebäude darin. Keine Wetterdaten, keine Mengeneingabe, keine
Wahrscheinlichkeit.

Zeitrahmen: **Wettbewerbsschluss ist heute (18.10.2026).** Arbeite in der Reihenfolge von Abschnitt 6 und halte
die Schnittlinie ein: Erst muss die Kernseite fertig, getestet und committet sein, dann kommen Zusatzteile.

## 1. Start der Session (kurz halten)

1. `AGENTS.md`, `PROJEKTUEBERBLICK.md` (vollständig) und `PROJECT_STATE.md` lesen. Sonst nur die in Abschnitt 4
   genannten Dateien öffnen.
2. Eigenen Branch `claude/hangcheck-v01` von `origin/claude/integration-2026-10-18` anlegen (`git fetch` vorher).
   Dort liegt der aktuelle gemeinsame Stand mit Hangkarte, Wirkungskette und Jury-Website.
3. Im Worktree fehlen `data/`, `models/`, `.venv/`, `frontend/node_modules`. Junctions zum Hauptcheckout
   `C:\Users\mario\Documents\HomeProjects\PreSlide` anlegen: kleine `.cmd`-Datei mit `mklink /J`-Zeilen in den
   Scratchpad schreiben und mit `cmd //c` ausführen (PowerShell `New-Item -ItemType Junction` wird blockiert).
4. Kurz prüfen, dass die App startet (`.claude/launch.json`, Konfiguration `preslide-api`, Port 8010; vorher
   `npm run build` in `frontend/`).

## 2. Nutzerfluss (so soll es sich anfühlen)

1. **Ort wählen**: eine der drei Möglichkeiten
   - Gemeinde eintippen (Vorschlagsliste, Umlaute, gleichnamige Gemeinden unterscheidbar),
   - auf die Karte klicken,
   - Knopf „Mein Standort“ (Browser-Ortung; nur zur Kartenauswahl, wird nirgends gespeichert oder weitergegeben).
   Dazu ein Umkreis-Regler 1–3 km (Standard 2 km) und die drei vorhandenen Beispielgebiete.
2. **Schalter „Starkregen oder Unwetter erwartet“** (Checkbox/Toggle).
   - Aus: Karte mit Ort und Umkreis, kurzer Satz „Schalter aktivieren, um zu sehen, welche Hänge man bei
     Starkregen zuerst ansehen sollte.“
   - An: Die Berechnung läuft (Ladeanzeige), danach erscheint der Layer.
3. **Ergebnis**:
   - Rot = **Prüfstufe 1** (oberste 5 % der bewertbaren Hangzellen im Umkreis), Orange = **Prüfstufe 2**
     (nächste 15 %), alles andere ohne Farbe.
   - Kurzliste „Hier zuerst hinschauen“: die 5 Prüfpunkte der Stufe 1 (mind. 300 m auseinander) mit Höhe, Neigung,
     Landbedeckung in Klartext.
   - Optional (Abschnitt 6, Schritt 5): je Prüfpunkt ein möglicher Fließweg hangabwärts und die Zahl der
     Straßen/Gebäude darin.
   - Ein fester, sichtbarer Hinweisblock (Abschnitt 3.4).

## 3. Feste Entscheidungen

### 3.1 Wissenschaftliche Grundlage
- **Modell**: das eingefrorene V0.4-Gelände-Modell
  `models/v04/final_c6d67a854ba7/conditional_logit_static.joblib`
  (SHA-256 `fbce46ad7f25e43e9ca954b177f4a5dea2e40680fa5fa035217cfcba15e753b4`), nur lesen, nie neu trainieren.
  Begründung: trainiert nur auf den 123 Entwicklungsereignissen, mit gematchten Kontrollen (weniger Meldebias als
  V0.5), am versiegelten Test geprüft (Gelände allein 0,702) und im Gebietstest an ungesehenen Hangmuren-Gebieten
  besser als Neigung allein. Die Wirkungskette nutzt dasselbe Modell (`config/wirkungskette_v01.json`).
  **Nicht** das V0.5-Modell der Hangkarte verwenden.
- **Merkmale**: Gelände 30 m, Landbedeckung CLC2018, Geologie 1:500 000, genau wie in der Hangkarte berechnet.
  Die Spaltenliste muss **exakt** `preslide.v04.models.STATIC` entsprechen (Reihenfolge eingeschlossen). Bei
  Abweichung laut abbrechen, nie still auffüllen oder umsortieren.
- **Einstufung**: rein relativ innerhalb des gewählten Umkreises, mit derselben Klassenlogik wie
  `preslide/wirkungskette/core.py::review_classes` (5 % / 15 % / Rest). Zellen ohne Landbedeckung oder Geologie,
  unter 5° Neigung oder außerhalb Österreichs werden nicht bewertet und **gezählt** angezeigt.
- **Kein Wetter**: Der Schalter ruft keine Wetterdaten ab und **verändert die Einstufung nicht**. Er wählt nur die
  Ansicht für den Starkregenfall. Die API bekommt keinen Wetter- oder Schalter-Parameter. Die INCA-Regenebene der
  Hangkarte kommt auf diese Seite **nicht**.
- Neue Version im eigenen Namensraum: `config/hangcheck_v01.json`, `preslide/hangcheck/`,
  `data/hangcheck_v01/cache/`, Seite `frontend/src/HangCheckPage.vue`, Route `#/hangcheck`. Die Config hält Status
  („Anwendung des eingefrorenen V0.4-Gelände-Modells; keine neue Auswertung, kein Training, kein Test“),
  `not_claimed`-Liste wie in `config/hangmap_v01.json`, Modellpfad und Hash, Klassen, Radiusgrenzen, Quellen.
  `hangmap_v01` und `wirkungskette_v01` bleiben unverändert.

### 3.2 Wörter (Jury-Wortlauttest gilt)
- Verboten auf der Seite (Regex in `frontend/tests/wording.test.mjs`): `wahrscheinlich`, `risik`, `vorhersag`,
  `prognos`, `gefährdet`. `HangCheckPage.vue` in die Liste `juryFiles` aufnehmen.
- Stattdessen: „Hier zuerst hinschauen“, „Prüfstufe 1/2“, „auffälligste Hänge in diesem Umkreis“,
  „möglicher Fließweg (Szenario, ungeprüft)“, „liegt im Szenario“ (nie „wird getroffen“).
- Kennzahlen nie als Literal in die Seite schreiben, nur aus API-Bündeln, immer mit Intervall.

### 3.3 Daten und Datenschutz
- Gemeindesuche **offline** aus der lokal gecachten Datei
  `data/wirkungskette_gebietstest_v01/cache/gisco/LAU_RG_01M_2021_4326.geojson` (GISCO LAU 2021). Auf Österreich
  filtern (`CNTR_CODE == 'AT'`; Felder u. a. `LAU_ID`, `LAU_NAME`, `POP_2021`). Ein Bezirksfeld gibt es nicht:
  Gleichnamige Gemeinden über das Bundesland unterscheiden (erste Ziffer der Gemeindekennziffer `LAU_ID`,
  1 = Burgenland … 9 = Wien; Zuordnung im Test prüfen). Mittelpunkt als repräsentativen Punkt
  innerhalb der Gemeinde berechnen (`representative_point`, nicht Schwerpunkt), als kleine JSON-Liste in
  `data/hangcheck_v01/` mit Hash-Sidecar ablegen. Kein externer Geocoder, damit Ortsangaben nicht an Dritte gehen.
  Fehlt die Datei: aus GISCO neu laden und Herkunft in `DATA_SOURCES.md` eintragen.
- Browser-Ortung nur clientseitig zur Kartenauswahl; Koordinaten nicht loggen, nicht in die URL schreiben.
- OSM-Infrastruktur (nur Schritt 5) über die vorhandene Overpass-Logik der Wirkungskette, gecacht, als
  „heutiger OpenStreetMap-Stand“ beschriftet.

### 3.4 Pflicht-Hinweisblock (sichtbar, nicht nur im Tooltip)
1. **Nicht markiert heißt nicht sicher.** Die Einstufung ist relativ: In jedem Gebiet sind Hänge markiert, auch
   wenn dort nichts passiert, und auch nicht markierte Hänge können abgehen.
2. Talwacht ist **keine Warnung**. Für aktuelle Unwetterwarnungen die offiziellen Stellen nennen: GeoSphere Austria
   und die Landeswarnzentralen; im Notfall Notruf 112 bzw. Feuerwehr 122. **Links nur setzen, wenn die URL in
   dieser Session tatsächlich geprüft wurde**, sonst nur den Namen der Stelle nennen.
3. Grundlage: Gelände (Höhenmodell Stand 2000), Landbedeckung 2018, Geologie 1:500 000; kein Wetter, kein
   Untergrund im Detail, keine Schutzbauten. Mehr unter „Methodik & Grenzen“.
4. Das Modell hat aus gemeldeten Ereignissen gelernt; ein Teil der Unterschiede kann daher von der Meldung kommen
   (z. B. Nähe zu Straßen), nicht vom Hang selbst.

### 3.5 Zielgruppe und Ton
Hauptnutzer: Gemeinden, Feuerwehr, Straßenerhalter („wo zuerst kontrollieren“). Für Bürger verständlich, aber ohne
Sicherheitsversprechen. Keine eigenen Verhaltensratschläge erfinden; nur auf offizielle Stellen verweisen. Sprache
Deutsch, kurze Sätze, keine Fachwörter ohne Erklärung.

## 4. Was es schon gibt (wiederverwenden, nicht neu schreiben)

| Baustein | Datei | Nutzen für Hang-Check |
|---|---|---|
| Rechnen für beliebigen Ort in AT | `preslide/hangmap/build.py` (`terrain_cells`, `land_cover_cells`, `geology_cells`, `build_features`, `eligibility`, `inside_austria`, `cached_json`) | Merkmale je 90-m-Zelle; nur das Modell und die Einstufung austauschen |
| API-Muster mit Lock und Cache | `preslide/hangmap/routes.py`, `config/hangmap_v01.json` (`cache`) | Vorlage für `/api/hangcheck` |
| Prüfstufen, Prüfpunkte, Fließweg | `preslide/wirkungskette/core.py` (`review_classes`, `select_release_points`, `d8_route`, `fixed_reach_stop`, `corridor`, Infrastruktur-`hits`, `count_by_type`, `banned_words`) | reine Funktionen, schon getestet |
| V0.4-Modell laden + Spaltenprüfung | `preslide/wirkungskette/build.py::model_bundle`, `preslide/v04/models.py::STATIC`, `add_one_hot` | genau so übernehmen |
| Senkenfüllung | `preslide.v04.terrain.fill_depressions` | Voraussetzung für Fließwege |
| OSM-Abruf | `preslide/wirkungskette/build.py` (`build_osm`, `parse_osm`, `classify_way`) | nur Schritt 5 |
| Karten-Seite mit 3D und Beispielen | `frontend/src/HangkartePage.vue`, `frontend/src/hangkarte.js`, `frontend/tests/hangkarte.test.mjs` | Vorlage für Karte, Layer, Ladezustände |
| Navigation, Wortlauttest | `frontend/src/navigation.js`, `frontend/src/App.vue`, `frontend/tests/wording.test.mjs`, `navigation.test.mjs` | neue Route und Menüpunkt |

Gemeinsame Hilfsfunktionen in ein Modul ziehen, wenn nötig; keine zweite Implementierung von Distanz,
Koordinatentransformation (EPSG:31287) oder Checkpoint-IO anlegen (AGENTS.md §47).

## 5. API

- `GET /api/hangcheck/orte?q=…` – höchstens 10 Gemeinden (Name, Bundesland, lon, lat).
- `GET /api/hangcheck/beispiele` – die drei Beispielgebiete aus der Config.
- `POST /api/hangcheck` mit `{longitude, latitude, radius_m}` → Zellen (Lage, Prüfstufe, Rangperzentil, Treiber in
  Klartext), Prüfpunkte, Zählungen (bewertet / ausgeschlossen nach Grund), Modell-Hash, Datenstände, Hinweistexte.
- `GET /api/hangcheck/fliesswege?…` (Schritt 5) – Fließwege der Prüfpunkte mit Szenarien 45 m und 467 m
  (Literaturwerte aus `config/wirkungskette_v01.json`) und Infrastruktur-Zählung im Korridor.
- Fehler: außerhalb Österreichs oder Radius außerhalb 1–3 km → 422 mit deutscher Meldung; laufende Berechnung → 503
  mit „bitte kurz warten“. Keine stillen Ersatzwerte.

## 6. Reihenfolge mit Zeitbudget

| # | Schritt | Budget |
|---|---|---|
| 1 | Setup (Branch, Junctions, App startet) | 15 min |
| 2 | Backend: Config, `preslide/hangcheck/` (Merkmale aus Hangmap, V0.4-Modell, Prüfstufen, Prüfpunkte), API, Gemeindeliste | 75 min |
| 3 | Frontend: `HangCheckPage.vue` mit Ortswahl (Suche, Klick, Standort), Umkreis, Schalter, Layer, Liste „Hier zuerst hinschauen“, Hinweisblock; Menüpunkt „Hang-Check“ in der Hauptnavigation und ein Knopf auf der Startseite | 75 min |
| 4 | Tests (Abschnitt 7), Browserprüfung, Doku, **Commit + Push** | 45 min |
| — | **Schnittlinie: Ab hier nur, wenn 1–4 fertig, grün und gepusht sind.** | |
| 5 | Fließwege und Straßen/Gebäude im Szenario für die Prüfpunkte | 60–90 min |
| 6 | Vorwärmen: Ergebnisse der drei Beispielgebiete und einiger bekannter Orte (z. B. Hauptorte in alpinen Tälern) in den Cache rechnen, damit die Jury-Vorführung ohne Internet und ohne Wartezeit läuft | 20 min |

Erste Berechnung messen: Wenn ein 3-km-Umkreis länger als ca. 60 s braucht, den Höchstradius auf 2 km senken
(in der Config, mit Begründung), nicht am Modell drehen.

## 7. Tests (vor dem Vertrauen einmal mit absichtlich eingebautem Fehler scheitern lassen)

Python (`tests/test_hangcheck.py`, synthetische Daten nur im Test):
1. Modell-Hash stimmt; falscher Hash → Abbruch.
2. Merkmalsspalten exakt `STATIC` in gleicher Reihenfolge; vertauschte/fehlende Spalte → Abbruch.
3. Prüfstufen: Anteil Stufe 1 ≈ 5 %, Stufe 2 ≈ 15 % der bewertbaren Zellen; gleiche Punktzahl bleibt gleiche Stufe;
   Gebiet mit sehr wenigen bewertbaren Zellen → klare Fehlermeldung statt Scheinergebnis.
4. Prüfpunkte mindestens 300 m auseinander (EPSG:31287-Meter, nicht Grad).
5. API nimmt keine Wetter- oder Schalter-Parameter an; zweimal derselbe Ort → identisches Ergebnis (Determinismus).
6. Außerhalb Österreichs und Radius-Grenzen → 422.
7. Gemeindesuche: Umlaute, Groß/Klein, gleichnamige Gemeinden, alle Punkte in Österreich.
8. Nur Schritt 5: Fließweg steigt auf der gefüllten Oberfläche nie an und endet spätestens bei der Szenario-Reichweite.

Frontend (`frontend/tests/hangcheck.test.mjs` + Wortlauttest):
- `HangCheckPage.vue` in `juryFiles`; der Test muss mit einem eingefügten „Risiko“ scheitern.
- Hinweis „Nicht markiert heißt nicht sicher“ ist im Seitentext vorhanden.
- Schalter aus → keine Layer-Anfrage; Schalter an → genau eine.
- Keine Kennzahl als Literal.

## 8. Verifikation vor „fertig“

- `.\.venv\Scripts\python -m pytest -q tests/test_hangcheck.py tests/test_hangmap.py tests/test_wirkungskette.py`,
  dann `cd frontend; npm test; npm run build`. Skip- und Fehlerzahlen ehrlich
  berichten.
- Die Verify-Skripte (`verify_state.py`, `verify_v04.py`) **nicht im Worktree** laufen lassen: Sie überschreiben dort
  `reports/v04/verification.json` mit einem CRLF-bedingten FAIL. Stattdessen mit `git status`/`git diff --stat`
  nachweisen, dass keine Datei unter `reports/v04/`, `reports/baseline/`, `archive/` oder `config/v04.json`
  verändert wurde.
- Browser (eingebauter Browser, `preview_start` mit `preslide-api`): Desktop und 375 px; die drei Beispielgebiete,
  eine eingetippte Gemeinde (z. B. eine Tiroler Talgemeinde), ein Kartenklick, Schalter aus/an, Fehlerfall außerhalb
  Österreichs. Konsole und Netzwerk ohne Fehler. Screenshot als Nachweis.
- CI-Hinweis: `ruff check` mit Pyflakes-Regeln läuft in CI, ist aber nicht in `.venv`; neue Module auf unbenutzte
  Importe prüfen.

## 9. Dokumentation und Abschluss

- `PROJECT_STATE.md`: kurzer Abschnitt `hangcheck_v01` (was, Modell, Grenzen, Tests).
- `PROJEKTUEBERBLICK.md`: eine Zeile unter „Webdemonstration“ und bei „Weitere Untersuchungslinien“: Anwendung,
  keine neue Studie.
- `DATA_SOURCES.md`: GISCO LAU 2021 (falls nicht schon eingetragen).
- Commit pro Meilenstein (Kernseite, dann Fließwege) mit klarer Nachricht, auf `claude/hangcheck-v01` pushen.
  In `main` oder den Integrationsstand erst nach Rücksprache mit dem Nutzer übernehmen.

## 10. Nicht tun

- Kein Training, keine neue Auswertung, keine Kennzahl zur Güte des Hang-Checks erfinden oder neu berechnen.
- Keine Wetterdaten, keine Regenmengen-Eingabe, keine Eintrittswahrscheinlichkeit, kein Ampel-„Grün = sicher“.
- Den Schalter nicht so darstellen, als würde er etwas berechnen.
- Keine eingefrorenen Artefakte (AGENTS.md §45) und keine bestehende Seite inhaltlich umbauen; Hangkarte und
  Wirkungskette bleiben, wie sie sind.
- Nichts öffentlich bereitstellen; keine Anfragen an Behörden oder Datenhalter.
- Rückfragen nur bei echten Blockern (fehlende Daten, Modell-Hash stimmt nicht, Spalten passen nicht).
