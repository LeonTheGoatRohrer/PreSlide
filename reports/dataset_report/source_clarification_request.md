# Anfrage zur Datennutzung und Qualitätsinterpretation

Entwurf — nicht versendet.

Sehr geehrtes GeoSphere-Austria-Team,

für das Forschungsprojekt PreSlide untersuchen wir, ob Umweltinformationen aus den 60 Tagen vor dokumentierten Rutschungen betroffene Hänge von nahe gelegenen, topografisch ähnlichen Kontrollhängen unterscheiden können. Das Projekt ist ein wissenschaftlicher Prototyp für einen österreichischen KI-Wettbewerb, kein operationelles Warnsystem.

Im öffentlichen ArcGIS-Verzeichnis ist folgender Dienst erreichbar:

https://gis.geosphere.at/maps/rest/services/naturgefahren/Naturgefahren/MapServer/0

Er enthält die für die Qualitätsprüfung hilfreichen Felder QUAL_LAGE, QUAL_MB, QUAL_PROZ, Prozessgruppe, Prozessuntergruppe sowie Datumsfelder und processTimeOrPeriodInfo. Das zugehörige Portal-Element ist jedoch als „Naturgefahren Test“ bezeichnet; eine Nutzungslizenz ist nicht angegeben.

Können Sie bitte klären:

1. Ist dieser Dienst zur externen wissenschaftlichen Nutzung freigegeben? Unter welcher Lizenz dürfen Daten verarbeitet und gegebenenfalls in einer Wettbewerbsdemo bzw. einem reproduzierbaren Datensatz weitergegeben werden?
2. Gelten die in QUAL_LAGE genannten Meterintervalle als Positionsunsicherheit der bereitgestellten Punktgeometrie? Repräsentieren die Punkte den Anriss, die Ablagerung oder lediglich eine allgemeine Ereignisposition?
3. Wie sind QUAL_MB und QUAL_PROZ sowie eventuell relevante Freigabefelder verbindlich zu interpretieren?
4. Wie verhalten sich Ereignisdatum_validFrom und die Einzelkomponenten zu mehrdeutigen Angaben in processTimeOrPeriodInfo? Gibt es eine autoritative Kennzeichnung taggenauer Ereignisse?
5. Falls der Testdienst nicht zur Nutzung bestimmt ist: Können Sie einen freigegebenen Export mit diesen Qualitätsangaben für Gleiten/Rutschen und Hangmuren ab 2018, gegebenenfalls ab 2015, bereitstellen?

Die bisherigen Ergebnisse beschränken sich auf einen lokalen Daten-Audit. Die Detaildaten wurden weder für Modelltraining noch für eine öffentliche Demo verwendet oder weitergegeben.

Vielen Dank für Ihre Unterstützung.
