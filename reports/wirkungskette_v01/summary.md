# Wirkungskette v01 – Prüfpunkt → Auslaufszenario → Infrastruktur (Demogebiet Stanz)

Stand 18.10.2026 · Branch `claude/wirkungskette-v01-f4836f` · explorative technische Demonstration, kein neues Ergebnis, kein Test.

## Was gebaut wurde

Auf der Seite `#/pruefgebiete` lässt sich für ein Demogebiet die ganze Kette verfolgen:

1. **Prüfpunkte (Befund):** relative Rangfolge von Hangzellen (90-m-Raster) im wählbaren Umkreis von 1–10 km. Grundlage ist das eingefrorene V0.4-Statikmodell. Es wurde nur auf den 123 Entwicklungsereignissen trainiert; die Modelldatei ist per SHA-256 identisch mit `reports/v04/FREEZE.json`. Stufe 1 = oberste 5 %, Stufe 2 = nächste 15 %, Stufe 3 = nächste 30 %, Stufe 4 = Rest, immer relativ zum gewählten Umkreis. Die Grenze von 10 km folgt aus dem V0.4-Design, dessen Kontrollen 750 m bis 10 km entfernt lagen.
2. **Auslaufszenario (Szenario, unvalidierte Illustration):** Abwärtsroute nach steilstem Gefälle (D8) auf dem gefüllten 30-m-DEM. Getrennte Endgründe: Rand, Nodata, Senke, Höchstlänge. Ein Randaustritt wird nie als Auslaufende ausgegeben. Vier Reichweiten werden immer zusammen als Band gezeigt:
   - 45 m und 467 m: Median und Maximum der horizontalen Reichweite von 178 Hangmuren auf offenem Hang (Hürlimann, McArdell & Rickli 2015).
   - Energielinie 11° und 7° mit Geschwindigkeitsgrenze 15 m/s (Horton et al. 2013, Flow-R, nach Zimmermann et al. 1997). Das sind Minimalwinkel für Muren, also die obere Reichweite.
   - Keine dieser Zahlen wurde an Ereignissen angepasst. Korridorbreite 50 m als benannte Darstellungsannahme.
3. **Exposition (Szenario):** Gebäude, Straßen, Forst- und Feldwege sowie Bahn aus OpenStreetMap (heutiger Stand), verschnitten mit jedem Szenariokorridor. Formulierung: „liegt im Auslaufszenario“.

Die Karte nutzt eine lokal aus dem DEM gerechnete Schummerung und optionale Höhenlinien, kein Satellitenbild und keine externen Kacheln. Unter der Karte liegt ein SVG-Geländeschnitt mit Anriss, Szenario-Stopps, Energielinien und Band. Jede Ebene ist als Befund, Szenario oder Illustration gekennzeichnet.

## Demogebiet

Stanz im Mürztal, Zentrum 47,44533° N / 15,49683° E (Cluster TE001, 25.07.2016: 243 Ereignisse, davon 56 Hangmuren). Der Sturm gehört zum versiegelten V0.4-Test, der bereits einmal ausgewertet wurde. Er dient hier nur als gekennzeichnete Demonstration; nichts wurde daran angepasst. Gelände (Skadi-Kachel, Stand 26.04.2016) und Landbedeckung (CLC2012) stammen nachweislich von vor dem Ereignis, die Infrastruktur nicht.

Rechenfenster: Radius 15,31 km (1021 × 1021 Zellen à 30 m, 0 Nodata). Im 10-km-Umkreis liegen 38 797 Rasterzellen, davon 36 569 bewertbar; 2 222 sind flacher als 5°, bei 6 ist das Einzugsgebiet abgeschnitten. Von 241 dokumentierten Ereignissen sind 238 bewertbar. Infrastruktur im Fenster: 39 041 Gebäude, 11 286 Straßen-, 9 886 Weg- und 810 Bahnabschnitte.

## Ergebnisse im Standardumkreis 3 km (Modus „Oberste Prüfpunkte“)

| Prüfpunkt | Höhe | Neigung | Landbedeckung | stärkste Treiber | Reichweite (45 m / 467 m / 11° / 7°) | Gebäude im Szenario (Spanne) | Straßen (Spanne) |
|---|---:|---:|---|---|---|---:|---:|
| P1 | 687 m | 53° | Wald | Rauigkeit, Hangposition 150 m, Wald | 42 / 435 / 102 / 187 m | 0–5 | 0–7 |
| P2 | 837 m | 40° | Grünland/Gebüsch | Rauigkeit, Wald, Hangposition | 30 / 462 / 360 / 432 m | 0–11 | 0–8 |
| P3 | 883 m | 37° | Landwirtschaft | Rauigkeit, Wald, Hangposition | 30 / 435 / 597 / 1219 m | 0–15 | 0–11 |
| P4 | 743 m | 32° | Grünland/Gebüsch | Rauigkeit, Hangposition, Wald | 30 / 440 / 60 / 470 m | 0–13 | 0–7 |
| P5 | 675 m | 21° | Siedlung/Verkehr | Landbedeckung Siedlung, Wald, Geologie | 30 / 447 / 60 / 175 m | 3–33 | 3–13 |

Alle 20 Szenarien enden innerhalb des Rechengebiets. Die volle D8-Route läuft danach entlang der Mürz bis zur Höchstlänge von 15 km weiter; das ist der Wasserweg, kein Auslauf.

Modus „Dokumentierte Hangmuren“ (55 im 3-km-Umkreis, Inventarpunkt als Anriss angenommen): Im längsten Szenario liegt bei 15 der 55 mindestens ein Gebäude, im kürzesten bei keinem. Mindestens eine Straße liegt im längsten Szenario bei 54, im kürzesten bei 9.

## Explorativer Befund (gesehene Daten, nur beschreibend)

Anteil der dokumentierten Ereignisse des 25.07.2016 je Prüfstufe gegen den Flächenanteil (3 km):

| Stufe | Fläche | alle Ereignisse (238) | Hangmuren (55) |
|---|---:|---:|---:|
| 1 | 5,0 % | 3,4 % | 1,8 % |
| 2 | 15,0 % | 13,4 % | 20,0 % |
| 3 | 30,0 % | 29,4 % | 34,5 % |
| 4 | 50,0 % | 53,8 % | 43,6 % |

**Die Prüfstufen konzentrieren die dokumentierten Ereignisse im Demogebiet nicht.** Das passt zum versiegelten Test: Für den Stanz-Sturm erreichte das Gelände allein pro Ereignis nur 0,455. Bei 10 km ist das Bild ähnlich (Stufe 1: 4,2 % der Ereignisse, 1,8 % der Hangmuren). Die obersten Prüfpunkte liegen oft an steilen, rauen Flanken nahe Straßen; P5 liegt mitten in Siedlungsfläche, und dort ist die Landbedeckung „Siedlung/Verkehr“ der stärkste Treiber. Das ist ein sichtbarer Hinweis auf den bekannten Meldebias des Modells.

## Was das zeigt und was nicht

- Gezeigt wird eine nachvollziehbare, reproduzierbare Kette vom Hang bis zur Infrastruktur, mit offenen Annahmen und ehrlichen Schwächen.
- Nicht gezeigt wird eine geprüfte Prüfpunktauswahl: Die lokale Auswertung spricht im Demogebiet dagegen, und für reine Hangmuren trennt eine Geländevorauswahl kaum (Pilot mudslide_cascade_v01, lokale AUC 0,539 [0,406; 0,669]).
- Ebenfalls nicht gezeigt wird ein geprüfter Auslauf. Das Inventar enthält keine Auslauf- oder Ablagerungsgeometrien, für Stanz sind alle Schadensfelder leer (Audit). Volumen, Material, Wassergehalt, Materialaufnahme, Schutzbauten und Fließtiefe fehlen.
- Es gibt keine Eintritts- oder Schadensaussage und keine Gesamtstufe aus Prüfstufe und Auslauf.

## Prüfungen

- `pytest tests/test_wirkungskette.py`: 38 bestanden, 0 übersprungen. Abgedeckt sind Radiusgrenzen, Metrik in EPSG:31287 (Grad werden abgelehnt), streng fallende D8-Route (auch auf 40 Zufallsstarts im echten Fenster), getrennte Endgründe, analytischer Energielinien-Stopp, Korridorzählung, keine verbotenen Wörter in API-Antworten, Cache-Identität. Ein Regressionstest deckt die Gleichheit von 10000 und 10000.0 in der Cache-Identität ab; der Fehler wurde während der Arbeit gefunden.
- Gesamte Pytest-Suite im Worktree: 214 bestanden, 7 fehlgeschlagen, 4 Fehler, 0 übersprungen. Alle 11 Ausfälle liegen in `test_baseline.py`, `test_stability.py` und einem V0.4-Checkpoint-Test. Ursachen sind die Worktree-Umgebung: nicht versionierte Baseline-Berichte (`reports/baseline/*.csv`, `baseline_membership.json`) fehlen, und Pfade über die data/models-Junctions liegen außerhalb des Worktrees. Keine dieser Dateien wurde verändert. Diese datenabhängigen Prüfungen und `verify_state.py`/`verify_v04.py` wurden hier also **nicht** bestanden gemeldet, sondern sind in der Hauptkopie nach dem Merge zu wiederholen.
- Fehlerinjektion (`scripts/wirkungskette_mutation_check.py` → `mutation_tests.json`): 11 eingebaute Fehler, alle 11 von den zugehörigen Tests erkannt.
- Frontend: 18 Tests bestanden (davon 7 neu), darunter ein Wortwahl-Test über alle eigenen Vue-Dateien. Er schlug bei einem absichtlich eingesetzten „Risiko“ an. `npm run build` bestanden.
- Browser (eigener Server, Port 8041): Desktop 1440 px mit Karte, Panel, Profil und Treffertabelle; 375 px ohne Seitenüberlauf (`scrollWidth` 375), Profil auf Telefonbreite lesbar. Das automatische Zoomen auf den Anrisspunkt nach der Auswahl ließ sich im verdeckten Browserfenster nicht bestätigen; der Knopf „Zum Anrisspunkt“ funktioniert.

## Ausführen

```text
.\.venv\Scripts\python -m preslide.wirkungskette build   # DEM, Merkmale, Relief, OSM (einmalig, ~2 min, gecacht)
.\.venv\Scripts\python -m preslide.wirkungskette audit   # reports/wirkungskette_v01/audit.json
.\.venv\Scripts\python -m preslide.wirkungskette pilot   # 1→5 Anrisspunkte als Text
```

API: `GET /api/wirkungskette?radius_m=3000&modus=pruefpunkte|hangmuren&anriss=<id>`, `/relief`, `/relief.png`, `/hoehenlinien`, `/pruefstufen?radius_m=`, `/pruefstufen.png?radius_m=`, `/kontext?radius_m=`.
