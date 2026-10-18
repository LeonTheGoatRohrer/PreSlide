# Murenanfälligkeit Österreich aus allen Inventardaten (anfaelligkeit_at_v01)

**Stand 18.10.2026. Vorab registriert** (`config/anfaelligkeit_at_v01.json`, `PREREGISTRATION.json`; Amendment 1: Skadi = SRTM, Amendment 2: exakte OSM-Abstände und CORINE-Kachelabfrage, beide vor jedem Modell) bevor ein Geländewert, eine Stichprobe oder ein Modell dieser Version entstand. Alle Zahlen stammen aus `results_srtm.json` / `results_skadi.json` und den Gebietstabellen in diesem Ordner.

> Die Werte sind eine **relative Anfälligkeit**: eine Rangfolge von Hangzellen innerhalb eines Gebiets. Sie sind **keine Wahrscheinlichkeit**, dass eine Mure abgeht, keine Gefahrenkarte und keine Warnung. Hintergrund und Verhältnis 1 : 3 sind gewählt, das Inventar ist unvollständig. Modellwichtigkeit ist keine Ursache.

## Frage und Antwort

Lernt ein statisches Modell aus Gelände und Geologie um genau verortete reine Hangmuren anderer österreichischer Gebiete, die Hangmuren eines **ganz zurückgehaltenen Gebiets** besser von Zufallspunkten desselben Gebiets zu unterscheiden als die Neigung allein?

- **Hauptergebnis (SRTM, 12 Prüfgebiete, jedes einmal ganz zurückgehalten):** AUC 0,728 [0,673; 0,780] (Zufall 0,5); nur Neigung 0,592 [0,565; 0,622].
- **Gepaarte Differenz Modell − Neigung: 0,136 [0,095; 0,175]** → **besser als die Neigung allein** (Intervall vollständig über 0).
- Über Zufall: ja (Intervall der mittleren AUC über 0,5).
- Einheiten sind **Gebiete** (Ereignisdokumentationen bzw. feste 50-km-Kacheln), nicht Punkte. Intervalle: 95 %, Bootstrap über Gebiete (2000 Ziehungen, Seed 20261018). Gebiete desselben Unwetters (Vorarlberg/Tirol und Gasen/Haslau August 2005; Nordhälfte und Taxenbach Juni 2013) sind möglicherweise abhängig.

## Daten

GeoSphere-Inventar (Abruf 14.10.2026, 25609 Einträge mit Lage): 3416 reine Hangmuren, davon 2686 genau verortet (≤ 20 m laut Inventar), 311 Duplikate (< 30 m) zusammengefasst → **2375 Kandidaten**. Nicht als Positive verwendet und nur gezählt: „Hangmure bis Lockergesteinsrutschung“ 368, „Hangmure und Lockergesteinsrutschung“ 73, „Hangmure und Rutschung“ 6.

- **SRTM (Hauptlauf):** Höhendaten vom Februar 2000; deshalb nur Ereignisse mit bekanntem Jahr ≥ 2001 (596 ohne Jahr oder älter ausgeschlossen, u. a. Thiersee 1970 und die Luftbildauswertungen ohne Datum). Geländeprüfung (Neigung ≥ 5°, Höhe gültig): 9 wegen Neigung < 5°, 0 ohne gültige Höhe ausgeschlossen. **1770 Positive**, 12 Prüfgebiete (≥ 10 Positive), 29 kleinere Gebiete nur im Training.
- **Skadi (Sensitivität, alle Daten):** alle Positive unabhängig vom Jahr, **2362 Positive**, 26 Prüfgebiete. Amendment 1: Die Skadi-Kacheln sind über Österreich zu 99,3–99,99 % zellidentisch mit SRTM; der Unterschied der beiden Läufe liegt fast nur in der Auswahl der Positive (auch undatierte Luftbildkartierungen und Thiersee 1970).
- **Hintergrund:** je Positiv drei Zufallspunkte im selben Gebiet, in den festen 5-km-Rasterzellen (EPSG:31287), die mindestens ein Positiv des Gebiets enthalten; Neigung ≥ 5°, ≥ 100 m von **jedem** Inventarpunkt (alle Prozesse), ≥ 60 m untereinander. Hintergrundpunkte sind Pseudo-Negative: Hänge ohne dokumentierte Meldung in der Nähe, keine nachweislich stabilen Hänge.
- **Merkmale:** Höhe, Neigung, Exposition (Sinus/Kosinus), Profil- und Plankrümmung, Rauigkeit (TRI), TPI 150/500 m, Hangposition 500 m, Einzugsgebiet und TWI (fehlend, wenn das Einzugsgebiet den 5-km-Rand erreicht), Geologie 1 : 500 000 (5 Klassen). **Keine** Wetter-, Koordinaten-, Jahres-, Infrastruktur- oder Nachbarereignis-Merkmale (Test mit Fehlerinjektion).
- **Prüfung:** Leave-one-area-out; zusätzlich werden alle Trainingspunkte im Umkreis von 1 km um das zurückgehaltene Gebiet entfernt. Modelle ohne Parametersuche (V0.4-Einstellungen), Trainingsgewicht je Gebiet 1/√(Positive), damit 2005 nicht dominiert.

## Ergebnisse SRTM (Hauptlauf)

| Modell | AUC (Mittel über Gebiete) | Differenz zu nur Neigung | Anteil Positive über 80. Perzentil des Hintergrunds | Average Precision |
|---|---|---|---|---|
| Gradient Boosting, Gelände + Geologie | 0,728 [0,673; 0,780] | 0,136 [0,095; 0,175] | 0,482 [0,381; 0,589] | 0,465 [0,400; 0,527] |
| Logistische Regression, Gelände + Geologie | 0,729 [0,667; 0,784] | 0,137 [0,086; 0,187] | 0,539 [0,416; 0,655] | 0,452 [0,385; 0,518] |
| Gradient Boosting, nur Neigung (Basislinie) | 0,592 [0,565; 0,622] | (Referenz) | 0,292 [0,237; 0,350] | 0,313 [0,288; 0,342] |
| Neigung als Rohwert (ohne Training) | 0,558 [0,491; 0,620] | -0,034 [-0,098; 0,027] | 0,248 [0,139; 0,369] | 0,305 [0,249; 0,368] |

Gepoolt über alle zurückgehaltenen Vorhersagen (beschreibend): Modell 0,676, nur Neigung 0,597, Neigung roh 0,566.

Ohne das größte Gebiet (Vorarlberg_Tirol_August_2005): AUC 0,733 [0,678; 0,787], Differenz zu nur Neigung 0,142 [0,103; 0,182].

### Alle Prüfgebiete

AUC je Gebiet: zurückgehaltene Positive gegen zurückgehaltenen Hintergrund. „Modell“ = Gradient Boosting, Gelände + Geologie. Die letzte Spalte rankt nur nach dem Abstand zu Gebäude/Straße (OSM 2026), kein Modellmerkmal.

| Gebiet | Jahr(e) | Positive | Hintergrund | AUC Modell | AUC nur Neigung | Differenz | AUC Neigung roh | AUC log. Regr. | AUC nur Infrastrukturabstand |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Vorarlberg_Tirol_August_2005 | 2005 | 1068 | 3204 | 0,681 | 0,607 | 0,074 | 0,573 | 0,641 | 0,625 |
| Oberkaernten_Ende_Oktober_Anfang_November 2018 | 2018 | 106 | 318 | 0,710 | 0,566 | 0,144 | 0,430 | 0,663 | 0,834 |
| Nordhaelfte_Oesterreich_Juni_2013 | 2013 | 102 | 306 | 0,752 | 0,634 | 0,118 | 0,617 | 0,721 | 0,638 |
| Oesterreich_Sept_2024 | 2024 | 87 | 261 | 0,776 | 0,555 | 0,221 | 0,567 | 0,754 | 0,622 |
| Sellrain_Juni_2015 | 2015 | 74 | 222 | 0,817 | 0,594 | 0,223 | 0,540 | 0,778 | 0,805 |
| Gasen_Haslau_August_2005 | 2005 | 71 | 213 | 0,769 | 0,538 | 0,231 | 0,682 | 0,844 | 0,727 |
| Klingfurth_Juni_2009 | 2009 | 58 | 174 | 0,533 | 0,520 | 0,012 | 0,453 | 0,474 | 0,534 |
| Stanz_im_Muerztal_25_Juli_2016 | 2016 | 46 | 138 | 0,601 | 0,557 | 0,045 | 0,587 | 0,631 | 0,543 |
| Moelltal_November_2019 | 2019 | 32 | 96 | 0,885 | 0,693 | 0,192 | 0,505 | 0,836 | 0,861 |
| Kaernten_Steiermark_August_2023 | 2023 | 19 | 57 | 0,730 | 0,640 | 0,089 | 0,725 | 0,786 | 0,656 |
| Suedwechsel_Juni_2018 | 2018 | 15 | 45 | 0,790 | 0,634 | 0,155 | 0,704 | 0,842 | 0,791 |
| Mautern_Aflenz_Juli 2024 | 2024 | 10 | 30 | 0,697 | 0,568 | 0,128 | 0,313 | 0,783 | 0,887 |

Nur im Training (weniger als 10 Positive): Edelschrott_Juli_2024 (2), Feldbach_August_2020 (3), Feldbach_Juni_August_2009 (3), Gasen_August_2017 (6), Gasen_September_2018 (6), Hartberg_Fuerstenfeld_Juni_2024 (2), Knittelfeld_August_2020 (3), Obdach_Packsattel_Juli_2012 (1), Oberwoelz_August_2017 (9), Pernegg_24_Juli_2016 (4), Pinzgau_Pongau_August_2024 (2), St_Lorenzen_i_P_Juli_2012 (9), Taxenbach_Juni_2013 (5), tile_10_10 (1), tile_10_6 (1), tile_10_7 (1), tile_11_7 (1), tile_12_6 (1), tile_2_8 (2), tile_3_7 (1), tile_6_7 (4), tile_6_8 (2), tile_7_6 (1), tile_7_7 (2), tile_7_8 (1), tile_8_6 (2), tile_8_7 (2), tile_9_7 (3), tile_9_8 (2).

### Worauf sich das Modell stützt (beschreibend)

Mittlerer AUC-Verlust im zurückgehaltenen Gebiet, wenn ein Merkmal zufällig vertauscht wird: Exposition 0,053, Rauigkeit 0,037, Höhe 0,036, Hangposition 500 m 0,030, TPI 500 m 0,013, Neigung 0,007. Das Modell stützt sich auf diese Merkmale; das ist keine Ursache.

## Meldebias-Kontrolle (wie V0.7, explorativ)

- Nur der Abstand zum nächsten Gebäude oder zur nächsten öffentlichen Straße (OSM 2026) als Rangfolge: AUC 0,710 [0,641; 0,778]. Werte über 0,5 heißen: gemeldete Hangmuren liegen näher an Infrastruktur als der Zufallshintergrund (Sichtbarkeit, Erhebungswege, oder echte Nähe von Siedlungen zu Hängen). Der Abstand ist nie ein Modellmerkmal. Die Abstände sind exakt (Amendment 2): der V0.7-Algorithmus ordnet jeden OSM-Knoten nur der nächstgelegenen Probe zu und überschätzt deshalb Abstände dicht beieinander liegender Proben; V0.7 selbst wurde nicht geändert (offener Punkt).
- Nur Punkte ≥ 200 m von Gebäude und Straße (Anteil Positive 0,38, Hintergrund 0,61; 8 Gebiete mit ≥ 5 Positiven und ≥ 5 Hintergrundpunkten): Modell AUC 0,697 [0,602; 0,761], nur Neigung 0,521 [0,479; 0,556], Differenz 0,176 [0,107; 0,241].
- Die meisten Positiven wurden auf Orthofotos kartiert („Ferndiagnose – Orthofoto“). Unter Wald sind Hangmuren schwer zu sehen; deshalb ist Landbedeckung nur eine Zusatzanalyse.

## Landbedeckung (CORINE passend zum Ereignisjahr, explorativ)

Nur Gebiete mit bekanntem Jahr ≥ 2002 und einem Kartenstand vor dem Ereignisjahr (12 Prüfgebiete, also alle SRTM-Prüfgebiete, daher dieselben Proben wie oben; Gasen_Haslau_August_2005: CLC2000, Kaernten_Steiermark_August_2023: CLC2018, Klingfurth_Juni_2009: CLC2006, Mautern_Aflenz_Juli 2024: CLC2018, Moelltal_November_2019: CLC2018, Nordhaelfte_Oesterreich_Juni_2013: CLC2012, Oberkaernten_Ende_Oktober_Anfang_November 2018: CLC2012, Oesterreich_Sept_2024: CLC2018, Sellrain_Juni_2015: CLC2012, Stanz_im_Muerztal_25_Juli_2016: CLC2012, Suedwechsel_Juni_2018: CLC2012, Vorarlberg_Tirol_August_2005: CLC2000). Gleiche Proben, gepaart:

| Modell | AUC (Mittel über Gebiete) | Differenz zu nur Neigung | Anteil Positive über 80. Perzentil des Hintergrunds | Average Precision |
|---|---|---|---|---|
| Gradient Boosting, Gelände + Geologie | 0,728 [0,673; 0,780] | 0,136 [0,095; 0,175] | 0,482 [0,381; 0,589] | 0,465 [0,400; 0,527] |
| Logistische Regression, Gelände + Geologie | 0,729 [0,667; 0,784] | 0,137 [0,086; 0,187] | 0,539 [0,416; 0,655] | 0,452 [0,385; 0,518] |
| Gradient Boosting, + Landbedeckung | 0,766 [0,697; 0,826] | 0,174 [0,119; 0,224] | 0,580 [0,444; 0,694] | 0,544 [0,453; 0,625] |
| Logistische Regression, + Landbedeckung | 0,746 [0,671; 0,811] | 0,154 [0,093; 0,216] | 0,568 [0,430; 0,696] | 0,509 [0,429; 0,580] |
| Gradient Boosting, nur Neigung (Basislinie) | 0,592 [0,565; 0,622] | (Referenz) | 0,292 [0,237; 0,350] | 0,313 [0,288; 0,342] |
| Neigung als Rohwert (ohne Training) | 0,558 [0,491; 0,620] | -0,034 [-0,098; 0,027] | 0,248 [0,139; 0,369] | 0,305 [0,249; 0,368] |

Zusatz durch Landbedeckung: Gradient Boosting 0,038 [0,015; 0,061], logistische Regression 0,017 [-0,014; 0,051]. Ein Vorteil wäre wegen der Orthofoto-Kartierung teilweise Sichtbarkeit.

## Datumsregel Gelände

Entscheidung des Nutzers vom 18.10.2026: Es zählt die Herkunft der Höhendaten, nicht das Dateidatum. SRTM wurde im Februar 2000 aufgenommen und liegt damit vor jedem Ereignis ab 2001. Lücken in SRTMGL1 v3 sind aus späteren Quellen gefüllt (kleiner Anteil steiler Zellen). SRTM ist ein Oberflächenmodell (Wald, Gebäude) und glatter als ein Laserscan-Geländemodell; Hangmuren sind meist kleiner als eine 30-m-Zelle. Amendment 1: Die seit V0 verwendeten Skadi-Kacheln sind über Österreich praktisch SRTM (99,3–99,99 % identische Zellen); auch alle früheren Talwacht-Geländemerkmale beruhen also auf SRTM-Höhen.
Beschreibend: Gebiete mit Ereignisjahr ≥ 2017 (Kaernten_Steiermark_August_2023, Mautern_Aflenz_Juli 2024, Moelltal_November_2019, Oberkaernten_Ende_Oktober_Anfang_November 2018, Oesterreich_Sept_2024, Suedwechsel_Juni_2018) mittlere Differenz Modell − Neigung 0,155, übrige 0,117.

## Sensitivität: alle Inventardaten (Skadi-Lauf)

26 Prüfgebiete, Hauptmodell AUC 0,682 [0,641; 0,723], Differenz zu nur Neigung **0,092 [0,055; 0,128]** → besser als die Neigung allein. Herkunft der Höhendaten für undatierte und vor 2000 liegende Ereignisse nicht nachweislich davor; deshalb nie Hauptergebnis.

| Modell | AUC (Mittel über Gebiete) | Differenz zu nur Neigung | Anteil Positive über 80. Perzentil des Hintergrunds | Average Precision |
|---|---|---|---|---|
| Gradient Boosting, Gelände + Geologie | 0,682 [0,641; 0,723] | 0,092 [0,055; 0,128] | 0,438 [0,370; 0,507] | 0,431 [0,385; 0,480] |
| Logistische Regression, Gelände + Geologie | 0,703 [0,663; 0,738] | 0,113 [0,079; 0,147] | 0,475 [0,407; 0,546] | 0,438 [0,396; 0,481] |
| Gradient Boosting, nur Neigung (Basislinie) | 0,590 [0,557; 0,622] | (Referenz) | 0,286 [0,229; 0,341] | 0,328 [0,299; 0,358] |
| Neigung als Rohwert (ohne Training) | 0,578 [0,535; 0,615] | -0,012 [-0,054; 0,028] | 0,248 [0,182; 0,316] | 0,317 [0,281; 0,355] |

### Alle Prüfgebiete (Skadi-Lauf)

| Gebiet | Jahr(e) | Positive | Hintergrund | AUC Modell | AUC nur Neigung | Differenz | AUC Neigung roh | AUC log. Regr. | AUC nur Infrastrukturabstand |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Vorarlberg_Tirol_August_2005 | 2005 | 1068 | 3204 | 0,703 | 0,621 | 0,082 | 0,573 | 0,666 | 0,625 |
| tile_2_7 | undatiert | 202 | 606 | 0,721 | 0,622 | 0,099 | 0,550 | 0,661 | 0,545 |
| Oberkaernten_Ende_Oktober_Anfang_November 2018 | 2018 | 106 | 318 | 0,726 | 0,537 | 0,189 | 0,430 | 0,662 | 0,834 |
| Nordhaelfte_Oesterreich_Juni_2013 | 2013 | 102 | 306 | 0,771 | 0,656 | 0,115 | 0,617 | 0,741 | 0,638 |
| Oesterreich_Sept_2024 | 2024 | 87 | 261 | 0,692 | 0,549 | 0,142 | 0,567 | 0,747 | 0,622 |
| Thiersee_1970 | 1970 | 84 | 252 | 0,456 | 0,541 | -0,084 | 0,575 | 0,533 | 0,701 |
| Sellrain_Juni_2015 | 2015 | 74 | 222 | 0,824 | 0,551 | 0,272 | 0,540 | 0,807 | 0,805 |
| Gasen_Haslau_August_2005 | 2005 | 71 | 213 | 0,772 | 0,593 | 0,179 | 0,682 | 0,838 | 0,727 |
| tile_3_7 | 2026 + 58 undatiert | 59 | 177 | 0,790 | 0,635 | 0,154 | 0,537 | 0,776 | 0,658 |
| Klingfurth_Juni_2009 | 2009 | 58 | 174 | 0,483 | 0,444 | 0,040 | 0,453 | 0,446 | 0,534 |
| Stanz_im_Muerztal_25_Juli_2016 | 2016 | 46 | 138 | 0,593 | 0,582 | 0,012 | 0,587 | 0,654 | 0,543 |
| tile_8_7 | 2024 + 32 undatiert | 34 | 102 | 0,624 | 0,372 | 0,252 | 0,681 | 0,681 | 0,519 |
| Moelltal_November_2019 | 2019 | 32 | 96 | 0,878 | 0,709 | 0,169 | 0,505 | 0,828 | 0,861 |
| tile_5_7 | undatiert | 32 | 96 | 0,710 | 0,593 | 0,116 | 0,608 | 0,744 | 0,684 |
| tile_6_7 | 2022, 2024 + 24 undatiert | 28 | 84 | 0,602 | 0,654 | -0,053 | 0,639 | 0,575 | 0,505 |
| tile_3_8 | undatiert | 26 | 78 | 0,656 | 0,635 | 0,021 | 0,594 | 0,673 | 0,612 |
| tile_8_6 | 2023, 2024 + 23 undatiert | 25 | 75 | 0,709 | 0,512 | 0,197 | 0,632 | 0,741 | 0,692 |
| Kaernten_Steiermark_August_2023 | 2023 | 19 | 57 | 0,782 | 0,656 | 0,126 | 0,725 | 0,798 | 0,656 |
| tile_11_6 | undatiert | 19 | 57 | 0,604 | 0,669 | -0,065 | 0,640 | 0,716 | 0,673 |
| Suedwechsel_Juni_2018 | 2018 | 15 | 45 | 0,804 | 0,659 | 0,145 | 0,704 | 0,787 | 0,791 |
| tile_6_8 | 2021 + 10 undatiert | 12 | 36 | 0,738 | 0,733 | 0,006 | 0,725 | 0,808 | 0,692 |
| tile_4_7 | undatiert | 11 | 33 | 0,736 | 0,664 | 0,072 | 0,551 | 0,818 | 0,658 |
| tile_9_7 | 2022, 2024, 2026 + 8 undatiert | 11 | 33 | 0,532 | 0,504 | 0,028 | 0,485 | 0,653 | 0,782 |
| Mautern_Aflenz_Juli 2024 | 2024 | 10 | 30 | 0,680 | 0,535 | 0,145 | 0,313 | 0,693 | 0,887 |
| tile_10_6 | 2023 + 9 undatiert | 10 | 30 | 0,633 | 0,655 | -0,022 | 0,717 | 0,640 | 0,407 |
| tile_10_7 | 2024 + 9 undatiert | 10 | 30 | 0,513 | 0,455 | 0,058 | 0,390 | 0,587 | 0,650 |

## Demogebiet

Nach der registrierten Regel: Prüfgebiet mit den meisten Positiven = **Vorarlberg_Tirol_August_2005**; darin der 9-km-Block mit den meisten Positiven (150). Die Rasterebene stammt aus dem Modell, das dieses Gebiet **nicht** im Training hatte, und zeigt Perzentilränge innerhalb des Blocks. Beschreibend: In den obersten 20 % der Blockfläche liegen 0,50 der dokumentierten Hangmuren des Blocks (nur Neigung: 0,25; Flächenanteil 0,20). Ein Block, nach Ereigniszahl gewählt: keine eigene Prüfung.

## Grenzen

- Inventarpunkte markieren nicht, ob Anriss, Weg oder Ablagerung gemeint ist; 30-m-Zellen sind gröber als viele Hangmuren.
- Die Gebiete sind vor allem dort, wo kartiert wurde; Hintergrund aus nicht kartierten Hängen zählt als „ohne Meldung“.
- Prüfgebiete sind wenige und ungleich groß; Gebiete desselben Unwetters sind nicht unabhängig.
- Alle Nebenanalysen sind explorativ; gezählt wurden die Hauptdifferenz und die 11 registrierten Nebenanalysen, alle berichtet.
- Keine Wahrscheinlichkeit, kein Risiko, keine Warnung, keine Gefahrenkarte.

## Tests

`tests/test_anfaelligkeit_at_v01.py`; 17 eingebaute Fehler, davon 17 von den Tests erkannt (`mutation_tests.json`).
