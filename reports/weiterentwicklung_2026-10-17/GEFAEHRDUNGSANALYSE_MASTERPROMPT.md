# Arbeitsauftrag: meldungsbasierte Prüfgebiete für Hangmuren und deren möglichen Auslauf

Stand: 17.10.2026. Dieser Text ist ein Arbeitsauftrag für eine neue Agent-Session. Er beschreibt das Ziel, den Entscheidungsablauf und die Nachweise. Er ist keine bereits ausgeführte Implementierung, Präregistrierung oder zugesicherte Modellleistung.

## 1. Auftrag und Arbeitsweise

Entwickle den kleinsten vollständigen, reproduzierbaren und wissenschaftlich vertretbaren Prototyp, der aus einer gemeldeten Hangmure räumliche Prüfgebiete in ihrer Umgebung ableitet. Prüfe zuerst, ob die verfügbaren Daten die gewünschten Aussagen überhaupt tragen. Baue keine umfangreiche Pipeline, bevor diese Machbarkeit geklärt ist.

Arbeite in autonomen, überprüften Batches. Triff gewöhnliche technische Entscheidungen selbst. Frage nur bei echten Blockern oder einer unvermeidbaren Änderung der wissenschaftlichen Fragestellung. Negative Ergebnisse und nachgewiesene Datenlücken sind zulässige Resultate. Erfinde weder Ereignisse noch Referenzflächen, Bodenwerte, Wahrscheinlichkeiten oder Modellgüte.

Dieser Auftrag betrifft gelände- und umweltbasierte Prüfprioritäten sowie szenariobasierte Auslaufbereiche. Die neuronale Bildsuche bleibt ein getrenntes Teilprojekt. Ihr Training, ihre Gewichte und ihre Ergebnisse werden durch diesen Auftrag weder neu ausgeführt noch verändert. Übernimm keine halb fertigen Komponenten ungeprüft.

## 2. Verbindlicher Einstieg und Schutz bestehender Arbeit

1. Lies AGENTS.md, PROJEKTUEBERBLICK.md vollständig, danach PROJECT_STATE.md. Beachte insbesondere die Regeln zu eingefrorenen Artefakten und statistischen Aussagen.
2. Prüfe Arbeitsverzeichnis, Git-Status, lokale Worktrees und den aktuellen Stand von origin/main. Dort sind V0.6–V0.9 und eine frühe Satellitenpipeline bereits vorhanden. Lokaler Hauptcheckout und Remote können unterschiedliche Stände haben. Vorhandene uncommittete Änderungen anderer Arbeiten erhalten; nichts pauschal zurücksetzen oder mitcommitten.
3. Suche gezielt nach bestehenden Hilfen für Raster, CRS, Distanzen, Hydrologie, Kontrollauswahl, gruppierte Aufteilungen, Hashes und Checkpoints. Wiederverwenden statt doppelt implementieren.
4. Wähle nach Bestandsprüfung einen freien Versionsnamen, beispielsweise hazard_v01, mit eigenen Verzeichnissen data/hazard_v01/, models/hazard_v01/, reports/hazard_v01/ und eigener config/hazard_v01.json. Kein Überschreiben früherer Experimente.
5. V0.3-Baseline und Archiv, V0.4-Präregistrierung, Amendments, Freeze, Konfiguration und einmal ausgewerteter Test bleiben unverändert. Früher betrachtete Ergebnisse dürfen keine nachträgliche Auswahl günstiger Schwellen, Regionen oder Modelle begründen.

### Bekannte Befunde, die nicht als offene Erfolge vorausgesetzt werden dürfen

- Das bestehende Fall-Kontroll-Ranking ist keine flächige Gefahrenwahrscheinlichkeit. Ein Transfer auf Rasterzellen benötigt eine eigene Prüfung im tatsächlichen Anwendungsszenario.
- Für Wetter wurde in den bisherigen Designs kein verlässlicher Zusatznutzen gegenüber statischen Merkmalen nachgewiesen. Dies ist weder ein Beweis für generelle Wirkungslosigkeit noch eine Grundlage für einen ungeprüften Wetterbonus.
- Der separate Pilot mudslide_cascade_v01 untersuchte 102 als Hangmure bezeichnete Ereignisgruppen aus 19 unabhängigen Einheiten. Das Umgebungsmodell erreichte eine einheitengewichtete lokale AUC von 0,539, mit 95-Prozent-Intervall 0,406–0,669 und Zufallsreferenz 0,5; obere Zufallsreferenz-Prüfung p = 0,279. Ein Nutzen der Vorauswahl ist damit nicht belegt. Gespeicherte Modelle reproduzieren die Vorhersagen; verification.json meldet PASS. Prüfe die Originaldateien unter reports/mudslide_cascade_v01/. Dieser Pilot misst gematchte Punktvergleiche, nicht die hier neu definierte Flächenaufgabe.
- Die bisherige Geländepipeline arbeitet mit einem auf 30 m projizierten Skadi-Komposit. Ein geeignetes historisches 5-m-DGM ist nicht vorauszusetzen. Ein untersuchtes 10-m-Produkt wurde mangels belegbarer zeitlicher Eignung nicht verwendet; das ist keine pauschale Aussage gegen alle 10-m-Produkte.
- Medien- und Kärnten-Episoden aus V0.9 sind bereits betrachtet. V0.9 verfehlte die vorgesehene Qualitäts-/Einheitenfreigabe. Solche Daten sind weder automatisch prozessrichtig noch erneut ungesehen.
- Die Satellitensuche hat bekannte Ereignisse teilweise wiedergefunden, aber auch viele Fehlvorschläge erzeugt. Eine zuverlässige freie Entdeckung unbekannter Muren ist nicht nachgewiesen. Bildbefunde werden in diesem Auftrag nicht automatisch zu Wahrheitslabels.

Diese Angaben sind übergebene Startbefunde. Prüfe die genannten Artefakte im tatsächlichen Arbeitsstand. Fehlen lokale oder noch nicht veröffentlichte Dateien, kennzeichne den Nachweis als dort nicht verfügbar; erfinde keine erfolgreiche Verifikation und rekonstruiere keine eingefrorenen Ergebnisse durch neue Trainingsläufe.

## 3. Nutzerfall und zulässige Aussagen

Ein Nutzer markiert den Ort einer gemeldeten Hangmure. Eine Meldung enthält Koordinaten, optional Ereignisdatum mit Genauigkeit, optional den Bezug des Orts zum Ereignis und einen freien Hinweis. Kein Handyfoto und keine neue Bild-KI in dieser Version.

Die Anwendung soll für einen einstellbaren Anzeigeumkreis, zunächst standardmäßig 5 km innerhalb Österreichs, folgende getrennte Informationen prüfen und gegebenenfalls darstellen:

1. Auslöse-Priorität: Welche Hangbereiche sind anhand von Gelände- und Umweltmerkmalen relativ prüfenswerter als andere?
2. Szenariobasierter Auslauf: Welche Bereiche könnten von festgelegten möglichen Anrissbereichen aus unter ausdrücklich benannten Annahmen erreicht werden?
3. Kombinierte Prüfpriorität: Wo treffen eine begründete Auslöse-Priorität und ein plausibler Auslaufzusammenhang zusammen?

Das sind Forschungs- und Entscheidungshilfen. Keine Aussage über akut bevorstehende Ereignisse, nachgewiesene Sicherheit oder eine bestimmte Eintrittswahrscheinlichkeit. Ein möglicher späterer Frühwarnnutzen ist Zukunftsarbeit und kein aktueller Leistungsnachweis.

### Begriffliche Regeln

- Verwende zunächst Auslöse-Priorität, Auslaufszenario und kombinierter Prüfindex. Verwende Wahrscheinlichkeit nur für eine konkret definierte, passend kalibrierte und geprüfte Größe.
- Multipliziere keine unkalibrierten Rangwerte und nenne das Ergebnis Gefährdungswahrscheinlichkeit. Klassen statt Prozentangaben lösen dieses Problem allein nicht.
- Eine Häufigkeit in einem Parameterszenario-Ensemble ist ein Szenarienanteil, keine automatisch kalibrierte Wahrscheinlichkeit.
- Kein Bildhinweis, kein Inventareintrag oder fehlende Daten bedeuten nicht ungefährlich. Nicht beurteilbar muss eine eigene Ausgabe bleiben.
- Geologie, Landbedeckung und Vegetationsindizes sind keine direkten Messungen von Bodenfeuchte, Bodenfestigkeit oder Versagenszustand. Nenne Proxys und ihre Grenzen ausdrücklich.
- Keine Schneelawinen. Hangmuren, Wildbachmuren und andere Rutschungen nicht stillschweigend als gleicher Prozess behandeln. Lege die zunächst modellierte Prozessklasse anhand der realen Referenzen fest. Erweiterungen sind getrennt zu begründen und zu registrieren.

## 4. Erste Phase: begrenzte Machbarkeitsprüfung mit verbindlicher Entscheidung

Setze für die erste Prüfung zunächst ein Arbeitsbudget von höchstens 45 Minuten aktiver Recherche und Inspektion an. Verwende vorhandene Daten und Caches. Starte in dieser Phase keine großen Downloads, Modelltrainings, Oberflächenarbeiten oder vollständigen Regionsberechnungen. Wird eine notwendige Quelle innerhalb des Budgets nicht verifiziert, dokumentiere den offenen Punkt und entscheide über einen kleineren sinnvollen Umfang, statt unbegrenzt weiterzusuchen.

Erzeuge eine kompakte Machbarkeitstabelle mit:

| Komponente | Erforderlicher Nachweis |
|---|---|
| Prozess | Eindeutiger Typ, gemischter Typ oder unbekannt |
| Ereignisort | Anriss, Transportbereich, Ablagerung, Schadensort oder unbekannt |
| Geometrie | Punkt/Unsicherheitsbereich, Anrisspolygon, Transportspur, Auslauf-/Ablagerungsfläche getrennt |
| Zeit | Ereignisdatum und Genauigkeit, Veröffentlichungszeit soweit vorhanden |
| Gelände | Quelle, native und verwendete Auflösung, Höhenbezug, Zustand vor dem Referenzereignis nachweisbar? |
| Unabhängigkeit | Zahl zeitlicher Episoden/räumlicher Blöcke, Clusterverteilung und frühere Verwendung |
| Meldungsumgebung | Anfragen mit weiteren geeigneten Referenzereignissen innerhalb des vorgesehenen Umkreises und Zeitbezugs |
| Auslaufprüfung | Reale, unabhängig dokumentierte Geometrien und deren Unsicherheit |

Zähle die verfügbaren Ereignisse und unabhängigen Einheiten je Kategorie. Leite keine Anrissmaske aus einem Inventarpunkt und keine Auslaufreferenz aus dem später zu prüfenden Modell ab.

Entscheide für jede Komponente ausdrücklich:

- umsetzbar und mit vorhandenen Referenzen quantitativ prüfbar;
- nur als technische beziehungsweise illustrative Demonstration umsetzbar;
- derzeit nicht sinnvoll prüfbar, deshalb zurückstellen.

Ohne geeignete Anrissreferenzen keine validierte Auslöseort-Erkennung behaupten. Ohne geeignete Auslaufreferenzen keine erreichte Auslaufgenauigkeit behaupten. Fehlen beide, beende die Modellierung nach dem Audit; ein nachvollziehbarer Daten- und Machbarkeitsbericht ist dann das Ergebnis. Eine anschauliche Abwärtsroute darf nur getrennt als unvalidierte Illustration entstehen.

Eine negative Machbarkeitsentscheidung ist keine Erlaubnis, synthetische Referenzen oder erfundene Kennzahlen als Ersatz einzusetzen. Wenn nur eine Komponente sinnvoll prüfbar ist, liefere diese vollständig und dokumentiere die zurückgestellte Komponente.

## 5. Design vor Ergebnissen registrieren

Nach dem Audit, vor dem ersten zu bewertenden Modell- oder Auslaufvergleich, registriere im neuen Namespace:

- Zielklasse und Bedeutung der Ortsreferenzen;
- Ein-/Ausschlussregeln und Zählungen;
- Rolle der Meldung und zeitliche Suchaufgabe;
- räumliche Domäne, Anzeigeumkreis, notwendige Zusatzflächen und gültige Rasterauflösung;
- Datensatz-, Konfigurations- und Codeidentitäten;
- unabhängige Einheiten, räumliche Abstände, Gruppensplits und Schutz vor überlappenden Referenzen;
- Referenzverfahren, ein erstes gelerntes Modell und ein begrenztes Rechenbudget;
- Auslaufannahmen, Parameterbereiche und Szenarien, soweit eine Auslaufprüfung zugelassen wurde;
- primäre Kennzahl, feste Flächenbudgets, Unsicherheitsverfahren und Abbruch-/Freigaberegeln;
- vollständige Liste geplanter Vergleiche und den Status explorativ oder tatsächlich neu bestätigend.

Technische Prüfungen auf einem echten Rasterfenster sind vorher erlaubt, sofern sie keine Grundlage zum Auswählen günstiger wissenschaftlicher Resultate werden. Designänderungen vor einem betroffenen Lauf als Amendment mit Grund dokumentieren. Eine nach Sicht auf Prüfresultate geänderte Variante bleibt eine neue explorative Untersuchung; sie erhält keinen neuen unberührten Test durch Umbenennung.

## 6. Zeitliche und räumliche Aufgabe eindeutig festlegen

Primäre erste Fragestellung ist retrospektiv: Gegeben eine dokumentierte Meldung, wie gut priorisiert das System weitere dokumentierte Ereignisorte derselben vorab definierten Episode in der Umgebung? Dies untersucht Unterstützung bei der Lageerkundung, keine Vorhersage künftiger Ereignisse.

Soll stattdessen ein zukünftiger Zeitraum untersucht werden, ist das ein eigenes Design mit festgelegtem Vorhersagehorizont und Informationen, die bei der Meldung tatsächlich verfügbar waren. Beide Aufgaben nicht vermischen.

- Die auslösende Meldung ist die bekannte Anfrage, nie ein Treffer der Suche. Schließe sie und ihren vorab festgelegten Unsicherheitsbereich aus der Trefferzählung aus.
- Lege die Wahl der Anfragen vor Auswertung fest. Verwende nicht nachträglich nur Meldungen mit besonders leicht auffindbaren Nachbarereignissen. Berichte auch Anfragen ohne weitere dokumentierte Nachbarereignisse; dort ist Recall gegebenenfalls nicht bestimmbar.
- Bekanntes Wissen aus einer Meldung darf als Anfrageinformation verwendet werden. Verdeckte Zielereignisse, deren Geometrien und spätere Berichte dürfen keine Eingabemerkmale werden.
- Alle Anfragen und Zielereignisse einer Abhängigkeitseinheit bleiben im selben äußeren Split. Mehrere Anfragen derselben Episode erhöhen die effektive Stichprobe nicht.
- Ohne belastbares Ereignisdatum bleiben statische Informationen zulässig. Verwende dann keine erfundene Wetterhistorie oder undokumentierte zeitliche Zuordnung.
- Für eine Anfrage gilt ein einheitlich definierter Informationsstand. Wetterfenster oder andere zeitliche Merkmale dürfen nicht das verborgene Datum eines gesuchten Zielereignisses benötigen. Lege den gemeinsamen Bezugszeitpunkt und die zu diesem Zeitpunkt tatsächlich verfügbaren Daten vorab fest; unklare Datumsangaben konservativ behandeln.

## 7. Gelände- und Datenaufbereitung

Nutze reale lokale Rasterfenster und vorhandene Hydrologie-Hilfen. Prüfe CRS, metrische Einheiten, Höhenbezug, Nodata, tatsächliche Auflösung und Ränder.

- Für retrospektive Prüfungen muss der Geländezustand vor dem jeweiligen Referenzereignis belegbar sein. Aktuelles Gelände für eine heutige Anwendung wird getrennt geführt. Downloadzeit, Produktveröffentlichung und Vermessungszeit sind verschiedene Angaben; nenne den tatsächlich vorhandenen zeitlichen Nachweis.
- Untersuche mögliche Veränderungen durch das eigene Referenzereignis. Ein Puffer beseitigt eine durch das Ereignis veränderte Rinne nicht automatisch; erforderlichenfalls älteres Gelände verwenden oder Ereignis ausschließen.
- Behaupte keine 5-m-Grundlage ohne geeignete Originaldaten. Resampling auf kleinere Pixel erzeugt keine neue Bodenauflösung. Berichte Grenzen bei schmalen Rinnen, Schutzbauten, Dämmen, Brücken und lokalen Hindernissen.
- Die Anzeige innerhalb von 5 km begrenzt nicht automatisch das physikalisch nötige Rechengebiet. Prüfe oberhalb liegende Einzugsgebiete und erforderliche Auslauf-/Randbereiche. Lade notwendige Zusatzfenster kontrolliert nach oder markiere die Analyse als räumlich unvollständig.
- Senkenfüllung, Gewässerkonditionierung und Fließrichtungsableitung als Verarbeitungsschritte dokumentieren. Eine rechnerisch gefüllte Senke ist kein Beleg, dass sich Material tatsächlich genauso bewegt.
- Quellen und Nutzungsrechte in DATA_SOURCES.md, Konfiguration in versionierten JSON-Dateien. Bestehende Hash-/Sidecar-Verfahren für teure Checkpoints verwenden; bei Cacheabweichungen laut scheitern.

## 8. Auslöse-Priorität auf der tatsächlichen Flächenaufgabe prüfen

Nur ausführen, wenn das Audit geeignete Referenzen und Kandidatenräume ergeben hat.

1. Beginne mit einer reproduzierbaren Geländereferenz und genau einer einfachen Modellfamilie, etwa logistischer Regression. Vorhandene V0.4/V0.5-Helfer dürfen wiederverwendet werden; ihre gematchten Kennzahlen sind aber kein Nachweis für Rasterzellen im Suchgebiet.
2. Verwende einen vorab definierten Kandidatenraum. Unterscheide mögliche Anrisshänge von Transport-/Ablagerungsbereichen. Keine Vorauswahl anhand der bereits bekannten verdeckten Zielereignisse.
3. Prüfe Gelände allein gegen Zufallsfläche und reine Steigungsregel. Wetter/Zeit und kombiniert kommen als registrierte Zusatzvergleiche nur hinzu, wenn Zeitpunkt, Daten und Rechenbudget passen. Wettervorteil nicht voraussetzen.
4. Random Forest und Gradient Boosting erst ergänzen, wenn der erste vollständige Vergleich funktioniert. Keine breite Parametersuche oder neuen neuronalen Netze ohne konkreten Bedarf und geeignete Labels.
5. Prüfe Melde-/Platzierungsverzerrungen. Fehlende explizite Straßendistanz entfernt diese nicht automatisch: Landbedeckung, Höhe, Talnähe und Ortsreferenzen können dieselbe Verzerrung tragen. Zeige registrierte Ablationen und die Auswertung ohne dominanten Cluster; verwende passende datierte Quellen, soweit verfügbar.
6. Keine harte Beschränkung späterer Suchschritte auf Modellvorschläge, bevor deren Ereignisabdeckung bei festgelegtem Flächenbudget geprüft wurde. Nicht erkannte Bereiche dürfen nicht als sicher erscheinen.

Primäre Kennzahl ist die Abdeckung weiterer geeigneter dokumentierter Ereignisse bei vorab festgelegten Anteilen der gültigen Suchfläche. Zeige eine Flächeneffizienzkurve und mindestens einen vorab ausgewählten Betriebspunkt. Berichte gleichzeitig die markierte Fläche, ausgelassene/ungültige Fläche und Zahl auswertbarer Anfragen.

Vergleiche Verfahren auf derselben vorab definierten Flächengrundlage. Zeige zusätzlich, wie viele Referenzereignisse wegen fehlender Daten außerhalb der auswertbaren Fläche liegen. Verbessere eine Kennzahl nicht dadurch, dass ein Verfahren schwierige Zielbereiche aus seiner Bewertungsdomäne entfernt.

ROC AUC und PR AUC gegen nicht verifizierten Hintergrund sind ergänzende Maße für die Trennung dokumentierter Ereignisse vom gewählten Hintergrund. Berichte Hintergrundauswahl und Gewichtung; interpretiere diese Größen nicht als echte flächige Fehlalarmrate oder kalibrierte Eintrittswahrscheinlichkeit. Eine echte Fehlalarm-/Recall-Prüfung braucht entsprechend vollständig untersuchte Referenzgebiete.

## 9. Auslauf als begrenztes Szenariomodell prüfen

Nur ausführen, wenn geeignete dokumentierte Anriss-/Auslaufreferenzen vorhanden sind; andernfalls technische Illustration ausdrücklich getrennt halten.

1. Wähle ein einfaches, fachlich begründetes Verfahren für die zugelassene Prozessklasse. Beginne mit einer DEM-basierten Abwärtsroute als Referenz, anschließend gegebenenfalls einem begründeten Reichweiten-/Auslaufwinkelmodell mit seitlicher Verteilung. Eine Wasser-Fließrichtung allein simuliert keinen vollständigen Murgang.
2. Nenne fehlende Größen wie Ausgangsvolumen, Materialeigenschaften und Wassergehalt. Nicht verfügbare Werte werden nicht ausgedacht. Verwende transparente, literatur- oder entwicklungsdatenbegründete Szenarien, deren Bereiche vor dem Test eingefroren werden.
3. Setze kein universelles Stoppkriterium „geringes Gefälle“ oder „Schwemmkegel erreicht“ ohne prozessbezogene Begründung. Beschreibe, was ein Modellstopp tatsächlich bedeutet und welche physikalischen Effekte fehlen.
4. Unterscheide Modellstopp, Senke, Nodata, unvollständiges Einzugsgebiet und Verlassen des Rechengebiets. Ein Austritt am Rasterrand bedeutet nicht, dass der reale Auslauf dort endet.
5. Vergleiche gegen einfache festgelegte Referenzen, zum Beispiel eine Abwärtsroute mit fester Reichweite. Parameterszenarien werden vollständig gezeigt; nicht die im Nachhinein passendste Kurve als Modellleistung berichten.
6. Prüfe erreichter Referenzflächenanteil, übermäßig markierte Fläche, Verfehlungen und geeignete Distanz-/Überlappungsmaße. Trenne Auslauf von Anriss und beziehe Geometrie-/Positionsunsicherheit ein. Die tatsächliche Referenzqualität begrenzt die Aussage.

Ergebnis sind Szenarien, Auslaufhüllen und eine ehrliche Prüfung ihrer Übereinstimmung mit unabhängigen Referenzen. Ohne passende Kalibrierungsgrundlage keine Erreichbarkeitswahrscheinlichkeit ausgeben.

## 10. Kombination nur bei begründeten Komponenten

Führe Auslöse-Priorität und Auslaufszenarien erst zusammen, wenn ihre Bedeutung und Grenzen geklärt sind. Eine kombinierte Karte übernimmt die Unsicherheit ihrer Komponenten und wird nicht allein durch Kombination validiert.

- Halte beide Komponenten einzeln verfügbar und sichtbar.
- Definiere vor Prüfung eine nachvollziehbare monotone Zuordnung zu Prüfprioritätsklassen oder einen ausdrücklich heuristischen Index. Begründe alle Gewichtungen und die Aggregation mehrerer möglicher Anrisse. Keine unkalibrierten Produkte als Wahrscheinlichkeiten ausgeben.
- Fehlende oder räumlich unvollständige Komponenten erzeugen nicht beurteilbar beziehungsweise eine klar benannte Teilanalyse. Nicht beurteilbar ist keine niedrige Priorität.
- Gib an, ob Klassen relativ zum aktuellen Suchgebiet oder zwischen Regionen vergleichbar definiert sind. Eine Änderung des Anzeigeumkreises darf nicht unbemerkt eine andere fachliche Bedeutung derselben Farbe erzeugen.
- Prüfe, ob die Kombination gegenüber ihren Einzelkomponenten bei gleicher markierter Fläche einen belegten Mehrwert hat. Ohne Nachweis beide Ebenen getrennt liefern, statt eine vermeintlich bessere Gesamtkarte zu erzwingen.

## 11. Statistik, Referenzunsicherheit und neue Bestätigung

- Effektive Stichprobe = unabhängige Episoden/Blöcke, nicht Rasterzellen, Kontrollpunkte oder wiederholte Meldungsanfragen.
- Alle Hauptergebnisse mit Zahl dieser Einheiten, geeignetem Intervall aus Resampling dieser Einheiten und passender Null-/Einfachreferenz berichten. Modellunterschiede gepaart auswerten. Einzelne positive Vergleiche nicht aus einer größeren Menge herausgreifen.
- Für Punktreferenzen Positionsunsicherheit berücksichtigen und die Abhängigkeit der Trefferzählung von einem vorab festgelegten Trefferradius zeigen. Keine großen Trefferpuffer nach Ergebnislage wählen. Unsicherheitsbereiche sind keine erfundenen Auslaufpolygone.
- Gruppen, Episoden und räumlich überlappende Daten nicht zwischen Training und äußerer Prüfung verteilen. Räumliche Abstände vorab festlegen und auf tatsächlichen Footprints prüfen. Ganze Regionen ausschließen, wenn die Daten dies erlauben; aus Zufallssplits keine geographische Übertragbarkeit ableiten.
- Vergleichsdaten, Parameterwahl und Klassenbildung ausschließlich aus dem Entwicklungsbestand. Finale Testauswertung pro eingefrorener Version einmal. Wiederholte Entwicklungsprüfungen bleiben Entwicklungsprüfungen.
- Prüfe jede vorgeschlagene neue Quelle auf frühere Nutzung, Duplikate, gemeinsame Episoden und Prozessfehler. V0.9-Daten sind bereits gesehen. Neue Bestätigung benötigt tatsächlich ungesehene Einheiten und ein vorab festgelegtes Protokoll.
- Änderungen an Stichprobe, Radius, Prozessfilter oder Datenqualität niemals zur Verbesserung eines bereits gesehenen Ergebnisses auswählen. Alle Ausschlüsse nach Grund zählen und dokumentieren.

## 12. Meldeendpunkt und Darstellung erst nach der fachlichen Prüfung

Nur umsetzen, soweit zuvor eine sinnvolle geprüfte oder eindeutig begrenzte Analyse verfügbar geworden ist. Fehlende wissenschaftliche Grundlage nicht durch UI-Aufwand ersetzen.

Geplanter Endpunkt: POST /api/meldungen.

- Eingang: Längengrad/Breitengrad in ausdrücklich festgelegtem CRS, Anzeigeumkreis mit begründeten Grenzen, optional Ereignisdatum und dessen Genauigkeit, optional Ortsbezug und Hinweis. Werte, Achsenreihenfolge und Geltungsbereich prüfen.
- Meldung mit Eingangszeitpunkt in UTC, Quelle, Ereigniszeit und Status UNVERIFIED getrennt speichern. Bestätigter Eingang bedeutet keine Bestätigung des Ereignisses.
- Nutzerberichte, Duplikate und Modellausgaben fließen niemals automatisch in verifizierte Trainings- oder Testdaten. Spätere Labelprüfung und Zulassung sind eigene nachvollziehbare Schritte.
- Antwort enthält Analyse-ID und Status. Bei längerer Berechnung nachvollziehbaren Jobstatus statt unkontrolliert blockierender Anfrage verwenden. Herkunft, Gültigkeitszeit, Modell-/Daten-/Konfigurationshash und Beurteilbarkeit pro Analyse speichern.
- Deutsche Oberfläche mit getrennten Ebenen für Meldung, Auslöse-Priorität, Fließwege, Auslaufszenarien und gegebenenfalls kombinierten Prüfindex. Nicht beurteilbare Flächen ausdrücklich zeigen.
- Rasterausgabe als COG, Vektorflächen als GeoParquet/GeoJSON, nur in eigenem Namespace und mit vorhandenen Checkpoint-Konventionen. CPU-first, kachelweise, keine landesweiten Raster im RAM.

Zurückgestellt bleiben Infrastrukturverschneidung, Betreiberkontakte und Benachrichtigungen, Satellitenprüfung, automatisches Weiterlernen, 3D-Ansicht und umfangreicher visueller Feinschliff. Keine externe Nachricht aus diesem Auftrag senden. Eine spätere 3D-Oberfläche ist Darstellung; sie erweitert nicht die wissenschaftliche Gültigkeit der Analyse.

## 13. Ausführung, Tests und Abschluss

Arbeite nach 1 → 5 → 20 realen Fällen und erst dann einem begründeten größeren Lauf. Das sind technische Skalierungsstufen, keine Zusicherung, dass genügend unabhängige Validierungsfälle vorhanden sind. Verwende Caches und Checkpoints. Baue zuerst genau einen vollständigen Vergleich statt mehrerer unvollständiger Modelle.

Tests konzentrieren sich auf gefährliche Fehler:

- Keine Quelle oder Wetterbeobachtung nach dem jeweils definierten Bezugszeitpunkt als Prognosemerkmal.
- Ortsreferenztyp und Prozessklasse werden nicht stillschweigend umgedeutet.
- Die auslösende Meldung zählt nicht als eigener Treffer und ihre Episode bleibt im äußeren Prüfsplit.
- Gruppen/Einheiten bleiben zusammen; Schutzabstände und Footprints werden eingehalten.
- CRS, metrische Distanzen, Achsenreihenfolge, Rastertransform und zirkuläre Exposition sind korrekt.
- Fließrichtung und Auslauf behandeln Senken, Nodata, Randabfluss und unvollständige Einzugsgebiete getrennt.
- Fehlende Daten oder Modellabdeckung werden nie zu niedriger Priorität oder einem Negativlabel.
- Meldungen und Modellausgaben gelangen nicht ungeprüft ins Training.
- Konfiguration und Quellen ändern Cacheidentität; veränderte oder korrupte Checkpoints werden abgelehnt.
- Eingefrorene Originalartefakte und einmal geöffnete Tests sind gegen Überschreiben geschützt.

Jeder neue Sicherheitstest muss an einem bewusst injizierten passenden Fehler scheitern, bevor er als Schutz gilt. Unit-Test-Fixtures dürfen synthetisch sein, jedoch nie als Forschungsdaten in data/ oder reports/ gelangen. Feste Seeds und reproduzierbare gespeicherte Vorhersagen; Fehler beheben und nachprüfen. Relevante pytest-Läufe, passende Verifikationsskripte und bei UI-Änderungen Frontendtests/Build tatsächlich ausführen; Fehler und Skips ehrlich berichten.

Pflege PROJECT_STATE.md, bei geändertem Gesamtstand PROJEKTUEBERBLICK.md und für neue Quellen DATA_SOURCES.md. Jeden eigenen verifizierten Meilenstein gezielt committen und pushen, ohne fremde Änderungen, Daten, Modelle, Einzelbefunde oder Geheimnisse. Keine History-Umschreibung eingefrorener Artefakte.

## 14. Erwartete Ergebnisse und zulässige Abschlusszustände

Liefere abhängig von der Machbarkeit:

1. Immer: Machbarkeitstabelle, Daten-/Referenzzahlen, geklärte Zielklasse und eine begründete Entscheidung je Komponente.
2. Bei geeigneten Daten: registrierter Pilot und reproduzierbare Auswertung der Flächenpriorisierung mit unabhängigen Einheiten, Intervallen und Einfachreferenzen.
3. Bei geeigneten Auslaufreferenzen: ehrliche Auslaufprüfung samt Szenarien und Unsicherheiten; andernfalls nur ausdrücklich unvalidierte technische Illustration oder begründetes Zurückstellen.
4. Eine kombinierte Karte nur bei nachvollziehbar begründeter Kombination; validiert nur im tatsächlich geprüften Umfang. Bei fehlendem Zusatznutzen getrennte Komponenten liefern.
5. Einen Meldeendpunkt nur bei sinnvoll verfügbarem Analysepfad; niemals automatische Umdeutung ungeprüfter Meldungen zu Wahrheit.
6. Einen kurzen Abschluss mit tatsächlich erreichtem Stand, unveränderten Originalergebnissen, bestandenen/fehlgeschlagenen/nicht ausgeführten Prüfungen, Blockern und den nächsten drei sinnvollen Aufgaben.

Erfolg bedeutet eine überprüfbare Antwort auf die Fragestellung. Wenn Daten oder Modellleistung die gewünschte Aussage nicht tragen, ist ein früh dokumentiertes Nein wertvoller als eine unbelegte Gefahrenkarte.
