# UI-Überarbeitung für Jury und Zuschauer (15.10.2026)

Ziel: Ein Komitee soll in 60 Sekunden verstehen, **was** untersucht wurde, **wie** und **was herauskam**, und danach gezielt in die Tiefe gehen können. Weniger Fließtext, klare Orientierung, kein Kinderton. Keine Änderung an Daten, Modellen oder Kennzahlen; alle Zahlen kommen weiter aus den API-Bündeln.

## Befunde am heutigen Stand
1. Zu viel Fließtext pro Seite; die zentrale Aussage steht erst nach mehrmaligem Scrollen.
2. Interne Versionsnamen (V0.4, V0.5, Abhängigkeitseinheiten, lokale AUC) dominieren; Laien finden keinen Einstieg.
3. Keine Seitenorientierung: man weiß nicht, welche Abschnitte folgen, und das beste Material (echtes Beispiel mit Karte) liegt zugeklappt versteckt.
4. Ergebnisse zeigen zwei lange, fast gleich aufgebaute Studienblöcke untereinander. Der Hauptbefund geht darin unter.
5. Es gibt keine „Idee in einem Bild".

## Änderungen
**Global**
- Studien erhalten sprechende Namen: *Hauptstudie* (V0.4, strenger Test) und *Ergänzungsstudie* (V0.5, explorativ). Die Versionsnummer bleibt klein als Etikett.
- Auf jeder Seite eine mitlaufende Abschnittsleiste („Auf dieser Seite") mit Sprunglinks und Hervorhebung des aktuellen Abschnitts.
- Kopfzeile: Beschriftung der Seiten als klarer Dreischritt; ausführliche Bildunterschrift entfällt.
- Tonfall: sachlich, kurze Sätze, Fachbegriffe in Kurzform mit Info-Symbol (bestehendes InfoTip-System), keine Erklärboxen auf Schulniveau.

**Projekt**
- Oben: *Kurzfassung* in drei Karten: Frage · Antwort · Grenze.
- Kennzahlenleiste (aus API): Ereignisse, Kontrollhänge je Ereignis, Merkmale, Hauptergebnis mit Intervall, unabhängige Testeinheiten.
- „Die Idee in einem Bild": Zeichnung Ereignishang + fünf ähnliche Vergleichshänge + gemeinsame Zeitachse.
- Bisherige Textabschnitte (Forschungsfrage, Fähigkeiten) auf je ein bis zwei Sätze verdichtet; Ausblick bleibt, gekürzt.

**Vorgehen**
- Sechs Schritte als kompakte Pipeline-Grafik mit Ein-Satz-Beschreibung.
- Echtes Beispiel mit Karte und Wettervorgeschichte steht **direkt sichtbar** (nicht zugeklappt) an zweiter Stelle.
- Vergleichsdesigns, Zeitachse und Schutzregeln bleiben, aber als knappe Karten; Quellen und Qualitätsregeln bleiben zugeklappt.

**Ergebnisse**
- Oben ein Hauptbefund-Panel mit Umschalter *Hauptstudie | Ergänzungsstudie*: Balkendiagramm (Gelände / Wetter / Kombination), Zufallslinie, Intervall, Wetter-Zusatznutzen auf einen Blick.
- Drei Kernaussagen als Karten (Gelände trägt Signal · Wetter-Zusatznutzen nicht belegt · Meldebias möglich).
- Grenzen als kompakte Karten; Tiefenanalysen bleiben in aufklappbaren Bereichen.

## Nicht angefasst
Daten, Modelle, eingefrorene Artefakte, Kennzahlenberechnung, API. Neue Wortwahl nur dort, wo sie Messwerte nicht umdeutet (kein Wetternutzen-Beleg, Meldebias-Hinweis, retrospektiv).

## Prüfung
`npm test`, `npm run build`, Sichtprüfung Desktop und 375 px, Konsole fehlerfrei, Direktlinks `/#/projekt`, `/#/vorgehen`, `/#/vorgehen/beispiel`, `/#/ergebnisse`, `/#/ergebnisse/v04` funktionieren weiter.
