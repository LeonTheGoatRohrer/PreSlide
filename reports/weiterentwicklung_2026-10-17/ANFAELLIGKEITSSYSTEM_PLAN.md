# Plan: Anfälligkeits- und Ereignissystem für Hangrutschungen

**Stand: 17. Oktober 2026. Reiner Plan, noch nichts umgesetzt, keine Daten bezogen.** Arbeitstitel im Entwurf: „Landslide Risk Intelligence System“. Der Entwurf wurde gegen die Datenrecherche (`RUTSCHUNGSDATENSAETZE_WELTWEIT.md`), die Ergebnisse aus `PROJEKTUEBERBLICK.md` und die Regeln aus `AGENTS.md` geprüft und an den Stellen geändert, die unten in Abschnitt 0 aufgelistet sind. Die Grundidee bleibt unverändert.

**Einordnung im Repository.** Das ist ein neuer Versionsstrang. Er bekommt einen eigenen Namensraum (`data/`, `models/`, `reports/` Unterordner, eigene `config/*.json`) und wird **vor jeder Modellierung** registriert (AGENTS.md Abschnitt 45). Die eingefrorenen Talwacht-Artefakte (V0.3-Baseline, V0.4-Vorregistrierung und versiegelter Test) werden nicht angefasst.

## 0. Änderungen gegenüber dem Entwurf

| Nr. | Änderung | Grund |
|---|---|---|
| 1 | **Pilotregion nicht mehr Taiwan, sondern Nepal (Modell A) und Emilia-Romagna (ereignisbezogene Tests).** Taiwan nur, wenn Daten beschafft werden. | Für Taiwan ist kein offener Direktdownload belegt. Belegt sind nur Marc et al. 2015 (HydroShare, CC BY-NC 4.0, 2,0 MB, Anzahl unbekannt) und Pixelmasken ohne Koordinaten in Landslide4Sense. Chi-Chi und Morakot nur ohne Download bzw. „auf Anfrage“ [Suchzusammenfassung]. Gorkha (CC0, Kartierumriss), Far-Western Nepal (CC BY 4.0, AOI) und RER2023 (CC BY 4.0) sind abgerufen und belegt. |
| 2 | **„Risk Score“ umbenannt in Anfälligkeitsindex (Modell A) und Ereignis-Hinweisindex (Modell B).** | „Risiko“ heißt in der Naturgefahrenkunde Gefahr mal Exposition und Schaden. Das System bewertet nur Anfälligkeit und Auslösebedingungen. |
| 3 | **Südtirol-Blindtest umgebaut:** Die Registry-Einstellung „negatives_allowed: false“ des Entwurfs widerspricht einem Test mit AUC. Der Test wird als Presence-Background-Test mit **vorab festgelegter** Teilmenge und Metrik definiert (Abschnitt 7). | IFFI ist kein vollständiges Kartierinventar: Aktualität, Datum und Vollständigkeit unterscheiden sich je Region, die Lizenz ist widersprüchlich. Ohne Negativdefinition ist AUC nicht definiert. |
| 4 | **Keine Trainingszahlen in Taiwan/Nepal ohne räumliche Hold-out-Gebiete.** Die Tabelle in Abschnitt 28 des Entwurfs („Taiwan hoch, Nepal hoch“) wäre sonst eine Trainingsmetrik. Die Karte zeigt nur Out-of-fold-Vorhersagen oder ist ausdrücklich als „im Training enthalten“ gekennzeichnet. | Räumliche Leckage (AGENTS.md Abschnitt 15). |
| 5 | **Modell B hat ein Machbarkeitsgate (Abschnitt 9).** Ein Inventar mit einem einzigen Ereignis enthält keine zeitliche Variation, Regen- und Bodenfeuchtefelder sind dort über das Gebiet nahezu konstant. | Dafür braucht es mehrere datierte Ereignisse mit Kontrollzeiten. Zudem fand Talwacht bisher keinen belegten Wetternutzen (Abschnitt 9). |
| 6 | **Quality-vs-Diversity-Experiment wird mit einem dritten Arm abgesichert** (D auf Größe von Q heruntergerechnet) und vorab registriert. | Sonst vermischt der Vergleich Labelqualität, Datenmenge, Auslöser und Region. |
| 7 | **Auslöser getrennt führen** (Erdbeben, Regen, Taifun/Hurrikan, unbekannt) und in der Auswertung stratifizieren. Für Erdbebeninventare Bodenerschütterung (PGA) als Merkmal oder getrennte Modelle. | Die Lage koseismischer Rutschungen wird stark von der Erschütterung bestimmt; Wenchuan, Gorkha, Kaikōura und Iburi sind Erdbebeninventare. |
| 8 | **Leckageregeln für Merkmale ergänzt:** DEM-Aufnahmedatum, Vegetations- und Landbedeckungsstand vor dem Ereignis, keine Nachereignis-Bildinformation. | AGENTS.md Abschnitt 13; eine Narbe im DEM oder ein NDVI-Einbruch nach dem Ereignis würde das Label verraten. |
| 9 | **Nutzereinträge („Neue Rutschung hier“) fließen nie ins Training oder in die Bewertung** und sind als nicht verifiziert markiert. | Rückkopplung, Meldebias, Missbrauch. |
| 10 | **Laufweg-Korridor wird gegen kartierte Auslaufflächen geprüft** (Gorkha, São Sebastião) oder als reine Illustration gekennzeichnet. | Eine nie validierte Simulation darf nicht als Schätzung auftreten. |
| 11 | **Baselines, Abbruchkriterien (Gates) und Phasenreihenfolge nach AGENTS.md ergänzt.** Oberfläche erst nach belegter räumlicher Generalisierung. | Eine hohe Zahl ohne Baseline sagt nichts; AGENTS.md Abschnitte 29 und 38. |
| 12 | **Brier Score und „Wahrscheinlichkeit“ gestrichen,** solange Negative gesampelt sind. PR-AUC wird nur bei festem, angegebenem Verhältnis berichtet. | Das Verhältnis Positive zu Negative ist eine Wahl der Stichprobe, nicht die Häufigkeit in der Landschaft. |
| 13 | **Oberfläche auf Deutsch, Hinweis „Forschungsprototyp, kein Warnsystem“ im Interface.** | AGENTS.md Abschnitt 30; Projektüberblick. |
| 14 | **Sentinel-2-Merkmale erst nach dem Gelände-Baseline** und nur als Vorereignis-Komposit. | Rechenaufwand auf dem Laptop; die Schwerpunkt-Frage ist, ob sie überhaupt etwas beitragen. |

## 1. Kernidee

Zwei verschiedene Fragen:

**Modell A: Grundanfälligkeit eines Hanges.** Wie anfällig ist dieser Hang grundsätzlich für eine Rutschung? Verwendet werden weitgehend statische Eigenschaften (Abschnitt 6). Ausgabe: **Anfälligkeitsindex 0–100**, relativ innerhalb des betrachteten Gebiets.

**Modell B: ereignisbezogene Bedingungen.** Unter den momentanen Bedingungen: Welche umliegenden Hänge könnten ebenfalls instabil sein? Zusätzlich zu Modell A kommen Niederschlag (aktuell und vorher), Bodenfeuchte, Vegetationsänderung vor dem Ereignis, ggf. Schnee und Temperatur sowie bei Erdbeben die Erschütterung. Ausgabe: **Ereignis-Hinweisindex 0–100**. Beispiel: „Grundanfälligkeit 58/100, aktuelle Bedingungen 81/100“.

**Wie eine gemeldete Rutschung zu lesen ist.** Eine registrierte Rutschung erhöht die Wahrscheinlichkeit nebenan nicht „von selbst“. Sie ist ein **Hinweis auf einen gemeinsamen Auslöser** (Starkregen, hohe Bodenfeuchte, Erdbeben). Genau deshalb werden die Nachbarhänge unter den aktuellen Bedingungen neu bewertet. Das System soll das so erklären und nicht anders.

**Grenzen von Modell B.** Niederschlags- und Bodenfeuchtedaten haben Auflösungen von rund 1 bis 10 km. Innerhalb eines Gebiets unterscheiden sie daher kaum zwischen Hängen. Der Unterschied zwischen Hängen kommt praktisch aus Modell A. Modell B kann nur Unterschiede zwischen Zeiten und Ereignissen erfassen. Das ist die ehrliche Beschreibung dessen, was der „Neue-Rutschung“-Fall leisten kann.

**Kein Warnsystem.** Das Ergebnis ist ein Forschungsprototyp. Es ist keine Gefahrenkarte und keine Handlungsempfehlung (vgl. `PROJEKTUEBERBLICK.md`).

## 2. Score ist keine Wahrscheinlichkeit

Die Oberfläche behauptet nicht „82 % Wahrscheinlichkeit“. Sie zeigt „Anfälligkeitsindex 82/100, sehr hoch im Vergleich zum Gebiet“.

Das Training mit Positiven und gesampelten Negativen kann nur eine **relative Rangordnung** liefern. Das Verhältnis der Klassen wird vom Sampling bestimmt (Abschnitt 5). Eine Wahrscheinlichkeit ist erst nach einer Kalibrierung gegen unabhängige, vollständig kartierte Ereignisse möglich (zum Beispiel Auftrittshäufigkeit pro Fläche und Jahr in einem vollständig kartierten Gebiet). Bis dahin: Rangwerte, Perzentile, Klassen.

## 3. Pilotregion und Datenlage

Die Pilotregion wird nach **belegter Datenlage** gewählt, nicht nach Bauchgefühl. Stand der Recherche (Details und Quellen in `RUTSCHUNGSDATENSAETZE_WELTWEIT.md`):

| Zweck | Datensatz | Belegte Eigenschaften |
|---|---|---|
| Modell A, Pilot | **Gorkha 2015** (USGS, Roback) | 24.915 Polygone (Gesamt) und 24.795 Anrissflächen, CC0, Kartierumriss und verdeckte Bereiche als eigene Layer |
| Modell A, Gebirgsvariante mit Monsun | **Far-Western Nepal** (Zenodo 4290099) | 26.350 Polygone und 25.639 Punkte, 24,1 MB, CC BY 4.0, AOI-Polygon; Datum nur für 8.778 Punkte, jährlich und teils automatisch |
| Regen-Pilot für ereignisbezogene Tests | **Emilia-Romagna RER2023** | 80.997 Polygone, 43,6 MB, CC BY 4.0, über 6.000 km² flächig kartiert; ein Ereignis, Anrissflächen nicht getrennt |
| Optional, ohne Beschaffung nicht möglich | **Taiwan** | Kein offener Direktdownload belegt (siehe Abschnitt 0, Nr. 1). Erst nach Beschaffung über Autoren oder die Behörde (CGS) in den Plan aufnehmen. |
| Optional | Iburi/Hokkaido 2018 | CC BY 4.0, 3,0 MB, Anzahl nicht auf der Datenseite, Wetterstationen beigelegt |
| Vorbehalt | Washington, Oregon (SLIDO), Hongkong, Wenchuan | Washington: Zugang, Zahl und Lizenz nicht geprüft. SLIDO: Lizenz nicht genannt. Hongkong: Nutzungsbedingungen nicht abgerufen. Wenchuan (Fan 2019): CC BY 4.0, aber nur 471 km². |
| Versiegelt, nur Blindtest | **IFFI Südtirol** | Offener Provinzzugang, CC BY-SA 3.0, 1:10.000; WFS-Zugang widersprüchlich belegt (Abschnitt 7) |

Die Webanwendung zeigt zunächst **eine** ausgewählte Region mit belegten Daten. Die ganze Welt wird nicht implementiert.

Pipeline:

```text
belegte Datensätze (Nepal, RER2023)
→ gemeinsames Format, Registry
→ Gelände und Vorereignis-Merkmale
→ Positive/Negative (nur in kartierten Flächen)
→ ML mit räumlicher Aufteilung
→ Anfälligkeitsraster
→ API
→ interaktive Karte
```

## 4. Einheitliches Datenformat und Registry

Alle Inventare werden in eine gemeinsame Struktur überführt:

```text
landslide_id, dataset, country, event_id
geometry, source_geometry, runout_geometry
landslide_type, process_class
date, date_resolution, trigger_class
area_m2
mapping_method, mapping_quality, mapping_complete
mapping_extent_id            # Verweis auf Kartierumriss
obscured_extent_id           # nicht kartierte Bereiche
license, license_note
crs_original
```

Besonders wichtig ist `source_geometry` (Anrissfläche), wenn vorhanden. Gelernt werden soll, **wo eine Rutschung beginnt**, nicht, wo das Material landet. Wo keine Anrissfläche vorliegt (zum Beispiel RER2023, Fan 2019 ohne getrennte Anrisse), wird das ausdrücklich festgehalten (`source_area_available: false`) und eine dokumentierte Ersatzregel verwendet (zum Beispiel oberstes Drittel des Polygons nach Höhe). Diese Ersatzregel wird einmal festgelegt, nicht je Datensatz nach Ergebnis gewählt.

`date_resolution` unterscheidet Tag, Ereignis, Jahr und unbekannt. Die zeitliche Vorgeschichte (Modell B) ist nur für Tag- und Ereignisauflösung zulässig.

Registry (Beispiel):

```yaml
gorkha_2015:
  geometry: polygon
  source_area_available: true
  mapping_complete: true        # innerhalb des Kartierumrisses
  quality: gold
  negatives_allowed: true
  trigger_class: earthquake
  date_resolution: event
  license: CC0-1.0

rer2023:
  geometry: polygon
  source_area_available: false
  mapping_complete: true
  quality: gold
  negatives_allowed: true
  trigger_class: rain
  date_resolution: event

iffi_suedtirol:
  quality: silver
  negatives_allowed: false      # keine Negativen aus IFFI-Lücken
  role: sealed_blind_test       # Presence-Background, Teilmenge vorab festgelegt
  license: CC-BY-SA-3.0
```

`role` ist `train`, `validation` oder `sealed_blind_test`. Ein neuer Datensatz wird hinzugefügt, ohne dass der Rest umgebaut wird. Die Registry gehört in die Konfiguration, ihre Prüfsumme in die Laufidentität.

## 5. Positive und negative Stichproben

**Positiv:** Anrissfläche (oder dokumentierte Ersatzregel) einer bekannten Rutschung.

**Negativ:** nur innerhalb eines Kartierumrisses, der systematisch auf Rutschungen untersucht wurde:

- ohne verdeckte Bereiche (Wolken, Schatten);
- mit Pufferabstand zu jeder bekannten Rutschung. Die Pufferbreite wird aus der Verteilung der Rutschungsgrößen und der Positionsgenauigkeit abgeleitet und in der Konfiguration festgelegt, nicht gewählt, um Ergebnisse zu verbessern;
- flächengewichtete Zufallsstichprobe über den Umriss (nicht nach Geländeähnlichkeit gematcht; Modell A fragt nach Anfälligkeit im ganzen Gebiet, nicht nach Nachbarhang-Unterschieden);
- Mindestabstand zwischen Negativen, kein Überlapp.

```text
bekannte Rutschung   █████
Puffer               ▒▒▒▒▒▒▒▒▒
Negativ                       ●   (erlaubt)
Negativ  █████●               (nicht erlaubt)
```

**Meldedaten werden nie als Negativquelle verwendet.** Fehlt ein Eintrag, folgt daraus nichts.

Das Klassenverhältnis ist festgelegt, angegeben und gleich für alle Vergleichsarme. PR-AUC wird nur mit diesem Verhältnis berichtet. Das ist ein Sampling-Parameter, keine Häufigkeit in der Landschaft.

## 6. Merkmale

Nicht 200 Merkmale, nur sinnvolle. Alle Merkmale tragen Aufnahme- oder Gültigkeitsdatum.

**Gelände (aus DEM):** Höhe, Neigung, Exposition (zirkulär, Sinus/Kosinus), Profil- und Plankrümmung, Rauigkeit, lokale Reliefenergie, Fließakkumulation, TWI, Abstand zur Entwässerung, Einzugsgebietsgröße.

**Oberfläche (Sentinel-2), zweite Stufe:** NDVI, Vegetationsbedeckung, eventuell NDMI und Bare-Soil-Index. Nicht jedes Band einzeln. Nur Vorereignis-Komposite.

**Boden und Geologie, wenn verfügbar:** Bodenklasse, Ton- und Sandanteil, Bodentiefe, Lithologie, geologische Einheit. Globale Bodendaten haben meist ~250 m Auflösung. Das ist gröber als die 10–30 m Zellen und wird so ausgewiesen.

**Auslöser (Modell B):** Niederschlag 24 h, 72 h, 7 d, Niederschlagsanomalie (Perzentil gegen Klimatologie), Bodenfeuchte, Vorfeuchte; bei Erdbebeninventaren PGA aus einer veröffentlichten Erschütterungskarte.

### Leckageregeln (Pflicht)

1. **DEM-Datum.** Ein nach dem Ereignis aufgenommenes DEM enthält die Anrissnarbe. Bevorzugt wird ein DEM, das vor allen Ereignissen aufgenommen wurde (zum Beispiel SRTM, Aufnahme 2000, mit Lücken und Kronenverzerrung), und sonst das Aufnahmedatum je Datensatz in der Registry. Das Copernicus-DEM wurde nach meinem Kenntnisstand 2011–2015 aufgenommen; das gilt vor Verwendung zu verifizieren und führt zum Ausschluss von Inventaren mit früheren Ereignissen, oder zu einer ausdrücklichen Einschränkung.
2. **Vegetation und Landbedeckung** nur aus Aufnahmen **vor** dem Ereignis (Fenster bis exklusiv t0). Ein Vegetationsverlust durch die Rutschung selbst darf kein Merkmal sein.
3. **Keine Oberflächenänderung nach t0.** Änderungsmerkmale sind nur als Vorereignis-Trend zulässig.
4. **Fenster `[t0 − Historie, t0)`** für alle zeitlichen Merkmale, mit Test (AGENTS.md Abschnitt 13).
5. **Merkmalsauswahl und Ablationen** laufen nur auf Trainings- und Validierungsfalten. Test- und Blindtest-Daten sind dafür gesperrt.

### Merkmalsauswahl

Permutations- und Baum-Wichtigkeit, SHAP, Ablationstests. Ein Merkmal ohne messbaren Beitrag fällt weg. Das macht das Modell kleiner, schneller und besser nachvollziehbar. Formulierung: „das Modell stützt sich stark auf X“, nicht „X verursacht Rutschungen“. Ob ein Prädiktor Meldeartefakt ist (Straßen, Siedlungen, Wald), wird vor der Interpretation geprüft (AGENTS.md Abschnitt 48).

## 7. Räumliche Aufteilung und Südtirol-Blindtest

**Keine zufälligen Pixel-Splits.** Aufteilung nach Kartierflächen, Einzugsgebieten oder Kacheln mit Puffer zwischen Trainings- und Testblöcken:

```text
Region A → Training
Region B → Training
Region C → Validierung
Region D → Test
```

Jede Region wird in ganze Einzugsgebiete/Blöcke zerlegt. Berichtet werden der Wert, die Zahl der unabhängigen Blöcke und ein Intervall aus einer blockweisen Bootstrap-Schätzung (AGENTS.md Abschnitt 48).

### Südtirol bleibt unangetastet

```text
TRAINING            NEIN
MERKMALSAUSWAHL     NEIN
TUNING              NEIN
SCHWELLENWAHL       NEIN
```

Erst wenn das Modell fertig und eingefroren ist, wird es **einmal** auf Südtirol angewendet. Die Aussage ist dann: „Das Modell wurde ohne alpine Daten trainiert und ohne Nachtraining auf ein alpines Gebiet angewendet.“

Bevor irgendein Modell läuft, wird festgelegt (Vorregistrierung):

- welche **Teilmenge von IFFI Südtirol** zählt (zum Beispiel nur Polygone aus Photointerpretation/Kartierung ab einem Stand, keine Stürze, keine Linien ohne Fläche);
- wie Hintergrundpunkte gezogen werden (flächengleichmäßig über das Gebiet, mit Puffer um bekannte Objekte) und das Klassenverhältnis;
- die Hauptmetrik (ROC-AUC und PR-AUC bei festem Verhältnis, dazu ein Presence-Background-Maß wie der Boyce-Index) und die Vergleichsbaseline (Neigung allein, Höhe allein, und der europaweite ELSUS-v2-Anfälligkeitsraster als externe Referenz, sofern zugänglich);
- die Schwelle für „Datum bekannt“, falls eine zeitliche Auswertung versucht wird.

Zwei Einschränkungen gelten ausdrücklich: Südtirol ist **eine** Region (wenige unabhängige Blöcke), und IFFI ist unvollständig. Der Test misst, wie gut dokumentierte Rutschungen gegen Hintergrund getrennt werden, nicht die Vollständigkeit. Nach der Bewertung gelten die Südtiroler Daten als gesehen; jede weitere Analyse darauf ist explorativ und so beschriftet.

Hinweis zur Lizenz: IFFI Südtirol steht unter CC BY-SA 3.0. Der Zugangsweg (WFS-Vektor oder nur WMS) ist in den Quellen widersprüchlich und vor der Registrierung zu testen.

## 8. Modelle und Experimente

**Erster starker Benchmark:** LightGBM oder XGBoost (tabellarische Geodaten, schnell, SHAP). Dazu logistische Regression, Random Forest und ein kleines neuronales Netz, damit sich zeigen lässt, ob komplexer überhaupt besser ist.

**Baselines (Pflicht):** Zufall; Neigung allein; Höhe allein; Neigung + Höhe + Krümmung als einfaches logistisches Modell; ELSUS v2 für Europa.

### Experimentarme

| Arm | Trainingsdaten |
|---|---|
| **MODEL_Q** | nur hochwertige, vollständig kartierte Inventare (Nepal, RER2023, eventuell Iburi) |
| **MODEL_D** | zusätzlich weitere Inventare mit schwächerer oder unvollständiger Qualität |
| **MODEL_D_gematcht** | wie MODEL_D, aber auf die **Größe von MODEL_Q** heruntergerechnet (gleiche Positivzahl, gleiche Verteilung der Auslöser) |

Die Frage lautet: Hilft Datenmenge, oder schadet Label-Rauschen mehr, als es nützt? Ohne den dritten Arm wäre „mehr Daten“ mit „mehr Diversität“ vermengt. Alle Arme laufen auf **denselben** räumlichen Falten. Der Unterschied zwischen zwei Armen wird als **gepaarte** Größe mit eigenem Intervall berichtet. „Besser“ wird nur behauptet, wenn das Intervall die Null ausschließt, sonst gilt „kein Vorteil belegt“ (AGENTS.md Abschnitt 48). Alle betrachteten Vergleiche werden gezählt.

Meldedaten werden in keinem Arm als Negativquelle verwendet.

## 9. Modell B: Voraussetzungen und Test

**Machbarkeitsgate vor jedem Aufwand.** Modell B braucht Daten, in denen sich der Auslöser zeitlich unterscheidet:

- mehrere **datierte Ereignisse** (nicht nur ein Sturm je Region), jeweils mit Positiven und Kontrollzeiten oder Kontrollorten;
- Wetter- und Bodenfeuchtedaten für alle Ereignisse und Zeitfenster;
- eine ausreichende Zahl unabhängiger Ereignisse. Die Mindestzahl wird vor der Modellierung festgelegt.

Ein Inventar mit einem einzigen Ereignis (RER2023, Gorkha, Zixing) liefert **keinen** zeitlichen Kontrast und ist für das Training von Modell B ungeeignet. Es taugt höchstens für den Nachbarschaftstest unten.

**Warum Vorsicht angebracht ist.** In Talwacht (V0.4, versiegelter Test) war der Wetterzusatz nicht belegt: kombiniert gegenüber Gelände allein +0,049 [−0,003; +0,108], das Intervall enthält die Null. In V0.5 war der Zusatz ebenfalls nicht belegt. Modell B ist daher eine **offene Hypothese**, kein sicherer Bestandteil. Fällt das Gate durch, bleibt das System bei Modell A plus erklärtem Nachbarschaftsvergleich.

**Test für die „Neue Rutschung“-Funktion.** Mit einem Ereignisinventar lässt sich retrospektiv prüfen:

> Gegeben eine einzelne bekannte Rutschung eines Ereignisses: Liegen die übrigen kartierten Rutschungen desselben Ereignisses in der Umgebung im Mittel höher in der Rangliste als die Hintergrundhänge, und besser als Modell A allein?

- Bewertung als Leave-one-event-out oder Leave-one-region-out, mit blockweisen Intervallen.
- Wegen der räumlichen Nachbarschaft der Rutschungen innerhalb eines Ereignisses (Cluster) zählt als Stichprobe die Zahl der **Ereignisse bzw. Blöcke**, nicht die Zahl der Rutschungen.
- Erst wenn dieser Test einen Vorteil gegenüber Modell A allein belegt, wird die Funktion in der Oberfläche als Modell-B-Ergebnis dargestellt. Vorher zeigt sie nur eine erklärte Auswahl ähnlicher Hänge (Abschnitt 11).

## 10. Benutzerworkflow: „Neue Rutschung registrieren“

Der Benutzer klickt auf die Karte, „Neue Rutschung hier“. Gespeichert werden Position, Zeit und Ereignisart. Danach „Umgebung analysieren“.

Das System untersucht zum Beispiel einen Radius von 5 km oder besser die **hydrologisch und topographisch verbundene Umgebung**, lädt die aktuellen Daten (Niederschlag, Bodenfeuchte, Gelände, Satellitenindikatoren) und bewertet die umliegenden Hänge neu. Es fragt:

> Was ist an diesem Hang gerade ungewöhnlich? (zum Beispiel 7-Tage-Niederschlag im 97. Perzentil, Bodenfeuchte im 94. Perzentil)

und sucht dann Hänge mit ähnlicher Kombination.

Regeln:

- Nutzereinträge sind **nicht verifiziert** und werden so gekennzeichnet.
- Sie gelangen **nie** in Training, Merkmalsauswahl oder Bewertung.
- Es werden keine personenbezogenen Daten gespeichert. Einträge bleiben lokal.
- Die Oberfläche spricht von „Hinweis“, nicht von „Vorhersage“.

## 11. Ähnliche-Hänge-Suche (eigenes Modul)

Wird eine Rutschung gemeldet, wird ihr Merkmalsvektor (Neigung, Exposition, Bodenfeuchte, Lithologie, TWI, Vegetation, …) mit den umliegenden Hängen verglichen. Ausgabe: „Hänge mit ähnlicher Kombination“. Das ist eine **Ähnlichkeit**, keine Vorhersage. Die Abstandsmetrik (zum Beispiel standardisierter Abstand mit zirkulärer Exposition) wird festgelegt und getestet; die Gewichtung ist keine freie Stellschraube.

## 12. Laufweg-Korridor (Runout)

Keine aufwendige Physik. Die Frage lautet nur: **Wo könnte Material ungefähr hinlaufen?**

Basis: DEM, Fließrichtung, Krümmung, Rinnen/Täler, mögliche Verzweigungen. Das Material folgt bevorzugt Gefälle und bestehenden Rinnen.

```text
QUELLE
  ●
   \
    ▼
     ╲
      ███
    Tal
```

### Algorithmus V1

1. DEM laden und Senken behandeln.
2. Fließrichtung mit einem Mehrfachfließverfahren (nicht nur D8) berechnen.
3. Abflusswege mit mehreren leicht abweichenden Pfaden ausgehend vom Anrissgebiet verfolgen.
4. Reichweitenbegrenzung durch einen empirischen Reichweitenwinkel (Fahrböschung), dessen Wert aus **kartierten** Ereignissen abgeleitet wird, nicht geraten.
5. Pfade zu einem Korridor mit Häufigkeitsstufen vereinigen.
6. Darstellung als **möglicher Auswirkungsbereich**, nicht als genaue Bahn.

### Unsicherheit

Drei Stufen statt einer Linie: Kern, möglicher Bereich, unsicherer Außenbereich.

### Validierung

Auslaufflächen sind in einigen Datensätzen kartiert (Gorkha: Quell- und Gesamtflächen getrennt; São Sebastião: Anrisspunkte und Flächenpolygone). Dort wird gemessen, welcher Anteil der kartierten Fläche im Korridor liegt und wie groß der Korridor im Verhältnis ist. Ohne diese Messung wird die Funktion in der Oberfläche als „Illustration, nicht validiert“ gekennzeichnet.

## 13. Karte, Oberfläche und API

**Karte als Mittelpunkt.** Ebenen:

```text
☑ Anfälligkeitsraster
☑ Dokumentierte Rutschungen
☐ Satellitenbild
☐ Gelände
☐ Laufweg-Korridor
```

Der Ebene „Dokumentierte Rutschungen“ gilt: Sie darf **kein gleichzeitiger Eingang** des Modells sein, wenn gezeigt werden soll, dass das Modell diese Stellen selbst erkennt. Gezeigt werden nur Vorhersagen, die ohne diese Rutschungen im Training entstanden sind (Out-of-fold), sonst steht „im Training enthalten“ in der Legende.

**Rasterausgabe.** Das Gebiet wird in 10–30-m-Zellen zerlegt. Pro Zelle: Merkmalsvektor → Modell → Index. Daraus eine Heatmap in Klassen. Auf der Laptop-CPU wird mit 30 m und kleinen Gebieten gearbeitet; keine landesweiten Raster im Speicher (AGENTS.md Abschnitt 24).

**Hangbasierte Darstellung (später).** Das Gebiet wird in Hangeinheiten segmentiert. Pro Hang: Median und Maximum des Index, Fläche, Haupttreiber (zum Beispiel „+ steile Neigung, + hohe Bodenfeuchte, + konkave Form, − dichte Vegetation“). Erst nach dem Pixelmodell.

**Workflows.** A: Klick auf einen Hang, Index und Haupttreiber. B: Rechteck aufziehen, Heatmap der Umgebung. C: „Neue Rutschung hier“ (Abschnitt 10).

**Oberfläche auf Deutsch.** Dauerhafter Hinweis „Forschungsprototyp, kein Warnsystem; Indexwerte sind relative Anfälligkeit, keine Wahrscheinlichkeit“.

**API (Entwurf):**

```text
GET  /api/susceptibility/point
GET  /api/susceptibility/area
GET  /api/slopes
GET  /api/historical-landslides
POST /api/events/landslide        # lokal, nicht verifiziert, nie im Training
POST /api/runout
GET  /api/explain
```

Beispielantwort:

```json
{
  "susceptibility_index": 84,
  "class": "sehr_hoch",
  "meaning": "relative Anfälligkeit im Gebiet",
  "drivers": ["steile Neigung", "hohe Bodenfeuchte", "hohe Fließakkumulation"],
  "in_training_data": false
}
```

Bei jeder Antwort steht die Information, ob die Zelle im Trainingsgebiet liegt.

## 14. Auswertung

Nicht Accuracy als Hauptmetrik (bei gesampelten Klassen aussagearm). Berichtet werden ROC-AUC, PR-AUC (bei festem, genanntem Verhältnis), Recall und Präzision bei einer vorab festgelegten Schwelle, F1, ausgewogene Genauigkeit, Konfusionsmatrix sowie ein Presence-Background-Maß. **Brier Score** erst nach einer gezeigten Kalibrierung.

Jede Hauptzahl steht zusammen mit:

- der Zahl **unabhängiger Einheiten** (Blöcke, Ereignisse), nicht der Zeilen;
- einem Intervall aus blockweisem Bootstrap;
- dem Vergleich gegen Zufall (Permutation oder Äquivalent) und gegen die Baselines;
- gepaarten Intervallen für Modellunterschiede.

Der wichtigste Punkt ist die **räumliche Generalisierung** (Training in Region A, Test in Region B). Dominiert ein Ereignis oder eine Region (zum Beispiel ein Sturm), wird das Ergebnis zusätzlich ohne dieses Cluster gezeigt.

### Benchmark-Tabelle (Ziel)

| Modell | Hold-out Nepal | Hold-out RER2023 | Südtirol (versiegelt) |
|---|---:|---:|---:|
| MODEL_Q | ? | ? | ? |
| MODEL_D | ? | ? | ? |
| MODEL_D_gematcht | ? | ? | ? |
| Baseline Neigung allein | ? | ? | ? |

Kein Eintrag ist ein Trainingsergebnis. Die Südtirol-Spalte wird genau einmal gefüllt. Ist ein Modell dort besser, heißt das nur: unter diesem Test, mit diesen Daten. Ein belegter Unterschied zwischen MODEL_Q und MODEL_D verlangt, dass das gepaarte Intervall die Null ausschließt.

## 15. Phasen mit Abbruchkriterien

| Phase | Inhalt | Gate (weiter nur, wenn …) |
|---|---|---|
| 0 | Vorregistrierung (Konfiguration, Registry, Südtirol-Teilmenge, Metriken, Baselines) | Konfiguration eingefroren, Prüfsumme gespeichert |
| 1 | Dataset-Framework, Gorkha und Far-Western Nepal, RER2023, IFFI getrennt | Lizenzen am Original festgehalten, Kartierumrisse verfügbar |
| 2 | Geländepipeline mit DEM-Datumsprüfung | Tests für CRS, Exposition (zirkulär) und Leckage bestehen |
| 3 | Positiv-/Negativsampling in Kartierumrissen | Pufferwirkung getestet, Mindestabstand eingehalten |
| 4 | Baselines, dann erstes Modell | Modell schlägt die Neigungs-Baseline in der räumlichen Validierung, sonst Ursachenanalyse statt Ausbau |
| 5 | Räumliche Auswertung mit Intervallen | Intervalle und unabhängige Einheiten berichtet |
| 6 | Quality-/Diversity-Experiment | Vorab registriert, drei Arme, gepaarte Auswertung |
| 7 | Modell-B-Gate (Abschnitt 9) | Genug datierte unabhängige Ereignisse, sonst Modell B streichen |
| 8 | Anfälligkeitsraster für die Pilotregion | Nur Out-of-fold oder klar gekennzeichnet |
| 9 | Backend-API | Datenkontrakte stabil |
| 10 | Karte in der bestehenden Oberfläche | Hinweise und Legende vollständig |
| 11 | Dokumentierte Rutschungen als Ebene | Out-of-fold-Kennzeichnung sichtbar |
| 12 | „Neue Rutschung“ und Ähnliche-Hänge-Suche | Nachbarschaftstest bestanden, sonst nur Ähnlichkeit |
| 13 | Laufweg-Korridor mit Validierung | Messung gegen kartierte Flächen oder Kennzeichnung als Illustration |
| 14 | Erklärbarkeit (SHAP, Haupttreiber) | Formulierungen ohne Kausalbehauptung |
| 15 | **Südtirol-Blindtest** | Modell und Konfiguration eingefroren; Ausführung genau einmal |

Die Reihenfolge folgt `AGENTS.md` Abschnitt 38: erst Daten, Modell und Auswertung, dann API und Karte.

## 16. Fertig ist die erste große Version, wenn …

Kein Notebook mit einem AUC-Wert genügt. Die Demo muss tatsächlich Folgendes können:

```text
Webseite öffnen
→ Pilotregion öffnen
→ Gebiet wählen
→ Anfälligkeitsraster erscheint (Out-of-fold oder gekennzeichnet)
→ Hang anklicken
→ Index und Haupttreiber
→ Dokumentierte Rutschungen optional einblendbar
→ Neue Rutschung markieren (lokal, unverifiziert)
→ Umgebung neu bewertet, ähnliche Hänge hervorgehoben
→ mögliche Quelle wählen
→ Laufweg-Korridor mit Unsicherheitsstufen
```

Zusätzlich verlangt die Definition: dokumentierte Datenherkunft (`DATA_SOURCES.md`), Tests gegen Leckage und Gruppentrennung, Baselines, ehrliche Grenzen (`LIMITATIONS.md`), reproduzierbarer Aufbau auf dem Laptop und ein eingefrorener Südtirol-Blindtest.

Stützt die Auswertung nur Teile (zum Beispiel Modell A, aber nicht Modell B), wird nur der gestützte Teil als Ergebnis dargestellt.

## 17. Kurzdarstellung für Außenstehende

> Das System lernt aus zehntausenden kartierten Hangrutschungen, welche Geländeeigenschaften instabile Hänge charakterisieren. Eine neue Rutschung wird als Hinweis auf gemeinsame Auslösebedingungen behandelt, nicht als Beweis für weitere Rutschungen. Das System bewertet die Umgebung unter den aktuellen Bedingungen neu und sucht ähnliche Hänge. Mit dem Geländemodell schätzt es grob, in welchen Bereich sich Material bewegen könnte. Es wurde ohne alpine Daten trainiert und anschließend einmal ohne Nachtraining auf ein alpines Gebiet angewendet.

Das ist ein Forschungsprototyp. Die Aussagekraft hängt davon ab, was Abschnitt 14 belegt, und nicht davon, wie überzeugend die Demo aussieht.

## 18. Offene Entscheidungen vor Phase 0

- Taiwan: Daten über Autoren oder CGS beschaffen oder streichen.
- DEM: SRTM (2000) gegenüber Copernicus-DEM (Aufnahmezeitraum prüfen) für die gewählten Inventare.
- Erschütterungskarte (PGA) für Erdbebeninventare: Quelle und Auflösung.
- Niederschlags- und Bodenfeuchtedatensatz für Modell B (Auflösung 1–10 km) und globale Verfügbarkeit.
- Südtirol-Teilmenge und Hintergrundverfahren, bevor Modelle laufen.
- Puffergröße und Klassenverhältnis, abgeleitet aus den Daten und eingefroren.
- Lizenzprüfung am Original für IFFI (drei widersprüchliche Angaben), SLIDO, Kaikōura V3 und Zixing.
