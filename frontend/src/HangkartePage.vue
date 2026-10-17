<script setup>
import {ref, computed, onMounted, onBeforeUnmount, watch} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {useResource} from './useResource.js'
import {CAVEATS, MIN_POINTS, MAX_POINTS, driverLabel, landCoverLabel, formatShare, pointProblem, shareColor} from './hangkarte.js'
maplibregl.setWorkerUrl(workerUrl)

const {data: meta, error: metaError} = useResource('/api/hangkarte/examples')
const container = ref(null)
const centre = ref(null), radius = ref(2000), mode = ref('auto'), points = ref([])
const result = ref(null), loading = ref(false), error = ref(''), hint = ref('')
const base = ref('ortho'), exaggeration = ref(1.5), showHeat = ref(true)
const wantRain = ref(false), rain = ref(null)
let map, ready = false, centreMarker, pointMarkers = [], groupMarkers = []

const canCompute = computed(() => centre.value && !loading.value && (mode.value === 'auto' || points.value.length >= MIN_POINTS))
const maxRadius = computed(() => meta.value?.area.radius_m.max ?? 3000)
const minRadius = computed(() => meta.value?.area.radius_m.min ?? 500)
const groupSize = computed(() => result.value?.group.length ?? 0)
const excluded = computed(() => Object.entries(result.value?.counts.excluded_by_reason ?? {}))
const reasonDe = {slope_below_minimum: 'Neigung unter 5° (außerhalb des Modellbereichs)', catchment_truncated: 'Einzugsgebiet am Rand abgeschnitten',
  no_land_cover: 'Landbedeckung nicht eindeutig', no_geology: 'Geologie nicht eindeutig', terrain_not_computable: 'Gelände nicht berechenbar',
  elevation_out_of_range: 'Höhe außerhalb des Modellbereichs', outside_austria: 'außerhalb Österreichs'}

function style() {
  const dem = {type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 14, encoding: 'terrarium'}
  return {version: 8, sources: {
    ortho: {type: 'raster', tiles: ['https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg'], tileSize: 256, maxzoom: 19,
      attribution: 'Orthofoto: basemap.at (CC BY 4.0)'},
    dem, hill: dem},
  layers: [{id: 'background', type: 'background', paint: {'background-color': '#eceee8'}},
    {id: 'ortho', type: 'raster', source: 'ortho'},
    {id: 'hillshade', type: 'hillshade', source: 'hill', paint: {'hillshade-exaggeration': .45, 'hillshade-shadow-color': '#1d2420', 'hillshade-highlight-color': '#ffffff', 'hillshade-accent-color': '#3a4a40'}}]}
}
function applyBase() {
  if (!ready) return
  map.setLayoutProperty('ortho', 'visibility', base.value === 'ortho' ? 'visible' : 'none')
  map.setPaintProperty('hillshade', 'hillshade-exaggeration', base.value === 'ortho' ? .35 : .9)
}
function applyTerrain() { if (ready) map.setTerrain({source: 'dem', exaggeration: Number(exaggeration.value)}) }

function marker(text, cls, color) {
  const el = document.createElement('div')
  el.className = cls; el.textContent = text
  if (color) el.style.setProperty('--c', color)
  return el
}
function clear(list) { list.forEach(m => m.remove()); list.length = 0 }
function drawCentre() {
  centreMarker?.remove()
  if (!centre.value) return
  centreMarker = new maplibregl.Marker({element: marker('◎', 'hk-centre')}).setLngLat([centre.value.longitude, centre.value.latitude]).addTo(map)
}
function drawPoints() {
  clear(pointMarkers)
  points.value.forEach((p, i) => pointMarkers.push(new maplibregl.Marker({element: marker(String(i + 1), 'hk-point')}).setLngLat([p.longitude, p.latitude]).addTo(map)))
}
function drawResult() {
  if (!ready) return
  clear(groupMarkers)
  const src = map.getSource('heat')
  if (!result.value) { src?.setData({type: 'FeatureCollection', features: []}); return }
  src.setData(result.value.heat)
  result.value.group.forEach((m, i) => {
    const el = marker(formatShare(m.share), 'hk-share', shareColor(m.share))
    el.title = `Hang ${i + 1}: ${formatShare(m.share)} des Vergleichs`
    groupMarkers.push(new maplibregl.Marker({element: el, anchor: 'bottom'}).setLngLat([m.longitude, m.latitude]).addTo(map))
  })
  map.setLayoutProperty('heat', 'visibility', showHeat.value ? 'visible' : 'none')
}
function fly(zoom = 13.6) {
  if (!centre.value) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  map.easeTo({center: [centre.value.longitude, centre.value.latitude], zoom, pitch: 62, bearing: -25, duration: reduce ? 0 : 1200})
}
function setCentre(c, zoom) {
  centre.value = c; result.value = null; points.value = []; rain.value = null; error.value = ''
  drawCentre(); drawPoints(); drawResult(); fly(zoom)
}
function pick(example) {
  radius.value = example.radius_m; mode.value = 'auto'
  setCentre({longitude: example.longitude, latitude: example.latitude})
  compute()
}
function onClick(e) {
  const p = {longitude: e.lngLat.lng, latitude: e.lngLat.lat}
  hint.value = ''
  if (mode.value === 'custom' && centre.value) {
    const problem = pointProblem(p, centre.value, radius.value, points.value)
    if (problem) { hint.value = problem; return }
    points.value = [...points.value, p]; result.value = null; drawPoints(); drawResult()
  } else {
    setCentre(p, Math.max(map.getZoom(), 12.5))
  }
}
function undoPoint() { points.value = points.value.slice(0, -1); result.value = null; drawPoints(); drawResult() }
function switchMode(m) { mode.value = m; result.value = null; hint.value = ''; if (m === 'auto') { points.value = []; drawPoints() }; drawResult() }

async function compute() {
  if (!centre.value) return
  loading.value = true; error.value = ''; result.value = null; drawResult()
  try {
    const body = {longitude: centre.value.longitude, latitude: centre.value.latitude, radius_m: Number(radius.value),
      points: mode.value === 'custom' ? points.value.map(p => [p.longitude, p.latitude]) : null}
    const r = await fetch('/api/hangkarte', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
    const json = await r.json()
    if (!r.ok) throw new Error(typeof json.detail === 'string' ? json.detail : 'Eingabe nicht gültig (Gebiet in Österreich wählen).')
    result.value = json; drawResult(); loadRain()
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
async function loadRain() {
  rain.value = null
  if (!wantRain.value || !centre.value) return
  try {
    const r = await fetch(`/api/hangkarte/rain?longitude=${centre.value.longitude}&latitude=${centre.value.latitude}`)
    rain.value = await r.json()
  } catch { rain.value = {available: false, reason: 'Anfrage fehlgeschlagen'} }
}
const rainMax = computed(() => Math.max(1, ...(rain.value?.days ?? []).map(d => d.rain_mm)))

onMounted(() => {
  map = new maplibregl.Map({container: container.value, style: style(), center: [13.3, 47.6], zoom: 6.4, pitch: 0, maxPitch: 82, attributionControl: false,
    locale: {'NavigationControl.ZoomIn': 'Vergrößern', 'NavigationControl.ZoomOut': 'Verkleinern', 'NavigationControl.ResetBearing': 'Norden', 'Map.Title': 'Karte'}})
  map.addControl(new maplibregl.NavigationControl({visualizePitch: true}), 'top-right')
  map.addControl(new maplibregl.ScaleControl({unit: 'metric'}), 'bottom-left')
  map.addControl(new maplibregl.AttributionControl({compact: true, customAttribution: 'Höhen: Mapzen/Skadi · Landbedeckung: CORINE · Geologie: GeoSphere Austria'}), 'bottom-right')
  map.on('load', () => {
    ready = true
    map.addSource('heat', {type: 'geojson', data: {type: 'FeatureCollection', features: []}})
    map.addLayer({id: 'heat', type: 'fill', source: 'heat', paint: {'fill-opacity': .55, 'fill-color': ['interpolate', ['linear'], ['get', 'percentile'],
      0, '#440154', 25, '#3b528b', 50, '#21908d', 75, '#5dc863', 100, '#fde725']}})
    applyBase(); applyTerrain()
  })
  map.on('click', onClick)
  map.on('error', () => { hint.value = 'Ein Teil der Kartenkacheln konnte nicht geladen werden (Internetverbindung?).' })
})
onBeforeUnmount(() => { clear(pointMarkers); clear(groupMarkers); centreMarker?.remove(); map?.remove() })
watch(base, applyBase); watch(exaggeration, applyTerrain); watch(showHeat, drawResult); watch(wantRain, loadRain)
</script>

<template>
  <section class="hk">
    <header class="hk-head">
      <p class="eyebrow">Anwendung · explorativ</p>
      <h1>Hangkarte</h1>
      <p class="hk-lead">Vergleicht Hänge in einem Gebiet allein anhand ihres Geländes und verteilt 100 % relativen Anteil auf die verglichenen Hänge.</p>
    </header>

    <aside class="hk-caveat" role="note" aria-label="Wichtige Einschränkungen">
      <strong>So ist diese Karte zu lesen</strong>
      <ul><li v-for="c in CAVEATS" :key="c">{{ c }}</li></ul>
    </aside>

    <div class="hk-grid">
      <div class="hk-panel">
        <h2>1 · Gebiet wählen</h2>
        <p class="hk-help">Karte anklicken (nur Österreich) oder ein Beispiel laden.</p>
        <div class="hk-examples" v-if="meta"><button v-for="e in meta.examples" :key="e.id" @click="pick(e)">{{ e.name }}</button></div>
        <p v-else-if="metaError" class="hk-warn" role="alert">{{ metaError }}</p>
        <label class="hk-field">Radius: <b>{{ Number(radius).toLocaleString('de-AT') }} m</b>
          <input type="range" :min="minRadius" :max="maxRadius" step="250" v-model="radius" @change="result=null; points=[]; drawPoints(); drawResult()"></label>

        <h2>2 · Vergleichsgruppe</h2>
        <div class="hk-seg" role="group" aria-label="Art der Vergleichsgruppe">
          <button :class="{on: mode==='auto'}" :aria-pressed="mode==='auto'" @click="switchMode('auto')">10 Hänge automatisch</button>
          <button :class="{on: mode==='custom'}" :aria-pressed="mode==='custom'" @click="switchMode('custom')">Eigene Punkte</button>
        </div>
        <p class="hk-help" v-if="mode==='auto'">Zehn über das Gebiet verteilte Hänge (mindestens 400 m Abstand, festgelegtes Zufallsverfahren, keine Auswahl nach Ergebnis).</p>
        <p class="hk-help" v-else>{{ MIN_POINTS }}–{{ MAX_POINTS }} Hänge im Gebiet anklicken: <b>{{ points.length }}</b> gewählt.
          <button class="hk-link" :disabled="!points.length" @click="undoPoint">letzten entfernen</button></p>
        <p v-if="hint" class="hk-warn" role="status">{{ hint }}</p>

        <button class="hk-go" :disabled="!canCompute" @click="compute">{{ loading ? 'Berechne … (erstes Mal bis ca. 20 s)' : 'Anteile berechnen' }}</button>
        <p v-if="error" class="hk-warn" role="alert">{{ error }}</p>

        <h2>Ansicht</h2>
        <div class="hk-seg" role="group" aria-label="Grundkarte">
          <button :class="{on: base==='ortho'}" :aria-pressed="base==='ortho'" @click="base='ortho'">Orthofoto</button>
          <button :class="{on: base==='relief'}" :aria-pressed="base==='relief'" @click="base='relief'">Reliefschummerung</button>
        </div>
        <label class="hk-field">Überhöhung: <b>{{ Number(exaggeration).toLocaleString('de-AT') }}×</b>
          <input type="range" min="1" max="3" step="0.25" v-model="exaggeration"></label>
        <label class="hk-check"><input type="checkbox" v-model="showHeat"> Farbebene aller bewertbaren Zellen</label>
        <label class="hk-check"><input type="checkbox" v-model="wantRain"> Zusatz: Niederschlag der letzten 7 Tage</label>
        <p class="hk-help">Mit gedrückter rechter Maustaste (oder Strg + Ziehen) neigen und drehen.</p>
      </div>

      <div class="hk-map-col">
        <div ref="container" class="hk-map" aria-label="3D-Geländekarte mit farbig markierten Hängen"></div>
        <div class="hk-legend" aria-hidden="true">
          <span>Farbebene: Rang im Gebiet</span><i class="bar"></i><span>niedriger</span><span class="r">höher</span>
        </div>
        <p v-if="loading" class="hk-busy" role="status">Gelände, Landbedeckung und Geologie werden berechnet …</p>
      </div>
    </div>

    <section v-if="result" class="hk-result" aria-live="polite">
      <h2>Relative Anteile in der Vergleichsgruppe <small>Summe {{ formatShare(result.group_share_sum) }} · {{ groupSize }} Hänge</small></h2>
      <p class="hk-note">{{ result.notice }}</p>
      <div class="table-scroll"><table class="hk-table">
        <caption>Die Anteile gelten nur innerhalb dieser Gruppe; ändert sich die Gruppe, ändern sich die Anteile.</caption>
        <thead><tr><th>Hang</th><th>Anteil</th><th>Höhe</th><th>Neigung</th><th>Landbedeckung</th><th>Stärkste Beiträge im Modell</th></tr></thead>
        <tbody><tr v-for="(m,i) in result.group" :key="i">
          <th><span class="hk-dot" :style="{background: shareColor(m.share)}"></span>{{ i+1 }}</th>
          <td><b>{{ formatShare(m.share) }}</b></td><td>{{ m.elevation_m }} m</td><td>{{ m.slope_deg.toLocaleString('de-AT') }}°</td>
          <td>{{ landCoverLabel(m.land_cover) }}</td>
          <td class="wrap"><span v-for="d in m.drivers" :key="d.feature" class="hk-drv">{{ d.contribution > 0 ? '▲' : '▼' }} {{ driverLabel(d.feature) }}</span></td>
        </tr></tbody>
      </table></div>
      <p class="hk-note">▲/▼: das Merkmal erhöht/senkt den Wert dieses Hangs relativ zum Modelldurchschnitt. Hoher Beitrag der Landbedeckung „Siedlung/Verkehr/sonstige“ oder „Grünland“ deutet auf mögliche Meldeeffekte, nicht auf Ursachen.</p>
      <p class="hk-note">{{ result.counts.eligible }} von {{ result.counts.grid_cells }} Rasterzellen (90 m) im Gebiet bewertbar;
        nicht bewertet: <span v-if="!excluded.length">keine</span><span v-for="([k,v],i) in excluded" :key="k">{{ i?'; ':'' }}{{ v }} × {{ reasonDe[k]||k }}</span>.
        Modell: V0.5, bedingte logistische Regression, nur Gelände/Landbedeckung/Geologie (22 Merkmale), unverändert übernommen. Landbedeckung: CORINE CLC2018.</p>
    </section>

    <section v-if="wantRain && rain" class="hk-rain">
      <h2>Zusatzebene: Niederschlag der letzten Tage <small>nicht im Modell, keine Bodenfeuchte</small></h2>
      <p v-if="rain.available===false" class="hk-warn">Nicht verfügbar: {{ rain.reason }}</p>
      <template v-else>
        <div class="hk-bars" role="img" :aria-label="`Tagesniederschlag der letzten ${rain.days.length} Tage, Summe ${rain.sum_mm} mm`">
          <div v-for="d in rain.days" :key="d.day_utc"><i :style="{height: (d.rain_mm/rainMax*70+2)+'px'}"></i><span>{{ d.rain_mm.toLocaleString('de-AT') }}</span><small>{{ d.day_utc.slice(5) }}</small></div>
        </div>
        <p class="hk-note">Summe {{ rain.sum_mm.toLocaleString('de-AT') }} mm in {{ rain.days.length }} UTC-Tagen (INCA, 1 km, am Gebietsmittelpunkt). {{ rain.note }}
          In V0.5 hat Wetter keinen belegten Zusatznutzen über das Gelände hinaus gebracht. Bodenfeuchte aus Satellitenradar (Sentinel-1) ist geplant, aber nicht umgesetzt.</p>
      </template>
    </section>
  </section>
</template>

<style scoped>
.hk{padding:48px 0 70px}.hk-head h1{font-size:clamp(44px,5vw,72px);letter-spacing:-3px;line-height:1.05;margin:0 0 14px;color:var(--blue)}.hk-lead{font-size:18px;line-height:1.55;max-width:720px;margin:0 0 24px}
.hk-caveat{border-left:3px solid var(--blue);background:#f7f7f8;padding:16px 20px;margin:0 0 28px;max-width:980px}.hk-caveat ul{margin:8px 0 0;padding-left:18px}.hk-caveat li{font-size:13px;line-height:1.6;margin-bottom:4px}
.hk-grid{display:grid;grid-template-columns:330px minmax(0,1fr);gap:28px;align-items:start}
.hk-panel h2{font-size:15px;letter-spacing:0;margin:22px 0 10px;font-weight:600}.hk-panel h2:first-child{margin-top:0}.hk-help{font-size:12px;color:var(--muted);line-height:1.6;margin:6px 0}
.hk-examples{display:flex;flex-direction:column;gap:6px;margin:8px 0 14px}.hk-examples button,.hk-seg button{background:#fff;border:1px solid #bcbcc4;padding:9px 12px;font-size:12px;text-align:left}.hk-examples button:hover{border-color:var(--blue);color:var(--blue)}
.hk-field{display:block;font-size:12px;margin:10px 0}.hk-field input[type=range]{width:100%;accent-color:var(--blue);display:block;margin-top:6px}.hk-check{display:flex;gap:8px;font-size:12px;margin:8px 0;align-items:center}
.hk-seg{display:flex;border:1px solid #bcbcc4}.hk-seg button{flex:1;border:0;border-right:1px solid #bcbcc4;text-align:center}.hk-seg button:last-child{border-right:0}.hk-seg button.on{background:var(--blue);color:#fff}
.hk-go{margin-top:14px;width:100%;background:var(--blue);color:#fff;border:1px solid var(--blue);padding:13px;font-size:13px}.hk-go:disabled{background:#c9c9cf;border-color:#c9c9cf;cursor:not-allowed;opacity:1}
.hk-link{background:none;border:0;color:var(--blue);text-decoration:underline;font-size:12px;padding:0 0 0 6px}.hk-warn{font-size:12px;color:#8a1f11;background:#fdf1ef;padding:9px 11px;margin:8px 0;line-height:1.5}
.hk-map-col{position:relative;min-width:0}.hk-map{height:min(72vh,680px);min-height:420px;border:1px solid var(--line);background:#eceee8}.hk-busy{position:absolute;top:12px;left:12px;background:#fff;padding:9px 12px;font-size:12px;margin:0;border:1px solid var(--line)}
.hk-legend{position:absolute;left:12px;bottom:34px;background:#fffffff0;border:1px solid var(--line);padding:8px 10px;font-size:10px;display:grid;grid-template-columns:auto auto;gap:3px 10px;pointer-events:none;max-width:210px}.hk-legend span:first-child{grid-column:1/-1;font-weight:600}.hk-legend .bar{grid-column:1/-1;height:8px;background:linear-gradient(90deg,#440154,#3b528b,#21908d,#5dc863,#fde725)}.hk-legend .r{text-align:right}
.hk-result,.hk-rain{margin-top:36px;border-top:1px solid var(--line);padding-top:26px}.hk-result h2,.hk-rain h2{font-size:24px;letter-spacing:-.6px;margin:0 0 12px}.hk-result h2 small,.hk-rain h2 small{display:block;font-size:12px;letter-spacing:0;color:var(--muted);font-weight:400;margin-top:6px}
.hk-table th,.hk-table td{padding:10px 14px}.hk-table td.wrap{white-space:normal;min-width:260px}.hk-dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:8px;border:1px solid #20202540}.hk-drv{display:block;font-size:11px;color:var(--muted);line-height:1.5}.hk-note{font-size:12px;color:var(--muted);line-height:1.7;max-width:980px;margin:14px 0 0}
.hk-bars{display:flex;gap:10px;align-items:flex-end;margin:16px 0;height:112px}.hk-bars>div{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:3px;width:52px}.hk-bars i{display:block;width:100%;background:var(--blue);opacity:.75}.hk-bars span{font-size:11px}.hk-bars small{font-size:10px;color:var(--muted)}
@media(max-width:900px){.hk-grid{grid-template-columns:1fr}.hk-map{height:62vh}}
</style>
<style>
.hk-centre{font-size:26px;line-height:1;color:#fff;text-shadow:0 0 4px #000,0 0 2px #000;pointer-events:none}
.hk-point{width:26px;height:26px;border-radius:50%;background:#fff;color:#202025;border:2px solid #002fa7;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 5px #0006}
.hk-share{background:var(--c,#fff);color:#fff;font-size:12px;font-weight:700;padding:3px 8px;border-radius:12px;border:2px solid #fff;text-shadow:0 0 3px #000,0 0 2px #000;box-shadow:0 1px 5px #0007;white-space:nowrap}
</style>
