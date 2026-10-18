<script setup>
// MapLibre with real 3D terrain (Terrarium DEM), paper-toned hillshade and basemap.at.
// Display only: the classes come from the API; this component never computes anything about slopes.
import {ref, watch, onMounted, onBeforeUnmount} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {zoomFor} from '../check.js'
import {circle} from '../hangcheck.js'
import {reducedMotion} from '../ui/motion.js'
maplibregl.setWorkerUrl(workerUrl)

const props = defineProps({
  centre: {type: Object, default: null}, radiusM: {type: Number, default: 2000},
  cells: {type: Object, default: null}, maxD: {type: Number, default: 1}, points: {type: Array, default: () => []},
  active: {type: Number, default: null}, base: {type: String, default: 'grau'}, arrival: Boolean,
  flows: {type: Object, default: null}, flowActive: {type: Number, default: null},   // possible flow paths (scenario)
  embedded: Boolean,   // small preview inside a page: no page padding, gestures need two fingers / Ctrl
})
const emit = defineEmits(['pick', 'hover', 'select', 'ready', 'failed'])
const el = ref(null)
let map = null, ready = false, centreMarker = null, pins = [], wave = 0
const EMPTY = {type: 'FeatureCollection', features: []}

function style() {
  const dem = {type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 14, encoding: 'terrarium',
    attribution: 'Relief: Mapzen Terrarium (AWS Open Data; u. a. DGM Österreich, EU-DEM, USGS)'}
  return {version: 8, sources: {
    grau: {type: 'raster', tiles: ['https://mapsneu.wien.gv.at/basemap/bmapgrau/normal/google3857/{z}/{y}/{x}.png'], tileSize: 256, maxzoom: 19, attribution: 'Karte: basemap.at (CC BY 4.0)'},
    ortho: {type: 'raster', tiles: ['https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg'], tileSize: 256, maxzoom: 19, attribution: 'Orthofoto: basemap.at (CC BY 4.0)'},
    dem, hill: dem,
    ring: {type: 'geojson', data: EMPTY}, cells: {type: 'geojson', data: EMPTY}, flows: {type: 'geojson', data: EMPTY}},
  layers: [
    {id: 'paper', type: 'background', paint: {'background-color': '#EAE7DF'}},
    {id: 'grau', type: 'raster', source: 'grau', paint: {'raster-opacity': .82, 'raster-saturation': -.35, 'raster-contrast': -.08}},
    {id: 'ortho', type: 'raster', source: 'ortho', layout: {visibility: 'none'}},
    {id: 'hill', type: 'hillshade', source: 'hill', paint: {'hillshade-exaggeration': .55, 'hillshade-shadow-color': '#3C4A52', 'hillshade-highlight-color': '#FBFAF6', 'hillshade-accent-color': '#5E6B60'}},
    {id: 'cells', type: 'fill', source: 'cells', paint: {'fill-color': ['match', ['get', 'stufe'], 1, '#D4432A', '#E9973A'], 'fill-opacity': 0}},
    {id: 'cells-edge', type: 'line', source: 'cells', paint: {'line-color': ['match', ['get', 'stufe'], 1, '#8E2715', '#A8641C'], 'line-width': 1, 'line-opacity': 0}},
    {id: 'flow-corr', type: 'fill', source: 'flows', filter: ['==', ['get', 'art'], 'korridor'], paint: {'fill-color': '#8DB6C7', 'fill-opacity': .32}},
    {id: 'flow-halo', type: 'line', source: 'flows', filter: ['!=', ['get', 'art'], 'korridor'], layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-color': '#FFFFFF', 'line-width': ['match', ['get', 'art'], 'kurz', 9, 6], 'line-opacity': .85}},
    {id: 'flow-lang', type: 'line', source: 'flows', filter: ['==', ['get', 'art'], 'lang'], layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-color': '#1E5A7A', 'line-width': 3, 'line-dasharray': [1.5, 1.2]}},
    {id: 'flow-kurz', type: 'line', source: 'flows', filter: ['==', ['get', 'art'], 'kurz'], layout: {'line-cap': 'round', 'line-join': 'round'}, paint: {'line-color': '#1E5A7A', 'line-width': 6}},
    {id: 'ring-halo', type: 'line', source: 'ring', paint: {'line-color': '#FFFFFF', 'line-width': 5, 'line-opacity': .7}},
    {id: 'ring', type: 'line', source: 'ring', paint: {'line-color': '#13202B', 'line-width': 2.2, 'line-dasharray': [2.5, 2]}},
  ]}
}

function setRing() {
  if (!ready) return
  map.getSource('ring').setData(props.centre ? {type: 'Feature', geometry: {type: 'LineString', coordinates: circle(props.centre, props.radiusM).geometry.coordinates[0]}, properties: {}} : EMPTY)
  centreMarker?.remove(); centreMarker = null
  if (props.centre) {
    const dot = document.createElement('div'); dot.className = 'tm-centre'; dot.setAttribute('aria-hidden', 'true')
    centreMarker = new maplibregl.Marker({element: dot}).setLngLat([props.centre.longitude, props.centre.latitude]).addTo(map)
  }
}
// The panel covers the left side (desktop) or the lower half (phone); the camera centres in the free part.
function padding() {
  if (!map || props.embedded) return
  const phone = window.innerWidth < 760
  map.setPadding(phone ? {top: 70, bottom: Math.round(window.innerHeight * .45), left: 0, right: 0} : {top: 80, bottom: 0, left: 452, right: 0})
}
function fly() {
  if (!props.centre) return
  const target = {center: [props.centre.longitude, props.centre.latitude], zoom: zoomFor(props.radiusM), pitch: 60, bearing: -18}
  if (reducedMotion()) { map.jumpTo(target); return }
  map.flyTo({...target, duration: 2500, curve: 1.3, essential: true})
}
function setOpacity(v) {
  map.setPaintProperty('cells', 'fill-opacity', v)
  map.setPaintProperty('cells-edge', 'line-opacity', v === 0 ? 0 : .9)
}
// Radial wave: cells appear by distance from the chosen point (750 ms); reduced motion shows the end state.
function reveal() {
  cancelAnimationFrame(wave)
  if (!ready) return
  map.getSource('cells').setData(props.cells ?? EMPTY)
  if (!props.cells) { setOpacity(0); return }
  if (reducedMotion()) { setOpacity(.58); return }
  const start = performance.now(), total = 750, maxD = props.maxD
  const frame = now => {
    const t = Math.min(1, (now - start) / total), r = maxD * (1 - Math.pow(1 - t, 2)) + 1
    map.setPaintProperty('cells', 'fill-opacity', ['case', ['<=', ['get', 'd'], r], .58, 0])
    map.setPaintProperty('cells-edge', 'line-opacity', ['case', ['<=', ['get', 'd'], r], .9, 0])
    if (t < 1) wave = requestAnimationFrame(frame)
  }
  wave = requestAnimationFrame(frame)
}
function drawPins() {
  pins.forEach(p => p.marker.remove()); pins = []
  if (!ready) return
  props.points.forEach((p, i) => {
    const b = document.createElement('button')
    b.type = 'button'; b.className = 'tm-pin'; b.textContent = String(p.nr)
    b.style.setProperty('--i', i)
    b.setAttribute('aria-label', `Prüfpunkt ${p.nr}`)
    b.addEventListener('mouseenter', () => emit('hover', p.nr)); b.addEventListener('mouseleave', () => emit('hover', null))
    b.addEventListener('focus', () => emit('hover', p.nr)); b.addEventListener('blur', () => emit('hover', null))
    b.addEventListener('click', e => { e.stopPropagation(); emit('select', p.nr) })
    const wrap = document.createElement('div'); wrap.className = 'tm-pin-wrap'; wrap.appendChild(b)
    pins.push({nr: p.nr, el: b, marker: new maplibregl.Marker({element: wrap, anchor: 'bottom'}).setLngLat([p.longitude, p.latitude]).addTo(map)})
  })
  highlight()
}
function highlight() { pins.forEach(p => p.el.classList.toggle('on', p.nr === props.active)) }
function setFlows() {
  if (!ready) return
  map.getSource('flows').setData(props.flows ?? EMPTY)
  // The asked point's path is drawn strongest; the others stay visible but quieter.
  const op = props.flowActive == null ? 1 : ['case', ['==', ['get', 'nr'], props.flowActive], 1, .35]
  map.setPaintProperty('flow-lang', 'line-opacity', op); map.setPaintProperty('flow-kurz', 'line-opacity', op)
}
/** Camera onto one point's possible flow path (both scenarios), keeping the tilted 3D view. */
function fitFlow(nr) {
  const coords = (props.flows?.features ?? []).filter(f => f.properties.nr === nr && f.properties.art !== 'korridor').flatMap(f => f.geometry.coordinates)
  if (!map || !coords.length) return
  const lons = coords.map(c => c[0]), lats = coords.map(c => c[1])
  map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], {padding: 90, maxZoom: 16, pitch: 58, duration: reducedMotion() ? 0 : 1400})
}
function setBase() {
  if (!ready) return
  map.setLayoutProperty('ortho', 'visibility', props.base === 'ortho' ? 'visible' : 'none')
  map.setLayoutProperty('grau', 'visibility', props.base === 'ortho' ? 'none' : 'visible')
  map.setPaintProperty('hill', 'hillshade-exaggeration', props.base === 'ortho' ? .25 : .55)
}

function flyToPoint(nr) {
  const p = props.points.find(x => x.nr === nr)
  if (p) map?.flyTo({center: [p.longitude, p.latitude], zoom: Math.max(map.getZoom(), 15), pitch: 62, duration: reducedMotion() ? 0 : 1400, essential: true})
}
function overview() { fly() }
/** Image of the current map for the print view (rendered once, no permanent preserveDrawingBuffer). */
function snapshot() {
  return new Promise(resolve => {
    if (!map) return resolve(null)
    const timer = setTimeout(() => resolve(null), 1500)   // no frame (hidden tab): print the list without the image
    map.once('render', () => { clearTimeout(timer); try { resolve(map.getCanvas().toDataURL('image/jpeg', .85)) } catch { resolve(null) } })
    map.triggerRepaint()
  })
}
defineExpose({flyToPoint, overview, snapshot, fitFlow})

onMounted(() => {
  try {
    // With a place the camera starts there (far and tilted for the arrival), otherwise on all of Austria.
    const c = props.centre, z = c ? zoomFor(props.radiusM) : 6.3
    const start = c ? {center: [c.longitude, c.latitude], zoom: props.arrival ? z - 3.2 : z, pitch: 60, bearing: props.arrival ? 12 : -18} : {center: [13.35, 47.6], zoom: 6.3, pitch: 0}
    map = new maplibregl.Map({container: el.value, style: style(), ...start, maxPitch: 78, attributionControl: false,
      canvasContextAttributes: {antialias: true}, cooperativeGestures: props.embedded,
      locale: {'NavigationControl.ZoomIn': 'Vergrößern', 'NavigationControl.ZoomOut': 'Verkleinern', 'NavigationControl.ResetBearing': 'Nach Norden drehen', 'Map.Title': 'Karte',
        'CooperativeGesturesHandler.WindowsHelpText': 'Strg und Mausrad zum Zoomen', 'CooperativeGesturesHandler.MacHelpText': '⌘ und Scrollen zum Zoomen', 'CooperativeGesturesHandler.MobileHelpText': 'Mit zwei Fingern bewegen'}})
  } catch (e) { emit('failed', 'Die 3D-Karte braucht WebGL. Die Ergebnisliste funktioniert trotzdem.'); return }
  map.addControl(new maplibregl.NavigationControl({visualizePitch: true, showCompass: !props.embedded}), 'top-right')
  if (!props.embedded) map.addControl(new maplibregl.ScaleControl({unit: 'metric'}), 'bottom-right')
  map.addControl(new maplibregl.AttributionControl({compact: true}), 'bottom-right')
  // Set up on style load (not 'load', which waits for every tile of the tilted 3D view).
  map.once('style.load', () => {
    ready = true
    map.setTerrain({source: 'dem', exaggeration: 1.4})
    map.setSky({'sky-color': '#C9D9E0', 'horizon-color': '#F5F3EE', 'fog-color': '#F5F3EE', 'sky-horizon-blend': .6, 'horizon-fog-blend': .7, 'fog-ground-blend': .4})
    setBase(); setRing(); reveal(); drawPins(); setFlows()
    // Attribution stays available behind the (i) button; folded so it does not cover a small preview or the phone sheet.
    if (props.embedded || window.innerWidth < 760) map.getContainer().querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
    emit('ready')
  })
  padding()
  if (props.arrival && props.centre) fly()
  window.addEventListener('resize', padding)
  // Pins sit on the 3D terrain: once late terrain tiles have arrived, place them again on the final surface.
  map.on('idle', () => { pins.forEach(p => p.marker.setLngLat(p.marker.getLngLat())); centreMarker?.setLngLat(centreMarker.getLngLat()) })
  map.on('click', e => emit('pick', {longitude: e.lngLat.lng, latitude: e.lngLat.lat}))
  let warned = false
  map.on('error', () => { if (!warned) { warned = true; emit('failed', 'Ein Teil der Kartenkacheln fehlt (Internetverbindung?). Die Prüfstufen kommen vom lokalen Server.') } })
})
onBeforeUnmount(() => { window.removeEventListener('resize', padding); cancelAnimationFrame(wave); pins.forEach(p => p.marker.remove()); centreMarker?.remove(); map?.remove() })
watch(() => props.centre, () => { setRing(); fly() })
watch(() => props.radiusM, () => { setRing(); if (props.centre) map?.easeTo({zoom: zoomFor(props.radiusM), duration: reducedMotion() ? 0 : 600}) })
watch(() => props.cells, reveal)
watch(() => props.points, drawPins)
watch(() => props.active, highlight)
watch(() => props.base, setBase)
watch(() => [props.flows, props.flowActive], setFlows)
</script>

<template><div ref="el" class="tm" role="region" aria-label="3D-Karte des gewählten Umkreises. Die Ergebnisliste im Panel enthält dieselben Prüfpunkte als Text."></div></template>

<style>
.tm{position:absolute;inset:0;background:var(--paper-2)}
.tm .maplibregl-ctrl-group{border-radius:12px;box-shadow:var(--shadow)}
.tm .maplibregl-ctrl-group button{width:40px;height:40px}
.tm-centre{width:18px;height:18px;border-radius:50%;background:var(--ink);border:3px solid #fff;box-shadow:0 0 0 6px rgb(19 32 43 / .18)}
.tm-pin{width:34px;height:42px;border:0;padding:0 0 8px;background:none;color:#fff;font:650 15px/1 var(--f-display);font-stretch:112%;cursor:pointer;position:relative;
  animation:pin-drop .55s var(--ease) both;animation-delay:calc(450ms + var(--i) * 120ms)}
.tm-pin::before{content:'';position:absolute;inset:0 0 8px;border-radius:50% 50% 50% 50%/45% 45% 55% 55%;background:var(--ink);border:2px solid #fff;box-shadow:0 6px 14px -4px rgb(19 32 43 / .6);z-index:-1;transition:background-color .2s,transform .2s}
.tm-pin::after{content:'';position:absolute;left:50%;bottom:2px;width:8px;height:8px;background:var(--ink);transform:translateX(-50%) rotate(45deg);z-index:-2}
.tm-pin.on::before,.tm-pin:hover::before,.tm-pin:focus-visible::before{background:var(--stufe1);transform:scale(1.12)}
.tm-pin.on::after,.tm-pin:hover::after{background:var(--stufe1)}
@keyframes pin-drop{from{opacity:0;transform:translateY(-18px)}}
@media (prefers-reduced-motion:reduce){.tm-pin{animation:none}}
</style>
