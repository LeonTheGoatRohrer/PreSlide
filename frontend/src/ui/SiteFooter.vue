<script setup>
import {mainNav, href} from '../navigation.js'
import Signet from './Signet.vue'
</script>
<template>
  <footer class="foot dark">
    <div class="wrap foot-grid">
      <div class="foot-brand">
        <a :href="href('start')" class="foot-logo"><Signet/><span>Talwacht</span></a>
        <p>Retrospektiver Forschungsprototyp für Österreich. Kein Warnsystem, keine Gefahrenkarte.</p>
      </div>
      <nav aria-label="Fußzeile">
        <p class="eyebrow">Seiten</p>
        <a :href="href('check')">Hang-Check</a>
        <a v-for="p in mainNav" :key="p.id" :href="href(p.id)">{{ p.label }}</a>
      </nav>
      <div>
        <p class="eyebrow">Quellen und Medien</p>
        <a :href="href('ueber', 'quellen')">Datenquellen und Lizenzen</a>
        <a :href="href('ueber', 'medien')">Medien und KI</a>
        <a :href="href('ueber', 'team')">Projekt und Kontakt</a>
      </div>
      <div>
        <p class="eyebrow">Datenstände</p>
        <p class="foot-data">Ereignisse: GeoSphere Austria · Gelände: Höhenmodell Stand 2000 · Landbedeckung: CORINE 2018 · Geologie 1:500 000 · Wetter: GeoSphere INCA, SPARTACUS</p>
      </div>
    </div>
    <div class="wrap foot-base"><span>Lokale Demonstration · Stand 18. Oktober 2026</span><span>Bei Gefahr: Notruf 112 · Feuerwehr 122</span></div>
  </footer>
</template>
<style>
.foot{padding:88px 0 28px}
.foot-grid{display:grid;grid-template-columns:1.4fr 1fr 1fr 1.3fr;gap:40px}
.foot-logo{display:inline-flex;align-items:center;gap:10px;text-decoration:none;font:650 1.5rem/1 var(--f-display);font-stretch:125%;color:#fff}
.foot-logo .signet{width:38px;height:30px;color:var(--glacier)}
.foot-brand p{margin-top:16px;color:var(--on-dark-2);max-width:32ch}
.foot nav,.foot-grid>div:not(.foot-brand){display:flex;flex-direction:column;gap:2px}
.foot-grid a:not(.foot-logo){color:var(--on-dark);text-decoration:none;min-height:36px;display:flex;align-items:center}
.foot-grid a:not(.foot-logo):hover{text-decoration:underline}
.foot-data{color:var(--on-dark-2);font-size:.95rem}
.foot-base{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;margin-top:64px;padding-top:20px;border-top:1px solid rgb(255 255 255 / .12);font:400 13px/1.4 var(--f-mono);color:var(--on-dark-2)}
@media (max-width:900px){.foot-grid{grid-template-columns:1fr 1fr}}
@media (max-width:560px){.foot-grid{grid-template-columns:1fr;gap:32px}.foot{padding-top:64px}}
@media print{.foot{display:none}}
</style>
