<script setup>
import {ref,computed,onMounted} from 'vue'
const data=ref(null),error=ref(''),sheet=ref(0)
const n=(v,d=3)=>v==null?'–':Number(v).toFixed(d).replace('.',',')
const pct=v=>v==null?'–':(100*Number(v)).toFixed(0)+' %'
const setNames={change_features:'Veränderungsmerkmale',contrast_only:'nur lokale Kontraste',ring_only_shortcut:'Abkürzungstest: nur Umgebung',nuisance_only_shortcut:'Abkürzungstest: nur Aufnahmezeitpunkte/Wolken'}
const modelNames={logistic_regression:'Logistische Regression',hist_gradient_boosting:'Gradient Boosting'}
const reasonNames={position_coarse:'Position gröber als 20 m',no_usable_before:'kein brauchbares Vorher-Bild',no_usable_after:'kein brauchbares Nachher-Bild',no_sentinel2_items:'keine Sentinel-2-Aufnahme','year_before_2018_no_l2a':'vor 2018: keine L2A-Daten'}
onMounted(async()=>{try{const r=await fetch('/api/satellite');if(!r.ok)throw Error('Satellitenergebnisse nicht verfügbar ('+r.status+').');data.value=await r.json()}catch(e){error.value=e.message}})
const rows=computed(()=>Object.entries(data.value?.baseline?.models||{}).map(([k,v])=>{const [s,m]=k.split('/');return {key:k,set:setNames[s]||s,model:modelNames[m]||m,...v}}))
const exclusions=computed(()=>Object.entries(data.value?.eligibility?.exclusions||{}))
const sheets=computed(()=>data.value?.contact_sheets||[])
</script>

<template>
  <section id="satellit" class="section results sat">
    <div class="section-heading"><div><p class="section-number">08 — Satellitenbilder vor und nach bekannten Ereignissen (Pipeline B, getrennt)</p><h2>Was eine Rutschung von oben sichtbar verändert.</h2></div></div>
    <p class="section-intro">PreSlide vergleicht Satellitenaufnahmen vor und nach bekannten Rutschungen. Dadurch kann das System lernen, welche sichtbaren Landschaftsveränderungen typisch für solche Ereignisse sind. Anschließend können historische Satellitenbilder nach ähnlichen Veränderungen durchsucht werden. <b>Ein Treffer ist zunächst nur ein Kandidat und keine bestätigte Rutschung.</b></p>
    <div class="howto"><h3>Strikte Trennung</h3><p>Diese Pipeline verwendet absichtlich Bilder <em>nach</em> dem Ereignis. Das Vorhersagemodell der Abschnitte 01–07 verwendet ausschließlich Informationen vor dem Ereignistag; kein Nachher-Bild fließt dort ein. Beide Pipelines schreiben in getrennte Verzeichnisse; Tests sichern die Trennung.</p></div>
    <p v-if="error" class="section-intro">{{error}}</p>
    <template v-if="data">
      <div class="stats" aria-label="Satellitenumfang">
        <div><b>{{data.eligibility.screened}}</b><span>Ereignisse ab {{data.config.min_event_year}} geprüft</span></div>
        <div><b>{{data.eligibility.usable}}</b><span>mit brauchbarem Vorher-/Nachher-Paar</span></div>
        <div><b>{{n(data.eligibility.days_before_median,0)}} / +{{n(data.eligibility.days_after_median,0)}}</b><span>Tage vor / nach Ereignis (Median)</span></div>
        <div v-if="data.dataset"><b>{{data.dataset.groups}} × 6</b><span>Gruppen (Ereignis + 5 Kontrollen), {{data.dataset.independence_units}} unabhängige Einheiten</span></div>
      </div>
      <h3>Auswahl der Aufnahmen</h3>
      <p class="section-intro">Sentinel-2 (Copernicus, 10 m) wird nicht „zur Mittagszeit“ abgefragt, sondern aus allen Überflügen der 180 Tage vor und 120 Tage nach dem Ereignis die zeitlich nächste Aufnahme ohne Wolken, Wolkenschatten oder Schnee <em>im Ausschnitt um das Ereignis</em> gewählt (Kernfenster {{data.config.core_m}} m: höchstens {{pct(data.config.core_cloud_max)}} Wolken, {{pct(data.config.core_snow_max)}} Schnee). Der Ereignistag selbst wird nie verwendet. Ausschnitt {{data.config.patch_m}} m × {{data.config.patch_m}} m; Vergleichsfenster {{data.config.small_m}} m, {{data.config.core_m}} m und ein Ring bis {{data.config.ring_m}} m, der großflächige saisonale Unterschiede herausrechnet.</p>
      <div class="method-grid"><div><div class="exclusion" v-for="[reason,count] in exclusions" :key="reason"><span>{{reasonNames[reason]||reason}}</span><b>{{count}}</b></div><p class="footnote">Jeder Ausschluss ist mit Grund gespeichert. Ereignisse vor 2018 und mit Positionsunsicherheit über {{data.config.max_position_upper_m}} m bleiben außen vor.</p></div>
        <div class="safeguards"><h3>Qualität</h3><ul><li>Wolken, Schatten und Schnee werden je Aufnahme lokal im Ausschnitt gemessen, nicht aus der Szenenstatistik übernommen.</li><li>Vorher und Nachher liegen auf demselben 10-m-Raster; eine Verschiebungsschätzung je Paar prüft die Deckung<span v-if="data.dataset"> ({{data.dataset.coreg_shift_gt1px}} Ausschnitte über 1 Pixel)</span>.</li><li>Kontrollen sind die gematchten Nachbarhänge mit denselben Aufnahmedaten: gleiche Jahreszeit, gleicher Schnee, gleiches Licht.</li><li>Auswertung nur auf Ereignisgruppen, die das Modell nie gesehen hat.</li></ul></div></div>
      <template v-if="sheets.length">
        <h3>Kontaktbögen zur Sichtprüfung</h3>
        <p class="section-intro">Vorher (links), Nachher (Mitte), NDVI-Veränderung (rechts; blau = Vegetationsverlust). Kreuz = gemeldete Position, Kasten = {{data.config.core_m}} m. Beschriftungen sind anonymisiert.</p>
        <div class="segmented" v-if="sheets.length>1"><button v-for="(s,i) in sheets" :key="s" :class="{active:sheet===i}" @click="sheet=i">Bogen {{i+1}}</button></div>
        <img class="sheet" :src="'/api/satellite/contact_sheets/'+sheets[sheet].replace('.png','')+'.png'" alt="Kontaktbogen Satellitenbilder vorher/nachher">
      </template>
      <template v-if="data.baseline">
        <h3>Erste Basislinie: Ereignis gegen seine fünf Kontrollen</h3>
        <table><thead><tr><th>Merkmale</th><th>Modell</th><th>ROC AUC</th><th>lokale AUC</th><th>Top-1</th><th>mittlerer Rang</th></tr></thead>
          <tbody><tr v-for="r in rows" :key="r.key"><td>{{r.set}}</td><td>{{r.model}}</td><td>{{n(r.roc_auc)}}</td><td>{{n(r.within_group_auc)}}</td><td>{{n(r.top1_rate)}}</td><td>{{n(r.mean_rank,2)}}</td></tr></tbody></table>
        <p class="section-intro">Zufall: lokale AUC 0,5, Top-1 0,167, Rang 3,5. Permutationstest (Zuordnung „welcher Hang ist das Ereignis“ zufällig vertauscht, {{data.baseline.permutation_null.draws}} Durchgänge): Nullmittel {{n(data.baseline.permutation_null.null_mean)}}, beobachtet {{n(data.baseline.permutation_null.observed)}}, p = {{n(data.baseline.permutation_null.p_upper)}}. Die Abkürzungstests müssen nahe Zufall liegen: Sie nutzen nur Veränderungen der Umgebung bzw. nur Aufnahmezeitpunkte und Wolkenanteile.</p>
      </template>
      <template v-if="data.discovery">
        <h3>Wiederentdeckung zurückgehaltener Ereignisse</h3>
        <div class="stats" aria-label="Wiederentdeckung"><div><b>{{data.discovery.detected_rank1}} / {{data.discovery.events}}</b><span>auf Rang 1 wiedergefunden</span></div><div><b>{{data.discovery.detected_top3}} / {{data.discovery.events}}</b><span>unter den ersten drei</span></div><div><b>{{n(data.discovery.median_hit_distance_m,0)}} m</b><span>mittlerer Ortsfehler</span></div><div><b>{{n(data.discovery.peaks_per_km2_mean,1)}}</b><span>Kandidaten je km²</span></div></div>
        <p class="section-intro">Für jedes zurückgehaltene Ereignis wird der gesamte {{data.config.patch_m}}-m-Ausschnitt mit einem Modell abgesucht, das dessen Episode nie gesehen hat. Treffer = Maximum innerhalb {{data.discovery.hit_radius_m}} m der gemeldeten Position. Das Suchgebiet ist klein und um das Ereignis zentriert: ein Ortungstest, noch keine Suche in unbekanntem Gelände. <b>Satellitengestützter Kandidat — nicht unabhängig bestätigt.</b></p>
      </template>
      <p class="footnote">Contains modified Copernicus Sentinel data (2018–2026); Katalog: Earth Search (Element 84). Keine Koordinaten oder Quellkennungen in dieser Ansicht.</p>
    </template>
  </section>
</template>

<style scoped>
.sat table{width:100%;border-collapse:collapse;margin:.5rem 0 1.5rem;font-size:.92rem}
.sat th,.sat td{padding:.35rem .5rem;border-bottom:1px solid var(--line,#ddd);text-align:left}
.sat td:nth-child(n+3),.sat th:nth-child(n+3){text-align:right}
.sat .sheet{width:100%;max-width:1050px;display:block;margin:.5rem 0 1.5rem;border:1px solid var(--line,#ddd)}
.sat .segmented{margin:.5rem 0}
@media (max-width:600px){.sat table{font-size:.8rem;display:block;overflow-x:auto}.sat th,.sat td{padding:.25rem}}
</style>
