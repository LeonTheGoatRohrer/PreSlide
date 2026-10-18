# Wirkungskette v03 – Nullreferenz zur v02-Gegenprobe

Stand 2026-10-18. Erzeugt von `python -m preslide.wirkungskette nullreferenz` aus der Registrierung `config/wirkungskette_v03.json` (vor dem Ziehen der Referenzpunkte festgelegt und committet). Zahlen: `nullreferenz.json`. **Explorativ.** Keine Trefferquote, keine Validierung; nichts wurde an den Ergebnissen angepasst.

## Frage

v02 fand: Bei 22/22 Ereignissen mit Verkehrsanlagen = 1 liegt eine Straße im längsten Auslaufszenario, bei 20/22 aber schon höchstens 25 m vom Inventarpunkt. Ohne Vergleich bleibt offen, ob das mehr ist als die Straßendichte der Gegend. Hier läuft dieselbe unveränderte v01-Kette (gleiche Szenarien, gleicher Korridor, gleiche Trefferregel, gleiche 25-m-Regel) für Hangpunkte derselben Gegend, die keine Inventarereignisse sind.

## Referenzpunkte

- Gebiet (Änderung 1, vor jeder Auswertung festgehalten): Zellen höchstens 2000 m vom nächsten der 24 v02-Primärereignisse, 60.7 km², davon 49.19 km² im 10-km-Rechenfenster (Anteil außerhalb 19%, dort gibt es keine Zellen). Die ursprünglich registrierte Regel (Kreis um den Schwerpunkt) ergab 7,4 km Radius, weil zwei Breitenauer Ereignisse 6–8 km westlich der Gasener Gruppe liegen; das wäre ein Drittel des Fensters gewesen, nicht dieselbe Gegend.
- Mindestabstand 250 m zu jedem Inventarpunkt (alle Prozesse, Jahre, Lageklassen).
- 500 Zellen je Rahmen, fester Seed 20261018, ohne Zurücklegen.

| Rahmen | Zellen im Gebiet | zu nah am Inventar | zulässig | gezogen | 1-km-Blöcke |
|---|---:|---:|---:|---:|---:|
| bewertbare Hangzellen | 5998 | 1475 | 4523 | 500 | 61 |
| alle Rasterzellen | 6072 | 1504 | 4568 | 500 | 64 |

Unabhängige Einheiten der Ereignisse: Gasen_September_2018 (14), ohne Kampagne 2018-06 (9), ohne Kampagne 2017-08 (1).

## Ergebnis (explorativ)

- **Straße im längsten Szenario.** Ereignisse mit Verkehrsanlagen = 1: 22/22 (1.00); bewertbare Referenz-Hangzellen: 395/500 (0.79), Intervall [0.68; 0.88]. Differenz +0.21 [0.12; 0.33]: über der Nullreferenz. Die Übereinstimmung im längsten Szenario geht in diesen Einheiten über das hinaus, was Hangpunkte derselben Gegend zeigen. Aufgeschlüsselt (beschreibend, kein eigener Vergleich): 20 der 20 Ereignisse mit Straße am Punkt und 2 der 2 ohne Straße am Punkt haben eine Straße im längsten Szenario. Der Überschuss gegenüber der Referenz kommt damit aus den Ereignissen mit Straße schon am Punkt; über den Auslauf der Ereignisse ohne Straße am Punkt sagt der Vergleich bei so wenigen Fällen nichts.
- **Straße höchstens 25 m vom Punkt.** Ereignisse: 20/22 (0.91); Referenz: 18/500 (0.04). Differenz +0.87 [0.80; 0.98]: über der Nullreferenz. Die Inventarpunkte liegen in diesen Einheiten öfter direkt an einer Straße als Hangpunkte derselben Gegend. Das passt zu Punkten, die an der Straße oder am Schadensort gesetzt wurden (Meldebezug), und sagt nichts über die Reichweite des Auslaufs.
- Mit allen Rasterzellen (auch flache Talbodenzellen) als Referenz: Straße im längsten Szenario 391/500 (0.78) (über der Nullreferenz), Straße am Punkt 16/500 (0.03) (über der Nullreferenz).
- **Gebäude.** Ereignisse mit Bauwerke = 1: im längsten Szenario 6/6 (1.00), Referenz 338/500 (0.68) (über der Nullreferenz); Gebäude am Punkt 3/6 (0.50) gegen 10/500 (0.02) (über der Nullreferenz). Nur 6 Ereignisse.
- Die Ereignisintervalle beruhen auf sehr wenigen unabhängigen Einheiten: Verkehrsanlagen = 1 auf 2 (4 exakte Resamples), Bauwerke = 1 auf 2, alle Primärereignisse auf 3. Die Intervalle sind grob und unterschätzen die Unsicherheit; wo alle Einheiten denselben Anteil haben, fällt das Intervall auf einen Punkt zusammen. Die Einordnung „über der Nullreferenz“ beschreibt daher nur diese Einheiten und ist kein belastbarer Befund.
- Keine Trefferquote, keine Validierung des Auslaufs: Dass ein Szenario eine Straße überdeckt, heißt nicht, dass sie beschädigt würde, und Referenzzellen sind nur nicht im Inventar, nicht nachweislich stabil.

## Primäre Vergleiche (Referenz: bewertbare Hangzellen)

Ereignisintervall: exakter Cluster-Bootstrap über die unabhängigen Einheiten. Referenzintervall: Block-Bootstrap über 1-km-Blöcke (2000 Ziehungen). Differenz: Ereignisanteil minus Referenzanteil, gemeinsame Ziehungen. 95-%-Perzentilintervalle.

| Merkmal | Ereignisgruppe | Ereignisse | Referenz | Differenz | Einordnung |
|---|---|---|---|---|---|
| Straße im kürzesten Szenario | Verkehrsanlagen = 1 | 21/22 = 0.95 [0.92; 1.00] | 40/500 = 0.08 [0.04; 0.12] | +0.88 [0.82; 0.94] | über der Nullreferenz |
| Straße im längsten Szenario | Verkehrsanlagen = 1 | 22/22 = 1.00 [1.00; 1.00] | 395/500 = 0.79 [0.68; 0.88] | +0.21 [0.12; 0.33] | über der Nullreferenz |
| Straße ≤ 25 m vom Punkt | Verkehrsanlagen = 1 | 20/22 = 0.91 [0.85; 1.00] | 18/500 = 0.04 [0.02; 0.06] | +0.87 [0.80; 0.98] | über der Nullreferenz |
| Gebäude im kürzesten Szenario | Bauwerke = 1 | 6/6 = 1.00 [1.00; 1.00] | 15/500 = 0.03 [0.01; 0.05] | +0.97 [0.95; 0.98] | über der Nullreferenz |
| Gebäude im längsten Szenario | Bauwerke = 1 | 6/6 = 1.00 [1.00; 1.00] | 338/500 = 0.68 [0.57; 0.78] | +0.32 [0.22; 0.43] | über der Nullreferenz |
| Gebäude ≤ 25 m vom Punkt | Bauwerke = 1 | 3/6 = 0.50 [0.40; 1.00] | 10/500 = 0.02 [0.01; 0.03] | +0.48 [0.37; 0.99] | über der Nullreferenz |

## Sekundäre Vergleiche

### Referenz: bewertbare Hangzellen

| Merkmal | Ereignisgruppe | Ereignisse | Referenz | Differenz | Einordnung |
|---|---|---|---|---|---|
| Straße im kürzesten Szenario | alle Primärereignisse | 22/24 = 0.92 [0.00; 1.00] | 40/500 = 0.08 [0.04; 0.12] | +0.84 [-0.08; 0.92] | nicht von der Nullreferenz unterscheidbar |
| Straße im längsten Szenario | alle Primärereignisse | 24/24 = 1.00 [1.00; 1.00] | 395/500 = 0.79 [0.68; 0.88] | +0.21 [0.12; 0.33] | über der Nullreferenz |
| Straße ≤ 25 m vom Punkt | alle Primärereignisse | 21/24 = 0.88 [0.00; 1.00] | 18/500 = 0.04 [0.02; 0.06] | +0.84 [-0.03; 0.96] | nicht von der Nullreferenz unterscheidbar |
| Gebäude im kürzesten Szenario | alle Primärereignisse | 13/24 = 0.54 [0.22; 1.00] | 15/500 = 0.03 [0.01; 0.05] | +0.51 [0.20; 0.97] | über der Nullreferenz |
| Gebäude im längsten Szenario | alle Primärereignisse | 21/24 = 0.88 [0.67; 1.00] | 338/500 = 0.68 [0.56; 0.78] | +0.20 [-0.04; 0.39] | nicht von der Nullreferenz unterscheidbar |
| Gebäude ≤ 25 m vom Punkt | alle Primärereignisse | 7/24 = 0.29 [0.11; 1.00] | 10/500 = 0.02 [0.01; 0.03] | +0.27 [0.09; 0.98] | über der Nullreferenz |

### Referenz: alle Rasterzellen

| Merkmal | Ereignisgruppe | Ereignisse | Referenz | Differenz | Einordnung |
|---|---|---|---|---|---|
| Straße im kürzesten Szenario | Verkehrsanlagen = 1 | 21/22 = 0.95 [0.92; 1.00] | 29/500 = 0.06 [0.03; 0.09] | +0.90 [0.84; 0.96] | über der Nullreferenz |
| Straße im längsten Szenario | Verkehrsanlagen = 1 | 22/22 = 1.00 [1.00; 1.00] | 391/500 = 0.78 [0.67; 0.88] | +0.22 [0.12; 0.33] | über der Nullreferenz |
| Straße ≤ 25 m vom Punkt | Verkehrsanlagen = 1 | 20/22 = 0.91 [0.85; 1.00] | 16/500 = 0.03 [0.01; 0.05] | +0.88 [0.80; 0.98] | über der Nullreferenz |
| Gebäude im kürzesten Szenario | Bauwerke = 1 | 6/6 = 1.00 [1.00; 1.00] | 16/500 = 0.03 [0.02; 0.05] | +0.97 [0.95; 0.98] | über der Nullreferenz |
| Gebäude im längsten Szenario | Bauwerke = 1 | 6/6 = 1.00 [1.00; 1.00] | 324/500 = 0.65 [0.55; 0.74] | +0.35 [0.25; 0.45] | über der Nullreferenz |
| Gebäude ≤ 25 m vom Punkt | Bauwerke = 1 | 3/6 = 0.50 [0.40; 1.00] | 11/500 = 0.02 [0.01; 0.04] | +0.48 [0.37; 0.99] | über der Nullreferenz |
| Straße im kürzesten Szenario | alle Primärereignisse | 22/24 = 0.92 [0.00; 1.00] | 29/500 = 0.06 [0.03; 0.09] | +0.86 [-0.05; 0.94] | nicht von der Nullreferenz unterscheidbar |
| Straße im längsten Szenario | alle Primärereignisse | 24/24 = 1.00 [1.00; 1.00] | 391/500 = 0.78 [0.67; 0.88] | +0.22 [0.12; 0.32] | über der Nullreferenz |
| Straße ≤ 25 m vom Punkt | alle Primärereignisse | 21/24 = 0.88 [0.00; 1.00] | 16/500 = 0.03 [0.01; 0.06] | +0.84 [-0.03; 0.96] | nicht von der Nullreferenz unterscheidbar |
| Gebäude im kürzesten Szenario | alle Primärereignisse | 13/24 = 0.54 [0.22; 1.00] | 16/500 = 0.03 [0.01; 0.05] | +0.51 [0.20; 0.96] | über der Nullreferenz |
| Gebäude im längsten Szenario | alle Primärereignisse | 21/24 = 0.88 [0.67; 1.00] | 324/500 = 0.65 [0.55; 0.74] | +0.23 [-0.02; 0.43] | nicht von der Nullreferenz unterscheidbar |
| Gebäude ≤ 25 m vom Punkt | alle Primärereignisse | 7/24 = 0.29 [0.11; 1.00] | 11/500 = 0.02 [0.01; 0.04] | +0.27 [0.09; 0.97] | über der Nullreferenz |

## Beschreibung der Referenzpunkte

| Rahmen | Routenende | kürzestes Szenario 0 m | Median nächste Straße (m) | Median nächstes Gebäude (m) |
|---|---|---:|---:|---:|
| bewertbare Hangzellen | max_laenge 399, rand 101 | 22 | 316.4 | 230.3 |
| alle Rasterzellen | max_laenge 397, rand 103 | 18 | 352.8 | 231.9 |
| Primärereignisse (v02) | – | – | 12.3 | 47.2 |

## Grenzen

- Punktbezug unbekannt: Inventarpunkte können am Schadensort liegen, Referenzzellen sind Zellanker im Hang. Genau dieser Unterschied kann die Differenz erklären.
- OpenStreetMap ist der heutige Stand (2026).
- Drei unabhängige Ereigniseinheiten; jedes Intervall daraus ist grob.
- Das Gebiet ist aus den Ereignislagen abgeleitet; es beschreibt die Infrastrukturdichte um diese Ereignisse, nicht in Österreich.
- Referenzzellen sind nicht nachweislich stabil, nur nicht im Inventar (Pseudo-Negative).
- Gezählte Vergleiche: 24 (6 primär, 18 sekundär); alle sind oben berichtet.
- Kette und Regeln unverändert aus `config/wirkungskette_v01.json` (SHA-256 7769ac5183ac…); v02-Ereigniszeilen wurden nachgerechnet und stimmen mit `reports/wirkungskette_v02/gegenprobe.json` überein.
