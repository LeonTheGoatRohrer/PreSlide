<script setup>
import { useResource } from './useResource.js'
import { ref, computed } from 'vue'
import IdeaDiagram from './IdeaDiagram.vue'
import SectionNav from './SectionNav.vue'
const {data:v04,error,loading,reload}=useResource('/api/results_v04')
const {data:cases,error:caseError,loading:caseLoading}=useResource('/api/cases')
const imageFailed=ref(false)
const n=v=>v==null?'–':Number(v).toLocaleString('de-AT',{minimumFractionDigits:2,maximumFractionDigits:2})
const facts=computed(()=>v04.value?[
  {value:v04.value.counts.complete_groups,label:'Ereignisse',note:'dokumentierte Rutschungen, Österreich'},
  {value:'5',label:'Kontrollhänge je Ereignis',note:'ähnliche Hänge ohne Meldung'},
  {value:n(v04.value.test.primary.value),label:'Trennschärfe (AUC)',note:`95 % [${n(v04.value.test.primary.ci95[0])}; ${n(v04.value.test.primary.ci95[1])}] · Zufall 0,50`},
  {value:v04.value.counts.partition.sealed_test.units,label:'unabhängige Testeinheiten',note:'Stürme als Zähleinheit, nicht Hänge'}
]:[])
const nav=[{id:'kurzfassung',label:'Kurzfassung'},{id:'idee',label:'Die Idee'},{id:'zahlen',label:'Kennzahlen'},{id:'ausblick',label:'Ausblick'}]
</script>
<template>
  <section class="project-hero">
    <div class="hero-copy"><p class="eyebrow">Maschinelles Lernen · Naturgefahren · Österreich</p><h1>Was verrät<br>ein Hang,<br><span>bevor er rutscht?</span></h1><p class="hero-lead">Talwacht prüft, ob Gelände und Wetter einen später betroffenen Hang von seiner Umgebung unterscheiden.</p><div class="hero-actions"><a class="button-primary" href="#/vorgehen">Vorgehen ansehen <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a><a class="text-link" href="#/ergebnisse">Direkt zu den Ergebnissen</a></div></div>
    <figure class="terrain-cover"><div class="terrain-title"><span>Ein Blick ins Gelände</span><span>Österreich</span></div><img v-if="cases?.length && !imageFailed" :src="`/api/cases/${cases[0].id}/terrain.png`" alt="Aus realen Höhendaten abgeleitete Geländeschummerung der ersten gespeicherten Beispielgruppe" @error="imageFailed=true"/><div v-else class="terrain-empty">{{imageFailed||caseError?'Geländeabbildung nicht verfügbar.':caseLoading?'Geländeabbildung wird geladen …':'Keine Geländeabbildung vorhanden.'}}</div><div class="terrain-caption"><p>Ähnliches Gelände. Anderes Schicksal.</p></div><figcaption>Reales Geländemodell · 30-m-Raster · Beispiel {{cases?.[0]?.id || 'wird geladen'}}<small>Mapzen / Skadi · offene Daten Österreichs · Copernicus · USGS</small></figcaption></figure>
  </section>
  <SectionNav :items="nav"/>
  <section id="kurzfassung" class="brief">
    <p class="eyebrow">Kurzfassung</p>
    <div class="brief-grid">
      <article><span class="brief-tag">Frage</span><h2>Unterscheidet sich ein betroffener Hang vorher von seinen Nachbarn?</h2><p>Jeder Hang wird mit fünf ähnlichen Hängen zum selben Zeitpunkt verglichen.</p></article>
      <article><span class="brief-tag">Antwort</span><h2>Das Gelände trägt Signal, das Wetter nicht belegbar.</h2><p>Die Rangfolge liegt klar über dem Zufall. Der Zusatznutzen des Wetters bleibt statistisch offen.</p></article>
      <article><span class="brief-tag">Grenze</span><h2>Retrospektiv, kleine Fallzahl, möglicher Meldebias.</h2><p>Kein Warnsystem. Wald und Siedlungsnähe können auch beeinflussen, was gemeldet wird.</p></article>
    </div>
  </section>
  <section id="idee" class="idea"><div class="idea-text"><p class="eyebrow">Die Idee</p><h2>Ein fairer Vergleich statt eines Zufallsvergleichs.</h2><p>Ein einzelner Rutschungshang sagt wenig. Erst der Vergleich mit ähnlichen Nachbarhängen zum gleichen Zeitpunkt zeigt, was ihn unterscheidet.</p><ul class="check-list"><li>Gelände: Neigung, Höhe, Form, Landbedeckung</li><li>Wetter: Regen, Temperatur, Schnee vor dem Ereignis</li><li>Auswertung nach Gruppen, ohne Datenleck</li></ul><a class="text-link" href="#/vorgehen">Alle Schritte im Detail</a></div><IdeaDiagram/></section>
  <section id="zahlen" class="facts"><p class="eyebrow">Kennzahlen der Hauptstudie</p>
    <p v-if="loading" role="status">Kennzahlen werden geladen …</p><div v-else-if="error" role="alert"><p>{{error}}</p><button @click="reload">Erneut laden</button></div>
    <dl v-else class="facts-grid"><div v-for="f in facts" :key="f.label"><dt>{{f.label}}</dt><dd><strong>{{f.value}}</strong><small>{{f.note}}</small></dd></div></dl>
    <p class="plain-note">Retrospektiver Forschungsprototyp. Die Werte beschreiben Unterschiede zwischen Hängen, keine aktuelle Rutschungsgefahr.</p>
  </section>
  <section id="ausblick" class="outlook"><p class="eyebrow">Nächste Forschungsfrage</p><h2>Umweltsignal oder Meldebias?</h2><p>Rutschungen nahe Straßen und Siedlungen werden eher entdeckt. Als Nächstes folgen unabhängige Ereignisepisoden und Satellitenprüfungen. Das ist noch keine vorhandene Funktion.</p></section>
  <a class="next-page" href="#/vorgehen"><div><span>02 / Vorgehen</span><strong>Wie aus Hängen<br>ein Experiment wird.</strong></div><svg viewBox="0 0 48 48" aria-hidden="true"><path d="M8 24h32M26 10l14 14-14 14"/></svg></a>
</template>
