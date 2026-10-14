# Wie viele Entwicklungsgruppen sind sinnvoll möglich?

## Was hier als Gruppe zählt

Eine Ereignisgruppe umfasst einen betroffenen Hang und fünf gematchte Kontrollen. Eine Abhängigkeitsgruppe umfasst dagegen alle Ereignisgruppen, die für Training und Prüfung zusammenbleiben müssen. Im Gespräch sind mit Entwicklungsgruppen diese Abhängigkeitsgruppen im Entwicklungsbestand gemeint.

Im aktuellen Code entstehen zeitliche Episoden durch Verkettung von Ereignistagen mit höchstens drei Tagen Abstand. Österreichweite Gleichzeitigkeit wird konservativ berücksichtigt. Positive Standorte mit weniger als 2 km Abstand werden zusätzlich verbunden, auch über verschiedene Jahre. Im fertigen Experiment kommen Verbindungen durch positive Standorte und nahe Proben hinzu. Diese Einheiten sind praktische Abhängigkeitsblöcke, keine physikalisch bewiesenen unabhängigen Stürme.

## Neu berechnete Zahlen aus vorhandenen Daten

| Bestand | Kandidaten/Ereignisse | Verschiedene Tage | Zeitliche Episoden | Abhängigkeitsgruppen |
|---|---:|---:|---:|---:|
| V0.4 fertig | 423 | siehe gespeicherte Partition | 36 | 30, vollständig verarbeitet |
| Tier 1/A, Kandidaten | 500 | 75 | 48 | 35, vorläufig |
| Tier 1/A + Tier 2/A Medien | 823 | 197 | 110 | 66, vorläufig |
| Voriger Bestand + Tier 1/C | 902 | 199 | 111 | 64, vorläufig |

Vorläufig bedeutet hier: zeitliche Episoden plus Verbindungen positiver Standorte unter 2 km. Es wurden keine neuen Kontrollen erzeugt, keine Wetterdaten heruntergeladen und keine Modelle trainiert. Die Kandidaten wurden nach identischem Standort und Ereignistag dedupliziert. Die Kategorie C hat keinen unabhängig bestätigten narrativen Tag.

Die 66 Gruppen dürfen nicht mit 66 Entwicklungsgruppen verwechselt werden: Ein neuer Test braucht eigene, bisher ungesehene Gruppen. Wenn der vollständig geprüfte Bestand mindestens 50 brauchbare und hinreichend vielfältige Gruppen liefert, wäre beispielsweise eine vorab festgelegte Planung mit ungefähr 35 Entwicklungs- und 15 neuen Testgruppen möglich. Die tatsächlichen Zahlen müssen Abhängigkeiten und ungesehene Episoden erlauben; die Aufteilung darf nicht nach Modellleistung gesucht werden. 15 Testgruppen ergeben weiterhin deutliche Unsicherheit.

## Warum keine seriöse nationale Maximalzahl genannt werden kann

1. Das Inventar ist unvollständig und regional unterschiedlich dokumentiert.
2. Nicht jedes Ereignis hat einen brauchbaren Tag oder eine brauchbare Position.
3. Mehrere hundert Rutschungen desselben Unwetters bilden keine mehreren hundert unabhängigen Situationen.
4. Zusätzliche Ereignisse können bisher getrennte Gruppen durch zeitliche oder räumliche Ketten verbinden.
5. Ausschlüsse können solche Ketten auch wieder aufbrechen. Die vorläufigen 66 sind deshalb keine mathematische Obergrenze für jede spätere Kohortendefinition.
6. Die Datenquelle allein belegt keine hinreichende Umweltabdeckung oder Qualität der Kontrollhänge.

Die 71 räumlich-zeitlichen Einheiten des bisherigen Audits werden nicht als unabhängige Gruppen verkauft: Die vorhandene Regenkorrelationsprüfung hat diese Aufteilung abgelehnt (90. Perzentil 0,636 bei Schwelle 0,5).

## Was ich zur Vergrößerung ändern würde

Zuerst die 323 Medienereignisse separat prüfen: Verfahren der Erfassung, Prozess, Datum, Position und Überschneidungen. Erst danach Matching und Umweltabdeckung testen. Kategorie C und Zwei-Tages-Fälle bleiben getrennte Sensitivitätsanalysen; kein willkürliches exaktes Ereignisdatum vergeben.

Weitere Quellen, beispielsweise WLV und veröffentlichte regionale Inventare, würden danach auf zusätzliche Episoden geprüft. Ein gemeinsames Ereignis in zwei Quellen ist eine Bestätigung, kein zweiter Trainingsfall. Frühere Jahre kommen nur bei kompatibler Umweltabdeckung und dokumentierter Änderung des Zeitraums infrage. Die österreichweite Maximalzahl bleibt bis zu einem solchen Audit unbekannt.

Alle bereits bewerteten V0.4-Testgruppen sind für eine neue Versionsentwicklung gesehen. Sie können in einer transparent dokumentierten neuen Entwicklungskohorte genutzt werden, liefern aber keinen neuen unabhängigen Test. Neue Ereignisse derselben Episode oder nahe Standorte sind ebenfalls nicht automatisch ungesehene Testdaten.

## Reproduzierbarkeit

Eingaben: `data/v04/audit/candidates.json`, `data/v04/audit/audit_exclusions.json`, `data/v04/partition/partition.json`.

Regeln: `preslide/v04/units.py`, insbesondere `temporal_episodes` und `blocks`. Die Nachzählung wendet diese bestehenden Funktionen auf deduplizierte Kandidatentabellen an. Eingabeprüfsummen und exakte Auswahlregeln stehen in `gruppen_audit.json`.
