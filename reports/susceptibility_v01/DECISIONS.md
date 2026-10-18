# susceptibility_v01 – Phase 0: Vorregistrierung und Entscheidungen

**Stand: 17.10.2026, vor jedem Download eines Inventars, vor jedem Geländemerkmal und vor jedem Modell.** Gilt für den Plan `reports/weiterentwicklung_2026-10-17/ANFAELLIGKEITSSYSTEM_PLAN.md`. Maschinenlesbar: `config/susceptibility_v01.json` (nach der Registrierung schreibgeschützt), Prüfsumme in `PREREGISTRATION.json`. Belege der Quellenabfragen: `phase0_evidence.json` (nur Metadaten). Herkunftsmarken wie in der Datenrecherche: **[A]** am Original abgerufen, **[G]** aus dem Gedächtnis, nicht belegt.

## Namensraum

`config/susceptibility_v01.json`, `preslide/susceptibility/`, `data/susceptibility_v01/`, `models/susceptibility_v01/`, `reports/susceptibility_v01/`. Der Schreibschutz (`paths.guard`) verweigert jeden Pfad außerhalb dieser Wurzeln und jeden eingefrorenen Baseline-Pfad. V0.3 bis V0.5 werden weder gelesen noch geschrieben.

## Was bei der Registrierung bekannt war

- Inhalte der Datenrecherche und des Plans.
- Zenodo-Metadaten von Far-Western Nepal und RER2023 (Lizenz, Dateigröße, md5).
- Südtirol: Feldliste, Gesamtzahlen je WFS-Layer und die Häufigkeit je Bewegungsart (`MOVEMENT_CODE`), abgefragt **ohne Geometrie**. Keine Lage, keine Fläche, kein Gelände.
- Keine Geometrie, kein Geländewert und kein Modellergebnis aus irgendeinem der Inventare.

## Entscheidungen aus Plan-Abschnitt 18

| Punkt | Entscheidung | Begründung und Beleg |
|---|---|---|
| Taiwan | gestrichen | Kein offener Download belegt (Auftrag). |
| DEM | **NASADEM HGT v001** (aus SRTM, 1″ ≈ 30 m), über Planetary Computer (anonymes Token) | SRTM wurde vom 11. bis 22.02.2000 aufgenommen [A, USGS EROS „SRTM 1 Arc-Second Global“]. NASADEM-Sammlung: Zeitstempel 2000-02-20, Lizenzlink „Public Domain“, anonymes Token funktioniert [A, STAC-Abfrage]. Damit liegt das DEM vor allen Ereignissen der Entwicklungsinventare (Gorkha 2015, Far-Western Nepal ab 2002, RER2023). Die Registry prüft das maschinell (`DEM acquired after`-Regel, mit Fehlerinjektion getestet). |
| DEM abgelehnt | Copernicus GLO-30 nur als gekennzeichnete Sensitivität für RER2023 | „Data were acquired by the TanDEM-X mission between 2011 and 2015“ [A, Copernicus Data Space, Kollektionsbeschreibung COP-DEM]. Liegt nach vielen Far-Western-Nepal-Ereignissen; für Gorkha (25.04.2015) je Kachel nicht als vorher belegbar. |
| SRTMGL1 direkt | nicht verwendet | Download nur über EarthExplorer/Earthdata mit Konto; Anmeldedaten gibt der Agent nicht ein. Die Mapzen-„Skadi“-Kacheln (offen auf AWS) sind laut Doku „essentially SRTMGL1 format … with global coverage“, ihre Quellmischung ist nicht belegt [A, tilezen/joerd formats.md]. |
| PGA für Erdbebeninventare | **USGS ShakeMap**, Ereignis `us20002926` (Gorkha), `grid.xml` 14,9 MB [A, USGS-Ereignis-API] | Öffentlich, ohne Konto. Nur in einer explorativen Merkmalsvariante „Gelände + PGA“ für Erdbebeninventare; Hauptmodelle nutzen nur Gelände. ShakeMap ist eine Modellschätzung (~1 km), keine Messung. |
| Niederschlag Modell B | **CHIRPS v2.0**, täglich, 0,05° (HTTPS ohne Konto, Abfrage 200) [A] | Global, lange Reihe. Lizenzwortlaut vor Gate 7 am Original prüfen [G: gemeinfrei]. |
| Bodenfeuchte Modell B | **ERA5-Land über die Open-Meteo-Archiv-API** (Abfrage liefert `soil_moisture_0_to_7cm`) [A] | Kein Konto; Nutzung nicht kommerziell frei [G], Bedingungen vor Gate 7 am Original prüfen. Native Zellgröße ~9 km [G]. |
| Modell B allgemein | vor Gate 7 werden keine Wetter- oder Bodenfeuchtedaten geladen | Mindestens 15 unabhängige, tagesgenau datierte Ereignisse (≥ 7 Tage oder ≥ 100 km auseinander, je ≥ 30 Rutschungen) sind vorab festgelegt. Gorkha und RER2023 sind je ein Ereignis, Far-Western Nepal nur Jahresdatum: **Das Gate wird mit den Pilotdaten voraussichtlich nicht bestanden.** Diese Erwartung steht hier vor jeder Auswertung. |
| Lizenz IFFI Südtirol | **CC BY-SA 3.0 (strengere Lesart)** | Der Datensatz „Eventi di frana“ im Open-Data-Portal der Provinz trägt `license_id: cc-zero`, die eingebetteten Metadaten nennen als Zugangsbedingung CC BY-SA 3.0 [A, CKAN data.civis.bz.it, Stand der Metadaten 23.04.2025]. Bei Widerspruch gilt die strengere Bedingung: Namensnennung und Weitergabe abgeleiteter Daten unter gleicher Lizenz. Rohdaten bleiben lokal. |
| Lizenz Far-Western Nepal, RER2023 | CC BY 4.0 | Zenodo-Datensatz selbst [A]. Far-Western Nepal: Konzept-DOI 4290099 leitet auf Version 4290100 um, Datei `LandslideInventory_FarWesternNepal.zip`, 24.112.492 B, md5 `faf80509…`. RER2023: `RER2023_V1.rar`, 43.630.642 B, md5 `3f17160d…`. |
| Lizenz Gorkha | CC0 laut Recherche [A, USGS-Datenseite], am Original in Phase 1 zu bestätigen | ScienceBase sperrt Skripte (Cloudflare); Abruf nur über den Browser, nichts wird umgangen. |
| SLIDO, Kaikōura V3, Zixing | nicht registriert | Nicht im Pilot; ohne Lizenzklärung nicht verwendbar. |
| Iburi | nicht registriert | Optional; vor Aufnahme eigene Ergänzung der Registry vor jedem Modell. |

## Stichprobe

- **Arbeitsraster** 30 m in der lokalen UTM-Zone, bilinear aus NASADEM.
- **Positiv:** genau eine Zelle je gültigem Rutschungspolygon, gleichverteilt (Seed) aus den Zellen der Anrissfläche, sonst aus dem obersten Höhendrittel des Polygons. Mindestfläche 900 m² (eine Zelle). Ausschlüsse werden nach Grund gezählt. Die Ersatzregel gilt für alle Datensätze gleich und wird nicht nach Ergebnis gewechselt.
- **Hintergrund:** flächengleichmäßig, nicht gematcht, nur im Kartierumriss und außerhalb verdeckter Flächen, Mindestabstand 90 m.
- **Klassenverhältnis 1 : 1** für Training, Validierung und Südtirol. Das ist ein Stichprobenparameter, keine Häufigkeit. PR-AUC wird nur mit diesem Verhältnis berichtet.
- **Puffer um bekannte Rutschungen:** Regel jetzt eingefroren, Zahl folgt aus den Daten. Je Entwicklungsinventar das 90. Perzentil des Äquivalenzradius √(Fläche/π); globaler Wert = Maximum über die Inventare, auf 10 m aufgerundet, mindestens 60 m, höchstens 300 m. Eingabe ist nur die Inventargeometrie (keine Geländewerte, kein Modell, kein Südtirol). Der Wert wird nach dem Download in **Amendment 1** festgeschrieben, vor jedem Geländemerkmal. Überschreitet er 300 m, ist das ein Gate-Befund und kein stilles Kappen.

**Warum nicht schon jetzt eine Zahl:** Der Auftrag verlangt eine aus den Daten abgeleitete Puffergröße. Die Daten liegen erst nach Phase 1 vor. Deshalb wird die Regel vorab registriert und der Wert vor jeder Modellierung per Amendment eingetragen. Ein Amendment darf nur Platzhalter füllen, die hier `null` sind; registrierte Werte kann es nicht überschreiben (Test mit Fehlerinjektion).

## Aufteilung und Metriken

- **Primär:** Leave-one-inventory-out über Gorkha, Far-Western Nepal und RER2023. **Sekundär:** räumliche Block-CV innerhalb jedes Inventars, 5-km-Blöcke, 1 km Lücke. Zufällige Pixel- oder Polygon-Splits sind verboten.
- **Hauptmetrik ROC-AUC.** Dazu Average Precision bei 1 : 1, kontinuierlicher Boyce-Index, Anteil der Positiven in den 20 % höchstbewerteten Flächen, ausgewogene Genauigkeit an der 80. Perzentile des Hintergrunds, Konfusionsmatrix. Kein Accuracy-Headline, kein Brier Score vor gezeigter Kalibrierung, keine Wahrscheinlichkeitssprache.
- **Unsicherheit:** Block-Bootstrap über 5-km-Blöcke (2.000 Wiederholungen, 95 %), Nullreferenz durch Permutation der Labels innerhalb der Blöcke (500). Zu jeder Zahl: unabhängige Einheiten, Verhältnis, Intervall, Baselines. Unterschiede sind gepaart; „besser“ nur, wenn das Intervall die Null ausschließt.
- **Dominanzprüfung:** Hält ein Block oder Cluster mehr als 20 % der Positiven, wird zusätzlich ohne ihn berichtet.

## Baselines

Zufall (0,5 und Permutationsnull), Neigung allein, Höhe allein, logistisches Modell aus Neigung, Höhe, Profil- und Plankrümmung. Für den Nachbarschaftstest (Phase 12) zusätzlich die **negative Entfernung zur nächsten anderen bekannten Rutschung**. ELSUS v2 bleibt optional, weil der Zugang nicht geprüft ist.

## Südtirol-Blindtest (versiegelt)

- Layer `p_bz-Geology:IdroGEO-Landslides-Events-Areas` (EPSG:25832), **nur Polygone**. Punkte, Linien, DGPV und Geomorphologie-Elemente zählen nicht.
- **Eingeschlossen** `MOVEMENT_CODE` 2 (Gleitung), 5 (schnelles Fließen/Mure), 7 (komplexe Rutschung): 3.523 von 10.463 Polygonen (Zählung ohne Geometrie). **Ausgeschlossen** Fallen/Kippen (1, 9), Einsturz (6, 10), laterale Zergleitung (3), langsames Fließen (4), diffuse Oberflächenrutschungsgebiete (11): Prozesse, die mit den Trainingsinventaren nicht vergleichbar sind. Mindestfläche 900 m².
- Kein Datumsfeld vorhanden, daher **keine zeitliche Auswertung**.
- Hintergrund flächengleichmäßig über die Landesfläche, ohne Neigungs- oder Landbedeckungsmaske, mit demselben globalen Puffer aus Amendment 1 (nie aus Südtirol abgeleitet), Mindestabstand 90 m, Verhältnis 1 : 1. Fünf weitere Hintergrundziehungen nur als Streuung; die erste Ziehung ist das Ergebnis.
- Eine vorab registrierte Zweitvariante „nur Hänge ≥ 10°“, gezählt als zweiter Vergleich, nicht als Headline.
- IFFI ist nicht vollständig: Der Test misst die Trennung **dokumentierter** Rutschungen vom Hintergrund, nicht die Vollständigkeit. Eine Region, räumlich korrelierte Blöcke.
- Ausführung **genau einmal**, nur nach ausdrücklicher Freigabe durch den Nutzer und mit eingefrorenem Modellmanifest. Danach gelten die Daten als gesehen.
- Bis dahin werden IFFI-Rohdaten nur unter `data/susceptibility_v01/sealed/` abgelegt und von keinem Trainings-, Auswahl- oder Schwellenschritt gelesen.

## Gates (vorab quantifiziert)

| Phase | Gate |
|---|---|
| 1 | Lizenz am Originaldatensatz festgehalten, Kartierumriss für jedes Entwicklungsinventar vorhanden |
| 2 | CRS-, Zirkular- und Leckage-Tests bestehen und schlagen nachweislich bei eingebautem Fehler an |
| 3 | Puffer- und Mindestabstandstests bestehen; jede Ziehung ist aus dem Seed reproduzierbar |
| 4 | Modell schlägt „Neigung allein“ im primären Design: Untergrenze des gepaarten 95-%-Intervalls der AUC-Differenz > 0, sonst Ursachenanalyse |
| 5 | Unabhängige Einheiten und Intervalle zu jeder Hauptzahl |
| 7 | ≥ 15 unabhängige tagesgenaue Ereignisse, sonst Modell B gestrichen |

Die Mindestzahlen sind Designentscheidungen, nicht aus Daten abgeleitet.

## Offen, per Amendment vor der jeweiligen Phase

Pufferwert (Amendment 1, nach Phase 1), Gorkha-Download (Browser), Hold-out-Ziele und Heruntersampeln der Arme (vor Phase 6), Verfahren des Nachbarschaftstests (vor Phase 12), Quelle der Landesgrenze Südtirol (vor Phase 15).

## Nachweis der Schutztests

`tests/test_susceptibility_v01.py` (25 Tests). `scripts/mutation_check_susceptibility.py` schaltet neun Schutzregeln einzeln ab (Versiegelung, Arme, DEM-Datum inkl. Tagesgrenze, Amendment-Überschreiben, Trainingsliste, Konfigurationshash, Amendment-Sidecar, Schreibschutz). Jeder Mutant lässt mindestens einen Test scheitern: `mutation_check.json`, Status PASS.
