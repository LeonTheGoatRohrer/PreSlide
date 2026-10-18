# Wirkungskette v01 – Audit vor dem Bau (Schritt 0)

Stand 18.10.2026. Zahlen aus `python -m preslide.wirkungskette audit` → `audit.json` (nur lesend auf allen Eingängen).

## Ergebnis in einem Satz

Prüfpunkte und Infrastrukturverschneidung sind als **technische Demonstration** umsetzbar. Den Auslauf kann dieses Inventar **nicht validieren**: Für das Demogebiet fehlen Auslauf- und Schadensangaben, deshalb wird er als **unvalidierte Illustration** gezeigt.

## Machbarkeit je Komponente

| Komponente | Befund | Entscheidung |
|---|---|---|
| Prozess | Stanz 25.07.2016 (V0.4): 241 Ereignisse, davon 160 Lockergesteinsrutschungen, 55 Hangmuren und 26 „Hangmure bis Lockergesteinsrutschung“ | Prozess eindeutig je Punkt |
| Ereignisort | Der Punkt hat kein Feld, das sagt, ob er Anriss, Transport, Ablagerung oder Schadensort markiert | Ortsbezug unbekannt, so gekennzeichnet |
| Geometrie | Nur Punkte. Kein Anrisspolygon, keine Transportspur, keine Ablagerungsfläche. Lage: 234 Punkte mit 0–5 m, 7 mit 20–100 m | keine Anriss- oder Auslaufreferenz |
| Zeit | Alle 241 Ereignisse mit „25.07.2016, früher Nachmittag“ (Tier A) | belastbar |
| Gelände | Skadi 1″, Kachel N47E015, Objektstand 26.04.2016 (vor dem Ereignis), EGM96, 30 m in EPSG:31287. Rechenfenster Radius 15,31 km (1021 × 1021 Zellen), 0 Nodata-Zellen, Senkenfüllung nach 872 Iterationen konvergiert | umsetzbar |
| Unabhängigkeit | Eine zeitliche Episode (TE001), ein Sturm. Gehört zum versiegelten V0.4-Test, der bereits einmal ausgewertet wurde | nur Demonstration, keine neue Bestätigung |
| Auslaufprüfung | Stanz: 0 von 241 Ereignissen mit einem Schadensfeld. Inventar im 10-km-Umkreis: 633 Ereignisse, 97 mit Schadensfeld (51 Verkehrsanlagen, 20 Bauwerke, 1 Versorgung), vor allem Gasen 2005/2017/2018. WLV: 112 Ereignisse mit qualitativer Intensität, ohne Geometrie | **Illustration**. Eine qualitative Gegenprobe wäre nur an den Schadensmeldungen anderer Kampagnen möglich, deren Punktbezug ebenfalls unbekannt ist. Hier zurückgestellt |

Über alle 423 V0.4-Positiven: 107 Ereignisse mit Schadensfeld (67 Verkehrsanlagen, 16 Bauwerke, 4 Versorgung). Bei den 153 Hangmuren-Typen sind es 35 (21 Verkehrsanlagen, 5 Bauwerke).

## Gelände und Rechengebiet

- Anzeige bis 10 km. Gerechnet wird mit 10 km + 300 m + 5010 m Rand, damit oberhalb liegende Einzugsgebiete enthalten sind. Von 38 797 Rasterzellen (90 m) haben nur 6 ein am Fensterrand abgeschnittenes Einzugsgebiet; sie gelten als nicht bewertbar.
- 2 222 Zellen liegen unter 5° Neigung und damit außerhalb des Modellbereichs. Sie werden als „nicht bewertet“ gezeigt, nicht als niedrige Stufe.
- Die Abwärtsroute läuft auf der gefüllten Oberfläche. Durchquerte, rechnerisch gefüllte Senken (Tiefe > 0,5 m) werden je Route gezählt. Rand, Nodata, Senke und Höchstlänge sind getrennte Endgründe.

## Infrastruktur

| Quelle | Inhalt | Lizenz | Entscheidung |
|---|---|---|---|
| OpenStreetMap über Overpass API | Gebäude, Straßen, Wege, Bahn; heutiger Stand (OSM-Basis 18.10.2026 09:50 UTC) | ODbL, Namensnennung „© OpenStreetMap-Mitwirkende“ | **verwendet**, einmal abgerufen und gecacht |
| GIP (Graphenintegrations-Plattform, data.gv.at) | amtliches Verkehrsnetz | CC BY 4.0 | Alternative für Straßen; nicht verwendet, weil Gebäude und Bahn ohnehin aus OSM kommen |
| BEV (Adressen/Gebäude) | amtliche Gebäudeadressen | je nach Produkt | nicht verwendet, weil keine Gebäudeumrisse für diese Demonstration nötig waren |

Abruf im Rechenfenster: 39 041 Gebäude, 11 286 Straßenabschnitte, 9 886 Forst- und Feldwege, 810 Bahnabschnitte. Kritische Infrastruktur wurde nicht abgerufen. Der OSM-Stand ist **heute**, nicht 2016: Gebäude können nach dem Ereignis entstanden sein.

## Hangkarte (Branch claude/clever-satoshi-e4ace7, dd3b69f)

- Inhalt: relative Anteile aus dem eingefrorenen **V0.5**-Statikmodell. Radius 0,5–3 km, 90-m-Zellen, CLC2018, Stichtag 17.10.2026.
- Das V0.5-Modell wurde auf allen 418 Gruppen trainiert, einschließlich des Stanz-Sturms. Im Demogebiet wäre es also in-sample angewendet.
- **Entscheidung:** Das Hangkarten-Modell wird nicht übernommen. Gezielt portiert wurden Rasterlogik (`grid_cells`, `dem_cell_xy`), Zulässigkeitsregeln, CORINE- und Geologie-Abfragen (jetzt mit Kachelung und Deduplizierung) sowie das Cache-Muster. Die Prüfpunkte nutzen das **V0.4-Statikmodell** (`models/v04/final_c6d67a854ba7/conditional_logit_static.joblib`, SHA-256 identisch mit `reports/v04/FREEZE.json`). Es wurde nur auf den 123 Entwicklungsereignissen trainiert, kein Stanz-Ereignis war darin. Landbedeckung CLC2012 nach der V0.4-Datumsregel (Stichtag vor 2019).
- Bekannte Grenze: Das V0.4-Modell lernte Kontraste gegen **gematchte** Kontrollen (Neigung ±5°, Höhe ±150 m, Exposition ±45°). Auf alle Hangzellen eines Fensters angewandt ist das eine Extrapolation über den Neigungsbereich hinaus.

## Literatur für das Auslaufszenario (geprüft, nicht an Ereignissen angepasst)

- Hürlimann, McArdell & Rickli (2015), Geomorphology 232: 178 Hangmuren auf offenem Hang in der Schweiz, horizontale Reichweite 7–467 m, Median 45 m. Median der Anrissbreite 12,5 m, betroffene Fläche 87–9460 m².
- Horton et al. (2013), Flow-R, NHESS 13:869–885: minimaler Fahrböschungswinkel etwa 11° für grob- bis mittelkörnige und etwa 7° für feinkörnige Muren (Zimmermann et al. 1997); Geschwindigkeitsgrenze 15 m/s.
- Die Winkel sind **Minima für (gerinnegebundene) Muren** und damit die obere Reichweite für Hangmuren. Hürlimann et al. schlossen 68 Ereignisse aus, weil sie in ein Gerinne flossen und dadurch deutlich weiter liefen.

## Abweichung vom Masterprompt

`GEFAEHRDUNGSANALYSE_MASTERPROMPT.md` stellt die Infrastrukturverschneidung bis nach einer fachlichen Prüfung zurück (Abschnitt 12). Dieser Auftrag verlangt sie ausdrücklich. Sie wird deshalb nur als räumliche Überlagerung mit einem unvalidierten Szenario gezeigt („liegt im Auslaufszenario“), ohne Schadens- oder Wahrscheinlichkeitsaussage.
