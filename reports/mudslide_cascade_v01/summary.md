# Pilot: Umgebung vorauswählen, danach Rutschungsspuren im Einzelbild suchen

Stand: 17.10.2026. Explorativ, eigener Namespace mudslide_cascade_v01. Keine bestehenden Experimente überschrieben. Keine kalibrierte Gefahrenkarte, keine bestätigten neuen Muren und kein automatisches Weiterlernen.

## 1. Umgebungsmodell: eindeutig als Hangmure bezeichnete Ereignisse

102 Ereignisgruppen mit je fünf gematchten Pseudo-Negativen, 19 unabhängige Einheiten. Bedingte logistische Regression auf Gelände, Landbedeckung und Geologie; keine Wetterwerte, Koordinaten oder Straßen-/Gebäudeabstände als Eingabe. Fünf vorab eingefrorene Episoden-Folds mit mindestens 1 km Abstand nach Trainingsbereinigung.

Lokale AUC, Einheiten gleich gewichtet: **0.539**, 95%-Intervall [0.406; 0.669]. Zufallsreferenz 0,5, oberer empirischer p-Wert 0.279.

Bei Suchbudget 50 % bleiben über die Einheiten gewichtet 55.1 % der positiven Hänge erhalten (95%-Intervall [0.361; 0.735]; Zufallsbudget 50 %). Je Ereignis gerechnet sind es 33.3 %. Die unterschiedliche Gewichtung zeigt die Bedeutung großer Episoden.

Die Landbedeckung liegt hier als grobe Punktklasse vor. Detaillierte Wald-/Wiesenanteile in der ganzen Umgebung und gemessene Bodeneigenschaften sind noch keine Eingaben dieses Piloten.

**Kein belastbarer Vorteil dieser Vorauswahl belegt.** Sie darf im aktuellen Stand andere Hänge nicht als sicher ausschließen. Landbedeckung kann weiterhin Erfassungsbias tragen; Geologie ersetzt keine gemessenen Bodeneigenschaften. Die Vorauswahl gilt hier für lokale Kandidatenpunkte und ist noch keine flächige Geländeklassifikation.

## 2. Bildnetz: echtes beaufsichtigtes RGB-Training

U-Net mit ResNet-18-Encoder (ImageNet-Start), 192 Landslide4Sense-Trainingsbilder und 64 Entwicklungsbilder mit Pixelmasken, acht feste Epochen auf CPU. Das Netz erhält nur die RGB-Kanäle einer einzelnen Aufnahme, keine Gelände- oder Kontextdaten. Räumliche Unabhängigkeit der öffentlichen Bildaufteilung ist unbekannt: **Die folgenden Pixelwerte sind beschreibende Entwicklungswerte, kein unabhängiger geografischer Leistungsnachweis.**

Gespeicherte Epoche 4 nach vorab festgelegtem Entwicklungs-Dice: Pixel-Precision 0.394, Pixel-Recall 0.731, Dice 0.512, IoU 0.344. Immer-Hintergrund hat auf diesen Masken Recall/Dice 0. Diese Werte sind keine Quote korrekt entdeckter Muren und keine Sicherheitswahrscheinlichkeiten. Einheitenintervalle werden mangels rekonstruierbarer räumlicher Einheiten nicht behauptet.

Landslide4Sense unterscheidet allgemeine Rutschungsspuren, keine reinen Muren. Der Nutzer hat dieses allgemeine Vortraining mit gesonderter Hangmurenprüfung ausdrücklich gewählt. Auch ein RGB-Netz kann sichtbare Straßen oder andere Bildabkürzungen lernen; der Ausschluss tabellarischer Infrastrukturmerkmale beseitigt das nicht automatisch.

## 3. Österreichische Hangmuren: gesonderter Transfercheck

14 vollständige, bildseitig auswertbare Gruppen, 81 Proben aus 5 unabhängigen Einheiten. Kein österreichisches Bild wurde zum Training oder zur Epochenwahl dieses Netzes benutzt. Diese Inventarereignisse waren im Projekt allerdings schon bekannt. Inventarpunkt und Kontrollhang sind schwache Bildlabels: Eine sichtbare Narbe ist am Positiv noch nicht unabhängig eingezeichnet und am Kontrollhang nicht unabhängig ausgeschlossen.

| Variante | gewichtete lokale AUC | 95%-Einheitenintervall |
|---|---:|---|
| Nur Bildnetz | 0.615 | [0.430; 0.825] |
| Vorauswahl und Bildnetz | 0.685 | [0.525; 0.845] |

Gepaarte Differenz Vorauswahl minus Bildnetz: +0.070, 95%-Intervall [-0.120; 0.260]. Zufallsreferenz der Rangfolge 0,5. Ein Nutzen der Vorauswahl wird nur bei einem vollständig positiven Differenzintervall behauptet.

Die Vorauswahl behält in dieser Transferteilmenge 57.1 % der inventarpositiven Hänge. Die AUC der Kette ist eine Rangdiagnose mit gleichem niedrigem Score für ausgesonderte Kandidaten; sie ist keine End-to-End-Fundquote und darf die ausgesonderten Positiven nicht verdecken.

Ausschlüsse nach vorab bestimmter Bildprüfung: {'nonfinite_RGB_candidate_window': 2, 'whole_event_group_excluded': 12, 'cloud_snow_or_invalid_candidate_window': 10}. Die zugehörigen Bildmasken, Vorhersagen und Beispielansichten bleiben lokal unter data/mudslide_cascade_v01/. Sämtliche zusätzlich markierten Flächen sind UNVERIFIED; kein Fund wird in die bestätigten Trainingsdaten übernommen.

## Konsequenz und nächster sinnvoller Schritt

Der kleine Versuch ist ausführbar und liefert eine messbare Antwort. Vor mehr Training zuerst österreichische sichtbare Spuren und echte Verwechslungen blind annotieren. Die Bildsuche zunächst ohne ausschließende Umgebungs-Vorauswahl prüfen. Ein weiterer Versuch braucht eine eigene Version und vorab festgelegte Regeln; keine Schwellen- oder Seed-Suche auf diesen Ergebnissen.

## Quellen und Nachweise

- Landslide4Sense: https://zenodo.org/records/10463239 (CC BY 4.0 laut Zenodo-Metadaten; RGB-Bänder und echte Pixelmasken).
- Lokale, unveränderte Inventar-, Gelände- und Geologiedaten: DATA_SOURCES.md.
- CONTEXT_REGISTRATION.json, APPEARANCE_REGISTRATION.json: Registrierung vor dem jeweiligen Training.
- context_results.json, appearance_results.json, transfer_results.json: alle Auswertungen, keine selektierte Ergebnisliste.
- verification.json und appearance_verification.json: gespeicherte Modelle/Vorhersagen nachprüfen.
