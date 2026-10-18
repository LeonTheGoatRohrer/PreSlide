# Meisterprompt: Talwacht neu – ein Werkzeug für Menschen am Hang

Diesen Text vollständig als Auftrag in eine neue Session geben. Er ersetzt für die Gestaltung den älteren
`MEISTERPROMPT_JURY_WEBSITE.md` („Föhnnacht“): Dessen Regeln zu Ehrlichkeit, Datenbindung und Medien gelten weiter,
seine Seitenstruktur und sein dunkles Farbkonzept nicht. Entscheidungen in diesem Text sind gefallen. Nicht neu
diskutieren, sondern umsetzen. Rückfragen nur bei echten Blockern.

---

## 0. Rolle, Anspruch, Auftrag

Du bist Creative Director und Senior Frontend Engineer in einer Person. Du hast Produktseiten gebaut, die man sich
merkt (Linear, Apple Weather, Windy, Felt, Mapbox Showcase, swisstopo). Dein Auftrag: die Weboberfläche von
**Talwacht** (internes Paket `preslide`) **komplett neu bauen**, als Werkzeug für Menschen, nicht als
Projektpräsentation.

Messlatte: Wer die Seite öffnet, soll innerhalb von fünf Sekunden verstehen, **was er hier für sich tun kann**, und
innerhalb von dreißig Sekunden **seinen eigenen Ort** auf einer echten 3D-Karte sehen. Danach soll er denken:
„Das kann nicht von einem Schulprojekt sein.“ Die Konkurrenz baut mit KI-Hilfe. Durchschnitt reicht nicht. Jedes
Detail (Abstände, Übergänge, Ladezustände, Fehlermeldungen, Handy) ist Teil der Bewertung.

Grundsätze in dieser Reihenfolge:
1. **Nutzer zuerst.** Die Seite beantwortet zuerst die Frage des Nutzers („Welche Hänge bei mir zuerst
   ansehen?“), danach „Warum kann ich dem trauen?“, ganz zuletzt „Wie wurde das erforscht?“.
2. **Ehrlich.** Keine Wahrscheinlichkeit, keine Warnung, keine erfundenen Zahlen. Die Ehrlichkeit wird gestaltet,
   nicht versteckt.
3. **Alles drin, nichts leer.** Jede bisherige Studie, jede Kennzahl, jede Abbildung bleibt erreichbar, aber an dem
   Ort, an dem ein Mensch sie sucht. Keine Seite, kein Menüpunkt, kein Abschnitt ohne echten Inhalt.

## 1. Start der Session

1. `AGENTS.md`, `PROJEKTUEBERBLICK.md` (vollständig), `PROJECT_STATE.md` lesen. Dann diesen Prompt noch einmal ganz.
2. Skills laden: `frontend-design:frontend-design` und `ui-ux-pro-max`. Ihre Hinweise gegen generische
   KI-Ästhetik ernst nehmen.
3. Branch: `git fetch origin`.
   - Wenn `origin/claude/hangcheck-v01` existiert und die Seite `#/hangcheck` enthält: `git switch -c
     claude/website-redesign origin/claude/hangcheck-v01`.
   - Sonst: `git switch -c claude/website-redesign origin/claude/meisterprompt-hangcheck` und
     `origin/claude/hangcheck-v01` an jeder Meilenstein-Grenze erneut prüfen und hineinmergen, sobald er da ist.
     Bis dahin den Hang-Check-Bereich gegen die bestehende Hangkarte (`/api/hangkarte`) bauen und die Umstellung
     auf `/api/hangcheck` als letzten Schritt von Meilenstein 2 einplanen.
   Danach in jedem Fall `git merge origin/claude/meisterprompt-hangcheck`: Nur dieser Branch enthält die Bilder in
   `frontend/public/media/` und diesen Prompt (der Hang-Check-Branch wurde davor abgezweigt). Prüfen, dass
   `frontend/public/media/tal.webp` danach vorhanden ist.
   Der Hang-Check wird in einer parallelen Session gebaut (`MEISTERPROMPT_HANGCHECK.md`). Seine Logik, API und Tests
   übernimmst du unverändert; du gestaltest nur Oberfläche und Einbettung.
4. Im Worktree fehlen `data/`, `models/`, `.venv/`, `frontend/node_modules`: Junctions zum Hauptcheckout
   `C:\Users\mario\Documents\HomeProjects\PreSlide` über eine kleine `.cmd`-Datei mit `mklink /J` im Scratchpad
   anlegen und mit `cmd //c` ausführen.
5. App starten (`.claude/launch.json`, `preslide-api`, Port 8010, vorher `npm run build`). Alle heutigen Seiten
   einmal durchklicken und Screenshots als Vorher-Stand im Scratchpad ablegen.

## 2. Was heute falsch ist (nicht wiederholen)

- Die Seite präsentiert das Projekt statt dem Nutzer zu helfen. Der Hang-Check liegt versteckt im Bereich
  „Forschung“.
- „Forschung“ ist ein eigener Menüpunkt mit vier Unterseiten, die kaum Inhalt haben oder sich überschneiden
  (Projekt, Vorgehen, Ergebnisse im Detail, Hangkarte).
- Die Navigationsleiste ist eine dünne Textzeile ohne Halt, ohne klare Hauptaktion und ohne Zustand.
- Weiße Fläche, Haarlinien und Helvetica: korrekt, aber austauschbar. Keine Bilder, keine Tiefe, keine Bewegung.
- Viele kleine graue Texte, Kennzahlen ohne Einordnung, Fachwörter ohne Erklärung.

## 3. Informationsarchitektur (fest)

Hauptnavigation, genau vier Einträge plus eine Hauptaktion:

| Menüpunkt | Route | Frage des Nutzers | Inhalt |
|---|---|---|---|
| **Hang-Check** (Hauptaktion, als Knopf) | `#/check` | „Was ist bei mir?“ | Vollbild-Kartenwerkzeug |
| **So funktioniert's** | `#/so-funktionierts` | „Woher weiß Talwacht das?“ | Methode als Geschichte |
| **Wie belastbar** | `#/belastbar` | „Kann ich dem trauen?“ | Ergebnisse, Grenzen, Gegenproben |
| **Studienatlas** | `#/studien` | „Ich will alles sehen.“ | Alle Studien, Daten, Abbildungen |
| **Über** | `#/ueber` | „Wer, welche Daten, welche KI?“ | Team, Quellen, Lizenzen, Medien und KI |

`#/` ist die Startseite. Es gibt **keinen** Menüpunkt „Forschung“ und keine Unterseiten-Leiste mehr.

Alle alten Adressen bleiben gültig und leiten sauber um (Test dazu): `#/start` → `#/`, `#/pruefgebiete` →
`#/so-funktionierts#wirkungskette`, `#/befunde` → `#/belastbar`, `#/methodik` → `#/so-funktionierts`,
`#/forschung`, `#/projekt`, `#/vorgehen`, `#/ergebnisse`, `#/ergebnisse/v04` usw. → passender Anker im
`#/studien`, `#/hangkarte` → `#/check`, `#/hangcheck` → `#/check`, dazu die bisherigen Legacy-Anker aus
`frontend/src/navigation.js`.

### 3.1 Startseite `#/` (in dieser Reihenfolge)

1. **Hero (100 svh)**: Vollflächig `media/tal.webp` (Handy `tal-1200.webp`), darüber eine feine, langsame
   Regen-Ebene (Canvas, 2D, ca. 120 schräge Linien in `--glacier` mit 6–12 % Deckkraft, pausiert bei reduzierter
   Bewegung). Im ruhigen Himmel links die Überschrift, darunter **direkt das Suchfeld**:
   „Gemeinde oder Ort eingeben“ mit Vorschlagsliste, daneben „Mein Standort“. Eine Auswahl startet den
   **Signatur-Übergang** (3.6). Unten rechts die Kennzeichnung „KI-generierte Illustration“.
2. **Drei Schritte, ein Satz je Schritt**, links `media/hang.webp` (4:5) groß, rechts die Schritte als Karten:
   Ort wählen · „Starkregen erwartet“ einschalten · Hänge sehen, die man zuerst ansieht. Knopf „Jetzt prüfen“.
3. **Live-Beispiel**: echtes, vorab berechnetes Ergebnis eines Beispielgebiets (aus dem Cache, ohne Wartezeit) als
   kleine 3D-Karte mit Prüfstufen. Text: was man sieht, in zwei Sätzen.
4. **Worauf das beruht**: drei Zahlenkarten, Werte nur aus der API, jeweils mit Intervall und einem Satz in
   Alltagssprache: dokumentierte Ereignisse (`counts.complete_groups`), Ergebnis im versiegelten Test
   (`test.primary` mit `ci95` und Zufallslinie), Gebietstest an ungesehenen Gebieten, sofern sein Bericht im
   Checkout liegt (sonst diese Karte durch „Wetter bringt keinen belegten Zusatz“ ersetzen). Zahlen zählen beim
   Sichtbarwerden hoch.
5. **Wofür es gedacht ist**: `media/morgen.webp` breit, darauf drei kurze Anwendungsfälle: Gemeinde nach dem
   Unwetter, Straßenerhalter bei der Kontrollfahrt, Anrainer, der seinen Hang verstehen will.
6. **Was Talwacht nicht kann**: ruhiger, dunkler Abschnitt (`--slate-900`), vier klare Sätze (keine Warnung, nicht
   markiert heißt nicht sicher, kein Wetter im Modell, Meldebias). Link auf „Wie belastbar“.
7. **Footer**: Quellen, „Medien und KI“, Kontakt/Team, Datenstände.

### 3.2 Hang-Check `#/check` (das Herz der Seite)

- Vollbild-Karte (MapLibre, echtes 3D-Gelände, siehe 3.7), darüber ein schwebendes Panel: Desktop links
  420 px, Handy als **Bottom Sheet** mit drei Rasthöhen (Kopf, halb, voll), mit Ziehgriff und Tastaturbedienung.
- Panel-Ablauf als klare Stufen mit Fortschritt: **1 Ort** (Suche, Kartenklick, Standort, Beispiele) → **2 Umkreis**
  (Regler 1–3 km, Kreis live auf der Karte) → **3 „Starkregen oder Unwetter erwartet“** (großer Schalter) →
  **Ergebnis**.
- Ergebnis-Auftritt: Die Prüfstufen erscheinen als **radiale Welle** vom gewählten Punkt aus (600–900 ms), die
  fünf Prüfpunkte fallen gestaffelt als nummerierte Marker ein. Liste „Hier zuerst hinschauen“ mit Höhe, Neigung,
  Landbedeckung im Klartext; Hover/Fokus in der Liste hebt den Marker hervor und umgekehrt; Klick fliegt hin.
- Falls der Hang-Check Fließwege und Straßen/Gebäude liefert: als eigene, abschaltbare Ebenen mit Legende
  („Szenario, ungeprüft“; „heutiger OpenStreetMap-Stand“).
- Pflicht-Hinweisblock aus `MEISTERPROMPT_HANGCHECK.md` 3.4 sichtbar im Ergebnis, nicht im Tooltip.
- Zustand in der URL (`#/check?lon=…&lat=…&r=…&regen=1`), Knopf „Link kopieren“.
- **Prüfliste drucken**: Druckansicht (eigenes Print-CSS) mit Kartenbild (`preserveDrawingBuffer` nur für den
  Export), Ortsname, Datum, Datenständen, Liste der Prüfpunkte mit Koordinaten und dem Hinweisblock. Für Gemeinden
  ist das der greifbarste Alltagsnutzen.
- Lade- und Fehlerzustände gestaltet: Skelett mit Fortschrittstext („Gelände lesen“, „Landbedeckung“,
  „Einstufen“), 503 → „Gerade läuft eine andere Berechnung, gleich noch einmal versuchen“, 422 außerhalb
  Österreichs → freundlich mit Karte von Österreich.

### 3.3 So funktioniert's `#/so-funktionierts`

Scrollgeschichte mit angehefteter Grafik (sticky), fünf Kapitel:
1. **Gemeldete Hänge**: echte Ereignispunkte aus `/api/pruefgebiete` auf einer Österreichkarte, nach Jahren
   einblendbar.
2. **Fünf Doppelgänger**: ein echtes Baseline-Beispiel (`/api/cases`) zeigt den gemeldeten Hang und seine fünf
   ähnlichen Nachbarhänge; Neigung, Höhe und Ausrichtung als kleine Vergleichsbalken.
3. **Was das Modell lernt**: Gelände, Landbedeckung, Geologie als Ebenen, die sich übereinanderlegen; Liste der
   wichtigsten Merkmale aus den gespeicherten Berichten, mit dem Satz „stützt sich stark auf“, nie „verursacht“.
4. **Die Wetterfrage**: 60-Tage-Regenverlauf des Beispiels (bestehende Wetterdaten); Ergebnis: kein belegter
   Zusatznutzen.
5. **Vom Hang zur Straße** (Anker `wirkungskette`): die bestehende Wirkungskette Stanz (`WirkungsketteView`) im
   neuen Stil, als Demonstration gekennzeichnet.

### 3.4 Wie belastbar `#/belastbar`

Eine ehrliche, schön gesetzte Ergebnisseite. Jede Aussage als Karte mit: Satz in Alltagssprache, Kennzahl mit
Intervall und Zufallslinie (bestehende `IntervalPlot.vue` neu gestaltet), Zahl unabhängiger Einheiten, Status-Chip
(versiegelter Test / explorativ / Demonstration), Link „Details im Studienatlas“. Inhalte: Gelände trennt über
Zufall (V0.4) · Wetter ohne belegten Zusatz (V0.4–V0.9) · Meldebias (V0.7, V0.7b falls vorhanden) · Extremwetter
am selben Ort (`/api/extremwetter`) · Gebietstest (falls vorhanden) · reine Hangmuren (`/api/hangmuren_pilot`,
503 = „Bericht liegt nur lokal“) · Satellit (`/api/satellite`). Darunter „Grenzen“ als klare Liste.

### 3.5 Studienatlas `#/studien`

Ersetzt den kompletten Forschungsbereich. **Alles, was heute irgendwo steht, ist hier, nichts doppelt.**
- Kopf: Zeitleiste aller Versionen (V0 … V0.9, Extremwetter, Wirkungskette v01–v03, Anfälligkeit international,
  Hangkarte, Hang-Check, `anfaelligkeit_at_v01`, Satelliten-Pipeline B, neuronale Murensuche) mit Datum und
  Status. Filter-Chips: Kernfrage · Wetter · Meldebias · Satellit · International · Anwendung · Plan.
- Jede Studie als Karte, die sich zu einem **Drawer** öffnet: Frage, Design, Ergebnis mit Intervall, Einheiten,
  Status, Grenzen, Abbildungen, Link zum Bericht (Markdown im Drawer gerendert) und zur Verifikation (PASS/FAIL).
- Die heutigen Detailkomponenten wandern in die passenden Drawer, neu gestaltet, Inhalt unverändert:
  `V04Results.vue`, `V05Results.vue`, `BenchmarkOverview.vue`, `StabilityFigures.vue`, `EventExplorer.vue`,
  `SatelliteResults.vue`, `ExtremwetterSection.vue`, `ResearchDetails.vue` (Baseline-Beispiel, Matching, Wetter),
  Hangkarte (als „Vorgänger des Hang-Checks“).
- **Datenbindung**: neuer, kleiner Endpunkt `GET /api/studien` (`preslide/studien.py`), der eine Registry
  (`config/studien_atlas.json`: id, Titel, Gruppe, Datum, Status, Pfade zu `summary.md`, `verification.json` und
  den JSON-Dateien mit Kennzahlen samt JSON-Pfad des Werts) liest und **nur gespeicherte Werte** ausliefert. Fehlt
  eine Datei, wird die Studie mit `verfuegbar: false` und Grund ausgeliefert, nie mit Ersatzwert. Bericht-Markdown
  über `GET /api/studien/{id}/bericht` (nur Pfade aus der Registry, kein freier Dateizugriff). Ein Test prüft, dass
  jeder Ordner `reports/*/` mit `summary.md` in der Registry steht oder ausdrücklich ausgenommen ist.
- Studien, deren Branch noch nicht integriert ist (V0.7b, Gebietstest, `anfaelligkeit_at_v01`-Ergebnis), erscheinen
  automatisch, sobald ihre Berichte im Checkout liegen. Nicht selbst mergen; in der Registry vorbereiten.

### 3.6 Signatur: vom Bild zur echten Karte

Das eine Element, an das man sich erinnert. Wählt der Nutzer im Hero einen Ort:
1. Das Suchfeld gleitet nach oben in die Navigationsleiste, die Überschrift blendet aus (250 ms).
2. Das KI-Bild des Tals zoomt leicht und verliert Schärfe und Sättigung (500 ms), während darunter die **echte
   3D-Karte** des gewählten Orts aufblendet, Kamera fliegt aus Schräglage (pitch 60°) heran (`flyTo`, 2,5 s).
3. Ankunft unter `#/check` mit gesetztem Ort, Panel bei Stufe 2.
Bedeutung, die die Jury verstehen soll: aus der Illustration wird echte Messung. Bei reduzierter Bewegung direkt
schneiden. Ohne WebGL: Weiterleitung auf `#/check` mit 2D-Ansicht.

### 3.7 Karte

- MapLibre (vorhanden, `maplibre-gl` 6.14). Gelände über `raster-dem` mit Terrarium-Kacheln
  (`https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`, Mapzen/AWS Open Data), Hangschummerung
  in Papiertönen, `terrain` Überhöhung 1,4, `sky` passend zum Thema.
- Basiskarte basemap.at (`bmapgrau` hell, Orthofoto als Umschalter), CC BY 4.0, Quellenangabe „basemap.at“.
  **Beide Kachelquellen vor dem Einbau tatsächlich abrufen und prüfen** und in `DATA_SOURCES.md` eintragen (Anbieter,
  URL, Lizenz, Abrufdatum). Fallback ohne Netz: die vom Backend gelieferten Rasterbilder (Relief/Prüfstufen) und
  ein Hinweis.
- Prüfstufe 1 `--stufe1`, Stufe 2 `--stufe2` als halbtransparente Flächen mit 1 px dunklerem Rand; Prüfpunkte als
  nummerierte Marker; Umkreis als gestrichelter Kreis.

## 4. Gestaltung: „Nach dem Regen“

Die Bildsprache der vier erzeugten Fotos bestimmt die Identität: nasses Grün, Nebel, Schieferblau, warmes Licht in
Fenstern, Signal-Orange der Warnkleidung. Hell und ruhig für das Werkzeug (man soll es bei Tageslicht und unter
Stress lesen können), dunkle Bildflächen für Gefühl und Ernst.

### 4.1 Farb-Tokens (`frontend/src/theme.css`, als Erstes geladen; Kontrast prüfen)

| Token | Hex | Rolle |
|---|---|---|
| `--paper` | `#F5F3EE` | Seitenhintergrund (Nebelweiß, nie reines Weiß) |
| `--paper-2` | `#EAE7DF` | Flächen, Panels auf Papier |
| `--card` | `#FFFFFF` | Karten mit Schatten |
| `--ink` | `#13202B` | Text, Logo |
| `--ink-2` | `#45535F` | Fließtext sekundär |
| `--ink-3` | `#76838F` | Beschriftung, Achsen (nur ≥ 14 px) |
| `--line` | `rgb(19 32 43 / .12)` | Linien |
| `--slate-900` | `#0E1822` | dunkle Abschnitte, Hero-Overlay |
| `--slate-700` | `#22313F` | dunkle Panels |
| `--moss` | `#3D5C38` | Marke, Gelände, Fokusring auf Papier |
| `--glacier` | `#8DB6C7` | Regen, Wasser, Fokus auf Dunkel |
| `--stufe1` | `#D4432A` | Prüfstufe 1, Hauptaktion |
| `--stufe2` | `#E9973A` | Prüfstufe 2 |
| `--infra` | `#2B59C3` | Straßen/Gebäude im Szenario |

Regeln: Orange-Rot ist **reserviert** für Prüfstufe 1 und die eine Hauptaktion; nirgends als Dekoration. Blau
(`--glacier`) nur für Wasser/Regen. Text mindestens 4,5 : 1, große Zahlen mindestens 3 : 1. Dunkelmodus über
`prefers-color-scheme` mit eigenen Token-Werten ist ein Zusatz nach Meilenstein 5, kein Muss.

### 4.2 Schrift (lokal über Fontsource, kein Google-CDN)

- **Display**: `@fontsource-variable/archivo` mit Breitenachse, `font-stretch` 112–125 %, Gewicht 600–700,
  Laufweite −0,02 em. Erinnert an gesperrte Ortsnamen auf Wanderkarten. Nur Überschriften und große Zahlen.
- **Text**: `@fontsource-variable/ibm-plex-sans`, 17–18 px, Zeilenhöhe 1,6, Gewicht 400/500.
- **Daten**: `@fontsource/ibm-plex-mono` für Intervalle, Koordinaten, Datumsangaben, Chips;
  `tabular-nums`.
- Skala: H1 `clamp(2.6rem, 6.5vw, 6rem)`, H2 `clamp(2rem, 4vw, 3.4rem)`, H3 1,4 rem, große Kennzahl
  `clamp(3.2rem, 7vw, 6rem)`, Eyebrow 12 px Mono, Großbuchstaben, Laufweite 0,14 em.
- Verfügbarkeit der Pakete und der Breitenachse vor dem Einbau prüfen. Ersatz nur, wenn ein Paket fehlt, dann mit
  Begründung im Commit.

### 4.3 Navigation

- Schwebende Leiste, 64 px, oben 16 px Abstand, Radius 16 px, maximal 1200 px breit, zentriert. Auf dem Hero
  transparent mit heller Schrift, nach 40 px Scroll Papier mit `backdrop-filter: blur(14px)` und feinem Schatten
  (Übergang 200 ms).
- Links das Signet (drei Höhenlinien, die einen Hang bilden, als SVG, dazu der Schriftzug „Talwacht“), Mitte die
  vier Menüpunkte mit gleitender Aktiv-Markierung, rechts der Knopf **„Hang prüfen“** (`--stufe1`) und ein kleines
  Suchsymbol, das die Ortssuche als Befehlspalette öffnet (`/` oder `Strg+K`).
- Handy: Signet + „Hang prüfen“ + Menü-Knopf; Menü als Vollbild-Sheet mit großen Einträgen. Auf `#/check` wird die
  Leiste kompakt (nur Signet, Zurück, Teilen).
- Aktiver Zustand, Fokus, Tastatur, `aria-current` sauber.

### 4.4 Layout, Tiefe, Bewegung

- Inhaltsbreite 1200 px, Rand 24 px (Handy 16 px), großzügiger Abstand zwischen Abschnitten (128–160 px Desktop,
  80 px Handy). Raster mit 12 Spalten; asymmetrische Bild-Text-Kompositionen statt gleich breiter Spalten.
- Karten: `--card`, Radius 20 px, Schatten zweilagig (eng + weich), beim Hover 2 px Anheben.
- Bewegung: ein System, nicht verstreute Effekte. Einblenden beim Scrollen (y 16 px → 0, Opacity, 500 ms,
  `cubic-bezier(.22,1,.36,1)`, gestaffelt 60 ms), Zahlen zählen hoch (1,2 s, einmal), Sticky-Grafiken in „So
  funktioniert's“, Seitenwechsel per View Transitions API (Fallback: Überblendung). `gsap` mit `ScrollTrigger` ist
  erlaubt, wenn CSS und `IntersectionObserver` nicht reichen. Kein Scroll-Kapern, keine Cursor-Effekte, keine
  Partikel außer dem Regen im Hero. `prefers-reduced-motion` zeigt Endzustände.
- Bilder: `<picture>` mit Breitenvarianten, `loading="lazy"` außer Hero, feste Seitenverhältnisse (kein
  Layoutsprung), dezenter Verlauf für Lesbarkeit von Text auf Bild.

### 4.5 Sprache

Deutsch, Du-Form auf Nutzerseiten, kurze Sätze, aktive Verben, Fachwörter beim ersten Auftreten erklärt (Tooltip-
System `InfoTip.vue` weiterverwenden). Textvorschläge:
- Hero H1: „Wo zuerst hinschauen, wenn der Starkregen kommt.“
- Hero Unterzeile: „Talwacht zeigt für deinen Ort die Hänge, die man bei Starkregen zuerst ansehen sollte, gelernt
  aus {N} dokumentierten Rutschungen in Österreich.“ ({N} aus der API.)
- Hang-Check Ergebnis: „Hier zuerst hinschauen“ · „Nicht markiert heißt nicht sicher.“
- „Wie belastbar“ Einstieg: „Wir zeigen dir nicht nur, was funktioniert, sondern auch, was nicht.“
- Abschluss Startseite: „Weniger Rätselraten nach dem Unwetter.“

## 5. Unverhandelbare Regeln

- **Wortlaut**: Der Test in `frontend/tests/wording.test.mjs` (`wahrscheinlich|risik|vorhersag|prognos|gefährdet`)
  gilt für **alle** neuen Nutzerseiten und Komponenten. Die Liste `juryFiles` auf die neuen Dateien umstellen; der
  Test muss mit einem eingefügten „Risiko“ scheitern.
- **Zahlen nur aus API-Bündeln**, nie als Literal (bestehender Literal-Test erweitern), immer mit Intervall,
  Einheitenzahl und Status. Feldnamen für V0.4 wie in `MEISTERPROMPT_JURY_WEBSITE.md` Abschnitt 5 und in
  `frontend/src/resultIntervals.js`.
- **Studien nicht vermischen**: explorativ bleibt explorativ, versiegelter Test bleibt der einzige Test; V0.5-
  Spannen sind keine Konfidenzintervalle.
- **KI-Bilder**: sichtbar gekennzeichnet („KI-generierte Illustration“, Mono 11 px, auf dem Bild), Abschnitt „Medien
  und KI“ unter `#/ueber` mit dem Inhalt aus `frontend/public/media/README.md`. Generierte Bilder nie als Beleg,
  nie neben Daten, als wären sie echt.
- **Eingefrorene Artefakte** (AGENTS.md §45), Pipeline-Code und Berichte werden nicht verändert. Backend-Änderungen
  nur: `/api/studien`, Registry, statische Auslieferung. Keine neue Auswertung, kein Training.
- **Datenschutz**: Ortssuche offline (Gemeindeliste des Hang-Checks), Standort nur clientseitig, kein Tracking,
  keine externen Fonts/Analytics.
- Neue Abhängigkeiten nur: die drei Fontsource-Pakete, optional `gsap`, optional `marked` (Markdown im Drawer;
  sonst ein kleiner eigener Renderer). Jede im Commit begründen, `package-lock.json` mitcommitten.

## 6. Medien

Bereits erzeugt und im Repository (`frontend/public/media/`, Herkunft in `README.md`): `tal` (Hero, 21:9),
`hang` (4:5), `morgen` (16:9), `luft` (16:9, ruhige Fläche, z. B. Hintergrund des Studienatlas-Kopfs mit starkem
Papier-Overlay). Zuerst diese verwenden.

Optional, nur nach Meilenstein 4 und wenn Zeit bleibt: **ein** Hero-Clip als Bild-zu-Video aus `tal`
(Higgsfield-Job `d3e15296-40b6-43c2-962a-d242e2b4a961` als Startbild). Restguthaben am 18.10.2026: 17,42 Credits;
höchstens 10 Credits ausgeben. Vorher Modell, Rollen und Kosten mit `models_explore` und `get_cost: true` prüfen,
bei Zeitüberschreitung nicht neu absenden. Prompt: „very slow subtle push-in, rain curtains drift gently, low clouds
move slightly, a few window lights flicker softly, no camera shake, no cuts“. Mit ffmpeg zu MP4 (H.264, `-an`,
`-crf 26`, `+faststart`) und WebM unter 4 MB, Standbild als Poster, kein Autoplay bei reduzierter Bewegung oder
`saveData`. In `README.md` protokollieren. Die Seite muss ohne Clip genauso gut sein.

## 7. Technik

- Vue 3 + Vite bleiben. Neue Struktur: `frontend/src/pages/` (StartPage, CheckPage, HowPage, EvidencePage,
  AtlasPage, AboutPage), `frontend/src/ui/` (NavBar, SearchPalette, BottomSheet, Reveal, CountUp, StatusChip,
  IntervalPlot neu, MediaCredit, Drawer), `frontend/src/map/` (TerrainMap, layers). Alte Seiten-Komponenten nach dem
  Umzug ihrer Inhalte löschen, nicht als toten Code liegen lassen. Die alten CSS-Dateien (`style.css`,
  `presentation.css`, `overview.css`, `jury.css`) durch `theme.css` + komponentennahe Styles ersetzen.
- **Auslieferung der Medien**: Vite kopiert `frontend/public/` nach `frontend/dist/`, aber `preslide/api.py`
  hängt heute nur `/assets` ein. `/media` (und ggf. `/fonts`, Favicon) als weiteres `StaticFiles`-Mount aus
  `dist/media` ergänzen, sonst liefern die Bilder 404. Im Browser prüfen.
- Leistung: Startseite ohne Karte unter 250 kB JS (gzip), Karte und Seiten per `defineAsyncComponent`, Hero-Bild
  mit `fetchpriority="high"`. Keine Layoutsprünge.
- Barrierefreiheit: Tastatur für alles inklusive Bottom Sheet und Karte, sichtbarer Fokus, Karte mit
  Textalternative (Ergebnisliste ist die Textalternative), `lang="de"`, Überschriftenhierarchie ohne Sprünge.
- Zustände: jede Datenquelle mit Laden, Fehler („Erneut laden“), Leer und „noch nicht verfügbar“ (503/404) im
  neuen Stil.

## 8. Meilensteine (jeweils: Build, Tests, Browserprüfung, Commit, Push von `claude/website-redesign`)

Heute ist Wettbewerbsschluss (18.10.2026). Arbeite so, dass nach **jedem** Meilenstein eine vollständige,
zusammenhängende Seite steht; bis zur Umstellung bleiben alte Inhalte unter ihren Adressen erreichbar.

| # | Inhalt | Richtwert |
|---|---|---|
| 1 | `theme.css`, Schriften, NavBar, Footer, Routen und Umleitungen, Startseite komplett (Hero mit Suche, drei Schritte, Zahlen, Anwendungen, Grenzen) | 2,5 h |
| 2 | `#/check` im neuen Stil: Vollbild-Karte, Panel/Bottom Sheet, Ergebnis-Auftritt, URL-Zustand, Signatur-Übergang vom Hero | 2 h |
| 3 | `#/belastbar` und `#/so-funktionierts` (inkl. Wirkungskette) | 2 h |
| 4 | `#/studien` mit `/api/studien`, Registry, Drawern, alle alten Detailinhalte umgezogen, `#/ueber`; alte Seiten entfernt | 2 h |
| 5 | Feinschliff: Bewegung, Druckansicht der Prüfliste, Leerzustände, Handy-Details, optional Hero-Clip | 1,5 h |

Wenn die Zeit nicht reicht, gilt die Reihenfolge: 1 → 2 → 4 (Inhalte dürfen nicht verloren gehen) → 3 → 5.

## 9. Qualitätsschleife (nach jedem Meilenstein, nicht erst am Ende)

1. Screenshots mit dem eingebauten Browser bei 1440, 1024, 768 und 375 px Breite, jeweils oben und an zwei
   Scrollpositionen. Ansehen.
2. Selbstkritik gegen diese Liste, Mängel sofort beheben, dann erneut Screenshots:
   - Versteht man in fünf Sekunden, was man tun kann? Ist die Suche ohne Scrollen sichtbar?
   - Wirkt irgendetwas wie eine Vorlage (gleich große Kacheln in Reihe, generische Icons, Farbverlauf ohne Grund,
     zentrierter Text überall)? Dann umbauen.
   - Gibt es leere oder fast leere Abschnitte, doppelte Inhalte, verwaiste Links? Entfernen oder füllen.
   - Stimmen Abstände im Raster, Grundlinien, Ausrichtung von Zahlen? Ist jede Zahl mit Intervall und Status?
   - Handy: kein waagrechtes Scrollen, Bottom Sheet bedienbar, Knöpfe ≥ 44 px, Text ≥ 16 px.
   - Konsole und Netzwerk ohne Fehler (außer dokumentierten 503).
3. Erst dann committen.

## 10. Tests und Verifikation

- `cd frontend; npm test; npm run build` grün. Neue Tests: Navigation (vier Menüpunkte, keine Forschungs-Unterseiten,
  alle alten Adressen leiten um), Wortlaut für alle neuen Dateien, keine Kennzahl-Literale, Registry deckt alle
  `reports/*/summary.md` ab, Studien-API liefert bei fehlender Datei `verfuegbar: false` statt Ersatzwert,
  Hang-Check-Panel: Schalter aus → keine Anfrage. Jeder neue Schutztest muss einmal mit eingebautem Fehler scheitern.
- `.\.venv\Scripts\python -m pytest -q tests/test_studien.py` plus die Tests des Hang-Checks und der Hangkarte;
  Skip- und Fehlerzahlen ehrlich nennen. Die Verify-Skripte nicht im Worktree ausführen (sie überschreiben dort
  `reports/v04/verification.json`); stattdessen mit `git diff --stat origin/claude/integration-2026-10-18` zeigen,
  dass unter `reports/`, `archive/`, `config/v0*.json`, `preslide/v0*` nichts geändert wurde.
- CI-Hinweis: `ruff check` (Pyflakes) läuft in CI; neue Python-Module auf unbenutzte Importe prüfen.
- Abschluss-Nachweis: je ein Screenshot pro Seite bei 1440 und 375 px.

## 11. Abschluss und Doku

- `PROJECT_STATE.md` und `PROJEKTUEBERBLICK.md` (Abschnitt Webdemonstration) knapp aktualisieren: neue Struktur,
  Routen, Studienatlas-Registry, Medien.
- `DATA_SOURCES.md`: basemap.at, Terrarium-Kacheln, Fontsource-Schriften (Lizenz OFL), Higgsfield-Medien.
- Branch pushen; in `main` oder den Integrationsstand erst nach Rücksprache mit dem Nutzer.

## 12. Nicht tun

- Keinen Menüpunkt „Forschung“, keine Unterseiten-Leisten, keine Seite ohne echten Inhalt.
- Keine Inhalte, Studien, Abbildungen oder Grenzen weglassen, nur weil sie unbequem sind.
- Keine Wahrscheinlichkeiten, Ampel-Grün, Risiko-Begriffe, Warnungs-Sprache, erfundene Testimonials, Logos von
  Behörden oder Partnern, die nicht zugestimmt haben.
- Keine generierten Bilder von Karten, Diagrammen, Zahlen oder echten Orten.
- Keine Änderung an Pipeline, Modellen, Berichten oder eingefrorenen Artefakten.
- Nichts öffentlich bereitstellen.
