<script setup>
import { computed } from 'vue'
import { useResource } from './useResource.js'
import InfoTip from './InfoTip.vue'
const { data: v04, error, loading, reload } = useResource('/api/results_v04')
const n = v => Number(v).toLocaleString('de-AT')
const excluded = computed(() => v04.value ? Object.values(v04.value.counts.exclusions).reduce((a, b) => a + b, 0) : 0)
const part = computed(() => v04.value?.counts.partition)
const limits = [
  ['Rückblick statt Warnung', 'Alle Ergebnisse stammen aus vergangenen Ereignissen. Talwacht ist kein Warnsystem und keine landesweite Gefahrenkarte.'],
  ['Kontrollen sind Pseudo-Negative', 'Ein Vergleichshang ohne Meldung kann trotzdem gerutscht sein. Fehlende Meldung ist kein Nachweis von Stabilität.'],
  ['Wenige unabhängige Einheiten', 'Ein Sturm liefert viele Ereignisse. Für die Unsicherheit zählen Wetterepisoden, nicht Hänge; im Test sind es nur wenige.'],
  ['Meldeverzerrung möglich', 'Das Modell nutzt Landbedeckung und Geländeform. Offenland und Siedlungsnähe beeinflussen auch, wo Ereignisse entdeckt werden.'],
  ['Hangmuren schwach getrennt', 'Für reine Hangmuren trennt das Gelände im Pilot kaum. Eine Rangfolge darf dort keinen Hang aussortieren.'],
  ['Grobe Eingangsdaten', 'Wetterraster um 1 km, Landbedeckung und Geologie in grobem Maßstab. Kleinräumige Unterschiede am Hang gehen verloren.'],
]
</script>
<template>
  <section class="page-intro compact"><p class="eyebrow">Methodik &amp; Grenzen</p><h1>Ein fairer Vergleich.<br><span>Und was er nicht zeigen kann.</span></h1></section>

  <section class="mk-block mk-design" aria-labelledby="mk-design">
    <div class="mk-text">
      <h2 id="mk-design">Jeder gemeldete Hang bekommt fünf Doppelgänger</h2>
      <p>Für jedes dokumentierte Ereignis werden in der Umgebung fünf Hänge mit ähnlicher Neigung, Höhe und Ausrichtung gesucht, an denen nichts gemeldet wurde. Alle sechs Hänge werden zum selben Stichtag t₀ betrachtet. Das Modell muss den gemeldeten Hang innerhalb dieser Gruppe vorne einreihen.</p>
      <p>Gemessen wird das mit der <InfoTip term="withinGroupAuc" label="lokalen AUC"/>: 0,5 entspricht Zufall, 1,0 hieße, der gemeldete Hang steht immer vorne. Der Wert ist eine Rangfolge innerhalb der Gruppe, keine Angabe, wie oft ein Hang rutscht.</p>
    </div>
    <div class="slope-group mk-group" role="img" aria-label="Ein gemeldeter Hang und fünf ähnliche Vergleichshänge"><i class="positive">P</i><i v-for="i in 5" :key="i">{{ i }}</i></div>
  </section>

  <section class="mk-block mk-rules" aria-labelledby="mk-rules">
    <h2 id="mk-rules">Was den Vergleich schützt</h2>
    <ul class="mk-list">
      <li><strong>Nur Information vor t₀.</strong> Wetter und Schnee stammen aus der Zeit vor dem Bezugszeitpunkt t₀, die Landbedeckung aus einem Kartenstand davor. Nichts ab t₀ fließt ein.</li>
      <li><strong>Gruppen bleiben zusammen.</strong> Ein Ereignis und seine Vergleichshänge liegen immer im selben Datenteil. Zeitlich verbundene Ereignisse ebenfalls.</li>
      <li><strong>Ein versiegelter Test.</strong> Design und Modelle wurden vorab registriert; der Test wurde genau einmal ausgewertet und steuert keine Auswahl mehr.</li>
      <li><strong>Unsicherheit nach Einheiten.</strong> Intervalle entstehen durch Wiederziehen ganzer Wetterepisoden, nicht einzelner Hänge.</li>
    </ul>
  </section>

  <section class="mk-block" aria-labelledby="mk-data">
    <h2 id="mk-data">Datenbasis der Hauptstudie</h2>
    <p v-if="loading" role="status" class="state">Datenbasis wird geladen …</p>
    <div v-else-if="error" role="alert" class="state state-error"><p>Datenbasis nicht verfügbar. {{ error }}</p><button type="button" @click="reload">Erneut laden</button></div>
    <dl v-else-if="v04" class="mk-flow">
      <div><dt>Kandidaten aus dem Inventar</dt><dd>{{ n(v04.counts.candidates) }}</dd></div>
      <div><dt>ausgeschlossen (Wetterdaten, Kontrollen, Neigung)</dt><dd>{{ n(excluded) }}</dd></div>
      <div><dt>vollständige Gruppen</dt><dd>{{ n(v04.counts.complete_groups) }}</dd></div>
      <div><dt>Entwicklung</dt><dd>{{ n(part.development.events) }} <small>Ereignisse · {{ n(part.development.units) }} Einheiten</small></dd></div>
      <div><dt>versiegelter Test</dt><dd>{{ n(part.sealed_test.events) }} <small>Ereignisse · {{ n(part.sealed_test.units) }} Einheiten</small></dd></div>
    </dl>
    <p class="figure-note">Quellen: Ereignisse von GeoSphere Austria; Gelände aus offenen Höhenmodellen; Wetter aus GeoSphere INCA, SPARTACUS und SNOWGRID; CORINE-Landbedeckung und Geologie. Ausschlusskriterien wurden nicht für bessere Kennzahlen gelockert.</p>
  </section>

  <section class="mk-block" aria-labelledby="mk-limits">
    <h2 id="mk-limits">Grenzen</h2>
    <div class="mk-limits">
      <article v-for="[title, text] in limits" :key="title"><h3>{{ title }}</h3><p>{{ text }}</p></article>
    </div>
  </section>

  <nav class="bf-more" aria-label="Methodik im Detail">
    <p class="eyebrow">Ausführlich im Forschungsbereich</p>
    <a href="#/vorgehen">Vorgehen: sechs Schritte, Zeitachse, Schutzregeln</a>
    <a href="#/vorgehen/beispiel">Echtes Beispiel einer Gruppe auf der Karte</a>
    <a href="#/vorgehen/quellen">Qualitätsregeln, Datenquellen und Nutzungsgrenzen</a>
  </nav>
</template>
