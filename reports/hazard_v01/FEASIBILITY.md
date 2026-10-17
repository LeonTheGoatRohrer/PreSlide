# hazard_v01 — Machbarkeitsprüfung (17.10.2026)

Audit nach `GEFAEHRDUNGSANALYSE_MASTERPROMPT.md`, Phase 1. Es wurde **kein Modell trainiert und nichts ausgewertet**; Zahlen aus `feasibility.json` (erzeugt von `scripts/hazard_v01_audit.py`, liest den eingefrorenen V0.4-Bestand nur lesend). Arbeitsstand: origin/main inkl. V0.6–V0.9 eingemergt.

## Entscheidung in einem Satz

Die Daten tragen **keine validierte Anriss- oder Auslaufaussage**. Es wird kein Design registriert und kein Flächenmodell gerechnet. Ergebnis ist dieser Bericht; ein Auslauf darf höchstens als getrennte, ausdrücklich unvalidierte Illustration entstehen.

## Machbarkeitstabelle

| Komponente | Befund (Nachweis) | Entscheidung |
|---|---|---|
| Prozess | V0.4-Positive: 102 Hangmure, 47 „Hangmure bis Lockergesteinsrutschung“, 4 gemischt, **270 Lockergesteinsrutschung** (Untergruppe laut Inventar, nicht gleich Hangmure). Eindeutig „Hangmure“ nur 102 Ereignisse. Prozessqualität `QUAL_PROZ` bei 11 015 von 25 609 Inventareinträgen „keine Information“. V0.9-Prozessaudit der Medienereignisse (Freigabe verfehlt) zeigt zusätzlich 7 von 15 prüfbaren Fällen anderer Prozess. | Zielklasse nur Hangmure/gleitend-fließend; als Flächenaufgabe zu klein, siehe Unabhängigkeit |
| Ereignisort | Inventar liefert eine Koordinate ohne Angabe, ob Anriss, Transport, Ablagerung oder Schadensort (kein entsprechendes Feld; offene Frage steht in `reports/dataset_report/source_clarification_request.md`). | **unbekannt** |
| Geometrie | Alle 25 609 Inventar-, 9 441 Medien- und 1 742 WLV-Einträge sind Punkte; keine Anrisspolygone, Spuren oder Ablagerungsflächen. Positionsobergrenze der 423 Positiven: 5 m (319), 20 m (58), 100 m (46) — Kategorien, keine bestätigte Vermessung. | nur Punkt/Unsicherheit |
| Zeit | Tag gesichert (Tier A); Uhrzeit nur bei 40 Ereignissen (`clock`), 299 `daypart`, 84 `day`. t0 ist konservative Untergrenze. | Wetter nur als bereits getestete Zusatzvariante; kein Zusatznutzen belegt (V0.4–V0.9) |
| Gelände | 30-m-Skadi-Komposit (Objekt-Datum Apr. 2016 muss t0 vorangehen); 10-m-DGM verworfen; kein belegtes historisches 5-m-DGM; Eigenveränderung durch das Ereignis nicht geprüft. | 30 m reicht nicht für schmale Rinnen/Anrissformen; keine 5-m-Aussage |
| Unabhängigkeit | 423 Positive, **30 Einheiten**, 36 Episoden; Entwicklung 123/19, versiegelter V0.4-Test 300/11 (**bereits gesehen**). Größte Einheit (Stanz 2016) 66 % aller Anfragen mit Nachbarn. | zu wenig, dominiert, gesehen |
| Meldungsumgebung | 369 von 423 Anfragen haben ≥1 weiteres Ereignis derselben Episode ≤5 km, 54 nicht. Das stammt aber aus nur **13 Einheiten** (Entwicklung 8, Test 5). Ohne Stanz bleiben 126 Anfragen. | Entwicklung: 8 Einheiten — keine tragfähige Auswertung; Test gesehen |
| Auslaufprüfung | Keine unabhängig dokumentierten Auslauf-/Ablagerungsgeometrien im Bestand; Satellitenbefunde sind nach `PROJEKTUEBERBLICK`/Auftrag keine Wahrheitslabels. | **nicht prüfbar** |

## Entscheidung je Komponente

- **Auslöse-Priorität (Fläche):** *derzeit nicht sinnvoll prüfbar, zurückgestellt.* Ohne Anrissreferenz wäre ein „Anrissgebiet“ nur aus Inventarpunkten abgeleitet (verboten). Eine Fläche-gegen-Hintergrund-Prüfung hätte in der Entwicklung 8 Einheiten mit Nachbarn; der einzige große, ungesehene Rest fehlt. Bereits gesehene Ergebnisse (V0.4/V0.5: Gelände und Landbedeckung trennen, mögliche Meldeverzerrung) beantworten die Flächenaufgabe nicht.
- **Auslaufszenario:** *nur als technische/illustrative Demonstration umsetzbar*, ohne Leistungsaussage; quantitative Prüfung entfällt mangels Referenzgeometrien.
- **Kombinierter Prüfindex:** *zurückgestellt* — setzt zwei begründete Komponenten voraus.
- **Meldeendpunkt/UI:** *zurückgestellt* — fehlende wissenschaftliche Grundlage nicht durch UI ersetzen.

## Was neue Daten ändern würden (nächste drei Aufgaben)

1. Anfrage an GeoSphere/Landesstellen: bezeichnet die Koordinate Anriss oder Ablagerung, und gibt es Anrissflächen/Ablagerungspolygone (z. B. aus Ereignisdokumentationen) für datierte Hangmuren? Das ist der Blocker für beide Kernkomponenten.
2. Falls Polygone erhältlich: Zählung nach Prozessklasse und unabhängigen Episoden (≥ ~15 ungesehene Einheiten), dann neues Design in `config/hazard_v01.json` registrieren, bevor irgendein Modell läuft.
3. Historisches Gelände vor den Referenzereignissen (ALS-DGM mit Aufnahmedatum) beschaffen und Veränderung durch das Ereignis prüfen; erst dann Auslaufreferenz-Vergleich sinnvoll.

## Unverändert / nicht ausgeführt

Eingefrorene Artefakte (V0.3-Baseline, V0.4-Registrierung/Test, V0.9) unberührt; keine Verifikationsskripte und keine Python-Tests ausgeführt (nur Datenaudit, keine Änderung an `preslide/`). Der Pilot `mudslide_cascade_v01` liegt nur im lokalen Hauptcheckout (nicht auf origin/main); dort `verification.json` = PASS, lokale AUC 0,539 [0,406; 0,669] laut `summary.md`, hier nur eingesehen, nicht neu gerechnet.
