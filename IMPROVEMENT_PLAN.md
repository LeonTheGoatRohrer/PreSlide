# PreSlide — Strategie zur Verbesserung der Aussagekraft (V0.4+)

Stand: 14.10.2026. Grundlage: eingefrorene V0.3-Baseline (`reports/baseline/`), V0.2-Stabilität, V0.3-Zufallsreferenz und eine heutige Nachzählung im lokalen Rohinventar (`data/raw/geosphere_natural_hazards.json`, `data/interim/event_exclusion_decisions.json`) sowie der GeoSphere-Data-Hub-Metadaten. Alle Zahlen unten sind entweder gespeicherte Ergebnisse oder heute nachgezählt; Schätzungen sind als solche markiert.

> **Kurzfassung.** Das Hauptproblem ist nicht das Modell, sondern (1) zu wenige unabhängige Wetterepisoden, (2) ein Studiendesign, in dem Positive und Kontrollen fast dasselbe Wetter haben, (3) dass der auslösende Regen am Ereignistag systematisch unsichtbar ist und (4) dass die Merkmale, die *innerhalb* eines Tals variieren (Krümmung, Einzugsgebiet, Landbedeckung, Geologie), fehlen. Alle vier lassen sich mit offenen Daten auf dem Laptop angehen. Satelliten sind für V0.4 **nicht** der wirksamste Hebel; sinnvoll sind sie später zur Qualitätssicherung der Labels.
>
> **Dringend:** INCA v1 wird laut GeoSphere im Dezember 2026 eingestellt. Die Wetterdaten für einen erweiterten Ereignisbestand sollten in den nächsten Wochen heruntergeladen und gecacht werden.

---

## 1. Was wir gelernt haben — warum die Genauigkeit niedrig ist

| # | Befund (gespeichert/nachgezählt) | Konsequenz |
|---|---|---|
| 1 | 60 Gruppen, aber nur **31 Wetterepisoden** (Daten ≤ 3 Tage zusammengefasst); größte Abhängigkeitsgruppe 15/45 Entwicklungsereignisse. Zufallsband der lokalen AUC ≈ 0,41–0,60. | Die Studie kann nur sehr starke Effekte erkennen. Mehr Zeilen aus *denselben* Stürmen helfen kaum; es braucht **mehr Episoden**. |
| 2 | Kontrollen liegen 0,75–10 km entfernt, Wetter hat 1 km Auflösung. Zwar teilt keine Kontrolle die INCA-Zelle des Positivs, aber die Unterschiede innerhalb der Gruppe sind klein und glatt. | Das räumliche Design **entfernt das Wettersignal weitgehend durch Konstruktion**. Ein schwaches Wetterergebnis ist hier erwartbar und kein Datenfehler. |
| 3 | Zeitpunkt t0 = lokale Mitternacht des Ereignistags, plus 1 h Randschutz. | Der **auslösende Starkregen am Ereignistag** fehlt in jedem Merkmal. Für flachgründige Hangmuren ist das oft der wichtigste Regen. Diese Lücke lässt sich **nur mit Niederschlagsdaten** schließen: Bei Starkregen ist es bewölkt, optische Satelliten (Sentinel-2) sehen nichts, und Radar (Sentinel-1) überfliegt nur alle 6–12 Tage, erfasst also nicht die auslösenden Stunden. |
| 4 | Matching auf Neigung, Höhe, Exposition (30 m Composite-DEM); keine Krümmung, kein Einzugsgebiet, keine Landbedeckung/Geologie. | Die statische Baseline ist schwach (RF-Gelände unter Zufall), weil genau die gematchten Größen keinen Kontrast mehr haben und die verbleibenden lokalen Treiber fehlen. |
| 5 | Positionsverschiebung ändert bei 23/45 Ereignissen die Neigung um > 5°. | Labelrauschen auf Hangebene; 30 m DEM verstärkt das. |
| 6 | RF/GBM lernen auf Rohwerten; die Bewertung ist innerhalb der Gruppe. | Die Modelle verschwenden Kapazität auf Unterschiede *zwischen* Gruppen, die für die Rangfolge innerhalb der Gruppe irrelevant sind. |

Daraus folgt die Reihenfolge der Hebel: **mehr unabhängige Episoden → Triggerregen sichtbar machen → lokal variierende statische Merkmale → designgerechte Modelle → Satellit zur Labelqualität.**

---

## 2. Hebel nach erwartetem Nutzen und Aufwand

| Hebel | Erwarteter Nutzen | Aufwand | Rechenbedarf | Empfehlung |
|---|---|---|---|---|
| A. Mehr Ereignisse/Episoden aus derselben Quelle (präzisere Datumsregel, ab 2011) | **hoch** (Statistische Aussagekraft) | 1–2 Tage | gering, v. a. Netz | **V0.4, sofort** |
| B. Uhrzeit/Tagesabschnitt aus Erzählfeld → Regen am Ereignistag vor dem Ereignis | **hoch** für die Wetterfrage | 0,5 Tag + Tests | gering | **V0.4** |
| C. Lokale Geländemerkmale (10 m DGM: Krümmung, TWI, Einzugsgebiet) + Landbedeckung + Geologie | mittel–hoch für statische und kombinierte Modelle | 1–1,5 Tage | mittel (fensterweise) | **V0.4** |
| D. Vorfeuchte/Schnee: SPARTACUS 90–180 d, SNOWGRID (Schneeschmelze), WINFORE SPEI | mittel | 0,5–1 Tag | gering | **V0.4** |
| E. Designgerechte Modelle (Gruppen-zentrierte Merkmale, bedingte logistische Regression, paarweises Ranking) | mittel, vor allem stabiler | 0,5 Tag | sehr gering | **V0.4** |
| F. Zeitliches Kontrolldesign (Case-Crossover: gleicher Hang, andere Daten) | **hoch** für die Frage „Bringt Wetter etwas?“ | 1 Tag | gering | **V0.5, Nutzerentscheidung** |
| G. ERA5-Land Bodenfeuchte | mittel, aber 9 km grob | 0,5 Tag | gering | optional, braucht kostenlosen CDS-Account |
| H. Sentinel-2 / Sentinel-1 | gering für Vorhersage, mittel für Labelprüfung | 2–5 Tage | hoch (Netz 20–100 GB) | **V0.6, nur QA-Pilot** |
| I. Komplexere Modelle (Deep Learning, Tuning) | gering bis negativ bei dieser Datenmenge | — | — | **nicht machen** |

---

## 3. Datenplan V0.4: mehr unabhängige Episoden

### 3.1 Was die Quelle tatsächlich hergibt (heute nachgezählt)

Rutsch-/Fließprozesse mit Tagesdatum ab 2011 in der GeoSphere-Quelle „Naturgefahren“: **2.450**. Davon bestehen die aktuellen V0-Kriterien **102**. Häufigster Ausschlussgrund allein: `single_reported_day` (**971 Ereignisse**, die sonst alle Kriterien erfüllen: Prozess, Lage ≤ 100 m, sicher Massenbewegung, Prozesscodierung).

Aufschlüsselung dieser 971 Erzähltexte:

| Erzählform | Anzahl | Beispiel (Form) | Vorschlag |
|---|---:|---|---|
| Ein Tag + Tagesabschnitt | 527 | „25. Juli 2016 (früher Nachmittag)“ | einschließen; Tag eindeutig |
| Ein Tag + Uhrzeit | 107 | „… ab ca. 21:00 Uhr …“ | einschließen; **stündliches t0** möglich |
| Sonstige/unklassifiziert | 207 | — | manuell/regelbasiert prüfen, im Zweifel ausschließen |
| Zwei Tage / Bereich | 108 | „06./07. Juni 2015“ | einschließen mit **t0 = Beginn des ersten Tages** (konservativ, kein Leck) oder ausschließen |
| Unsichere Formulierung | 15 | „vermutlich …“ | ausschließen |
| Leer | 7 | — | ausschließen |

Hochrechnung (vor Wetter-/Matching-Verlusten):

| Variante | Ereignisse | Verschiedene Tage | Episoden (≤ 3 d) |
|---|---:|---:|---:|
| V0 heute | 102 | 45 | 31 |
| + gelockerte Datumsregel | 1.073 | 95 | 60 |
| + Zeitraum ab 2011 | 1.211 | 98 | 62 |

**Wichtig:** Die neuen Ereignisse sind extrem geballt (25.07.2016 Stanz: 318; 30.10.2018 Oberkärnten: 148; 08.06.2015: 107). Ohne Begrenzung würde ein einziger Sturm das Modell dominieren. Daher **Obergrenze je Episode**:

| Obergrenze je Episode | Ereignisse (vor Verlusten) | davon 2011–2016 |
|---:|---:|---:|
| 10 | 283 | 40 |
| 20 | 414 | 80 |
| 30 | 519 | 120 |

Mit den bisherigen Verlustraten (≈ 40 % durch Wetterlücken, zu wenige Kontrollen, negative Niederschläge, flache DEM-Neigung) ergibt Obergrenze 20 realistisch **≈ 230–260 vollständige Gruppen aus ≈ 55–60 Episoden** — etwa doppelt so viele Episoden wie bisher. Die Auswahl innerhalb einer Episode erfolgt deterministisch per Hash der Ereignis-ID, nicht nach Datenqualität oder Ergebnis.

### 3.2 Vorab festzulegende Regeln (Präregistrierung)

Bevor irgendein neues Ergebnis betrachtet wird, in `config/v04.json` einfrieren (mit SHA-256 im Bericht):

1. Prozess-, Lage- und Qualitätskriterien wie V0 (unverändert, nicht gelockert).
2. Neue Datumsregel inkl. Abbildung Tagesabschnitt → konservativer Stichzeitpunkt (z. B. „Nachmittag“ → 12:00 lokal, „Abend“ → 17:00, „Nacht auf X“ → 18:00 des Vortags, nicht zuordenbar → Mitternacht wie V0). Immer der **früheste** plausible Zeitpunkt.
3. Episodendefinition (Daten ≤ 3 Tage Abstand) und Obergrenze je Episode.
4. **Externer Prüfbestand:** alle Episoden, die *kein* Baseline-Ereignis enthalten, werden per Hash der Episoden-ID zu ≈ 1/3 in einen versiegelten Test gelegt. Er wird genau einmal mit den eingefrorenen V0.4-Modellen bewertet.
5. Primärer Endpunkt: lokale AUC innerhalb der Gruppe (kombiniert vs. Gelände), mit Episoden-Bootstrap und 100 Label-Permutationen wie V0.3. Sekundär: Top-1-Rate, AP.
6. Abbruchkriterium: weniger als 20 neue unabhängige Episoden nach dem Audit → stoppen und berichten statt Kriterien weiter zu lockern.

Die Baseline-Ereignisse und ihre Splits bleiben unverändert; der alte Testbestand fließt in **keine** Modellwahl ein.

### 3.3 Reichen rund 60 Episoden? Wie kommen wir auf mehr?

Rund 60 Episoden sind **zu wenig, um mittlere Effekte (AUC ≈ 0,60) sicher nachzuweisen**. Schätzung: Dafür bräuchte es ≈ 150 oder mehr effektiv unabhängige Einheiten. (Die Zahl 120 in Abschnitt 3.1 zählt Ereignisse 2011–2016 bei Obergrenze 30, keine Episoden.) Verluste durch Wetterlücken oder Matching betreffen einzelne Ereignisse. Eine Episode fällt nur weg, wenn *alle* ihre Ereignisse ausfallen, deshalb gehen deutlich weniger Episoden als Ereignisse verloren.

Heute nachgezählt (Rutschen/Fließen, Tagesdatum, gelockerte Datumsregel; Episode = Daten ≤ 3 Tage auseinander):

| Stufe | Zusätzliche Einschlüsse | Ereignisse | Episoden (nur zeitlich) | Episoden (zeitlich + räumlich > 50 km getrennt) |
|---|---|---:|---:|---:|
| A | V0.4-Plan, ab 2011, Lage ≤ 100 m | 1.211 | 62 | 93 |
| B | + Ereignisse vor 2011 (tägliches SPARTACUS ab 1961) | 1.659 | 66 | 98 |
| C | + Qualitätsfelder „keine Information“/„wahrscheinlich“ | 2.247 | 141 | 229 |
| D | + Lage 100–1.000 m | 2.880 | 212 | 347 |

Bewertung je Hebel:

1. **Unabhängigkeitseinheit räumlich-zeitlich definieren (kostenlos, sofort).** Ein Gewitter in Vorarlberg und eines in der Steiermark am selben Tag sind meteorologisch getrennte Ereignisse. Eine präregistrierte Regel (gleiches Zeitfenster *und* ≤ 50 km) macht aus 62 → 93 Einheiten. Sie wird geprüft, indem gemessen wird, wie stark die INCA-Niederschlagsreihen zwischen getrennten Teilen korrelieren. Die Distanzgrenze wird vorher festgelegt und nicht nach Ergebnis gewählt.
2. **Zweite Qualitätsstufe „Medienauswertung“ (größter Hebel im räumlichen Design).** Die zusätzlichen Ereignisse aus Stufe C stammen fast alle aus `Auswertung WebInfo` (Zeitungs-/Webmeldungen) mit Lageklasse ≤ 100 m, aber ohne Qualitätsbewertung. Sie sind über viele einzelne Tage verteilt und verdoppeln deshalb die Episoden. Vorschlag: Stufe 1 (geprüft) und Stufe 2 (Medien) getrennt kennzeichnen, auf beiden trainieren, den **Hauptendpunkt nur auf Stufe 1** auswerten und Stufe 2 getrennt berichten. Nie unmarkiert vermischen.
3. **Ungenaue Lagen (100–1.000 m) nur im zeitlichen Design (V0.5).** Für „gleicher Hang, andere Tage“ muss die Lage nur auf die 1-km-Wetterzelle genau sein, nicht auf den Hang. Damit wären bis zu ≈ 210–350 Episoden nutzbar. Im räumlichen Kontrollen-Design bleiben diese Ereignisse ausgeschlossen, weil Kontrollen nur 750 m entfernt liegen.
4. **Vor 2011:** bringt kaum Episoden (+4), weil alte Einträge meist nur Monatsdatum haben. Niedrige Priorität.
5. **Weitere Inventare / Nachbarländer** (z. B. Bayern, Südtirol, Schweiz): würde die Episodenzahl am stärksten unabhängig erhöhen, ändert aber den Gebietszuschnitt „Österreich“ und braucht andere Wetterdaten (INCA endet an der Grenze). Erst nach V0.4 prüfen, mit Nutzerentscheidung.

Empfohlene Kombination für V0.4: Stufe A + räumlich-zeitliche Einheit + Medien-Stufe 2 → **≈ 140–230 Einheiten vor Verlusten**. Für V0.5 kommt Stufe D im zeitlichen Design hinzu.

### 3.4 Weitere Ereignisquellen (nachrangig)

- **WLV Ereignisse** (CC BY 4.0, 1.742 Rutschungen): ohne Lage- und Datumsgenauigkeit. Nur als Abgleich nutzbar (gleicher Ort ± 200 m, gleiches Datum → zusätzliche Bestätigung einer GeoSphere-Position), nicht als eigene Positive.
- **INSPIRE Media** (CC BY 4.0): gleiche IDs; kann für Ereignisse aus der Testquelle eine lizenzklare Bestätigung liefern. Lohnt sich vor allem, falls Ergebnisse öffentlich werden.
- Lizenz: Der erweiterte Bestand stützt sich noch stärker auf die Testquelle ohne geklärte Lizenz. Für lokale Forschung ist das vom Nutzer autorisiert; vor einer Veröffentlichung wäre eine Anfrage bei GeoSphere sinnvoll.

---

## 4. Neue Merkmale

Alle Merkmale strikt aus `[t0 − Fenster, t0)`. Neue Leckagetests sind Pflicht, bevor eine Quelle in Merkmale eingeht.

### 4.1 Triggerregen am Ereignistag (Hebel B)

Für Ereignisse mit Uhrzeit oder Tagesabschnitt wird t0 auf den konservativen Stichzeitpunkt gesetzt. Neue Merkmale: Regen 3 h / 6 h / 12 h / „seit Mitternacht“ vor t0, maximale Stundenintensität seit Mitternacht. Ereignisse ohne Zeitangabe behalten t0 = Mitternacht; diese Merkmale sind dort 0 Stunden lang und werden als **fehlend** markiert, nicht als 0 mm. Die Modellvariante wird zusätzlich nur auf der Teilmenge mit Zeitangabe ausgewertet.

Test: Für jedes Ereignis liegt die letzte verwendete Stunde (inkl. ±1 h Unsicherheit) vor t0.

### 4.2 Vorfeuchte und Schnee (Hebel D) — GeoSphere Data Hub, ohne Account

Heute verifiziert (`dataset.api.hub.geosphere.at/v1/datasets`, Archiv jeweils 1961 → 13.10.2026):

| Datensatz | Parameter | Zweck |
|---|---|---|
| `spartacus-v2-1d-1km` | RR, TN, TX, SA | Vorregen 90/180 Tage; ersetzt INCA langfristig |
| `snowgrid_cl-v2-1d-1km` | snow_depth, swe_tot | Schneeschmelze = Abnahme SWE in 3/7/14 d; Schneebedeckung |
| `winfore-v2-1d-1km` | ET0, SPEI30, SPEI90, SPEI365 | standardisierte Vorfeuchte/Trockenheit |

Achtung Tagesgrenze: Tageswerte (z. B. Niederschlagstag 06–06 UTC) müssen so abgeschnitten werden, dass der letzte genutzte Tag vollständig vor t0 endet — im Zweifel t0 − 2 Tage. Das wird im Code geprüft und getestet.

### 4.3 Lokale Geländemerkmale (Hebel C)

- **DGM Österreich 10 m** (OGD, CC BY 4.0; Größe vor Download prüfen und erfragen) statt 30-m-Composite. Nur Fenster lesen.
- Abgeleitet: Profil-/Plankrümmung, Topographic Wetness Index, Einzugsgebietsgröße, relative Hangposition, Rauigkeit. Das sind die klassischen Treiber flachgründiger Rutschungen, die *innerhalb* eines Tals variieren und vom aktuellen Matching nicht ausgeglichen werden.
- **Landbedeckung:** ESA WorldCover 10 m (2020/2021, CC BY 4.0) oder CORINE 2018. Wald vs. Grünland ist für Hangmuren sehr relevant. Kartenstand muss vor t0 liegen oder wird als quasi-statisch dokumentiert (Grenze offenlegen).
- **Geologie:** GeoSphere Geologische Karte 1:500.000 / 1:200.000 (Lizenz prüfen). Grob, aber besser als nichts.
- Matching bleibt unverändert auf Neigung/Höhe/Exposition, damit V0.4 vergleichbar bleibt; die neuen Größen sind Merkmale und werden zusätzlich als Balance-Diagnose berichtet.

### 4.4 ERA5-Land (optional, Hebel G)

Bodenfeuchte in 4 Schichten, Schneeschmelze, stündlich, ~9 km. Braucht einen kostenlosen Copernicus-CDS-Account und API-Key — **nur der Nutzer kann den anlegen**. Wegen 9 km hilft es innerhalb der Gruppe kaum, vor allem im Case-Crossover-Design (Abschnitt 6).

---

## 5. Modellierung und Auswertung (Hebel E)

- **Gruppen-zentrierte Merkmale:** jedes Merkmal zusätzlich als Abweichung vom Gruppenmittel. Das entfernt das regionale Wetterniveau und zwingt das Modell auf den lokalen Kontrast, den die Bewertung misst.
- **Bedingte logistische Regression** (das Standardmodell für 1:k-gematchte Fall-Kontroll-Studien) als neue Hauptbaseline; dazu ein paarweises Ranking-Modell (z. B. `HistGradientBoosting` auf Paar-Differenzen oder LightGBM-LambdaRank, falls die Abhängigkeit sauber installierbar ist).
- Höchstens 3 Modellfamilien × 3 Merkmalsvarianten, feste Hyperparameter oder verschachtelte gruppierte CV nur auf dem Entwicklungsbestand. Keine Seed-Suche.
- Auswertung wie V0.2/V0.3: gruppierte Folds nach **Episode**, Wiederholungen, Permutations-Null, Episoden-Bootstrap. Zusätzlich räumliche Prüfung (Bundesland-Holdout), sobald genug Episoden außerhalb der Steiermark vorhanden sind.
- Grobe Stärke-Abschätzung (Schätzung, nicht gemessen): Das Zufallsband der lokalen AUC von ±0,095 bei 45 Ereignissen schrumpft bei ≈ 180 effektiv unabhängigen Ereignissen auf ≈ ±0,05. Erst dann sind Effekte um AUC 0,60 sicher erkennbar.

---

## 6. Zeitliches Kontrolldesign (Hebel F) — die stärkste Antwort auf die Wetterfrage

Das bisherige Design fragt „**welcher** Hang am selben Tag?“. Wetter kann dort nur über kleine lokale Kontraste wirken. Die Frage „bringt Vorwetter Information?“ beantwortet ein **Case-Crossover-Design** direkter: derselbe Hang, verglichen mit Referenzdaten ohne dokumentiertes Ereignis (z. B. gleicher Kalendermonat in anderen Jahren, zeitlich geschichtet). Gelände ist dann identisch, nur die Zeit variiert.

- Daten: SPARTACUS/SNOWGRID/WINFORE liefern pro Punkt die gesamte tägliche Reihe seit 1961 mit **einer** Anfrage je Punkt. INCA (stündlich, ab 2011) nur für eine kleine Zahl von Referenzdaten.
- Regeln: Referenzdaten außerhalb ± 30 Tage um jedes Inventarereignis an diesem Ort; gleiche Fensterlogik und gleiche Leckageprüfungen.
- Ehrliche Einordnung: Inventareinträge entstehen bevorzugt nach Unwettern. Ein hohes Ergebnis wäre daher teilweise trivial („vor Rutschungen regnet es“) und kein Warnsystem-Nachweis. Wissenschaftlich interessant ist die **Kombination**: welche Hänge (räumliches Design) bei welchem Vorwetter (zeitliches Design).
- Das erweitert die Forschungsfrage — **deshalb Nutzerentscheidung** und eigene Versionsnummer (V0.5).

---

## 7. Satellitendaten — lohnt sich das?

### 7.1 Einsatzmöglichkeiten

| Einsatz | Daten | Nutzen | Kommentar |
|---|---|---|---|
| Vorfeld-Merkmale (Vegetation, Feuchte vor t0) | S2 NDVI/NDMI, S1 VV/VH | **gering–mittel** | Hangmuren sind oft < 1.000 m² (≈ 10 S2-Pixel). Vegetationszustand ist größtenteils quasi-statisch und billiger über WorldCover zu haben. S1-Rückstreuung im Gebirge stark durch Layover/Schatten gestört. |
| Positionen verbessern | S2 vor/nach (NDVI-Abfall) | **mittel** | Adressiert direkt Befund 5. Nur Labelkorrektur, kein Merkmal → kein Leck, aber Auswahlverzerrung zu großen, sichtbaren Rutschungen dokumentieren. |
| Pseudo-Negative prüfen | S2 vor/nach an Kontrollen | **mittel** | Findet undokumentierte Rutschungen an Kontrollen. Bei kleiner Zahl wenig Effekt auf Metriken, aber stärkt die Glaubwürdigkeit. |
| Detektor (V3 laut AGENTS.md) | S1+S2 | später | Erst sinnvoll mit gelabelten Rutschflächen; für V0.4 außer Reichweite. |

### 7.2 Rechen- und Datenbedarf (Schätzung)

- Zugriff ohne eigene Prozessierung über **Microsoft Planetary Computer STAC** (S2 L2A als COG, S1 RTC bereits geländekorrigiert) oder **Copernicus Data Space** (Account nötig). Rohes S1 GRD selbst mit SNAP zu prozessieren ist auf dem Laptop im Zeitrahmen **nicht** sinnvoll.
- S2-Ausschnitte: COG-Blöcke sind ≈ 5 × 5 km; pro Gruppe und Szene werden mehrere Blöcke à ~0,5 MB gelesen. Mit 3–4 wolkenfreien Szenen vor t0 + 1–2 nach t0 je Gruppe: **≈ 20–40 GB Netzverkehr, 5–15 h Laufzeit** für ≈ 250 Gruppen; mit allen Szenen im 60-Tage-Fenster eher 100 GB. CPU-seitig harmlos, RAM gering bei fensterweisem Lesen; gespeicherte Ausschnitte ≈ 1–3 GB.
- Wolken nach Starkregenereignissen sind häufig; ein relevanter Anteil der Gruppen wird keine brauchbare Nachher-Szene haben.
- **Festlegung:** Für den Zeitraum des auslösenden Regens werden ausschließlich Niederschlagsdaten (INCA/SPARTACUS) verwendet. Optische Daten sind in diesem Zeitraum durch Bewölkung praktisch nicht vorhanden. Satelliten liefern nur die Zustände davor (wolkenfreie Szenen Wochen vorher) oder danach (Labelprüfung).

### 7.3 Empfehlung

Satelliten **nicht** in V0.4-Merkmale aufnehmen. Stattdessen V0.6-Pilot: 30 Gruppen, S2 vor/nach, manuelle plus automatische Prüfung von Positiv-Position und Kontrollen. Nur wenn der Pilot zeigt, dass ≥ 20 % der Positionen sichtbar korrigierbar sind oder Kontrollen nennenswert betroffen sind, auf den ganzen Bestand ausweiten.

---

## 8. Gesamter Rechen- und Speicherbedarf V0.4 (Schätzung, auf 1/5/20 Ereignissen zu messen)

| Schritt | Netz | Laufzeit | Speicher | Engpass |
|---|---|---|---|---|
| Audit mit neuer Datumsregel | keins (Cache) | Minuten | MB | — |
| INCA stündlich (alle Kandidaten, Punkte je Datum gebündelt) | ≈ 300–500 Anfragen | 2–3 h (Limit **240/h, 5/s**, heute verifiziert) | ≈ 1–2 GB roh | Rate-Limit; **vor Dez. 2026** |
| SPARTACUS/SNOWGRID/WINFORE | ≈ 3 × 300 Anfragen | 4–5 h | < 1 GB | Rate-Limit |
| DEM 30 m (bestehende Pipeline) | Kacheln großteils gecacht | 1–3 h | heute ≈ 8 MB/Ereignis → ≈ 3–5 GB | Disk |
| DGM 10 m + Ableitungen | einmalig mehrere GB | 1–3 h | 5–10 GB | Fensterverarbeitung, nie national in RAM |
| Kontrollen (6.000 Kandidaten/Ereignis) | — | auf 20 Ereignissen messen | ≈ wie heute je Ereignis | CPU, parallelisierbar |
| Training + Stabilität + 100 Permutationen | — | < 1–2 h | < 1 GB | — |

Gesamt realistisch **2–3 Arbeitstage plus über Nacht laufende Downloads**. Alles CPU, kein GPU-Bedarf. Freier Plattenplatz ≥ 25 GB empfohlen.

---

## 9. Ablauf mit Prüfpunkten

| Phase | Inhalt | Prüfpunkt / Abbruch |
|---|---|---|
| 0 | `config/v04.json` präregistrieren und hashen; versionierter Runner nach `reports/experiments/<id>/`, Baseline-Schutz bleibt aktiv | Tests: Baseline-Hashes unverändert |
| 1 | Datumsparser für Tagesabschnitt/Uhrzeit + Tests; Audit-Trockenlauf; Episoden und Obergrenze anwenden | ≥ 20 neue Episoden, sonst stoppen und berichten |
| 2 | **INCA-Download zuerst** (1 → 5 → 20 → alle), dann Tagesprodukte | Werte plausibel, keine Stunde ≥ t0 |
| 3 | Gelände 30 m für neue Ereignisse, Kontrollen, dann DGM 10 m + WorldCover + Geologie | Matching-Qualität ≥ V0; Leckage- und Abstandstests grün |
| 4 | Merkmalstabelle; Modelle nur auf Entwicklungsbestand (Baseline-Dev + neue Nicht-Test-Episoden) | Permutations-Null mitlaufen lassen |
| 5 | Versiegelten externen Test **einmal** bewerten, Bericht, Web-Ansicht ergänzen | Ergebnis unabhängig vom Ausgang berichten |
| 6 (optional) | Case-Crossover V0.5 | nach Nutzerfreigabe |
| 7 (optional) | Satelliten-QA-Pilot V0.6 | Ausweitung nur bei Pilot-Nutzen |

---

## 10. Was der Nutzer entscheiden oder tun muss

1. **Freigabe der gelockerten Datumsregel** (Abschnitt 3.2) und der Episoden-Obergrenze (Vorschlag: 20). Das ändert Einschlusskriterien und wird deshalb als V0.4 versioniert.
1b. **Medien-Stufe 2** (Abschnitt 3.3, Hebel 2) und **räumlich-zeitliche Unabhängigkeitseinheit** (Hebel 1) aufnehmen?
2. **Case-Crossover (V0.5)** ja/nein — erweitert die Forschungsfrage; erst damit werden ungenaue Lagen (100–1.000 m) nutzbar.
3. Optional: kostenlosen **Copernicus-CDS-Account** für ERA5-Land anlegen; optional Planetary-Computer-/CDSE-Zugang für den Satellitenpilot.
4. Kenntnisnahme: INCA v1 läuft im Dezember 2026 aus; Phase 2 sollte bald laufen.

## 11. Bewusst nicht geplant

- Kriterien so lange lockern, bis die AUC steigt; schwierige Ereignisse entfernen; Kontrollen nachjustieren.
- Den alten Test oder Steiermark-Test zur Auswahl von Merkmalen oder Modellen verwenden.
- Deep Learning, umfangreiches Hyperparameter-Tuning, GPU-Pipelines.
- Österreichweite Gefahrenkarte oder Warnsystem-Aussagen.

Realistische Erwartung: Eine deutliche Verbesserung ist am ehesten von den lokalen Geländemerkmalen und dem Triggerregen am Ereignistag zu erwarten; ob vorgelagertes Wetter im räumlichen Design einen Nutzen bringt, kann auch nach V0.4 negativ ausfallen. Mit doppelt so vielen Episoden und einem versiegelten externen Test wäre aber auch ein negatives Ergebnis belastbar.
