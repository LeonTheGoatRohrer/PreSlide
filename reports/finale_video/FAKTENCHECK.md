# Finale-Film: Faktencheck (Prototyp, 06.11.2026)

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

## Bewusst nicht gesagt (Entscheidung des Autors)

Der Schalter „Starkregen erwartet“ ruft kein Wetter ab und ändert die Einstufung nicht. Das wird im Film nicht
angesagt. Der Sprechtext behauptet aber auch nicht, dass die App Wetterdaten nutzt. In einer Jury-Fragerunde sollte
die Antwort darauf bereitliegen.
