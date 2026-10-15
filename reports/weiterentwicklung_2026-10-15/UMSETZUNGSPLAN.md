# Umsetzungsplan: Professionalisierung und Merkmalsoptimierung (Stand 15.10.2026)

Dieser Plan setzt auf dem Stand nach PR #1 auf (Pipeline A: V0.4 abgeschlossen, Baseline V0.3 eingefroren; Pipeline B: satellite-0.2 abgeschlossen, satellite-0.3 „whole-patch cloud screening“ in Arbeit). Er ist in vier Arbeitspakete gegliedert, die in der angegebenen Reihenfolge abgearbeitet werden sollen. Jedes Paket hat ein klares „Fertig“-Kriterium. Regeln aus `AGENTS.md` gelten unverändert: nur reale Daten, keine Zukunftsinformation in Pipeline A, keine Auswahl nach Testergebnissen, jede Erweiterung als neue, vorab registrierte Version.

Aufwandsschätzung: Arbeitstage eines Agenten/Entwicklers inklusive Rechenzeit auf dem Laptop; Netzlaufzeiten (Satellitenpatches) laufen im Hintergrund.

| Paket | Inhalt | Aufwand | Abhängigkeit |
|---|---|---:|---|
| P1 | Infrastruktur: CI, Verifikation, Registrierung, Kleinigkeiten | 1–2 Tage | keine |
| P2 | Pipeline B satellite-0.3/0.4: normierte Veränderung, Persistenz, Geländefilter, Positionsschärfung | 2–3 Tage | satellite-0.3 (läuft) |
| P3 | Pipeline A V0.5: hydrologische Regenmerkmale, Meldebias-Kontrolle | 2–3 Tage | P1 (Registrierung) |
| P4 | Pipeline A V0.6: Case-Crossover-Design für den Ereignistag | 3–4 Tage | P3 |

---

## P1 — Infrastruktur und Professionalisierung

### P1.1 Continuous Integration (GitHub Actions)

- Datei `.github/workflows/ci.yml`, ausgelöst bei Push und Pull Request.
- Jobs:
  1. **Python**: Python 3.11, `pip install -r requirements-lock.txt`, `pytest -q -m "not local_data"`.
     Tests, die lokale Rohdaten oder Caches brauchen (`test_baseline`, `test_stability`, `test_completed_experiment`, Teile von `test_v04_science`, `test_api` mit Demo-Bundle), bekommen den Marker `local_data` (in `tests/conftest.py` registrieren). Die Satelliten-Tests laufen vollständig, da sie synthetische Fixtures verwenden.
  2. **Frontend**: Node 22, `npm ci --ignore-scripts`, `npm test`, `npm run build`.
  3. **Reproduzierbarkeit der Berichte** (leichtgewichtig): `python -c "import json; json.load(open('reports/satellite/baseline_results.json'))"` für alle JSON-Berichte, damit keine ungültige Datei eingecheckt wird.
- Status-Badge in `README.md`.
- Fertig: CI grün auf dem Branch; ein absichtlich fehlerhafter Test wird rot.

### P1.2 Verifikationsskript für Pipeline B

- `scripts/verify_satellite.py` nach dem Muster von `scripts/verify_v04.py`:
  - Manifest `reports/satellite/MANIFEST.json` mit SHA-256 aller Tabellen (`data/satellite/tables/*.parquet`), Modelle, Berichte und Konfiguration; Prüfung Konfigurationshash gegen Registrierung.
  - Nachrechnen der Out-of-fold-Vorhersagen aus `baseline_oof_scores.parquet` mit den gespeicherten Folds (Gruppenisolation je Einheit prüfen).
  - Schreibt `reports/satellite/verification.json` mit `status: PASS|FAIL` und Liste der Abweichungen.
  - Prüft die Isolation: kein Modul unter `preslide/` außer `preslide/satellite/` importiert das Satellitenpaket; `data/v04/.../dataset.parquet` enthält keine Satellitenspalten (bereits Tests, hier zusätzlich als Laufzeitprüfung).
- Fertig: PASS auf dem aktuellen Stand; Aufruf im README dokumentiert.

### P1.3 Vorregistrierung als Regel

- Vorlage `config/REGISTRATION_TEMPLATE.json`: Version, Datum, Frage, primärer Endpunkt, Entscheidungsregel, Daten, was nicht verändert werden darf, Konfigurationshash.
- `scripts/register.py <config> <reports-dir>`: schreibt `PREREGISTRATION.json` mit Hash, verweigert Überschreiben.
- Alle Pipelines lesen die Konfiguration über eine `config()`-Funktion, die bei Hashabweichung nach Registrierung abbricht (V0.4 hat das; Pipeline B zieht nach).
- Fertig: satellite-0.3 und alle folgenden Versionen besitzen eine Registrierungsdatei vor dem ersten Lauf.

### P1.4 Kleinere Punkte

- `RESULTS.md`: Abschnitt Pipeline B (Basislinie, Wiederentdeckung, Kandidatenvalidierung) mit Verweis auf `reports/satellite/`.
- Frontend: Abschnitt „Quellen und Lizenzen“ mit Copernicus-Hinweis, GeoSphere, Mapzen, Earth Search; Fußzeile ergänzen.
- `scripts/run_pipeline_b.ps1`: Standardkette `eligibility → dataset → contact → baseline → discovery → report` mit Neustart aus dem Cache nach GDAL-Absturz (Schleife, wie im Session-Log erprobt).
- Typisierung der neuen Module (`preslide/satellite/*.py`) und `ruff`-Konfiguration in `pyproject.toml`; nur Fehler, keine Stilumbauten.
- `.gitattributes` mit `* text=auto eol=lf`, damit Prüfsummen in Worktrees nicht an CRLF scheitern (bekanntes Problem der Baseline-Tests im Worktree).
- Fertig: Dokumente aktualisiert, Skript läuft durch, `ruff check` ohne Fehler.

---

## P2 — Pipeline B: satellite-0.3 abschließen, dann satellite-0.4

Voraussetzung: satellite-0.3 (Wolkenmaske mit Puffer über den ganzen 2,56-km-Ausschnitt, erneute Wiederentdeckung) ist abgeschlossen und berichtet. Die folgenden Punkte bilden **satellite-0.4** und werden vor dem Lauf registriert (P1.3). Primärer Endpunkt: Zahl der innerhalb 160 m wiedergefundenen zurückgehaltenen Ereignisse unter den ersten drei Kandidaten und Kandidaten je km²; Nebenendpunkt lokale AUC. Keine Auswahl einzelner Merkmale nach dem Ergebnis.

### P2.1 Veränderung relativ zur Vorgeschichte (normierte Differenz)

- Für jede Gruppe liegen `before_reference` und `before_primary` vor. Neu in `features.py`:
  - `ref_delta = before_primary − before_reference` je Index (NDVI, NBR, BSI, NDWI, Helligkeit).
  - Streuung der Vorgeschichte je Fenster: `sigma_pre = std(ref_delta)` im 320-m-Kern und im Ring, mit Untergrenze (z. B. 0,02), damit sehr stabile Flächen nicht explodieren.
  - Normierte Merkmale: `z_small = d_small_contrast / sigma_pre_ring`, `z_core = d_core_mean / sigma_pre_core`, zusätzlich `frac_z_below(−2)` im Kern.
- Fallback: Gruppen ohne brauchbares `before_reference` bekommen die Normierung mit dem Median der Streuung aller Gruppen derselben Jahreszeit; die Fallback-Fälle werden gezählt und gemeldet.
- Implementierung als Karten (Boxfilter), damit die Suche unverändert funktioniert.
- Fertig: Merkmale in `dataset.parquet`, Basislinie mit und ohne Normierung berichtet, Testfall mit synthetischer Ernteveränderung (gleichmäßige Abnahme im Ring → z nahe 0, lokaler Fleck → z deutlich negativ).

### P2.2 Persistenz als Merkmal

- `after_confirm` liegt für die meisten Gruppen vor. Neu: dieselben Veränderungsmerkmale für das Paar `before_primary → after_confirm` sowie das Paar `after_primary → after_confirm`.
- Merkmal `persistence = sign-konsistente Veränderung in beiden Nachher-Bildern` (z. B. min(|d_ndvi_small_contrast(after_primary)|, |d_ndvi_small_contrast(after_confirm)|) mit gleichem Vorzeichen) und `regrowth = d_ndvi(after_primary → after_confirm)` (Ernte wächst nach, Narbe nicht).
- Gruppen ohne `after_confirm` (Wolken) behalten fehlende Werte; HistGradientBoosting verarbeitet sie nativ, die logistische Regression bekommt Trainingsmittel wie in V0.4.
- Fertig: Persistenzmerkmale in Tabelle und Suche; Bericht, wie oft `after_confirm` fehlt.

### P2.3 Geländefilter in der Suche

- Für jeden Suchausschnitt Neigung aus dem 30-m-Skadi-Fenster (vorhandener Code in `preslide/terrain.py`) auf das 10-m-Raster reprojizieren.
- Regeln (registriert, nicht nachjustiert): Maxima nur dort, wo Neigung ≥ 8° und SCL-Wasserklasse im Kern < 10 %; Kandidaten innerhalb 100 m einer Wolken-/Schneemaske (P satellite-0.3) sind ausgeschlossen.
- Zusätzlich Neigung und Exposition als Merkmale im Kandidatenbericht (nicht im Modell, damit die Suche weiter ein Veränderungs- und kein Suszeptibilitätsmodell bleibt).
- Fertig: Kandidaten je km² vor/nach Filter, Trefferquote vor/nach Filter in `heldout_discovery_results.md`.

### P2.4 Positionsschärfung bekannter Ereignisse (einzige erlaubte Rückkopplung nach Pipeline A)

- Für jedes wiedergefundene Ereignis (Treffer innerhalb 160 m, Persistenz bestätigt) den Schwerpunkt des Veränderungsflecks berechnen.
- Tabelle `data/satellite/tables/position_refinement.parquet`: alte Position, neue Position, Abstand, Flächengröße, Konfidenz, Quelle (`satellite_scar_centroid`).
- Pipeline A darf nur die Koordinate übernehmen, nie Merkmale aus dem Nachher-Bild. Die Übernahme erfolgt als eigene Datensatzversion (`V0.5-positions`) mit Herkunftsspalte; die ursprünglichen Positionen bleiben erhalten.
- Vorab festgelegte Prüfung: Verteilung der Verschiebungen gegen die Positionsklassen (≤ 5 m, ≤ 20 m) der Quelle; bei systematischen Verschiebungen > 50 m in der 5-m-Klasse ist die Quelle oder der Schwerpunkt zu hinterfragen, nicht automatisch zu überschreiben.
- Fertig: Tabelle, Bericht `position_refinement.md`, keine Änderung an Pipeline A ohne neue Version.

### P2.5 Stufe 6: Suche in unbekanntem Gebiet

- Erst nach P2.1–P2.3 und nur, wenn die Wiederentdeckung die registrierte Schwelle erreicht (Vorschlag: ≥ 50 % der zurückgehaltenen Ereignisse unter den ersten drei bei ≤ 2 Kandidaten je km²).
- Gebiet: ein Sturmfußabdruck in der Steiermark (z. B. 2023-08) ohne die dort bekannten Ereignisse; Kacheln 2,56 km, vorhandene Auswahl- und Patchlogik.
- Ausgabe: Kandidatenpolygone, Rangliste, Kontaktbögen; Status `UNVERIFIED`; Validierung nach P2.2 mit `after_confirm`.

---

## P3 — Pipeline A V0.5: Merkmale und Meldebias

Neue Version, registriert vor dem Lauf (`config/v05.json`, `reports/v05/PREREGISTRATION.json`), getrennte Ausgaben (`data/v05/`, `models/v05/`, `reports/v05/`). Der V0.4-Test ist gesehen und steuert nichts mehr; Entwicklung ausschließlich mit gruppierter Kreuzvalidierung auf den V0.4-Entwicklungseinheiten; der V0.4-Test wird nur einmal am Ende mit dem registrierten Primärmodell bewertet, falls überhaupt (Entscheidung in der Registrierung festhalten).

### P3.1 Hydrologische Regenmerkmale (aus gecachten INCA-Stunden, keine neuen Downloads)

- Antecedent Precipitation Index: `API_t = k · API_{t−1} + RR_t` stündlich mit zwei Abklingkonstanten (Halbwertszeit 3 Tage und 14 Tage), Wert am letzten zulässigen Stundenpunkt vor t0 (Randregel aus V0.4 unverändert).
- Intensität-Dauer: maximale Summe über 3 h, 6 h, 12 h, 24 h, 72 h im 60-Tage-Fenster und deren Zeitpunkt relativ zu t0.
- Nasstage: Zahl der Tage mit ≥ 1 mm und ≥ 10 mm in 14/30/60 Tagen; längste Trockenperiode davor.
- Schnee+Regen: SNOWGRID-Schmelze (vorhanden) plus Regen derselben Tage als Summe „verfügbares Wasser“.
- Alle Merkmale in `preslide/v05/weather.py` mit denselben Randregeln (`T + 1 h < t0`), Tests analog `tests/test_v04_science.py` (kein Stundenwert erreicht t0).
- Fertig: Merkmale im Datensatz, Abdeckung je Merkmal, Vergleich Varianten `V0.4-Merkmale` gegen `V0.4 + hydrologisch` in der Entwicklung.

### P3.2 Meldebias-Kontrolle

- Neue statische Kovariaten: Distanz zum nächsten Gebäude und zur nächsten Straße (OpenStreetMap über Overpass oder BEV-Adressdaten; Quelle, Lizenz und Abrufdatum in `DATA_SOURCES.md`; zeitlicher Stand nach t0 ist hier akzeptabel, weil Gebäude und Straßen im Wesentlichen persistent sind, dies ist zu dokumentieren).
- Zwei registrierte Auswertungen: (a) Kovariate im Modell; (b) Matching mit zusätzlichem Kaliper „Distanz zu Infrastruktur“ (Kontrollen genauso sichtbar wie der Ereignishang). Berichtet wird, wie stark die Landbedeckungs- und Geländeeffekte aus V0.4 unter (b) schrumpfen.
- Fertig: `reports/v05/reporting_bias.md` mit beiden Auswertungen; keine Interpretation als Kausalität.

### P3.3 Mehr unabhängige Episoden (optional in V0.5, sonst V0.6)

- Medienereignisse (Tier 2) als getrennt gekennzeichnete Daten mit eigener Herkunftsspalte; nur in Sensitivitätsanalysen, nie in der Hauptauswertung ohne Registrierung.

---

## P4 — Pipeline A V0.6: Case-Crossover für den Ereignistag

- Design: derselbe Hang zu mehreren Kontrollzeitpunkten (z. B. gleiche Kalenderwoche in anderen Jahren und ±4, ±8 Wochen im selben Jahr), Merkmale identisch wie V0.5, konditionale logistische Regression über den Hang als Stratum (vorhandene Implementierung aus V0.4).
- Damit wird der Regen am Ereignistag bis zum Ereigniszeitpunkt nutzbar, weil Kontrollzeitpunkte keine Zukunft des Ereignisses sind; die Randregel bleibt `T + 1 h < t0`.
- Vorregistrierung: Kontrollzeitpunkte, Ausschluss von Zeitpunkten mit bekannten Ereignissen am selben Hang (Inventarabgleich), Primärendpunkt (lokale AUC über Zeitpunkte), Zufallsreferenz.
- Fertig: `reports/v06/summary.md`, Vergleich Case-Crossover gegen Nachbarhang-Design auf denselben Ereignissen.

---

## Reihenfolge und Meilensteine

1. **Woche 1:** P1.1 CI, P1.2 Verifikation, P1.3 Registrierung, P1.4; parallel satellite-0.3 abschließen.
2. **Woche 2:** P2.1–P2.3 als satellite-0.4 (registriert), Bericht; P2.4 Positionsschärfung als Tabelle.
3. **Woche 3:** P3.1–P3.2 als V0.5 (registriert), Entwicklungsauswertung, Bericht.
4. **Danach:** P2.5 Stufe 6 nur bei erreichter Schwelle; P4 als V0.6.

## Risiken

- **Metrik-Jagd:** Jede Version wird vor dem Lauf registriert; Varianten werden alle berichtet, nicht ausgewählt.
- **Wenige unabhängige Einheiten (15 in Pipeline B, 19 Entwicklung in Pipeline A):** Konfidenzintervalle und Permutationsnull bleiben Pflicht; P3.3/P4 sind der eigentliche Hebel für mehr Episoden.
- **Netz- und GDAL-Stabilität:** Patch-Läufe mit 2 Workern und Cache-Neustart (P1.4-Skript).
- **Lizenz der Infrastrukturdaten (P3.2):** vor dem Download in `DATA_SOURCES.md` klären; nur lokale Forschung.
- **Trennung der Pipelines:** Einzige Rückkopplung ist die Positionskorrektur (P2.4) als neue Datensatzversion mit Herkunft; Tests sichern, dass keine Nachher-Merkmale in Pipeline A gelangen.
