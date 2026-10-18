<script setup>
import { computed } from 'vue'
import { useResource } from './useResource.js'
import { comparisonInterval } from './resultIntervals.js'
import { fmt } from './metricDefinitions.js'
import IntervalPlot from './IntervalPlot.vue'
import InfoTip from './InfoTip.vue'
import ExtremwetterSection from './ExtremwetterSection.vue'
const { data: v04, error: e04, loading: l04, reload: r04 } = useResource('/api/results_v04')
const { data: bench, error: eBench, loading: lBench, reload: rBench } = useResource('/api/benchmarks')
const { data: pilot, error: ePilot, loading: lPilot, reload: rPilot } = useResource('/api/hangmuren_pilot')
const n = v => Number(v).toLocaleString('de-AT')
const signed = v => (v > 0 ? '+' : '') + fmt(v)
const range = (iv, f = fmt) => `[${f(iv[0])}; ${f(iv[1])}]`
const primary = computed(() => v04.value?.test.primary)
const test = computed(() => v04.value?.counts.partition.sealed_test)
const variants = computed(() => [['static', 'Gelände allein'], ['temporal', 'Wetter allein'], ['combined', 'Gelände + Wetter']].map(([key, label]) => ({
  key, label,
  value: v04.value?.test.results['conditional_logit/' + key]?.local_auc_weighted,
  interval: comparisonInterval(bench.value, 'v04_test', key),
})))
const combined = computed(() => v04.value?.test.results['conditional_logit/combined'])
</script>
<template>
  <section class="page-intro compact"><p class="eyebrow">Ergebnisse kurz</p><h1>Das Gelände trennt.<br><span>Das Wetter bringt keinen belegten Zusatz.</span></h1></section>

  <section class="bf-block" aria-labelledby="bf-main">
    <div class="bf-head">
      <p class="study-label">Hauptstudie V0.4 · versiegelter Test, genau einmal ausgewertet</p>
      <h2 id="bf-main">Gemeldeter Hang gegen fünf ähnliche Nachbarhänge</h2>
    </div>
    <p v-if="l04" role="status" class="state">Testergebnis wird geladen …</p>
    <div v-else-if="e04" role="alert" class="state state-error"><p>Testergebnis nicht verfügbar. {{ e04 }}</p><button type="button" @click="r04">Erneut laden</button></div>
    <div v-else-if="v04" class="bf-main">
      <div class="bf-headline">
        <strong>{{ fmt(primary.value) }}</strong>
        <span>Gelände + Wetter · <InfoTip term="withinGroupAuc" :value="primary.value" label="lokale AUC"/></span>
        <p>95-%-Intervall {{ range(primary.ci95) }} · Zufall {{ fmt(primary.chance) }} · 95-%-Grenze zufälliger Rangfolgen {{ fmt(primary.random_rank_null_q95) }} · p gegen Zufall {{ fmt(combined.p_upper_vs_random_rank) }}</p>
        <p class="figure-note">{{ n(test.events) }} Ereignisse, aber nur <strong>{{ n(test.units) }} unabhängige Einheiten</strong>. Das Intervall stammt aus dem Wiederziehen ganzer Einheiten.</p>
      </div>
      <div class="bf-variants" aria-labelledby="bf-variants-title">
        <h3 id="bf-variants-title">Gelände gegen Wetter</h3>
        <p v-if="lBench" role="status" class="state">Intervalle werden geladen …</p>
        <div v-else-if="eBench" role="alert" class="state state-error"><p>Intervalle nicht verfügbar. {{ eBench }}</p><button type="button" @click="rBench">Erneut laden</button></div>
        <div v-for="v in variants" v-else :key="v.key" class="bf-variant">
          <div class="bf-variant-label"><span>{{ v.label }}</span><strong>{{ fmt(v.value) }}</strong></div>
          <IntervalPlot v-if="v.interval" :value="v.value" :interval="v.interval.range" :reference="primary.chance" :tone="v.key === 'combined' ? 'blue' : 'grey'" :label="v.label + ', lokale AUC im Test'"/>
          <small>{{ v.interval ? v.interval.label + ' ' + range(v.interval.range) : 'Intervall für diese Variante nicht verfügbar.' }}</small>
        </div>
      </div>
    </div>
  </section>

  <section v-if="v04" class="bf-block bf-weather" aria-labelledby="bf-weather">
    <div class="bf-head">
      <p class="study-label">Gepaarter Vergleich derselben Testgruppen</p>
      <h2 id="bf-weather">Bringt das Wetter zusätzlich etwas?</h2>
    </div>
    <div class="bf-split">
      <div>
        <p class="limit-value"><strong>{{ signed(primary.combined_minus_static.mean) }}</strong> <InfoTip term="weatherDelta" :value="primary.combined_minus_static.mean" label="Gelände + Wetter minus Gelände"/></p>
        <IntervalPlot :value="primary.combined_minus_static.mean" :interval="primary.combined_minus_static.ci95" :reference="0" reference-label="kein Unterschied" :min="-0.15" :max="0.25" signed tone="grey" label="Zusatz durch Wetter"/>
      </div>
      <div>
        <p>Das 95-%-Intervall {{ range(primary.combined_minus_static.ci95, signed) }} schließt null ein. Ein Zusatznutzen des Wetters ist damit <strong>nicht belegt</strong>. Das heißt nicht, dass Wetter keinen Einfluss hat: Das Wetterraster ist rund 1 km grob, und Regen nach dem Stichtag bleibt bewusst unsichtbar.</p>
        <p class="figure-note">Die ergänzende Studie V0.5 mit zehn ungematchten Umgebungshängen kommt zum selben Schluss. Details im Forschungsbereich.</p>
      </div>
    </div>
  </section>

  <section class="bf-block bf-weak" aria-labelledby="bf-weak">
    <div class="bf-head">
      <p class="study-label">Pilot · explorativ · bereits bekannte Ereignisse</p>
      <h2 id="bf-weak">Schwäche: reine Hangmuren</h2>
    </div>
    <p v-if="lPilot" role="status" class="state">Pilotergebnis wird geladen …</p>
    <div v-else-if="ePilot" role="alert" class="state state-error"><p>Pilotergebnis nicht verfügbar. {{ ePilot }}</p><button type="button" @click="rPilot">Erneut laden</button></div>
    <div v-else-if="pilot" class="bf-split">
      <div>
        <p class="limit-value"><strong>{{ fmt(pilot.local_auc_units) }}</strong> lokale AUC, Gelände allein</p>
        <IntervalPlot :value="pilot.local_auc_units" :interval="pilot.ci95" :reference="pilot.chance" tone="mur" label="Pilot reine Hangmuren, lokale AUC"/>
        <small>95-%-Intervall {{ range(pilot.ci95) }} · {{ n(pilot.events) }} Ereignisse · {{ n(pilot.units) }} Einheiten</small>
      </div>
      <div>
        <p>Werden nur eindeutig als Hangmure gemeldete Ereignisse betrachtet, unterscheidet das Gelände den betroffenen Hang kaum von seinen Nachbarn. Das Intervall schließt den Zufallswert {{ fmt(pilot.chance) }} ein.</p>
        <p class="figure-note">Für die Prüfpunkte heißt das: Eine Geländerangfolge darf bei Hangmuren keinen Hang als unauffällig aussortieren. Je Ereignis gerechnet liegt der Wert bei {{ fmt(pilot.local_auc_events) }}.</p>
      </div>
    </div>
  </section>

  <section v-if="v04" class="bf-block" aria-labelledby="bf-storm">
    <div class="bf-head"><p class="study-label">Einordnung</p><h2 id="bf-storm">Ein Sturm prägt den Test</h2></div>
    <p class="bf-text">Ein großer Teil der Testereignisse stammt aus einer einzigen Episode (Stanz, Juli 2016). Jede unabhängige Einheit zählt deshalb gleich viel. Bei gleicher Gewichtung aller Ereignisse läge die kombinierte lokale AUC bei {{ fmt(combined.local_auc_events) }} statt {{ fmt(primary.value) }}.</p>
  </section>

  <ExtremwetterSection/>

  <nav class="bf-more" aria-label="Weiter im Forschungsbereich">
    <p class="eyebrow">Ausführlich im Forschungsbereich</p>
    <a href="#/ergebnisse/v04">V0.4: alle Modelle und Testdetails</a>
    <a href="#/ergebnisse/v05">V0.5: Umgebungshänge, Karten, Merkmale</a>
    <a href="#/ergebnisse/vergleich">Alle Untersuchungen im Vergleich</a>
    <a href="#/ergebnisse/historie">Frühere Untersuchungen und Ereignis-Explorer</a>
  </nav>
</template>
