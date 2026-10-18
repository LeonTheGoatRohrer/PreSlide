# extremwetter_v01 – Fehlerinjektion der Sicherheitstests

Stand 18.10.2026. Jeder Fehler wurde einzeln in den Code eingebaut, `tests/test_extremwetter.py` ausgeführt
(53 Tests, ohne Fehler: 53 bestanden, 0 übersprungen) und der Code danach wiederhergestellt (per `diff` geprüft).

| # | Eingebauter Fehler | Ergebnis |
|---|---|---|
| M1 | Primärfenster endet einen Tag später (enthält den SPARTACUS-Tag vor dem Ereignistag, der bis 07:00 des Ereignistags reicht) | 35 Tests scheitern |
| M2 | Ereignisjahr nicht aus den Referenzjahren ausgeschlossen | 2 scheitern |
| M3 | Ausschlusspuffer um dokumentierte Ereignisse 2 statt 3 Tage | 2 scheitern |
| M4 | Kalenderversatz vor dem Jahreswechsel angewendet (Jahresgrenzen-Fehler) | 1 scheitert |
| M5 | Gleichstände im Perzentilrang voll statt zur Hälfte gezählt | 3 scheitern |
| M6 | Bootstrap zieht einzelne Ereignisse statt ganzer Episoden | 1 scheitert |
| M7 | NaN in der Wetterreihe wird nicht abgelehnt | 1 scheitert |
| M8 | Nullverteilung ohne Leave-one-out (Pseudo-Fall zählt sich selbst als Referenz) | 1 scheitert |

Zusätzlich wurden die Fallfenster der ersten 20 Ereignisse im Pilot unabhängig aus den gecachten Rohantworten
(ohne Projektcode) nachgerechnet: 20/20 identisch.
