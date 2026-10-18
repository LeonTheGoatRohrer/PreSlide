<script setup>
// "So funktioniert's": the method as a story in five chapters, each with a graphic that stays in view while reading.
import {ref, computed, watch, defineAsyncComponent} from 'vue'
import {useResource} from '../useResource.js'
import {formatValue, plotScale} from '../studien.js'
import {driverLabel} from '../hangkarte.js'
import {vReveal} from '../ui/motion.js'
import StatusChip from '../ui/StatusChip.vue'
import IntervalPlot from '../ui/IntervalPlot.vue'
import InfoTip from '../InfoTip.vue'
import '../legacy.css'
const EventMap = defineAsyncComponent(() => import('../map/EventMap.vue'))
const WirkungsketteView = defineAsyncComponent(() => import('../wirkungskette/WirkungsketteView.vue'))

const {data: pg, error: pgError, reload: pgReload} = useResource('/api/pruefgebiete')
const {data: cases} = useResource('/api/cases')
const {data: v05} = useResource('/api/results_v05')
const {data: v04} = useResource('/api/results_v04')
const {data: atlas} = useResource('/api/studien')
const n = v => Math.round(v).toLocaleString('de-AT')
const year = ref(null)
const years = computed(() => [...new Set((pg.value?.jahre ?? []).map(j => j.jahr))].sort())
const shownCount = computed(() => (pg.value?.punkte ?? []).filter(p => !year.value || p.tag.startsWith(String(year.value))).length)
const topClusters = computed(() => [...(pg.value?.cluster ?? [])].sort((a, b) => b.n_positive - a.n_positive).slice(0, 6))

// Chapter 2 and 4: one real stored example group of the historical baseline.
const example = ref(null), exampleError = ref('')
watch(cases, async list => {
  if (!list?.length || example.value) return
  try {
    const r = await fetch(`/api/cases/${encodeURIComponent(list[0].id)}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    example.value = await r.json()
  } catch (e) { exampleError.value = `Beispielgruppe nicht verfügbar (${e.message}).` }
}, {immediate: true})
const samples = computed(() => example.value?.samples ?? [])
function placeOnImage(s) {
  const c = example.value.terrain_corners, west = c[0][0], east = c[1][0], north = c[0][1], south = c[2][1]
  return {left: (s.longitude - west) / (east - west) * 100 + '%', top: (north - s.latitude) / (north - south) * 100 + '%'}
}
const bars = computed(() => {
  const list = samples.value
  if (!list.length) return []
  const metric = (key, unit, digits = 0) => {
    const vals = list.map(s => s[key]), lo = Math.min(...vals), hi = Math.max(...vals)
    return {key, unit, rows: list.map(s => ({name: s.name, positive: s.positive, v: s[key], w: hi > lo ? 18 + (s[key] - lo) / (hi - lo) * 82 : 60,
      text: s[key].toLocaleString('de-AT', {maximumFractionDigits: digits}) + unit}))}
  }
  return [{label: 'Neigung', ...metric('slope', '°', 1)}, {label: 'Höhe', ...metric('elevation', ' m')}, {label: 'Ausrichtung', ...metric('aspect', '°')}]
})
const rain = computed(() => {
  const days = (example.value?.history ?? []).filter(h => h.name === 'Ereignishang')
  const max = Math.max(1, ...days.map(d => d.rain_mm))
  return {days, max, total: days.reduce((a, d) => a + d.rain_mm, 0)}
})
const fmtDate = d => new Date(d + 'T12:00:00').toLocaleDateString('de-AT', {day: 'numeric', month: 'long', year: 'numeric'})

// Chapter 3: strongest terrain, land-cover and geology coefficients of the stored V0.5 model (standardised).
const learned = computed(() => Object.entries(v05.value?.coefficients ?? {})
  .filter(([k]) => driverLabel(k) !== k).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 6)
  .map(([k, c]) => ({k, label: driverLabel(k), c})))
const maxCoef = computed(() => Math.max(...learned.value.map(l => Math.abs(l.c)), 0.0001))
const weather = computed(() => atlas.value?.studien?.find(s => s.id === 'v04')?.kennzahlen?.[2] ?? null)
const part = computed(() => v04.value?.counts.partition)
const excluded = computed(() => v04.value ? Object.values(v04.value.counts.exclusions).reduce((a, b) => a + b, 0) : 0)
const iv = f => `${formatValue(f.art, f.intervall[0])} bis ${formatValue(f.art, f.intervall[1])}`
</script>

<template>
  <section class="page-head wrap">
    <p class="eyebrow">So funktioniert's</p>
    <h1>Woher Talwacht weiß, welche Hänge auffallen.</h1>
    <p class="lead">Fünf Kapitel vom gemeldeten Hang bis zur Straße darunter. Jede Grafik zeigt echte, gespeicherte Daten des Projekts.</p>
  </section>

  <section class="ch wrap" aria-labelledby="ch1">
    <div class="ch-text">
      <p class="ch-no mono">Kapitel 1</p>
      <h2 id="ch1">Gemeldete Hänge</h2>
      <p>Ausgangspunkt sind Rutschungen und Hangmuren, die GeoSphere Austria dokumentiert hat, mit geprüftem Datum, Prozess und Lage.<template v-if="pg"> Für die Hauptstudie blieben {{ n(pg.zaehlung.positive_ereignisse) }} Ereignisse aus {{ n(pg.zaehlung.episoden) }} Wetterepisoden, darunter {{ n(pg.zaehlung.hangmuren) }} reine Hangmuren.</template></p>
      <p>Viele Punkte liegen dicht beisammen, weil ein einzelner Sturm ganze Hänge auf einmal betrifft. Deshalb zählt für die Unsicherheit die Episode, nicht der einzelne Hang.</p>
      <div v-if="years.length" class="ch-years" role="group" aria-label="Jahr wählen">
        <button type="button" :aria-pressed="year === null" @click="year = null">Alle</button>
        <button v-for="y in years" :key="y" type="button" :aria-pressed="year === y" @click="year = y">{{ y }}</button>
      </div>
      <details v-if="topClusters.length" class="ch-more">
        <summary>Die dichtesten Häufungen</summary>
        <table class="ch-table"><thead><tr><th scope="col">Beginn</th><th scope="col">Ereignisse</th><th scope="col">davon Hangmuren</th></tr></thead>
          <tbody><tr v-for="c in topClusters" :key="c.id"><td class="mono">{{ c.first_day }}</td><td>{{ n(c.n_positive) }}</td><td>{{ n(c.n_hangmure) }}</td></tr></tbody></table>
        <ul class="ch-notes"><li v-for="h in pg.hinweise" :key="h">{{ h }}</li></ul>
      </details>
    </div>
    <figure class="ch-graphic card">
      <div v-if="pg" class="ch-map"><EventMap :points="pg.punkte" :year="year"/></div>
      <div v-else-if="pgError" class="state state-error"><p>Ereignisübersicht nicht verfügbar.</p><button type="button" @click="pgReload">Erneut laden</button></div>
      <figcaption v-if="pg"><span><i class="dot d1"></i>Lockergesteinsrutschung</span><span><i class="dot d2"></i>Hangmure</span><span><i class="dot d3"></i>Hangmure gemischt</span><span class="mono">{{ n(shownCount) }} Punkte</span></figcaption>
    </figure>
  </section>

  <section class="ch wrap" aria-labelledby="ch2">
    <div class="ch-text">
      <p class="ch-no mono">Kapitel 2</p>
      <h2 id="ch2">Fünf Doppelgänger</h2>
      <p>Jeder gemeldete Hang bekommt fünf Nachbarhänge ohne Meldung, die ihm möglichst gleichen: 750 m bis 10 km entfernt, Neigung höchstens 5° anders, Höhe höchstens 150 m, Ausrichtung höchstens 45°, untereinander mindestens 400 m auseinander.</p>
      <p>Alle sechs Hänge werden zum selben Stichtag betrachtet. Das Modell muss den gemeldeten Hang innerhalb seiner Gruppe vorne einreihen. Nichts nach dem Stichtag fließt ein.</p>
      <p class="note">Vergleichshänge sind Hänge ohne dokumentierte Rutschung, keine bewiesen stabilen Hänge.</p>
    </div>
    <figure class="ch-graphic card">
      <p v-if="exampleError" class="state">{{ exampleError }}</p>
      <template v-else-if="example">
        <div class="ch-terrain"><img :src="example.terrain_url" alt="Geländeschummerung aus realen Höhendaten rund um die Beispielgruppe">
          <span v-for="(s, i) in samples" :key="s.name" class="ch-pt" :class="{pos: s.positive}" :style="placeOnImage(s)">{{ s.positive ? 'P' : i }}</span></div>
        <div class="ch-bars">
          <div v-for="b in bars" :key="b.key" class="ch-bar"><p class="mono">{{ b.label }}</p>
            <div v-for="r in b.rows" :key="r.name" class="ch-bar-row" :class="{pos: r.positive}"><span>{{ r.positive ? 'gemeldet' : r.name.replace('Kontrolle', 'Nachbar') }}</span><i :style="{width: r.w + '%'}"></i><b class="mono">{{ r.text }}</b></div>
          </div>
        </div>
        <figcaption>Echte Beispielgruppe {{ example.id }} der historischen Baseline · {{ example.state }} · {{ fmtDate(example.event_date) }}</figcaption>
      </template>
      <div v-else class="skeleton" style="height:360px"></div>
    </figure>
  </section>

  <section class="ch wrap" aria-labelledby="ch3">
    <div class="ch-text">
      <p class="ch-no mono">Kapitel 3</p>
      <h2 id="ch3">Was das Modell lernt</h2>
      <p>Gelände, Landbedeckung und Geologie liegen als Ebenen übereinander. Aus vielen Gruppen lernt ein einfaches, gut prüfbares Modell (bedingte logistische Regression), welche Unterschiede den gemeldeten Hang von seinen Doppelgängern trennen.</p>
      <p>Das Modell stützt sich stark auf die rechts gezeigten Merkmale. Das heißt nicht, dass sie Rutschungen verursachen: Siedlungsnähe etwa kann auch nur bedeuten, dass dort eher gemeldet wird.</p>
    </div>
    <figure class="ch-graphic card ch-layers-fig">
      <div class="ch-layers" aria-hidden="true">
        <div class="ly ly3"></div><div class="ly ly2"></div><div class="ly ly1"></div>
      </div>
      <ol class="ly-key"><li><i class="ly3"></i>Geologie 1:500 000</li><li><i class="ly2"></i>Landbedeckung CORINE 2018</li><li><i class="ly1"></i>Gelände 30 m, Stand 2000</li></ol>
      <div v-if="learned.length" class="ch-coef">
        <p class="mono">Stärkste Merkmale · V0.5-Modell, explorativ · standardisierte Koeffizienten</p>
        <div v-for="l in learned" :key="l.k" class="ch-coef-row"><span>{{ l.label }}</span><i :class="l.c > 0 ? 'up' : 'down'" :style="{width: Math.abs(l.c) / maxCoef * 46 + '%'}"></i><b class="mono">{{ l.c > 0 ? '+' : '−' }}{{ Math.abs(l.c).toLocaleString('de-AT', {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</b></div>
        <p class="ch-coef-key"><span><i class="up"></i>spricht eher für den gemeldeten Hang</span><span><i class="down"></i>eher für die Nachbarn</span></p>
      </div>
    </figure>
  </section>

  <section class="ch wrap" aria-labelledby="ch4">
    <div class="ch-text">
      <p class="ch-no mono">Kapitel 4</p>
      <h2 id="ch4">Die Wetterfrage</h2>
      <p>Für jede Gruppe liegt der Regen der 60 Tage vor dem Stichtag vor, stündlich auf 1 km genau. Die naheliegende Frage: Verrät der Regen zusätzlich zum Gelände, welcher Hang rutscht?</p>
      <p>Die Antwort aus dem versiegelten Test: <strong>kein belegter Zusatznutzen.</strong> Benachbarte Hänge bekommen im 1-km-Raster fast denselben Regen; der Unterschied zwischen ihnen liegt im Gelände. Deshalb nutzt der Hang-Check kein Wetter.</p>
      <div v-if="weather?.verfuegbar" class="ch-weather">
        <p class="ch-w-num"><strong>{{ formatValue(weather.art, weather.wert) }}</strong> <span>{{ weather.label }} <InfoTip term="weatherDelta" :value="weather.wert" label=""/></span></p>
        <IntervalPlot :value="weather.wert" :interval="weather.intervall" :reference="0" reference-label="kein Unterschied" :min="plotScale(weather).min" :max="plotScale(weather).max" signed tone="grey" :label="weather.label"/>
        <p class="mono note">95-%-Intervall {{ iv(weather) }} · {{ weather.einheiten }} unabhängige Einheiten · <StatusChip status="versiegelt"/></p>
      </div>
    </div>
    <figure class="ch-graphic card">
      <template v-if="rain.days.length">
        <p class="mono ch-rain-head">Niederschlag am gemeldeten Hang, Tag für Tag vor dem Stichtag</p>
        <div class="ch-rain" role="img" :aria-label="`Tagesniederschlag der ${rain.days.length} Tage vor dem Stichtag, zusammen ${Math.round(rain.total)} mm`">
          <i v-for="d in rain.days" :key="d.date" :style="{height: Math.max(1, d.rain_mm / rain.max * 100) + '%'}" :title="`${d.date}: ${d.rain_mm.toFixed(1)} mm`"></i>
          <span class="ch-t0">Stichtag</span>
        </div>
        <div class="ch-rain-axis mono"><span>{{ rain.days[0].date }}</span><span>höchster Tag {{ rain.max.toLocaleString('de-AT', {maximumFractionDigits: 1}) }} mm</span><span>{{ rain.days.at(-1).date }}</span></div>
        <figcaption>Dieselbe Beispielgruppe wie in Kapitel 2 · GeoSphere INCA, 1 km</figcaption>
      </template>
      <div v-else class="skeleton" style="height:300px"></div>
    </figure>
  </section>

  <section class="ch-rules dark" aria-labelledby="ch-rules">
    <div class="wrap">
      <p class="eyebrow">Was den Vergleich fair hält</p>
      <h2 id="ch-rules">Vier Regeln, ohne die keine Zahl gilt.</h2>
      <ul class="rules">
        <li><strong>Nur Information vor dem Stichtag.</strong> Wetter, Schnee und Landbedeckung stammen aus der Zeit davor.</li>
        <li><strong>Gruppen bleiben zusammen.</strong> Ein Ereignis und seine Nachbarhänge liegen immer im selben Datenteil, zeitlich verbundene Ereignisse ebenfalls.</li>
        <li><strong>Ein versiegelter Test.</strong> Design und Modelle wurden vorab registriert; der Test wurde genau einmal ausgewertet.</li>
        <li><strong>Unsicherheit nach Episoden.</strong> Intervalle entstehen durch Wiederziehen ganzer Wetterepisoden, nicht einzelner Hänge.</li>
      </ul>
      <dl v-if="v04" class="flow">
        <div><dt>Kandidaten</dt><dd>{{ n(v04.counts.candidates) }}</dd></div>
        <div><dt>ausgeschlossen</dt><dd>{{ n(excluded) }}</dd></div>
        <div><dt>vollständige Gruppen</dt><dd>{{ n(v04.counts.complete_groups) }}</dd></div>
        <div><dt>Entwicklung</dt><dd>{{ n(part.development.events) }}<small> · {{ n(part.development.units) }} Einheiten</small></dd></div>
        <div><dt>versiegelter Test</dt><dd>{{ n(part.sealed_test.events) }}<small> · {{ n(part.sealed_test.units) }} Einheiten</small></dd></div>
      </dl>
    </div>
  </section>

  <section id="wirkungskette" class="ch-chain wrap" aria-labelledby="ch5">
    <div class="ch-chain-head">
      <p class="ch-no mono">Kapitel 5</p>
      <h2 id="ch5">Vom Hang zur Straße</h2>
      <p class="lead">An einem Demogebiet (Stanz, Juli 2016) geht die Kette weiter: vom auffälligen Hang über einen möglichen Fließweg bis zu Straßen und Gebäuden im Szenario. Prüfstufen und Fließweg bleiben bewusst getrennt.</p>
      <p class="ch-chain-tags"><StatusChip status="demonstration"/><span class="note">Fließwege sind unvalidierte Szenarien aus Literaturreichweiten; Straßen und Gebäude nach heutigem OpenStreetMap-Stand.</span></p>
    </div>
    <div class="legacy detail ch-chain-body"><WirkungsketteView/></div>
    <p><a class="link" href="#/studien#wirkungskette_v01">Wirkungskette v01 bis v03 im Studienatlas, mit Gegenprobe und Nullreferenz</a></p>
  </section>
</template>

<style>
.ch{display:grid;grid-template-columns:5fr 7fr;gap:clamp(28px,5vw,80px);align-items:start;padding-bottom:clamp(72px,10vw,140px)}
.ch-text{display:flex;flex-direction:column;gap:16px;padding-top:12px;min-height:min(70vh,640px)}
.ch-text p{color:var(--ink-2)}
.ch-text strong{color:var(--ink)}
.ch-no{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--moss)}
.ch-graphic{position:sticky;top:96px;margin:0;padding:16px;display:flex;flex-direction:column;gap:12px}
.ch-graphic figcaption{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.85rem;color:var(--ink-2)}
.ch-map{position:relative;aspect-ratio:16/10;border-radius:12px;overflow:hidden}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.d1{background:#3D5C38}.d2{background:#B0331D}.d3{background:#E9973A}
.ch-years{display:flex;flex-wrap:wrap;gap:6px}
.ch-years button{min-height:36px;min-width:44px;padding:0 10px;border-radius:999px;border:1px solid var(--line-2);background:var(--card);font:500 .85rem/1 var(--f-mono)}
.ch-years button[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
.ch-more summary{cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center}
.ch-table{border-collapse:collapse;width:100%;font-size:.92rem;margin:8px 0}
.ch-table th,.ch-table td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
.ch-notes{padding-left:1.1em;font-size:.9rem;color:var(--ink-2);display:grid;gap:6px}
.ch-terrain{position:relative;border-radius:12px;overflow:hidden;aspect-ratio:3/2;background:var(--paper-2)}
.ch-terrain img{width:100%;height:100%;object-fit:fill}
.ch-pt{position:absolute;transform:translate(-50%,-50%);width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:var(--card);border:2px solid var(--ink);font:650 12px/1 var(--f-mono);box-shadow:var(--shadow)}
.ch-pt.pos{background:var(--stufe1);border-color:#fff;color:#fff;width:30px;height:30px}
.ch-bars{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.ch-bar p{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-2);margin-bottom:6px}
.ch-bar-row{display:grid;grid-template-columns:62px 1fr auto;align-items:center;gap:6px;font-size:.78rem;color:var(--ink-2);margin-bottom:3px}
.ch-bar-row i{height:8px;border-radius:4px;background:var(--line-2)}
.ch-bar-row.pos i{background:var(--stufe1)}
.ch-bar-row.pos span{color:var(--ink);font-weight:600}
.ch-bar-row b{font-weight:500;font-size:.75rem}
.ch-layers-fig{gap:20px}
.ch-layers{position:relative;height:250px;perspective:900px}
.ly{position:absolute;left:12%;right:12%;height:130px;border-radius:12px;transform:rotateX(58deg) rotateZ(-28deg);box-shadow:0 18px 30px -18px rgb(19 32 43 / .5);display:flex;align-items:flex-end;padding:10px 14px;transition:transform .6s var(--ease)}
.ly-key{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.85rem;color:var(--ink-2)}
.ly-key i{display:inline-block;width:22px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.ly1{top:110px}
.ly1,.ly-key .ly1{background:linear-gradient(135deg,#8C9A8E,#5C6B60 40%,#A9B2A3)}
.ly2{top:60px}
.ly2,.ly-key .ly2{background:repeating-linear-gradient(45deg,#3D5C38 0 18px,#7E9B59 18px 34px,#C8C08A 34px 44px);opacity:.92}
.ly3{top:10px}
.ly3,.ly-key .ly3{background:repeating-linear-gradient(-30deg,#9C8F7A 0 26px,#B9AE94 26px 40px,#7C7769 40px 52px);opacity:.88}
.ch-layers-fig:hover .ly3{transform:rotateX(58deg) rotateZ(-28deg) translateY(-14px)}
.ch-coef p.mono{font-size:11px;letter-spacing:.06em;color:var(--ink-2);margin-bottom:8px}
.ch-coef-row{display:grid;grid-template-columns:minmax(120px,1.1fr) 1fr auto;align-items:center;gap:10px;padding:5px 0;font-size:.92rem;border-bottom:1px solid var(--line)}
.ch-coef-row i{height:10px;border-radius:5px}
.ch-coef-row b{font-size:.82rem;font-weight:500}
i.up{background:var(--stufe2)}i.down{background:var(--glacier)}
.ch-coef-key{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:.82rem;color:var(--ink-2)}
.ch-coef-key i{display:inline-block;width:14px;height:8px;border-radius:4px;margin-right:6px}
.ch-weather{margin-top:10px;padding:18px;border-radius:16px;background:var(--card);box-shadow:var(--shadow)}
.ch-w-num{display:flex;flex-direction:column;gap:4px}
.ch-w-num strong{font:650 2.4rem/1 var(--f-display);font-stretch:122%;color:var(--ink)}
.ch-w-num span{font-size:.9rem}
.ch-weather .note{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:8px;font-size:12px}
.ch-rain-head{font-size:11px;letter-spacing:.06em;color:var(--ink-2)}
.ch-rain{position:relative;height:260px;display:flex;align-items:flex-end;gap:2px;padding-right:4px;border-bottom:1px solid var(--line-2);border-right:2px dashed var(--ink)}
.ch-rain i{flex:1;background:var(--glacier);border-radius:2px 2px 0 0;min-width:2px}
.ch-t0{position:absolute;right:6px;top:0;font:500 11px/1 var(--f-mono);background:var(--card);padding:3px 5px;border-radius:4px}
.ch-rain-axis{display:flex;justify-content:space-between;gap:8px;font-size:11px;color:var(--ink-2)}
.ch-rules{padding:var(--section) 0;margin-bottom:var(--section)}
.ch-rules h2{color:#fff;max-width:18ch}
.rules{list-style:none;margin:36px 0 0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:0 48px}
.rules li{padding:20px 0;border-top:1px solid rgb(255 255 255 / .14);color:var(--on-dark-2)}
.rules strong{display:block;color:#fff;font:650 1.25rem/1.2 var(--f-display);font-stretch:112%;margin-bottom:6px}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:44px 0 0}
.flow div{padding:16px;border-radius:14px;background:var(--slate-700)}
.flow dt{font:500 11px/1.3 var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--on-dark-2)}
.flow dd{margin:8px 0 0;font:650 1.8rem/1 var(--f-display);font-stretch:118%;color:#fff}
.flow small{font:400 .8rem/1 var(--f-text);color:var(--on-dark-2)}
.ch-chain{padding-bottom:var(--section)}
.ch-chain-head{max-width:820px;margin-bottom:28px;display:grid;gap:14px}
.ch-chain-tags{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
.ch-chain-body{margin-bottom:20px}
@media (max-width:980px){
  .ch{grid-template-columns:1fr}
  .ch-text{min-height:0}
  .ch-graphic{position:relative;top:auto}
  .rules{grid-template-columns:1fr}
  .flow{grid-template-columns:1fr 1fr}
}
@media (max-width:560px){.ch-bars{grid-template-columns:1fr}}
</style>
