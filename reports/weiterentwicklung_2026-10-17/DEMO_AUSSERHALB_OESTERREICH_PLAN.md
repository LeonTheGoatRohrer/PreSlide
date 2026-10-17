# Plan: Demo der Rutschungssuche in einer Region mit vorhandenen Labels

Stand: 17.10.2026. Status: Plan, nichts umgesetzt. Bezug: `NEURONALE_MURENSUCHE_PLAN.md`, Namespace `satellite_nn_v01`.

## 1. Entscheidung und Aussagegrenze

Österreich hat keine pixelgenauen Rutschungslabels, die wir nutzen könnten. Die Demo läuft deshalb in einer anderen Region, für die ein offenes Rutschungsinventar mit Polygonen existiert. Zulässige Aussage: *Die Methode (RGB-Einzelbild, Netz A) findet in Region X sichtbare Rutschungsspuren mit gemessener Precision/Recall.* Nicht zulässig: Aussagen über Österreich, über Muren im Besonderen oder über Vorhersage. Die bestehenden Österreich-Ergebnisse (V0.3–V0.9) bleiben unverändert.

## 2. Anforderungen an das Demogebiet (alle müssen erfüllt sein)

1. **Nicht im Training:** Das Gebiet und dessen Ereignisse kommen nicht in Landslide4Sense vor. Die Kacheln dort haben keine Koordinaten, die Herkunft ist nur aus der Veröffentlichung bekannt (laut Originalbeschreibung vier Ereignisregionen in Asien; vor Auswahl aus der Quelle selbst prüfen). Im Zweifel anderes Gebiet wählen.
2. **Polygoninventar offen lizenziert**, mit Ereignisdatum oder -zeitraum und Kartierung auf Satellitenbildern bzw. Luftbildern.
3. **Freie Sentinel-2-L2A-Aufnahme** nach dem Ereignis, kurz danach, geringe Bewölkung über dem Gebiet (SCL-Prüfung).
4. **Ähnliche Bilddomäne** wie das Training: Sentinel-2, 10 m, bewachsene Hänge mit kahlen Narben.
5. **Vollständigkeit prüfbar:** Das Inventar deckt ein zusammenhängendes Gebiet vollständig ab; nur dann sind Recall und Fehlalarme pro km² berechenbar.

## 3. Kandidaten (zu verifizieren, keine bestätigten Fakten)

| Kandidat | Warum interessant | Zu prüfen |
|---|---|---|
| Puerto Rico, Hurrikan Maria 2017 (USGS-Inventar) | Tropisch bewachsene Hänge, ähnlich zum Training; Polygone offen | Nicht in L4S? Wolkenfreie Szene nach Sep. 2017; Lizenz/Datenfreigabe |
| Kaikoura, Neuseeland, 2016 (GNS-Inventar) | Große Datenbasis, andere Landschaft (Gegenprobe zur Übertragung) | Sentinel-2-Verfügbarkeit nach Nov. 2016, Lizenz |
| Weitere offene Inventare (z. B. Sammlungen im USGS-/Zenodo-Katalog) | Alternativen, falls oben etwas nicht passt | Je Gebiet dieselbe Checkliste |

Auswahl nach Checkliste in Abschnitt 2, nicht nach der erwarteten Trefferquote. Die Wahl wird vor dem ersten Modelllauf festgehalten.

## 4. Ablauf (Pilot vor Vollauf)

1. **Quellenprüfung (ohne Modell):** Inventar, Lizenz, Ereignisdatum, CRS, Vollständigkeit; Überschneidung mit Landslide4Sense ausschließen. Nur Download nach Freigabe (Name, Quelle, Größe nennen).
2. **Szene:** Sentinel-2-L2A holen, SCL-Wolken-/Schneemaske, Bandwerte auf die Skalierung des Trainings bringen. Die Trainingswerte sind vorskaliert (Mittel ca. 0,93–0,96); die Umrechnung muss an Trainingsdaten dokumentiert und vorab festgelegt werden, nicht am Demogebiet angepasst.
3. **Rasterung der Labels:** Polygone in das 10-m-Raster der Szene bringen, CRS und Pixelversatz prüfen (Test mit absichtlich verschobener Maske muss die Metrik verschlechtern).
4. **Pilot:** ein Ausschnitt von etwa 10 × 10 km; Netz A kachelt (128 px, Schritt 64), mosaikiert, bildet Objekte (Mindestfläche 400 m²). Ergebnis nur ansehen und Metriken berechnen, keine Parameter ändern.
5. **Vollauf** über das ganze Gebiet, sobald der Pilot technisch sauber ist.
6. **Kennzahlen:** Objekt-Precision und -Recall (1:1-Abgleich, IoU ≥ 0,30), Pixel-IoU, Fehlalarme je km² auswertbarer Fläche, Anteil ungeklärter/maskierter Fläche, Ergebnis nach Objektgröße. Vergleichswerte: Immer-Hintergrund und, falls vorhanden, die alte Änderungsengine.
7. **Unsicherheit:** Konfidenzintervall per Bootstrap über räumliche Blöcke (nicht über Kacheln); Anzahl unabhängiger Blöcke angeben. Ein einzelnes Ereignis ist ein Fallbeispiel, kein Nachweis der Verallgemeinerung.
8. **Negativkontrolle:** dieselbe Szenenart ohne Ereignis (Aufnahme vor dem Ereignis) laufen lassen; viele Funde dort deuten auf Fehlalarme durch Ernte, Wolken, Schatten oder Gelände.

## 5. Schwellen und Regeln (vorab, keine Anpassung am Demogebiet)

- Entscheidungsschwelle 0,5 wie in der Registrierung; Wahl einer anderen Schwelle nur auf den Entwicklungskacheln des Trainings, nie am Demogebiet.
- Das Demogebiet wird einmal ausgewertet. Danach keine Korrektur von Parametern und kein erneutes Ausweisen als ungesehen.
- Alle gerechneten Varianten werden berichtet, auch schlechte.
- Ein schlechtes Ergebnis wird als solches gezeigt: Dann bleibt die Demo bei der Methodendarstellung, und Österreich braucht eigene Labels (siehe Abschnitt 7).

## 6. Darstellung

Karte mit Szene, Referenzpolygonen und Modellfunden (Treffer, Fehlalarm, Übersehenes getrennt eingefärbt), Maske der unbewertbaren Flächen, Kennzahlentabelle mit Intervallen, ausdrückliche Zeile „Region X, nicht Österreich; Netz A auf Landslide4Sense vortrainiert, Dev-Daten nicht räumlich unabhängig". Beschriftung „Rutschungsverdacht", nicht „Mure".

## 7. Später, für Österreich

Eigene Labels sind der Engpass: 20 → 100 Bildbereiche mit Polygonen aus Orthofoto oder dokumentierter Geländeerhebung (siehe Phase 1 des Hauptplans). Erst damit lässt sich der Transfer nach Österreich messen.

## 8. Risiken

- Das Training stammt aus anderen Landschaften; Transfer kann schwach sein. Das ist ein gültiges Ergebnis.
- Inventare enthalten Kartierfehler und Lücken; Fehlalarme können echte, nicht kartierte Rutschungen sein. Daher Stichprobe der Fehlalarme visuell prüfen und getrennt zählen.
- Skalierung zwischen Trainings- und Szenenwerten ist die wahrscheinlichste technische Fehlerquelle; zuerst mit einer Kachel gegen Farbansicht prüfen.

## 9. Fertig, wenn

Gebiet nach Checkliste gewählt und dokumentiert, Quelle/Lizenz/Prüfsumme gespeichert, Pilot und Vollauf mit gespeicherten Vorhersagen, Kennzahlen mit Intervallen, Negativkontrolle, Karte, kurze Limitierungen. Ablage unter `reports/satellite_nn_v01/demo/`, `data/satellite_nn_v01/demo/`.
