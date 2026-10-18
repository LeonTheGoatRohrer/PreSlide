<script setup>
import { computed } from 'vue'
import { useResource } from './useResource.js'
import { fmt } from './metricDefinitions.js'
import { problemSources } from './sources.js'
import HangProfile from './HangProfile.vue'
import IntervalPlot from './IntervalPlot.vue'
import InfoTip from './InfoTip.vue'
const { data: v04, error: e04, loading: l04, reload: r04 } = useResource('/api/results_v04')
const { data: pg } = useResource('/api/pruefgebiete')
const { data: pilot, error: ePilot, loading: lPilot, reload: rPilot } = useResource('/api/hangmuren_pilot')
const n = v => Number(v).toLocaleString('de-AT')
const signed = v => (v > 0 ? '+' : '') + fmt(v)
const range = (iv, f = fmt) => `[${f(iv[0])}; ${f(iv[1])}]`
const years = computed(() => {
  const list = (pg.value?.jahre || []).map(j => j.jahr)
  return list.length ? `${Math.min(...list)}–${Math.max(...list)}` : ''
})
const primary = computed(() => v04.value?.test.primary)
const test = computed(() => v04.value?.counts.partition.sealed_test)
const chain = [
  { title: 'Prüfpunkte am Hang', text: 'Hänge im Unwettergebiet werden nach Gelände und Landbedeckung in eine Rangfolge gebracht. Ergebnis ist eine Prüfstufe, kein Urteil über den einzelnen Hang.', out: 'Prüfstufe je Hang' },
  { title: 'Möglicher Auslauf', text: 'Vom Prüfpunkt aus wird hangabwärts verfolgt, wohin abgehendes Material laufen könnte. Die Annahmen werden benannt.', out: 'Auslauf-Szenario' },
  { title: 'Betroffene Infrastruktur', text: 'Wo ein Szenario Straßen, Bahnlinien oder Gebäude erreicht, steigt die Dringlichkeit der Begehung.', out: 'Liste berührter Objekte' },
]
</script>
<template>
  <section class="start-hero" aria-labelledby="start-title">
    <div class="start-copy">
      <p class="eyebrow">Hangrutschungen und Muren in Österreich</p>
      <h1 id="start-title">Nach dem Unwetter:<br><span>Welche Hänge zuerst prüfen?</span></h1>
      <p class="start-lead">Starkregen löst Rutschungen und Muren aus. Danach stehen viele Hänge gleichzeitig zur Begutachtung an. Talwacht soll helfen, die Reihenfolge zu begründen: Welche Hänge ähneln früher betroffenen Hängen am stärksten, und wo könnte abgehendes Material Straßen oder Häuser erreichen?</p>
      <div class="start-actions">
        <a class="button-primary" href="#/pruefgebiete">Demo öffnen: Prüfgebiete <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a>
        <a class="button-primary button-check" href="#/hangcheck">Hang-Check für meinen Ort <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a>
        <a class="text-link" href="#/befunde">Ergebnisse in zwei Minuten</a>
      </div>
    </div>
    <HangProfile/>
  </section>

  <section class="start-context" aria-labelledby="ctx-title">
    <h2 id="ctx-title" class="eyebrow">Ausgangslage, belegt</h2>
    <ul class="ctx-list">
      <li v-for="s in problemSources.filter(x => x.fact)" :key="s.id"><p><strong>{{ s.fact.figure }}</strong> {{ s.fact.text }}</p><a :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.short }}</a></li>
    </ul>
    <p class="ctx-counter"><strong>Gegenbefund:</strong> Schadensereignisse an Wildbächen zeigen 1962–2017 keinen klaren Trend; zusätzliche Schutzbauten haben die Zunahme an Niederschlag bisher ausgeglichen. Mehr Regen bedeutet also nicht automatisch mehr Schaden. <a :href="problemSources.find(s => s.id === 'schloegl').url" target="_blank" rel="noopener noreferrer">Schlögl et al. 2021</a></p>
  </section>

  <section class="start-chain" aria-labelledby="chain-title">
    <div class="chain-head">
      <p class="eyebrow">Was Talwacht dafür tut</p>
      <h2 id="chain-title">Eine Kette in drei Schritten</h2>
      <p>Jeder Schritt baut auf dem vorigen auf. Die Nummern entsprechen der Skizze oben.</p>
    </div>
    <ol class="chain">
      <li v-for="(c, i) in chain" :key="c.title">
        <span class="chain-no" aria-hidden="true">{{ i + 1 }}</span>
        <h3>{{ c.title }}</h3>
        <p>{{ c.text }}</p>
        <p class="chain-out"><span>Ausgabe</span>{{ c.out }}</p>
      </li>
    </ol>
    <p class="chain-status">Stand: Die Demo zeigt die dokumentierten Ereignisse und ihre Häufung. Prüfpunkte, Auslauf und Infrastruktur werden dort schrittweise angebunden, jeweils erst nach eigener Prüfung.</p>
    <a class="button-primary" href="#/pruefgebiete">Zur Demo <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a>
  </section>

  <section class="start-figures" aria-labelledby="fig-title">
    <p class="eyebrow">Drei Kernzahlen aus dem versiegelten Test</p>
    <h2 id="fig-title" class="sr-only">Kernzahlen</h2>
    <p v-if="l04" role="status" class="state">Kernzahlen werden geladen …</p>
    <div v-else-if="e04" role="alert" class="state state-error"><p>Kernzahlen nicht verfügbar. {{ e04 }}</p><button type="button" @click="r04">Erneut laden</button></div>
    <div v-else-if="v04" class="figure-rows">
      <article class="figure-row">
        <div class="figure-value"><strong>{{ n(v04.counts.complete_groups) }}</strong><span>dokumentierte Ereignisse<template v-if="years">, {{ years }}</template></span></div>
        <div class="figure-body">
          <p>Jedes mit fünf ähnlichen Vergleichshängen ohne Meldung, alle zum selben Stichtag betrachtet. <template v-if="pg">Darunter {{ n(pg.zaehlung.hangmuren) }} reine Hangmuren.</template></p>
          <p class="figure-note">Für die Unsicherheit zählen nicht Hänge, sondern unabhängige Wetterepisoden: im Test {{ n(test.units) }} Einheiten für {{ n(test.events) }} Ereignisse.</p>
        </div>
      </article>
      <article class="figure-row">
        <div class="figure-value"><strong>{{ fmt(primary.value) }}</strong><span><InfoTip term="withinGroupAuc" :value="primary.value" label="Trennschärfe innerhalb der Gruppe"/></span></div>
        <div class="figure-body">
          <IntervalPlot :value="primary.value" :interval="primary.ci95" :reference="primary.chance" label="Gelände und Wetter, lokale AUC im Test"/>
          <p>Gelände + Wetter, 95-%-Intervall {{ range(primary.ci95) }}. Der gemeldete Hang landet deutlich öfter vor seinen Vergleichshängen als bei zufälliger Reihenfolge.</p>
        </div>
      </article>
      <article class="figure-row">
        <div class="figure-value"><strong>{{ signed(primary.combined_minus_static.mean) }}</strong><span><InfoTip term="weatherDelta" :value="primary.combined_minus_static.mean" label="Zusatz durch Wetter"/></span></div>
        <div class="figure-body">
          <IntervalPlot :value="primary.combined_minus_static.mean" :interval="primary.combined_minus_static.ci95" :reference="0" reference-label="kein Unterschied" :min="-0.15" :max="0.25" signed tone="grey" label="Zusatz durch Wetter gegenüber Gelände allein"/>
          <p>95-%-Intervall {{ range(primary.combined_minus_static.ci95, signed) }} schließt null ein: <strong>kein belegter Zusatznutzen des Wetters.</strong> Das ist ein gültiges Ergebnis, kein Fehler.</p>
        </div>
      </article>
    </div>
  </section>

  <section class="start-limit" aria-labelledby="limit-title">
    <p class="eyebrow">Ehrliche Grenze</p>
    <h2 id="limit-title">Bei reinen Hangmuren trennt das Gelände kaum.</h2>
    <div class="limit-grid">
      <div>
        <p v-if="lPilot" role="status" class="state">Pilotergebnis wird geladen …</p>
        <div v-else-if="ePilot" role="alert" class="state state-error"><p>Pilotergebnis nicht verfügbar. {{ ePilot }}</p><button type="button" @click="rPilot">Erneut laden</button></div>
        <template v-else-if="pilot">
          <p class="limit-value"><strong>{{ fmt(pilot.local_auc_units) }}</strong> lokale AUC, 95-%-Intervall {{ range(pilot.ci95) }}</p>
          <IntervalPlot :value="pilot.local_auc_units" :interval="pilot.ci95" :reference="pilot.chance" tone="mur" label="Pilot reine Hangmuren, lokale AUC"/>
          <p class="figure-note">Pilot, explorativ: {{ n(pilot.events) }} Ereignisse, {{ n(pilot.units) }} unabhängige Einheiten, bereits bekannte Daten. Das Intervall schließt den Zufallswert ein.</p>
        </template>
      </div>
      <ul class="limit-list">
        <li><strong>Rückblick, kein Warnsystem.</strong> Talwacht wurde an vergangenen Ereignissen geprüft und gibt keine Warnung für heute.</li>
        <li><strong>Rangfolge, kein Maß der Häufigkeit.</strong> Die Werte ordnen Hänge innerhalb einer Vergleichsgruppe. Sie sind nicht kalibriert und sagen nicht, wie oft ein Hang rutscht.</li>
        <li><strong>Mögliche Meldeverzerrung.</strong> Das Modell stützt sich stark auf Landbedeckung. Nahe Straßen und Siedlungen werden Ereignisse eher entdeckt und gemeldet.</li>
      </ul>
    </div>
    <a class="text-link" href="#/methodik">Methodik und alle Grenzen</a>
  </section>

  <nav class="start-paths" aria-label="Weiter">
    <a href="#/befunde"><span>Ergebnisse</span><strong>Was die Daten zeigen, mit Unsicherheit.</strong></a>
    <a href="#/methodik"><span>Methodik &amp; Grenzen</span><strong>Wie der Vergleich fair bleibt.</strong></a>
    <a href="#/forschung"><span>Forschungsbereich</span><strong>Alle Studien, Karten und die Historie.</strong></a>
  </nav>

  <section class="start-sources" aria-labelledby="src-title">
    <h2 id="src-title" class="eyebrow">Quellen zur Ausgangslage</h2>
    <ol>
      <li v-for="s in problemSources" :key="s.id">{{ s.cite }} <a :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.urlLabel }}</a></li>
    </ol>
  </section>
</template>
