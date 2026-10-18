# Offene Rutschungsinventare weltweit: Recherche für Lage- und Stärkemodelle

**Stand: 17. Oktober 2026. Reine Literatur- und Portalrecherche. Es wurde nichts heruntergeladen, kein Datensatz geöffnet und keine Datei in `data/` angelegt.** `DATA_SOURCES.md` bleibt unverändert, weil noch nichts bezogen wurde. Vor jedem Download sind Lizenz, Feldliste und Kartierumriss am Original zu prüfen und dann dort einzutragen.

Zweck: Datensätze finden, aus denen sich lernen lässt, **wo im Gelände Rutschungen entstehen** (Lage), möglichst mit Größe/Stärke, Datum und Auslöser. Objektiv kartierte, flächig erfasste Inventare zählen mehr als Meldedaten mit Bias.

## 1. Wie die Angaben zu lesen sind

Jede Zahl und Lizenz trägt eine Herkunftsmarke:

| Marke | Bedeutung |
|---|---|
| **[A]** | Auf einer tatsächlich abgerufenen Seite gelesen (Quelle genannt). |
| **[S]** | Nur aus einer Suchzusammenfassung. Die Seite selbst wurde nicht gelesen. Nicht als gesichert werten. |
| **[G]** | Nur aus dem Gedächtnis, nicht verifiziert. |
| **unbekannt** | Nicht auffindbar. Der Eintrag nennt, wo die Angabe stehen müsste. |

**Bewertung 1–5** für den genannten Zweck: Lage plus Stärke, geringer Bias, Menge, Zugänglichkeit. Die Bewertung ist ein Urteil der Recherche, keine Messgröße. Wo der Zugang nicht belegt ist, wurde abgewertet.

**Abdeckung und Lücken.** Mehrere wichtige Quellen waren nicht erreichbar: ScienceBase (USGS) liegt hinter einer Cloudflare-Sperre, ebenso GNS (Neuseeland), ESDAC/JRC, Géorisques, Bhukosh (Indien), Figshare, opendata.swiss und einige Verlagsseiten. Dort fehlen Dateigrößen, Zählungen und Lizenzen, und der Eintrag sagt das ausdrücklich. Nicht oder nur oberflächlich geprüft: Colorado CGS, Pennsylvania/Utah/Kentucky, Japan (Kumamoto, Hiroshima), Bhutan, Ecuador, Chile, SilentSlides (unter diesem Namen nichts gefunden).

## 2. Die fünf besten Kandidaten

Auswahl nach dem Zweck (objektiv kartiert, Polygone, Größe ableitbar, offen zugänglich, Kartierumriss für Kontrollen):

| Rang | Datensatz | Warum | Haupteinschränkung |
|---|---|---|---|
| 1 | **Emilia-Romagna RER2023** (Italien) | 80.997 Polygone aus 0,2-m-Luftbildern, Starkregen, >6.000 km² flächig kartiert, CC BY 4.0, 43,6 MB [A] | Ein Ereignis (Mai 2023), Apennin statt Alpen, zwei Regenphasen nicht getrennt |
| 2 | **IFFI** (Italien, ISPRA + Regionen) | Größtes Alpeninventar: über 684.000 Phänomene [A], Maßstab 1:10.000 [S], direkter Nachbar Österreichs | Lizenzangaben widersprechen sich, Datum oft fehlend, Aktualität je Region verschieden, Sturz muss gefiltert werden |
| 3 | **Gorkha 2015, Roback et al.** (USGS) | 24.915 Polygone, Public Domain (CC0), Layer „Extent of mapping“ und „Obscured areas“ liefern den Kartierumriss [A] | Erdbeben-Auslöser, nicht Regen |
| 4 | **Wenchuan mehrzeitig, Fan et al. 2019** (ESSD) | Koseismische Rutschungen plus Folgejahre bis 2018, Aktivitätsklassen, Fehlerangabe (Fläche ±19 %), 527 Murgänge mit Niederschlag, CC BY 4.0 [A] | Nur 471 km² in 42 Einzugsgebieten, Erdbebenkontext |
| 5 | **Far-Western Nepal** (Zenodo 4290099) | 26.350 Polygone und 25.639 Punkte, Monsun statt Erdbeben, AOI-Polygon, 24,1 MB, CC BY 4.0 [A] | Datum nur für 8.778 Punkte und teils automatisch aus Landsat abgeleitet (Genauigkeit 83 %) |

Knapp dahinter: USGS-Kompilation v3 (CC0), Oregon SLIDO, Zixing RLZX-LIM, Sen12Landslides, Kaikōura 2016.

## 3. Gesamttabelle, sortiert nach Bewertung

Spalte „Kontrollen“: Lässt sich ein kartiertes Gebiet ohne Ereignis ableiten? „ja“ heißt, ein Kartierumriss oder eine Untersuchungsfläche liegt dem Datensatz bei. „bedingt“ heißt, nur mit Zusatzquelle oder Annahme. „nein“ heißt, Nichtmeldung bedeutet nicht „keine Rutschung“.

### Bewertung 5

| Datensatz | Region | Anzahl | Geometrie | Lizenz | Erfassung / Bias | Kontrollen |
|---|---|---|---|---|---|---|
| Emilia-Romagna RER2023 | Italien | 80.997 [A] | Polygon, Shapefile | CC BY 4.0 [A] | manuell, Luftbild 0,2 m, Regen Mai 2023 | ja |

### Bewertung 4

| Datensatz | Region | Anzahl | Geometrie | Lizenz | Erfassung / Bias | Kontrollen |
|---|---|---|---|---|---|---|
| IFFI | Italien | >684.000 [A] | Punkt, Linie, Polygon [S] | widersprüchlich (CC BY 4.0, CC BY-SA 4.0, CC BY-NC-SA 3.0) [A/S] | Luftbild, Feld, Archiv; Datum oft fehlend | ja, regional verschieden |
| Gorkha 2015 (Roback, USGS) | Nepal | 24.915 [A] | Polygon (Gesamt + Anriss getrennt) | CC0 [A] | Bilder <1 m vorher/nachher | ja (Extent-Layer) |
| Wenchuan mehrzeitig (Fan 2019) | China | 8.917 koseismisch [A] | Polygon | CC BY 4.0 [A] | manuell, 5 Kartierer, 76 % Übereinstimmung | ja (42 Einzugsgebiete) |
| Far-Western Nepal | Nepal | 26.350 Polygone [A] | Polygon + Punkt | CC BY 4.0 [A] | Google Earth, 79 Zeitschnitte | ja (AOI) |
| Zixing RLZX-LIM | China | 19.403 [A] | Polygon | Artikel CC BY 4.0, Datenlizenz ungeprüft | visuell, Gaofen 2 m, Feldprüfung (Vollständigkeit 96,7 % bei 213 Stichproben, straßennah) | ja |
| USGS Landslide Inventories v3 | USA | Zahl unbekannt (Viewer nennt 613.724, Version unklar) | Punkt + Polygon | CC0 [A] | Mosaik vieler Quellen, Feld `Confidence` | **nein** (Kartiergrenzen fehlen) |
| Oregon DOGAMI SLIDO 4.5 | USA | 71.318 Ablagerungen [A] | Polygon, Punkt, Linie | **nicht genannt** | Studien-Mosaik, teils Lidar | ja (`Inventory_Map_Index`) |
| USGS Earthquake-Ground-Failure-Repository (Tanyaş 2017) | global | 32 Inventare [A] | je Inventar verschieden | CC0 [A] | Bildinterpretation, Erdbeben | ja, je Inventar zu prüfen |
| Sen12Landslides | global (15 Inventare) | ~75.000 Annotationen [A] | Maske + Polygone | CC BY 4.0 [A] | Sentinel-1/2 + DEM, Datum teils geschätzt | ja (Zufallshintergrund, nicht gematcht) |
| Kaikōura 2016 (V3) | Neuseeland | 31.623 Anriss-, 26.559 Ablagerungspolygone [S] | Polygon | unklar (GNS-Haftungsausschluss) | Orthofoto 0,3 m + Lidar, manuell | ja |
| Hongkong ENTLI | Hongkong | ~110.500 [A] | unklar (Krone/Bahn) | **unklar** | Luftbild ab 1945, nur Jahr | ja |
| Süd-Kirgisistan (GFZ) | Kirgisistan | 1.583 [A] | Polygon | CC BY 4.0 [A] | halbautomatisch aus NDVI-Zeitreihen | ja |
| São Sebastião 2023 | Brasilien | 1.116 Polygone + 989 Anrisspunkte [A] | Polygon, Punkt | CC BY 4.0 [A] | Luftbild 10 cm | ja |

### Bewertung 3

| Datensatz | Region | Anzahl | Lizenz | Kurzurteil |
|---|---|---|---|---|
| Cyclone Gabrielle 2023 | Neuseeland | >140.000 [A] | unbekannt | Hervorragend und regenbedingt, aber Zugang noch nicht öffentlich belegt: bei GNS anfragen. Potenziell 5. |
| Haiti 2010 (Gorum, Harp, USGS) | Haiti | 23.567 (Harp) [S] / >4.490 (Gorum) [S] | nicht angegeben | Zählungen widersprechen sich, Metadaten prüfen |
| Iburi / Hokkaido 2018 (Zhang) | Japan | Zahl nicht auf der Seite; 5.625–7.142 [S] | CC BY 4.0 [A] | Klein (3,0 MB), Altrutschungen getrennt, Wetterstationen beigelegt |
| Washington DNR | USA | unbekannt | unbekannt | Lidar-basiert, expertengeprüft, aber nichts verifizierbar (Dienst verlangt Token) |
| Kalifornien CGS | USA | ~53.000 Einzelpolygone, nicht dedupliziert [A, Layerzählung] | CC BY [A], Reproduktionshinweis ungeklärt | Datumsfelder fast leer (z. B. 98 von 16.756), Auslöserfeld leer, keine Kartiergrenzen |
| North Carolina NCGS | USA | „>4.500“ [A] | unbekannt | Punkte + Umrisse + Ablagerungen, Felder und Download ungeprüft |
| Nepal-Monsun (BGS) | Nepal | 12.838 [A] | OGL [A] | Nur Kronenpunkte mit Geländeattributen, Landsat-Auflösung, 2011/2012 fehlen |
| Chi-Chi/Morakot (Marc 2015) | Taiwan | unbekannt | CC BY-NC 4.0 [A] | Regeninduziert, klein, nicht kommerziell |
| NIED Landformen | Japan | unbekannt | Namensnennung; kommerziell nur mit Genehmigung [A] | Landesweit, aber alte große Landformen, keine Ereignisse |
| Wenchuan, Xu et al. 2014 | China | 197.481 [S] | Public Domain | Zahl nicht bestätigt; Erdbeben |
| Bayern LfU GEORISK | Deutschland | „>10.000 Hangbewegungen“ [A] | CC BY 4.0 [A] | Alle Prozessarten, Abdeckung in den Alpenlandkreisen gut; Download-Dienst belegt (Shapefile), Felder und Datum nicht; Hinweisbereiche modelliert |
| Südtirol IFFI-WFS | Italien | unbekannt (per WFS ermittelbar) | CC BY-SA 3.0 [A] | Offener Direktzugang zu einem Teil von IFFI, 1:10.000 |
| NVE Skredhendelser | Norwegen | >100.000 Lawinen- und Rutschereignisse [A] | CC BY 3.0 [A] | Qualitätsstufen A–D, Straßen-/Bahnbias, Anteil Erd- und Flutrutschungen unbekannt |
| Oberösterreich Ereigniskataster Rutschung | Österreich | unbekannt | CC BY 4.0 [A] | Offenes Shapefile (EPSG:31255), Inhalt ungeprüft, mögliche Vermischung mit Modellflächen |
| WLV Ereignisse (bundesweit) | Österreich | unbekannt (GPKG 2,5 MB) | INSPIRE noConditionsApply [A] | Amtlich erfasst, nur Schadensereignisse im WLV-Bereich, Rutschung ~5–10 % der Ereignisse; Felder und Datum unbekannt |
| OÖ Karte der Phänomene | Österreich | unbekannt | CC BY 4.0 [A] | Geländemerkmale (Rutschung, Anrisse, Übermurung), vermutlich ohne Ereignisdatum |
| BOKU-Fallstudie (Zenodo 11400480) | Österreich | unbekannt | CC BY 4.0 [A] | ~9,7 MB Shapefiles, Inhalt unklar |
| Kärnten Natur- und Umweltereignisse | Österreich | unbekannt | CC BY Österreich 4.0 [S] | Meldungs- und schadensgetrieben, unverifiziert |
| Puerto Rico Hurricane Maria | USA | unbekannt | nicht angegeben | Sehr genau (1:600 bis 1:1.000), aber nur ~10 km² |
| Landslide4Sense | global (4 Gebiete) | 3.799 Training-Patches [A] | CC BY 4.0 [A] | 3,1 GB, keine Koordinaten und kein Datum öffentlich |
| UGLC (Unified Global Landslide Catalogue) | global | ~1,06 Mio. Punkte / 984.126 Polygone [A] | CC BY-NC 4.0 [A] | Sammelkatalog, heterogen, nur als Fundliste |
| NASA COOLR, 22 neue Regeninventare | global | „Tausende“ [A] | unbekannt | Figshare nicht abrufbar, ungeprüft |
| Himalaya-weit (Chen 2024) | Himalaya | >265.000 [S] | unbekannt | CNN-abgeleitete Labels, 30 m |
| RLBJ Peking 2023 | China | 15.383 [S] | unbekannt | Repository nicht gefunden |

### Bewertung 2 oder 1

| Datensatz | Bew. | Warum |
|---|---|---|
| NASA Global Landslide Catalog (GLC) | 2 | 11.033 Punkte [A], Stärkeklasse und Auslöser vorhanden, aber Medienbias, Positionsklassen bis 250 km, Lizenz nicht angegeben |
| GeoSphere GEORIOS | 2 | Medienbasiert, „bei weitem nicht vollständig“ [S] |
| Kolumbien SGC | 2 | 6.826 Punkte [A], CC BY 4.0, nur Typ, kein Datum |
| Peru INGEMMET | 2 | >34.000 Ereignisse [S], Dienst beim Abruf nicht erreichbar |
| Frankreich BDMvt | 2 | 65.942 Punkte, 17.696 Glissements [A], Meldebias, Lizenz unbelegt |
| NZLD (GNS) | 2 | 22.575 Datensätze (2017) [S], Meldedaten, Zugang über Registrierung |
| Slowenien | 2 | Kein systematisches Landesregister [S]; Feldschicht ohne Zahl und Lizenz |
| Schweiz StorMe / WSL | 2 | Kein offener Landesdownload, schadensgetrieben |
| ELSUS v2 | 2 | Anfälligkeitsraster, kein Inventar; als Vergleichsbaseline brauchbar |
| Nepal Durham 2010–2021, ICIMOD, Gnyawali (Gorkha), Kashmir 2005, Wanzhou/Fuling | 2 | Inhalt, Anzahl oder Lizenz nicht prüfbar |
| CAS Landslide Dataset | 2 | 20.865 Bilder [A], Lizenzen je Teilsatz verschieden (teils nicht kommerziell), kaum Negativbilder |
| HR-GLDD | 2 | 576 MB [A], keine Georeferenz |
| GDCLD | 2 | 26,3 GB [A], fast nur Erdbeben, „nur wissenschaftliche Forschung“, teils nicht öffentliche Bilder |
| GSI Indien (Bhukosh) | 2 | 91.000 Rutschungen laut Behörde [S], Portal nicht erreichbar |
| Burgenland Verdachtsflächen | 2 | Hinweis-, keine Ereigniskartierung |
| Steiermark Gefährdungspotentialkarte | 1–2 | Modellausgabe, als Label zirkulär |
| Bayern Gefahrenhinweiskarte | 1 | Modellkarte, als Label ungeeignet |
| Bijie | 1 | 770 Rutschungsbilder, überwiegend Steinschlag, Lizenz unklar, Konto nötig |
| Global Fatal Landslide Database | 1 | Median 681 km² Positionsunsicherheit [A], nur tödliche Ereignisse |
| European Landslide Database (Herrera 2018) | 1 | Rohdaten nicht offen |

## 4. Steckbriefe der Datensätze mit Bewertung 4 oder 5

Pro Datensatz: Quelle, Volumen, Felder, Zeitraum, Besonderheiten. Alle Links sind Einstiegsseiten, keine geprüften Direktdownloads, soweit nicht anders vermerkt.

### Emilia-Romagna RER2023 (5/5)
- Quelle: ESSD-Artikel https://essd.copernicus.org/articles/17/1055/2025/ [A]; Daten Zenodo DOI 10.5281/zenodo.13742643 (V1, 10.09.2024, `RER2023_V1.rar`, 43,6 MB) [A].
- 80.997 Polygone, manuell im Maßstab 1:800 bis 1:200 aus Luftbildern (0,2 m, RGB+NIR, aufgenommen 23.05.2023, Vorher-Bilder AGEA 2020) digitalisiert; kartiert über 6.000 km² [A]. CRS im Artikel nicht genannt.
- Attribute: IDC, ClassMan, Lito (Geologie am Zentroid), GLI, NFS, ClassNew [A]. Keine Fläche im Attribut, aber aus der Geometrie ableitbar.
- Zeit: zwei Regenereignisse (1.–3. und 15.–16.05.2023), nicht getrennt.
- Weitere Version: Ferrario & Livio, 47.523 Rutschungen aus PlanetScope (3 m), ausdrücklich nicht validiert, CC BY 4.0, 38,2 MB, UTM 32N, Nicht-Rutschungs-Polygone in eigener Datei: https://zenodo.org/records/8102429 [A].
- Probleme: Typen enthalten auch Flows, nach `ClassNew` filtern. Ein Ereignis, eine Region.

### IFFI (4/5)
- Quellen: https://www.progettoiffi.isprambiente.it/ , Portal https://idrogeo.isprambiente.it , ISPRA-News 2026 mit „über 684.000“ [A]. Ältere Stände: „über 620.000“ und „über 635.000 (1116–2024, 25.004 km²)“ [A/S].
- Geometrie: Punkt (Krone), Polygon wenn kartierbar, Linie wenn die Breite nicht kartierbar ist [S]. Maßstab 1:10.000 [S]. CRS unbekannt. Nationale WMS/WFS-Endpunkte und Direktdownload: nicht bestätigt (müssten im IdroGEO-Bereich „Open data“ stehen).
- Felder: Bewegungsart (inkl. Sturz, Rutschung, Fließen, komplex), Fläche, Datum und Auslöser teilweise [S]. Attributliste nicht abgerufen.
- **Lizenz widersprüchlich:** CC BY 4.0 laut ISPRA-Rechtshinweis [S], CC BY-SA 4.0 im Lizenzdokument Valle d'Aosta [A], CC BY-NC-SA 3.0 auf der alten Projektseite [A]. Die gültige Fassung am Download dokumentieren. CC BY-SA kann Bedingungen für abgeleitete Daten auslösen, CC BY-NC schließt kommerzielle Nutzung aus.
- Aktualität: Stände je Region zwischen 2007 und 2017 [S].
- Südtirol: eigener offener Zugang über WFS/WMS, CC BY-SA 3.0 [A]: https://geoservices1.civis.bz.it/geoserver/p_bz-Geology/ows

### Gorkha 2015, Roback et al. (4/5)
- https://www.usgs.gov/data/map-data-landslides-triggered-25-april-2015-mw-78-gorkha-nepal-earthquake [A], DOI 10.5066/F7DZ06F9. CC0 [A].
- 24.915 Gesamtflächen und 24.795 Anrissflächen, Shapefile; 142 Gesamtflächen ohne Anriss, 12 Anrisse ohne Gesamtfläche [A]. Andere Gorkha-Inventare zählen 47.200 Rutschungen (anderes Zählverfahren) [S].
- Zeitraum 26.04.–15.06.2015 [A]. Volumen ~123 MB [S]. CRS auf der Seite nicht genannt.
- Kontrollflächen: „Extent of mapping“ und „Obscured areas“ als eigene Layer [A].

### Wenchuan mehrzeitig, Fan et al. 2019 (4/5)
- https://essd.copernicus.org/articles/11/35/2019/essd-11-35-2019.html [A]; Zenodo 10.5281/zenodo.1405489, 35,6 MB insgesamt [A].
- 8.917 koseismische Rutschungen, dazu neue und remobilisierte Rutschungen für 2011, 2013, 2015, 2017, 2018; 471 km², 42 Einzugsgebiete; 527 Murgänge in 244 Einzugsgebieten (2008–2017) mit Niederschlag von Talstationen [A].
- Polygone, Klassen Rutschung/Murgang/Kanalablagerung, Aktivitätsgrade A0–A4. Visuelle Interpretation, Flächenunsicherheit ±19 %. CC BY 4.0 [A].

### Far-Western Nepal (4/5)
- https://zenodo.org/record/4290099 [A]. 26.350 Polygone, 25.639 Punkte, 8.778 datierte Punkte (1992–2018), 24,1 MB (vier Shapefiles inkl. AOI), UTM 44N, CC BY 4.0 [A].
- Quelle: 93 Google-Earth-Bilder, 79 Zeitschnitte 2002–2018, Klassifikation flach/tiefgründig. Datierung automatisch aus Landsat-Vegetation (Genauigkeit 83 %). Nutzungsbedingungen der Quellbilder (Google Earth) nicht geprüft.

### Zixing RLZX-LIM (4/5)
- Scientific Data, https://pmc.ncbi.nlm.nih.gov/articles/PMC12325695/ [A]; Daten Figshare DOI 10.6084/m9.figshare.27960762 (403, nicht geprüft).
- 19.403 flache Rutschungen, ~53,89 km², 4 bis 171.982 m². Auslöser Starkregen (Taifun Gaemi, 26.–28.07.2024). Visuelle Interpretation (Gaofen 2 m), Polygonflächen ±20 bis 28 % gegen UAV. Untersuchungsgebiet als Shapefile.
- Datenlizenz nicht bestätigt (Artikel: CC BY 4.0). Ein Sturm, daher starke Clusterabhängigkeit.

### USGS Landslide Inventories ver. 3.0 (4/5)
- https://www.usgs.gov/data/landslide-inventories-across-united-states-ver-30-february-2025 [A], DOI 10.5066/P14AJF8I. CC0 [A].
- GeoPackage, Shapefile, CSV. Felder: `USGS_ID`, `Date_Min`/`Date_Max`, `Fatalities`, `Confidence` (1, 2, 3, 5, 8), `LS_Type`, `Inventory`, `Inv_URL` [A]. Keine Fläche, kein Auslöser.
- Gesamtzahl und Volumen nicht abrufbar (ScienceBase gesperrt). Kartiergrenzen der Quell-Inventare fehlen: Kontrollen nur über die Originalinventare (`Inv_URL`).
- Enthält Nicht-Rutschungen (Erosions-, Lawinenrinnen) und gemischte Prozesse.

### Oregon DOGAMI SLIDO 4.5 (4/5)
- https://www.oregon.gov/dogami/slido/pages/data.aspx [A]. 71.318 Rutschungsablagerungen (Release 12.04.2024), 599 MB File-Geodatabase [A].
- Layer Punkte, Polygone, Linien, Suszeptibilitätsraster 10 m. **Lizenz auf der Seite nicht genannt**, nur Disclaimer. CRS und Feldkatalog stehen in den XML-Metadaten.
- `Inventory_Map_Index` liefert die Kartierflächen und damit Kontrollen.

### USGS Earthquake-Ground-Failure-Repository (4/5)
- https://www.usgs.gov/data/open-repository-earthquake-triggered-ground-failure-inventories [A], DOI 10.5066/F7H70DB4, CC0 [A]. Beherbergt 32 Inventare [A]. Gesamtzahl der Rutschungen, Formate und Volumen unbekannt (ScienceBase gesperrt). USGS warnt, die Inventare nicht unreflektiert zu vergleichen.

### Sen12Landslides (4/5)
- https://huggingface.co/datasets/paulhoehn/Sen12Landslides [A], Paper https://pmc.ncbi.nlm.nih.gov/articles/PMC12606323/ [A]. 171 GB, CC BY 4.0.
- ~75.000 Annotationen aus 15 Inventaren, 128×128-Patches, 10 m, 15 Zeitschritte, Sentinel-1/2 + DEM, Ereignisdatum (bekannt ±7 Tage, sonst aus NDVI-Abfall geschätzt) und Auslöser. Hintergrundpatches sind Zufallsstichprobe, **nicht** nach Gelände gematcht.

### Kaikōura 2016, Massey et al. (4/5)
- V2: 29.519 Anrisszentroide [A, GNS-ArcGIS-Dienst]; V3 (DOI 10.21420/WX2X-H603): 31.623 Anrisspolygone, 26.559 Ablagerungspolygone [S]. Orthofoto 0,3 m, DSM, Lidar [A]. Lizenz: GNS-Haftungsausschluss, keine CC-Angabe. Auslöser Erdbeben (14.11.2016).

### Hongkong ENTLI (4/5)
- https://data.gov.hk/en-data/dataset/hk-cedd-csu-cedd-entli [A]. ~110.500 Features [A]. Felder u. a. Typ (relikt, Kanal, offener Hang, Küste), Breite, Länge, Neigung, Vegetation, **Jahr der ersten Beobachtung** [A]. Luftbild-Interpretation ab 1945, Aktualisierung alle drei Jahre. Nutzungsbedingungen nicht abgerufen. Klein, städtisch überprägt.

### Süd-Kirgisistan (GFZ) (4/5)
- DOI 10.5880/GFZ.1.4.2020.002 [A, Datenbeschreibung]. 1.583 Polygone 1986–2013, 2.500 km², CC BY 4.0. Felder `Year`, `Date_o`, `Date_ref`, `Area`. Halbautomatisch aus NDVI-Zeitreihen; langsame Rutschungen ohne Vegetationsstörung werden nicht erfasst.

### São Sebastião 2023 (4/5)
- https://zenodo.org/records/11120078 [A]. 989 Anrisspunkte, 1.116 Flächenpolygone, 1 Murgang, 7,1 MB, CC BY 4.0. Luftbilder 10 cm. Ein Ereignis, CRS nicht angegeben.

## 5. Bekannte Probleme, die sich durch alle Quellen ziehen

- **Unvollständige Kartierung.** Ein Inventar zeigt nur, was kartiert wurde. Außerhalb des Kartierumrisses (und in verdeckten Bereichen: Wolken, Schatten, Wald) bedeutet „kein Eintrag“ nichts. Nur Datensätze mit Umrissen (Gorkha, SLIDO, RER2023, Fan 2019, Far-Western Nepal) erlauben saubere Kontrollen.
- **Meldebias.** GLC/COOLR, GEORIOS, StorMe, BDMvt, NVE, NZLD, SGC, INGEMMET beruhen auf Medien, Behörden oder Schadensmeldungen: überrepräsentiert sind Straßen, Siedlungen und Schäden. Bei GLC sind Deutschland und die Schweiz durch einen einzelnen Beitragenden überrepräsentiert [A].
- **Gemischte Prozesse.** Sturz/Steinschlag, Einsturz, Erosion, Lawine und Murgang stecken in vielen Inventaren (IFFI, BDMvt, USGS v3, Bijie, NC). Vor jeder Nutzung nach Prozess filtern; nicht alle Typfelder sind belegt.
- **Datum.** Viele Inventare haben nur ein Ereignis- oder Jahresdatum (ENTLI, Far-Western Nepal, Kirgisistan) oder gar keins (SGC, Kalifornien nahezu leer, IFFI lückenhaft). Zeitliche Vorgeschichte lässt sich nur für ereignisbezogene Inventare belastbar aufbauen.
- **Duplikate und abweichende Zählungen.** Gorkha: 24.915 (Roback) gegenüber 47.200 [S] je nach Zählverfahren. Haiti: 4.490 bis 30.828 [S]. Wenchuan: bis zu 197.481 [S] gegenüber ~60.000 [S]. Verschmelzung benachbarter Rutschungen („Amalgamation“) verzerrt Anzahl und Fläche.
- **Erdbeben-Auslöser.** Gorkha, Wenchuan, Kaikōura, Iburi, Haiti, Tanyaş-Sammlung, GDCLD: Die Lage hängt stark von Bebenstärke und Entfernung zur Verwerfung ab. Die Übertragung auf regenbedingte Rutschungen ist unsicher.
- **Ein Ereignis, ein Sturm.** RER2023, Zixing, São Sebastião, Gabrielle: sehr gute Qualität, aber eine einzige Wetterlage; die effektive Stichprobe der unabhängigen Ereignisse ist klein.
- **Mischlizenzen.** CAS Landslide Dataset (Teilsätze unterschiedlich), GDCLD (nur Forschung), UGLC (nicht kommerziell), Marc 2015 (nicht kommerziell), IFFI (drei widersprüchliche Angaben), SLIDO und Haiti (keine Angabe).
- **Modellierte Karten sind keine Inventare.** ELSUS, Gefahrenhinweiskarten (Bayern, Steiermark, Aargau) und Gefährdungskarten dürfen nicht als Ziel dienen: Zirkularität.

## 6. Österreich, Alpen und der Test auf österreichischem Gelände

**Wichtig vorab:** Ein objektiv und flächendeckend kartiertes, offenes Rutschungsinventar für Österreich wurde bisher nicht gefunden. Die nationale Quelle (GeoSphere GEORIOS) ist medienbasiert. Das Talwacht-Projekt arbeitet bereits mit dieser Quelle. Alle weiteren Ereignisdaten Österreichs stehen deshalb für die Auswertung zur Verfügung, aber nicht als unabhängiges Gegenstück.

| Datensatz | Befund |
|---|---|
| GeoSphere GEORIOS | Medienbasiert, unvollständig; 487 Massenbewegungen 2023 bis März 2024 [S]; Gesamtzahl und Geometrie unbekannt |
| Oberösterreich, Ereigniskataster Rutschung (Gefahrenhinweiskarte 2.0) | Offenes Shapefile (CC BY 4.0, EPSG:31255), Stand 2025 [A]; ZIP-Inhalt, Anzahl und Geometrietyp ungeprüft: https://doris-metadaten.ooe.gv.at/at.gv.ooe.doris.geonetwork_extern/srv/api/records/4A987D31-E415-465F-99F5-8982F62E085E |
| Kärnten, Natur- und Umweltereignisse | CC BY Österreich 4.0 [S], Meldedaten, unverifiziert |
| Burgenland Verdachtsflächen, Steiermark Gefährdungspotential | Hinweis- bzw. Modellflächen, als Label ungeeignet |
| **WLV Ereignisse** (Wildbach- und Lawinenverbauung, BMLUK) | Bundesweit, amtlich erfasst (Forsttechnischer Dienst), aber nur schadensbildende Ereignisse im WLV-Bereich. Rutschung ist eine von vier Prozessarten (Wasser, Schnee, Rutschung, Steinschlag). GPKG-ZIP 2.479.812 Bytes [A, HEAD-Abfrage], Lizenz INSPIRE „noConditionsApply“ (keine CC-Angabe). Anzahl, Felder, Datumsfeld und Zeitraum unbekannt. Nach den Jahresberichten ist Rutschung ein kleiner Anteil (2024 „rund 10 %“ von 423–425 Ereignissen, 2025 „5 %“; Erfassung schwankt stark, 2025 unvollständig) [A]. Entscheidungsnötig: https://www.data.gv.at/katalog/datasets/ccca05aa-728d-4218-9f4c-81286c537527. Bew. 3 |
| OÖ „Karte der Phänomene“ (Punkte, Flächen, Linien) | Laut Abstract Sturzblöcke, Rutschung, Übermurung, Anrisse, Abrisskanten; CC BY 4.0, EPSG:31255, Shapefile-ZIP [A]. Anzahl, Felder, Zeitraum unbekannt; vermutlich Geländemerkmale ohne Ereignisdatum. Bew. 3 |
| NÖ Gefahrenhinweiskarte Rutschprozesse (MoNOE) | TIFF-Modellraster, 16.126.774 Bytes, CC BY 4.0 [A]. Modellausgabe, kein Ereignisinventar; höchstens als Prädiktor. Bew. 2 |
| GBA/GeoSphere „Massenbewegungen in Österreich“ | Web-App mit ~100.000 Objekten, nur publizierte oder in Medien erschienene Fälle, „berechtigt zu keiner statistischen Auswertung“ [S]. Der INSPIRE-Punktlayer `NZ_ObservedEvent_Media` (Felder `description`, `hazardCategory`, `validFrom`, `validTo`; keine Fläche; CC BY 4.0) ist die bereits bekannte GEORIOS-Quelle [A]. Bew. 2 |
| Steiermark Rutschungskataster | Datengrundlage des Landesmodells [S]; offener Download nicht belegt. Nur die Modellkarte ist einsehbar. Bew. 2 |
| Tirol, Vorarlberg, Salzburg | Kein offener Rutschungs-Ereignisdatensatz gefunden (data.gv.at ohne Treffer; Landesportale teils nicht erreichbar, Tirol-CKAN 404). Vorarlberg: nur Hinweiskarte Schutzwald (kein Rutschungsdatensatz); BioSLIDE (Schmaltz 2016) ohne belegten Download. Bew. 1 |
| BOKU-Fallstudie, Zenodo 11400480 | „Land Use Legacies in Landslide Modeling – an Austrian Case Study“: Shapefiles, ca. 9,7 MB, CC BY 4.0 [A]. Anzahl, Gebiet und Datum nicht auf der Seite; Inhalt und README prüfen. Bew. 3 (Methodik-Testkandidat) |

Auf data.gv.at ergaben die Suchbegriffe „Hangrutschung“, „Hangbewegung“, „Georisiken“, „Hangmure“ und „Rutschgefährdung“ keine brauchbaren Treffer. Die vollständige Trefferliste (u. a. weitere OÖ-Hinweiskarten Sturz/Einsturz, NÖ Sturzereignisse, HWRL „Vergangene Ereignisse“ als Hochwasserdaten) steht nicht in diesem Dokument; sie enthält nach dem Befund des Agenten kein weiteres Rutschungsinventar.

**Konsequenz:** Der einzige bundesweit amtlich erfasste, offene und neue Kandidat ist WLV Ereignisse; er ist klein, auf Schadensfälle begrenzt und im Inhalt unbekannt. Oberösterreich bietet die besten offenen Flächendaten, ebenfalls mit ungeklärtem Inhalt. Ein belegter objektiver, datierter Rutschungs-Ereignisdatensatz auf Landesebene fehlt. Tirol, Vorarlberg, Salzburg und Steiermark sollten direkt im Browser oder per Anfrage an die Landesgeologie geprüft werden, bevor „nicht vorhanden“ endgültig gilt.

Für den Alpenraum außerhalb Österreichs sind die verwandtesten Quellen:

- **IFFI** (Südtirol, Trentino, Friaul, Lombardei, Piemont).
- **Südtirol IFFI** mit offener Provinz-Schicht (CC BY-SA 3.0, 1:10.000, EPSG:25832). Die Angaben zum Zugang widersprechen sich: Ein Abruf nennt WFS 2.0.0 und WMS über `geoservices1.civis.bz.it/geoserver` [A], ein anderer fand in den Metadaten nur ein WMS und keinen Vektordownload [A]. Vor Nutzung testen.
- **Bayern GEORISK:** Der „Georisiken in Bayern – Downloaddienst“ des LfU ist belegt: CC BY 4.0, Shapefile, EPSG:25832/4258, ganz Bayern, monatlich aktualisiert; enthält Anbruchbereiche, Punktobjekte, Ablagerungsbereiche und Gefahrenhinweisbereiche. Anzahl, Felder und ein Ereignisdatum sind nicht belegt [A]. Dienst-URL: https://www.lfu.bayern.de/gdi/dls/georisiken.xml. Beigemischte Hinweisbereiche sind modelliert und dürfen nicht als Label dienen.
- Die Schweiz bietet keinen offenen Landesdownload.

## 7. Empfehlung

### Womit starten (2–3 Datensätze)

1. **Emilia-Romagna RER2023.** Kleinster Aufwand für das größte Qualitätsplus: 43,6 MB, CC BY 4.0, regeninduziert, objektiv und flächig kartiert, Polygone. Geeignet, um die Kontrollflächenlogik (Gebiet innerhalb der Kartierung, ohne Polygon) und die Geländemerkmale zu erproben. Vorher nach Rutschungs- und Fließtyp filtern.
2. **IFFI, Teilmenge Südtirol/Trentino zuerst.** Alpines Gelände, Maßstab 1:10.000, und der Südtiroler WFS-Zugang ist offen. Lizenzfassung beim Download festhalten, Sturz entfernen, Datumsvollständigkeit je Region prüfen. Erst danach andere Regionen laden.
3. **Gorkha (Roback) oder Far-Western Nepal als Gegenprobe** auf Hangsteilheit und Geologie. Gorkha hat den sauberen CC0-Kartierumriss, Far-Western Nepal ist ein Monsun- statt Erdbebengebiet. Beide dienen als Test, ob die gelernten Geländemuster über Gebirge hinweg tragen. Sen12Landslides ist erst sinnvoll, wenn Sentinel-Eingaben gebraucht werden (171 GB).

### Welches Modell auf Österreich testen

Trainiert auf **IFFI Südtirol/Trentino** (und ggf. RER2023) lässt sich am ehesten sinnvoll in Österreich testen: ähnliches alpines Gelände, grenznah, ähnliche Prozesse (Gleiten, Fließen). Als österreichische Prüfmengen kommen in Frage:

- **Oberösterreich Ereigniskataster Rutschung** (CC BY 4.0), sobald Geometrie, Felder und der Anteil modellierter Flächen am ZIP geklärt sind.
- **Die bereits aufbereiteten GeoSphere-Ereignisse des Talwacht-Projekts** als Vergleich mit Datum. Für sie gilt weiter die Regel aus AGENTS.md Abschnitt 45: Der versiegelte V0.4-Test ist gesehen und darf keine Auswahl mehr steuern; ein Vergleich gilt als explorativ und wird so beschriftet.

Zu erwarten sind Verschiebungen zwischen den Quellen: unterschiedliche Kartiermaßstäbe, Prozessdefinitionen und Vollständigkeit. Eine Aussage über Generalisierung erfordert einen Test **ohne** Auswahl nach Ergebnis und mit Angabe der unabhängigen Einheiten.

### Konsequenz für Talwacht

Das aktuelle Experiment nutzt ein Meldeinventar mit Pseudo-Negativen; V0.4 und V0.5 weisen selbst auf möglichen Meldebias hin. Inventare mit Kartierumriss (RER2023, Gorkha, SLIDO, Fan 2019) erlauben Kontrollen **aus kartierten Gebieten ohne Ereignis**. Das wäre eine objektivere Gegenprobe zum Meldebias. Jede Verwendung wäre eine neue Version mit eigener Konfiguration, vorab registriert (AGENTS.md Abschnitt 45).

## 8. Offene Prüfpunkte vor dem ersten Download

- IFFI: gültige Lizenz, Download-Endpunkt, Attributliste, Datumsabdeckung je Region.
- RER2023: CRS, Geometriefelder, Typklassen nach Datei prüfen.
- Cyclone Gabrielle: DOI und Lizenz bei GNS erfragen. Kaikōura V3: Lizenz auf der Katalogseite klären.
- Zixing: Lizenz und CRS auf Figshare/Zenodo (zenodo.14277611 laut Suchzusatz, ungeprüft).
- USGS v3: Gesamtzahl, Dateigrößen und Kartiergrenzen im Browser prüfen (ScienceBase blockiert Skripte).
- Oregon SLIDO: Lizenz erfragen. Washington DNR: Zugang und Lizenz.
- Oberösterreich ZIP: Geometrie, Felder, Ereignis- gegenüber Modellflächen.
- Bayern GEORISK: Feldschema, Anzahl, Ereignisdatum, Trennung von Beobachtungsobjekten und modellierten Hinweisbereichen.
- WLV Ereignisse (GPKG, 2,5 MB): Anzahl der Rutschungsereignisse, Datumsfeld, Geometrietyp, Zeitraum.
- Südtirol IFFI: ob WFS tatsächlich Vektordaten ausliefert.
- Tirol, Vorarlberg, Salzburg, Steiermark: per Browser oder Anfrage an die Landesgeologie.
- RLBJ Peking: Repository im Artikel suchen. Bhukosh (Indien): Nutzungsbedingungen, sobald das Portal erreichbar ist.
- SilentSlides: Quelle bei der Auftraggeberseite erfragen; unter diesem Namen wurde nichts gefunden.
