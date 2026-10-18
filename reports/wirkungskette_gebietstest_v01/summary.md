# Gebietstest der Prüfstufen an ungesehenen Hangmuren-Gebieten (wirkungskette_gebietstest_v01)

Stand 18.10.2026 · Branch `claude/wirkungskette-v02-gebietstest` · vorab registriert, einmal ausgewertet, eingefroren.
Registriert als `wirkungskette_v02`; der Name war früher von der Auslauf-Gegenprobe belegt, deshalb in einen eigenen Namensraum umgezogen (Amendment 2, Konfiguration bytegleich).

## Frage

Legen die Prüfstufen der Wirkungskette, also das eingefrorene V0.4-Geländemodell, dokumentierte, genau verortete reine Hangmuren aus Ereignisdokumentationen, die das Modell nie gesehen hat, häufiger in die obersten 5 % bzw. 20 % der bewertbaren Fläche als die Neigung allein und als der Flächenanteil?

## Ablauf und Nachweis

| Schritt | Zeitpunkt (UTC) | Datei / Commit |
|---|---|---|
| Registrierung (Regeln, Kennzahl, Basislinie, Unsicherheit, Datumsregel) | 10:49 | `PREREGISTRATION.json`, Commit d2acef7 |
| Code, Gebietszusammensetzung, technischer Pilot an Klingfurth | 10:59 | f39c9d1 |
| Amendment 1: Skadi ist praktisch SRTMGL1, Skadi-Sensitivität entfällt, Umzug angekündigt | 11:13 | `AMENDMENT_1.json`, 12dfa1d |
| Volllauf, einmal | 12:59 | `test_results.json` |
| Einfrieren und Umzug | danach | `FREEZE.json`, `AMENDMENT_2.json`, d80efc0 |

Auftrag des Nutzers (über die Website-Session): „Den Demo-Test würde ich machen, wie du empfohlen hast. Aber ich würde sagen, zuerst einmal mit Gebiet rechnen.“

## Gebiete (Regel: Kampagnenjahr 2000–2015, mindestens 50 genau verortete reine Hangmuren, Lagefehler höchstens 20 m)

Gebiet = LAU-2021-Gemeinden mit mindestens 5 Zielereignissen der Kampagne. 30-m-SRTM (Aufnahme Februar 2000), 90-m-Zellen, Landbedeckung nach Jahr: CORINE 2000 für 2005, 2006 für 2009, 2012 für 2013/2015.

| Gebiet | Ziele im Gebiet (außerhalb) | Fläche | Gemeinden | bewertbare Zellen | V0.4-Trainingsereignisse im Gebiet |
|---|---:|---:|---:|---:|---:|
| Vorarlberg/Tirol August 2005 | 1 144 (32) | 2 027 km² | 40 | 237 513 | 3 |
| Nordhälfte Österreich Juni 2013 | 84 (21) | 593 km² | 7 | 71 786 | 0 |
| Sellrain Juni 2015 | 86 (6) | 62 km² | 1 | 7 600 | 0 |
| Gasen/Haslau August 2005 | 74 (2) | 124 km² | 2 | 14 515 | 4 |
| Klingfurth Juni 2009 | 73 (0) | 71 km² | 3 | 7 362 | 0 |

Nicht bewertbar waren vor allem Zellen flacher als 5°. Bei den Zielereignissen betraf das nur Klingfurth (9 von 73, als nicht erfasst gezählt).

## Ergebnis

Anteil der Zielereignisse, deren Zelle in den obersten k % der bewertbaren Fläche ihres Gebiets liegt:

| Gebiet | Modell 5 % | Modell 20 % | Neigung 5 % | Neigung 20 % |
|---|---:|---:|---:|---:|
| Vorarlberg/Tirol 2005 | 3,8 % | 28,8 % | 0,5 % | 12,5 % |
| Nordhälfte 2013 | 5,9 % | 35,7 % | 0,0 % | 7,1 % |
| Sellrain 2015 | 24,4 % | 62,8 % | 2,3 % | 31,4 % |
| Gasen/Haslau 2005 | 27,0 % | 75,7 % | 21,6 % | 52,7 % |
| Klingfurth 2009 | 11,0 % | 26,0 % | 1,4 % | 11,0 % |
| **Gebiete gleich gewichtet** | **14,4 %** [5,5; 22,7] | **45,8 %** [27,5; 64,1] | 5,2 % [0,2; 13,8] | 22,9 % [9,3; 40,8] |
| Ereignisse gepoolt | 6,7 % | 33,5 % | 1,7 % | 15,3 % |
| Zufall (Flächenanteil) | 5 % | 20 % | 5 % | 20 % |

Gepaarte Differenz Modell − Neigung (Gebiete gleich gewichtet): **+22,9 Prozentpunkte [+12,7; +30,5]** bei 20 % und +9,3 Pp. [+2,8; +15,8] bei 5 %. Intervalle: zweistufiger Cluster-Bootstrap (Gebiete, dann 2-km-Blöcke), 2 000 Ziehungen, Seed 20261018.

**Nach der registrierten Regel:** Das Modell ist bei 20 % und bei 5 % besser als Zufall und besser als die Neigung allein, denn alle Intervalle schließen den Vergleichswert aus. Die Neigung allein ist nicht nachweislich besser als Zufall. Das Modell liegt in jedem der fünf Gebiete über der Neigung.

## Wie das zu lesen ist

- **Nur 5 unabhängige Einheiten.** Vorarlberg/Tirol und Gasen/Haslau (beide August 2005) können zum selben Unwetter gehören. Ein Perzentil-Bootstrap über 5 Gebiete unterschätzt die Unsicherheit eher.
- **Das Gebiet zählt mehr als einzelne Punkte.** Gepoolt über Ereignisse (dominiert von Vorarlberg mit 1 144 Zielen) ist der Wert bei 20 % mit 33,5 % deutlich niedriger, und bei 5 % ist Vorarlberg kaum über Zufall (3,8 %).
- **Die Neigungs-Basislinie ist schwach.** Die steilsten Zellen sind oft Fels und Wände, auf denen keine Hangmuren entstehen. Der Vorsprung des Modells zeigt vor allem, dass Rauigkeit, Hangposition und Landbedeckung zusammen besser ordnen als die Neigung allein. Ein gelerntes Gelände-Bodenmodell als stärkere Basislinie war nicht registriert.
- **Meldebias bleibt möglich.** Die Gemeinden wurden wegen ihrer Ereignisse gewählt. Nicht kartierte Hänge in diesen Gemeinden zählen als Hintergrund. Das Modell stützt sich auch auf Grünland gegenüber Wald, und Hangmuren auf Grünland sind leichter zu kartieren (Luftbild). Das ist eine Rangfolge, keine Eintritts- oder Schadensaussage.
- **Datierung:** Bei Vorarlberg/Tirol sind 565 Ziele „sicher“ und 563 „vermutlich“ August 2005 datiert, einige nur über Luftbildvergleiche 2000–2006. Die Regel filtert nicht nach Datierungssicherheit. Für ein statisches Modell ist das unkritisch, für eine Ereigniszuordnung nicht.
- **Kontrast zu Stanz:** Im versiegelten V0.4-Test trennte das Gelände im Stanz-Sturm nicht (0,455), und im Stanz-Demofenster bündeln die Stufen die Ereignisse nicht. Die Stufen helfen also nicht überall; Stanz war das Gebiet mit den vielen Lockergesteinsrutschungen.
- **Gelände:** SRTM vom Februar 2000 ist nachweislich älter als alle Kampagnen. Die Skadi-Kacheln des V0.4-Trainings sind über Österreich zu 99,5–99,8 % zellgleich mit SRTMGL1 (Amendment 1). Training und Test nutzen also dieselbe Höhenquelle.
- **Ab jetzt gesehen:** Die fünf Gebiete sind nach diesem Test gesehen. Ein neues Modell mit allen Inventardaten darf seinen Erfolg nicht an diesen Gebieten als „ungesehen“ ausweisen.

## Demogebiet

Nach der registrierten Regel (Gebiet mit den meisten Zielen, darin die Gemeinde mit den meisten) ist das **Mittelberg im Kleinwalsertal** (120 Hangmuren). Die Prüfgebiete-Seite hat einen Gebietswähler: Stanz (2016) und Mittelberg (2005, SRTM + CORINE 2000). Im 10-km-Umkreis liegen 285 Hangmuren; 12 553 Zellen auf deutschem Gebiet werden als „außerhalb Österreichs“ nicht bewertet. Auslaufszenario und Infrastruktur sind unverändert eine unvalidierte Illustration (heutiger OSM-Stand).

## Prüfungen

- `tests/test_wirkungskette_gebietstest.py` und `tests/test_wirkungskette.py`: 65 bestanden, 0 übersprungen. Darunter: Die Merkmalsfunktion liefert auf demselben Fenster exakt die Werte des eingefrorenen V0.4-Codes; das DEM-Fenster reproduziert das V0.4-Fenster; Landbedeckungsjahrgang vor dem Kampagnenjahr; Erfassungsmetrik, Bootstrap und Gebietsregel; der Volllauf wird nur einmal geschrieben.
- Fehlerinjektion (`mutation_tests.json`): 6 von 6 eingebauten Fehlern erkannt. Der Bootstrap-ohne-Gebietsziehung-Fehler wurde erst nach einer Testergänzung erkannt; das ist dort vermerkt.
- Browser: Gebietswechsel Stanz ↔ Mittelberg, Karte mit Relief, Prüfstufen und Korridor; 375 px ohne Seitenüberlauf.

## Ausführen

```text
.\.venv\Scripts\python -m preslide.wirkungskette gt-areas            # Gebietszusammensetzung (keine Modellwerte)
.\.venv\Scripts\python -m preslide.wirkungskette gt-full             # verweigert: Test ist bereits ausgewertet
.\.venv\Scripts\python -m preslide.wirkungskette build --gebiet mittelberg
```
