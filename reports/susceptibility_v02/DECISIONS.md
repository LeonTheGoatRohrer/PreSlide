# susceptibility_v02 – Phase 0: Vorregistrierung auslöserspezifischer Anfälligkeitsmodelle

**Stand: 18.10.2026, vor jedem v02-Download, jeder v02-Stichprobe, jedem Geländewert eines neuen Inventars und jedem Modell.** Maschinenlesbar: `config/susceptibility_v02.json` (nach der Registrierung schreibgeschützt), Prüfsumme in `PREREGISTRATION.json`, Datenlage in `phase0_data_audit.json`. Regeln im Code: `preslide/susceptibility/v02.py`. v01-Dateien werden nicht verändert.

## Warum eine neue Version

susceptibility_v01 ist am Phase-4-Gate gestoppt: Ein gemeinsames Geländemodell überträgt zwischen Gorkha (Erdbeben) und Far-Western Nepal (Monsun) nicht belegbar mehr als die Neigung (+0,006 AUC [−0,005; +0,017]). Die explorative Ursachenanalyse zeigte, dass die Hangposition ihr Vorzeichen umkehrt (TPI-AUC 0,568 gegenüber 0,461) und der Feuchteindex nur im Erdbebeninventar trennt (TWI-AUC 0,347 gegenüber 0,455). Diese Ergebnisse sind gesehen. Eine Änderung des Designs ist deshalb eine neue Version mit eigener Vorregistrierung (AGENTS.md Abschnitt 45), keine Nachbesserung von v01.

## Hypothese

> Die Geländeanfälligkeit unterscheidet sich zwischen erdbeben- und regenausgelösten Rutschungen. Ein Geländemodell überträgt auf ein neues Inventar desselben Auslösers besser als die Neigung allein und besser als ein Geländemodell, das auf dem anderen Auslöser trainiert wurde.

**Gesehene Daten erzeugen keine Bestätigung.** Gorkha und Far-Western Nepal haben die Hypothese hervorgebracht. Bestätigend sind deshalb nur Tests auf den beiden Inventaren, die in v01 nie modelliert wurden: **Iburi 2018** (Erdbeben) und **RER2023** (Regen). Die Gegenrichtungen (Test auf Gorkha bzw. Far-Western Nepal) werden gerechnet, aber als „Testinventar in v01 gesehen“ gekennzeichnet.

## Was bei der Registrierung bekannt war

- Alle v01-Ergebnisse (Phase 4, Block-CV, Ursachenanalyse), darunter Gelände- und Merkmalsverteilungen von Gorkha und Far-Western Nepal.
- RER2023: Attribute, Anzahlen und Flächenquantile aus dem v01-Phase-1-Audit; kein Geländewert, keine Stichprobe.
- Iburi und Wenchuan (in v01 als Kandidaten geladen): Dateiliste, Geometrietyp, Anzahl, Begrenzungsrechteck, KBS, Feldnamen, Metadatentext, Abgleich der Einzugsgebiets-Kennungen. **Kein Geländewert, keine Flächen- oder Lageverteilung der Rutschungen, kein Modell.**
- USGS-Ereignis-API: ShakeMap-Produkte für Gorkha und Iburi (Quelle, Version, Zeitstempel, Dateigröße). Nichts heruntergeladen.

## Datenlage je Auslöser (Kern der Phase 0)

| Auslöser | Inventar | Lizenz am Original | Unabhängiger Kartierumriss | Status |
|---|---|---|---|---|
| Erdbeben | Gorkha 2015 | CC0 1.0 | ja (`MappingExtent20170209.shp`, 28.345 km², verdeckte Flächen) | Entwicklung (in v01 gesehen) |
| Erdbeben | Iburi 2018 (Zhang et al., Zenodo 2577300) | CC BY 4.0 | **nein** | `pending_extent` |
| Regen | Far-Western Nepal | CC BY 4.0 | ja (AOI, 6.409 km²) | Entwicklung (in v01 gesehen) |
| Regen | RER2023 | CC BY 4.0 | **nein** | `pending_extent` |
| (Erdbeben, geprüfte Alternative) | Wenchuan, Fan et al. 2019 | CC BY 4.0 | **nein** | `excluded` |
| – | IFFI Südtirol | CC BY-SA 3.0 | – | versiegelt (v01), von v02 nie gelesen |

**Ergebnis: Derzeit kann keiner der beiden Auslöser mit zwei Inventaren besetzt werden.** Je Auslöser fehlt der Kartierumriss des zweiten Inventars. Phase 1 kann erst beginnen, wenn mindestens ein Umriss beschafft ist; dafür braucht es eine Anfrage, die der Nutzer stellt.

### Iburi 2018

Das Archiv enthält Rutschungspolygone (5.625, JGD2000/UTM 54N), Altrutschungen (1.649), reaktivierte Altrutschungen (110), vier AMeDAS-Regenstationen und drei Standardabweichungsellipsen. Die Ellipsen sind eine Statistik der Rutschungsverteilung (1 bis 3 Standardabweichungen um den Schwerpunkt) und damit **aus den Polygonen abgeleitet**: Hintergrund darin läge per Konstruktion dort, wo Rutschungen sind. Die Datensatzbeschreibung nennt ein „Untersuchungsgebiet“ ohne Datei; Literaturangaben zur betroffenen Fläche schwanken zwischen etwa 400 und über 700 km², weil jede Studie eigene Grenzen zieht.

Zulässige Beschaffungswege, in dieser Reihenfolge, vor jedem Geländewert:
1. Umriss oder Untersuchungsgebietsgrenze von den Autoren (Zhang, Wang; Shimane University).
2. Der Interpretationsbereich des GSI-Datensatzes D1-No.991 (Luftbilder 6.–11.09.2018, GeoJSON 1,1 MB, GSI-Nutzungsbedingungen mit Quellenangabe), **nur wenn das GSI-Archiv ihn selbst als Daten enthält**. Dann ersetzen die GSI-Polygone die Zenodo-Polygone, weil Inventar und Umriss aus derselben Kartierung stammen müssen. Die Webseite beschreibt keinen solchen Bereich; das Archiv wird erst nach der Registrierung geprüft.

ShakeMap: Ereignis `us2000h8ty` (M 6,6, 05.09.2018 18:07:59 UTC), Produkt `atlas` Version 1, `grid.xml` 14.484.026 B.

### RER2023

Der Zenodo-Datensatz enthält nur `RER2023_V1.shp`. Der ESSD-Artikel sagt, die Fläche sei nach Gemeindegrenzen aufgeteilt worden und umfasse über 6.000 km², nennt aber weder die Gemeinden noch eine Grenzdatei. Die regionale INSPIRE-Schicht der Flächen mit Schutzmaßnahmen nach den Rutschungen vom Mai 2023 ist aus den Rutschungen abgeleitet und **kein** Kartierumriss.

Zulässige Wege: (1) Umrissdatei von den Autoren (Korrespondenz: A. Corsini, Universität Modena und Reggio Emilia) oder der Region Emilia-Romagna; (2) eine von Autoren oder Region veröffentlichte Liste der kartierten Gemeinden, kombiniert mit amtlichen ISTAT-Gemeindegrenzen 2023. Ein Umriss aus Hülle, Puffer oder Auswahl von Gemeinden nach enthaltenen Rutschungen ist verboten.

### Wenchuan (geprüft, ausgeschlossen)

Als Ersatz für Iburi geprüft. `DF_Catchments.shp` enthält 252 Murgang-Einzugsgebiete mit Kennungen wie „B45“; die Rutschungsschichten tragen ganzzahlige Kennungen 1–43. Es gibt keine Zuordnung, und die 42 kartierten Einzugsgebiete (471 km² laut Artikel) sind nicht als Umriss veröffentlicht. 65 Einzugsgebiete schneiden das Begrenzungsrechteck der Kartierung von 2008. Sie über die Lage der Rutschungen auszuwählen hieße, den Umriss aus den Polygonen abzuleiten. **Kein Ersatzinventar in v02.** Ein Wechsel nach Ansicht der Daten wäre eine neue Version.

## Entscheidungen

| Punkt | Entscheidung | Begründung |
|---|---|---|
| Namensraum | `config/susceptibility_v02.json`, `preslide/susceptibility/v02.py`, `data/susceptibility_v02/`, `models/susceptibility_v02/`, `reports/susceptibility_v02/` | v01-Module (`registry.py`, `paths.py`) sind in der v01-Registrierung gehasht und bleiben unverändert; v02 nutzt deren Amendment- und Hashfunktionen. |
| Rohdaten | v01-Rohdaten (Gorkha, Far-Western Nepal, RER2023, Iburi-Kandidat) werden nur gelesen | Prüfsummen liegen in der v01-Herkunft vor; kein erneuter Download. |
| Kartierumriss | nur unabhängig definiert (Datei des Anbieters/der Autoren oder benannte Verwaltungs-/Einzugsgebietseinheiten mit amtlichen Grenzen) | Hintergrund in einem aus Rutschungen abgeleiteten Gebiet misst nicht Anfälligkeit, sondern Nähe zu Rutschungen. |
| Erdbebenmodell | Histogram Gradient Boosting auf 12 Geländemerkmalen + log10(PGA in % g) aus USGS-ShakeMap | Auftrag; die Erschütterung erklärt in Gorkha vermutlich einen Teil des Höhen-/Reliefsignals. PGA ist modelliert (~1 km), keine Messung, und nicht aus Rutschungsdaten abgeleitet. |
| Regenmodell | Histogram Gradient Boosting auf denselben 12 Geländemerkmalen | Kein brauchbares Auslöserfeld: RER2023 ist ein Ereignis, Far-Western Nepal nur jahresdatiert. |
| Hyperparameter | unverändert aus v01 Amendment 3, keine Abstimmung, keine weitere Modellfamilie | Keine Auswahl am Test möglich; der in v01 bessere Random Forest wird nicht nachträglich zum Primärmodell. |
| Gelände | Merkmale und Parameter aus v01 Amendment 2, NASADEM (Feb. 2000, vor allen Ereignissen) | Vergleichbarkeit mit v01; v01-Geländeblöcke dürfen bei gültiger Prüfsumme wiederverwendet werden. |
| Positive Iburi | Zenodo-Polygone ohne Anrissfläche → oberstes Höhendrittel; Polygone, die Altrutschungen schneiden, nur als Ausschlussfläche | Gleiche Logik wie das Datumsfilter in Far-Western Nepal: Das DEM enthält die alte Narbe bereits. |
| Positive RER2023 | alle `ClassNew`-Klassen (Gleit- und Fließtypen); Phase 1 bestätigt am Artikel, dass keine Sturz-/Kippklasse dabei ist | Kein Prozessfilter nach Ergebnis; dieselbe Kleinpolygonregel wie v01. |
| Puffer | v01-Regel über alle v02-Entwicklungsinventare, Wert per Amendment 1 nach Phase 1 | Daten erst nach Phase 1 vollständig. |
| Verhältnis | 1 : 1 | Wie v01; Stichprobenparameter, keine Häufigkeit. |
| Seeds | 301–304 | Neue Version, eigene Ziehungen. |
| Südtirol | bleibt versiegelt; v02 hat keinen Blindtest und kann den Ordner nicht lesen (`readable` verweigert, getestet) | Auftrag. |

## Design, Hypothesentests und Gates

**Design:** Leave-one-inventory-out innerhalb jedes Auslösers, beide Richtungen. Bestätigend ist nur die Richtung Gorkha → Iburi bzw. Far-Western Nepal → RER2023. Unsicherheit: Block-Bootstrap über 5-km-Blöcke des Testinventars (2.000), Nullreferenz durch Permutation innerhalb der Blöcke (500). Unabhängige Einheiten (Blöcke) stehen neben jeder Zahl; jedes Testinventar ist ein einzelnes Ereignis.

**Vier bestätigende Tests** (Bonferroni: bestanden, wenn das 0,625. Perzentil der gepaarten Bootstrap-Differenz über 0 liegt; das 95-%-Intervall wird daneben berichtet):

| Test | Vergleich auf dem neuen Inventar | Bedeutung |
|---|---|---|
| H1-Erdbeben | Gelände + PGA (trainiert auf Gorkha) − logistisch Neigung + PGA | Gelände trägt über Neigung und Erschütterung hinaus |
| H1-Regen | Gelände (trainiert auf Far-Western Nepal) − Neigung allein | Gelände trägt über Neigung hinaus |
| H2-Erdbeben | Gelände trainiert auf Gorkha − Gelände trainiert auf Far-Western Nepal | gleicher Auslöser schlägt anderen Auslöser |
| H2-Regen | Gelände trainiert auf Far-Western Nepal − Gelände trainiert auf Gorkha | gleicher Auslöser schlägt anderen Auslöser |

**Schlussregel:** Die auslöserspezifische Hypothese gilt für einen Auslöser nur, wenn H1 und H2 dieses Auslösers bestehen. Kein anderes Modell, Merkmal oder Split ersetzt einen gescheiterten Test; ein Scheitern führt zur Ursachenanalyse.

**Sekundär (gezählt, nicht bestätigend):** H3 Vorzeichen der Hangposition (TPI-AUC > 0,5 auf Iburi, < 0,5 auf RER2023, je 95-%-Intervall ohne 0,5); H4 PGA-Zuwachs (Gelände + PGA − Gelände) auf Iburi; alle Gegenrichtungen; Baselines Neigung allein, PGA allein; Zusatzmaße wie in v01.

**Gates:**

| Phase | Gate |
|---|---|
| 0 | Diese Registrierung mit Prüfsumme committet, vor jedem v02-Download und jedem Modell |
| 1 | Je Auslöser: beide Inventare mit Lizenz am Original und unabhängigem Kartierumriss; Erdbeben zusätzlich ShakeMap für beide Ereignisse über den ganzen Umriss. Ein Auslöser ohne zweites Inventar wird nicht modelliert und nicht ersetzt; scheitern beide, endet v02 nach Phase 1. **Bei der Registrierung für beide Auslöser nicht erfüllt.** |
| 2 | KBS-, Zirkular-, PGA-Interpolations- und Leckagetests bestehen und schlagen bei eingebautem Fehler an |
| 3 | Puffer-, Umriss- und Mindestabstandstests bestehen; jede Ziehung aus dem Seed reproduzierbar |
| 4 | H1/H2 je Auslöser nach der Bonferroni-Regel |

## Vorab registrierte Sensitivität: Gorkha mit 20-km-Blöcken

Frage: Wie viel des v01-Vorteils innerhalb Gorkhas (+0,122 gegenüber Neigung bei 5-km-Blöcken) ist räumliche Nähe zur Zone starker Erschütterung? Räumliche Block-CV in Gorkha mit **20-km-Blöcken**, 5 Falten, 1 km Abstand; dieselbe CV mit 5-km-Blöcken wird in v02 mit identischem Code und identischen Stichproben wiederholt, damit der Vergleich gepaart ist. Modelle: Gelände gegen Neigung sowie Gelände + PGA gegen Neigung + PGA. Bootstrap über 20-km-Blöcke; unter 25 Blöcken mit Positiven gilt das Intervall als instabil.

Deutung vorab festgelegt: Liegt die 20-km-Differenz (Gelände − Neigung) unter der Hälfte der 5-km-Differenz oder schließt ihr 95-%-Intervall die Null ein, beruht ein großer Teil des Gorkha-Vorteils auf räumlicher Nähe (Erschütterungs-Stellvertreter). Schrumpft der Vorteil mit PGA (Gelände + PGA gegenüber Neigung + PGA) auf weniger als die Hälfte, erklärt die modellierte Erschütterung ihn weitgehend. Gorkha ist gesehen: Die Sensitivität ist explorativ und kein Gate. Sie braucht kein zweites Inventar und kann nach Phase 1 unabhängig von Iburi laufen, sobald die ShakeMap für Gorkha geladen ist.

## Verboten

Südtirol öffnen; Modell, Hyperparameter, Merkmale oder Splits nach einer v02-Ausgabe ändern; Gorkha- oder Far-Western-Nepal-Ergebnisse als Bestätigung ausgeben; Kartierumrisse aus Rutschungspolygonen ableiten; zufällige Pixel- oder Polygon-Splits.

## Nächste Schritte (Nutzerentscheidung)

1. **Umrisse anfragen** (der Nutzer sendet, der Agent entwirft auf Wunsch): RER2023 bei A. Corsini oder der Region Emilia-Romagna; Iburi bei Zhang/Wang (Shimane University).
2. Nach Freigabe: GSI-Archiv D1-No.991 (1,1 MB) laden und prüfen, ob es einen Interpretationsbereich enthält.
3. Unabhängig davon möglich: ShakeMap Gorkha laden und die 20-km-Sensitivität rechnen (explorativ).

## Nachweis der Schutztests

`tests/test_susceptibility_v02.py`: 30 Tests (1 übersprungen vor der Registrierung: Prüfsummenvergleich). `scripts/mutation_check_susceptibility_v02.py` schaltet 18 Regeln einzeln ab (Auslösertrennung, gesehener Testsatz, Umrisspflicht, Lizenz, DEM-Tagesgrenze, ShakeMap-Pflicht, Bonferroni, Trainingsliste, Gegenauslöser-Referenz, Konfigurationshash, Schreibschutz, Leseverbot Südtirol). Jeder Mutant lässt mindestens einen Test scheitern: `mutation_check.json`, Status PASS.

---

## Nachtrag 18.10.2026: Phase 1 – GSI-Prüfung (Iburi) und Gorkha-Sensitivität

Dieser Nachtrag wurde nach der Registrierung angefügt. Die Prüfsumme dieser Datei in `PREREGISTRATION.json` bezieht sich auf den Stand ohne Nachtrag. Die Konfiguration ist unverändert; Designänderungen stehen nur in `AMENDMENT_1.json`. Der Nutzer hat genau zwei Downloads freigegeben: das GSI-Archiv D1-No.991 und die Gorkha-ShakeMap `grid.xml`.

### Iburi: Das GSI-Archiv enthält den Interpretationsbereich als Daten

`phase1_iburi_gsi_check.json` (nur Ebenen- und Metadaten, Anzahlen; kein Geländewert, keine Stichprobe):

- Archiv: 1.179.719 B, SHA-256 `5353f224…`. Vier Dateien mit cp932-Namen; die Mitgliederprüfung ist bestanden.
- `…_判読範囲.geojson`: der Interpretationsbereich. Eine von GSI gezeichnete, geschlossene, einfache Linie (LineString) mit 1.802 Stützpunkten. Die Fläche ist der Ring selbst, 1.357,6 km² in EPSG:32654. Es wird nichts abgeleitet, gepuffert oder ergänzt; eine offene Linie würde verweigert (getestet).
- `…_雲による未判読範囲.geojson`: 10 wegen Wolken nicht interpretierte Flächen, 1,65 km², alle im Bereich. Dort wird kein Hintergrund gezogen.
- `…_斜面崩壊・堆積範囲.geojson`: 3.307 Polygone (CRS84). Davon 3.306 im gemeinsamen Stil, alle im Bereich, eine ungültige Geometrie. Ein abweichend gestaltetes Objekt (schwarz, Linie unsichtbar, ca. 830 m²) ist nur Ausschlussfläche. Abriss und Ablagerung sind laut Haftungshinweis gemeinsam kartiert; deshalb gilt die Regel „oberstes Höhendrittel“.
- Der Haftungshinweis nennt Luftbilder vom 6.–11.09.2018 und keine Geländeprüfung.

**Entscheidung (Amendment 1, vor jeder v02-Stichprobe, jedem v02-Merkmal und jedem Modell):** Iburi wechselt auf den registrierten Ersatzweg 2. Positive und Umriss stammen aus der GSI-Kartierung; die Zenodo-Polygone werden nicht mehr verwendet. `old_landslides.shp` (Zenodo) bleibt wie registriert reine Ausschlussfläche. Rolle `development`, Arbeits-KBS EPSG:32654. Lizenz: GSI-Nutzungsbedingungen mit Quellenangabe.

Iburi bleibt der bestätigende Testsatz des Erdbebenarms. Es gibt noch keinen Iburi-Geländewert, keine Stichprobe und kein Modell.

**Phase-1-Gate:**

- Erdbeben: noch offen. Es fehlen die Iburi-ShakeMap (`us2000h8ty`, 14.484.026 B; Download nicht freigegeben) über den ganzen Umriss und das Puffer-Amendment. Das Puffer-Amendment trägt jetzt die nächste freie Nummer statt „Amendment 1“. Erst danach dürfen Iburi-Stichproben gezogen werden.
- Regen: weiter nicht erfüllt, RER2023 bleibt `pending_extent`.

Offener Prüfpunkt für Phase 1: Die Zenodo-Altrutschungen stammen aus einer anderen Kartierung, deren Abdeckung den GSI-Bereich möglicherweise nicht ganz deckt (Begrenzungsrechteck beginnt bei 42,58° N, der GSI-Bereich bei 42,54° N). Die Abdeckung wird vor dem Puffer-Amendment gezählt und berichtet.

### Gorkha: vorab registrierte 20-km-Sensitivität (explorativ)

ShakeMap Gorkha: Version 1, atlas, process_timestamp 2020-06-03T05:37:03, updateTime 1594162031303, `grid.xml` 14.875.206 B (= Registrierung), SHA-256 `3ffbe249…`. Werte eingefroren in `data/susceptibility_v02/raw/shakemap_gorkha_2015/provenance.json`. PGA an allen 48.074 v01-Stichproben, 0 außerhalb des Gitters.

| Differenz der ROC AUC | 5-km-Blöcke | 20-km-Blöcke |
|---|---|---|
| EQ_TERRAIN − slope_only | +0,124 [0,113; 0,136] | +0,120 [0,096; 0,142] |
| EQ_TERRAIN_PGA − slope_pga_logistic | +0,062 [0,055; 0,069] | +0,055 [0,041; 0,071] |

Die Mindestens-25-Blöcke-Regel ist erfüllt: Positive liegen in 575 bzw. 76 Blöcken.

Deutungsregel:

1. Räumliche Nähe erklärt **keinen** großen Teil. Die 20-km-Differenz ist 97 % der 5-km-Differenz; ihr Intervall enthält die Null nicht.
2. „Weitgehend durch modellierte Erschütterung erklärt“ ist formal **nicht** erfüllt, aber nur knapp. Mit PGA bleiben 50,1 % des Vorteils, die Schwelle liegt bei unter 50 %. PGA halbiert den Vorteil also fast genau.

Explorativ, ein Ereignis, keine Übertragbarkeitsaussage. Bericht: `SENSITIVITY_GORKHA_20KM.md`.

### Nächste Schritte

1. Download der Iburi-ShakeMap freigeben, dann Abdeckung prüfen.
2. Abdeckung der Altrutschungen zählen.
3. Puffer-Amendment schreiben (registrierte v01-Regel über alle v02-Entwicklungsinventare).
4. Iburi-Gelände und -Stichproben (Phase 2/3).
5. H1/H2 für den Erdbebenarm.

Der Regenarm wartet weiter auf einen Umriss für RER2023.

---

## Nachtrag 2, 18.10.2026: Iburi-ShakeMap, Altrutschungen, Puffer – Phase-1-Gate Erdbeben erfüllt

Der Nutzer hat den Download der Iburi-ShakeMap freigegeben. Zahlen: `phase1_iburi_extent_counts.json` (nur Anzahlen und Polygonflächen; kein Geländewert, keine Stichprobe).

- **ShakeMap Iburi:** `us2000h8ty`, atlas, Version 1, process_timestamp 2020-06-05T21:31:12, `grid.xml` 14.484.026 B (= Registrierung), SHA-256 `e1ff18e3…`. Alle 1.802 Stützpunkte des GSI-Bereichs liegen im Gitter und haben einen Wert. Das Produkt rechnet mit einer Punktquelle (465 Stationen); auch das ist ein Modellwert, keine Messung am Hang.
- **Altrutschungen (Zenodo, andere Kartierung):** Für diese Kartierung gibt es keinen Umriss. Ihr Begrenzungsrechteck lässt 253 km² (18,6 %) des GSI-Bereichs offen. Dort liegen nur 2 der 3.306 GSI-Polygone. 129 GSI-Polygone berühren Altrutschungen; sie sind keine Positiven, sondern nur Ausschlussfläche. Damit bleiben **3.177 Positive**. Alle 110 reaktivierten Rutschungen liegen in der Altrutschungsschicht. Die registrierte Regel bleibt unverändert. Die Grenze wird dokumentiert: Im offenen Teil kann Hintergrund auf nicht kartierten Altnarben liegen, und innerhalb des Rechtecks ist die Vollständigkeit angenommen, nicht belegt.
- **Puffer (Amendment 2, registrierte Regel):** Das 90. Perzentil des Äquivalenzradius beträgt Gorkha 17,47 m, Far-Western Nepal 93,54 m (beide aus v01 Amendment 1, identische Positivdefinition) und Iburi 87,11 m. Das Maximum, auf 10 m aufgerundet, ergibt **100 m** (Untergrenze 60 m, Obergrenze 300 m nicht erreicht). RER2023 ist nicht enthalten; sein vorläufiger v01-Wert (26,1 m) läge darunter.
- Die Stufenprüfung des Amendment-Skripts wurde vor Amendment 2 präzisiert. Gesperrt sind v02-Stichproben, v02-Geländeblöcke und Modelle. PGA-Merkmal und Vorhersagen der Gorkha-Sensitivität beruhen auf den v01-Stichproben und hängen von keinem Stichprobenparameter ab.

**Phase-1-Gate:**

- **Erdbeben erfüllt:** Beide Inventare haben eine Lizenz am Original und einen unabhängigen Umriss, und beide ShakeMaps decken den ganzen Umriss ab.
- **Regen nicht erfüllt:** RER2023 bleibt `pending_extent`. Dieser Arm wird weder modelliert noch ersetzt.
- Die Bonferroni-Korrektur bleibt wie registriert über 4 Tests. H1/H2-Regen werden als „nicht durchführbar“ berichtet, nicht gestrichen.

**Nächster Schritt (Phase 2):** Iburi-Geländeblöcke mit dem v01-Code in EPSG:32654 rechnen. Zuerst die DEM-Abdeckung prüfen; das braucht NASADEM-Kacheln um 42–43° N, 141–142° E, also einen neuen Download, der freigegeben werden muss. Danach PGA- und Interpolationstests für Iburi, dann die Ziehung (Phase 3).

---

## Nachtrag 3, 18.10.2026: Phase 2 – Geländeblöcke; Versatzfehler im v01-DEM-Fenster

Der Nutzer hat den Download der NASADEM-Kacheln für den Iburi-Umriss freigegeben: n42e141, n42e142, n43e141 und n43e142 von Planetary Computer, wie in v01. Größe und SHA-256 stehen in `data/susceptibility_v02/dem/nasadem/*/provenance.json`. Die MD5-Prüfung war nur bei n42e141 möglich; die übrigen drei haben kein einteiliges ETag, wie bereits teils in v01. Code: `preslide/susceptibility/v02_terrain.py` (v01-Merkmalscode, Parameter aus v01 Amendment 2, gegen den registrierten Text geprüft).

### Gefundener Fehler im v01-Code (v01 bleibt unverändert)

`terrain.dem_window` in v01 übergibt `rasterio.merge` die angefragten Längen- und Breitengrenzen. Das Mosaik beginnt dann an diesen Grenzen statt auf dem Pixelraster der Kacheln, und die Kachelpixel werden mit ganzzahligem Versatz kopiert. Jeder Block ist deshalb um bis zu ein halbes NASADEM-Pixel verschoben (0,5 Bogensekunden, höchstens etwa 15 m), je Block unterschiedlich.

Nachweis:

- Ein synthetischer Kacheltest scheiterte mit dem alten Verfahren.
- Auf echten Iburi-Fenstern ergaben sich Verschiebungen von bis zu 6 m und Höhenabweichungen von bis zu 3,8 m gegenüber direkter Reprojektion; nach der Korrektur ist die Abweichung 0.

Wirkung auf die v01-Blöcke, gemessen am selben Raster:

| Inventar | Blöcke | Höhe: mittlere / 99.-Perz. Abweichung | Neigung: mittlere / 99.-Perz. Abweichung |
|---|---|---|---|
| Gorkha | 168 | 4,1 m / 19,7 m | 1,6° / 8,7° |
| Far-Western Nepal | 42 | 4,4 m / 18,5 m | 1,6° / 8,9° |

Details: `phase2_terrain_v01_comparison_*.json`.

**Folgen für v01:**

- Die v01-Merkmale sind leicht unscharf. Das ist ein zufälliger Lageversatz von höchstens einer halben 30-m-Zelle und kein Informationsleck.
- Positive und Hintergrund sind gleich betroffen. Die v01-Ergebnisse (Phase 4, Block-CV, Ursachenanalyse) und die explorative Gorkha-Sensitivität beruhen auf diesen Merkmalen. Ihre Schlussfolgerungen bleiben stehen, die AUC-Werte enthalten aber diese zusätzliche Unschärfe.
- v01 wird nicht geändert; der Fehler ist hier dokumentiert.

**Korrektur in v02:**

- Die Grenzen werden nach außen auf das Kachelraster gerundet. Der Code prüft, dass alle Kacheln ein gemeinsames Raster haben und dass das Mosaik darauf liegt.
- Damit verwirklicht v02 die registrierte bilineare Neuabtastung korrekt; eine Designänderung ist das nicht.
- Damit Training und Test gleich behandelt sind, wurden die Blöcke von Gorkha (168) und Far-Western Nepal (42) im v02-Namensraum neu gerechnet. Die Registrierung erlaubt die Wiederverwendung der v01-Blöcke, verlangt sie aber nicht. Die v01-Kacheln wurden nur gelesen, nichts neu geladen.

### Ergebnis Phase 2

| Inventar | KBS | Blöcke | Umriss vollständig abgedeckt | Höhe im Umriss (min / Median / max) | NaN (Einzugsgebiet, TWI) |
|---|---|---|---|---|---|
| Iburi | EPSG:32654 | 10 | ja (1.357,5 km² aus Zellen, 1.357,6 km² Fläche) | −8 / 63 / 472 m | 0,5 % |
| Gorkha | EPSG:32645 | 168 | ja | 148 / 1.795 / 7.946 m | 0,4 % |
| Far-Western Nepal | EPSG:32644 | 42 | ja | 286 / 1.688 / 4.318 m | 0,4 % |

- Die Meridiankonvergenz bleibt überall unter der registrierten 2°-Grenze (Iburi 0,76°, Gorkha 1,45°, Far-Western Nepal 0,29°).
- Die Bedingung sin² + cos² der Exposition = 1 ist erfüllt.
- Berichte: `phase2_terrain_*.json`. Sie enthalten nur Verteilungen über den ganzen Umriss, keinen Wert an einer Rutschung und keine Stichprobe.

**Phase-2-Gate:** KBS-, Exposition-, PGA-Interpolations- und Leckagetests bestehen und schlagen bei eingebautem Fehler an. Das zeigen:

- v01-Tests für Neigung und zirkuläre Exposition (52).
- `test_susceptibility_v02_pga.py` (32).
- `test_susceptibility_v02_terrain.py` (9): Kachelprüfsumme, Parameter, UTM-54N-Orientierung über ein synthetisches Kachelfenster und eine Kachelnaht, Rasterausrichtung, Blockabdeckung, DEM-Datum, Meridiankonvergenz.
- `mutation_check_pga.json`: 36 von 36 Fehlern erkannt.

**Gate erfüllt.**

### Offene Entscheidung vor Phase 3 (nicht entschieden, keine Stichprobe gezogen)

Etwa **2,6 % des Iburi-Umrisses (≈ 36 km²) haben eine NASADEM-Höhe von genau 0 m** im Süden, an der Pazifikküste. Das ist Meer, das NASADEM auf 0 setzt. Der GSI-Interpretationsbereich schließt dort offenbar Wasser ein. Area-gleichverteilter Hintergrund würde rund 2,6 % Meerzellen ziehen (flach, Höhe 0). Das wäre trivial „keine Rutschung“ und würde jede AUC einschließlich der Neigungs-Baseline aufblähen.

Vorschlag: Ein Amendment vor der Ziehung schließt Hintergrundzellen mit NASADEM-Höhe ≤ 0 m aus, gezählt und berichtet, für alle Inventare gleich. Die Regel stammt aus dem DEM, nicht aus den Rutschungen. Für Gorkha und Far-Western Nepal ändert sie nichts (0 Zellen ≤ 0 m).

---

## Nachtrag 4, 18.10.2026: Phase 3 – Ziehung (Amendment 3, Pufferfehler gefunden und behoben)

**Amendment 3** (vom Nutzer freigegeben, vor jeder v02-Stichprobe):

- Hintergrundzellen mit NASADEM-Höhe ≤ 0 m werden verworfen und gezählt, für alle Inventare gleich (Meer im Iburi-Umriss).
- Außerdem schriftlich festgelegt:
  - Zufallsströme: `default_rng([301, k])`, k = Index in (far_western_nepal, gorkha_2015, iburi_2018).
  - Positiv- und Hintergrunddefinitionen, Quelle der Geländemerkmale (v02-Blöcke), 5-km-Blockkennung.
  - log10 PGA für die Erdbebeninventare.
- Die Stufenprüfung des Amendment-Skripts wurde getrennt: Gelände-Amendments müssen vor den Geländeblöcken stehen, Stichproben-Amendments vor Stichproben und Modellen.

**Erste Ziehung verworfen (vor jedem Modell):**

- Die Verifikation von Iburi und Gorkha schlug fehl: Je ein Hintergrundpunkt lag 99,67 m bzw. 99,75 m von einer bekannten Rutschung entfernt (Puffer 100 m).
- Ursache: GEOS vereinfacht die Eingabe einer Pufferberechnung um 1 % des Abstands (voreingestellter Vereinfachungsfaktor). Ein gepuffertes Polygon kann deshalb Punkte verfehlen, die etwa 1 m innerhalb des wahren Abstands liegen. Nachweis: ein einzelnes gültiges Polygon mit 11 Stützpunkten; sein 100,48-m-Puffer enthält einen Punkt in 99,67 m nicht.
- Die v01-Korrektur (umschreibender Radius) deckt das nicht ab. v01 hat die Prüfung nur zufällig bestanden (Minimum 100,67 m); v01 bleibt unverändert.
- Korrektur in v02: Jede Hintergrundkandidatin wird zusätzlich exakt geprüft (STRtree `dwithin` plus genauer Abstand) und verworfen, wenn sie näher als 100 m an einer bekannten Rutschung liegt. Die Polygonzone bleibt Vorfilter. Die Regel selbst ist unverändert.
- Neu gezogen wurde mit demselben Seed.
- Die fehlgeschlagenen Verifikationen bleiben erhalten (`phase3_verification_*_first_draw_FAILED.json`). Far-Western Nepal hatte bestanden und ist bei der Neuziehung bytegleich (SHA-256 `f41de992…`).

**Ergebnis** (`phase3_sampling_*.json`, `phase3_verification_*.json`, alle PASS einschließlich identischer Wiederholung aus dem Seed):

| Inventar | Positive | Hintergrund | 5-km-Blöcke | Hintergrund-Mindestabstand | verworfen: ≤ 0 m / exakter Puffer |
|---|---|---|---|---|---|
| Far-Western Nepal | 1.551 | 1.551 | 305 | 100,51 m | 0 / 0 |
| Iburi | 3.177 | 3.177 | 69 | 100,21 m | 434 / 1 |
| Gorkha | 24.036 | 24.036 | 1.262 | 100,14 m | 0 / 1 |

Weitere Kennwerte:

- Kein Hintergrundpunkt liegt auf ≤ 0 m, in verdeckten Flächen oder außerhalb des Umrisses.
- Alle Paare halten mindestens 90 m Abstand.
- Keine PGA-NaN.
- NaN nur bei Einzugsgebiet/TWI (abgeschnittene Einzugsgebiete): Iburi 14, Gorkha 148, Far-Western Nepal 8.
- Gezählte Ausschlüsse bei den Positiven:
  - Iburi: 129 berühren Altrutschungen.
  - Gorkha: 747 doppelte Zellen, 11 außerhalb des Umrisses.
  - Far-Western Nepal: 21 doppelt, 15 außerhalb.

Ein transienter GDAL-Speicherfehler beim Lesen trat zweimal auf, jeweils vor dem Schreiben. Die Wiederholung war erfolgreich, das Ergebnis ist durch die Wiederholungsprüfung belegt. Der Leser hält jetzt das Höhenband je Block im Speicher.

**Phase-3-Gate erfüllt:** Puffer-, Umriss- und Mindestabstandsprüfungen bestehen, und jede Ziehung ist aus dem Seed reproduzierbar. Tests: `test_susceptibility_v02_sampling.py` (8). Die Mutationsprüfung umfasst 45 eingebaute Fehler, alle erkannt.

**Nächster Schritt (Phase 4):** bestätigende Tests H1-EQ und H2-EQ (Gorkha → Iburi) mit den registrierten Modellen, Seeds und Bonferroni-Regel über 4 Tests; H1/H2-Regen als „nicht durchführbar“ berichten. Bisher hat kein Modell eine v02-Stichprobe gesehen.

---

## Nachtrag 5, 18.10.2026: Phase 4 – bestätigender Test (einmal gerechnet)

Code: `preslide/susceptibility/v02_evaluate.py`. Die Modelle, Hyperparameter und Seeds sind die registrierten; es gibt keine weitere Modellfamilie.

Vorgehen:

- Vor der Wertung lief ein Pilot nur auf gesehenen Daten (Gorkha → Far-Western Nepal, ohne Ausgaben). Ein Test stellt sicher, dass der Pilot Iburi nicht liest.
- Die Wertung ist write-once; eine zweite verweigert der Code (getestet).
- Mutationsprüfung: 52 von 52 eingebauten Fehlern erkannt.

| Test | Ergebnis |
|---|---|
| H1-EQ | −0,015 [−0,040; +0,009], Bonferroni-Untergrenze −0,047 → **nicht bestanden** |
| H2-EQ | +0,053 [+0,031; +0,073], Untergrenze +0,023 → bestanden |
| H1/H2-Regen | nicht durchführbar (RER2023 `pending_extent`) |

**Schluss nach der registrierten Regel:** Auslöserspezifische Geländeanfälligkeit ist für Erdbeben nicht belegt; Regen ist nicht getestet.

Sekundär:

- Neigung allein erreicht auf Iburi 0,841. Das Geländemodell liegt mit −0,021 [−0,042; −0,004] darunter.
- PGA-Zuwachs: kein Nutzen belegt.
- TPI-Vorzeichen auf Iburi > 0,5 (0,574).
- In der Gegenrichtung erreicht das Iburi-Geländemodell auf Gorkha 0,502.

**Ursachenanalyse (explorativ):** Die Geländewerte überlappen kaum. Nur 31 % der Iburi-Stichproben liegen im Höhenbereich von Gorkha, umgekehrt 4 %. Baummodelle extrapolieren nicht; die Neigung überträgt, weil ihre Richtung stabil ist.

Bericht: `PHASE4_RESULTS.md`. v02 ist damit abgeschlossen. Eine Erweiterung, etwa auf Erdbebeninventare mit ähnlicher Landschaft oder auf ein Modell mit stabiler Extrapolation, wäre eine neue Version mit eigener Vorregistrierung. Iburi ist jetzt gesehen.
