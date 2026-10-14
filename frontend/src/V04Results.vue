<script setup>
import {ref,computed,onMounted} from 'vue'
const data=ref(null),error=ref('')
const labels={conditional_logit:'Bedingte logistische Regression',logistic_regression:'Logistische Regression',hist_gradient_boosting:'Gradient Boosting'}
const variants={static:'Gelände',temporal:'Zeitlich (Wetter/Schnee)',combined:'Kombiniert'}
const n=v=>v==null?'–':Number(v).toFixed(3).replace('.',',')
onMounted(async()=>{try{const r=await fetch('/api/results_v04');if(!r.ok)throw Error('V0.4-Ergebnisse nicht verfügbar ('+r.status+').');data.value=await r.json()}catch(e){error.value=e.message}})
const rows=(src)=>Object.entries(src||{}).map(([k,v])=>{const [m,f]=k.split('/');return {key:k,model:labels[m],variant:variants[f],...v}})
const devRows=computed(()=>rows(data.value?.development))
const testRows=computed(()=>rows(data.value?.test?.results))
const parts=computed(()=>Object.entries(data.value?.counts.partition||{}))
</script>

<template>
  <section id="v04" class="section results v04">
    <div class="section-heading"><div><p class="section-number">07 — Neue Version V0.4 (getrennt von V0–V0.3)</p><h2>Mehr Episoden, versiegelter Test.</h2></div></div>
    <p v-if="error" class="section-intro">{{error}}</p>
    <template v-if="data">
      <p class="section-intro">Vorab registrierte Regeln: alle Ereignisse ab 2011 mit sicher bekanntem Tag (Freitext und Strukturfeld übereinstimmend), ohne Obergrenze je Sturm; jede unabhängige Episode zählt in der Auswertung gleich. Baseline-freie Episoden bilden einen versiegelten Test, der genau einmal bewertet wurde.</p>
      <div class="stats" aria-label="V0.4-Umfang">
        <div><b>{{data.counts.candidates}}</b><span>Kandidaten</span></div>
        <div><b>{{data.counts.complete_groups}}</b><span>vollständige Gruppen</span></div>
        <div v-for="[k,v] in parts" :key="k"><b>{{v.events}} / {{v.units}}</b><span>{{k==='sealed_test'?'Test':'Entwicklung'}}: Ereignisse / Einheiten</span></div>
      </div>
      <div v-if="data.test" class="howto">
        <h3>Primärer Endpunkt (versiegelter Test)</h3>
        <p>Lokale AUC der kombinierten bedingten logistischen Regression, jede Einheit gleich gewichtet: <b>{{n(data.test.primary.value)}}</b> (95 %: {{n(data.test.primary.ci95[0])}}–{{n(data.test.primary.ci95[1])}}). Zufall: 0,5; 95 % der Zufallsrangfolgen liegen unter {{n(data.test.primary.random_rank_null_q95)}}. Kombiniert minus Gelände: {{n(data.test.primary.combined_minus_static.mean)}} (95 %: {{n(data.test.primary.combined_minus_static.ci95[0])}} bis {{n(data.test.primary.combined_minus_static.ci95[1])}}).</p>
      </div>
      <h3>Versiegelter Test</h3>
      <table v-if="testRows.length"><thead><tr><th>Modell</th><th>Merkmale</th><th>lokale AUC</th><th>Top-1</th><th>lokale AP</th><th>p gegen Zufall</th></tr></thead>
        <tbody><tr v-for="r in testRows" :key="r.key"><td>{{r.model}}</td><td>{{r.variant}}</td><td>{{n(r.local_auc_weighted)}}</td><td>{{n(r.top1_weighted)}}</td><td>{{n(r.local_ap_weighted)}}</td><td>{{n(r.p_upper_vs_random_rank)}}</td></tr></tbody></table>
      <h3>Entwicklung (gruppierte Kreuzvalidierung, Median aus 5 Wiederholungen)</h3>
      <table><thead><tr><th>Modell</th><th>Merkmale</th><th>lokale AUC</th><th>Top-1</th><th>lokale AP</th></tr></thead>
        <tbody><tr v-for="r in devRows" :key="r.key"><td>{{r.model}}</td><td>{{r.variant}}</td><td>{{n(r.local_auc_weighted)}}</td><td>{{n(r.top1_weighted)}}</td><td>{{n(r.local_ap_weighted)}}</td></tr></tbody></table>
      <p class="section-intro">Zufallsreferenzen: lokale AUC 0,5, Top-1 0,167, lokale AP 0,408. Kontrollen sind Pseudo-Negative; Werte sind Rangvergleiche innerhalb gematchter Gruppen, keine Rutschungswahrscheinlichkeiten und kein Nachweis geografischer Übertragbarkeit.</p>
    </template>
  </section>
</template>

<style scoped>
.v04 table{width:100%;border-collapse:collapse;margin:.5rem 0 1.5rem;font-size:.92rem}
.v04 th,.v04 td{padding:.35rem .5rem;border-bottom:1px solid var(--line,#ddd);text-align:left}
.v04 td:nth-child(n+3),.v04 th:nth-child(n+3){text-align:right}
@media (max-width:600px){.v04 table{font-size:.8rem}.v04 th,.v04 td{padding:.25rem}}
</style>
