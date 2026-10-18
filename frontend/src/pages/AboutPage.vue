<script setup>
import {vReveal} from '../ui/motion.js'
import {problemSources} from '../sources.js'
// Provenance as recorded in DATA_SOURCES.md; licences are quoted as stated there, never extended.
const data = [
  ['Dokumentierte Ereignisse', 'GeoSphere Austria, Inventar gravitativer Massenbewegungen („Naturgefahren Test“)', 'Spezifische Weiterverwendungslizenz ungeklärt; lokale, nicht kommerzielle Forschung. Rohdaten bleiben lokal.'],
  ['Gelände für das Modell', 'Mapzen/Skadi 1″ (über Österreich praktisch SRTMGL1, Aufnahme Februar 2000); DGM Österreich, EU-DEM, USGS', 'Quellen­spezifische Bedingungen der Anbieter (u. a. DGM Österreich CC BY 3.0 AT, Copernicus, USGS gemeinfrei)'],
  ['Landbedeckung', 'Copernicus CORINE Land Cover 2012 und 2018 (EEA)', 'Copernicus Land, frei und offen mit Namensnennung'],
  ['Geologie', 'GeoSphere Austria, geologische Einheiten 1:500 000', '© GeoSphere Austria, CC BY 4.0'],
  ['Wetter (Studien)', 'GeoSphere Austria INCA v1, SPARTACUS v2, SNOWGRID-CL v2, je 1 km', 'CC BY 4.0, © GeoSphere Austria'],
  ['Straßen und Gebäude', 'OpenStreetMap über Geofabrik, Stand 14.10.2026', 'ODbL 1.0, © OpenStreetMap-Mitwirkende'],
  ['Satellitenbilder (Pipeline B)', 'Copernicus Sentinel-2 L2A über Earth Search (Element 84)', 'Enthält veränderte Copernicus-Sentinel-Daten'],
  ['Kartenhintergrund', 'basemap.at (grau und Orthofoto)', 'CC BY 4.0, Quelle: basemap.at; nur Anzeige'],
  ['3D-Relief der Karte', 'Mapzen Terrarium-Kacheln (AWS Open Data)', 'Mapzen-Bedingungen; nur Anzeige, nicht im Modell'],
]
const media = [
  ['tal', 'Alpental zur blauen Stunde vor einem Gewitter', 'Startseite, Kopfbild'],
  ['hang', 'Person im Regen vor einem Bauernhaus, Blick auf den Hang', 'Startseite, drei Schritte'],
  ['morgen', 'Morgen nach dem Unwetter, frische Rutschung auf der Straße', 'Startseite, Anwendungen'],
  ['luft', 'Luftbild: Wald, Wiesen, Serpentinenstraße, Bach', 'Studienatlas, Kopf'],
]
const software = ['Vue 3 und Vite (MIT)', 'MapLibre GL JS (BSD-3-Clause)', 'FastAPI (MIT)', 'Schriften Archivo und IBM Plex über Fontsource (SIL Open Font License 1.1), lokal ausgeliefert']
</script>

<template>
  <section class="page-head wrap">
    <p class="eyebrow">Über Talwacht</p>
    <h1>Wer, welche Daten, welche KI.</h1>
    <p class="lead">Alles, was hinter der Seite steht: das Projekt, die Herkunft jeder Datenquelle und wo künstliche Intelligenz im Spiel war.</p>
  </section>

  <section id="team" class="wrap about-block" aria-labelledby="about-team">
    <h2 id="about-team" v-reveal>Das Projekt</h2>
    <div class="about-cols">
      <p v-reveal="1">Talwacht ist ein retrospektiver Forschungsprototyp für Österreich (internes Paket <code>preslide</code>), eingereicht zum Wettbewerb am 18. Oktober 2026. Die Kernfrage: Lässt sich ein Hang, an dem später eine Rutschung gemeldet wurde, vorher von ähnlichen Nachbarhängen unterscheiden?</p>
      <p v-reveal="2">Alle Berechnungen laufen lokal auf einem gewöhnlichen Laptop. Die Seite sendet keine Ortsangaben an Dritte, setzt keine Analyse- oder Werbedienste ein und lädt keine Schriften von fremden Servern. Team und Kontakt stehen in den Unterlagen der Wettbewerbseinreichung.</p>
    </div>
  </section>

  <section id="quellen" class="wrap about-block" aria-labelledby="about-src">
    <h2 id="about-src" v-reveal>Datenquellen und Lizenzen</h2>
    <div class="src-table" role="table" aria-label="Datenquellen">
      <div class="src-row src-headrow" role="row"><span role="columnheader">Wofür</span><span role="columnheader">Anbieter und Datensatz</span><span role="columnheader">Lizenz und Nutzung</span></div>
      <div v-for="([what, who, lic], i) in data" :key="what" class="src-row" role="row" v-reveal="i % 4"><span role="cell"><strong>{{ what }}</strong></span><span role="cell">{{ who }}</span><span role="cell" class="note">{{ lic }}</span></div>
    </div>
    <h3 class="about-sub">Quellen zur Ausgangslage</h3>
    <ol class="cite-list">
      <li v-for="s in problemSources" :key="s.id">{{ s.cite }} <a :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.urlLabel }}</a></li>
    </ol>
    <h3 class="about-sub">Software</h3>
    <ul class="soft-list"><li v-for="s in software" :key="s">{{ s }}</li></ul>
  </section>

  <section id="medien" class="about-media dark" aria-labelledby="about-media">
    <div class="wrap">
      <p class="eyebrow">Medien und KI</p>
      <h2 id="about-media">Die Bilder sind erfunden. Die Zahlen nicht.</h2>
      <div class="about-cols media-intro">
        <p>Alle Fotos auf dieser Seite sind <strong>KI-generierte Illustrationen</strong> (Higgsfield, Modell <code>gpt_image_2_5</code>, erzeugt am 18.10.2026). Sie zeigen keine echten Orte, Ereignisse oder Daten und sind auf dem Bild selbst gekennzeichnet. Sie stehen nie als Beleg neben einer Kennzahl.</p>
        <p>Karten, Prüfstufen, Diagramme und alle Kennzahlen stammen dagegen aus echten Daten und gespeicherten Berichten des Projekts. Code und Texte entstanden mit Unterstützung von KI-Programmierassistenten; keine Zahl wurde von einer KI erzeugt oder geschätzt.</p>
      </div>
      <ul class="media-grid">
        <li v-for="([file, motive, use]) in media" :key="file">
          <figure><img :src="`/media/${file === 'tal' ? 'tal-1200' : file === 'hang' ? 'hang-600' : file + '-960'}.webp`" loading="lazy" decoding="async" :alt="'KI-generierte Illustration: ' + motive"><span class="ai-credit">KI-generierte Illustration</span></figure>
          <p><strong>{{ motive }}</strong><span class="mono">{{ file }}.webp · {{ use }}</span></p>
        </li>
      </ul>
      <p class="note media-proc">Ablauf: je eine Probe in Standardqualität, danach die gewählte Probe als Bildreferenz für die Endfassung (2k, hohe Qualität), umgewandelt in WebP. Herkunft, Aufträge und Prompts: <code>frontend/public/media/README.md</code>.</p>
    </div>
  </section>
</template>

<style>
.about-block{padding-bottom:clamp(64px,9vw,120px)}
.about-block h2{margin-bottom:28px}
.about-cols{display:grid;grid-template-columns:1fr 1fr;gap:32px 56px}
.about-cols p{color:var(--ink-2)}
code{font:500 .9em/1 var(--f-mono);background:var(--paper-2);padding:2px 6px;border-radius:5px}
.dark code{background:var(--slate-700)}
.src-table{border-top:1px solid var(--line-2)}
.src-row{display:grid;grid-template-columns:1fr 1.6fr 1.6fr;gap:24px;padding:18px 0;border-bottom:1px solid var(--line)}
.src-headrow{font:500 12px/1.4 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2);padding:14px 0}
.about-sub{margin:48px 0 16px}
.cite-list,.soft-list{margin:0;padding-left:1.2em;display:grid;gap:10px;color:var(--ink-2);max-width:900px}
.about-media{padding:var(--section) 0}
.about-media h2{color:#fff;max-width:18ch;margin-bottom:32px}
.about-media .about-cols p{color:var(--on-dark-2)}
.about-media strong{color:#fff}
.media-grid{list-style:none;margin:56px 0 0;padding:0;display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.media-grid figure{position:relative;margin:0;border-radius:14px;overflow:hidden;aspect-ratio:4/3}
.media-grid img{width:100%;height:100%;object-fit:cover}
.media-grid p{display:flex;flex-direction:column;gap:4px;margin-top:12px;font-size:.95rem}
.media-grid .mono{font-size:12px;color:var(--on-dark-2)}
.media-proc{margin-top:40px;max-width:80ch}
@media (max-width:900px){.about-cols{grid-template-columns:1fr}.media-grid{grid-template-columns:1fr 1fr}.src-row{grid-template-columns:1fr;gap:4px}.src-headrow{display:none}}
</style>
