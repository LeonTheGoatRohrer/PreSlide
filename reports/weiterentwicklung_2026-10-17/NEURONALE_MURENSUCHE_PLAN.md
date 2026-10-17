# Neuronale Suche nach Rutschungs- und Murenspuren mit kontrolliertem Weiterlernen

Stand: 17.10.2026. Status: konkreter Implementierungsplan, noch keine Implementierung, Präregistrierung oder neue Modellleistung. Arbeitsname: satellite_nn_v01. Der Auftrag dieser Session umfasst die Planung.

## 1. Ziel und fachliche Grenzen

Eine vorgegebene Region wird in überlappende Bildkacheln zerlegt. Ein auf echten Rutschungsmasken trainiertes neuronales Netz markiert sichtbare Spuren auf einer einzelnen Aufnahme. Ein zweites, getrennt trainiertes Netz prüft denselben Bildbereich. Unsichere Fälle werden zusätzlich geprüft oder bleiben unklar. Geeignete neue Beispiele können später das Training ergänzen.

Die beiden Netze erhalten ausschließlich RGB-Kanäle derselben einzelnen Sentinel-2-Aufnahme, keine Wetterwerte, Ereigniskoordinaten als Merkmal, vorherigen Aufnahmen oder DEM-Kanäle. Koordinaten dienen nur der Verortung und Datenaufteilung. SCL dient der vorgelagerten Qualitätskontrolle. So bleibt der gewünschte Einzelbildnachweis überprüfbar. Zur menschlichen Labelprüfung dürfen zusätzliche Belege verwendet werden; sie sind keine Eingaben der beiden Einzelbildnetze.

Wichtige Unterscheidungen:

- Das Ziel ist eine sichtbare Spur eines bereits geschehenen Prozesses. Ein Einzelbild bestimmt weder das Ereignisdatum noch sicher den genauen Prozess.
- Landslide4Sense enthält die Klasse landslide, keine gesicherte Unterklasse Mure. Damit ist zunächst nur eine Erkennung allgemeiner Rutschungsspuren trainierbar. Ausgaben heißen Rutschungsverdacht. Für die Behauptung ausschließlich Muren braucht es zusätzlich fachlich klassifizierte Murenpolygone und entsprechend gelabelte andere Rutschungsarten als Gegenbeispiele. Ohne diese Labels wird der engere Anspruch nicht freigegeben.
- Kein sichtbarer Hinweis bedeutet nicht nachgewiesen keine Mure: Kleine, bewaldete oder alte überprägte Ereignisse können im Bild unsichtbar sein.
- Das geplante Weiterlernen ist überwachte Nachschulung beziehungsweise Self-Training mit Pseudo-Labels. Es ist kein Reinforcement Learning: Eine unabhängige Belohnungsquelle und eine Aufgabe zur Steuerung von Aktionen sind hier nicht vorgesehen.

## 2. Bestehendes wiederverwenden

Der Hauptbranch enthält die Satellitenarbeit noch nicht. Relevante lokale Entwicklungsstände:

| Bestand | Verwendung |
|---|---|
| .claude/worktrees/umsetzungsplan-2026-10-15-8d2e89/preslide/satellite/ | STAC, Rasterfenster, Gitter, Radiometrie, Wolkenpuffer und bisherige Suchreferenz |
| .claude/worktrees/satellite-data-outputs-d17502/preslide/satellite/scan.py | Regionskachelung, verblindeter Prüfbogen und Kandidatenexport |
| data/satellite/ | Vorhandene Bild-Caches nur lesend nutzen, sofern Schema und Hashes passen |
| preslide/common.py, preslide/v04/pipeline.py | Vorhandene JSON-, Hash- und Sidecar-Helfer verwenden; keine zweite Implementierung wissenschaftlicher Primitive |

Die Bildpipeline umfasst bereits RGB, NIR und SWIR. V1 der neuronalen Suche verwendet bewusst nur RGB; die übrigen Bänder dürfen eine später registrierte Variante begründen. Eine fehlgeschlagene allgemeine ImageNet-Embedding-Referenz aus der alten Pipeline ist kein Ersatz für ein auf Rutschungsmasken feintrainiertes Netz.

Vor Übernahme selektiv die beiden Satellitenstände zusammenführen und ihre Tests ausführen. Nicht alle anderen Experimentzweige mitmergen. Der letzte gespeicherte satellite-0.4-Gesamtcheck meldet FAIL bei baseline_manifest_in_this_checkout; die übrigen dort aufgeführten Checks sind wahr. Diese Integritätsfrage muss im ausführbaren Checkout geklärt werden, bevor dessen Ergebnisse als vollständig geprüft bezeichnet werden.

Neue Ausgaben ausschließlich unter data/satellite_nn_v01/, models/satellite_nn_v01/ und reports/satellite_nn_v01/. Eigene Konfiguration config/satellite_nn_v01.json. Daten, Modelle und Einzelbefunde bleiben gitignoriert. V0.3, V0.4 und alle bestehenden Satellitenergebnisse bleiben unverändert. Die neue Bibliothek wird nicht aus der Vorhersagepipeline A importiert.

## 3. Phase 0: Daten- und Rechenprüfung, dann Design registrieren

Zuerst einen technischen Probelauf ohne wissenschaftliche Auswertung durchführen:

1. Verfügbaren RAM, freien Speicher und CPU-Laufzeit für Laden, Vorwärtslauf und einen Trainingsschritt messen; verwendete Umgebung festhalten. Keine CUDA-Voraussetzung.
2. Eine echte Bild-/Maskenpaarung der Trainingsquelle prüfen, anschließend fünf und zwanzig Paare. Bandreihenfolge, Skalierung, Maskenklassen, Nodata und Farbansicht kontrollieren.
3. Externe Datensatzdateien und Gewichte erst nach Prüfung der Nutzungsrechte beziehen. Keine unbekannten Downloadskripte ausführen. HTTPS-Download, Originalquelle, Lizenz und Prüfsumme speichern. Für Planerstellung wurde nichts installiert und kein Trainingsdatensatz heruntergeladen.
4. Quellregionen, Ereignisse, überlappende Footprints und mögliche Duplikate auditieren. Die Herkunft muss eine gemeinsame Aufteilung verwandter Bilder ermöglichen. Wenn das beim öffentlichen Datensatz nicht rekonstruierbar ist, erlaubt er nur Vortraining; keine angeblich räumlich unabhängige Bewertung aus zufällig aufgeteilten Kacheln ableiten.
5. Danach Datenquellen, Zielklasse, Bildkanäle, Splits, Seeds, Architektur, Trainingsbudget, Schwellenwahl, Kennzahlen und Regeln zum Weiterlernen vor der eigentlichen Modellierung registrieren. Änderungen danach als datierte Amendments vor dem betroffenen Lauf.

Startwerte dieses Plans sind Entwurfsentscheidungen, keine empirisch optimalen Einstellungen. Die spätere registrierte Konfiguration muss alle Werte enthalten. Rechenanpassungen aus dem technischen Pilot werden vor Registrierung festgehalten.

Ergebnis: admission.json, Ressourcenmessung, Lizenz-/Quellenmanifest, eingefrorenes Splitmanifest und PREREGISTRATION.json. Abbruch vor großem Training, wenn Rechte, Bildschema oder Gruppenzuordnung ungeklärt bleiben.

## 4. Phase 1: echte Trainingslabels aufbauen

### Externes Vortraining

Primärkandidat ist Landslide4Sense: 3.799 beschriftete Trainingskacheln mit Pixelmasken, 128 × 128 Pixel; der Datensatz kombiniert Satellitenkanäle und Geländeebenen. Wir extrahieren ausschließlich die RGB-Bänder B4/B3/B2. Das Zenodo-Metadatum nennt CC BY 4.0. Öffentlich aufgeführte Validierungs- und Testbilder haben laut Originalbeschreibung keine herunterladbaren Masken; sie werden nicht als lokal auswertbarer Test eingeplant. [Datensatz](https://zenodo.org/records/10463239), [Metadaten](https://zenodo.org/api/records/10463239).

Die Originalrepository-Baseline bietet einen Link zu vortrainierten U-Net-Gewichten an. Er ließ sich in dieser Prüfung nicht erfolgreich öffnen. Zudem erwarten diese Gewichte andere Eingangskanäle. Deshalb baut der Plan nicht auf einem sofort verfügbaren, fertig trainierten RGB-Murendetektor auf. [Originalrepository](https://github.com/iarai/Landslide4Sense-2022).

### Österreichische Anpassung und Prüfung

- Vorhandene 129 Ereignisgruppen aus 15 Einheiten nur als Kandidaten für Bildannotation behandeln. Ein Inventarpunkt ist keine Pixelmaske und belegt nicht, dass auf der ausgewählten Aufnahme eine Spur sichtbar ist.
- Zunächst 1 → 5 → 20 reale Bildbereiche vollständig prüfen und sichtbare Flächen als Polygone einzeichnen. Labelwerkzeug: einfacher lokaler Polygoneditor mit Rasterhintergrund und GeoJSON-Export; vorhandenen Prüfbogen für Ja/Nein/Unklar weiterverwenden.
- Sichtbare Rutschung, sichtbarer anderer Prozess, unklar und unbrauchbares Bild getrennt erfassen. Unklare Pixel erhalten ignore, kein Hintergrundlabel. Nur explizit geprüfte Hintergrundflächen dürfen als Nicht-Rutschung lernen.
- Alte Fehlvorschläge gezielt aufnehmen: Ernte/Acker, Rodung, Steinbruch, Baustelle, Bachbett-/Hochwasserablagerung, Schnee, Wolke, Dunst und Schatten. Die alten Verwerfungen sind Einladungen zur Labelprüfung, noch keine vollständigen Masken.
- Auch zufällige gut sichtbare Hintergrundflächen und schwach bewertete Stellen annotieren. Nur die besten Treffer zu prüfen würde übersehene Ereignisse und Fehler der ersten Engine verbergen.
- Annotation mit Quelle, Datum, Bild-ID, Prozessbeleg, Prüfer und Unsicherheitsgrund speichern. Ein zweiter menschlicher Prüfer kontrolliert die Freigabestichprobe; ungeklärte Streitfälle bleiben unknown.

Ziel des ersten Anpassungspiloten: 100 geprüfte positive Objektbeispiele und 200 geprüfte schwierige Gegenbeispiele, soweit die realen Daten das hergeben. Mehrere Ausschnitte desselben Ereignisses erhöhen nicht die Zahl unabhängiger Einheiten. Werden diese Planungszahlen nicht erreicht, wird der kleinere Bestand berichtet; nichts wird erfunden oder automatisch als wahr ersetzt.

## 5. Phase 2: Bildregion kacheln

1. Eingang: georeferenzierte Sentinel-2-Aufnahme, Regionspolygon beziehungsweise bbox, Aufnahmedatum und SCL-Qualitätsdaten.
2. 128 × 128 Pixel pro Kachel auf einem festen 10-m-Gitter, Schrittweite 64 Pixel. Das entspricht 1,28 km Kantenlänge und 50 Prozent Überlappung. Überlappung schützt Objekte am Kachelrand. Sie erzeugt keine zusätzlichen unabhängigen Beispiele.
3. Ungültige Pixel, Schnee und Wolken einschließlich 100-m-Puffer maskieren; Minimum 90 Prozent gültige Pixel für einen auswertbaren Bildbereich. Objektfenster mit zu viel Maske werden unklar, nicht negativ. Diese Startregeln werden vor Modellierung registriert.
4. RGB-Transformation für Training und Anwendung identisch speichern. Rohreflektanz und Bandnummern vorab gegen Farbansicht prüfen. Keine automatische Anpassung anhand des Testgebiets. Trainingsnormalisierung nur aus Trainingsdaten; eventuelle Unterschiede der Quelldaten müssen dokumentiert aufgelöst werden.
5. Vorhersagekarten überlappend und an Rändern gewichtet zusammensetzen. Zusammenhängende Flächen erst danach bilden, damit eine Narbe nicht mehrfach gezählt wird. GeoJSON-Polygone und Fundstellen auf das metrische Raster zurückführen.
6. Initiale Mindestfläche 4 zusammenhängende gültige Pixel = 400 m²; kleine Objekte separat als außerhalb der primären messbaren Größenklasse melden. Das ist eine Auswertungsgrenze, keine Garantie, dass alle größeren Objekte sichtbar sind.

Ort, Jahreszeit und Auflösung bleiben innerhalb des auditierten Einsatzbereichs. Drohnenfotos, Orthofotos oder Handyaufnahmen sind andere Bilddomänen und benötigen eigene Kalibrierung und Prüfdatensätze. Hochskalieren erzeugt keine zusätzlichen Bodendetails.

## 6. Phase 3: Suchnetz A trainieren

Architektur: U-Net mit ResNet-18-Encoder, drei RGB-Kanäle und ein Rutschungslogit pro Pixel. ImageNet-Gewichte dienen ausschließlich als Start des Encoders. Sie erkennen ohne anschließendes Fachtraining keine Muren.

Vorgesehene Trainingskonfiguration:

- Verlust: gleich gewichtete maskierte Binary Cross Entropy und Dice Loss. ignore-Pixel tragen zu keinem der beiden Terme bei.
- AdamW, Lernrate 0,001 für Decoder und 0,0001 für freigegebene Encoderblöcke, weight decay 0,0001.
- Erste fünf Epochen Encoder einfrieren, anschließend letzten Encoderblock mittrainieren. Höchstens 30 Epochen, Early Stopping nach fünf Epochen ohne besseren Objekt-F1 auf dem Entwicklungsbestand; alle Kennzahlen ebenfalls speichern.
- Batchgröße zunächst 4, bei CPU/RAM-Pilot vorab festgelegte Reduktion. Höchstens zwei Loader-Worker. Seed 42, deterministische Operationen; nicht reproduzierbare Schritte müssen vor Ergebnisproduktion gelöst werden.
- Gemeinsame 90°-Drehungen und Spiegelungen für Bild und Maske, schwache Helligkeitsvariation; keine geometrisch entkoppelten Masken, keine erfundenen Erdrutsche.
- Positiv-/Hintergrundsampling nur innerhalb des Trainings. Vor dem ersten großen Lauf einen kleinen Satz echter, eindeutig gelabelter Beispiele überfitten: So müssen Maskenlage, Loss und Optimierung nachweislich funktionieren.

Ausgabe: Pixelkarte, Objektpolygone, unbearbeiteter Modellscore, Modell-/Daten-/Konfigurationshash und Bildreferenz. A wird zunächst allein gegen die alte Änderungsengine und eine Immer-Hintergrund-Referenz geprüft. Der alten Engine wird kein Ausschlussrecht gegeben: V1 sucht alle auswertbaren Kacheln ab. Sonst könnten ihre Fehlschläge vom neuen Netz nie korrigiert werden.

## 7. Phase 4: Prüfnetz B trainieren

Architektur: Lite R-ASPP mit MobileNetV3-Large-Encoder, RGB und eigener binärer Segmentierungsausgabe. ImageNet-Encoderstart, neu trainierter Rutschungskopf; COCO/VOC-Gewichte werden nicht als landslide-vortrainiert ausgegeben. Das Modell ist in torchvision verfügbar. [Offizielle Architektur/API](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.segmentation.lraspp_mobilenet_v3_large.html).

B verwendet dieselben geprüften Wahrheitslabels, wird aber separat mit Seed 43 und eigenem Optimierer trainiert. Kein Distillieren der A-Labels. Schwierige Gegenbeispiele werden in beiden Trainings vertreten; derselbe räumliche Split gilt für beide. Startbudget und Verlust wie A, Modellwahl auf Entwicklungsdaten. Verschiedene Architekturen und Seeds machen die Fehler nicht automatisch unabhängig.

Bei Anwendung bekommt B nur das unveränderte RGB-Fenster der A-Fundstelle mit ausreichend Umgebung. Keine A-Maske, kein A-Score, kein Texturteil als Eingang. B muss die Fläche selbst markieren. Beide Masken werden auf demselben Originalraster verglichen. Räumliche Überlappung, nicht nur zweimal Ja irgendwo im Bild, ist erforderlich.

Gemeinsame Fehler separat zählen: A richtig/B falsch, A falsch/B richtig, beide falsch und beide richtig. B bleibt während eines Nachschulungszyklus eingefroren; beide Modelle ändern sich nie unbemerkt während eines Scans.

## 8. Phase 5: Scores und Entscheidungen

Rohscores sind zunächst keine verlässlichen Prozentangaben. Pixelkalibrierung und Objektkalibrierung sind verschiedene Aufgaben. Für Kandidaten wird aus vorher festgelegten Masken-/Logitmerkmalen ein eigener Objekt-Kalibrator auf getrennten Entwicklungsgruppen angepasst. Erst nach Prüfung von Brier Score und Zuverlässigkeitskurve dürfen vergleichbare Objektscores als geschätzte Wahrscheinlichkeiten erscheinen. Beide Einzelwerte werden nicht multipliziert, weil ihre Fehler abhängig sind. [Kalibrierung](https://proceedings.mlr.press/v70/guo17a.html).

Kalibrierung und Schwellenwahl innerhalb des Entwicklungsbestands trennen: gruppiert erzeugte Out-of-fold-Objektvorhersagen oder disjunkte Kalibrierungs-/Schwellengruppen verwenden. Der finale Test ist dafür gesperrt. Bei zu wenigen Gruppen nur Scores anzeigen; keine Scheingenauigkeit in Prozent erzeugen.

Vorläufiger Ablauf bis zur validierten Schwellenwahl:

| Befund | Status | Weiteres Vorgehen |
|---|---|---|
| Keine ausreichende Bildqualität | UNASSESSABLE | Anderes Bild anfordern; sonst Stopp |
| A unter Suchschwelle, Bild auswertbar | NO_VISIBLE_DETECTION | Kein sichtbarer Hinweis; kein automatisches Negativlabel |
| A meldet Kandidat, B lehnt ab oder ist unsicher | DISAGREEMENT | Zusatzprüfung C; sonst UNKNOWN |
| A und B oberhalb ihrer Freigabeschwelle, Masken-IoU mindestens 0,30 | MODEL_AGREEMENT | Starker Verdacht und Pseudo-Label-Kandidat, kein bestätigtes Ereignis |
| Unabhängig geprüfte Quelle/Annotation bestätigt Objekt | VERIFIED_POSITIVE oder VERIFIED_NEGATIVE | Für nächste Trainingsversion zulässig |

Die Schwellen werden auf räumlich getrennten Entwicklungsgruppen festgelegt: Suchschwelle für mindestens 80 Prozent Objekt-Recall, Freigabeschwellen für mindestens 90 Prozent Objekt-Precision bei mindestens 50 Prozent Recall. Wird kein solches Paar gefunden, ist automatische Freigabe deaktiviert. Das sind angestrebte Betriebspunkte für eine Suchhilfe, keine schon erreichten Leistungen. Testwerte werden unverändert berichtet, auch wenn sie diese Ziele verfehlen.

### Zusatzprüfung C und Stopp

C erhält keine bisherigen Urteile. Bevorzugt ist ein menschlicher Prüfer mit unabhängiger Quelle, etwa Orthofoto oder dokumentierter Geländeerhebung. Eine spätere Satellitenaufnahme kann Persistenz belegen, aber nicht allein den Prozess. Ein drittes Netz ist erst sinnvoll, wenn es separat ausgebildet und als zusätzlicher Prüfer evaluiert wurde; ein anderes Sprachmodell-Prompt zählt nicht als unabhängiger Nachweis.

Automatisch höchstens eine Zusatzprüfung. Ohne ausreichenden Beleg bleibt UNKNOWN. Widerspruch wird nicht durch wiederholtes Nachfragen oder Mehrheitswahl in ein positives Trainingslabel verwandelt. C-Belege dienen der Prüfung, nicht heimlich dem Einzelbildbenchmark.

## 9. Phase 6: unangetastete Bewertung

- Vor Kachelung und Augmentation nach Ereignis/zeitlicher Episode, räumlichem Block und Bildüberlappung aufteilen. Alle Bilder und Wiederholungsaufnahmen derselben Narbe bleiben zusammen. Quellbilder mit Überlappung verbinden, Hash-/Near-Duplicate-Prüfung ergänzen; Trainings-Test-Abstand initial mindestens 1 km zwischen Footprints.
- Vorhandene österreichische Episoden sind aus früheren Analysen bekannt. Sie können eine neue Methodenentwicklung und explorative Prüfung tragen, werden aber nicht als neue unberührte wissenschaftliche Bestätigung bezeichnet. Eine neue Bestätigung braucht bisher ungesehene räumlich/zeitlich getrennte Episoden.
- Primärer Bewertungsbestand: vollständig annotierte, zusammenhängende kleine Suchgebiete einschließlich zufälliger Hintergrundflächen, nicht nur inventarzentrierte positive Ausschnitte. Zwei Prüfer, Streitfälle unknown. Ohne vollständige Inventarisierung im Testgebiet kein Recall behaupten.
- Primärer Endpunkt: Precision der endgültig ausgegebenen Objektvorschläge. Dazu Recall, F1, pixelweise IoU/Dice, Fehlalarme je tatsächlich auswertbarem km², ungeklärter Anteil, übersprungene Fläche, Laufzeit und Größenklassen berichten.
- Ein vorher definierter 1:1-Abgleich mit Referenzpolygonen (IoU mindestens 0,30) verhindert, dass mehrere Treffer desselben Objekts mehrfach zählen. Verfehlungen kleiner Spuren getrennt zeigen; Grenzobjekte nicht wegfiltern, um Ergebnisse zu verbessern.
- Jede Kennzahl mit Anzahl unabhängiger Episoden und einem Bootstrap-Intervall über diese Einheiten; Nullreferenz/Raumabdeckung und alle verglichenen Varianten berichten. Verbesserung A+B gegenüber A ist ein gepaarter Vergleich mit eigenem Intervall.
- Automatische Pseudo-Label-Nutzung erst nach einem eingefrorenen Audit der Konsensliste: mindestens 100 geprüfte Konsensobjekte aus mindestens zehn unabhängigen Episoden, Precision mindestens 90 Prozent und untere 95-Prozent-Grenze des Einheiten-Bootstraps mindestens 80 Prozent. Bei zu wenig Material oder zu breitem Intervall bleibt diese Funktion aus. Diese Schwelle erlaubt nur experimentelles Pseudo-Training, keine bestätigten Murenlabels.

Ein Freigabetest wird pro eingefrorener Version einmal geöffnet. Nach Sicht darauf keine Parameter korrigieren und denselben Test erneut als unberührt verkaufen. Wiederverwendete Entwicklungsprüfungen bleiben solche; neue Bestätigung erfordert einen neuen Test.

## 10. Phase 7: kontrolliert dazulernen

Automatischer Datenfluss und bestätigte Wahrheit werden getrennt gespeichert:

    Fundstelle
      → A/B stimmen räumlich überein
      → PSEUDO_POSITIVE in eigener Warteschlange
      → unabhängige Prüfung
      → VERIFIED_POSITIVE / VERIFIED_NEGATIVE / UNKNOWN
      → neuer versionierter Trainingsbestand
      → neues Modell, Entwicklungsvergleich, ggf. Freigabe

Standardmäßig ist auto_train_pseudolabels=false. Übereinstimmung wird also automatisch gesammelt und zur Prüfung vorgelegt. Nach Bestehen des Audits aus Phase 6 ist ein separat registrierter experimenteller Self-Training-Lauf möglich:

- Nur Konsens aus Trainings-/Suchregionen; niemals aus Validierungs-, Kalibrierungs-, Audit- oder Testgruppen und deren Überlappungs-/Abstandszonen. Wiederkehrende Fundstellen deduplizieren; keine zehn Kacheln derselben Narbe als zehn neue Objekte zählen.
- Nur die räumlich übereinstimmende Positivfläche als Pseudo-Maske verwenden. Nicht übereinstimmende und nicht geprüfte restliche Pixel bleiben ignore. Aus Nein wird keine automatische Negativmaske.
- Pseudo-Labels bleiben als solche erkennbar, mit Gewicht 0,2 gegenüber verifizierten Labels und höchstens 10 Prozent des effektiven Loss-Gewichts je Trainingszyklus. Alle Mini-Batches enthalten verifizierte Beispiele; verifizierte schwierige Negative bleiben enthalten.
- Keine Parameteraktualisierung während der Suche und kein sofortiges Nachlernen nach jedem Fund. Für den ersten Nachschulungszyklus mindestens 30 neue verifizierte Objektbeispiele aus mindestens drei neuen Trainingsepisoden sammeln, einschließlich mindestens zehn verifizierter schwieriger Negative. Pseudo-Beispiele sind nur eine optionale Ergänzung nach Audit, kein Ersatz für diesen ersten Qualitätsnachweis.
- A wird als neue Version nachgeschult; B bleibt währenddessen Prüfreferenz. Ursprüngliche verifizierte Daten werden weiterverwendet, um Vergessen und Positivverzerrung zu begrenzen. Ein später aktualisiertes B ist ein eigener registrierter Lauf.
- Kandidatenmodell gegen bisheriges Modell auf unveränderten Entwicklungsgruppen vergleichen. Nur übernehmen, wenn das gepaarte Intervall einen positiven Precision-Unterschied belegt, Recall höchstens fünf Prozentpunkte verliert und Fehlalarme/km² nicht steigen. Andernfalls bisheriges Modell aktiv lassen. Alle fehlgeschlagenen Zyklen ebenfalls berichten.
- Modelle als unveränderliche Versionen speichern; Aktivzeiger erst nach Freigabe wechseln, Rückwechsel jederzeit möglich. Modellgenerierte Bilder oder Labels werden niemals stillschweigend zu Ground Truth.

Das Risiko falscher Pseudo-Labels ist empirisch dokumentiert. Die Beschränkungen sind deshalb Teil des Lernverfahrens. [Bestätigungsfehler](https://arxiv.org/abs/1908.02983), [Self-Training-Beispiel FixMatch](https://research.google/pubs/fixmatch-simplifying-semi-supervised-learning-with-consistency-and-confidence/).

## 11. Konkrete Dateien und ausführbare Schnittstellen

Die folgende Struktur und CLI sind zu implementierende Schnittstellen, noch keine ausführbaren Befehle:

| Datei | Aufgabe |
|---|---|
| config/satellite_nn_v01.json | Alle Schwellen, Seeds, Bilder, Architektur, Budget und Freigaberegeln |
| preslide/satellite_nn/paths.py | Versionierte Wurzeln und Schutz alter Artefakte |
| preslide/satellite_nn/data.py | Quellenprüfung, RGB-/Maskenadapter, Gruppe/Footprint, Labelmanifest |
| preslide/satellite_nn/tiles.py | Überlappung, gültige Pixel, Mosaik, Pixel↔Geometrie |
| preslide/satellite_nn/models.py | A/B, konsistente Ein-/Ausgaben, sichere Zustandsgewichte |
| preslide/satellite_nn/train.py | CPU-Training, Checkpoints, deterministische Wiederaufnahme |
| preslide/satellite_nn/infer.py | Regionenscan und unabhängiger B-Aufruf |
| preslide/satellite_nn/decisions.py | Kalibrierung, Objektabgleich, Zustandsmaschine |
| preslide/satellite_nn/review.py | Vorhandenen Prüfbogen und Polygonannotation anbinden |
| preslide/satellite_nn/update.py | Gold-/Pseudo-Trennung, Zulassung, Replay und Modellfreigabe |
| preslide/satellite_nn/evaluate.py | Objekt-/Flächenmetriken, Episodenintervalle, Vergleich und Testversiegelung |
| scripts/verify_satellite_nn.py | Unabhängiger Hash-/Split-/Label-/Vorhersagecheck |
| tests/test_satellite_nn.py | Wissenschaftlich gefährliche Fehler absichern |

Geplante Reihenfolge aus dem Projektroot mit Windows-Python:

    .\.venv\Scripts\python -m preslide.satellite_nn audit --limit 1
    .\.venv\Scripts\python -m preslide.satellite_nn audit --limit 5
    .\.venv\Scripts\python -m preslide.satellite_nn audit --limit 20
    .\.venv\Scripts\python -m preslide.satellite_nn prepare
    .\.venv\Scripts\python -m preslide.satellite_nn register
    .\.venv\Scripts\python -m preslide.satellite_nn train --model a --pilot
    .\.venv\Scripts\python -m preslide.satellite_nn train --model a
    .\.venv\Scripts\python -m preslide.satellite_nn train --model b
    .\.venv\Scripts\python -m preslide.satellite_nn calibrate
    .\.venv\Scripts\python -m preslide.satellite_nn scan --config config/satellite_nn_v01.json
    .\.venv\Scripts\python -m preslide.satellite_nn review-import --labels labels.geojson
    .\.venv\Scripts\python -m preslide.satellite_nn evaluate --development
    .\.venv\Scripts\python -m preslide.satellite_nn freeze
    .\.venv\Scripts\python -m preslide.satellite_nn evaluate --sealed-test
    .\.venv\Scripts\python scripts/verify_satellite_nn.py

prepare darf Dateien und Splits aufbauen, aber keine Modellergebnisse produzieren. register friert diesen Stand vor dem ersten Fachtraining ein. Alte öffentliche Vortrainingsgewichte werden mit Herkunft erfasst. Nachtrainingszyklus nur über eigenen neuen registrierten Konfigurationsstand, nicht durch Überschreiben von v01.

Neue Abhängigkeit nur bei tatsächlichem Bedarf: torch/torchvision CPU, gegebenenfalls h5py für die Originaldateien. Vorhandene Versionen zuerst prüfen; neue Pins in einer getrennten NN-Lockdatei dokumentieren, ohne die eingefrorene Baselineumgebung zu ersetzen. Keine weitere Modellbibliothek nötig; kleiner U-Net-Decoder und vorhandene torchvision-Architekturen reichen.

## 12. Nachweise und Tests vor Freigabe

Vor jeder sicherheitsrelevanten Testfreigabe den Test an einem gezielt injizierten Fehler scheitern lassen:

- Dieselbe Szene/Narbe oder ein überlappendes Footprint in Training und Test → muss abgelehnt werden.
- Ein Testkandidat wird in die Trainingswarteschlange geschoben → muss abgelehnt werden.
- Zwei zustimmende Netze erzeugen VERIFIED_POSITIVE → muss abgelehnt werden.
- Cloud/Nodata wird zu NO_VISIBLE_DETECTION oder einem Negativlabel → muss abgelehnt werden.
- B erbt A-Maske/Score als Eingangsmerkmal → Schnittstellentest muss scheitern.
- Zweimal Ja an verschiedenen Stellen ohne Maskenüberlappung → kein Konsens.
- Vertauschte Bandreihenfolge, Maskeninterpolation oder falscher Rastertransform → Adapter-/Geometrietests fangen den Fehler ab; unter anderem Kachelrand und UTM-Zonengrenze testen.
- Ein Objekt in mehreren überlappenden Kacheln → genau ein Kandidat/Match.
- Pseudo-Label überschreitet Gewicht/Quote, UNKNOWN lernt mit oder ein Schutzpfad wird beschrieben → Fehler.
- Zweite Auswertung desselben versiegelten Tests → verweigern.
- Unveränderte Eingaben und Seeds → identische gespeicherte Vorhersagen innerhalb der vorher definierten numerischen Toleranz.

Relevante Python-Tests plus matching Verifikation und Schutz der alten Manifest-/Archivhashes ausführen. UI-Tests/Build nur bei tatsächlichen Frontendänderungen. Keine Datenprüfungen aus einem leeren Worktree als bestanden ausgeben.

## 13. Lieferbare Meilensteine und Zeitrahmen

| Meilenstein | Fertig, wenn |
|---|---|
| M0: nutzbare Daten | Rechte/Schema/Regionen geprüft, Labels sichtbar, CPU-Pilot gemessen, Design registriert |
| M1: erstes Fachnetz | A auf realen Masken trainiert; 1/5/20-Probenprüfung und unabhängige Entwicklungsgruppen ausgewertet |
| M2: Regionenkarte | Überlappender Einzelbildscan mit Polygonen, Bildqualität und Herkunft funktioniert |
| M3: zweite Prüfung | B separat trainiert; räumlicher Konsens und Fehlerkorrelation gegenüber A dokumentiert |
| M4: prüfbarer Datensatz | Verblindete Prüfung/Annotation, Gold-/Pseudo-/Unknown-Trennung und Export funktionieren |
| M5: erster Lernzyklus | Neue Trainingsversion nachvollziehbar erzeugt; Nutzen oder fehlender Nutzen auf Entwicklungsgruppen gemessen; Rollback geprüft |
| M6: Freigabe | Gesamtkette eingefroren, neuer Test einmal ausgewertet, Unsicherheiten und alle Varianten berichtet |

Zuerst M0 bis M2 fertigstellen, danach B und Weiterlernen. Der Engpass sind echte, prozessgerechte Labels und unabhängige Prüfung; weitere Netze ersetzen diese Arbeit nicht. Reine Murenerkennung darf erst nach Erfüllung der Unterklassenanforderung aus Abschnitt 1 als solche bezeichnet werden.

Bis zum Wettbewerbsschluss am 18.10.2026 ist keine belastbare Zusage für neue Modelle, unabhängige Validierung und nachgewiesene Lernverbesserung möglich. Ein erster technischer Pilot hängt von Datenzugang und gemessener CPU-Laufzeit ab. Dieser Plan und eine eventuell fertiggestellte Demo werden als neue Entwicklung gezeigt; bestehende Ergebnisse bleiben die belegte wissenschaftliche Grundlage.

## 14. Erste drei Umsetzungsschritte

1. Satelliten-Bildleser und Prüfbogen selektiv in einen ausführbaren Stand übernehmen, Schutz-/Integritätschecks klären und eigenen NN-Namespace einrichten.
2. Landslide4Sense-RGB/Masken und fünf österreichische Aufnahmen mit verifizierbaren Polygonlabels auditieren; Band-/Skalierungs- und CPU-Pilot ausführen, Datensatzgruppierung festlegen.
3. Design registrieren und A als erstes echtes Rutschungsnetz trainieren. B und automatisches Weiterlernen erst nach messbarem Ergebnis von A hinzufügen.
