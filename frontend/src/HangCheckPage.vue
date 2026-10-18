<script setup>
import {ref, computed, onMounted, onBeforeUnmount, watch} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {useResource} from './useResource.js'
import {OFFICIAL, FALLBACK_HINWEISE, STUFE_FARBE, createLayerLoader, placeKey, classShareText, circle, km} from './hangcheck.js'
maplibregl.setWorkerUrl(workerUrl)

const {data: meta, error: metaError} = useResource('/api/hangcheck/beispiele')
const container = ref(null)
const place = ref(null), radius = ref(2000), starkregen = ref(false)
const result = ref(null), loading = ref(false), error = ref(''), hint = ref('')
const query = ref(''), suggestions = ref([]), searchOpen = ref(false), locating = ref(false)
let map, ready = false, centreMarker, pointMarkers = [], searchTimer, searchSeq = 0

const hinweise = computed(() => meta.value?.hinweise ?? FALLBACK_HINWEISE)
const radiusCfg = computed(() => meta.value?.radius_m ?? {min: 1000, max: 3000, step: 500})
const stufen = computed(() => meta.value?.stufen ?? [])
const stufe1 = computed(() => result.value?.zaehlung.stufen['Prüfstufe 1'] ?? 0)

async function fetchLayer(body) {
  const r = await fetch('/api/hangcheck', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
  const json = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(typeof json.detail === 'string' ? json.detail : `Berechnung nicht möglich (HTTP ${r.status}).`)
  return json
}
const loader = createLayerLoader(fetchLayer)

async function refresh() {
  error.value = ''
  if (!starkregen.value || !place.value) { result.value = null; draw(); return }
  const key = placeKey(place.value, radius.value)
  loading.value = !loader.has(place.value, radius.value)
  try {
    const r = await loader.update({on: starkregen.value, place: place.value, radiusM: radius.value})
    if (key === placeKey(place.value, radius.value) && starkregen.value) { result.value = r; draw() }
  } catch (e) {
    if (key === placeKey(place.value, radius.value)) { error.value = e.message; result.value = null; draw() }
  } finally {
    if (key === placeKey(place.value, radius.value)) loading.value = false
  }
}

// ---------- place choice ----------
function setPlace(p, zoom) {
  place.value = p; result.value = null; error.value = ''; hint.value = ''
  drawPlace(); fly(zoom); refresh()
}
function pickExample(e) { radius.value = e.radius_m; query.value = ''; setPlace({longitude: e.longitude, latitude: e.latitude, name: e.name}) }
function pickSuggestion(o) { query.value = o.anzeige; searchOpen.value = false; setPlace({longitude: o.longitude, latitude: o.latitude, name: o.anzeige}) }
function onSearchInput() {
  clearTimeout(searchTimer)
  const q = query.value.trim()
  if (q.length < 2) { suggestions.value = []; searchOpen.value = false; return }
  searchTimer = setTimeout(async () => {
    const seq = ++searchSeq
    try {
      const r = await fetch('/api/hangcheck/orte?q=' + encodeURIComponent(q))
      const json = await r.json()
      if (seq === searchSeq) { suggestions.value = json.orte ?? []; searchOpen.value = true }
    } catch { if (seq === searchSeq) { suggestions.value = []; hint.value = 'Gemeindesuche nicht erreichbar.' } }
  }, 180)
}
function onSearchEnter() { if (suggestions.value.length) pickSuggestion(suggestions.value[0]) }
function locate() {
  // Browser location only moves the map; it is not stored, logged or put into the address.
  if (!navigator.geolocation) { hint.value = 'Dieser Browser bietet keine Standortabfrage an.'; return }
  locating.value = true; hint.value = ''
  navigator.geolocation.getCurrentPosition(
    pos => { locating.value = false; query.value = ''; setPlace({longitude: pos.coords.longitude, latitude: pos.coords.latitude, name: 'Mein Standort'}) },
    () => { locating.value = false; hint.value = 'Standort nicht verfügbar oder nicht freigegeben. Bitte Gemeinde eintippen oder auf die Karte klicken.' },
    {enableHighAccuracy: false, timeout: 10000, maximumAge: 60000})
}
function onRadius() { drawPlace(); fly(); refresh() }

// ---------- map ----------
function style() {
  const dem = {type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 14, encoding: 'terrarium'}
  return {version: 8, sources: {
    ortho: {type: 'raster', tiles: ['https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg'], tileSize: 256, maxzoom: 19,
      attribution: 'Orthofoto: basemap.at (CC BY 4.0)'}, hill: dem},
  layers: [{id: 'background', type: 'background', paint: {'background-color': '#eceee8'}},
    {id: 'ortho', type: 'raster', source: 'ortho', paint: {'raster-saturation': -0.35}},
    {id: 'hillshade', type: 'hillshade', source: 'hill', paint: {'hillshade-exaggeration': .35, 'hillshade-shadow-color': '#1d2420'}}]}
}
function el(text, cls) { const d = document.createElement('div'); d.className = cls; d.textContent = text; return d }
function drawPlace() {
  if (!ready) return
  centreMarker?.remove(); centreMarker = null
  map.getSource('umkreis').setData(place.value ? circle(place.value, Number(radius.value)) : {type: 'FeatureCollection', features: []})
  if (place.value) centreMarker = new maplibregl.Marker({element: el('◎', 'hc-centre')}).setLngLat([place.value.longitude, place.value.latitude]).addTo(map)
}
function draw() {
  if (!ready) return
  pointMarkers.forEach(m => m.remove()); pointMarkers = []
  map.getSource('zellen').setData(result.value?.zellen ?? {type: 'FeatureCollection', features: []})
  for (const p of result.value?.pruefpunkte ?? []) {
    const m = el(String(p.nr), 'hc-point'); m.title = `Prüfpunkt ${p.nr}`
    pointMarkers.push(new maplibregl.Marker({element: m}).setLngLat([p.longitude, p.latitude]).addTo(map))
  }
}
function fly(zoom) {
  if (!ready || !place.value) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (zoom) { map.easeTo({center: [place.value.longitude, place.value.latitude], zoom, duration: reduce ? 0 : 900}); return }
  const ring = circle(place.value, Number(radius.value), 32).geometry.coordinates[0]
  const lons = ring.map(c => c[0]), lats = ring.map(c => c[1])
  map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], {padding: 24, duration: reduce ? 0 : 900})
}
function showPoint(p) {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  map.easeTo({center: [p.longitude, p.latitude], zoom: 15, duration: reduce ? 0 : 900})
  container.value?.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block: 'center'})
}

onMounted(() => {
  map = new maplibregl.Map({container: container.value, style: style(), center: [13.3, 47.6], zoom: 6.3, attributionControl: false, dragRotate: false,
    locale: {'NavigationControl.ZoomIn': 'Vergrößern', 'NavigationControl.ZoomOut': 'Verkleinern', 'Map.Title': 'Karte'}})
  map.addControl(new maplibregl.NavigationControl({showCompass: false}), 'top-right')
  map.addControl(new maplibregl.ScaleControl({unit: 'metric'}), 'bottom-left')
  map.on('load', () => {
    ready = true
    map.addSource('umkreis', {type: 'geojson', data: {type: 'FeatureCollection', features: []}})
    map.addSource('zellen', {type: 'geojson', data: {type: 'FeatureCollection', features: []}})
    map.addLayer({id: 'zellen', type: 'fill', source: 'zellen', paint: {'fill-opacity': .62,
      'fill-color': ['match', ['get', 'stufe'], 1, STUFE_FARBE[1], STUFE_FARBE[2]]}})
    map.addLayer({id: 'umkreis', type: 'line', source: 'umkreis', paint: {'line-color': '#ffffff', 'line-width': 2.5, 'line-dasharray': [2, 1.5]}})
    drawPlace(); draw(); fly()
  })
  map.on('click', e => { query.value = ''; setPlace({longitude: e.lngLat.lng, latitude: e.lngLat.lat, name: 'Gewählter Kartenpunkt'}) })
  map.on('error', () => { hint.value = 'Ein Teil der Kartenkacheln konnte nicht geladen werden (Internetverbindung?).' })
})
onBeforeUnmount(() => { clearTimeout(searchTimer); pointMarkers.forEach(m => m.remove()); centreMarker?.remove(); map?.remove() })
watch(starkregen, refresh)
</script>

<template>
  <section class="hc">
    <header class="hc-head">
      <p class="eyebrow">Anwendung · Gelände-Modell</p>
      <h1>Hang-Check</h1>
      <p class="hc-lead">Ort wählen, Schalter setzen: Die Karte markiert die auffälligsten Hänge in diesem Umkreis. Dort sollte man bei Starkregen zuerst hinschauen.</p>
    </header>

    <aside class="hc-notice" role="note" aria-label="Bitte zuerst lesen">
      <h2>Bitte zuerst lesen</h2>
      <ol>
        <li v-for="h in hinweise" :key="h.titel"><strong>{{ h.titel }}</strong> {{ h.text }}</li>
      </ol>
      <p class="hc-official">Offizielle Unwetterwarnungen: <a :href="OFFICIAL.geosphere" target="_blank" rel="noopener">GeoSphere Austria</a> und die Landeswarnzentralen der Bundesländer.</p>
    </aside>

    <div class="hc-grid">
      <div class="hc-panel">
        <h2>1 · Ort wählen</h2>
        <div class="hc-search">
          <label for="hc-ort" class="hc-label">Gemeinde</label>
          <input id="hc-ort" type="search" v-model="query" autocomplete="off" placeholder="z. B. Landeck" role="combobox"
                 :aria-expanded="searchOpen && suggestions.length > 0" aria-controls="hc-ort-liste" aria-autocomplete="list"
                 @input="onSearchInput" @keydown.enter.prevent="onSearchEnter" @keydown.escape="searchOpen=false">
          <ul v-if="searchOpen" id="hc-ort-liste" class="hc-suggest" role="listbox" aria-label="Gefundene Gemeinden">
            <li v-for="o in suggestions" :key="o.kennziffer" role="option" :aria-selected="false">
              <button type="button" @click="pickSuggestion(o)">{{ o.name }} <small>{{ o.bundesland }}</small></button>
            </li>
            <li v-if="!suggestions.length" class="hc-none">Keine Gemeinde gefunden.</li>
          </ul>
        </div>
        <p class="hc-help">Oder auf die Karte klicken, ein Beispiel wählen oder den eigenen Standort nutzen.</p>
        <button type="button" class="hc-secondary" :disabled="locating" @click="locate">{{ locating ? 'Standort wird abgefragt …' : 'Mein Standort' }}</button>
        <p class="hc-help">Der Standort bewegt nur die Karte. Er wird nicht gespeichert und nicht weitergegeben.</p>
        <div class="hc-examples" v-if="meta"><span class="hc-label">Beispiele</span>
          <button v-for="e in meta.beispiele" :key="e.id" type="button" @click="pickExample(e)">{{ e.name }}</button></div>
        <p v-else-if="metaError" class="hc-warn" role="alert">{{ metaError }}</p>
        <label class="hc-field">Umkreis: <b>{{ km(radius) }}</b>
          <input type="range" :min="radiusCfg.min" :max="radiusCfg.max" :step="radiusCfg.step" v-model.number="radius" @change="onRadius"></label>
        <p v-if="place" class="hc-place">Gewählt: <b>{{ place.name }}</b></p>

        <h2>2 · Lage</h2>
        <label class="hc-switch">
          <input type="checkbox" role="switch" v-model="starkregen" :aria-checked="starkregen">
          <span class="hc-track" aria-hidden="true"><span></span></span>
          <span>Starkregen oder Unwetter erwartet</span>
        </label>
        <p class="hc-help">Der Schalter ruft keine Wetterdaten ab und ändert die Einstufung nicht. Er zeigt nur die Ansicht für den Starkregenfall.</p>
        <p v-if="!starkregen" class="hc-off">Schalter aktivieren, um zu sehen, welche Hänge man bei Starkregen zuerst ansehen sollte.</p>
        <p v-else-if="!place" class="hc-off">Zuerst einen Ort wählen.</p>
        <p v-if="hint" class="hc-warn" role="status">{{ hint }}</p>
        <p v-if="error" class="hc-warn" role="alert">{{ error }}</p>
      </div>

      <div class="hc-map-col">
        <div ref="container" class="hc-map" aria-label="Karte mit Umkreis und markierten Hängen"></div>
        <div class="hc-legend">
          <span class="hc-legend-title">Auffälligste Hänge in diesem Umkreis</span>
          <span><i :style="{background: STUFE_FARBE[1]}"></i>Prüfstufe 1<template v-if="stufen.length"> · oberste {{ classShareText(stufen, 1) }}</template></span>
          <span><i :style="{background: STUFE_FARBE[2]}"></i>Prüfstufe 2<template v-if="stufen.length"> · nächste {{ classShareText(stufen, 2) }}</template></span>
          <span><i class="none"></i>ohne Farbe: nicht markiert heißt nicht sicher</span>
          <small class="hc-sources">Orthofoto: basemap.at (CC BY 4.0) · Relief: Mapzen/Skadi · Landbedeckung: CORINE · Geologie: GeoSphere Austria · Gemeinden: GISCO · Karte: MapLibre</small>
        </div>
        <p v-if="loading" class="hc-busy" role="status">Gelände, Landbedeckung und Geologie werden berechnet … (beim ersten Mal bis ca. 30 s)</p>
      </div>
    </div>

    <section v-if="starkregen && result" class="hc-result" aria-live="polite">
      <h2>Hier zuerst hinschauen</h2>
      <p class="hc-note">Die {{ result.pruefpunkte.length }} auffälligsten Stellen der Prüfstufe 1, mindestens {{ result.pruefpunkte_abstand_m }} m voneinander entfernt. Rangfolge nur innerhalb von {{ km(result.radius_m) }} Umkreis.</p>
      <ol class="hc-points">
        <li v-for="p in result.pruefpunkte" :key="p.nr">
          <span class="hc-nr" aria-hidden="true">{{ p.nr }}</span>
          <div>
            <p class="hc-facts"><b>{{ p.hoehe_m.toLocaleString('de-AT') }} m Höhe</b> · {{ p.neigung_grad.toLocaleString('de-AT') }}° Neigung · {{ p.landbedeckung }} · {{ p.geologie }}</p>
            <p class="hc-drivers">Das Modell stützt sich hier vor allem auf: <span v-for="(d, i) in p.treiber" :key="d.merkmal">{{ i ? '; ' : '' }}{{ d.merkmal }} ({{ d.richtung }})</span>.</p>
            <p v-if="p.treiber.some(d => d.merkmal.startsWith('Landbedeckung Siedlung') && d.richtung.startsWith('hebt'))" class="hc-caution">Siedlungs- oder Verkehrsfläche hebt hier die Einstufung. Das kann ein Meldeeffekt sein (Ereignisse an Straßen werden eher gemeldet), nicht unbedingt eine Eigenschaft des Hangs.</p>
            <button type="button" class="hc-link" @click="showPoint(p)">Auf der Karte zeigen</button>
          </div>
        </li>
      </ol>
      <p v-if="result.pruefpunkte.length < 5" class="hc-note">In der Prüfstufe 1 liegen nicht genug getrennte Stellen für fünf Prüfpunkte.</p>
      <p class="hc-note">{{ result.zaehlung.bewertet.toLocaleString('de-AT') }} von {{ result.zaehlung.zellen.toLocaleString('de-AT') }} Rasterzellen ({{ result.zellgroesse_m }} m) im Umkreis bewertet,
        davon {{ stufe1.toLocaleString('de-AT') }} in Prüfstufe 1 und {{ (result.zaehlung.stufen['Prüfstufe 2'] ?? 0).toLocaleString('de-AT') }} in Prüfstufe 2.
        Nicht bewertet: <span v-if="!result.zaehlung.ausgeschlossen.length">keine</span><span v-for="(a, i) in result.zaehlung.ausgeschlossen" :key="a.grund">{{ i ? '; ' : '' }}{{ a.anzahl.toLocaleString('de-AT') }} × {{ a.grund }}</span>.</p>
      <p class="hc-note">Grundlage: {{ result.datenstand.terrain }}, {{ result.datenstand.land_cover }}, {{ result.datenstand.geology }}. Modell: {{ result.modell.variante }}, unverändert übernommen
        (Prüfsumme {{ result.modell.bundle_sha256.slice(0, 12) }}…). Treiber sind Beiträge im Modell, keine Ursachen. <a href="#/methodik">Methodik &amp; Grenzen</a></p>
    </section>
  </section>
</template>

<style scoped>
.hc{padding:48px 0 70px}.hc-head h1{font-size:clamp(44px,5vw,72px);letter-spacing:-3px;line-height:1.05;margin:0 0 14px;color:var(--blue)}.hc-lead{font-size:18px;line-height:1.55;max-width:720px;margin:0 0 24px}
.hc-notice{border-left:4px solid #c62828;background:#fbf6f4;padding:16px 20px;margin:0 0 28px;max-width:980px}.hc-notice h2{font-size:15px;margin:0 0 8px;letter-spacing:0}
.hc-notice ol{margin:0;padding-left:20px}.hc-notice li{font-size:14px;line-height:1.6;margin-bottom:6px}.hc-official{font-size:13px;margin:10px 0 0}
.hc-grid{display:grid;grid-template-columns:330px minmax(0,1fr);gap:28px;align-items:start}
.hc-panel h2{font-size:15px;letter-spacing:0;margin:24px 0 10px;font-weight:600}.hc-panel h2:first-child{margin-top:0}
.hc-help{font-size:12px;color:var(--muted);line-height:1.6;margin:6px 0}.hc-label{display:block;font-size:12px;font-weight:600;margin-bottom:4px}
.hc-search{position:relative}.hc-search input{width:100%;box-sizing:border-box;padding:11px 12px;font-size:15px;border:1px solid #bcbcc4;background:#fff}
.hc-suggest{position:absolute;z-index:5;left:0;right:0;top:100%;margin:0;padding:0;list-style:none;background:#fff;border:1px solid #bcbcc4;border-top:0;max-height:300px;overflow:auto;box-shadow:0 6px 18px #0002}
.hc-suggest button{display:block;width:100%;text-align:left;background:#fff;border:0;border-bottom:1px solid #eee;padding:10px 12px;font-size:14px}.hc-suggest button:hover,.hc-suggest button:focus{background:#eef2fb}
.hc-suggest small{color:var(--muted);margin-left:6px}.hc-none{padding:10px 12px;font-size:13px;color:var(--muted)}
.hc-secondary{width:100%;background:#fff;border:1px solid var(--blue);color:var(--blue);padding:10px;font-size:13px;margin-top:4px}
.hc-examples{display:flex;flex-direction:column;gap:6px;margin:14px 0}.hc-examples button{background:#fff;border:1px solid #bcbcc4;padding:9px 12px;font-size:12px;text-align:left}.hc-examples button:hover{border-color:var(--blue);color:var(--blue)}
.hc-field{display:block;font-size:12px;margin:10px 0}.hc-field input{width:100%;accent-color:var(--blue);display:block;margin-top:6px}.hc-place{font-size:13px;margin:8px 0 0}
.hc-switch{display:flex;align-items:center;gap:12px;font-size:15px;font-weight:600;cursor:pointer;padding:12px;border:1px solid #bcbcc4;background:#fff;position:relative}
.hc-switch input{position:absolute;opacity:0;width:1px;height:1px}.hc-track{flex:none;width:46px;height:26px;border-radius:13px;background:#b7b7bf;position:relative;transition:background .15s}
.hc-track span{position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:#fff;transition:left .15s}
.hc-switch input:checked + .hc-track{background:#c62828}.hc-switch input:checked + .hc-track span{left:23px}.hc-switch input:focus-visible + .hc-track{outline:3px solid var(--blue);outline-offset:2px}
.hc-off{font-size:13px;background:#f3f4f6;padding:10px 12px;line-height:1.5;margin:10px 0}
.hc-warn{font-size:12px;color:#8a1f11;background:#fdf1ef;padding:9px 11px;margin:8px 0;line-height:1.5}
.hc-map-col{position:relative;min-width:0}.hc-map{height:min(72vh,660px);min-height:420px;border:1px solid var(--line);background:#eceee8}
.hc-busy{position:absolute;top:12px;left:12px;right:60px;background:#fff;padding:9px 12px;font-size:12px;margin:0;border:1px solid var(--line)}
.hc-legend{border:1px solid var(--line);border-top:0;background:#fff;padding:9px 12px;font-size:12px;display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center}
.hc-legend-title{font-weight:600;flex-basis:100%}.hc-sources{flex-basis:100%;color:var(--muted);font-size:10px;line-height:1.5}.hc-legend i{display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:-2px;opacity:.85}.hc-legend i.none{border:1px dashed #777;box-sizing:border-box}
.hc-result{margin-top:36px;border-top:1px solid var(--line);padding-top:26px}.hc-result h2{font-size:28px;letter-spacing:-.6px;margin:0 0 10px}
.hc-points{list-style:none;padding:0;margin:18px 0;display:grid;gap:12px;max-width:980px}.hc-points li{display:flex;gap:14px;border:1px solid var(--line);padding:14px;background:#fff}
.hc-nr{flex:none;width:30px;height:30px;border-radius:50%;background:#c62828;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
.hc-facts{margin:0 0 4px;font-size:14px;line-height:1.5}.hc-drivers{margin:0 0 4px;font-size:12px;color:var(--muted);line-height:1.5}
.hc-caution{margin:2px 0 6px;font-size:12px;line-height:1.5;color:#6b4a00;background:#fff6e0;padding:6px 9px}
.hc-link{background:none;border:0;color:var(--blue);text-decoration:underline;font-size:12px;padding:0}
.hc-note{font-size:12px;color:var(--muted);line-height:1.7;max-width:980px;margin:12px 0 0}
@media(max-width:900px){.hc-grid{grid-template-columns:1fr}.hc-map{height:60vh;min-height:360px}}
</style>
<style>
.hc-centre{font-size:26px;line-height:1;color:#fff;text-shadow:0 0 4px #000,0 0 2px #000;pointer-events:none}
.hc-point{width:26px;height:26px;border-radius:50%;background:#c62828;color:#fff;border:2px solid #fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 5px #0007}
</style>
