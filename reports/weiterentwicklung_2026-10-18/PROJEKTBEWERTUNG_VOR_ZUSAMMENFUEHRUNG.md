# Talwacht – ehrliche Projektbewertung vor der Zusammenführung

Stand 18.10.2026. Geprüft wurden alle Branches und Sessions dieser Projektfamilie sowie `origin/main`. Es wurde nichts
gerechnet, trainiert oder verändert. Die Inventarzahlen in Abschnitt 5 wurden für diesen Bericht direkt aus
`data/raw/geosphere_natural_hazards.json` (Abruf 14.10.2026) gezählt. „Genau verortet“ heißt dort Lagequalität
„sehr genau (0–5 m)“ oder „genau (5–20 m)“; das sind Kategorien des Inventars, keine Vermessung.

## 1. Kurzfazit

- **Gut belegt und zeigbar:** Mit dem fairen Vergleich (gemeldeter Hang gegen ähnliche Nachbarhänge am selben Tag)
  trennt das Gelände deutlich über Zufall. Ein Zusatznutzen des Wetters ist in keiner Variante belegt (V0.4 bis V0.9).
  Das Projekt arbeitet sauber: vorab registriert, versiegelter Test, offene Grenzen.
- **Technisch fertig, aber nicht geprüft:** die Kette Prüfpunkt → Auslaufszenario → Infrastruktur (Wirkungskette).
  Sie läuft, ist aber im einzigen Demogebiet (Stanz) nicht bestätigt, und der Auslauf ist ungeprüft.
- **Nicht machbar mit den heutigen Daten:** eine Wahrscheinlichkeit, dass an einem bestimmten Hang eine Mure abgeht.
- **Deine Demo-Idee ist machbar und sinnvoll**, wenn wir sie an einem Ort mit vielen dokumentierten Hangmuren
  machen, den kein Modell gesehen hat, und die Prüfstufen dort vorab festgelegt prüfen. Der beste Kandidat ist das
  Unwetter Vorarlberg/Tirol vom August 2005 (Abschnitt 5).

## 2. Was funktioniert und was man guten Gewissens zeigen kann

| Baustein | Stand | Zeigen? | So formulieren |
|---|---|---|---|
| Datenbasis 423 Ereignisse, 5 gematchte Kontrollhänge | fertig, verifiziert | **ja** | „dokumentierte Ereignisse, je mit fünf ähnlichen Hängen ohne Meldung“ |
| V0.4 versiegelter Test: Gelände + Wetter 0,751 [0,633; 0,866], Gelände 0,702, Wetter 0,604, 11 Einheiten | fertig, einmal ausgewertet | **ja**, mit Intervall | „Der gemeldete Hang landet deutlich öfter vorn als bei Zufall“ |
| Wetter ohne Zusatznutzen: V0.4, V0.5/V0.6, V0.9 auf ungesehenen Episoden (Gelände 0,770) | fertig (V0.6–V0.9 nur auf `origin/main`) | **ja**, als Befund | „Das Gelände zählt, ein Zusatz durch Wetter ist nicht belegt“ |
| Extremwetter am selben Ort (Case-Crossover): 24,6 % der Episoden mit extrem nassen 3 Tagen statt 5 % | fertig, explorativ | **ja**, als explorativ | „Zusammenhang, keine Ursache; Haupttest knapp nicht erfüllt“ |
| V0.8 Case-Crossover: Ereigniszeiten sind nasser als gewöhnliche Zeiten (0,818) | fertig, explorativ | ja, als „Wann“-Befund | keine Vorhersage |
| Meldebias-Kontrolle V0.7: Abstand zu Straßen/Gebäuden allein trennt 0,928 | fertig, explorativ | **ja**, als Grenze | „Ein Teil des Signals ist Sichtbarkeit“ |
| Prüfpunkte (Rangfolge von Hangzellen mit dem V0.4-Geländemodell) | technisch fertig | **nur als Demonstration** | „Prüfstufe, relativ im gewählten Umkreis“. In Stanz: oberste 5 % der Fläche enthalten nur 3,4 % der Ereignisse, also keine Bündelung |
| Auslaufszenario (D8 hangabwärts, Reichweiten aus der Literatur 45/467 m, 11°/7°) | technisch fertig | **nur als Szenario** | „möglicher Weg hangabwärts, ungeprüft“ |
| Infrastruktur im Szenario (OSM: Gebäude, Straßen, Bahn) | technisch fertig | **ja, als Szenario** | „liegt im Auslaufszenario“, nicht „wird getroffen“ |
| Hangkarte 3D (V0.5-Modell, relative Anteile) | fertig, nicht gemergt | eher nein | baut auf V0.5, dessen hohe Trennung teils Meldebias ist |
| Satelliten-Pipeline B (vorher/nachher) | fertig bis Stufe 5 | ja, als Forschung | „unterscheidet Ereignis von Kontrolle (0,79–0,80), Ortung im offenen Ausschnitt nur mäßig besser als Zufall, keiner der 30 geprüften Kandidaten bestätigt“ |
| Hangmuren-Pilot (Gelände nur für reine Hangmuren) | lokal, nicht committet | **ja, als Grenze** | 0,539 [0,406; 0,669]: Gelände trennt reine Hangmuren kaum |
| Neuronale Murensuche | nur Gerüst | **nein** | Plan, kein Ergebnis |
| Internationale Anfälligkeit (Nepal, Japan, Italien) | v01 Hürde nicht bestanden, v02 blockiert | als Forschungsbefund | „überträgt zwischen Regionen nicht besser als die Neigung allein“ |

## 3. Was nicht geht und warum

**Eine Wahrscheinlichkeit, dass an einem Hang eine Mure abgeht, kann das Projekt nicht liefern.**

1. Das Design vergleicht gemeldete Hänge mit ausgewählten Nachbarn. Daraus entsteht eine Rangfolge, keine Häufigkeit.
   Für eine Wahrscheinlichkeit bräuchte man ein Gebiet, in dem alle Ereignisse vollständig kartiert sind, und eine
   Kalibrierung.
2. Das Inventar enthält nur Punkte. Ob ein Punkt Anriss, Weg oder Ablagerung markiert, ist unbekannt
   (`reports/hazard_v01/FEASIBILITY.md` auf dem Branch der Gefährdungsanalyse).
3. Für die zeitliche Komponente (wann) fehlt ein belegter Wetternutzen bei 1 km Auflösung.
4. Ein Auslauf lässt sich nicht prüfen, weil es keine Auslauf- oder Ablagerungsflächen gibt.

Auch eine Warnung, eine Gefahrenkarte oder eine Schadensvorhersage ist nicht belegt. Das gehört so auf die Website.

## 4. Was die Daten aus anderen Ländern leisten

Die Anfälligkeitsarbeit nutzt Polygoninventare aus Nepal (Gorkha 2015, Erdbeben; Far-Western Nepal, Monsun),
Japan (Iburi 2018) und Italien (Emilia-Romagna 2023, Regen). Sie haben echte Rutschungsflächen, also genau das,
was in Österreich fehlt. Aber:

- Ein gemeinsames Geländemodell überträgt zwischen den Regionen **nicht besser als die Neigung allein**
  (+0,006 [−0,005; +0,017], susceptibility_v01). Erdbeben- und Regenrutschungen sitzen an verschiedenen Stellen
  im Gelände.
- Die Fortsetzung (v02, getrennt nach Auslöser) wartet auf die Kartierumrisse für Iburi und Emilia-Romagna; ohne
  sie lässt sich kein ehrlicher Hintergrund ziehen.
- Für eine Demo in Österreich bringen diese Daten deshalb derzeit **kein** geprüftes Modell. Sie sind ein
  wertvoller Forschungsbefund („Anfälligkeit ist regional und auslöserabhängig“), kein Werkzeug für die Demo.

## 5. Deine Demo-Idee, geprüft

> Ort mit vielen Muren → dort Punkte suchen, an denen eher eine Mure abgehen könnte → grob prüfen, ob bergab
> Straße oder Häuser liegen.

### 5.1 Ein Ort mit vielen Muren: ja, und besser als Stanz

Das volle GeoSphere-Inventar enthält **3.416 reine Hangmuren**, davon **2.686 genau verortet**; im Modellbestand
sind es nur 102. Die größten Häufungen genau verorteter reiner Hangmuren nach Ereignisdokumentation:

| Ereignis (Projekt im Inventar) | Hangmuren genau verortet | Jahr | Schwerpunkte | vom Modell gesehen? |
|---|---:|---|---|---|
| Vorarlberg/Tirol August 2005 | **1.176** | 2005 | Mittelberg, Laterns | **nein** |
| Oberkärnten Okt./Nov. 2018 | 112 | 2018 | Lesachtal, Kötschach-Mauthen | teilweise möglich (prüfen) |
| Nordhälfte Österreich Juni 2013 | 105 | 2013 | Gerlos, Wildschönau | nein |
| Österreich September 2024 | 97 | 2024 | Hofstetten-Grünau, Frankenfels | teilweise möglich (prüfen) |
| Thiersee 1970 | 97 | 1970 | Thiersee | nein (zu alt für Landbedeckung) |
| Sellrain Juni 2015 | 92 | 2015 | Sellrain | nein |
| Gasen/Haslau August 2005 | 76 | 2005 | Birkfeld, Gasen | nein |
| Klingfurth Juni 2009 | 73 | 2009 | Bromberg, Walpersbach | nein |
| Stanz im Mürztal Juli 2016 | 55 | 2016 | Stanz | ja (versiegelter Test, gesehen) |

Das V0.4-Modell kennt nur Ereignisse ab 2016. Vorarlberg/Tirol 2005, Sellrain 2015, Gasen 2005 und Klingfurth 2009
sind für das Modell **ungesehen**. Dort kann man die Prüfstufen ehrlich testen, statt sie nur zu zeigen.

### 5.2 Punkte mit höherer Prüfstufe suchen: machbar, aber nur mit Test vorher

Die Wirkungskette kann für jeden Ort Prüfstufen rechnen (Code fertig). Ob sie dort etwas taugen, ist offen:
In Stanz bündeln sie die Ereignisse nicht. Damit die Demo ehrlich bleibt:

- **Vorab festlegen, bevor gerechnet wird:** welche Gebiete (Regel, z. B. alle Ereignisdokumentationen vor 2016 mit
  mindestens 50 genau verorteten Hangmuren), welche Kennzahl (Anteil der dokumentierten Hangmuren in den obersten
  5 % und 20 % der Fläche gegen den Flächenanteil), welcher Vergleich (Neigung allein als Basislinie), welche
  Unsicherheit (Wiederziehen ganzer Gebiete).
- **Alle Gebiete berichten**, nicht nur das beste. Das Demogebiet wird nach einer festen Regel gewählt (z. B. das mit
  den meisten Hangmuren), nicht nach dem Ergebnis.
- Wenn die Prüfstufen auch dort nicht besser sind als die Neigung allein, zeigt die Demo genau das. Das ist ein
  gültiges Ergebnis.

Offene technische Fragen dafür:
- **Gelände-Datum:** Die Projektregel verlangt, dass die Geländedatei vor dem Ereignis entstanden ist. Die
  30-m-Skadi-Kacheln tragen ein Datum von 2016, beruhen aber auf älteren Aufnahmen (u. a. SRTM 2000). Für 2005 muss
  entschieden und dokumentiert werden, ob die Herkunft der Höhendaten statt des Dateidatums zählt.
- **Landbedeckung:** Für 2005 braucht es CORINE 2000 (Download, Klassen auf das Modell abbilden).
- **Meldebias:** Ereignisdokumentationen wie 2005 sind Geländeerhebungen in einem abgegrenzten Gebiet. Das
  verringert, aber beseitigt nicht die Häufung entlang von Straßen.

### 5.3 Grob prüfen, ob bergab Straße oder Häuser liegen: machbar und ehrlich

Genau das macht die Wirkungskette schon: hangabwärts nach dem steilsten Gefälle, Reichweite als Band aus der
Literatur, dann OpenStreetMap-Gebäude und -Straßen im Korridor. Formulierung: „Wenn hier eine Mure abgeht, liegen im
möglichen Weg hangabwärts diese Straßen und Gebäude.“ Kein Training nötig.

Eine echte Gegenprobe ist nur eingeschränkt möglich: Das Inventar hat Schadensfelder (Verkehrsanlagen, Bauwerke),
aber bei den genau verorteten reinen Hangmuren sind sie fast immer leer (Verkehrsanlagen bekannt bei 42 von 2.686,
davon 36 mit Schaden). Das reicht für einen beschreibenden Abgleich, nicht für einen Test. Die laufende Session
„Qualitative Auslauf-Gegenprobe an Schadensmeldungen“ arbeitet daran.

Grenzen: OpenStreetMap ist der heutige Stand; Schutzbauten, Volumen, Wassergehalt und Material fehlen. Personen- oder
Einwohnerzahlen sind nicht eingebunden (möglich wäre das Bevölkerungsraster der Statistik Austria, Lizenz prüfen).

## 6. Empfohlene Reihenfolge

1. **Vorab registrieren** (neue Version, z. B. `wirkungskette_v02`): Gebietsregel, Kennzahl, Basislinie Neigung,
   Unsicherheit, Datumsregel für Gelände und Landbedeckung. Noch keine Rechnung.
2. **Pilot 1 → alle Gebiete:** Prüfstufen in den registrierten Gebieten rechnen, alle berichten.
3. **Demogebiet nach der Regel** (voraussichtlich Vorarlberg/Tirol 2005, Kleinwalsertal oder Laternsertal) mit
   Prüfstufen, Auslaufszenario und Infrastruktur bauen.
4. **Dann zusammenführen:** `origin/main` (V0.6–V0.9, Pipeline B, CI), lokaler `main`, aktueller Stand,
   Wirkungskette, Extremwetter, Website; volle Prüfung in der Hauptkopie.
5. **Dann die Website** nach dem Meisterprompt, mit dem neuen Demogebiet und dem Testergebnis.

## 7. Entscheidungen, die der Nutzer treffen muss

- Demo-Test wie in 6.1–6.3 vorab registrieren und an ungesehenen Gebieten prüfen (empfohlen), oder die Kette nur als
  Demonstration ohne Test zeigen.
- Datumsregel für Gelände vor 2016 (Herkunft der Höhendaten statt Dateidatum) und Download CORINE 2000.
- Ob der Hangmuren-Pilot (`reports/mudslide_cascade_v01/`) committet wird; die Website nutzt ihn.
- Ob die Hangkarte (V0.5) in die Zusammenführung kommt.
