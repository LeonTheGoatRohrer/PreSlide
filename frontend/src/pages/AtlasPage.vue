<script setup>
// Studienatlas: every study of the project in one place, with stored figures from GET /api/studien.
import {ref, computed, watch, defineAsyncComponent} from 'vue'
import {marked} from 'marked'
import {useResource} from '../useResource.js'
import {filterStudies, studyForAnchor, headline, formatValue, plotScale} from '../studien.js'
import {vReveal} from '../ui/motion.js'
import StatusChip from '../ui/StatusChip.vue'
import IntervalPlot from '../ui/IntervalPlot.vue'
import Drawer from '../ui/Drawer.vue'
import '../legacy.css'
const props = defineProps({anchor: {type: String, default: ''}})
const details = {
  baseline: defineAsyncComponent(() => import('../ResearchDetails.vue')),
  v04: defineAsyncComponent(() => import('../V04Results.vue')),
  v05: defineAsyncComponent(() => import('../V05Results.vue')),
  satellite: defineAsyncComponent(() => import('../SatelliteResults.vue')),
  extremwetter: defineAsyncComponent(() => import('../ExtremwetterSection.vue')),
  hangkarte: defineAsyncComponent(() => import('../HangkartePage.vue')),
}
const BenchmarkOverview = defineAsyncComponent(() => import('../BenchmarkOverview.vue'))

const {data, error, loading, reload} = useResource('/api/studien')
const group = ref(''), openId = ref(null), report = ref({id: null, html: '', state: 'idle'}), initialCase = ref('')
const studies = computed(() => data.value?.studien ?? [])
const shown = computed(() => filterStudies(studies.value, group.value))
const timeline = computed(() => filterStudies(studies.value, ''))
const current = computed(() => studies.value.find(s => s.id === openId.value) ?? null)
const groups = computed(() => data.value?.gruppen ?? [])
const fmtDate = d => d ? new Date(d + 'T12:00:00').toLocaleDateString('de-AT', {day: '2-digit', month: '2-digit', year: 'numeric'}) : ''
const iv = f => f.intervall ? `${formatValue(f.art, f.intervall[0])} bis ${formatValue(f.art, f.intervall[1])}` : ''

function open(s) {
  openId.value = s.id; report.value = {id: null, html: '', state: 'idle'}
  history.replaceState(null, '', '#/studien#' + s.id)
}
function close() { openId.value = null; history.replaceState(null, '', '#/studien') }
async function readReport(s) {
  report.value = {id: s.id, html: '', state: 'loading'}
  try {
    const r = await fetch(`/api/studien/${encodeURIComponent(s.id)}/bericht`)
    if (!r.ok) throw new Error(r.status === 404 ? 'Der Bericht liegt in diesem Checkout nicht vor.' : `Bericht nicht erreichbar (HTTP ${r.status}).`)
    report.value = {id: s.id, html: marked.parse(await r.text(), {gfm: true}), state: 'ready'}
  } catch (e) { report.value = {id: s.id, html: '', state: 'error', message: e.message} }
}
function showCase(id) { initialCase.value = id; open(studies.value.find(s => s.id === 'baseline')) }
// Old addresses arrive as anchors (#/studien#v04): open the matching study once the atlas has loaded.
watch([() => props.anchor, studies], ([a]) => {
  if (a === 'vergleich' || a === 'kernfrage') return
  const s = studyForAnchor(studies.value, a)
  if (s && openId.value !== s.id) open(s)
}, {immediate: true})
</script>

<template>
  <section class="atlas-head">
    <picture class="atlas-img"><img src="/media/luft-960.webp" srcset="/media/luft-960.webp 960w, /media/luft.webp 1600w" sizes="100vw" alt="KI-generierte Illustration: Luftbild von Wald, Wiesen, einer Serpentinenstraße und einem Bach."></picture>
    <span class="ai-credit">KI-generierte Illustration</span>
    <div class="wrap atlas-head-copy">
      <p class="eyebrow">Studienatlas</p>
      <h1>Jede Untersuchung. Auch die, die nichts gezeigt haben.</h1>
      <p class="lead">Frage, Design, Ergebnis mit Unsicherheit, unabhängige Einheiten, Status und Bericht. Alle Zahlen kommen aus den gespeicherten Ergebnisdateien des Projekts.</p>
    </div>
  </section>

  <section id="kernfrage" class="wrap atlas-core" aria-labelledby="core-title">
    <div>
      <p class="eyebrow">Die Kernfrage</p>
      <h2 id="core-title">Unterscheidet sich ein Hang vor der Rutschung von ähnlichen Nachbarhängen?</h2>
    </div>
    <dl class="core-list">
      <div v-reveal="0"><dt>Vergleich</dt><dd>Jeder gemeldete Hang gegen fünf ähnliche Nachbarhänge ohne Meldung, alle zum selben Stichtag. Nur Information von vor dem Stichtag.</dd></div>
      <div v-reveal="1"><dt>Antwort</dt><dd>Das Gelände trennt über Zufall. Ein Zusatznutzen des Wetters ist in keiner Variante belegt.</dd></div>
      <div v-reveal="2"><dt>Grenze</dt><dd>Rückblick mit wenigen unabhängigen Episoden; ein Teil des Signals kann aus der Meldung stammen. Kein Warnsystem.</dd></div>
    </dl>
  </section>

  <p v-if="loading" class="wrap state" role="status">Studienatlas wird aus den gespeicherten Berichten geladen …</p>
  <div v-else-if="error" class="wrap state state-error" role="alert"><p>Studienatlas nicht verfügbar. {{ error }}</p><button type="button" @click="reload">Erneut laden</button></div>
  <template v-else-if="data">
    <section class="wrap atlas-time" aria-labelledby="time-title">
      <h2 id="time-title" class="eyebrow">Zeitleiste · {{ studies.length }} Untersuchungen</h2>
      <ol class="time-track">
        <li v-for="s in timeline" :key="s.id"><button type="button" :class="'st-' + s.status" @click="open(s)"><i aria-hidden="true"></i><span class="mono">{{ fmtDate(s.datum) }}</span><strong>{{ s.kurztitel ?? s.titel }}</strong></button></li>
      </ol>
      <div class="atlas-filter" role="group" aria-label="Nach Thema filtern">
        <button type="button" :aria-pressed="group === ''" @click="group = ''">Alle</button>
        <button v-for="g in groups" :key="g.id" type="button" :aria-pressed="group === g.id" @click="group = g.id">{{ g.label }}</button>
      </div>
    </section>

    <section class="wrap atlas-grid" aria-label="Studien">
      <article v-for="(s, i) in shown" :key="s.id" class="card hover atlas-card" v-reveal="i % 3">
        <div class="ac-top"><StatusChip :status="s.status"/><span class="mono ac-date">{{ fmtDate(s.datum) }}</span></div>
        <h3>{{ s.titel }}</h3>
        <p class="ac-q">{{ s.frage }}</p>
        <div v-if="headline(s)" class="ac-fig">
          <strong>{{ formatValue(headline(s).art, headline(s).wert) }}</strong>
          <span>{{ headline(s).label }}<template v-if="headline(s).intervall"> · {{ headline(s).intervall_art ?? '95-%-Intervall' }} {{ iv(headline(s)) }}</template></span>
        </div>
        <p v-else-if="!s.verfuegbar" class="ac-na">Noch nicht verfügbar</p>
        <button type="button" class="link ac-open" @click="open(s)">Details <span class="sr-only">zu {{ s.titel }}</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></button>
      </article>
    </section>

    <section id="vergleich" class="wrap atlas-compare" aria-labelledby="cmp-title">
      <p class="eyebrow">Alle Modellläufe im Vergleich</p>
      <h2 id="cmp-title">V0 bis V0.5 nebeneinander. Unterschiedliche Designs bleiben getrennt.</h2>
      <div class="legacy detail"><BenchmarkOverview/></div>
    </section>
  </template>

  <Drawer v-if="current" :label="current.titel" @close="close">
    <article class="sd">
      <header class="sd-head">
        <div class="ac-top"><StatusChip :status="current.status"/><span class="mono ac-date">{{ fmtDate(current.datum) }}</span><span v-if="current.verifikation?.status" class="sd-ver mono" :class="current.verifikation.status === 'PASS' ? 'ok' : 'bad'">Verifikation {{ current.verifikation.status }}</span></div>
        <h2>{{ current.titel }}</h2>
      </header>
      <div v-if="!current.verfuegbar" class="state" role="status"><p><strong>Noch nicht verfügbar.</strong> <template v-for="g in current.grund ?? []" :key="g">{{ g }} </template></p></div>
      <dl class="sd-facts">
        <div><dt>Frage</dt><dd>{{ current.frage }}</dd></div>
        <div v-if="current.design"><dt>Design</dt><dd>{{ current.design }}</dd></div>
        <div v-if="current.ergebnis"><dt>Ergebnis</dt><dd>{{ current.ergebnis }}</dd></div>
      </dl>
      <div v-if="current.kennzahlen?.some(f => f.verfuegbar)" class="sd-figs">
        <div v-for="f in current.kennzahlen.filter(x => x.verfuegbar)" :key="f.label" class="sd-fig">
          <div class="sd-fig-head"><strong>{{ formatValue(f.art, f.wert) }}</strong><span>{{ f.label }}</span></div>
          <IntervalPlot v-if="plotScale(f)" :value="f.wert" :interval="f.intervall" :reference="plotScale(f).reference ?? 0" :reference-label="f.bezug_label ?? (f.art === 'delta' ? 'kein Unterschied' : 'Zufall')" :min="plotScale(f).min" :max="plotScale(f).max" :signed="f.art === 'delta'" :tone="f.art === 'delta' ? 'grey' : 'moss'" :label="f.label"/>
          <p class="mono sd-fig-meta"><template v-if="f.intervall">{{ f.intervall_art ?? '95-%-Intervall' }} {{ iv(f) }}</template><template v-if="f.einheiten != null"> · {{ f.einheiten.toLocaleString('de-AT') }} {{ f.einheiten_label ?? 'unabhängige Einheiten' }}</template></p>
          <p v-if="f.satz" class="sd-fig-text">{{ f.satz }}</p>
        </div>
      </div>
      <div v-if="current.grenzen?.length" class="sd-limits"><h3>Grenzen</h3><ul><li v-for="g in current.grenzen" :key="g">{{ g }}</li></ul></div>
      <p v-if="current.link" class="sd-link"><a class="link" :href="current.link.href">{{ current.link.label }}</a></p>

      <div v-if="current.detail && details[current.detail]" class="sd-detail legacy detail">
        <component :is="details[current.detail]" v-bind="current.detail === 'baseline' ? {mode: 'method', initialCase} : {}"/>
        <component :is="details.baseline" v-if="current.detail === 'baseline'" mode="history" @show-case="showCase"/>
      </div>

      <div v-if="current.bericht" class="sd-report">
        <button v-if="report.id !== current.id" type="button" class="btn btn-quiet" @click="readReport(current)">Bericht lesen</button>
        <p v-else-if="report.state === 'loading'" class="state" role="status">Bericht wird geladen …</p>
        <p v-else-if="report.state === 'error'" class="state state-error" role="alert">{{ report.message }}</p>
        <div v-else class="md" v-html="report.html"></div>
      </div>
    </article>
  </Drawer>
</template>

<style>
.atlas-head{position:relative;padding:clamp(150px,20vh,210px) 0 clamp(56px,8vw,96px);overflow:hidden;isolation:isolate}
.atlas-img,.atlas-img img{position:absolute;inset:0;width:100%;height:100%;z-index:-2}
.atlas-img img{object-fit:cover}
.atlas-head::before{content:'';position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgb(245 243 238 / .82),rgb(245 243 238 / .9) 60%,var(--paper))}
.atlas-head h1{max-width:17ch;margin-bottom:22px}
.atlas-core{display:grid;grid-template-columns:5fr 7fr;gap:clamp(28px,5vw,72px);padding-bottom:clamp(56px,8vw,104px)}
.core-list{margin:0;display:grid;gap:0}
.core-list div{display:grid;grid-template-columns:120px 1fr;gap:20px;padding:18px 0;border-top:1px solid var(--line-2)}
.core-list dt{font:500 12px/1.6 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
.core-list dd{margin:0}
.atlas-time{padding-bottom:28px}
.time-track{list-style:none;margin:0 0 24px;padding:8px 0 16px;display:flex;gap:0;overflow-x:auto;scrollbar-width:thin;position:relative}
.time-track li{flex:none;width:150px;position:relative}
.time-track li::before{content:'';position:absolute;left:0;right:0;top:15px;height:2px;background:var(--line-2)}
.time-track button{position:relative;display:flex;flex-direction:column;gap:4px;width:100%;padding:0 12px 0 0;border:0;background:none;text-align:left;min-height:44px}
.time-track i{width:14px;height:14px;border-radius:50%;margin-top:9px;margin-bottom:8px;background:var(--paper);border:3px solid var(--ink-2)}
.time-track .st-versiegelt i,.time-track .st-eingefroren i,.time-track .st-abgeschlossen i{border-color:var(--moss);background:var(--moss)}
.time-track .st-explorativ i{border-color:#B7782A}
.time-track .st-demonstration i,.time-track .st-anwendung i{border-color:var(--infra)}
.time-track span{font-size:11.5px;color:var(--ink-2)}
.time-track strong{font-size:.92rem;line-height:1.25;font-weight:600}
.time-track button:hover strong{text-decoration:underline}
.atlas-filter{display:flex;flex-wrap:wrap;gap:8px}
.atlas-filter button{min-height:40px;padding:0 16px;border-radius:999px;border:1px solid var(--line-2);background:var(--card);font-weight:500}
.atlas-filter button[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
.atlas-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;padding-top:28px;padding-bottom:clamp(64px,9vw,120px)}
.atlas-card{display:flex;flex-direction:column;gap:10px;padding:22px}
.ac-top{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.ac-date{font-size:12px;color:var(--ink-2)}
.atlas-card h3{font-size:1.25rem}
.ac-q{color:var(--ink-2);font-size:.95rem}
.ac-fig{display:flex;flex-direction:column;gap:2px;margin-top:auto;padding-top:12px;border-top:1px solid var(--line)}
.ac-fig strong{font:650 2rem/1 var(--f-display);font-stretch:120%;font-variant-numeric:tabular-nums}
.ac-fig span{font-size:.82rem;color:var(--ink-2)}
.ac-na{margin-top:auto;padding-top:12px;border-top:1px solid var(--line);font:500 12px/1.4 var(--f-mono);color:var(--ink-2);text-transform:uppercase;letter-spacing:.1em}
.ac-open{align-self:flex-start;border:0;background:none;padding:6px 0;min-height:44px;cursor:pointer}
.atlas-compare{padding-bottom:var(--section)}
.atlas-compare h2{max-width:22ch;margin-bottom:28px}
.sd{padding:28px clamp(18px,4vw,48px) 64px}
.sd-head h2{font-size:clamp(1.9rem,3.4vw,2.8rem);margin-top:14px;max-width:20ch}
.sd-ver{font-size:12px;padding:4px 8px;border-radius:6px}
.sd-ver.ok{background:var(--moss-soft);color:var(--moss)}
.sd-ver.bad{background:#FBEAE6;color:#7A2414}
.sd .state{margin-top:20px}
.sd-facts{margin:28px 0 0}
.sd-facts div{display:grid;grid-template-columns:110px 1fr;gap:16px;padding:14px 0;border-top:1px solid var(--line)}
.sd-facts dt{font:500 12px/1.7 var(--f-mono);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
.sd-facts dd{margin:0}
.sd-figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin-top:24px}
.sd-fig{background:var(--card);border-radius:16px;box-shadow:var(--shadow);padding:18px}
.sd-fig-head{display:flex;flex-direction:column;gap:4px;margin-bottom:6px}
.sd-fig-head strong{font:650 2.2rem/1 var(--f-display);font-stretch:122%;font-variant-numeric:tabular-nums}
.sd-fig-head span{font-size:.92rem;color:var(--ink-2)}
.sd-fig-meta{font-size:12px;color:var(--ink-2);margin-top:8px}
.sd-fig-text{font-size:.92rem;margin-top:8px}
.sd-limits{margin-top:28px}
.sd-limits h3{font-size:1.1rem;margin-bottom:8px}
.sd-limits ul{margin:0;padding-left:1.2em;color:var(--ink-2);display:grid;gap:6px}
.sd-link{margin-top:20px}
.sd-detail{margin-top:36px;padding-top:24px;border-top:1px solid var(--line-2)}
.sd-report{margin-top:36px}
.md{font-size:.98rem;line-height:1.65;padding-top:16px;border-top:1px solid var(--line-2)}
.md h1{font-size:1.8rem;margin:0 0 16px}.md h2{font-size:1.4rem;margin:28px 0 10px}.md h3{font-size:1.15rem;margin:22px 0 8px}
.md p,.md ul,.md ol{margin:0 0 12px}
.md table{border-collapse:collapse;display:block;overflow-x:auto;font-size:.88rem;margin:0 0 16px}
.md th,.md td{border:1px solid var(--line-2);padding:5px 8px;text-align:left;vertical-align:top}
.md code{font-size:.85em}
.md pre{overflow:auto;background:var(--paper-2);padding:12px;border-radius:10px}
@media (max-width:980px){.atlas-grid{grid-template-columns:1fr 1fr}.atlas-core{grid-template-columns:1fr}}
@media (max-width:640px){.atlas-grid{grid-template-columns:1fr}.core-list div,.sd-facts div{grid-template-columns:1fr;gap:4px}}
</style>
