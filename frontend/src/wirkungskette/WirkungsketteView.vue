<script setup>
import {ref, computed, watch, onMounted, onBeforeUnmount, shallowRef} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import ProfileChart from './ProfileChart.vue'
import {RADIUS, LAYER_KIND, CLASS_COLORS, NOT_ASSESSED_COLOR, INFRA, STATUS_SHORT, REASON_TEXT,
  count, percent, meters, clampRadius, scenarioBand, infraBand, rangeText} from './chain.js'

maplibregl.setWorkerUrl(workerUrl)
const API = '/api/wirkungskette'
const radiusInput = ref(RADIUS.initial)          // slider position (live label)
const radius = ref(RADIUS.initial)               // committed radius (request)
const mode = ref('pruefpunkte')
const anriss = ref(null)
const scenario = ref('reach_467m')
const data = shallowRef(null), error = ref(''), loading = ref(true)
const show = ref({pruefstufen: true, relief: true, hoehenlinien: false, kontext: true, ereignisse: false})
const mapBox = ref(null), mapNote = ref('')

const chain = computed(() => data.value?.auswahl || null)
const selectedScenario = computed(() => chain.value?.szenarien.find(s => s.id === scenario.value) || chain.value?.szenarien[0])
const band = computed(() => scenarioBand(chain.value?.szenarien))
const infra = computed(() => infraBand(chain.value?.szenarien))
const hits = computed(() => (chain.value?.treffer || []).filter(t => t.szenarien.includes(selectedScenario.value?.id)))
const hitRows = computed(() => hits.value.slice().sort((a, b) => INFRA.findIndex(i => i.key === a.typ) - INFRA.findIndex(i => i.key === b.typ)))
const showAllHits = ref(false)
const classes = computed(() => data.value?.pruefstufen.stufen || [])
const assessedShare = computed(() => {
  const p = data.value?.pruefstufen
  return p ? p.zellen_bewertbar / p.zellen_gesamt : null
})
const expl = computed(() => data.value?.explorativ_dokumentierte_ereignisse)

let controller, fitNext = 'radius'
async function load() {
  controller?.abort()
  controller = new AbortController()
  loading.value = true; error.value = ''
  const q = new URLSearchParams({radius_m: radius.value, modus: mode.value})
  if (anriss.value) q.set('anriss', anriss.value)
  try {
    const r = await fetch(`${API}?${q}`, {signal: controller.signal})
    if (r.status === 503) throw new Error('Das Demogebiet ist auf diesem Rechner noch nicht vorbereitet (python -m preslide.wirkungskette build).')
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Die Szenarien konnten nicht berechnet werden (HTTP ${r.status}).`)
    data.value = await r.json()
    anriss.value = data.value.auswahl.anriss.id
    const fit = fitNext
    fitNext = 'selection'
    if (!data.value.auswahl.szenarien.some(s => s.id === scenario.value)) scenario.value = data.value.auswahl.szenarien[0].id
    draw()
    setTimeout(() => { if (fit === 'radius') fitRadius(); else fitSelection() }, 0)
  } catch (e) {
    if (e.name !== 'AbortError') { error.value = e.message; data.value = null }
  } finally { loading.value = false }
}
function commitRadius() { radius.value = clampRadius(radiusInput.value); radiusInput.value = radius.value }
watch(radius, () => { anriss.value = null; fitNext = 'radius'; load(); refreshRaster(); refreshContext() })
watch(mode, () => { anriss.value = null; fitNext = 'radius'; load() })
function chooseRelease(id) { if (id !== anriss.value) { anriss.value = id; load() } }

// ---------- map ----------
let map, ready = false, disposed = false, reliefMeta = null, contoursLoaded = false
const empty = {type: 'FeatureCollection', features: []}

function circleRing(lon, lat, r) {   // geodesic small circle (spherical earth), display only
  const R = 6371008.8, d = r / R, la = lat * Math.PI / 180, lo = lon * Math.PI / 180, out = []
  for (let i = 0; i <= 96; i++) {
    const b = i / 96 * 2 * Math.PI
    const la2 = Math.asin(Math.sin(la) * Math.cos(d) + Math.cos(la) * Math.sin(d) * Math.cos(b))
    const lo2 = lo + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(la), Math.cos(d) - Math.sin(la) * Math.sin(la2))
    out.push([lo2 * 180 / Math.PI, la2 * 180 / Math.PI])
  }
  return out
}
function centre() { return data.value?.demo.zentrum || [15.49683, 47.44533] }
function fitRadius() {
  if (!map) return
  const ring = circleRing(...centre(), radius.value), b = new maplibregl.LngLatBounds()
  ring.forEach(p => b.extend(p))
  map.fitBounds(b, {padding: 24, duration: 0})
}
function fitSelection() {
  const c = data.value?.auswahl
  if (!map || !c) return
  const longest = c.szenarien.reduce((a, b) => (b.laenge_m > a.laenge_m ? b : a))
  const b = new maplibregl.LngLatBounds()
  b.extend(c.anriss.lage)
  longest.korridor.coordinates[0].forEach(p => b.extend(p))
  map.fitBounds(b, {padding: 70, maxZoom: 15.5, duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 600})
}
function setData(id, value) { map.getSource(id)?.setData(value) }
function fc(features) { return {type: 'FeatureCollection', features} }
function pt(c, props = {}) { return {type: 'Feature', properties: props, geometry: {type: 'Point', coordinates: c}} }

async function refreshRaster() {
  if (!ready) return
  try {
    const r = await fetch(`${API}/pruefstufen?radius_m=${radius.value}`)
    if (!r.ok) return
    const {ecken} = await r.json()
    const url = `${API}/pruefstufen.png?radius_m=${radius.value}`
    const src = map.getSource('pruefstufen')
    if (src) src.updateImage({url, coordinates: ecken})
    else map.addSource('pruefstufen', {type: 'image', url, coordinates: ecken})
    if (!map.getLayer('pruefstufen')) map.addLayer({id: 'pruefstufen', type: 'raster', source: 'pruefstufen', paint: {'raster-opacity': ['interpolate', ['linear'], ['zoom'], 12, .78, 15, .38], 'raster-resampling': 'nearest', 'raster-fade-duration': 0}}, 'kontext-strasse')
    applyVisibility()
  } catch { mapNote.value = 'Die Prüfstufen-Ebene konnte nicht geladen werden.' }
}
async function refreshContext() {
  if (!ready) return
  try {
    const r = await fetch(`${API}/kontext?radius_m=${radius.value}`)
    if (r.ok) setData('kontext', await r.json())
  } catch { mapNote.value = 'Die Infrastruktur-Grundlage konnte nicht geladen werden.' }
}
async function loadContours() {
  if (contoursLoaded || !ready) return
  contoursLoaded = true
  try {
    const r = await fetch(`${API}/hoehenlinien`)
    if (r.ok) setData('hoehenlinien', await r.json())
    else contoursLoaded = false
  } catch { contoursLoaded = false }
}

function draw() {
  if (!ready || !data.value) return
  const d = data.value, c = d.auswahl
  setData('radius', fc([{type: 'Feature', properties: {}, geometry: {type: 'LineString', coordinates: circleRing(...centre(), d.umkreis_m)}}]))
  setData('anrisse', fc(d.anrisspunkte.map((a, i) => pt(a.anriss.lage, {id: a.anriss.id, label: a.anriss.art === 'Prüfpunkt' ? a.anriss.id : '', sel: a.anriss.id === c.anriss.id ? 1 : 0, art: a.anriss.art === 'Prüfpunkt' ? 'p' : 'h', i}))))
  setData('route', fc([{type: 'Feature', properties: {}, geometry: {type: 'LineString', coordinates: c.route.koordinaten}}]))
  const order = c.szenarien.slice().sort((a, b) => b.laenge_m - a.laenge_m)
  setData('korridore', fc(order.map(s => ({type: 'Feature', properties: {id: s.id, sel: s.id === scenario.value ? 1 : 0}, geometry: s.korridor}))))
  const stops = c.szenarien.map(s => pt(s.stopp_lage, {id: s.id, label: s.bezeichnung, sel: s.id === scenario.value ? 1 : 0}))
  setData('stopps', fc(stops))
  setData('treffer', fc(c.treffer.map(t => pt(t.lage, {typ: t.typ, inside: t.szenarien.includes(scenario.value) ? 1 : 0}))))
  setData('ereignisse', fc((d.explorativ_dokumentierte_ereignisse.punkte || []).map(p => pt(p.lage, {h: p.prozess === 'Hangmure' ? 1 : 0}))))
}
watch(scenario, draw)

function applyVisibility() {
  if (!ready) return
  const vis = (ids, on) => ids.forEach(id => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'))
  vis(['pruefstufen'], show.value.pruefstufen)
  vis(['relief'], show.value.relief)
  vis(['hoehenlinien', 'hoehenlinien-haupt'], show.value.hoehenlinien)
  vis(['kontext-strasse', 'kontext-bahn', 'kontext-gebaeude'], show.value.kontext)
  vis(['ereignisse'], show.value.ereignisse)
  if (show.value.hoehenlinien) loadContours()
}
watch(show, applyVisibility, {deep: true})

async function initMap() {
  const r = await fetch(`${API}/relief`).catch(() => null)
  reliefMeta = r && r.ok ? await r.json() : null
  if (disposed) return
  map = new maplibregl.Map({
    container: mapBox.value, center: centre(), zoom: 12, minZoom: 10, maxZoom: 17, attributionControl: false,
    dragRotate: false, pitchWithRotate: false, cooperativeGestures: false,
    locale: {'NavigationControl.ZoomIn': 'Vergrößern', 'NavigationControl.ZoomOut': 'Verkleinern'},
    style: {version: 8, sources: {}, layers: [{id: 'bg', type: 'background', paint: {'background-color': '#f3f3f1'}}]},
  })
  map.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right')
  map.addControl(new maplibregl.ScaleControl({unit: 'metric'}), 'bottom-left')
  map.addControl(new maplibregl.AttributionControl({compact: true, customAttribution: 'Gelände: Mapzen/AWS Skadi (u. a. österr. DGM, EU-DEM) · Infrastruktur © OpenStreetMap-Mitwirkende (ODbL)'}), 'bottom-right')
  map.on('error', e => { if (!mapNote.value) mapNote.value = 'Eine Kartenebene konnte nicht geladen werden; die Tabellen bleiben gültig.'; console.warn(e?.error) })
  map.on('load', () => {
    if (reliefMeta) {
      map.addSource('relief', {type: 'image', url: `${API}/relief.png`, coordinates: reliefMeta.corners})
      map.addLayer({id: 'relief', type: 'raster', source: 'relief', paint: {'raster-opacity': .55, 'raster-contrast': .15, 'raster-fade-duration': 0}})
    } else mapNote.value = 'Das Geländerelief ist nicht verfügbar.'
    for (const id of ['hoehenlinien', 'kontext', 'radius', 'korridore', 'route', 'stopps', 'treffer', 'ereignisse', 'anrisse']) map.addSource(id, {type: 'geojson', data: empty})
    map.addLayer({id: 'hoehenlinien', type: 'line', source: 'hoehenlinien', filter: ['!', ['get', 'haupt']], paint: {'line-color': '#8d8a80', 'line-width': .5, 'line-opacity': .55}})
    map.addLayer({id: 'hoehenlinien-haupt', type: 'line', source: 'hoehenlinien', filter: ['get', 'haupt'], paint: {'line-color': '#7a776d', 'line-width': 1, 'line-opacity': .7}})
    map.addLayer({id: 'kontext-strasse', type: 'line', source: 'kontext', filter: ['==', ['get', 'typ'], 'strasse'], paint: {'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, .8, 15, 3], 'line-opacity': .9}})
    map.addLayer({id: 'kontext-bahn', type: 'line', source: 'kontext', filter: ['==', ['get', 'typ'], 'bahn'], paint: {'line-color': '#4a4a52', 'line-width': 1.4, 'line-dasharray': [3, 2]}})
    map.addLayer({id: 'kontext-gebaeude', type: 'circle', source: 'kontext', minzoom: 12.5, filter: ['==', ['get', 'typ'], 'gebaeude'], paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 12.5, 1, 16, 3.5], 'circle-color': '#5d5d66', 'circle-opacity': .7}})
    map.addLayer({id: 'radius', type: 'line', source: 'radius', paint: {'line-color': '#202025', 'line-width': 1, 'line-dasharray': [4, 3]}})
    map.addLayer({id: 'korridore', type: 'fill', source: 'korridore', paint: {'fill-color': '#002fa7', 'fill-opacity': ['case', ['==', ['get', 'sel'], 1], .32, .10]}})
    map.addLayer({id: 'korridore-linie', type: 'line', source: 'korridore', filter: ['==', ['get', 'sel'], 1], paint: {'line-color': '#002fa7', 'line-width': 1.6}})
    map.addLayer({id: 'route', type: 'line', source: 'route', paint: {'line-color': '#202025', 'line-width': 1.6, 'line-dasharray': [2, 1.5]}})
    map.addLayer({id: 'ereignisse', type: 'circle', source: 'ereignisse', paint: {'circle-radius': 3.2, 'circle-color': ['case', ['==', ['get', 'h'], 1], '#202025', '#ffffff'], 'circle-stroke-color': '#202025', 'circle-stroke-width': 1}})
    map.addLayer({id: 'treffer', type: 'circle', source: 'treffer', filter: ['==', ['get', 'inside'], 1], paint: {'circle-radius': ['match', ['get', 'typ'], 'gebaeude', 5, 4], 'circle-color': ['match', ['get', 'typ'], 'gebaeude', '#202025', 'bahn', '#4a4a52', '#ffffff'], 'circle-stroke-color': ['match', ['get', 'typ'], 'gebaeude', '#ffffff', '#202025'], 'circle-stroke-width': 1.6}})
    map.addLayer({id: 'stopps', type: 'circle', source: 'stopps', paint: {'circle-radius': ['case', ['==', ['get', 'sel'], 1], 6, 4], 'circle-color': ['case', ['==', ['get', 'sel'], 1], '#002fa7', '#ffffff'], 'circle-stroke-color': '#002fa7', 'circle-stroke-width': 2}})
    map.addLayer({id: 'anrisse', type: 'circle', source: 'anrisse', paint: {'circle-radius': ['case', ['==', ['get', 'sel'], 1], 9, ['==', ['get', 'art'], 'p'], 6.5, 4.5], 'circle-color': ['case', ['==', ['get', 'art'], 'p'], CLASS_COLORS[1], '#202025'], 'circle-stroke-color': '#ffffff', 'circle-stroke-width': ['case', ['==', ['get', 'sel'], 1], 3, 1.5]}})
    map.on('click', 'anrisse', e => { const id = e.features?.[0]?.properties?.id; if (id) chooseRelease(id) })
    map.on('mouseenter', 'anrisse', () => { map.getCanvas().style.cursor = 'pointer' })
    map.on('mouseleave', 'anrisse', () => { map.getCanvas().style.cursor = '' })
    map.getContainer().querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
    ready = true
    refreshRaster(); refreshContext(); draw(); fitRadius(); applyVisibility()
  })
}
onMounted(() => { load(); initMap() })
onBeforeUnmount(() => { disposed = true; controller?.abort(); map?.remove() })

const releaseOptions = computed(() => data.value?.anrisspunkte || [])
function statusClass(s) { return s === 'gestoppt' ? 'ok' : 'open' }
</script>

<template>
  <section class="wk" aria-labelledby="wk-title">
    <header class="wk-head">
      <p class="wk-kicker">Demogebiet · {{ data?.demo.name || 'Stanz im Mürztal' }} · Stichtag 25.07.2016</p>
      <h2 id="wk-title">Wirkungskette: Prüfpunkt, Auslauf, Infrastruktur</h2>
      <p class="wk-lead">Wo lohnt ein genauer Blick auf den Hang, wohin könnte Material von dort abfließen, und welche Gebäude, Straßen und Bahnstrecken liegen auf diesem Weg? Jede Ebene sagt, welche Art von Aussage sie macht.</p>
      <p class="wk-seal">{{ data?.demo.kennzeichnung || 'Versiegeltes, bereits einmal ausgewertetes V0.4-Testereignis; hier nur Demonstration.' }}</p>
    </header>

    <!-- Signature: the chain itself, filled with the live numbers of the current selection -->
    <ol class="wk-chain" aria-label="Wirkungskette der aktuellen Auswahl" :aria-busy="loading">
      <li>
        <span class="wk-tag" data-kind="Befund">Befund</span>
        <h3>Prüfpunkt</h3>
        <p v-if="chain" class="wk-chain-main">{{ chain.anriss.bezeichnung }}</p>
        <p v-if="chain" class="wk-chain-sub">{{ chain.anriss.art === 'Prüfpunkt' ? `Rangfolge im Umkreis von ${meters(data.umkreis_m)}` : 'Inventarpunkt als Anriss angenommen' }} · {{ count(chain.anriss.neigung_grad) }}° · {{ chain.anriss.landbedeckung }}</p>
      </li>
      <li>
        <span class="wk-tag" data-kind="Szenario">Szenario</span>
        <h3>Möglicher Auslauf</h3>
        <p v-if="band" class="wk-chain-main">{{ meters(band.min) }} bis {{ meters(band.max) }}</p>
        <p v-if="chain" class="wk-chain-sub">entlang der Abwärtsroute · vier Literaturannahmen · nicht geprüft</p>
      </li>
      <li>
        <span class="wk-tag" data-kind="Szenario">Szenario</span>
        <h3>Liegt im Auslaufszenario</h3>
        <p v-if="chain" class="wk-chain-main">{{ rangeText(infra.gebaeude) }} Gebäude · {{ rangeText(infra.strasse) }} Straßen · {{ rangeText(infra.bahn) }} Bahn</p>
        <p v-if="chain" class="wk-chain-sub">Spanne über die vier Szenarien · räumliche Überlagerung, keine Schadensaussage</p>
      </li>
    </ol>

    <div class="wk-controls">
      <div class="wk-control wk-radius">
        <label for="wk-radius">Umkreis <output for="wk-radius">{{ meters(radiusInput) }}</output></label>
        <input id="wk-radius" type="range" :min="RADIUS.min" :max="RADIUS.max" :step="RADIUS.step" v-model.number="radiusInput"
               @change="commitRadius" @keyup.enter="commitRadius" aria-describedby="wk-radius-why">
        <small id="wk-radius-why">1 bis 10 km: Die Kontrollhänge des Modells lagen 750 m bis 10 km vom Ereignis entfernt. Weiter hat das Modell nie verglichen.</small>
      </div>
      <fieldset class="wk-control">
        <legend>Anrisspunkte</legend>
        <div class="wk-seg" role="radiogroup">
          <label :class="{on: mode === 'pruefpunkte'}"><input type="radio" value="pruefpunkte" v-model="mode"> Oberste Prüfpunkte</label>
          <label :class="{on: mode === 'hangmuren'}"><input type="radio" value="hangmuren" v-model="mode"> Dokumentierte Hangmuren</label>
        </div>
      </fieldset>
      <div class="wk-control">
        <label for="wk-anriss">Anrisspunkt</label>
        <select id="wk-anriss" :value="anriss" @change="chooseRelease($event.target.value)" :disabled="!releaseOptions.length">
          <option v-for="a in releaseOptions" :key="a.anriss.id" :value="a.anriss.id">{{ a.anriss.bezeichnung }}</option>
        </select>
      </div>
    </div>

    <div class="wk-stage">
      <div class="wk-mapcol">
        <fieldset class="wk-layers">
          <legend class="sr-only">Kartenebenen</legend>
          <label><input type="checkbox" v-model="show.pruefstufen"> Prüfstufen <span class="wk-tag" data-kind="Befund">Befund</span></label>
          <label><input type="checkbox" v-model="show.ereignisse"> Dokumentierte Ereignisse <span class="wk-tag" data-kind="Befund">Befund</span></label>
          <label><input type="checkbox" v-model="show.kontext"> Straßen, Bahn, Gebäude</label>
          <label><input type="checkbox" v-model="show.relief"> Relief <span class="wk-tag" data-kind="Illustration">Illustration</span></label>
          <label><input type="checkbox" v-model="show.hoehenlinien"> Höhenlinien <span class="wk-tag" data-kind="Illustration">Illustration</span></label>
        </fieldset>
        <div class="wk-mapwrap">
          <div ref="mapBox" class="wk-map" role="region" aria-label="Karte des Demogebiets mit Prüfstufen, Abwärtsroute, Auslaufkorridoren und Infrastruktur"></div>
          <p v-if="loading" class="wk-busy" role="status">Szenarien werden berechnet …</p>
          <div class="wk-mapbtns"><button type="button" @click="fitSelection" :disabled="!chain">Zum Anrisspunkt</button><button type="button" @click="fitRadius">Ganzen Umkreis zeigen</button></div>
          <div class="wk-legend" aria-hidden="true">
            <div class="wk-legend-row"><span v-for="c in classes" :key="c.id" class="wk-sw" :style="{background: CLASS_COLORS[c.id]}"></span><span class="wk-sw" :style="{background: NOT_ASSESSED_COLOR, opacity: .45}"></span></div>
            <div class="wk-legend-row wk-legend-text"><span>Stufe 1</span><span>4</span><span>nicht bewertet</span></div>
            <div class="wk-legend-row"><i class="wk-k-route"></i>Route <i class="wk-k-corr"></i>Korridor <i class="wk-k-hit"></i>Treffer</div>
          </div>
        </div>
        <p v-if="mapNote" class="wk-warn" role="alert">{{ mapNote }}</p>
      </div>

      <aside class="wk-panel" aria-live="polite">
        <p v-if="error" class="wk-warn" role="alert">{{ error }} <button type="button" @click="load">Erneut berechnen</button></p>
        <template v-else-if="chain">
          <p class="wk-panel-kicker">{{ chain.anriss.art }}<template v-if="chain.anriss.klasse"> · Prüfstufe {{ chain.anriss.klasse }}</template></p>
          <h3 class="wk-panel-title">{{ chain.anriss.bezeichnung }}</h3>
          <dl class="wk-facts">
            <div><dt>Höhe</dt><dd>{{ count(chain.anriss.hoehe_m) }} m</dd></div>
            <div><dt>Neigung</dt><dd>{{ count(chain.anriss.neigung_grad) }}°</dd></div>
            <div><dt>Route</dt><dd>{{ meters(chain.route.laenge_m) }}</dd></div>
          </dl>
          <div v-if="chain.anriss.treiber?.length" class="wk-drivers">
            <p>Am stärksten am Rang beteiligt <small>(Beitrag im Modell, keine Ursache)</small></p>
            <ul><li v-for="t in chain.anriss.treiber" :key="t.merkmal"><span>{{ t.merkmal }}</span><b :class="t.beitrag > 0 ? 'up' : 'down'">{{ t.richtung }}</b></li></ul>
          </div>
          <p v-if="chain.anriss.einzugsgebiet_unvollstaendig" class="wk-warn">Das Einzugsgebiet dieses Punkts reicht über das Rechengebiet hinaus.</p>
          <p class="wk-route-end"><b>Routenende:</b> {{ chain.route.ende_text }}<template v-if="chain.route.senken_zellen">; {{ count(chain.route.senken_zellen) }} Zellen durch rechnerisch gefüllte Senken</template>.</p>

          <div class="wk-scen" role="radiogroup" aria-label="Szenario für Karte und Trefferliste">
            <label v-for="s in chain.szenarien" :key="s.id" class="wk-scen-row" :class="{on: scenario === s.id}">
              <input type="radio" :value="s.id" v-model="scenario">
              <span class="wk-scen-name">{{ s.bezeichnung }}</span>
              <span class="wk-scen-len">{{ meters(s.laenge_m) }}</span>
              <span class="wk-scen-status" :class="statusClass(s.status)">{{ STATUS_SHORT[s.status] }}</span>
              <span class="wk-scen-infra">{{ count(s.infrastruktur.gebaeude.anzahl) }} Geb. · {{ count(s.infrastruktur.strasse.anzahl) }} Str. · {{ count(s.infrastruktur.bahn.anzahl) }} Bahn</span>
            </label>
          </div>
          <p v-if="selectedScenario" class="wk-source">{{ selectedScenario.quelle }}</p>
        </template>
        <p v-else-if="loading" class="wk-note">Szenarien werden berechnet …</p>
      </aside>
    </div>

    <ProfileChart v-if="chain" :chain="chain" :selected="scenario" @select="id => scenario = id" />

    <div v-if="chain" class="wk-hits">
      <h3>Im Szenario „{{ selectedScenario?.bezeichnung }}“ liegen</h3>
      <p class="wk-note">{{ data.korridor }}. „Liegt im Auslaufszenario“ heißt nur räumliche Überlagerung, keine Aussage über Schaden. Gebäude- und Straßenstand: OpenStreetMap heute, nicht 2016.</p>
      <dl class="wk-hit-counts">
        <div v-for="i in INFRA" :key="i.key"><dt>{{ i.label }}</dt><dd>{{ count(selectedScenario.infrastruktur[i.key].anzahl) }}</dd>
          <small v-if="i.key !== 'gebaeude' && selectedScenario.infrastruktur[i.key].laenge_m">{{ meters(selectedScenario.infrastruktur[i.key].laenge_m) }} im Korridor</small></div>
      </dl>
      <div v-if="hitRows.length" class="wk-table-wrap">
        <table class="wk-table">
          <thead><tr><th scope="col">Art</th><th scope="col">Name</th><th scope="col">OSM-Klasse</th><th scope="col">Länge im Korridor</th></tr></thead>
          <tbody>
            <tr v-for="t in (showAllHits ? hitRows : hitRows.slice(0, 12))" :key="t.typ + t.osm_id">
              <td>{{ INFRA.find(i => i.key === t.typ)?.label }}</td><td>{{ t.name || '–' }}</td><td>{{ t.klasse === 'yes' ? 'ohne Angabe' : t.klasse }}</td>
              <td>{{ t.typ === 'gebaeude' ? '–' : meters(t.laenge_im_korridor_m) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <button v-if="hitRows.length > 12" type="button" class="wk-more" @click="showAllHits = !showAllHits">{{ showAllHits ? 'Weniger zeigen' : `Alle ${count(hitRows.length)} Einträge zeigen` }}</button>
      <p v-if="!hitRows.length" class="wk-note">In diesem Szenario liegt keine kartierte Infrastruktur im Korridor. Das heißt nicht, dass der Bereich unbedenklich ist.</p>
    </div>

    <div v-if="data" class="wk-lower">
      <section class="wk-expl" aria-labelledby="wk-expl-h">
        <span class="wk-tag" data-kind="Befund">Befund · explorativ</span>
        <h3 id="wk-expl-h">Wo liegen die dokumentierten Ereignisse in den Prüfstufen?</h3>
        <p class="wk-note">{{ count(expl.bewertbar) }} von {{ count(expl.gesamt) }} Ereignissen des 25.07.2016 sind bewertbar. Wären die Stufen hilfreich, lägen die Ereignisse häufiger in Stufe 1 als die Fläche. Gesehene Daten, nur beschreibend, keine Trefferquote.</p>
        <table class="wk-share">
          <thead><tr><th scope="col">Stufe</th><th scope="col">Fläche</th><th scope="col">alle Ereignisse</th><th scope="col">Hangmuren</th></tr></thead>
          <tbody>
            <tr v-for="c in classes" :key="c.id">
              <th scope="row"><span class="wk-sw" :style="{background: CLASS_COLORS[c.id]}"></span>{{ c.id }}</th>
              <td><span class="wk-bar" :style="{width: (expl.flaechenanteil_je_stufe[c.id] * 100) + '%'}"></span>{{ percent(expl.flaechenanteil_je_stufe[c.id]) }}</td>
              <td><span class="wk-bar ev" :style="{width: (expl.gruppen.alle.anteil_je_stufe[c.id] * 100) + '%'}"></span>{{ percent(expl.gruppen.alle.anteil_je_stufe[c.id]) }}</td>
              <td><span class="wk-bar ev" :style="{width: (expl.gruppen.hangmuren.anteil_je_stufe[c.id] * 100) + '%'}"></span>{{ percent(expl.gruppen.hangmuren.anteil_je_stufe[c.id]) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="wk-finding">Im Demogebiet konzentriert die Stufe 1 die dokumentierten Ereignisse nicht: {{ percent(expl.gruppen.alle.anteil_je_stufe[1]) }} der Ereignisse und {{ percent(expl.gruppen.hangmuren.anteil_je_stufe[1]) }} der Hangmuren liegen dort, bei {{ percent(expl.flaechenanteil_je_stufe[1]) }} der Fläche.</p>
      </section>

      <section class="wk-limits" aria-labelledby="wk-lim-h">
        <h3 id="wk-lim-h">Was diese Ansicht nicht leistet</h3>
        <ul>
          <li v-for="s in data.pruefstufen.schwaechen" :key="s">{{ s }}</li>
          <li>Die obersten Prüfpunkte liegen oft nahe Straßen und Siedlungen. Das Modell stützt sich auf Landbedeckung und Rauigkeit; ein Teil davon kann Meldebias sein.</li>
          <li>{{ data.auslaufpruefung }}</li>
          <li>Fehlende Größen im Auslaufszenario: {{ data.fehlende_groessen.join(', ') }}.</li>
          <li>Prüfstufen sind relativ zum gewählten Umkreis ({{ percent(assessedShare) }} der Zellen bewertbar<template v-for="(n, k) in data.pruefstufen.nicht_bewertbar_nach_grund" :key="k">; {{ count(n) }} {{ REASON_TEXT[k] || k }}</template>). Nicht bewertete Flächen sind keine niedrige Stufe.</li>
          <li>Die Prüfstufen sind nicht mit dem Auslauf zu einer Gesamtstufe verrechnet, weil keine der beiden Komponenten geprüft ist.</li>
        </ul>
        <p class="wk-note">{{ data.hinweis }}</p>
        <p class="wk-note">Quellen: {{ Object.values(data.quellen).join(' · ') }}. Konfiguration {{ data.identitaet.konfiguration_sha256.slice(0, 12) }}, Modell {{ data.identitaet.modell_sha256.slice(0, 12) }}.</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
.wk{--ink:#202025;--plum:#7a1e48;margin:0;padding-top:8px}
.wk-head{max-width:820px}
.wk-kicker{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 10px;font-weight:600}
.wk-head h2{font-size:clamp(26px,3.2vw,40px);letter-spacing:-1.2px;line-height:1.1;margin:0 0 14px;font-weight:500;color:var(--blue)}
.wk-lead{font-size:16px;line-height:1.6;margin:0 0 10px}
.wk-seal{font-size:12px;color:var(--muted);border-left:2px solid var(--plum);padding-left:10px;margin:0}
.wk-tag{display:inline-block;font-size:9.5px;letter-spacing:.07em;text-transform:uppercase;font-weight:700;padding:1px 6px;border:1px solid currentColor;line-height:1.5;vertical-align:1px}
.wk-tag[data-kind=Befund]{color:var(--plum)}
.wk-tag[data-kind=Szenario]{color:var(--blue)}
.wk-tag[data-kind=Illustration]{color:#6b6b74}
.wk-chain{list-style:none;margin:26px 0 22px;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:2px solid var(--ink);border-bottom:1px solid var(--line)}
.wk-chain li{position:relative;padding:14px 26px 16px 0;min-width:0}
.wk-chain li+li{padding-left:26px;border-left:1px solid var(--line)}
.wk-chain li+li::before{content:'';position:absolute;left:-7px;top:22px;width:12px;height:12px;background:#fff;border-top:2px solid var(--ink);border-right:2px solid var(--ink);transform:rotate(45deg)}
.wk-chain h3{font-size:12px;font-weight:600;margin:8px 0 6px;letter-spacing:0;text-transform:none;color:var(--muted)}
.wk-chain-main{font-size:21px;letter-spacing:-.5px;line-height:1.25;margin:0 0 6px;font-variant-numeric:tabular-nums}
.wk-chain-sub{font-size:12px;color:var(--muted);margin:0;line-height:1.5}
.wk-controls{display:grid;grid-template-columns:minmax(0,1.3fr) auto minmax(0,1fr);gap:18px 28px;align-items:end;margin-bottom:14px}
.wk-control{border:0;padding:0;margin:0;min-width:0}
.wk-control>label,.wk-control legend{display:block;font-size:12px;color:var(--muted);margin-bottom:6px;padding:0}
.wk-radius output{color:var(--ink);font-weight:600;margin-left:6px}
.wk-radius input{width:100%;accent-color:var(--blue);min-height:28px}
.wk-radius small{display:block;font-size:11px;color:var(--muted);line-height:1.5;margin-top:2px}
.wk-seg{display:flex;border:1px solid var(--line)}
.wk-seg label{display:flex;align-items:center;gap:6px;padding:0 12px;min-height:44px;font-size:12px;cursor:pointer;white-space:nowrap}
.wk-seg label+label{border-left:1px solid var(--line)}
.wk-seg label.on{background:var(--blue);color:#fff}
.wk-seg input{position:absolute;opacity:0;width:1px;height:1px}
.wk-seg label:focus-within{outline:3px solid var(--blue);outline-offset:2px}
.wk-control select{width:100%;min-height:44px;border:1px solid #bcbcc4;background:#fff;padding:0 10px;font-size:13px}
.wk-stage{display:grid;grid-template-columns:minmax(0,1fr) 330px;border:1px solid var(--line);margin-bottom:18px}
.wk-mapcol{min-width:0;border-right:1px solid var(--line)}
.wk-layers{border:0;margin:0;padding:10px 12px;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;border-bottom:1px solid var(--line)}
.wk-layers label{display:inline-flex;align-items:center;gap:6px;cursor:pointer;min-height:32px}
.wk-mapwrap{position:relative}
.wk-map{height:540px;width:100%}
.wk-mapbtns{position:absolute;top:10px;left:10px;display:flex;gap:6px}
.wk-mapbtns button{min-height:34px;padding:6px 10px;font-size:11px;background:#fff;border:1px solid #bcbcc4}
.wk-busy{position:absolute;top:52px;left:10px;margin:0;background:#fff;border:1px solid var(--line);padding:8px 12px;font-size:12px}
.wk-legend{position:absolute;left:10px;bottom:34px;background:#ffffffee;border:1px solid var(--line);padding:8px 10px;font-size:10px;display:grid;gap:4px;pointer-events:none}
.wk-legend-row{display:flex;align-items:center;gap:4px}
.wk-legend-text{justify-content:space-between;color:var(--muted)}
.wk-sw{display:inline-block;width:18px;height:10px;margin-right:2px}
.wk-legend .wk-sw{width:22px;margin:0}
.wk-k-route,.wk-k-corr,.wk-k-hit{display:inline-block;margin:0 4px 0 8px}
.wk-k-route{width:16px;border-top:2px dashed var(--ink);margin-left:0}
.wk-k-corr{width:14px;height:9px;background:#002fa752;border:1px solid var(--blue)}
.wk-k-hit{width:9px;height:9px;border-radius:50%;background:var(--ink);border:1.5px solid #fff;box-shadow:0 0 0 1px var(--ink)}
.wk-panel{padding:18px 18px 16px;min-width:0}
.wk-panel-kicker{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--plum);margin:0 0 6px;font-weight:600}
.wk-panel-title{font-size:22px;letter-spacing:-.5px;margin:0 0 12px;color:var(--ink);font-weight:500;overflow-wrap:anywhere}
.wk-facts{display:flex;gap:18px;margin:0 0 14px}
.wk-facts dt{font-size:10px;color:var(--muted)}
.wk-facts dd{margin:2px 0 0;font-size:18px;letter-spacing:-.4px}
.wk-drivers{border-top:1px solid var(--line);padding-top:10px;margin-bottom:10px}
.wk-drivers p{font-size:12px;margin:0 0 6px}
.wk-drivers small{color:var(--muted)}
.wk-drivers ul{list-style:none;margin:0;padding:0;font-size:12px}
.wk-drivers li{display:flex;justify-content:space-between;gap:10px;padding:4px 0;border-bottom:1px solid #f0f0f2}
.wk-drivers b{font-weight:500;white-space:nowrap}
.wk-drivers b.up{color:var(--plum)}
.wk-drivers b.down{color:#4d6a52}
.wk-route-end{font-size:12px;line-height:1.55;margin:10px 0 12px}
.wk-route-end b{font-weight:600}
.wk-scen{display:grid;border-top:1px solid var(--line)}
.wk-scen-row{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:9px 8px;border-bottom:1px solid var(--line);cursor:pointer;font-size:12px}
.wk-scen-row input{position:absolute;opacity:0;width:1px;height:1px}
.wk-scen-row:focus-within{outline:3px solid var(--blue);outline-offset:-3px}
.wk-scen-row.on{background:#002fa70f;box-shadow:inset 3px 0 0 var(--blue)}
.wk-scen-name{font-weight:600}
.wk-scen-len{text-align:right;font-variant-numeric:tabular-nums}
.wk-scen-status{font-size:11px;color:var(--muted)}
.wk-scen-status.open{color:#8a5a00}
.wk-scen-infra{text-align:right;font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}
.wk-source{font-size:11px;color:var(--muted);line-height:1.55;margin:10px 0 0}
.wk-hits{margin:22px 0}
.wk-hits h3{font-size:19px;font-weight:500;margin:0 0 6px}
.wk-hit-counts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:14px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.wk-hit-counts div{padding:12px 14px 12px 0}
.wk-hit-counts div+div{padding-left:14px;border-left:1px solid var(--line)}
.wk-hit-counts dt{font-size:11px;color:var(--muted)}
.wk-hit-counts dd{margin:4px 0 0;font-size:30px;letter-spacing:-1px;font-variant-numeric:tabular-nums}
.wk-hit-counts small{font-size:11px;color:var(--muted)}
.wk-table-wrap{overflow-x:auto;max-width:100%}
.wk-table{border-collapse:collapse;width:100%;font-size:12px}
.wk-table th,.wk-table td{text-align:left;padding:8px 12px 8px 0;border-bottom:1px solid #eaeaed;white-space:nowrap}
.wk-table thead th{font-weight:400;color:var(--muted);font-size:11px}
.wk-more{margin-top:10px;font-size:12px}
.wk-lower{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:40px;border-top:1px solid var(--line);padding-top:22px}
.wk-lower h3{font-size:17px;font-weight:500;margin:8px 0 8px}
.wk-share{border-collapse:collapse;width:100%;font-size:12px;margin:10px 0}
.wk-share th,.wk-share td{text-align:left;padding:7px 8px 7px 0;border-bottom:1px solid #eaeaed;font-weight:400;font-variant-numeric:tabular-nums}
.wk-share thead th{color:var(--muted);font-size:11px}
.wk-share td{position:relative;min-width:72px}
.wk-bar{display:block;height:4px;background:#c9c9cf;margin-bottom:4px;max-width:100%}
.wk-bar.ev{background:var(--ink)}
.wk-finding{font-size:13px;line-height:1.6;border-left:2px solid var(--plum);padding-left:10px}
.wk-limits ul{margin:0 0 10px;padding-left:18px;font-size:12.5px;line-height:1.6;display:grid;gap:6px}
.wk-note{font-size:12px;color:var(--muted);line-height:1.6;margin:6px 0}
.wk-warn{color:#8a1c12;font-size:12px;margin:8px 12px}
.wk-panel .wk-warn{margin:0 0 10px}
.wk-warn button{margin-left:8px;font-size:12px;min-height:36px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
@media (max-width:980px){.wk-stage{grid-template-columns:1fr}.wk-mapcol{border-right:0;border-bottom:1px solid var(--line)}.wk-controls{grid-template-columns:1fr 1fr}.wk-radius{grid-column:1/-1}.wk-lower{grid-template-columns:1fr;gap:26px}}
@media (max-width:640px){
  .wk-chain{grid-template-columns:1fr}
  .wk-chain li,.wk-chain li+li{padding:12px 0;border-left:0}
  .wk-chain li+li{border-top:1px solid var(--line)}
  .wk-chain li+li::before{left:18px;top:-7px;transform:rotate(135deg)}
  .wk-chain-main{font-size:18px}
  .wk-controls{grid-template-columns:1fr}
  .wk-seg{flex-direction:column}
  .wk-seg label+label{border-left:0;border-top:1px solid var(--line)}
  .wk-map{height:400px}
  .wk-hit-counts{grid-template-columns:1fr 1fr}
  .wk-hit-counts div:nth-child(3){border-left:0;padding-left:0}
  .wk-hit-counts div:nth-child(n+3){border-top:1px solid var(--line)}
  .wk-hit-counts dd{font-size:24px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
