# susceptibility_v01 – Phase 1: Gate nicht erfüllt

**Stand: 17.10.2026.** Kein Geländemerkmal, kein Modell. Grundlage: `phase1_audit_far_western_nepal.json`, `phase1_audit_rer2023.json` (aggregiert, ohne Einzelsätze), `DATA_SOURCES.md` (Abschnitt susceptibility_v01).

**Gate laut Registrierung:** Lizenz am Originaldatensatz festgehalten **und** Kartierumriss für jedes Entwicklungsinventar vorhanden.

| Inventar | Lizenz am Original | Kartierumriss | Gate |
|---|---|---|---|
| Far-Western Nepal | CC BY 4.0 (Zenodo) | ja: AOI, 1 Polygon, 6.409 km²; eine Selbstüberschneidung, mit `make_valid` repariert (Flächenänderung < 1 m²) | erfüllt |
| RER2023 | CC BY 4.0 (Zenodo) | **nein**: Archiv enthält nur `RER2023_V1.shp`; der Artikel nennt „über 6.000 km²“ und eine Aufteilung nach Gemeindegrenzen, aber keine Grenzdatei | **nicht erfüllt** |
| Gorkha 2015 | CC0 1.0 (USGS-Datenseite) | laut Datenseite vorhanden („extent of geographic areas in which mapping was completed“, „obscured areas“), aber nicht bezogen | **nicht erfüllt**: ScienceBase zeigt eine Cloudflare-Menschprüfung; sie wurde nicht umgangen |

Deshalb wurde **Amendment 1 (Pufferwert) nicht geschrieben**: Die registrierte Regel verlangt das Maximum über alle Entwicklungsinventare, und Gorkha fehlt. Vorläufige, nicht eingefrorene Werte des 90. Perzentils des Äquivalenzradius: Far-Western Nepal 63,1 m, RER2023 26,1 m.

## Weitere Befunde (vor jeder Modellierung)

1. **Far-Western Nepal widerspricht der registrierten DEM-Regel.** Registriert war `earliest_event_date 2002-01-01` (aus „Bilder 2002–2018“). Die datierte Punktschicht reicht jedoch bis 1992: 2.436 von 8.778 datierten Rutschungen liegen vor 2000, 408 im Jahr 2000 (relativ zur Aufnahme im Februar unklar), 5.934 danach. 17.572 Polygone haben kein Datum. Für diese Rutschungen kann das SRTM/NASADEM-Gelände die Narbe bereits enthalten. Der registrierte Wert ist falsch und wird nicht still geändert.
2. **Kleine Polygone.** RER2023: Median 479 m², 57.609 von 80.997 Polygonen liegen unter einer 30-m-Zelle (900 m²) und fallen nach der registrierten Regel heraus (verbleiben 23.388). Far-Western Nepal: 5.617 von 26.350 unter 900 m². Das 30-m-DEM ist für RER2023 grob.
3. **Prozessmischung RER2023.** `ClassNew` enthält Schuttströme (DF1 6.040, DF2 6.095) und Erdströme (EF 4.435) neben Gleitungen. Die Registrierung filtert RER2023 bisher nicht nach Typ; vor Phase 3 festzulegen.
4. **Zählabweichung Far-Western Nepal:** Punktschicht 25.679 Objekte, Datensatzbeschreibung 25.639. 2 leere und 1 ungültiges Polygon (gezählt).
5. **Zeichenkodierung Südtirol:** Einige WFS-Bezeichnungen enthalten bereits beim Anbieter Ersatzzeichen (`Oberfl�chen`); die Codes sind eindeutig, daher ohne Folgen.

## Entscheidungen, die vor Phase 2 nötig sind

| Nr. | Frage | Optionen | Empfehlung |
|---|---|---|---|
| A | Gorkha beziehen | Nutzer bestätigt die Cloudflare-Prüfung im Browserfenster selbst; danach werden Dateinamen und Größen genannt und nur die Shapefiles geladen | A |
| B | RER2023 ohne Kartierumriss | (1) Umriss bei Autoren oder Region Emilia-Romagna anfragen; (2) Umriss aus den im Artikel genannten Gemeinden mit amtlichen Grenzen bilden, falls die Gemeindeliste veröffentlicht ist; (3) RER2023 aus der Entwicklung nehmen. **Kein** Umriss aus der Hülle der Rutschungspolygone: Er läge per Konstruktion dort, wo Rutschungen sind. | (1), ersatzweise (2) |
| C | Far-Western Nepal und DEM-Datum | (1) Positive nur aus Rutschungen mit Jahr ≥ 2001; alle übrigen Polygone nur als Ausschlussfläche für den Hintergrund; (2) Far-Western Nepal herausnehmen; (3) als Einschränkung hinnehmen (verletzt die registrierte Regel) | (1), als Amendment vor jedem Geländemerkmal |
| D | Südtirol-Schnappschuss | Geometrie jetzt einmal in den versiegelten Ordner laden und per Prüfsumme einfrieren (der Anbieter aktualisiert „bei Bedarf“), ohne sie zu öffnen; oder erst in Phase 15 abrufen | jetzt einfrieren, nur nach Freigabe |

B und C ändern das registrierte Design und werden als Amendment mit Begründung festgehalten, bevor irgendein Modell oder Geländewert die Daten sieht. Der Amendment-Mechanismus erlaubt bisher nur das Füllen von Platzhaltern; eine Korrektur registrierter Werte bräuchte eine ausdrückliche, getestete Erweiterung (alter Wert, neuer Wert, Grund).
