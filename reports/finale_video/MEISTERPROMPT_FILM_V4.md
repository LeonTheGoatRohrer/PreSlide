# Meisterprompt: Talwacht-Finalfilm v4

Diesen Prompt in eine Claude-Code-Session im PreSlide-Repository einfügen.

---

Du überarbeitest den Talwacht-Finalfilm. Er entscheidet mit über die Platzierung im Wettbewerb. Ziel: Eine Jury versteht jede Zahl, glaubt jedes Bild und bekommt am Schluss Gänsehaut. Der Film soll Emotion übertragen, nicht nur Information.

## Ausgangslage

- Lies zuerst `AGENTS.md`, `PROJEKTUEBERBLICK.md`, `PROJECT_STATE.md` (Pflicht, §43).
- Filmcode: `scripts/finale_video/` (`build_film.py`, `mg/scenes.js`, `render_mg.mjs`, `voiceover_elevenlabs.py`, `export_data.py`). Faktencheck: `reports/finale_video/FAKTENCHECK.md`.
- Assets liegen gitignored unter `deliverables/finale_video/` (Worktree `finale-video-5min-84f3dd`). App-Aufnahmen: Worktree `video-pitch-script-497edf`, `deliverables/pitch/app3`.
- Stand v3: 293,1 s, 960 × 540. **Formularvorgabe: 3 bis 5 Minuten, höchstens 500 MB.** Harte Grenze 300 s.
- v3 nicht überschreiben; Ausgabe als neue Datei.

## Unverrückbare Regeln

- Nur belegte Zahlen. Jede neue Aussage kommt in den Faktencheck. Keine erfundenen Messwerte.
- Der versiegelte Test ist gesehen und bleibt unangetastet (§45). Nichts neu trainieren, bewerten oder auswählen. Schematische Grafiken werden als „Schema“ beschriftet.
- Keine kausalen oder Wahrscheinlichkeitsaussagen über Rutschungen. Talwacht warnt nicht.
- KI-Bilder bleiben als „KI-generierte Illustration“ gekennzeichnet. Sie zeigen keine echten Ereignisse.
- Keine urheberrechtlich geschützten Filmszenen oder Musikstücke nachahmen, keine Komponistennamen in Musikprompts.
- Bilder selbst prüfen (Kontaktbögen, Einzelbilder), Audio messen (Pegel, Spitzen). Was du nicht hören kannst, sagst du offen.

## 1. Mure statt Wildbach (Bild)

Beanstandet: Im Kaltstart (`c5_tear` = `k1`, `c7_slide` = `k2`) und bei der +15-%-Einblendung (`why1` = `a08`) fließt schäumendes, flüssiges Wasser wie in einem Wildbach. Das Holz treibt obenauf wie Streichhölzer und wirkt unecht.

Eine echte Mure sieht so aus:
- dickflüssiger Brei wie nasser Beton, dunkel graubraun, kein Weißwasser, keine Wellen, wenig Spritzer;
- steile, blockreiche Front, die sich wälzt; dahinter ein schlammiger Körper; Schübe statt gleichmäßigem Fließen;
- seitliche Schlammwälle (Levees) an den Rinnenrändern;
- ganze Fichtenstämme mit Wurzeltellern, halb eingebettet, gleich schnell wie der Schlamm, nicht treibend;
- enge steile Rinne oder durchweichter Hang im Bergwald, Regen, gedämpfte Farben;
- Augenzeugen-Anmutung: Tele, leichte Handkamera, Abstand vom sicheren Ufer.

Vorgehen: erst 2 bis 3 Modelle an einer Einstellung pilotieren, Kontaktbogen beurteilen, dann erst alle Einstellungen. Weißwasser, Fluss-Optik, treibendes Holz: verwerfen. Benötigt: Hangabriss, Murenfront zur Kamera, Totale mit Levees, dazu Schlussbilder (Berg in der Dämmerung, alte Narbe im Hang). Auch der Ton folgt dem Bild: tiefes Grollen, schlagende Steine, kein Wasserrauschen.

## 2. Problem 3: Diagramme, die zeigen, was gemeint ist

Die zufälligen Punkte links und rechts von „t₀“ sagen nichts aus und `t₀` ist nirgends erklärt. Neu, drei klar getrennte Takte, synchron zum Sprechtext:

1. **Zeitregel.** Echte Zeitachse eines echten Ereignisses (Tamsweg, 05.07.2023) mit echten täglichen Regenbalken der 60 Tage davor. Senkrechte Linie, beschriftet „Ereignistag t₀“. Links „Das darf das Modell sehen“. Rechts schraffierte, leere Fläche mit Schloss: „gesperrt, keine Daten ab t₀“. Keine Daten nach t₀ darstellen.
2. **Gruppenregel.** Falsch gegen richtig: Hang im Testteil, Zwilling im Trainingsteil, rot durchgestrichen, „das Modell erkennt nur den Ort wieder“. Daneben ganze Gruppen je in einem Topf, „immer zusammen“.
3. **Versiegelung.** Echter Ablauf als Zeitstrahl mit echten Daten aus `reports/v04/` (nur lesen): Plan festgeschrieben → Modell eingefroren → Test einmal geöffnet. Aufteilung: 123 Ereignisse Entwicklung, 300 versiegelt.

## 3. Ergebnis: 0,75 wovon?

Die Zahl braucht Einheit und Bedeutung: **AUC = Fläche unter der Kurve**, lokal innerhalb jeder Ereignisgruppe, jede Episode gleich gewichtet.

- Einblendung: „AUC 0,75“, darunter „0,5 = Münzwurf · 1,0 = immer richtig“.
- Paarvergleich animieren: betroffener Hang gegen Zwilling, wer steht in der Rangfolge vorne? Dann 100 Vergleiche als Raster, rund 75 richtig.
- Kurve grob zeigen: Diagonale = Zufall (Fläche 0,5), darüber eine Kurve, Fläche gefüllt, beschriftet „Schema · Fläche = 0,75“. Die Fläche muss rechnerisch 0,75 sein.
- Klarstellen: „Das ist keine Wahrscheinlichkeit für eine Rutschung.“
- Belegt anzeigen: 0,751 [0,633; 0,866], 11 Episoden, eine Episode stellt 243 von 300 Ereignissen, jedes Ereignis gleich gewichtet nur 0,67.

## 4. Problem 4: „Mit Wetter wird es besser“ ist missverständlich

Es klingt, als funktioniere die Software bei schönem Wetter besser. Text und Bild ändern zu: Ich dachte, mit **zusätzlichen Wetterdaten** liefert das Modell bessere Ergebnisse, und es hat mich überrascht, dass sich das nicht belegen ließ.

Balken zeigen: Gelände allein 0,70 → Gelände + Wetterdaten 0,75; Zuwachs +0,05 [−0,00; +0,11], Intervall berührt die Null, „nicht belegt“.

Danach die Extremwetter-Grafik verständlich machen: „extrem nass“ = die nassesten 5 % aller 3-Tage-Fenster an diesem Ort zu dieser Jahreszeit (1991 bis 2025). Also per Definition 5 von 100 bei Zufall. Gemessen: rund 25 von 100. Beschriftung „bei Zufall“ statt „erwartet“. Weiterhin: 35 Episoden, [11,8; 38,2], explorativ, Haupttest knapp nicht erfüllt, Meldebias möglich.

## 5. Problem 5: 0,93 erklären

Kurz sagen, dass auch das eine AUC ist: In 93 von 100 Vergleichen reiht allein der Abstand zu Straßen und Häusern den gemeldeten Hang vor einen ungemeldeten Umgebungspunkt, ohne jede Information über den Berg. Klarstellen, dass es hier nicht die Zwillinge sind. 0,78 [0,68; 0,89] ebenso als AUC beschriften.

## 6. „Hang-Check“ deutsch aussprechen

Die Stimme sagt es zu englisch. „Hang“ ist das deutsche Wort, kurzes a. Mehrere Schreibweisen im Sprachmodell testen (`Hang-Tscheck`, `Hangtscheck` usw.), geschrieben bleibt im Bild „Hang-Check“. Varianten für den Nutzer ablegen.

## 7. Finale

Nach der bestehenden Zeile „Denn der nächste Starkregen kommt. Und dann sollte man wissen, wo man zuerst hinschaut.“ folgt wörtlich:

> Der Berg warnt nicht. Der Berg erklärt nichts. Aber er hat Spuren hinterlassen, vierhundertdreiundzwanzig Mal. Ich habe angefangen zuzuhören. Das ist Talwacht.

Jeden Satz einzeln sprechen, ruhig, mit echten Pausen, kein Pathos. Bild: Berg → alte Narbe im Hang → die echten 423 Punkte leuchten nacheinander auf der echten Österreich-Karte auf → Gelände mit Puls → Titel.

## 8. Musik: der eigentliche Unterschied

v3 gemessen: Der Schluss (−18,5 dB) ist leiser als der Anfang (−15 dB), die Musik läuft flach durch und wird unter der Stimme weggeduckt. Am Ende eine Spitze über 1,0.

Neu: eigene Finalmusik, die vom App-Teil an über Minuten wächst.
- Dünn beginnen, dann tiefe Streicher, Puls, höheres Register, Chor; keine Stilkopie.
- Unter „der nächste Starkregen kommt“ schon deutlich spürbar, danach einige Sekunden ohne Stimme wirklich hochgehen.
- Unter dem Zitat weiter steigen, Stimme bleibt verständlich.
- Bei „Ich habe angefangen zuzuhören“ fast Stille: ein Atemzug.
- „Das ist Talwacht“: voller Einsatz exakt nach dem letzten Wort, Titel im selben Bild, langer Nachklang.

Der Höhepunkt wird gemessen und bildgenau auf diesen Moment gelegt. Vorspann, Hit und Abspann ohne Übersteuerung; Lautheit um −14 LUFS, Spitzen unter −1 dBTP.

## 9. Fertigstellung

- Final 1920 × 1080, Motion Graphics in voller Auflösung neu rendern, schwache 480p-Clips aufwerten oder ersetzen.
- Länge ≤ 300 s: Für die neuen Erklärungen an anderer Stelle kürzen (Kaltstart, „Fünf Probleme“, Daten, App, Fazit). Keine Aussage zu Grenzen streichen, die für die Ehrlichkeit nötig ist.
- Prüfen: Kontaktbogen des ganzen Films, Einzelbilder aller neuen Grafiken, Überlappungen der Sprachspuren (Warnungen aus `build_film.py`), Pegelkurve, Dauer, Dateigröße.
- `reports/finale_video/FAKTENCHECK.md` aktualisieren. Offene Punkte dort benennen, etwa Quellen, die nur als Abstract gelesen wurden.
- Am Ende: Pfad zur Datei, was geprüft wurde, was nur der Mensch beurteilen kann (Klang, Stimme, Gänsehaut).
