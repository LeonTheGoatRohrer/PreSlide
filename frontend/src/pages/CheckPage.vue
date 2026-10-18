<script setup>
// Hang-Check: pick a place and radius, see where to look first; ask any review point where material could flow.
// "Starkregen oder Unwetter erwartet" switches on the heavy-rain view with all possible flow paths (scenario).
// No request ever carries weather or the switch: place and radius only; the classes never change.
import {ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineAsyncComponent} from 'vue'
import {RADIUS, clampRadius, readParams, readCheck, OFFLINE, normalize, coord, wantFlows, normalizeFlows, flowsToShow} from '../check.js'
import {createLayerLoader, FALLBACK_HINWEISE, OFFICIAL, classShareText, km, flowUrl, infraText} from '../hangcheck.js'
import {checkHash, loadExamples} from '../places.js'
import {takePendingPlace, takeArrival} from '../session.js'
import PlaceSearch from '../ui/PlaceSearch.vue'
import BottomSheet from '../ui/BottomSheet.vue'
const TerrainMap = defineAsyncComponent(() => import('../map/TerrainMap.vue'))

const props = defineProps({params: {type: Object, default: () => ({})}})
const initial = readParams(props.params)
const place = ref(takePendingPlace() ?? initial.place), radius = ref(initial.radius), rain = ref(initial.rain)
const limits = ref(RADIUS), examples = ref([]), meta = ref(null)
const status = ref('idle'), failure = ref(null), result = ref(null), phase = ref(0)
const active = ref(null), base = ref('grau'), mapNote = ref(''), copied = ref(false)
const arrival = takeArrival(), mapRef = ref(null), sheet = ref(null), listRef = ref(null)
const webgl = (() => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false } })()
let seq = 0, flowSeq = 0, timer = 0, phaseTimer = 0
const flows = ref(null), flowState = ref('idle'), flowError = ref(''), asked = ref(null)

const notice = computed(() => result.value?.raw.hinweise?.length ? result.value.raw.hinweise : meta.value?.hinweise?.length ? meta.value.hinweise : FALLBACK_HINWEISE)
const stage = computed(() => !place.value ? 1 : status.value !== 'ready' ? 2 : !rain.value ? 3 : 4)
const steps = ['Ort', 'Umkreis', 'Hänge', 'Starkregen']
const shownFlows = computed(() => flowsToShow(flows.value, rain.value, asked.value))
const flowFor = nr => (rain.value || asked.value === nr) ? flows.value?.byNr?.[nr] ?? null : null
const PHASES = ['Gelände lesen', 'Landbedeckung und Geologie', 'Hänge einstufen']
const counts = computed(() => result.value?.raw.zaehlung)
const vintages = computed(() => result.value?.raw.datenstand ?? meta.value?.datenstand ?? null)
const printDate = new Date().toLocaleDateString('de-AT', {day: '2-digit', month: '2-digit', year: 'numeric'})
const snapshot = ref(null)

function syncAddress() {
  const h = checkHash(place.value, radius.value, rain.value)
  if (location.hash !== h) history.replaceState(null, '', h)
}
// One request per place and radius (shared Hang-Check loader); the body is exactly the loader's request body:
// position and radius.
async function fetchLayer(body) {
  let r
  try {
    r = await fetch('/api/hangcheck', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
  } catch { throw OFFLINE() }
  return readCheck(r)
}
const loader = createLayerLoader(fetchLayer)
// Possible flow paths of all review points: one request per place and radius, only when the heavy-rain view is on
// or a point is asked about. Same parameters as above (position and radius), nothing else.
async function fetchFlows(body) {
  let r
  try { r = await fetch(flowUrl({longitude: body.longitude, latitude: body.latitude}, body.radius_m)) } catch { throw OFFLINE() }
  return readCheck(r)
}
const flowLoader = createLayerLoader(fetchFlows)
async function loadFlows() {
  if (!place.value || status.value !== 'ready' || !wantFlows(rain.value, asked.value)) return
  const mine = ++flowSeq
  if (!flows.value) flowState.value = 'loading'
  flowError.value = ''
  try {
    const data = await flowLoader.update({on: true, place: place.value, radiusM: radius.value})
    if (mine !== flowSeq) return
    flows.value = normalizeFlows(data); flowState.value = 'ready'
    if (asked.value != null) { await nextTick(); mapRef.value?.fitFlow(asked.value) }
  } catch (e) { if (mine === flowSeq) { flowState.value = 'error'; flowError.value = e.message } }
}
async function askFlow(nr) {
  asked.value = asked.value === nr ? null : nr
  active.value = nr
  if (asked.value == null) return
  if (flows.value) mapRef.value?.fitFlow(nr)
  await loadFlows()
}
async function compute() {
  const mine = ++seq
  if (!place.value) { status.value = 'idle'; result.value = null; return }
  status.value = 'loading'; failure.value = null; result.value = null; active.value = null
  phase.value = 0; clearInterval(phaseTimer); phaseTimer = setInterval(() => { phase.value = Math.min(PHASES.length - 1, phase.value + 1) }, 1600)
  let data
  try { data = await loader.update({on: true, place: place.value, radiusM: radius.value}) }
  catch (e) { if (mine === seq) { clearInterval(phaseTimer); status.value = 'error'; failure.value = {kind: e.kind ?? 'error', message: e.message} } return }
  if (mine !== seq) return
  clearInterval(phaseTimer)
  if (!data) { status.value = 'idle'; return }
  result.value = {raw: data, ...normalize(data, place.value)}
  status.value = 'ready'
  await nextTick()
  sheet.value?.set('halb')
  // Bring "Hier zuerst hinschauen" into view inside the panel.
  const panel = document.querySelector('.bs-body'), t = document.getElementById('cp-erg')
  if (panel && t) panel.scrollTo({top: t.getBoundingClientRect().top - panel.getBoundingClientRect().top + panel.scrollTop - 12, behavior: 'smooth'})
  loadFlows()
}
function schedule(delay = 0) { clearTimeout(timer); timer = setTimeout(compute, delay) }

function choose(p) {
  place.value = p
  if (p.radius_m) radius.value = clampRadius(p.radius_m, limits.value)
  failure.value = null
}
function pickOnMap(p) { choose({id: 'karte', name: 'Punkt auf der Karte', label: 'Punkt auf der Karte', region: '', longitude: p.longitude, latitude: p.latitude, radius_m: null}) }
function reset() { place.value = null; rain.value = false; result.value = null; status.value = 'idle'; flows.value = null; asked.value = null }
function selectPoint(nr) {
  active.value = nr
  mapRef.value?.flyToPoint(nr)
  listRef.value?.querySelector(`[data-nr="${nr}"]`)?.scrollIntoView({block: 'nearest', behavior: 'smooth'})
}
async function copyLink() {
  try { await navigator.clipboard.writeText(location.href); copied.value = true; setTimeout(() => { copied.value = false }, 1800) } catch { copied.value = false }
}
async function printList() {
  snapshot.value = await mapRef.value?.snapshot?.() ?? null
  await nextTick()
  window.print()
}
const driverText = p => (p.treiber ?? []).map(t => typeof t === 'string' ? t : t.merkmal).filter(Boolean).slice(0, 3).join(' · ')

watch([place, radius], ([p], [p0]) => {
  syncAddress()
  flowSeq++; flows.value = null; asked.value = null; flowState.value = 'idle'
  if (!p) { seq++; clearInterval(phaseTimer); status.value = 'idle'; result.value = null; return }
  schedule(p !== p0 ? 0 : 350)
})
watch(rain, () => { syncAddress(); loadFlows() })
// Address changes from outside the page (search palette, back button) set a new place.
watch(() => props.params, p => {
  const next = readParams(p, limits.value), own = takePendingPlace()
  const target = own ?? next.place
  if (target && (!place.value || target.longitude !== place.value.longitude || target.latitude !== place.value.latitude)) place.value = target
  if (next.radius !== radius.value && p.r != null) radius.value = next.radius
  if (next.rain !== rain.value && (p.regen != null || !own)) rain.value = next.rain
})
onMounted(async () => {
  syncAddress()
  if (place.value) compute()
  try {
    const e = await loadExamples()
    examples.value = e.examples; meta.value = e.meta
    if (e.meta?.radius_m) { limits.value = e.meta.radius_m; radius.value = clampRadius(radius.value, limits.value) }
  } catch { examples.value = [] }
})
onBeforeUnmount(() => { clearTimeout(timer); clearInterval(phaseTimer); seq++ })
</script>

<template>
  <div class="check" :class="{arriving: arrival}">
    <h1 class="sr-only">Hang-Check</h1>
    <div class="check-map">
      <TerrainMap v-if="webgl" ref="mapRef" :centre="place" :radius-m="radius" :cells="result?.cells ?? null" :max-d="result?.maxD ?? 1"
                  :points="result?.points ?? []" :active="active" :base="base" :arrival="arrival"
                  :flows="shownFlows" :flow-active="asked"
                  @pick="pickOnMap" @hover="nr => (active = nr)" @select="selectPoint" @failed="m => (mapNote = m)"/>
      <div v-else class="check-nogl"><p>Diese Ansicht braucht WebGL für die 3D-Karte. Ort, Umkreis und die Liste der Prüfpunkte funktionieren trotzdem.</p></div>
      <div v-if="arrival" class="arrival" aria-hidden="true"><img src="/media/tal-1200.webp" alt=""><span class="ai-credit">KI-generierte Illustration</span></div>
      <div class="map-tools" role="group" aria-label="Kartenhintergrund">
        <button type="button" :aria-pressed="base === 'grau'" @click="base = 'grau'">Karte</button>
        <button type="button" :aria-pressed="base === 'ortho'" @click="base = 'ortho'">Luftbild</button>
      </div>
      <p v-if="mapNote" class="map-note" role="status">{{ mapNote }}</p>
    </div>

    <BottomSheet ref="sheet" label="Hang-Check: Ort, Umkreis, Schalter und Ergebnis">
      <header class="cp-head">
        <p class="eyebrow">Hang-Check</p>
        <ol class="cp-progress" aria-label="Fortschritt">
          <li v-for="(s, i) in steps" :key="s" :class="{done: stage > i + 1, now: stage === i + 1}" :aria-current="stage === i + 1 ? 'step' : undefined"><span>{{ s }}</span></li>
        </ol>
      </header>

      <section class="cp-step" aria-labelledby="cp-ort">
        <h2 id="cp-ort" class="cp-title"><span class="cp-no">1</span>Ort</h2>
        <div v-if="place" class="cp-place">
          <div><strong>{{ place.name }}</strong><span v-if="place.region"> · {{ place.region }}</span><small v-if="!place.private" class="mono">{{ coord(place.latitude) }} N · {{ coord(place.longitude) }} O</small><small v-else>Standort wird nur im Browser verwendet und nicht gespeichert.</small></div>
          <button type="button" class="cp-change" @click="reset">Ändern</button>
        </div>
        <template v-else>
          <PlaceSearch compact @select="choose"/>
          <p class="cp-hint">Oder direkt auf die Karte tippen.</p>
          <div v-if="examples.length" class="cp-examples">
            <span class="cp-small">Beispiele</span>
            <button v-for="e in examples" :key="e.id" type="button" class="cp-chip" @click="choose(e)">{{ e.name }}</button>
          </div>
        </template>
      </section>

      <section class="cp-step" :class="{dim: !place}" aria-labelledby="cp-umkreis">
        <h2 id="cp-umkreis" class="cp-title"><span class="cp-no">2</span>Umkreis <output class="cp-val mono" for="cp-radius">{{ km(radius) }}</output></h2>
        <input id="cp-radius" v-model.number="radius" class="cp-range" type="range" :min="limits.min" :max="limits.max" :step="limits.step" :disabled="!place"
               :aria-valuetext="km(radius)" :style="{'--p': (radius - limits.min) / (limits.max - limits.min) * 100 + '%'}">
        <div class="cp-scale mono" aria-hidden="true"><span>{{ km(limits.min) }}</span><span>{{ km(limits.max) }}</span></div>
      </section>

      <section class="cp-step" :class="{dim: !place}" aria-labelledby="cp-regen">
        <h2 id="cp-regen" class="sr-only">Starkregen</h2>
        <label class="cp-switch" :class="{on: rain}">
          <span class="cp-no">3</span>
          <span class="cp-switch-text"><strong id="cp-sw-l">Starkregen oder Unwetter erwartet</strong><small id="cp-sw-d">Zeigt für alle Prüfpunkte, wohin Material fließen könnte, und welche Straßen und Gebäude im Szenario liegen. Ruft kein Wetter ab; die Einstufung bleibt gleich.</small></span>
          <input v-model="rain" type="checkbox" role="switch" :disabled="!place" :aria-checked="rain" aria-labelledby="cp-sw-l" aria-describedby="cp-sw-d">
          <span class="cp-toggle" aria-hidden="true"></span>
        </label>
        <p v-if="place && !rain" class="cp-hint">Bei jedem Prüfpunkt kannst du auch einzeln fragen, wohin es fließt. Die Markierung ist relativ: nicht markiert heißt nicht sicher.</p>
      </section>

      <section v-if="place" class="cp-result" aria-labelledby="cp-erg" aria-live="polite">
        <h2 id="cp-erg" class="cp-result-title">Hier zuerst hinschauen</h2>

        <div v-if="status === 'loading'" class="cp-loading" role="status">
          <ol class="cp-phases"><li v-for="(p, i) in PHASES" :key="p" :class="{done: i < phase, now: i === phase}">{{ p }}</li></ol>
          <div class="skeleton" style="height:58px"></div><div class="skeleton" style="height:58px"></div><div class="skeleton" style="height:58px"></div>
        </div>

        <div v-else-if="status === 'error'" class="state" :class="{'state-error': failure.kind !== 'busy'}" role="alert">
          <p>{{ failure.message }}</p>
          <button v-if="failure.kind === 'busy' || failure.kind === 'offline' || failure.kind === 'error'" type="button" @click="compute">Noch einmal versuchen</button>
          <button v-if="failure.kind === 'outside'" type="button" @click="reset">Anderen Ort wählen</button>
        </div>

        <template v-else-if="status === 'ready' && result">
          <ul class="cp-legend" aria-label="Legende">
            <li><i class="sw sw1"></i><span><strong>Prüfstufe 1</strong> auffälligste {{ classShareText(result.raw.stufen, 1) }} der bewerteten Hänge im Umkreis</span></li>
            <li><i class="sw sw2"></i><span><strong>Prüfstufe 2</strong> die nächsten {{ classShareText(result.raw.stufen, 2) }}</span></li>
            <li><i class="sw sw0"></i><span>ohne Markierung</span></li>
            <li v-if="shownFlows.features.length"><i class="sw swf"></i><span><strong>möglicher Fließweg</strong> (Szenario, ungeprüft): durchgezogen bis 45 m, gestrichelt bis 467 m, hellblau der Korridor</span></li>
          </ul>
          <div v-if="rain" class="cp-rainview" role="status">
            <p class="cp-rainview-title">Starkregen-Ansicht: mögliche Fließwege aller Prüfpunkte</p>
            <p v-if="flowState === 'loading'">Fließwege werden berechnet. Beim ersten Mal kann das wegen der Straßen- und Gebäudedaten etwas dauern …</p>
            <p v-else-if="flowState === 'error'" class="cp-flow-err">{{ flowError }} <button type="button" class="cp-link" @click="loadFlows">Noch einmal versuchen</button></p>
            <template v-else-if="flows">
              <p>{{ flows.hinweis }}</p>
              <p v-if="flows.osm" class="cp-small">Straßen und Gebäude: {{ flows.osm.hinweis }}<template v-if="flows.osm.stand">, Stand {{ flows.osm.stand.slice(0, 10) }}</template>.</p>
            </template>
          </div>
          <ol v-if="result.points.length" ref="listRef" class="cp-points">
            <li v-for="p in result.points" :key="p.nr" :data-nr="p.nr" :class="{on: active === p.nr}">
              <button type="button" class="cp-pt-main" @click="selectPoint(p.nr)" @mouseenter="active = p.nr" @mouseleave="active = null" @focus="active = p.nr" @blur="active = null">
                <span class="cp-pin" aria-hidden="true">{{ p.nr }}</span>
                <span class="cp-pt">
                  <strong>Prüfpunkt {{ p.nr }}</strong>
                  <span>{{ p.hoehe_m.toLocaleString('de-AT') }} m Höhe · {{ p.neigung_grad.toLocaleString('de-AT') }}° Neigung · {{ p.landbedeckung }}</span>
                  <small v-if="driverText(p)">Auffällig durch: {{ driverText(p) }}</small>
                  <small class="mono">{{ coord(p.latitude) }} N · {{ coord(p.longitude) }} O</small>
                </span>
              </button>
              <button type="button" class="cp-flow-btn" :aria-expanded="asked === p.nr || (rain && !!flowFor(p.nr))" @click="askFlow(p.nr)">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c3 4 6 7.5 6 11a6 6 0 0 1-12 0c0-3.5 3-7 6-11z"/></svg>{{ asked === p.nr ? 'Fließweg hervorgehoben' : 'Wohin fließt es?' }}
              </button>
              <p v-if="asked === p.nr && flowState === 'loading'" class="cp-flow-wait" role="status">Fließweg wird berechnet …</p>
              <p v-else-if="asked === p.nr && flowState === 'error'" class="cp-flow-err" role="alert">{{ flowError }}</p>
              <div v-if="flowFor(p.nr)" class="cp-flow">
                <p class="cp-flow-title">Möglicher Fließweg (Szenario, ungeprüft)</p>
                <dl>
                  <div v-for="(sc, k) in [flowFor(p.nr).kurz, flowFor(p.nr).lang].filter(Boolean)" :key="sc.id">
                    <dt>{{ k === 0 ? 'Kurz' : 'Lang' }} · {{ sc.bezeichnung }}</dt>
                    <dd>Weg {{ Math.round(sc.laenge_m).toLocaleString('de-AT') }} m hangabwärts. <template v-if="infraText(sc.im_szenario, flows.typen)">Im Szenario liegen: {{ infraText(sc.im_szenario, flows.typen) }}.</template><template v-else>Keine Straßen oder Gebäude im Szenario.</template>
                      <small v-if="sc.status !== 'gestoppt'">{{ sc.status_text }}.</small></dd>
                  </div>
                </dl>
                <p class="cp-small">Reichweiten aus der Literatur (Hürlimann, McArdell &amp; Rickli 2015): Median und größte beobachtete Reichweite von 178 Hangmuren. Keine Menge, keine Schutzbauten.</p>
                <template v-if="!rain">
                  <p class="cp-small">{{ flows.hinweis }}</p>
                  <p v-if="flows.osm" class="cp-small">Straßen und Gebäude: {{ flows.osm.hinweis }}<template v-if="flows.osm.stand">, Stand {{ flows.osm.stand.slice(0, 10) }}</template>.</p>
                </template>
              </div>
            </li>
          </ol>
          <p v-else class="state">In diesem Umkreis gibt es keine Prüfpunkte der Stufe 1.</p>
          <p v-if="counts" class="cp-counts">
            {{ counts.bewertet.toLocaleString('de-AT') }} von {{ counts.zellen.toLocaleString('de-AT') }} Hangzellen bewertet<template v-if="result.raw.zellgroesse_m"> ({{ result.raw.zellgroesse_m }} m)</template>.
            <template v-for="a in counts.ausgeschlossen ?? []" :key="a.grund"> {{ a.anzahl.toLocaleString('de-AT') }} {{ a.grund }}.</template>
          </p>
          <div class="cp-actions">
            <button type="button" class="btn btn-quiet" @click="copyLink">{{ copied ? 'Link kopiert' : 'Link kopieren' }}</button>
            <button type="button" class="btn btn-quiet" @click="printList">Prüfliste drucken</button>
          </div>
        </template>
      </section>

      <section class="cp-notice" aria-labelledby="cp-notice">
        <h2 id="cp-notice" class="sr-only">Wichtige Hinweise</h2>
        <div v-for="h in notice" :key="h.titel"><strong>{{ h.titel }}</strong><p>{{ h.text }}</p></div>
        <p class="cp-small">Unwetterwarnungen: <a :href="OFFICIAL.geosphere" target="_blank" rel="noopener noreferrer">GeoSphere Austria</a> und die Landeswarnzentralen. <template v-if="vintages">Datenstand: {{ Object.values(vintages).join(' · ') }}. </template><a href="#/belastbar">Wie belastbar ist das?</a></p>
      </section>
    </BottomSheet>

    <section class="print-sheet" aria-hidden="true">
      <h1>Prüfliste Hang-Check</h1>
      <p v-if="place">{{ place.name }}<template v-if="place.region"> ({{ place.region }})</template> · Umkreis {{ km(radius) }} · erstellt am {{ printDate }}</p>
      <img v-if="snapshot" :src="snapshot" alt="">
      <table v-if="result?.points.length">
        <thead><tr><th>Nr.</th><th>Höhe</th><th>Neigung</th><th>Landbedeckung</th><th>Koordinaten (WGS84)</th><th v-if="flows">Im Fließweg-Szenario (467 m)</th><th>Gesehen</th></tr></thead>
        <tbody><tr v-for="p in result.points" :key="p.nr"><td>{{ p.nr }}</td><td>{{ p.hoehe_m }} m</td><td>{{ p.neigung_grad }}°</td><td>{{ p.landbedeckung }}</td><td>{{ coord(p.latitude) }} N, {{ coord(p.longitude) }} O</td><td v-if="flows">{{ infraText(flows.byNr[p.nr]?.lang?.im_szenario, flows.typen) || 'keine' }}</td><td></td></tr></tbody>
      </table>
      <div class="print-notice"><div v-for="h in notice" :key="h.titel"><strong>{{ h.titel }}</strong> {{ h.text }}</div></div>
      <p v-if="vintages">Datenstand: {{ Object.values(vintages).join(' · ') }}<template v-if="result?.raw.modell"> · Modell {{ result.raw.modell.variante }}</template></p>
    </section>
  </div>
</template>

<style>
.check{position:fixed;inset:0;z-index:1}
.check-map{position:absolute;inset:0}
.check-nogl{position:absolute;inset:0;display:grid;place-items:center;padding:24px 24px 24px 460px;background:var(--paper-2);color:var(--ink-2)}
.arrival{position:absolute;inset:0;z-index:5;pointer-events:none;animation:arrive 1.1s var(--ease) .15s forwards}
.arrival img{width:100%;height:100%;object-fit:cover;filter:blur(8px) saturate(.45);transform:scale(1.08)}
@keyframes arrive{to{opacity:0;visibility:hidden}}
@media (prefers-reduced-motion:reduce){.arrival{display:none}}
.map-tools{position:absolute;z-index:6;right:62px;top:96px;display:flex;background:var(--card);border-radius:12px;box-shadow:var(--shadow);padding:4px}
.map-tools button{min-height:36px;padding:0 12px;border:0;border-radius:9px;background:none;font-weight:600;font-size:.92rem;color:var(--ink-2)}
.map-tools button[aria-pressed=true]{background:var(--ink);color:#fff}
.map-note{position:absolute;z-index:6;right:16px;bottom:44px;max-width:360px;padding:10px 14px;border-radius:12px;background:var(--card);box-shadow:var(--shadow);font-size:.9rem;color:var(--ink-2)}
.check .maplibregl-ctrl-top-right{top:84px}

.cp-head{margin-bottom:12px}
.cp-head .eyebrow{margin-bottom:12px}
.cp-progress{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;list-style:none;margin:0;padding:0}
.cp-progress li{font:500 11px/1.2 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-2);padding-top:10px;border-top:3px solid var(--line-2);transition:border-color .3s}
.cp-progress li.done{border-color:var(--moss);color:var(--ink)}
.cp-progress li.now{border-color:var(--ink);color:var(--ink)}
.cp-step{padding:18px 0;border-bottom:1px solid var(--line);transition:opacity .3s}
.cp-step.dim{opacity:.45}
.cp-title{display:flex;align-items:center;gap:10px;font:650 1.15rem/1.2 var(--f-display);font-stretch:112%;letter-spacing:-.01em;margin-bottom:12px}
.cp-no{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--ink);color:#fff;font:600 13px/1 var(--f-mono);flex:none}
.cp-val{margin-left:auto;font-size:.95rem;font-weight:500}
.cp-place{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;background:var(--card);border-radius:14px;box-shadow:var(--shadow)}
.cp-place div{display:flex;flex-direction:column;gap:2px;min-width:0}
.cp-place small{font-size:.82rem;color:var(--ink-2)}
.cp-change{min-height:44px;padding:0 14px;border-radius:10px;border:1px solid var(--line-2);background:none;font-weight:600}
.cp-hint{margin-top:10px;font-size:.95rem;color:var(--ink-2)}
.cp-small{font-size:.85rem;color:var(--ink-2)}
.cp-examples{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:14px}
.cp-chip{min-height:40px;padding:0 14px;border-radius:999px;border:1px solid var(--line-2);background:var(--card);font-weight:500;font-size:.92rem}
.cp-chip:hover{border-color:var(--ink)}
.cp-range{width:100%;height:44px;-webkit-appearance:none;appearance:none;background:none;margin:0}
.cp-range::-webkit-slider-runnable-track{height:6px;border-radius:3px;background:linear-gradient(90deg,var(--ink) var(--p),var(--line-2) var(--p))}
.cp-range::-moz-range-track{height:6px;border-radius:3px;background:linear-gradient(90deg,var(--ink) var(--p),var(--line-2) var(--p))}
.cp-range::-webkit-slider-thumb{-webkit-appearance:none;width:26px;height:26px;margin-top:-10px;border-radius:50%;background:var(--card);border:2px solid var(--ink);box-shadow:var(--shadow)}
.cp-range::-moz-range-thumb{width:24px;height:24px;border-radius:50%;background:var(--card);border:2px solid var(--ink)}
.cp-scale{display:flex;justify-content:space-between;font-size:.8rem;color:var(--ink-2)}
.cp-switch{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px;padding:16px;border-radius:16px;background:var(--card);box-shadow:var(--shadow);cursor:pointer;position:relative;transition:box-shadow .2s}
.cp-switch.on{box-shadow:0 0 0 2px var(--ink),var(--shadow)}
.cp-switch-text{display:flex;flex-direction:column;gap:2px}
.cp-switch-text strong{font:650 1.12rem/1.2 var(--f-display);font-stretch:110%}
.cp-switch-text small{font-size:.86rem;color:var(--ink-2)}
.cp-switch input{position:absolute;opacity:0;inset:0;cursor:pointer;margin:0}
.cp-switch input:disabled{cursor:not-allowed}
.cp-toggle{width:58px;height:34px;border-radius:17px;background:var(--line-2);position:relative;transition:background-color .25s}
.cp-toggle::after{content:'';position:absolute;top:3px;left:3px;width:28px;height:28px;border-radius:50%;background:#fff;box-shadow:0 2px 6px rgb(19 32 43 / .3);transition:transform .25s var(--ease)}
.cp-switch.on .cp-toggle{background:var(--ink)}
.cp-switch.on .cp-toggle::after{transform:translateX(24px)}
.cp-switch:has(input:focus-visible){outline:3px solid var(--moss);outline-offset:3px}
.cp-result{padding:20px 0 6px}
.cp-result-title{font-size:1.7rem;margin-bottom:14px}
.cp-loading{display:grid;gap:10px}
.cp-phases{list-style:none;margin:0 0 6px;padding:0;display:grid;gap:6px;font-size:.95rem;color:var(--ink-2)}
.cp-phases li::before{content:'○ ';color:var(--line-2)}
.cp-phases li.done::before{content:'● ';color:var(--moss)}
.cp-phases li.now{color:var(--ink);font-weight:600}
.cp-phases li.now::before{content:'◐ ';color:var(--ink)}
.cp-legend{list-style:none;margin:0 0 16px;padding:0;display:grid;gap:6px;font-size:.92rem;color:var(--ink-2)}
.cp-legend li{display:flex;align-items:center;gap:10px}
.cp-legend strong{color:var(--ink)}
.sw{width:18px;height:14px;border-radius:3px;flex:none}
.sw1{background:color-mix(in srgb,var(--stufe1) 70%,transparent);border:1px solid #8E2715}
.sw2{background:color-mix(in srgb,var(--stufe2) 70%,transparent);border:1px solid #A8641C}
.sw0{background:transparent;border:1px dashed var(--line-2)}
.cp-points{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.cp-points li{background:var(--card);border-radius:14px;box-shadow:var(--shadow);transition:box-shadow .2s}
.cp-points li.on{box-shadow:0 0 0 2px var(--stufe1),var(--shadow)}
.cp-pt-main{display:flex;gap:14px;width:100%;text-align:left;padding:14px 14px 8px;border:0;border-radius:14px;background:none}
.cp-flow-btn{display:inline-flex;align-items:center;gap:6px;min-height:40px;margin:0 14px 12px 60px;padding:0 12px;border-radius:999px;border:1px solid #9CBFD0;background:#EEF5F8;color:#1E5A7A;font-weight:600;font-size:.88rem}
.cp-flow-btn:hover{border-color:#1E5A7A}
.cp-flow-btn[aria-expanded=true]{background:#1E5A7A;color:#fff;border-color:#1E5A7A}
.cp-flow-btn svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2}
.cp-flow-wait,.cp-flow-err{margin:0 14px 12px 60px;font-size:.88rem;color:var(--ink-2)}
.cp-flow-err{color:#7A2414}
.cp-flow{margin:0 14px 14px 60px;padding:12px;border-radius:12px;background:#EEF5F8;font-size:.9rem}
.cp-flow-title{font-weight:600;color:#1E5A7A;margin-bottom:6px}
.cp-flow dl{margin:0;display:grid;gap:8px}
.cp-flow dt{font:500 11.5px/1.3 var(--f-mono);letter-spacing:.04em;text-transform:uppercase;color:var(--ink-2)}
.cp-flow dd{margin:2px 0 0}
.cp-flow dd small{display:block;color:var(--ink-2)}
.cp-flow .cp-small{margin-top:8px}
.cp-rainview{margin:0 0 14px;padding:14px;border-radius:14px;background:#EEF5F8;border:1px solid #CFE1EA;display:grid;gap:6px;font-size:.9rem}
.cp-rainview-title{font-weight:650;color:#1E5A7A}
.cp-link{border:0;background:none;padding:0;text-decoration:underline;font-weight:600;color:inherit;min-height:32px}
.swf{background:linear-gradient(90deg,#1E5A7A 55%,transparent 55%) 0 50%/100% 4px no-repeat,rgb(141 182 199 / .35);border-radius:3px}
@media (max-width:420px){.cp-flow-btn,.cp-flow,.cp-flow-wait,.cp-flow-err{margin-left:14px}}
.cp-pin{display:grid;place-items:center;flex:none;width:32px;height:32px;border-radius:50%;background:var(--ink);color:#fff;font:650 15px/1 var(--f-display)}
.cp-points li.on .cp-pin{background:var(--stufe1)}
.cp-pt{display:flex;flex-direction:column;gap:2px;min-width:0}
.cp-pt span{font-size:.95rem}
.cp-pt small{font-size:.8rem;color:var(--ink-2)}
.cp-counts{margin-top:14px;font-size:.86rem;color:var(--ink-2)}
.cp-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.cp-actions .btn{min-height:44px;padding:0 16px;font-size:.95rem}
.cp-notice{margin-top:18px;padding:18px;border-radius:16px;background:var(--slate-900);color:var(--on-dark);display:grid;gap:12px}
.cp-notice strong{color:#fff}
.cp-notice p{font-size:.9rem;color:var(--on-dark-2)}
.cp-notice a{color:var(--glacier)}
.cp-notice .cp-small{color:var(--on-dark-2)}
.print-sheet{display:none}
@media (max-width:759px){
  .map-tools{top:84px;right:58px}
  .check-nogl{padding:24px 24px 50vh}
  .cp-result-title{font-size:1.45rem}
}
@media print{
  @page{margin:14mm}
  body{background:#fff}
  .check{position:static}
  .check-map,.bs,.skip{display:none!important}
  .print-sheet{display:block;color:#000;font-size:11pt}
  .print-sheet h1{font-size:20pt;margin-bottom:6pt}
  .print-sheet img{width:100%;max-height:90mm;object-fit:cover;margin:8pt 0;border:1px solid #999}
  .print-sheet table{width:100%;border-collapse:collapse;margin:8pt 0}
  .print-sheet th,.print-sheet td{border:1px solid #666;padding:4pt 6pt;text-align:left;font-size:10pt}
  .print-sheet td:last-child{width:22mm}
  .print-notice{display:grid;gap:4pt;margin:8pt 0;padding:8pt;border:1.5pt solid #000;font-size:9.5pt}
}
</style>
