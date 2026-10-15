# Pipeline B satellite-0.4 — geführte Suche mit manueller Prüfung (Stage 6)

Stand: 2026-10-15. Status: Plan registriert **vor** dem ersten Scan; Umsetzung siehe `preslide/satellite/scan.py`.

## Ziel

Messen, wie viele der vom Detektor vorgeschlagenen Stellen tatsächlich Rutschungen sind (Precision), wenn der Nutzer
Region und Zeitfenster vorgibt und jeden Kandidaten von Hand prüft. Die Labels sind danach eine eigene, klar
gekennzeichnete Datenbasis. Es wird **nur Precision** gemessen; Recall ist nicht messbar (kein Inventar der
„nicht gefundenen“ Rutschungen).

## Nicht-Ziele

- Kein Eingriff in Pipeline A, V0.4/V0.5, `PREREGISTRATION.json`, Baseline-Hashes oder `test_results.json`.
- Keine Behauptung „Rutschung gefunden“ ohne manuelle Bestätigung; Status bleibt `UNVERIFIED`, bis das Label vorliegt.
- Labels fließen **nicht** in einen bereits gesehenen Test ein; Nutzung als Training erst in einer neuen Version.

## Ablauf

1. **Eingabe:** `--name`, `--bbox lon_min lat_min lon_max lat_max`, `--before-start/--before-end`
   (Referenzfenster vor dem Ereignis), `--after-start/--after-end` (Fenster nach dem Ereignis).
2. **Kacheln:** Region in überlappende 2,56-km-Kacheln (Schrittweite 1,6 km = Kante − 2 × 480 m Rand).
3. **Bildpaar pro Kachel:** STAC-Suche (Earth Search Sentinel-2), je Fenster die Aufnahme mit dem geringsten
   Wolken-/Schnee-/Nodata-Anteil **über die ganze Kachel**; zusätzlich eine spätere Bestätigungsaufnahme
   (`confirm`), wenn vorhanden. Kachel ohne brauchbares Paar → protokolliert mit Grund, nie stillschweigend.
4. **Detektor:** unverändert satellite-0.3 (gepufferte Wolkenmaske 100 m, Log-Odds-LR, Peaks ≥ 320 m Abstand).
   Trainiert auf allen Ereignisgruppen **ohne** die Unabhängigkeitseinheiten der bekannten Ereignisse in der Region,
   damit der Rückfund bekannter Ereignisse ehrlich bleibt.
5. **Bekannte Ereignisse:** Peaks innerhalb 160 m eines dokumentierten V0.4-Positivs werden getrennt gezählt
   (Rückfund = Plausibilitätsprüfung), nicht als Kandidaten geprüft.
6. **Persistenz:** Bestätigungspaar wird mit derselben Regel bewertet wie in Stage 5 (`persistence_rule`).
7. **Prüfbogen:** eine selbständige HTML-Datei (`data/satellite/scan/<name>/review.html`, lokal, nicht im Git):
   je Kandidat vorher/nachher/Bestätigung/ΔNDVI, Verdikt `Rutschung / keine Rutschung / unsicher` + Notiz,
   Export als `labels.json`. Die Reihenfolge ist **gemischt**, Rang und Score sind verborgen.
   Stichprobe: Top-N nach Score (Stratum `top`) **plus** M zufällige niedriger bewertete Peaks (Stratum `random`),
   damit sich der Nutzen des Rankings gegen die Basisrate messen lässt.
8. **Auswertung:** `scan-labels` liest `labels.json`, schreibt `reports/satellite/scan_<name>_results.json`:
   Precision@N (Top-Stratum), Rate im Zufallsstratum, Anteil unsicher, Rückfundrate bekannter Ereignisse,
   gescannte km², Kacheln mit/ohne Paar. Konfidenzintervall nach Wilson; effektive Stichprobe = Zahl der Kandidaten,
   aber Kandidaten innerhalb eines Sturms sind abhängig → im Bericht ausweisen.

## Erfolgskriterien (vorab festgelegt)

- Pilot: ≥ 1 Region mit dokumentierten Ereignissen; Rückfundrate bekannter Ereignisse wird berichtet (Vergleichswert
  Stage 5 mit Puffer: 40/129 im Suchfenster, daher ist niedrige Rückfundrate zu erwarten und kein Fehler).
- Precision@30 wird so berichtet, wie sie ist. Ein Ergebnis von 0 echten Rutschungen ist ein gültiges Ergebnis.
- Keine Anpassung von Schwellen nach Sicht der Labels. Änderungen = neue Version, vorher registriert.

## Bekannte Risiken

- 10-m-Auflösung: kleine Rutschungen (< ~20 m) bleiben unsichtbar; „nicht gefunden“ ≠ „nicht passiert“.
- Prüfung mit Sentinel-2 allein ist unsicher; für Zweifelsfälle Orthofoto (basemap.at, Land Steiermark) heranziehen
  und im Notizfeld vermerken (`quelle: orthofoto`).
- Wolken-/Dunstränder dominierten Stage 5; Puffer ist aktiv, Restrisiko bleibt.
- Sturm-Cluster: viele Kandidaten desselben Tages sind nicht unabhängig.
- GDAL kann bei hoher Parallelität abstürzen (Exit 139): Scan läuft mit 2 Workern, jede Kachel ist gecacht, Neustart setzt fort.

## Arbeitsschritte

1. Config `scan`-Abschnitt + Version satellite-0.4 (vor Lauf). ✔ siehe Commit
2. `scan.py`: Kachelung, Paarwahl, Scan, Dedup, Prüfbogen, Auswertung (reine Funktionen getestet).
3. CLI-Stufen `scan`, `scan-labels`.
4. Tests (Kachelung, Dedup, Precision/Wilson, Prüfbogen-Verblindung, Fenster-Reihenfolge vorher < nachher).
5. Pilot auf kleiner Region (1 → 4 Kacheln), dann Region.
6. `PROJECT_STATE.md` aktualisieren.
