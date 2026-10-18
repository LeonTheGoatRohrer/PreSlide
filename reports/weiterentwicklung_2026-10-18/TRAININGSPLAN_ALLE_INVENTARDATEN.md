# Plan: Murenanfälligkeit aus allen Inventardaten lernen (Entwurf, nicht registriert)

Stand 18.10.2026. Auftrag des Nutzers: Nach dem Demo-Test sollen alle vorhandenen Inventardaten, besonders die vielen
Hangmuren von 2005 und den 2000er-Jahren, für ein Trainingsmodell verwendet werden, das lernt, **in welcher Umgebung
oft Muren abgehen**. Dieser Entwurf ist die Grundlage für eine eigene, vorab registrierte Version. Noch nichts
gerechnet.

## 1. Warum das neu ist

Bisher hat Talwacht nur 423 Ereignisse mit gesichertem Tag (ab 2016) genutzt, davon 102 reine Hangmuren, jeweils
gegen fünf ähnliche Nachbarhänge am selben Tag. Diese Frage („Welcher Hang am selben Tag?“) braucht ein genaues
Datum. Die neue Frage („Wo im Gelände gehen oft Muren ab?“) ist **statisch**: Sie braucht kein genaues Datum, nur
eine gute Lage. Dadurch werden die übrigen Inventardaten nutzbar:

- 3.416 reine Hangmuren im GeoSphere-Inventar, davon 2.686 genau verortet (≤ 20 m laut Inventar).
- Mehrere große Ereignisdokumentationen mit Geländeerhebung, z. B. Vorarlberg/Tirol 2005 (1.176 genau verortet).

## 2. Design in einem Satz

Positive sind genau verortete Hangmuren, Hintergrund sind Zufallspunkte im selben Erhebungsgebiet; ein Modell lernt
den Unterschied aus Gelände, Landbedeckung und Geologie und wird an **ganzen Gebieten geprüft, die es im Training
nie gesehen hat**.

## 3. Zur Idee „wo einer ist, zeigt, wo ein anderer sein könnte“

Die Idee ist richtig, wenn das Modell die **Umgebung** lernt: Viele Muren in einem Gebiet zeigen, welche Hänge dort
typisch betroffen sind (Neigung, Hangform, Rinnen, Landbedeckung, Untergrund). Das leistet das Design oben.

Was das Modell **nicht** als Eingabe bekommen darf: Abstand oder Anzahl anderer gemeldeter Muren in der Nähe. Sonst
lernt es, wo gemeldet wurde, statt wo Muren abgehen (Meldebias), und bei der Prüfung wäre das zirkulär. Die
„Nachbarschaft“ steckt stattdessen in Merkmalen der Umgebung, etwa Einzugsgebiet, Hangposition auf 150 m und 500 m,
Rinnen und Krümmung.

## 4. Bausteine

| Baustein | Festlegung (Vorschlag) |
|---|---|
| Positive | GeoSphere-Inventar, Prozessuntergruppe „Hangmure“ (optional getrennt: „Hangmure bis Lockergesteinsrutschung“), Lage ≤ 20 m; Mehrfachpunkte < 30 m zusammenfassen |
| Gebiete | Ereignisdokumentationen (`RegKatE_ID`) und für Punkte ohne Projekt feste Rasterkacheln; Gebietsgrenzen nicht aus den Punkten ableiten (amtliche Gemeindegrenzen nach fester Regel) |
| Hintergrund | Zufallspunkte im selben Gebiet, Verhältnis fest (z. B. 1 : 1), Puffer um alle bekannten Inventarpunkte, Neigung ≥ 5° |
| Merkmale | wie V0.4-Gelände: Höhe, Neigung, Exposition (zirkulär), Krümmungen, Rauigkeit, TPI 150/500 m, Hangposition, Einzugsgebiet, TWI; Landbedeckung CORINE passend zum Ereignisjahr; Geologie 1 : 500 000. **Keine** Wetter-, Koordinaten- oder Meldeabstandsmerkmale |
| Modelle | Neigung allein (Basislinie), logistische Regression, Gradient Boosting. Kein neuronales Netz: Dafür gibt es keinen Grund und zu wenige unabhängige Gebiete |
| Prüfung | Leave-one-area-out: jedes Gebiet einmal ganz zurückhalten. Hauptkennzahl AUC gegen Hintergrund im zurückgehaltenen Gebiet, Differenz zur Neigung mit Intervall über Gebiete |
| Meldebias | wie V0.7: Abstand zu Straßen/Gebäuden aus OSM nur als Kontrolle, nicht als Merkmal; Ergebnis getrennt für straßenferne Hintergrundpunkte |
| Demo | Werte im Demogebiet nur aus dem Modell, das dieses Gebiet **nicht** im Training hatte |

## 5. Ehrliche Erwartung

Die internationale Arbeit (susceptibility_v01) fand zwischen weit entfernten Regionen keinen belegten Vorteil gegenüber
der Neigung allein. Innerhalb Österreichs und desselben Prozesses (Regen, Hangmure) kann das besser sein; belegt ist
es nicht. Auch dieses Modell liefert eine **relative Anfälligkeit**, keine Wahrscheinlichkeit, weil Hintergrund und
Verhältnis gewählt sind und das Inventar unvollständig ist.

## 6. Reihenfolge

1. Demo-Test der eingefrorenen Prüfstufen an ungesehenen Gebieten abschließen und einfrieren (läuft in der
   Wirkungsketten-Session).
2. Diesen Entwurf als eigene Version registrieren (`config/…json`, schreibgeschützt), bevor ein Geländewert gerechnet
   wird.
3. Pilot 1 → 5 → 20 Gebiete, dann alle.
4. Ergebnis in die Website: Anfälligkeitskarte im Demogebiet aus dem zurückgehaltenen Modell, mit Prüfergebnis.
