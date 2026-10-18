# Medien: Herkunft und Kennzeichnung

Alle Bilder in diesem Ordner sind **KI-generierte Illustrationen** (Higgsfield, Modell `gpt_image_2_5`), erzeugt am
18.10.2026 für die Talwacht-Webseite. Sie zeigen keine echten Orte, Ereignisse oder Daten und müssen auf der Seite
sichtbar als „KI-generierte Illustration“ gekennzeichnet werden.

Ablauf: je eine Probe in Standardqualität (1k, low, 0,25 Credits), danach die ausgewählte Probe als Bildreferenz
(`image_references`) für die Endfassung in `resolution: 2k`, `quality: high` (2,75 Credits). Gesamt 12 Credits.
Umgewandelt mit Pillow 12.3 in WebP (Qualität 62–78, Lanczos-Skalierung).

| Datei | Größen | Seitenverhältnis | Probe-Job | End-Job | Motiv / Verwendungsidee |
|---|---|---|---|---|---|
| `tal.webp`, `tal-1200.webp` | 2400 × 1029, 1200 × 514 | 21:9 | `9eb36df5-3b8a-401e-8da4-dec679f31387` | `d3e15296-40b6-43c2-962a-d242e2b4a961` | Alpental zur blauen Stunde vor einem Gewitter, Dorf mit Kirche, Bach, Straße; ruhiger Himmel oben für die Überschrift. Hero |
| `hang.webp`, `hang-600.webp` | 1200 × 1500, 600 × 750 | 4:5 | `dc33bd49-99a0-4be3-86c9-ab3e20187d87` | `e0d571e9-e085-435f-bae1-6e789b6c7fc0` | Person von hinten im Regen vor einem Bauernhaus, Blick auf den steilen Hang darüber. „Dein Hang“ |
| `morgen.webp`, `morgen-960.webp` | 1920 × 1086, 960 × 543 | 16:9 | `ca161adb-df4b-4eb8-898c-455f9ca5dca9` | `c6505804-06a4-44bd-815b-6b897dc70c84` | Morgen nach dem Unwetter: frische Hangrutschung bis auf die Straße, zwei Personen in Warnkleidung. Problem / Anwendung |
| `luft.webp`, `luft-960.webp` | 1600 × 905, 960 × 543 | 16:9 | `590ba0f7-9e44-4e89-b725-e8732ae0b4fa` | `53ca2967-7030-45b2-bd66-395ec0a19fb6` | Luftbild senkrecht: Wald, Wiesen, Serpentinenstraße, Bach. Ruhige Fläche / Übergang |

Prompts (Endfassung, gekürzt; vollständige Probe-Prompts in der Session vom 18.10.2026):

- **tal**: „cinematic wide landscape photograph of a narrow Austrian alpine valley at blue hour just before a heavy
  summer thunderstorm … village with white church and warm window lights, creek and winding road … calm dark sky in
  the upper third free for a headline … no people, no text, no logos“
- **hang**: „documentary photograph from behind of a person in a dark rain jacket in a garden next to a traditional
  Austrian alpine farmhouse, looking up at a steep wet meadow slope above the house in light rain … face not visible“
- **morgen**: „early morning after a storm in an Austrian alpine valley, a fresh shallow landslide scar on a steep
  green meadow slope, mud and stones have run down onto a narrow wet asphalt road, two workers in orange
  high-visibility jackets assess it from a safe distance“
- **luft**: „top-down aerial drone photograph of Austrian alpine terrain, spruce forest, steep green meadows, a thin
  gravel road with switchbacks and a creek in a gully“

Restguthaben nach der Erzeugung: 17,42 Credits (Plan „plus“).
