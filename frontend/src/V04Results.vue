<script setup>
import {ref,computed,onMounted} from 'vue'
import SectionGuide from './SectionGuide.vue'
const data=ref(null),error=ref('')
const labels={conditional_logit:'Bedingte logistische Regression',logistic_regression:'Logistische Regression',hist_gradient_boosting:'Gradient Boosting'}
const variants={static:'Gelände',temporal:'Zeitlich (Wetter/Schnee)',combined:'Kombiniert'}
const n=v=>v==null?'–':Number(v).toFixed(3).replace('.',',')
onMounted(async()=>{try{const r=await fetch('/api/results_v04');if(!r.ok)throw Error('V0.4-Ergebnisse nicht verfügbar ('+r.status+').');data.value=await r.json()}catch(e){error.value=e.message}})
const rows=(src)=>Object.entries(src||{}).map(([k,v])=>{const [m,f]=k.split('/');return {key:k,model:labels[m],variant:variants[f],...v}})
const devRows=computed(()=>rows(data.value?.development))
const testRows=computed(()=>rows(data.value?.test?.results))
const parts=computed(()=>Object.entries(data.value?.counts.partition||{}))
const takeaway=computed(()=>{
  const p=data.value?.test?.primary;if(!p)return 'Der versiegelte Test liegt in dieser Ansicht nicht vor.'
  const aucPart=p.ci95[0]>0.5?`Die lokale AUC von ${n(p.value)} liegt mit ihrem 95-%-Intervall (${n(p.ci95[0])}–${n(p.ci95[1])}) über dem Zufall von 0,5.`:`Die lokale AUC von ${n(p.value)} ist mit ihrem 95-%-Intervall (${n(p.ci95[0])}–${n(p.ci95[1])}) nicht klar vom Zufall (0,5) zu trennen.`
  const d=p.combined_minus_static,wPart=d.ci95[0]>0?'Das Wetter verbessert das Ergebnis messbar.':d.ci95[1]<0?'Das Wetter verschlechtert das Ergebnis messbar.':`Ob das Wetter zusätzlich hilft, bleibt offen: Der Unterschied zu „nur Gelände“ (${n(d.mean)}) ist nicht von null zu trennen.`
  return aucPart+' '+wPart
})
</script>

<template>
  <section id="v04" class="section results v04">
    <div class="section-heading"><div><p class="section-number">06 — Neue Version V0.4 (getrennt von V0–V0.3)</p><h2>Mehr Episoden, versiegelter Test.</h2></div></div>
    <p v-if="error" class="section-intro">{{error}}</p>
    <template v-if="data">
      <SectionGuide kind="Teil B · Ergebnisse" what="Ein zweiter, größerer Durchlauf mit Regeln, die vor der Auswertung festgeschrieben wurden, und einem Test, den bis dahin niemand gesehen hatte." see="Zuerst der Umfang, dann das Hauptergebnis, darunter die Tabelle des versiegelten Tests und die Entwicklungsergebnisse zum Vergleich." why="Der Test wurde genau einmal bewertet und danach nicht mehr verändert. Das schließt aus, dass Einstellungen so lange angepasst wurden, bis die Zahl gut aussah." :take="takeaway"/>
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
      <table v-if="testRows.length"><thead><tr><th>Modell</th><th>Merkmale</th><th>lokale AUC</th><th>Top-1</th><th>lokale AP</th><th>lokale AUC je Ereignis</th><th>p gegen Zufall</th></tr></thead>
        <tbody><tr v-for="r in testRows" :key="r.key"><td>{{r.model}}</td><td>{{r.variant}}</td><td>{{n(r.local_auc_weighted)}}</td><td>{{n(r.top1_weighted)}}</td><td>{{n(r.local_ap_weighted)}}</td><td>{{n(r.local_auc_events)}}</td><td>{{n(r.p_upper_vs_random_rank)}}</td></tr></tbody></table>
      <p class="section-intro">„Lokale AUC“ gewichtet jede unabhängige Einheit gleich; „je Ereignis“ gewichtet jedes Ereignis gleich und wird daher vom größten Sturm im Test dominiert. Große Unterschiede zwischen beiden Spalten zeigen, dass das Ergebnis von wenigen Episoden abhängt.</p>
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
@media (max-width:600px){.v04 table{font-size:.8rem;display:block;overflow-x:auto}.v04 th,.v04 td{padding:.25rem}}
</style>
