# Meisterprompt: Talwacht-Film V6 – fünf alternative Enden

Stand 10.11.2026. Für **eine** Claude-Code-Sitzung, die alles von Anfang bis Ende erledigt: planen, Material erzeugen, schneiden, prüfen, abgeben. Die Messwerte unten wurden an den echten Dateien ermittelt (V5 am 08.11., Song-Phrasen am 10.11.2026).

---

## 0. Das Problem in einem Satz

Der Film „Talwacht“ (V5, 5:04,6) ist bis zum Beat Drop nach „Das. Ist. Talwacht.“ fertig. Das **Outro danach gefällt dem Nutzer nicht**: Es hat **kein Kino-Gefühl** (wirkt wie eine Diashow aus 6 kurzen Schnitten in 12,8 s), und **man sieht nicht, wie man Talwacht benutzt**.

## 1. Auftrag

Baue **5 komplett verschiedene Enden**. Alle fünf:

- beginnen **exakt am Drop** (`D = 291,80 s` Filmzeit). Alles davor bleibt Bild für Bild und Ton für Ton wie in V5.
- laufen auf **demselben Soundtrack wie V5**, also „Two Faced“ von purc mit Drop bei Songsekunde 52,00 auf `D`. Kein anderer Song, keine zusätzliche Musik.
- sind **im Schnitt mit der Musik synchron**: harte Schnitte auf Schlägen, große Bildwechsel auf Taktanfängen, Höhepunkte auf Phrasenanfängen, Bass-Schläge mit Bildimpuls (Kamera-Shake, Blitz, Licht).
- dauern nach dem Drop **höchstens ca. 20 s** (vom Nutzer freigegeben). Empfohlen sind **19,50 s = 3 Phrasen**, Film endet dann bei ca. **311,3 s (5:11,3)**.

Die fünf Richtungen:

| # | Pflicht | Idee (Vorschlag, frei veränderbar) |
|---|---|---|
| 1 | **Episch** | Größe und Wucht. Ein Alpental im Gewitter, die Kamera steigt über einen Grat, unter ihr das ganze Tal. Auf dem Drop bricht der Himmel auf (Blitz auf Bass). TALWACHT erscheint riesig über dem Tal. Musik und Bild steigern sich bis zum letzten Takt. |
| 2 | **Cinematisch** | Kino-Look: 2,39:1-Balken, langsame Kamera, Tiefenschärfe, Farbe im Grading, wenige lange Einstellungen gegen den schnellen Beat (Kontrast). Nacht, Regen auf Asphalt, ein Ort unter dem Hang, ein Licht geht an. Ruhe gegen den Bass. |
| 3 | frei, **Pflicht: Anwendung zeigen** | Wer benutzt die App wann? Vorschlag: Bei einer Unwetterwarnung prüft jemand aus der Gemeinde oder vom Bauhof am Handy den Hang über dem Ort. Er sieht die Prüfpunkte, „Wo zuerst hinschauen“, und geht mit Stirnlampe hinaus. Die echte App-Aufnahme ist im Handy zu sehen. |
| 4 | frei | z. B. „Daten-Puls“: Die 423 Punkte über Österreich leuchten im Takt auf, dann ein Flug auf echtes Gelände (DEM, Blender), auf dem die Prüfpunkte erscheinen. |
| 5 | frei | z. B. Vorher/Nachher im Split-Screen oder ein radikal minimales Ende (Schwarz, ein Schlag, Titel). Entscheide selbst, was den Unterschied zu 1–4 am größten macht. |

Der Nutzer will etwas, das „alle umhaut“. Qualität vor Menge: Lieber 5 starke Enden als 5 mittelmäßige mit vielen Effekten.

## 2. Wo alles liegt

Projekt (Git-Repo): `C:\Users\mario\Documents\HomeProjects\PreSlide`
**Arbeitsordner für den Film** (Worktree, Branch `claude/video-professionalisieren-804986`):
`C:\Users\mario\Documents\HomeProjects\PreSlide\.claude\worktrees\video-professionalisieren-804986`
Alle Pfade unten sind relativ zu diesem Ordner. `deliverables/` ist gitignored und liegt nur hier.

| Was | Pfad |
|---|---|
| Fertiger Film V5 (1920×1080, 25 fps, 304,60 s) | `deliverables/finale_video/Talwacht_Finale_v5.mp4` |
| Schnittskript (V4 und `--v5`) | `scripts/finale_video/build_film.py` (V5-Zeiten ab Zeile 38, Audio-Mix ab ca. 320, `picture_v5()` ab ca. 421) |
| V5-Schnittzeiten | `deliverables/finale_video/build_v5/timeline.json` |
| V5-Montage-Clips (das alte Outro) | `deliverables/finale_video/build_v5/drop1_mure.mp4` … `drop6_zoom_end.mp4` |
| V5-Mix (float32, Stereo) | `deliverables/finale_video/build_v5/mix.f32`, fertiger Ton `audio.m4a` |
| TALWACHT-Endframe-Clip | `deliverables/finale_video/build/end.mp4` (7,7 s) |
| Song | `deliverables/finale_video/song/two_faced.mp3` (Original: `C:\Users\mario\Downloads\two faced.mp3`, 356,9 s) |
| Soundeffekte | `deliverables/finale_video/sfx/` (`boom`, `thunder`, `riser`, `rain`, `debris`, `tear`, `slide`, `scan` …) |
| Stimme letzte Zeile | `deliverables/finale_video/voice_v5/q5.mp3`, Werkzeug `scripts/finale_video/final_line.py` |
| Motion-Graphics-Szenen (Quelle) | `scripts/finale_video/mg/scenes.js`, Renderer `scripts/finale_video/render_mg.mjs` |
| Gerenderte MG-Clips | `deliverables/finale_video/mgclips/` (`spuren.mp4` = Österreich-Karte mit 423 Punkten, `twin.mp4`, `end.mp4`, …) |
| Frühere KI-Clips (Kling/GPT Image, gekennzeichnet) | `deliverables/finale_video/ai/` |
| Echte Murenclips + Lizenzliste | `deliverables/finale_video/echte_muren/` und `LISTE.md` |
| Handy-Aufnahme App, Gasteiner Tal (390×844 @3x) | `deliverables/finale_video/app_mobile/app_02_hangcheck_gastein_mobile.webm`, Skript `scripts/finale_video/record_app_mobile.mjs` |
| App-Aufnahmen 1920×1080 | `…\.claude\worktrees\video-pitch-script-497edf\deliverables\pitch\app3\` (`app_02_hangcheck_gastein.webm`, `app_04_starkregen.webm`, `app_05_belastbar.webm` …) |
| Faktencheck des Films | `reports/finale_video/FAKTENCHECK.md` |
| Vorgänger-Prompt (V5) | `reports/finale_video/MEISTERPROMPT_FILM_V5_BEATDROP.md` |
| Python mit numpy | `C:\Users\mario\Documents\HomeProjects\PreSlide\.venv\Scripts\python.exe` |

Nicht anfassen: `Talwacht_Finale_v4.mp4`, `Talwacht_Finale_v5.mp4`, `build/`, `build_v5/`, `voice_v4_fast/`, `voice_v5/`, `voice_v6/` (gehört einer anderen Sitzung). Neue Dateien nur in `deliverables/finale_video/build_v6/` und im Ausgabeordner.

## 3. Musik: gemessene Werte (nachprüfen, nicht neu raten)

- **Drop bei Songsekunde 52,00.** Der Pegel springt von ca. −22 dB auf ca. −9 dB (RMS), der Bass (< 150 Hz) um ca. 24 dB.
- **Song-Offset:** Songsekunde 0 liegt bei Filmzeit `SONG_START = 239,80 s`. Umrechnung: Filmzeit = Songzeit + 239,80.
- **Raster nach dem Drop:** Schlag = **0,40625 s** (ca. 148 BPM), Takt = **1,625 s**, **Phrase = 4 Takte = 6,50 s**.
- **Phrasenanfänge** (Song → Film): 52,00 → 291,80 · 58,50 → 298,30 · 65,00 → 304,80 · **71,50 → 311,30**.
- Pro Phrase ist der **4. Takt etwas lauter** (Fill / Akzent): Song 56,9–58,5, 63,4–65,0, 69,9–71,5 (gemessen +1 bis +3 dB). Diese Takte sind gute Stellen für einen Aufbau direkt vor einem großen Schnitt.
- Der laute Teil geht bis ca. Songsekunde 100. Bei 20 s ist also kein natürliches Songende da. Das Ende muss gebaut werden. Empfehlung: harter Schluss genau auf dem Downbeat **311,30 s**, ein letzter `boom` mit Hall-Ausklang (ca. 1,5–2,5 s, darf über 311,3 hinaus), danach Stille und Schwarz. Alternativ den Song über 1,5 s ausblenden wie in V5. Pro Variante entscheiden, was besser zur Bildidee passt.
- Vor dem Bauen: die Schlagzeiten nach dem Drop im Song **frameweise nachmessen** (Onset-Erkennung im Bassband). Für jedes Ende eine Tabelle mit Soll- und Ist-Zeiten aller Schnitte führen. Schnitte höchstens ±1 Frame (0,04 s) neben dem Schlag.

## 4. Inhaltliche Regeln (aus dem Faktencheck, hart)

- **Keine neuen Zahlen oder Behauptungen.** Text im Bild nur aus dem, was der Film schon sagt (423 dokumentierte Rutschungen, Nachbarhänge als Vergleich, Prüfpunkte, „Wo zuerst hinschauen, wenn der Starkregen kommt“). Talwacht **sagt keine Muren vorher**. Die App zeigt, wo man zuerst hinschauen sollte. Keine Szene darf eine Vorhersage, einen Alarm „Mure in 10 Minuten“ oder eine Evakuierung durch die App zeigen.
- **KI-Material immer mit Einblendung „KI-generierte Illustration“.** Echte Clips immer mit Quelle („Echte Aufnahme · … · USGS, gemeinfrei“). Keinen ausländischen Clip als österreichisches Ereignis zeigen. Gyirong (Lizenz unsicher), Saint-Julien (CC BY-SA) und `14_…` nicht verwenden.
- Personen in KI-Szenen sind erfundene Figuren und keine echten Personen oder Behörden. Keine echten Logos (z. B. Feuerwehr-Wappen, Gemeindewappen).
- Im App-Bildschirm nur echte App-Aufnahmen, keine KI-erfundene Oberfläche.
- UI- und Bildtext auf Deutsch. Stil der bestehenden Captions: kleine orange Kapitälchen und eine graue Unterzeile.
- **Gesprochen wird nach dem Drop nichts Neues**, außer eine Variante gewinnt klar durch höchstens eine kurze Zeile in derselben Stimme (Alistair, `elevenlabs_v4`, Pitch wie `final_line.py`). Dann im Bericht begründen.
- Jedes Ende schließt mit dem Wort-/Bildzeichen TALWACHT. Das kann der V5-Endframe sein oder eine neue Inszenierung, z. B. Titel im Tal. Unterzeile und Quellenzeile müssen aber lesbar stehen.

## 5. Higgsfield: nur Unlimited, keine Credits

Der Nutzer hat ein **3-Tage-Unlimited-Trial** und will, dass **keine Credits verbraucht** werden.

1. Zuerst prüfen: `balance` und `models_explore` mit `action: list, unlim: true`. Nur wenn **`unlim.available: true`** ist, darf generiert werden, und nur mit Modellen mit `supports_unlim: true` in den Konfigurationen, die der Text „Unlim configs“ als abgedeckt nennt (Auflösung, Dauer, Modus).
2. Stand 10.11.2026 (alte Sitzung): `unlim.available: false`, Plan Ultra, 165,69 Credits, Trial nicht aktiv. **Wenn das weiterhin so ist: nicht generieren.** Dem Nutzer kurz sagen, dass das Trial im Connector nicht ankommt, und ihn bitten, den Higgsfield-Connector mit dem Trial-Konto neu anzumelden.
3. Vor **jeder** Generierung den Kontostand notieren und danach vergleichen. Sinkt er, sofort aufhören und dem Nutzer melden.
4. Kandidaten (laut Liste unlim-fähig): **Video** Seedance 2.5 (bis 1080p, 4–30 s, Start-/Endbild, Referenzen) und Seedance 2.0 (bis 4k im Modus `std`). **Bild** GPT Image 2.6 / 2.5, Nano Banana Pro (bis 4k), Seedream 5.5. Native Tonspur der Videos ausschalten (`generate_audio: false`). Der Ton kommt nur aus dem Song und `sfx/`.
5. Arbeitsweise für Qualität: erst Standbilder in 16:9 und 2k–4k erzeugen (Schlüsselbilder je Einstellung), die besten auswählen, dann Bild-zu-Video mit Start- und optional Endbild. Pro Einstellung 2–4 Takes erzeugen und den besten nehmen. Clips auf 1920×1080 bringen, Grading im Schnitt einheitlich halten (Farbton passend zum Film: dunkles Blau/Grau, orange Akzente).
6. Ohne Higgsfield gibt es diese Fallbacks ohne Credits: Blender-MCP (Geländeflug über ein echtes DEM-Stück, Licht, Regen, Blitz), die echten Murenclips, MG-Szenen in `scenes.js`, die App-Aufnahmen und Kamerafahrten über bestehende KI-Standbilder.

## 6. Vorgehen (klein testen, dann voll)

1. **Plan:** Für jedes Ende eine Shot-Liste mit Zeiten auf dem Raster (Schlag/Takt/Phrase), Bildinhalt, Quelle (KI/echt/App/MG/Blender), Einblendung und Ton (welcher `sfx` auf welchem Schlag). In `reports/finale_video/V6_ENDEN_SHOTLISTE.md` schreiben.
2. **Material:** erzeugen bzw. heraussuchen. Alles nach `deliverables/finale_video/v6_material/<ende>/`, mit einer Liste der Higgsfield-Job-IDs und Prompts.
3. **Schnitt:** `build_film.py` um einen Schalter `--v6 <1..5>` ergänzen, oder ein eigenes Skript `scripts/finale_video/build_endings_v6.py`, das den V5-Kopf wiederverwendet. Das Bild bis `D` wird aus `Talwacht_Finale_v5.mp4` kopiert (Stream-Copy bis zum letzten Keyframe vor `D`, Rest dekodiert, wie `picture_v5()`). V4 und V5 müssen mit den alten Aufrufen **bitgleich** reproduzierbar bleiben.
4. **Ton:** Den V5-Mix bis `D` unverändert übernehmen. Nach `D` den Song weiterlaufen lassen, `sfx` pro Ende dazu, Ende nach Abschnitt 3. Mastering wie V5: lineare Verstärkung auf −14 LUFS, Limiter, True Peak ≤ −1 dBTP, kein dynamisches loudnorm.
5. **Pilot:** Zuerst Ende 1 komplett in 960 px bauen und prüfen (Sync-Tabelle, Kontaktbogen). Danach alle fünf in 1920.

## 7. Abgabe

Ausgabeordner: **`deliverables/finale_video/enden_v6/`**. Darin nur die fertigen Clips, keine Zwischendateien:

```text
Ende_1_episch.mp4
Ende_2_cinematisch.mp4
Ende_3_anwendung.mp4
Ende_4_<name>.mp4
Ende_5_<name>.mp4
```

- Jeder Clip beginnt **12,64 s vor dem Drop**, auf dem Satzanfang von `q3` (Filmzeit 279,16 s: „Aber er hat Spuren hinterlassen, vierhundertdreiundzwanzig Mal … Das. Ist. Talwacht.“), und läuft bis zum Ende. So hört man den Anlauf und kann die fünf Enden direkt vergleichen.
- 1920×1080, 25 fps, H.264 (CRF ≤ 18), AAC 256 kbit/s.
- Zusätzlich `enden_v6/UEBERSICHT.md`: je Ende 2–3 Sätze zur Idee, Länge, verwendetes Material (KI/echt), und ein Kontaktbogen-PNG (alle 0,4 s ein Bild ab `D`).
- Ganze Filme erst rendern, wenn der Nutzer ein Ende ausgewählt hat.

## 8. Abnahme (messen, nicht aus dem Gedächtnis)

1. `ffprobe` aller Clips: Auflösung, fps, Dauer, Audio-Codec.
2. **Gleichheit bis zum Drop:** Clip-Bild und -Ton von 279,16 bis `D` gegen V5 vergleichen (PSNR ≥ 50 dB oder inf).
3. **Sync:** Pegelsprung bei `D` ± 1 Frame. Sync-Tabelle aller Schnitte (Soll/Ist) in der Übersicht.
4. Lautheit −14 LUFS ± 0,5, True Peak ≤ −1 dBTP.
5. Jede KI-Einstellung trägt sichtbar „KI-generierte Illustration“, jeder echte Clip seine Quelle (im Kontaktbogen prüfen).
6. Higgsfield: Kontostand vorher und nachher im Bericht. Er muss gleich geblieben sein.

## 9. Abschluss

- Kurzer Bericht an den Nutzer: der Ordnerpfad, eine Zeile pro Ende, Abweichungen vom Plan, Kontostand Higgsfield vorher/nachher.
- Hinweis: „Two Faced“ von purc ist ein kommerzieller Song. Bei der Jury-Vorführung meist unproblematisch, auf YouTube, Instagram oder TikTok sind Claims oder Stummschaltung möglich.
- `reports/finale_video/FAKTENCHECK.md` um die neuen Bildquellen der Enden ergänzen (als Abschnitt „V6-Enden, Entwurf“).
- Skripte und Berichte committen und pushen. Keine Videos, Audios oder Build-Dateien committen (gitignored).
