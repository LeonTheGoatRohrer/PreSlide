# Konkreter Änderungsplan für eine neue PreSlide-Version

Status: Vorschlag, nicht implementiert. Ziel ist zusätzliche, belastbare Information über Boden und Wasser sowie eine größere Vielfalt unabhängiger Situationen. Eine AUC-Steigerung wird nicht garantiert.

## 1. Neue Version und Prüfregeln vor Berechnungen festlegen

Vorgeschlagene Pfade: `config/v05.json`, `preslide/v05/`, `data/v05/`, `models/v05/`, `reports/v05/`. Bestehende Baseline und V0.4 bleiben archivierte Vergleiche.

Registrieren: Kohorten, Quellen, zeitliche Zulässigkeit, Missing-Regeln, Gruppenbildung, Entwicklungs-/Testzuordnung, primäre Kennzahl und Modellvergleiche. Ein neuer Test muss aus bislang ungesehenen Abhängigkeitseinheiten bestehen. Die aktuelle V0.4-Testleistung darf keine Merkmals- oder Parametersuche steuern.

## 2. Mehr nutzbare Episoden gewinnen

**Geplante Änderungen:**

- `v05/audit.py`: Tier-1/A als Kernkohorte; 323 Tier-2/A-Medienereignisse separat erfassen und prüfen. Datenqualität je Quelle erhalten, keine stillschweigende Gleichsetzung.
- Herkunft, Datum, Ortsunsicherheit, Prozess und Erfassungsart dokumentieren; Doppelmeldungen entfernen.
- `v05/units.py` und `partition.py`: Kandidatenzahl, Episoden, räumliche Ketten und neue ungesehene Gruppen vor Modellierung berichten. Regeln festlegen, bevor Ergebnisse entstehen.
- Nach Stichprobenprüfung vollständige Kontrollen und Umweltabdeckung für neue Ereignisse in Stufen 1 → 5 → 20 → Gesamtbestand ermitteln.
- Gruppierung nicht künstlich lockern, um eine gewünschte Anzahl zu erreichen. Eine verfeinerte Sturmabgrenzung wäre eine eigene Hypothese mit Abhängigkeitsprüfung.

**Prüfpunkt:** Erst nach Verarbeitung nutzbare Gruppen zählen. Bei weniger als 50 insgesamt das kleinere Experiment transparent auswerten; keine 35/15-Aufteilung erzwingen. Bestehende und neue Quellen getrennt berichten.

## 3. Positionen und Meldebias untersuchen

- Eine vorab definierte, nach Region, Erfassungsart und Positionskategorie ausgewählte Stichprobe von zunächst 20 Ereignisgruppen prüfen.
- Anriss, Transport-/Ablagerungsbereich und Inventarpunkt unterscheiden. Unsichtbare kleine Rutschungen als nicht prüfbar erfassen.
- Kontrollen auf sichtbare undokumentierte Ereignisse prüfen. Nachherbilder ausschließlich zur dokumentierten Labelprüfung verwenden, nicht als Vorhersagemerkmale.
- Infrastrukturnähe und Erfassungsart für Bias-Diagnosen ermitteln. Melde- oder Qualitätsfelder nicht zu versteckten Prädiktoren machen.

**Prüfpunkt:** Belegte Korrekturen in einer neuen Labelversion speichern. Prüfer wählen oder korrigieren nicht anhand der Modellwerte. Vergleich auf identischer Kohorte und Bericht über selektive Sichtbarkeit.

## 4. Bodenbeschaffenheit ergänzen

**Quellenkandidaten:**

- ISRIC SoilGrids 250 m: Ton-/Schluff-/Sandanteile, Grobanteil, Bodendichte und Wasserhaltekennwerte. https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
- WCS oder Rasterausschnitte, keine landesweiten Raster im RAM: https://docs.isric.org/globaldata/soilgrids/wcs.html
- EU-SoilHydroGrids 250 m: gesättigte hydraulische Leitfähigkeit, Feldkapazität und Sättigungswassergehalt; Registrierung erforderlich. https://esdac.jrc.ec.europa.eu/content/3d-soil-hydraulic-database-europe-1-km-and-250-m-resolution
- BFW eBOD als lokale Qualitätsreferenz, begrenzt auf kartierte landwirtschaftlich nutzbare Böden; Massenzugriff und Nutzungsbedingungen gesondert prüfen. https://www.bfw.gv.at/digitale-bodenkarte-landwirtschaftlicher-boeden/

**Geplante Datei:** `v05/soil.py`. Zunächst ein kompakter Block aus ungefähr 6–10 Merkmalen, fachlich geeignete Tiefen etwa 15–30 und 30–60 cm im Quellenpilot prüfen. Texturanteile nicht als drei unabhängige Größen behandeln, da sie sich zum Ganzen ergänzen. Quelle, Rasterzelle, Einheit, Tiefe, Version und Unsicherheit speichern.

Diese Karten sind modellierte Schätzungen, keine örtlichen Bodenproben. Moderne Karten dürfen nicht automatisch für frühere Ereignisse als vorab verfügbare Messung gelten. Eingangs-/Kartierungszeitstände und mögliche nachträgliche Veränderungen prüfen; nicht nachweisbar zeitlich zulässige Merkmale bleiben aus der strikten Hauptanalyse heraus. Eine ausdrücklich quasi-statische Zusatzanalyse wäre gesondert zu registrieren.

**Prüfpunkt:** Abdeckung je Region und Klasse, Variation zwischen Positiv und Kontrollen, Unsicherheit und Sensitivität bei Positionsverschiebungen messen. Neue Merkmale dürfen nicht nur eine andere Darstellung bereits vorhandener Geländegrößen liefern.

## 5. Feinere Geologie prüfen

GeoSphere geologische Einheiten 1:50.000 statt nur 1:500.000: https://gis.geosphere.at/maps/rest/services/geologie/einheiten_50/MapServer/0

**Geplante Datei:** `v05/geology.py`. Polygonabfrage über REST/WFS; Lithologie und Lockermaterial unterscheiden. Bedeckung, Kartierungsstand, Lizenz, Grenzunsicherheit und Klassenharmonisierung vor Aufnahme prüfen. Keine nachträglich kartierten Rutschablagerungen als Prädiktor verwenden. 1:50.000 ist ein Kartenmaßstab und keine 50-m-Messauflösung.

**Prüfpunkt:** Gröbere und feinere Geologie auf denselben Ereignissen vergleichen. Ein fein gezeichneter Kartenausschnitt allein beweist keinen Zusatznutzen.

## 6. Vorfeuchte als zeitlichen Zustand ergänzen

**Erster Quellenpilot:** Copernicus Soil Water Index Europa, ungefähr 1 km. Historische V1 reicht vom 01.01.2015 bis 12.07.2025 und wurde ersetzt; Nachfolgeversion und Übergang für 2025/2026 gesondert prüfen. https://land.copernicus.eu/en/products/soil-moisture/daily-soil-water-index-europe-1km

**Alternative:** ERA5-Land über CDS mit Nutzeraccount/API-Zugang, vier Bodenwasserschichten, etwa 9 km. https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview

**Geplante Datei:** `v05/moisture.py`. Letzter zulässiger Zustand, Mittelwert und Änderung der Vorwoche; wenige fachlich ausgewählte Zeitskalen/Schichten. Jahreszeitliche Abweichungen nur gegen frühere Referenzdaten berechnen. Messzeit, Repräsentationsintervall, Produktlatenz, Versionswechsel, Qualitätsmasken und Alter der letzten Beobachtung erhalten.

Im Gebirge sind fehlende oder unzuverlässige Satellitenwerte zu erwarten. SWI-Zeitskalen sind keine direkt gemessenen Zentimetertiefen. ERA5-Land ist eine Modellschätzung und oft für mehrere Hänge identisch. Regionale Feuchte kann über Wechselwirkungen mit örtlichen Bodeneigenschaften helfen; sie ist kein Porenwasserdruck.

**Prüfpunkt:** Vor allem Coverage und Unterschiede innerhalb der Sechsergruppen prüfen. Ohne brauchbare Abdeckung keine stillschweigende Interpolation oder Nullersetzung. Ein fehlender Zusatznutzen ist ein gültiges Ergebnis.

## 7. Kompakte Merkmale und Modelle vergleichen

**Geplante Dateien:** `v05/features.py`, `models.py`, `experiment.py`.

- Baseline: vorhandene Gelände-/Landbedeckungs-/Geologiemerkmale.
- Zusatzblöcke einzeln: Boden; feinere Geologie; Vorfeuchte; vorhandenes Wetter.
- Wenige vorab begründete Kombinationen: Regen × Vorfeuchte, Regen × Durchlässigkeit, Vorfeuchte × lokale Geländeform.
- Bedingte logistische Regression als Hauptreferenz, dazu höchstens ein nichtlineares Vergleichsmodell.
- Wenige Regularisierungs-/Komplexitätswerte nur innerhalb verschachtelter gruppierter Entwicklungsvalidierung auswählen. Jede Vorverarbeitung ausschließlich am jeweiligen Training fitten.
- Gleiche Ereignisse und äußere Splits für Paarvergleiche verwenden; Zusatzanalyse zum Verlust an Daten durch neue Quellen.

**Prüfpunkt:** Wiederholbarer Zusatznutzen gegenüber Baseline, Gruppen-Bootstrap mit Unsicherheit, lokale AUC und Top-1 nebeneinander. Lernkurven nach unabhängigen Gruppen statt nur nach Tabellenzeilen. Zusätzliche Merkmale bei schwacher Abdeckung oder ausbleibendem Gewinn nicht zum Selbstzweck behalten.

## 8. Tests und einmalige neue Bewertung

Tests schützen Zukunftsgrenzen, Produktintervalle/Latenz, Gruppenintegrität, CRS, Einheiten, Raster-nodata, Kartenstände, doppelte Fälle, fehlerhafte Caches und Baseline-Prüfsummen. Kleine Real-Daten-Piloten vor Skalierung. Neuer Test erst nach Freeze, Ergebnisse unabhängig vom Ausgang berichten.

Landbedeckungs-/Meldebias-Sensitivität und räumliche Übertragbarkeit separat prüfen. Lokale AUC bleibt eine Rangkennzahl, keine absolute Rutschungswahrscheinlichkeit. Kein neuer Test aus bereits gesehenen V0.4-Testfällen erzeugen.

## 9. Optionale eigene zeitliche Forschungsfrage

Case-Crossover: gleicher Hang zu Ereignis- und geeigneten Referenzzeitpunkten. Referenzzeitpunkte zeitlich/ saisonal passend wählen, Inventarereignisse ausschließen, alle Zeitreihen am jeweiligen Stichtag abschneiden und dieselben Abhängigkeiten berücksichtigen. Das erweitert die Fragestellung und ist ein eigenes, ausdrücklich zu entscheidendes Experiment. Viele Referenzzeitpunkte erzeugen keine ebenso vielen unabhängigen Rutschungsereignisse.

## Priorität und Entscheidung

Zuerst Gruppen-/Qualitätsaudit und Positionsprüfung; danach Bodenblock plus genau eine Vorfeuchtequelle im kleinen Pilot; anschließend kompakte Entwicklungsvalidierung. Erst bei nachgewiesener Qualität und Zusatzinformation skalieren. Feinere Geologie parallel als Quellenprüfung, nicht als garantierte Leistungssteigerung.

Planungsziel ist ein belastbarer Zusatznutzen und gegebenenfalls eine unabhängig bestätigte lokale AUC um 0,75–0,80. Es gibt keine Zusage, dass zusätzliche Parameter 0,80 ermöglichen. Die reine Modellierung bleibt CPU-tauglich; Raster fensterweise und Anfragen gecacht. Keine zusätzlichen Skills, Plugins oder Pakete wurden für diesen Plan installiert.
