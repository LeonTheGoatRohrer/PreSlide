# Hangkarte (hangmap_v01) – Stand 17.10.2026

**Was es ist:** Anwendung des eingefrorenen V0.5-Modells (bedingte logistische Regression, nur statische Merkmale: Gelände, Landbedeckung, Geologie; SHA-256 des Modells in `config/hangmap_v01.json` geprüft). Keine neue Auswertung, kein neues Training, keine Berührung eingefrorener Artefakte (schreibt nur nach `data/hangmap_v01/`).

**Was es nicht ist:** keine Eintrittswahrscheinlichkeit, keine Warnung, keine validierte Gefahrenkarte, keine Kausalität. Die Anteile gelten nur innerhalb der gezeigten Vergleichsgruppe (Summe 100 %). Das V0.5-Modell wurde auf bereits gesehenen Ereignissen angepasst; die hohe Trennung (lokale AUC 0,85) ist teils Meldebias, mit gematchten Kontrollen nur 0,70. Die farbliche Hervorhebung von Siedlungs-/Grünlandhängen spiegelt genau diese Struktur wider.

## Methode
- Gebiet: Mittelpunkt + Radius (500–3000 m), Zellen im 90-m-Raster auf dem 30-m-DEM (EPSG:31287, Distanzen in Metern).
- Merkmale: unveränderter V0.5-Code (`preslide.v05.terrain.static_features`) für Krümmungen, TRI, TPI, Hangposition, Einzugsgebiet/TWI; Landbedeckung CORINE CLC2018, Geologie 1:500 000.
- Bewertbar: Neigung ≥ 5°, Höhe 0–4500 m, innerhalb Österreichs, Einzugsgebiet nicht am Fensterrand abgeschnitten, Landbedeckung und Geologie eindeutig. Nicht bewertete Zellen werden je Grund gezählt und gemeldet, nie aufgefüllt.
- Vergleichsgruppe: (a) 10 Zellen, Mindestabstand 400 m, Ziehung mit festem Seed aus Koordinaten+Radius (kein Auswählen nach Ergebnis); (b) 2–12 vom Nutzer gewählte Punkte. Anteil = Softmax des linearen Modellwerts in der Gruppe.
- Farbebene: Softmax über alle bewertbaren Zellen des Gebiets, gefärbt nach Rang-Perzentil (Anteile einzelner Zellen sind sehr spitz verteilt).
- Zusatzebene Niederschlag (INCA, 7 Tage): getrennt, nicht Teil der Anteile; keine Bodenfeuchte. Sentinel-1-Bodenfeuchte nicht umgesetzt.
- Nur Vor-Ereignis-Information: Es gibt keinen Ereignistag; das Modell verwendet ausschließlich statische Merkmale (Test erzwingt Allowlist ohne Wetter/Zeit). DEM-Kacheln müssen vor dem Referenzdatum 2026-10-17 geändert worden sein.

## Prüfungen (Details siehe `tests/test_hangmap.py`)
- Anteile summieren sich je Gruppe zu 1 (auch Gruppengröße 1, extreme Scores); Reihenfolge folgt dem Score.
- Aspekt zirkulär (359° ↔ 1° = 2°); Distanz/Raster in Projektion gegen Geodäsie (3 Längenlagen, Lat/Lon-Vertauschung wird erkannt).
- Gruppenauswahl: Mindestabstand, Determinismus, unabhängig von der Eingabereihenfolge.
- Modell-Hash, Cache-Prüfsumme, Radius-/Punkt-Validierung, nicht bewertbarer Punkt wird abgelehnt statt bewertet.
- Fehlerinjektion: Gruppenbildung ignoriert, Aspekt ohne Bogenmaß, Abstandsregel entfernt → jeweils der zuständige Test scheitert.

## Konsistenz mit V0.5-Trainingsmerkmalen (Stichprobe, 1 Ereignis + 8 Positive)
- Gleiche Positionen, anderes DEM-Fenster: Merkmalsabweichungen durch Raster-Ursprung/Bilinear-Resampling klein (Höhe ≤ 1,5 m, Neigung ≤ 0,13°, TPI500 ≤ 1,5 m, log10-Einzugsgebiet ≤ 0,12).
- Landbedeckungsklasse stimmt, außer (a) Ereignisse vor 2019 (dort CLC2012 im Training, hier immer CLC2018) und (b) Zellmitte statt exakter Position (bis ca. 21 m) an Polygonrändern. Das verändert den Modellwert teils deutlich (Landbedeckung hat große Koeffizienten) – ein Hinweis, wie stark das Modell an der Landbedeckung hängt.

## Bekannte Grenzen
- Anteile sind stark gespreizt (z. B. 74 % / 20 % / 6 % / < 1 % …) – das spiegelt die Modellsteilheit auf Landbedeckung/Höhe/Hangposition, nicht Gewissheit.
- Gebietsradius ≤ 3 km; ein Radius-Fenster hat 5,3 km Rand für Einzugsgebiete (wenige Randzellen werden ausgeschlossen).
- Orthofoto-/Terrarium-Kacheln stammen von Drittservern und werden vom Browser geladen (nur Darstellung).
