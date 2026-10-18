# Wirkungskette v02 – Gegenprobe des Auslaufszenarios mit Schadensmeldungen

Stand 2026-10-18. Erzeugt von `python -m preslide.wirkungskette gegenprobe` aus der Registrierung `config/wirkungskette_v02.json` (vor jeder Kettenberechnung für diese Ereignisse festgelegt und committet). Zahlen: `gegenprobe.json`. Explorativ; nichts wurde an den Ergebnissen angepasst.

## Wichtigste Einschränkung zuerst

Das Inventar sagt nicht, ob ein Punkt den Anriss, die Transportbahn, die Ablagerung oder den Schadensort markiert. Hier wird der Punkt als Anriss gesetzt, weil die Kette einen Startpunkt braucht. Liegt der Punkt in Wahrheit am Schadensort, enthält schon der Korridor um den Startpunkt die beschädigte Anlage, und die Übereinstimmung sagt nichts über den Auslauf. **Deshalb wird keine Trefferquote behauptet.** Die Tabellen zeigen nur, ob Szenario und Schadensmeldung qualitativ zusammenpassen oder sich widersprechen.

## Auswahl

Inventar im 10-km-Umkreis des Demozentrums, beide Schadensdetailfelder gesetzt, Ereignisbeginn nach dem DEM-Objektdatum (2016-04-26), keine Sturzprozesse, Lagegenauigkeit höchstens 100 m.

| Ausschlussgrund (in dieser Reihenfolge) | Primärset 2017/2018 | Sekundärset alle Jahre nach DEM |
|---|---:|---:|
| ausserhalb_umkreis | 24976 | 24976 |
| schadensdetail_leer | 572 | 572 |
| ereignis_nicht_nach_dem | 18 | 18 |
| jahr_nicht_im_primaerset | 17 | 0 |
| prozess_ausgeschlossen | 0 | 0 |
| lage_ungenauer_als_100m | 2 | 16 |
| **verbleibend** | **24** | **27** |

Primärset nach Jahr: {2017: 1, 2018: 23}; nach Kampagne: {'Gasen_September_2018': 14, 'ohne Kampagne 2018-06': 9, 'ohne Kampagne 2017-08': 1}.

Sekundärset nach Jahr: {2016: 1, 2017: 1, 2018: 23, 2023: 1, 2025: 1}.

Unabhängige Einheiten: Die Ereignisse eines Tages und eines Gebiets hängen voneinander ab (gleicher Niederschlag, oft gleiche Straße). Das Primärset besteht im Wesentlichen aus den Gasen-Kampagnen Juni und September 2018 plus einem Ereignis 2017, also etwa drei unabhängigen Einheiten, nicht so vielen wie Zeilen.

## Ergebnis (Primärset, qualitativ)

- **Verkehrsanlagen gegen Straße.** 22 von 24 Ereignissen haben Verkehrsanlagen = 1. Bei 21 davon liegt eine Straße im kürzesten, bei 22 im längsten Szenario. Aber bei 20 dieser 22 Ereignisse liegt die nächste Straße schon höchstens 25 m vom Inventarpunkt entfernt. Die Übereinstimmung entsteht also am Startpunkt, nicht entlang des Auslaufs. Das passt dazu, dass die Punkte an der Straße oder am Schadensort gesetzt sein könnten; über die Reichweite des Szenarios sagt es nichts.
- Die Gegengruppe (Verkehrsanlagen = 0) hat nur 2 Ereignisse (1 davon mit Straße am Punkt; im längsten Szenario 2 mit Straße). Damit kann die Tabelle nicht zwischen Ereignissen mit und ohne Straßenschaden unterscheiden.
- **Bauwerke gegen Gebäude.** 6 Ereignisse mit Bauwerke = 1: Gebäude im kürzesten Szenario bei 6, im längsten bei 6 (3 davon mit Gebäude schon am Punkt). 18 Ereignisse mit Bauwerke = 0: Gebäude im kürzesten Szenario bei 7, im längsten bei 15. Das längste Szenario überdeckt also auch dort Gebäude, wo keine Gebäudeschäden gemeldet sind. Überlagerung ist keine Schadensaussage (Volumen, Schutzbauten, Bauweise fehlen), und das längste Szenario ist als obere Reichweite gedacht.
- **Kein Widerspruch, aber auch keine Bestätigung.** Im längsten Szenario gibt es 0 Straßenschäden und 0 Gebäudeschäden ohne entsprechendes Objekt im Korridor. Weil die meisten Punkte schon an der Anlage liegen, ist dieses Fehlen von Widersprüchen nahezu zwangsläufig und keine Validierung des Auslaufs.
- Bei 6 Ereignissen endet das 11°-Energielinien-Szenario schon an der Startzelle (Länge 0 m): Das Gelände fällt dort zur nächsten Abwärtszelle flacher als 11° ab. Das spricht eher für eine Lage auf Straße oder Talboden als für einen Anriss im steilen Hang.
- Lagegenauigkeit der Punkte: {'Lage relativ genau (20-100m)': 24}. Die Unsicherheit von 20–100 m ist größer als die halbe Korridorbreite von 25 m.
- Nicht berechnet, weil nicht registriert: eine Nullreferenz, wie oft ein beliebiger Hangpunkt derselben Gegend eine Straße im Korridor hätte. Ohne sie lässt sich nicht sagen, ob die Übereinstimmung über die Straßendichte hinausgeht.

## Primärset (2017/2018)

### Verkehrsanlagen gegen Straße (primaer)

Schadensfeld `Verkehrsanlagen`; Infrastruktur im Szenario = OSM-Typ strasse schneidet den Korridor.

Kürzestes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 21 | 1 |
| Schadensfeld nein | 1 | 1 |

Längstes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 22 | 0 |
| Schadensfeld nein | 2 | 0 |

### Bauwerke gegen Gebäude (primaer)

Schadensfeld `Bauwerke`; Infrastruktur im Szenario = OSM-Typ gebaeude schneidet den Korridor.

Kürzestes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 6 | 0 |
| Schadensfeld nein | 7 | 11 |

Längstes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 6 | 0 |
| Schadensfeld nein | 15 | 3 |

### Verkehrsanlagen gegen Straße, Forst-/Feldweg oder Bahn (sekundaer)

Schadensfeld `Verkehrsanlagen`; Infrastruktur im Szenario = OSM-Typ strasse, weg, bahn schneidet den Korridor.

Kürzestes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 21 | 1 |
| Schadensfeld nein | 2 | 0 |

Längstes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 22 | 0 |
| Schadensfeld nein | 2 | 0 |

### Kontext: Objekt schon am Punkt

Wie oft die nächste Straße bzw. das nächste Gebäude höchstens 25 m (halbe Korridorbreite) vom Inventarpunkt entfernt ist, also schon der Startkorridor sie enthält:

| Gruppe | Ereignisse | Objekt am Punkt |
|---|---:|---:|
| Verkehrsanlagen_1_strasse_am_punkt | 22 | 20 |
| Verkehrsanlagen_0_strasse_am_punkt | 2 | 1 |
| Bauwerke_1_gebaeude_am_punkt | 6 | 3 |
| Bauwerke_0_gebaeude_am_punkt | 18 | 4 |

## Sekundärset (alle Jahre nach dem DEM, gekennzeichnet sekundär)

### Verkehrsanlagen gegen Straße (primaer)

Schadensfeld `Verkehrsanlagen`; Infrastruktur im Szenario = OSM-Typ strasse schneidet den Korridor.

Kürzestes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 22 | 1 |
| Schadensfeld nein | 3 | 1 |

Längstes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 23 | 0 |
| Schadensfeld nein | 4 | 0 |

### Bauwerke gegen Gebäude (primaer)

Schadensfeld `Bauwerke`; Infrastruktur im Szenario = OSM-Typ gebaeude schneidet den Korridor.

Kürzestes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 7 | 0 |
| Schadensfeld nein | 9 | 11 |

Längstes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 7 | 0 |
| Schadensfeld nein | 17 | 3 |

### Verkehrsanlagen gegen Straße, Forst-/Feldweg oder Bahn (sekundaer)

Schadensfeld `Verkehrsanlagen`; Infrastruktur im Szenario = OSM-Typ strasse, weg, bahn schneidet den Korridor.

Kürzestes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 22 | 1 |
| Schadensfeld nein | 4 | 0 |

Längstes Szenario:

| | im Szenario ja | im Szenario nein |
|---|---:|---:|
| Schadensfeld ja | 23 | 0 |
| Schadensfeld nein | 4 | 0 |

### Kontext: Objekt schon am Punkt

Wie oft die nächste Straße bzw. das nächste Gebäude höchstens 25 m (halbe Korridorbreite) vom Inventarpunkt entfernt ist, also schon der Startkorridor sie enthält:

| Gruppe | Ereignisse | Objekt am Punkt |
|---|---:|---:|
| Verkehrsanlagen_1_strasse_am_punkt | 23 | 21 |
| Verkehrsanlagen_0_strasse_am_punkt | 4 | 2 |
| Bauwerke_1_gebaeude_am_punkt | 7 | 4 |
| Bauwerke_0_gebaeude_am_punkt | 20 | 6 |

## Ereignisse des Primärsets

| ID | Datum | Prozess | Lage | V | B | Route | kürzestes | längstes | Str. kurz/lang | Geb. kurz/lang | nächste Str./Geb. (m) |
|---|---|---|---|---:|---:|---|---|---|---|---|---|
| 1306549_001 | 2018-06-14 | Rutschung oder Hangmure | 20-100m | 1 | 0 | max_laenge | energy_11deg 0 m (gestoppt) | reach_467m 464.6 m (gestoppt) | 1/12 | 2/18 | 0.2 / 10.9 |
| 1306599_001 | 2017-08-06 | Lockergesteinsrutschung | 20-100m | 0 | 1 | max_laenge | reach_45m 42.4 m (gestoppt) | reach_467m 447 m (gestoppt) | 0/1 | 1/1 | 127.1 / 2.4 |
| 1306819_001 | 2018-09-14 | Lockergesteinsrutschung | 20-100m | 1 | 0 | rand | energy_11deg 0 m (gestoppt) | reach_467m 462.4 m (gestoppt) | 1/9 | 3/13 | 13.9 / 22.3 |
| 1306820_001 | 2018-09-14 | Hangmure | 20-100m | 1 | 0 | rand | reach_45m 30 m (gestoppt) | reach_467m 452.1 m (gestoppt) | 1/8 | 0/13 | 20.5 / 48.2 |
| 1306821_001 | 2018-09-14 |  - | 20-100m | 1 | 0 | max_laenge | reach_45m 42.4 m (gestoppt) | reach_467m 434.6 m (gestoppt) | 2/4 | 1/5 | 7.3 / 63.5 |
| 1306822_001 | 2018-09-14 | Lockergesteinsrutschung | 20-100m | 1 | 0 | max_laenge | reach_45m 30 m (gestoppt) | reach_467m 434.6 m (gestoppt) | 1/5 | 0/2 | 13.1 / 92.1 |
| 1306823_001 | 2018-09-14 | Lockergesteinsrutschung | 20-100m | 1 | 0 | max_laenge | reach_45m 42.4 m (gestoppt) | energy_7deg 651.8 m (gestoppt) | 1/3 | 0/2 | 6.2 / 17.6 |
| 1306825_001 | 2018-09-14 | Hangmure | 20-100m | 1 | 1 | max_laenge | reach_45m 42.4 m (gestoppt) | energy_7deg 809.1 m (gestoppt) | 2/4 | 1/3 | 18.5 / 25.4 |
| 1306826_001 | 2018-09-14 | Hangmure | 20-100m | 1 | 0 | max_laenge | reach_45m 30 m (gestoppt) | energy_7deg 796.7 m (gestoppt) | 2/4 | 1/3 | 12.6 / 30.3 |
| 1306827_001 | 2018-09-14 | Hangmure | 20-100m | 1 | 1 | max_laenge | reach_45m 42.4 m (gestoppt) | energy_7deg 754.3 m (gestoppt) | 2/4 | 3/5 | 30.3 / 22.7 |
| 1306828_001 | 2018-09-14 | Hangmure | 20-100m | 1 | 1 | rand | reach_45m 42.4 m (gestoppt) | reach_467m 441.8 m (gestoppt) | 0/4 | 1/4 | 85.2 / 63.5 |
| 1306830_001 | 2018-09-14 | Lockergesteinsrutschung | 20-100m | 0 | 1 | rand | reach_45m 30 m (gestoppt) | reach_467m 439.7 m (gestoppt) | 2/9 | 2/13 | 21.9 / 5.4 |
| 1306831_001 | 2018-09-14 | Rutschung oder Hangmure | 20-100m | 1 | 0 | max_laenge | reach_45m 42.4 m (gestoppt) | reach_467m 454.3 m (gestoppt) | 2/3 | 2/2 | 6.2 / 14.9 |
| 1306832_001 | 2018-09-14 | Hangmure | 20-100m | 1 | 1 | rand | reach_45m 30 m (gestoppt) | reach_467m 457.3 m (gestoppt) | 2/8 | 2/13 | 18 / 32.4 |
| 1306833_001 | 2018-09-14 | Rutschung oder Hangmure | 20-100m | 1 | 0 | max_laenge | reach_45m 30 m (gestoppt) | reach_467m 447 m (gestoppt) | 1/4 | 1/11 | 9 / 46.2 |
| 1306834_001 | 2018-09-14 | Rutschung oder Hangmure | 20-100m | 1 | 0 | rand | reach_45m 42.4 m (gestoppt) | reach_467m 457.3 m (gestoppt) | 1/5 | 0/14 | 4 / 79.7 |
| 1306895_001 | 2018-06-13 | Rutschung oder Hangmure | 20-100m | 1 | 0 | rand | energy_11deg 0 m (gestoppt) | reach_467m 447 m (gestoppt) | 1/2 | 0/2 | 3.5 / 32 |
| 1306896_001 | 2018-06-13 | Lockergesteinsrutschung | 20-100m | 1 | 0 | rand | energy_11deg 0 m (gestoppt) | reach_467m 447 m (gestoppt) | 1/2 | 0/2 | 16.6 / 71.1 |
| 1306897_001 | 2018-06-13 | Lockergesteinsrutschung | 20-100m | 1 | 0 | rand | reach_45m 42.4 m (gestoppt) | reach_467m 434.6 m (gestoppt) | 3/4 | 0/2 | 12.1 / 64.7 |
| 1306898_001 | 2018-06-13 | Rutschung oder Hangmure | 20-100m | 1 | 0 | rand | reach_45m 42.4 m (gestoppt) | energy_7deg 692.1 m (gestoppt) | 1/4 | 0/0 | 5.7 / 151.4 |
| 1306899_001 | 2018-06-13 | Rutschung oder Hangmure | 20-100m | 1 | 0 | rand | energy_11deg 0 m (gestoppt) | reach_467m 427.3 m (gestoppt) | 1/1 | 0/0 | 3 / 213.4 |
| 1306900_001 | 2018-06-13 | Rutschung oder Hangmure | 20-100m | 1 | 0 | rand | energy_11deg 0 m (gestoppt) | reach_467m 447 m (gestoppt) | 1/1 | 0/0 | 1.2 / 92.9 |
| 1306901_001 | 2018-06-13 |  - | 20-100m | 1 | 0 | rand | reach_45m 30 m (gestoppt) | reach_467m 464.6 m (gestoppt) | 1/2 | 0/1 | 14.6 / 243.5 |
| 1306902_001 | 2018-06-13 | Lockergesteinsrutschung | 20-100m | 1 | 0 | rand | reach_45m 30 m (gestoppt) | reach_467m 464.6 m (gestoppt) | 1/2 | 2/3 | 6.2 / 49.6 |

V = Verkehrsanlagen, B = Bauwerke (1 = im Inventar gesetzt). Str./Geb. = Anzahl OSM-Objekte im Korridor.

## Weitere Grenzen

- Punktbezug unbekannt: Der Inventarpunkt kann Anriss, Transportbahn, Ablagerung oder Schadensort markieren.
- OpenStreetMap ist der heutige Stand (2026), nicht der zum Ereignis; Objekte können jünger oder neu gebaut sein.
- Das DEM-Objektdatum 26.04.2016 ist ein Upload-Datum; die zugrunde liegende Vermessung ist älter.
- Verkehrsanlagen = 1 bei fast allen ausgewählten Ereignissen; die Nein-Zeile ist sehr klein.
- Lagegenauigkeit 20–100 m bei den meisten Ereignissen ist größer als die halbe Korridorbreite; ein Treffer oder Fehlen kann allein an der Punktlage liegen.
- Szenarien, Korridor und Infrastrukturtypen stammen unverändert aus `config/wirkungskette_v01.json` (SHA-256 7769ac5183ac…).
- Gezählte Tabellen: 12 (2 primäre und 1 sekundäre Gegenüberstellung × kürzestes/längstes Szenario × Primär-/Sekundärset); alle sind oben berichtet.
