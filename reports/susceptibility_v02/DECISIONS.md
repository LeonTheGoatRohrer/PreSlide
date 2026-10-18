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
