# Finale-Film: Faktencheck (v4, 07.11.2026)

Jede Zahl und Sachaussage im Film mit Quelle. Filmaufnahmen sind KI-generierte Illustrationen und als solche
eingeblendet; sie zeigen keine echten Orte oder Ereignisse. Karten, Punkte, Gelände, Kandidaten und Straßen sind echte Daten.

| Aussage im Film | Wert | Quelle |
|---|---|---|
| Starkregen in Österreich +15 % in 40 Jahren | rund 15 % seit etwa 1980, GeoSphere-Studie mit 883 Stationen | [GeoSphere Austria, Presseunterlage 12.03.2025](https://geosphere.at/de/dokumente/news/news_presse/geosphere_studie-starkregen-zunahme_250312_final.pdf/@@download/file), über Suchergebnis, PDF selbst nicht ausgelesen |
| Murenauslösender Regen wahrscheinlicher, größere Flächen | Projektion, alle Emissionsszenarien, regional ungleich, über 3 600 Wildbachereignisse | Kaitna et al. 2025, Communications Earth & Environment 6, [DOI 10.1038/s43247-025-02760-w](https://doi.org/10.1038/s43247-025-02760-w), nur Abstract gelesen |
| 25 609 Einträge, alle Naturgefahren | 25 609 | `data/raw/geosphere_natural_hazards.json` |
| 423 Ereignisse, je 5 Kontrollen | 423 Gruppen | `reports/v04/summary.md` |
| Zwillinge: ± 5°, ± 150 m, ± 45°, 750 m bis 10 km, gleicher Stichtag | Kaliber | `preslide/matching.py`, `PROJEKTUEBERBLICK.md` |
| Beispiel Tamsweg 05.07.2023, Kandidaten und 5 Kontrollen | echte Gruppe `1310420_001` | `data/v04/cache/control_pools/`, V0.4-Datensatz |
| Versiegelter Test 0,75 [0,63; 0,87] | 0,751 [0,633; 0,866] | `reports/v04/summary.md` |
| Gelände 0,70, Wetter 0,60 | 0,702, 0,604 | `reports/v04/summary.md` |
| Zusatz Wetter nicht belegt | +0,049 [−0,003; +0,108] | `reports/v04/summary.md` |
| 11 Episoden, eine mit 243 von 300 | Stanz 2016 | `PROJECT_STATE.md` |
| 24,6 % statt 5 %, Intervall [11,8; 38,2], 35 Episoden | explorativ, Haupttest 0,587 [0,481; 0,691] nicht erfüllt | `reports/extremwetter_v01/summary.md` |
| 0,93 nur Abstand zu Straßen und Gebäuden | 0,928, ungematchtes V0.5-Design, explorativ | `reports/v07/summary.md` |
| 0,78 bei ähnlicher Nähe zu Infrastruktur | 0,783 [0,679; 0,888], 173 Gruppen, 10 Einheiten, explorativ | `reports/v07/summary.md` |
| Gasteiner Tal: kein Ereignis im Modell bekannt | 0 Ereignisse im 20-km-Umkreis von Bad Gastein in V0.4/V0.5 | `reports/weiterentwicklung_2026-10-18/VIDEO_PITCH_SKRIPT.md` auf Branch `claude/video-pitch-script-497edf` |
| Möglicher Weg hangabwärts | D8-Route, Reichweiten aus der Literatur, ungeprüft | `reports/wirkungskette_v01/summary.md` |
| Prüfstufen noch nicht an neuen Gebieten bestätigt | in Stanz keine Bündelung (Stufe 1: 3,4 % der Ereignisse auf 5 % der Fläche) | `reports/wirkungskette_v01/summary.md` |
| Reine Hangmuren kaum getrennt | 0,539 [0,406; 0,669], explorativ | `reports/mudslide_cascade_v01/summary.md` auf Branch `portfolio/2026-10-29` |

## Neu in v4

| Aussage im Film | Wert | Quelle |
|---|---|---|
| 0,75 ist eine AUC, Fläche unter der Kurve, lokal je Ereignisgruppe, jede Episode gleich gewichtet | gewichtete lokale AUC 0,751 | `reports/v04/summary.md`, Zeile 140 |
| „rund 3 von 4 Vergleichen“ | Lesart der lokalen AUC: Anteil der Paare betroffener Hang gegen Zwilling, in denen der betroffene vorne liegt; Episoden gleich gewichtet | wie oben |
| Jedes Ereignis gleich gewichtet: 0,67 | 0,668 | `reports/v04/summary.md`, Zeile 147 (lokale AUC ungewichtet) |
| Pfeil- und Rasterbild „8 Paare“, „100 Vergleiche“, Kurve | **Schema, keine Messwerte.** Kurve y = x^(1/3) hat rechnerisch die Fläche 0,75. Die lokale AUC ist ein Mittel über Gruppen und hat keine einzelne gemessene Kurve | im Film als Schema beschriftet |
| Regenbalken Tamsweg, 60 Tage bis 05.07.2023 | echte INCA-Tageswerte des positiven Samples `1310420_001`, 61 Tage, 196,4 mm; ab t₀ bewusst keine Daten | `data/v04/run_c6d67a854ba7/weather/history_2023-07-05_*.parquet` |
| Plan 13:23, eingefroren 15:39:31, Test 15:39:41, alle am 14.10.2026 UTC | Zeitstempel | `reports/v04/PREREGISTRATION.json`, `FREEZE.json`, `test_results.json` |
| 123 Ereignisse / 19 Einheiten, 300 / 11 | Aufteilung | `PROJEKTUEBERBLICK.md`, `reports/v04/summary.md` |
| Gelände 0,70 → Gelände + Wetterdaten 0,75, Balken ab 0,5 | 0,702, 0,751; Zuwachs +0,049 [−0,003; +0,108] | `reports/v04/summary.md` |
| „Extrem nass“ = nasseste 5 von 100 Zeiträumen je 3 Tage je Ort, ±15 Kalendertage, 1991 bis 2025; „wenn der Regen egal wäre“ 5 von 100 per Definition; „rund 25“ | 95. Perzentil der Referenz; gemessen 24,6 % | `reports/extremwetter_v01/summary.md` |
| 93 von 100 Vergleichen | Lesart von 0,928 (bedingte log. Regression, nur Infrastruktur; Vergleichspunkte ungematcht) | `reports/v07/summary.md`, Zeile 11 |

Hergestellt mit: im Kaltstart zwei echte, gemeinfreie USGS-Aufnahmen von Murgängen (Elk-Fire-Brandfläche bei Dayton, Wyoming, 15.07.2025, https://www.usgs.gov/media/videos/postfire-debris-flow-2024-elk-fire-burn-area; Las Lomas, https://www.usgs.gov/media/videos/las-lomas-debris-flow, Ort und Datum dort nicht angegeben), im Bild als echte Aufnahme beschriftet; Berg und Narbe im Finale Kling 4.0 aus Standbildern von GPT Image 2.6, hinter der +15-%-Einblendung ein solches Standbild mit Kamerabewegung, Musik ElevenLabs Music v2.5, Sprecher Alistair (ElevenLabs v4 über Higgsfield), der letzte Satz zusätzlich tiefer, in drei Wörter mit langen Pausen geschnitten. Alles KI-generiert und im Film so gekennzeichnet.

## Noch offen vor der Abgabe

- GeoSphere-Presseunterlage (+15 %) ist nur über ein Suchergebnis belegt, Kaitna et al. 2025 nur als Abstract. Beides vor der Abgabe im Original nachlesen.
- Die Datei `reports/mudslide_cascade_v01/summary.md` (0,54) liegt nicht auf diesem Branch.

## Bewusst nicht gesagt (Entscheidung des Autors)

Der Schalter „Starkregen erwartet“ ruft kein Wetter ab und ändert die Einstufung nicht. Das wird im Film nicht
angesagt. Der Sprechtext behauptet aber auch nicht, dass die App Wetterdaten nutzt. In einer Jury-Fragerunde sollte
die Antwort darauf bereitliegen.
