<script setup>
// Event-level error explorer. All values come from the results bundle (saved out-of-training predictions).
import { computed, ref, watch } from 'vue'
import InfoTip from './InfoTip.vue'
import { fmt } from './metricDefinitions.js'

const props = defineProps({ explorer: { type: Object, required: true }, model: { type: String, required: true }, names: Object, featureNames: Object })
const emit = defineEmits(['show-case'])
const order = ref('worst'), cohort = ref('all'), selected = ref(null)
const n = (v, d = 1) => fmt(v, d)
const rankText = v => fmt(v, Number.isInteger(v) ? 0 : 1)
const date = s => new Date(s + 'T12:00:00').toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: 'numeric' })
const state = s => s?.replace('Kaernten', 'Kärnten').replace('Oberoesterreich', 'Oberösterreich').replace('Niederoesterreich', 'Niederösterreich')

const v = (e, f = 'combined') => e.variants[props.model][f]
const change = e => v(e, 'static').rank - v(e, 'combined').rank
const matchingCut = computed(() => {
  const s = props.explorer.events.map(e => e.matching_score_mean).sort((a, b) => a - b)
  return s[Math.floor(s.length * 0.75)]
})
const filters = {
  worst: { label: 'Schlechteste Platzierung zuerst', keep: () => true, sort: (a, b) => v(b).rank - v(a).rank || v(a).controls_beaten - v(b).controls_beaten },
  best: { label: 'Beste Platzierung zuerst', keep: () => true, sort: (a, b) => v(a).rank - v(b).rank || v(b).controls_beaten - v(a).controls_beaten },
  improved: { label: 'Wetter hat verbessert', byOutcome: true, keep: e => change(e) > 0, sort: (a, b) => change(b) - change(a) },
  worsened: { label: 'Wetter hat verschlechtert', byOutcome: true, keep: e => change(e) < 0, sort: (a, b) => change(a) - change(b) },
  position: { label: 'Grobe Position (bis 100 m)', keep: e => e.position_category_m >= 100, sort: (a, b) => v(b).rank - v(a).rank },
  matching: { label: 'Schwächstes Matching (oberes Viertel)', keep: e => e.matching_score_mean >= matchingCut.value, sort: (a, b) => b.matching_score_mean - a.matching_score_mean },
  sameWeather: { label: 'Wetter nahezu gleich', keep: e => e.weather_nearly_identical, sort: (a, b) => a.weather_std_diff_median - b.weather_std_diff_median },
}
const list = computed(() => props.explorer.events
  .filter(e => cohort.value === 'all' || e.evaluation === cohort.value)
  .filter(filters[order.value].keep)
  .slice().sort(filters[order.value].sort))
watch(list, l => { if (!l.some(e => e.alias === selected.value)) selected.value = l[0]?.alias ?? null }, { immediate: true })
watch([order, cohort, () => props.model], () => { selected.value = list.value[0]?.alias ?? null })
const event = computed(() => props.explorer.events.find(e => e.alias === selected.value))
const ranked = computed(() => {
  if (!event.value) return []
  const scores = v(event.value).scores
  return event.value.slopes.map((s, i) => ({ ...s, score: scores[i] })).sort((a, b) => b.score - a.score)
})
const summary = computed(() => {
  const ev = list.value
  if (!ev.length) return null
  return { beaten: ev.reduce((s, e) => s + v(e).controls_beaten, 0) / ev.length, first: ev.filter(e => v(e).rank === 1).length, count: ev.length }
})
const verdict = computed(() => {
  if (!event.value) return ''
  const c = change(event.value)
  return c > 0 ? 'Wetter hat den Rutschungshang nach vorne gebracht' : c < 0 ? 'Wetter hat den Rutschungshang nach hinten gerückt' : 'Wetter hat den Rang nicht verändert'
})
</script>

<template>
  <div class="explorer">
    <div class="explorer-controls">
      <div class="case-picker"><label for="explorer-order">Ereignisse anzeigen</label><select id="explorer-order" v-model="order"><option v-for="(f, key) in filters" :key="key" :value="key">{{ f.label }}</option></select></div>
      <div class="segmented" role="group" aria-label="Auswertung"><button :class="{ active: cohort === 'all' }" :aria-pressed="cohort === 'all'" @click="cohort = 'all'">Alle 60</button><button :class="{ active: cohort === 'development' }" :aria-pressed="cohort === 'development'" @click="cohort = 'development'">Entwicklung</button><button :class="{ active: cohort === 'test' }" :aria-pressed="cohort === 'test'" @click="cohort = 'test'">Ursprünglicher Test</button></div>
    </div>
    <p v-if="summary" class="explorer-summary">{{ summary.count }} Ereignisse · {{ names[model] }}, Gelände + Wetter · im Mittel <InfoTip term="controlsBeaten" :value="summary.beaten" :label="`${n(summary.beaten, 2)} von 5 Kontrollen geschlagen`" /> · {{ summary.first }}× auf Rang 1<template v-if="!filters[order].byOutcome"> (Zufall wäre etwa {{ n(summary.count / 6, 1) }}×)</template><template v-else> · nach dem Ergebnis ausgewählt, daher kein Zufallsvergleich</template></p>
    <p v-else class="explorer-summary">Keine Ereignisse für diese Auswahl.</p>
    <div class="explorer-grid" v-if="event">
      <div class="explorer-list table-scroll">
        <table class="mini explorer-table"><caption class="sr-only">Ereignisliste</caption>
          <thead><tr><th>Ereignis</th><th><InfoTip term="positiveRank" label="Rang" /></th><th><InfoTip term="controlsBeaten" label="Geschlagen" /></th><th><InfoTip term="rankChange" label="Wetter" /></th></tr></thead>
          <tbody><tr v-for="e in list" :key="e.alias" :class="{ active: e.alias === selected }">
            <th><button @click="selected = e.alias" :aria-pressed="e.alias === selected">{{ e.alias }}<small>{{ date(e.event_date) }} · {{ state(e.state) }}</small></button></th>
            <td>{{ rankText(v(e).rank) }}</td><td>{{ v(e).controls_beaten }}/5</td>
            <td :class="change(e) > 0 ? 'up' : change(e) < 0 ? 'down' : ''">{{ change(e) > 0 ? '▲' : change(e) < 0 ? '▼' : '–' }} {{ change(e) ? rankText(Math.abs(change(e))) : '' }}</td>
          </tr></tbody>
        </table>
      </div>
      <div class="explorer-detail">
        <p class="eyebrow">{{ event.alias }} · {{ event.evaluation === 'test' ? 'Ursprüngliche Testgruppe' : 'Entwicklungsgruppe' }} · {{ date(event.event_date) }} · {{ state(event.state) }} · {{ event.process_type }}</p>
        <p class="explorer-source">{{ event.evaluation === 'test' ? 'Bewertet vom ursprünglichen Modell, das diese Gruppe nie gesehen hat.' : 'Bewertet nur von Modellen, die diese Gruppe nicht im Training hatten; Modellscore = Median aus fünf Wiederholungen.' }}
          <button v-if="event.demo_case" class="link-button" @click="emit('show-case', event.demo_case)">Auf der Karte ansehen ({{ event.demo_case }})</button></p>
        <div class="explorer-headline">
          <div><span><InfoTip term="positiveRank" :value="v(event).rank" label="Rang des Rutschungshangs" /></span><strong>{{ rankText(v(event).rank) }}<small> von 6</small></strong></div>
          <div><span><InfoTip term="controlsBeaten" :value="v(event).controls_beaten" label="Kontrollen geschlagen" /></span><strong>{{ v(event).controls_beaten }}<small> / 5</small></strong></div>
          <div><span><InfoTip term="rankChange" :value="change(event)" label="Durch Wetter" /></span><strong :class="change(event) > 0 ? 'up' : change(event) < 0 ? 'down' : ''">{{ change(event) > 0 ? '+' : '' }}{{ rankText(change(event)) }}</strong><small>{{ verdict }}</small></div>
        </div>
        <div class="rank-rows">
          <div v-for="f in ['static', 'temporal', 'combined']" :key="f" class="rank-row">
            <span>{{ featureNames[f] }}</span>
            <div class="rank-dots" :aria-label="`Rang ${rankText(v(event, f).rank)} von 6, ${v(event, f).controls_beaten} von 5 Kontrollen geschlagen`">
              <i v-for="(s, i) in event.slopes.map((x, k) => ({ ...x, score: v(event, f).scores[k] })).sort((a, b) => b.score - a.score)" :key="s.name" :class="{ pos: s.positive }" :title="`${i + 1}. ${s.name} · Modellscore ${n(s.score, 4)}`"></i>
            </div>
            <b>Rang {{ rankText(v(event, f).rank) }}</b>
          </div>
          <small>Punkte: alle sechs Hänge nach Modellscore geordnet, links der höchste. Blau = Rutschungshang.<template v-if="event.evaluation === 'development'"> Spanne des Rangs über die fünf Wiederholungen (Gelände + Wetter): {{ rankText(v(event).repetition_rank_min) }}–{{ rankText(v(event).repetition_rank_max) }}.</template></small>
        </div>
        <div class="table-scroll"><table class="mini explorer-slopes"><caption>Die sechs Hänge nach <InfoTip term="modelScore" label="Modellscore" /> ({{ names[model] }}, Gelände + Wetter)</caption>
          <thead><tr><th>Hang</th><th>Score</th><th>Neigung</th><th>Höhe</th><th>Exposition</th><th>Entfernung</th><th>Regen 7 T.</th><th>Regen 30 T.</th></tr></thead>
          <tbody><tr v-for="s in ranked" :key="s.name" :class="{ pos: s.positive }"><th>{{ s.name }}</th><td>{{ n(s.score, 4) }}</td><td>{{ n(s.slope) }}°</td><td>{{ n(s.elevation, 0) }} m</td><td>{{ n(s.aspect, 0) }}°</td><td>{{ s.positive ? '—' : n(s.distance_km) + ' km' }}</td><td>{{ n(s.rain_7d) }} mm</td><td>{{ n(s.rain_30d) }} mm</td></tr></tbody>
        </table></div>
        <dl class="explorer-quality">
          <div><dt><InfoTip term="matchingScore" :value="event.matching_score_mean" /></dt><dd>{{ n(event.matching_score_mean, 2) }}</dd></div>
          <div><dt><InfoTip term="weatherDifference" :value="event.weather_std_diff_median" /></dt><dd>{{ n(event.weather_std_diff_median, 2) }}{{ event.weather_nearly_identical ? ' · nahezu gleich' : '' }}</dd></div>
          <div><dt><InfoTip term="positionCategory" :value="event.position_category_m" /></dt><dd>bis {{ event.position_category_m }} m</dd></div>
          <div><dt><InfoTip term="positionSensitivity" :value="event.position_max_slope_change_deg" /></dt><dd>{{ n(event.position_max_slope_change_deg) }}°</dd></div>
          <div><dt><InfoTip term="dependencyGroups" :value="event.dependence_group_events" label="Abhängigkeitsgruppe" /></dt><dd>{{ event.dependence_group }} · {{ event.dependence_group_events }} {{ event.dependence_group_events === 1 ? 'Ereignis' : 'Ereignisse' }}</dd></div>
        </dl>
        <p class="footnote">Einzelne Ereignisse sind keine Evidenz. Schlecht platzierte Ereignisse werden bewusst nicht entfernt: Sie zeigen, wo das Modell scheitert.</p>
      </div>
    </div>
  </div>
</template>

<style>
.explorer-controls{display:flex;justify-content:space-between;align-items:end;gap:20px;flex-wrap:wrap;margin:26px 0 14px}
.explorer-controls select{min-height:44px}
.explorer-controls .segmented button{min-height:40px}
.explorer-summary{font-size:13px;color:#3c3c44;margin:0 0 18px}
.explorer-grid{display:grid;grid-template-columns:370px minmax(0,1fr);gap:40px;align-items:start}
.explorer-grid>*{min-width:0}
.explorer-list{max-height:640px;overflow:auto;border:1px solid var(--line)}
.explorer-table{width:100%}
.explorer-table th button{border:0;background:none;padding:6px 0;text-align:left;font-size:13px;display:flex;flex-direction:column;gap:2px;width:100%;min-height:40px}
.explorer-table th button small{font-size:10px;color:var(--muted);font-weight:400}
.explorer-table tr.active{background:#f3f5fb}.explorer-table tr.active th button{color:var(--blue);font-weight:600}
.explorer-table thead th{position:sticky;top:0;background:#fff;z-index:2}
.up{color:#0a6b3a}.down{color:#a3271f}
.explorer-source{font-size:12px;color:var(--muted);line-height:1.6;margin:-10px 0 18px}
.link-button{border:0;background:none;color:var(--blue);text-decoration:underline;padding:0 0 0 6px;font-size:12px;min-height:32px}
.explorer-headline{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-bottom:20px}
.explorer-headline>div{padding:16px 18px 16px 0;display:flex;flex-direction:column;gap:6px}
.explorer-headline>div+div{border-left:1px solid var(--line);padding-left:18px}
.explorer-headline span{font-size:11px;color:var(--muted)}
.explorer-headline strong{font-size:38px;font-weight:400;letter-spacing:-1.5px;line-height:1}
.explorer-headline strong small{font-size:16px;letter-spacing:0;color:var(--muted)}
.explorer-headline>div>small{font-size:11px;color:var(--muted)}
.explorer-slopes{width:100%;margin-top:24px}.explorer-slopes caption{text-align:left;font-size:12px;color:var(--muted);padding-bottom:8px}
.explorer-slopes tr.pos th,.explorer-slopes tr.pos td{color:var(--blue);font-weight:600}
.explorer-quality{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0;margin:22px 0 0;border-top:1px solid var(--line)}
.explorer-quality>div{padding:12px 12px 12px 0;border-bottom:1px solid var(--line)}
.explorer-quality dt{font-size:11px;color:var(--muted);margin-bottom:6px}.explorer-quality dd{margin:0;font-size:15px}
@media(max-width:900px){.explorer-grid{grid-template-columns:minmax(0,1fr)}.explorer-list{max-height:320px}}
@media(max-width:520px){.explorer-headline>div{padding:12px 8px 12px 0}.explorer-headline>div+div{padding-left:10px}.explorer-headline strong{font-size:28px}.explorer-headline span{font-size:10px}}
</style>
