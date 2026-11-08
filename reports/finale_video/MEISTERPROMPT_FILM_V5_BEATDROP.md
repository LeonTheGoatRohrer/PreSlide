# Meisterprompt: Talwacht-Film V5 – neuer Schluss mit Beat Drop

Stand 08.11.2026. Ausführung: eine Claude-Code-Sitzung mit Higgsfield-MCP (Stimme, optional Bild/Video) und dem bestehenden ffmpeg-Schnittskript. Alle Messwerte unten wurden am 08.11.2026 an den echten Dateien ermittelt.

---

## Auftrag

Baue aus `Talwacht_Finale_v4.mp4` die Version **V5**. Ändere nur den Schluss:

1. **Musik ab dem Abspann-Aufbau:** Unter den letzten rund 52 Sekunden läuft der Song „Two Faced“ von purc statt `sfx/finale.mp3`.
2. **„Das. Ist. Talwacht.“** wird neu gesprochen, mit klar hörbarem **T** in „Talwacht“.
3. **Direkt nach „Talwacht“ kommt der Beat Drop.**
4. **Nach dem Drop folgt eine kurze Montage aus 6 Bildern** (Mure bricht los, Handy-App Gasteiner Tal, Rückblick auf das Projekt), dann ein langsamer Zoom-out und eine Überblendung in den bestehenden TALWACHT-Endframe.
5. **Alles andere bleibt Bild für Bild gleich**, auch Bild und Text im Aufbau vor „Das ist Talwacht“.

**Harte Grenze:** Gesamtlänge **höchstens 5:00,0** (`MAX_LAENGE_S = 300.0`; der Nutzer kann das ändern, siehe Abschnitt 4).

---

## 1. Dateien

| Was | Pfad |
|---|---|
| Arbeitsordner (Branch `claude/video-professionalisieren-804986`) | `C:\Users\mario\Documents\HomeProjects\PreSlide\.claude\worktrees\video-professionalisieren-804986` |
| Schnittskript V4 | `scripts/finale_video/build_film.py` (Liste `SEGMENTS`, Audio-Mix ab ca. Zeile 215) |
| Letzte Zeile (Wortschnitt, Pitch, Hall) | `scripts/finale_video/final_line.py` |
| Motion-Graphics-Szenen | `scripts/finale_video/mg/scenes.js` |
| Fertiges V4 (1920×1080, 25 fps, 298,68 s) | `deliverables/finale_video/Talwacht_Finale_v4.mp4` |
| Schnittzeiten V4 | `deliverables/finale_video/build/timeline.json` |
| Endframe-Clip (TALWACHT + Unterzeile) | `deliverables/finale_video/build/end.mp4` (7,7 s) |
| Echte Murenclips + Lizenzliste | `deliverables/finale_video/echte_muren/` und `LISTE.md` |
| App-Aufnahmen 1920×1080 | `C:\Users\mario\Documents\HomeProjects\PreSlide\.claude\worktrees\video-pitch-script-497edf\deliverables\pitch\app3\` |
| App-Aufnahmeskript (Playwright) | `…\video-pitch-script-497edf\scripts\pitch\record_app.mjs` |
| Song | `C:\Users\mario\Downloads\two faced.mp3` (356,9 s) |
| Stimme | Higgsfield `elevenlabs_v4`, Preset **Alistair**, `voice_id d9d5c263-f84e-4752-97b5-3750fcc6fd2f`, `voice_type preset` |

Python mit numpy liegt im Hauptcheckout unter `C:\Users\mario\Documents\HomeProjects\PreSlide\.venv\Scripts\python.exe`.

Die V4-Ausgabe nicht überschreiben. Schreibe nach `Talwacht_Finale_v5.mp4` (`--out`).

---

## 2. Messwerte (nicht neu raten, nur nachprüfen)

**Song „two faced.mp3“**
- **Drop exakt bei 52,00 s.** Der Pegel springt dort von −22 dB auf etwa 0 dB (10-ms-Auflösung, 808-Schlag).
- Davor liegt ein **flaches, leises Intro** (−22 bis −24 dB RMS über 52 s), ohne Riser und ohne Pause vor dem Drop.
- Tempo nach dem Drop: Schlag alle **0,406 s (ca. 148 BPM)**, Takt = **1,625 s**. Starke Einsätze bei 52,00 · 52,39 · 52,80 · 53,21 · 53,61 · 54,03 · … Taktanfänge also bei Songzeit 52,00 · 53,62 · 55,25 · 56,87 · 58,50 · 60,12.
- Laut bleibt es bis ca. 100 s, danach folgt wieder ein ruhiger Teil.

**V4-Schluss (Videozeit)**
| Segment | Start | Inhalt |
|---|---|---|
| `last` | 265,64 | „Denn der nächste Starkregen kommt …“ |
| `q1` | 271,16 | „Der Berg warnt nicht. Der Berg erklärt nichts.“ |
| `q3` | 279,16 | „Aber er hat Spuren hinterlassen,“ |
| `spuren` | 281,96 | Österreich-Karte zählt bis 423 · „vierhundertdreiundzwanzig Mal.“ · „Ich habe angefangen zuzuhören.“ · ab 288,11 „Das. Ist. Talwacht.“ |
| `end` | 290,96 | Schnitt auf den TALWACHT-Titel genau auf das Wort „Talwacht“, Halt bis 298,68 |

- In `q5.mp3` sind die Wörter einzeln geschnitten: Das 0,00 s, Ist ca. 1,4 s, Talwacht ca. 2,85 s (also ca. 290,96 im Film). Das Wort endet nach ca. 0,85 s, also bei **ca. 291,8**.
- **Vermutliche Ursache für das schwache T:** `final_line.py` schneidet „Talwacht“ ab `WORDS_S[2][0] = 1.76` s in `q5s.mp3` und blendet die ersten **12 ms** ein. Der T-Plosiv dauert nur wenige Millisekunden und liegt genau auf diesem Schnitt bzw. in dieser Einblendung. Dazu kommen Pitch −2 Halbtöne und 12 % Verlangsamung, die den Anschlag zusätzlich weicher machen.

**Higgsfield:** 450 Credits (Plan ultra). Frühere Takes „Das ist … Talwacht.“ existieren (`2967c7bc`, `6fc02f0b`, `c6524584`, `baf008ab`).

---

## 3. Arbeitsschritte

Vor jedem Schritt erst klein testen, dann den ganzen Film rendern (Prinzip aus AGENTS.md §4).

### Schritt A – „Das. Ist. Talwacht.“ neu, mit hörbarem T (Credits: ≤ 15)
1. Mit `elevenlabs_v4`, Alistair, **4 Takes** erzeugen, Rhythmus wie bisher (drei einzelne Wörter, ruhig, tief). Textvarianten, damit das T trägt:
   - `Das. ... Ist. ... Talwacht.`
   - `Das. ... Ist. ... TALwacht.`
   - `Das. ... Ist. ... T-alwacht.` (nur wenn die anderen das T verschlucken)
   - `Das ist. ... Talwacht.`
   Vorher den Preis prüfen. Wenn ein Take mehr als 5 Credits kostet, nur 2 Takes erzeugen.
2. `final_line.py` für V5 anpassen (Parameter, keine neue Logik):
   - Den Wortanfang von „Talwacht“ **im Wellenbild messen**, nicht schätzen. Den Schnitt **30–40 ms vor** den Plosiv setzen.
   - Einblendung am Wortanfang **3 ms** statt 12 ms (die 12 ms am Wortende bleiben).
   - Nur für „Talwacht“ eine Präsenzanhebung (z. B. `equalizer=f=4000:t=q:w=1:g=4`), damit das T durch den Song kommt.
   - Pitch und Tempo wie bisher (`PITCH = 0.891`), damit die Stimme zum restlichen Film passt.
3. **Prüfen:** Den Anfang von „Talwacht“ als Spektrogramm-PNG rendern (`ffmpeg … showspectrumpic`). Zwischen 3 und 8 kHz muss vor dem „a“ ein kurzer, breitbandiger Anschlag zu sehen sein. Zusätzlich 4 s Audio um das Wort herum als MP3 in den Scratchpad legen und dem Nutzer zum Anhören geben, **bevor** der ganze Film gerendert wird.
4. Den gewählten Take nach `voice_v5/q5.mp3` schreiben. `voice_v4_fast/q5.mp3` nicht überschreiben.

### Schritt B – Zeitachse für den Drop festlegen
1. `D` = Videozeitpunkt, an dem der Ausklang von „Talwacht“ hörbar zu Ende ist. Messen, auf ganze Frames runden (25 fps → Vielfache von 0,04 s). Ziel: ca. **0,05–0,10 s nach dem letzten Laut**, kein Loch.
2. **Pausen straffen, damit nach dem Drop mehr Zeit bleibt:** Die Pausen zwischen den Wörtern von 0,75/0,85 s auf ca. **0,50/0,55 s** kürzen. „Talwacht“ beginnt dadurch ca. 0,55 s früher. Den Schnitt `spuren → end` (TALWACHT-Titel) **genau mit dem neuen Wortbeginn mitziehen**: `spuren` wird um dieselbe Zeit kürzer. Am Ende von `spuren` steht nur die fertige 423-Karte still, es fehlt also kein Inhalt. Alles davor bleibt unverändert.
3. Ergebnis aufschreiben: neues `D` (erwartet ca. **291,2 s**), `Montage = MAX_LAENGE_S − D` (erwartet ca. **8,8 s** bei 5:00).
4. **Song-Offset:** `song_start = D − 52,00` (erwartet ca. 239,2 s, also kurz nach dem App-Kapitel bei `use1`). So trifft Songsekunde 52,00 exakt `D`. Die Rechnung im Skript als Kommentar mit beiden Zahlen festhalten.

### Schritt C – Musik-Mix
1. Ab `song_start` läuft der Song von Songsekunde 0. `finale.mp3` wird ersetzt: Es läuft wie in V4 bis `song_start`, dann eine **4-s-Überblendung** in den Song, danach ist `finale.mp3` stumm. `music.mp3` (Cue 1) bleibt unverändert.
2. **Ducking unter der Stimme** wie in V4 beibehalten (Hüllkurve, `depth`). Das Song-Intro ist leise, deshalb das Intro-Gain so wählen, dass die Erzählung in `fazit`, `next`, `last`, `q1` und `spuren` klar vorne bleibt. Messen: Stimme mindestens 8 dB über der Musik (RMS über die Sprechpassagen).
3. **Atempause vor dem Drop:** Weil der Song keinen eigenen Riser oder Break hat, die Musik **von Beginn von „Das“ bis `D`** um ca. 10–12 dB absenken (nicht auf null). Die drei Wörter stehen dann fast allein, und der Drop wirkt dadurch härter. Bei `D` ohne Rampe zurück auf volle Lautstärke. Optional `sfx/boom.mp3` leise (Gain ≤ 0,5) exakt auf `D` legen, aber nur, wenn es den 808 nicht verschmiert.
4. Das `boom` aus V4 auf dem Titel-Schnitt (`hit`) entfernen. Es lag auf dem alten Titel und würde jetzt vor dem Drop stören.
5. Ende: Song in den letzten **1,5 s** ausblenden, das Bild blendet gleichzeitig auf Schwarz.
6. Mastering wie in V4 (lineare Verstärkung auf −14 LUFS, Limiter). Kein dynamisches loudnorm, sonst wird der Drop platt.

### Schritt D – Die Montage nach dem Drop (6 Bilder)
Schnitte liegen **auf den Schlägen** des Songs (`D + n × 0,406 s`). Takt = 1,625 s. Zeiten relativ zu `D`, ausgelegt für ca. **8,8 s**:

| # | Zeit ab D | Bild | Text im Bild (Stil der V4-Captions, klein, orange Kapitälchen + graue Unterzeile) |
|---|---|---|---|
| 1 | 0,00 – 1,62 (1 Takt) | **Die Mure bricht los.** Das echte Video, in dem die Mure plötzlich voll losgeht. Kandidaten: `02_usgs_elk_fire.mp4` (ca. 80–125 s) oder `05_usgs_hermits_peak.mp4` (ca. 80–155 s). Den Clip so legen, dass **der Moment des Losbrechens genau auf `D` fällt**. Im Kontaktbogen und dann frameweise suchen. Nicht dieselbe Stelle wie im Kaltstart (Elk Fire ab 69,5 s, Las Lomas ab 4,5 s). | Einblendung wie V4: „Echte Aufnahme · Murgang, … · USGS, gemeinfrei“ |
| 2 | 1,62 – 3,25 (1 Takt) | **Handy-App, Gasteiner Tal.** Neue Aufnahme der Web-App im Handy-Format (siehe unten), in einem schlichten, dunklen Handy-Rahmen mittig auf dunklem Hintergrund, leichter Push-in. | „HANG-CHECK · GASTEINER TAL“ |
| 3 | 3,25 – 4,06 (2 Schläge) | Zweiter echter Murgang, andere Einstellung: `01_usgs_las_lomas.mp4` (Murenfront, ca. 10–50 s, andere Stelle als im Kaltstart). | „423 DOKUMENTIERTE RUTSCHUNGEN“ |
| 4 | 4,06 – 4,87 (2 Schläge) | Projektbild „Nachbarhang als Vergleich“: Frame aus der MG-Szene `twin` (Kapitel p2b). | „NACHBARHÄNGE ALS VERGLEICH“ |
| 5 | 4,87 – 5,69 (2 Schläge) | App „Möglicher Weg hangabwärts“: Ausschnitt aus `app_04_starkregen.webm` mit Fließwegen und Prüfpunkten 1–4. | „WO ZUERST HINSCHAUEN“ |
| 6 | 5,69 – Ende | **Langsamer Zoom-out** über die Österreich-Karte mit den 423 Punkten (Schlussbild der Szene `spuren`), z. B. Skalierung 1,25 → 1,0 über ca. 2,4 s mit sanftem Ein- und Ausklingen. Ab ca. 6,9 s **1,2 s Überblendung in den Endframe** aus `end.mp4`, und zwar ab dem Zeitpunkt in `end.mp4`, an dem Unterzeile und Quellenzeile vollständig stehen (ca. 1,5–2 s). Halten. Letzte 1,0 s Abblende auf Schwarz. | keiner, nur der Endframe |

Regeln für die Montage:
- **Keine neuen Zahlen.** Text nur aus dem, was V4 schon zeigt (423, Nachbarhang, Prüfpunkte, „Wo zuerst hinschauen“). Nichts erfinden.
- Echte Clips **immer** mit Quellen-Einblendung. KI-Bilder (falls in Schritt E verwendet) **immer** mit „KI-generierte Illustration“. Keinen ausländischen Clip als österreichisches Ereignis zeigen. Gyirong (Lizenz unsicher), Saint-Julien (CC BY-SA) und Fremdmaterial aus `14_…` nicht verwenden.
- Harte Schnitte auf dem Schlag, keine Wischblenden. Höchstens ein kurzer Weiß- oder Helligkeitsblitz von 2 Frames genau auf `D`.
- Die Endframe-Optik ist fix: Es ist exakt der V4-Endframe (TALWACHT, Unterzeile „Wo zuerst hinschauen, wenn der Starkregen kommt“, Höhenlinien-Hintergrund, Quellenzeile). Nicht neu gestalten.

**Handy-Aufnahme Gasteiner Tal (0 Credits):**
- `record_app.mjs` kopieren nach `scripts/finale_video/record_app_mobile.mjs` und nur die Szene `app_02_hangcheck_gastein` übernehmen. Viewport **390×844**, `deviceScaleFactor: 3`, `isMobile: true`, `hasTouch: true`. URL `/#/check?lon=13.11000&lat=47.11000&ort=Gasteiner+Tal+%28Salzburg%29&r=2000`, dann auf die Prüfpunkte zoomen, ca. 4 s Material.
- Zuerst prüfen, ob die App im Handy-Format sauber aussieht (Panel nicht über der Karte, keine abgeschnittenen Texte). Wenn nicht: als Fallback den passenden Ausschnitt aus `app_04_starkregen.webm` hochkant in den Handy-Rahmen setzen und das im Bericht so nennen.
- Die App vorher wie beim Pitch lokal starten (Port 8012) und den Server danach wieder beenden.

### Schritt E – Optionale Higgsfield-Bilder (Budget gesamt ≤ 150 Credits, Reserve ≥ 250)
Nur wenn die Montage mit echtem Material sichtbar schwächer ist:
- Ein KI-Handfoto „Hand hält Smartphone vor verregnetem Alpental“ mit leerem, dunklem Bildschirm, in den die Aufnahme montiert wird (1 Bild, `gpt_image_2_6` oder vergleichbar). Mit Kennzeichnung.
- **Kein** KI-Murgang, solange echte Clips reichen.
- Vor jeder Generierung den Preis mit `models_explore get` prüfen. Verbrauch und Restguthaben im Bericht nennen.

### Schritt F – Schnittskript
- `build_film.py` um einen V5-Schalter ergänzen (z. B. `--v5`). Ändern dürfen sich nur: die `q5`-Quelle, die Pausen, die Länge von `spuren`, das Segment `end` (wird zu Montage + Endframe) und der Musik-Mix. V4 muss mit dem alten Aufruf **bitgleich** reproduzierbar bleiben.
- Montage-Segmente als eigene IDs in `timeline.json` (`drop1_mure`, `drop2_handy`, `drop3_mure2`, `drop4_twin`, `drop5_weg`, `drop6_zoom_end`).
- Zuerst nur die letzten 70 s rendern (`--width 960`, Ausschnitt ab 235 s) und prüfen, erst dann den ganzen Film in 1920.

---

## 4. Länge: Entscheidung des Nutzers

- **Standard (5:00 hart):** Montage ca. 8,8 s, wie in der Tabelle oben.
- **Falls der Nutzer bis 5:05 erlaubt (`MAX_LAENGE_S = 305`):** Bild 1 auf **2 Takte** (3,25 s) verlängern, mit einem Schnitt innerhalb des Clips auf dem Taktanfang. Endframe-Halt +1,5 s. Montage dann ca. 12 s. Sonst bleibt alles gleich.
- Nie Inhalt vor `song_start` kürzen, um Zeit zu gewinnen.

---

## 5. Abnahme (alles messen, nichts aus dem Gedächtnis)

1. `ffprobe`: Dauer ≤ `MAX_LAENGE_S`, 1920×1080, 25 fps, AAC.
2. **Bildgleichheit:** Bis `song_start` müssen V4 und V5 Frame für Frame gleich sein (`ffmpeg … -lavfi "[0][1]psnr"` über 0 bis `song_start`; bei identischer Kodierung PSNR = inf oder ≥ 50 dB). Von `song_start` bis zum neuen Wortbeginn ebenso, mit Ausnahme der gekürzten Standzeit am Ende von `spuren`.
3. **Drop-Sync:** Im fertigen Mix den Pegelsprung suchen. Er muss bei `D` ± 1 Frame liegen. Die Schnitte 2–6 dürfen höchstens ±1 Frame vom Schlagraster abweichen. Tabelle mit Soll- und Ist-Zeiten in den Bericht.
4. **T-Test:** Spektrogramm-PNG des Wortanfangs „Talwacht“ im fertigen Mix (nicht nur im Voice-Take).
5. Lautheit: −14 LUFS ±0,5, True Peak ≤ −1 dBTP. Stimme in den Erzählpassagen ≥ 8 dB über der Musik.
6. Kontaktbogen der letzten 15 s (alle 0,4 s ein Bild) als PNG und **10 s Vorschau-MP4 um den Drop** in den Scratchpad legen und dem Nutzer zeigen.
7. Lizenz-Einblendung bei jedem echten Clip sichtbar (im Kontaktbogen prüfen).

---

## 6. Abschluss

- Kurzer Bericht: was geändert wurde, gemessenes `D`, `song_start`, Gesamtlänge, gewählter Take, Credits verbraucht und übrig, Abweichungen vom Plan.
- Hinweis an den Nutzer: „Two Faced“ von purc ist ein kommerzieller Song. Bei der Jury-Vorführung ist das meist unproblematisch. Auf YouTube, Instagram oder TikTok kann ein Copyright-Claim oder eine Stummschaltung kommen.
- Skriptänderungen committen und pushen. Keine Videos, Audios oder Build-Dateien committen (gitignored).
