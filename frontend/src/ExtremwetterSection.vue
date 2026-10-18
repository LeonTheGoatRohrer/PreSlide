<script setup>
import { computed } from 'vue'
import { useResource } from './useResource.js'
import { extremwetterFigures, extremwetterState } from './extremwetter.js'
import { fmt } from './metricDefinitions.js'
const { data, error, loading, status, reload } = useResource('/api/extremwetter')
const state = computed(() => extremwetterState({ loading: loading.value, status: status.value, data: data.value }))
const parsed = computed(() => extremwetterFigures(data.value))
const text = v => typeof v === 'string' ? v : ''
</script>
<template>
  <section class="bf-block bf-extreme" aria-labelledby="bf-extreme">
    <div class="bf-head">
      <p class="study-label">Extremwetter · explorativ</p>
      <h2 id="bf-extreme">Extremwetter vor den Ereignissen</h2>
    </div>
    <p v-if="state === 'loading'" role="status" class="state">Extremwetter-Analyse wird abgefragt …</p>
    <div v-else-if="state === 'pending'" role="status" class="state state-pending">
      <p><strong>Analyse läuft noch.</strong> Sobald das geprüfte Ergebnis vorliegt, erscheinen hier die Kernzahlen mit Intervall.</p>
      <button type="button" @click="reload">Erneut abfragen</button>
    </div>
    <p v-else-if="state === 'missing'" role="status" class="state state-pending">Die Extremwetter-Analyse ist in diesem Stand der Oberfläche noch nicht angebunden.</p>
    <div v-else-if="state === 'error'" role="alert" class="state state-error"><p>Extremwetter-Analyse nicht erreichbar. {{ error }}</p><button type="button" @click="reload">Erneut laden</button></div>
    <template v-else>
      <p v-if="text(data.zusammenfassung || data.summary)" class="bf-text">{{ text(data.zusammenfassung || data.summary) }}</p>
      <dl v-if="parsed.figures.length" class="ext-figures">
        <div v-for="f in parsed.figures" :key="f.label">
          <dt>{{ f.label }}</dt>
          <dd><strong>{{ fmt(f.value) }}</strong><template v-if="f.unit"> {{ f.unit }}</template><small>95-%-Intervall [{{ fmt(f.interval[0]) }}; {{ fmt(f.interval[1]) }}]<template v-if="f.note"> · {{ f.note }}</template></small></dd>
        </div>
      </dl>
      <p v-else class="state">Ergebnis liegt vor; die Kernzahlen werden nach dem Abgleich der Feldnamen hier angezeigt.</p>
      <p v-if="parsed.skipped" class="figure-note">{{ parsed.skipped }} Angabe(n) ohne vollständiges Intervall werden nicht angezeigt.</p>
      <p class="figure-note">Explorative Auswertung auf bereits bekannten Ereignissen; kein Teil des versiegelten Tests.</p>
    </template>
  </section>
</template>
