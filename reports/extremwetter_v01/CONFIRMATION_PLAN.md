# Bestätigungsplan Extremwetter (registriert, nicht ausgeführt)

Stand: 18.10.2026. Geschrieben, **bevor das explorative Gesamtergebnis von extremwetter_v01 angesehen wurde**
(bekannt waren nur die Perzentilränge der 20 Pilotereignisse). Der Plan wird mit diesem Commit eingefroren;
Änderungen nur als datierte Ergänzung mit Begründung und nur, bevor neue Ereignisse ausgewertet werden.

## Warum ein eigener Bestätigungsschritt

extremwetter_v01 verwendet 423 Ereignisse, die schon in V0.4/V0.5 gesehen wurden, und prüft viele Varianten
(51 Vergleichszeilen). Das Ergebnis ist darum explorativ. Eine belastbare Aussage braucht **neue, ungesehene
Sturmepisoden** und **genau einen vorab festgelegten Test**.

## Bestätigungskohorte

1. **Quelle:** neuer Abzug des GeoSphere-Naturgefahren-Inventars (Abrufdatum nach dem 18.10.2026), gleiche
   Endpunkte wie V0.4.
2. **Einschluss:** unverändert nach `config/v04.json` (Prozessgruppen Gleiten/Rutschen und Fließen mit den fünf
   Untergruppen, Qualitätsstufe 1, Positionsklasse ≤ 100 m, Datumsstufe A nach `preslide/v04/dates.py`
   RULES_VERSION v04-dates-1, Deduplikation gleicher Ort/Tag).
3. **Neu und ungesehen:** Ein Ereignis ist nur zulässig, wenn
   - seine ID nicht unter den V0.4-Auditkandidaten (`data/v04/audit/candidates.json`) und nicht unter den
     102 Baseline-Kandidaten ist, **und**
   - sein Ereignistag mehr als 3 Tage von jedem Ereignistag der 423 Kohortenereignisse entfernt ist (keine
     Episode, deren Wetter schon angesehen wurde).
4. **Getrennt geführt, nicht Teil des Haupttests:** Medienereignisse (Qualitätsstufe 2) und Datumsstufen B/C.
   Sie dürfen beschreibend berichtet werden, aber nie den Haupttest ersetzen oder ergänzen.

## Festgelegter Test (genau einer)

- Design, Wetterquelle, Referenzregel, Ausschlussregel und Statistik **identisch** mit
  `config/extremwetter_v01.json` (SHA-256 `98e33aa7ea3c56afe35695be9ba2d33ba1b755eb7e482a34dcc9880f3f0b2a88`).
- **Primärstatistik:** episodengewichteter mittlerer Perzentilrang des 3-Tage-Niederschlags, Fenster endet mit
  dem SPARTACUS-Tag *Ereignistag − 2* (Messung bis 07:00 MEZ des Vortags), Referenz 1991–2025 ohne Ereignisjahr,
  ±15 Kalendertage, Ausschluss dokumentierter Rutschungstage ≤ 10 km und ±3 Tage.
- **Unabhängige Einheit:** zeitliche Episode (Tagesabstand ≤ 3 Tage) innerhalb der Bestätigungskohorte.
- **Erfolgskriterium (beides nötig):** einseitiges p < 0,05 gegen die Pseudo-Fall-Nullverteilung (5000 Ziehungen,
  Seed 20261019) **und** untere Grenze des 95-%-Episoden-Bootstrap-Intervalls (2000 Ziehungen, Seed 20261018)
  über 0,5.
- **Mindestgröße:** ausgewertet wird erst, wenn die Kohorte **mindestens 10 Episoden** enthält. Vorher wird nur
  gezählt (Ereignisse, Episoden), keine Wetterstatistik berechnet. Wird die Mindestgröße nie erreicht, bleibt
  das Ergebnis „nicht bestätigt, nicht widerlegt“.
- **Keine Alternativen:** kein Wechsel von Fenster, Fensterende, Referenzjahren, Gewichtung oder Schwelle nach
  dem Ergebnis. Alle Sekundärvergleiche aus extremwetter_v01 dürfen beschreibend mitberichtet werden, zählen
  aber nicht als Bestätigung.

## Ablauf

1. Neuen Inventarabzug cachen, Kohorte bilden, Zählung und Ausschlussgründe als `confirmation/cohort.json`
   speichern und committen, **bevor** Wetter abgefragt wird.
2. Pilot 1 → 5 → 20 Ereignisse: Fallfenster gegen die Rohantwort prüfen (nur Datenprüfung).
3. Einmalige Auswertung; das Skript schreibt `confirmation/test_result.json` und verweigert jede zweite
   Ausführung (wie der versiegelte V0.4-Test).
4. Bericht: Ergebnis mit Intervall, Nullreferenz und Episodenzahl; Hinweis auf Meldebias und dass Bestätigung
   eines Zusammenhangs keine Kausalität zeigt.

## Bekannte Grenzen schon vor der Ausführung

- Meldebias wirkt auch in neuen Ereignissen: Nach Unwettern wird vollständiger kartiert.
- Neue Ereignisse liegen zeitlich nach 2026-06; SPARTACUS ist mit etwa einem Tag Verzug verfügbar, die
  Referenzjahre enden 2025.
- Bei wenigen großen Stürmen kann eine einzelne Episode das Ergebnis dominieren; die Primärgewichtung (jede
  Episode gleich) begrenzt das, beseitigt es aber nicht.
