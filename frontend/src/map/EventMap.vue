<script setup>
// Austria overview of the documented events (GET /api/pruefgebiete): one dot per event, filtered by year.
import {ref, watch, onMounted, onBeforeUnmount} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
maplibregl.setWorkerUrl(workerUrl)
const props = defineProps({points: {type: Array, required: true}, year: {type: Number, default: null}})
const el = ref(null)
let map = null, ready = false
const COLORS = {'Lockergesteinsrutschung': '#3D5C38', 'Hangmure': '#B0331D', 'Hangmure gemischt': '#E9973A'}
function data() {
  return {type: 'FeatureCollection', features: props.points.map(p => ({type: 'Feature', properties: {jahr: Number(p.tag.slice(0, 4)), klasse: p.klasse},
    geometry: {type: 'Point', coordinates: [p.lon, p.lat]}}))}
}
function filter() {
  if (!ready) return
  map.setFilter('ev', props.year ? ['==', ['get', 'jahr'], props.year] : null)
}
onMounted(() => {
  try {
    map = new maplibregl.Map({container: el.value, center: [13.35, 47.62], zoom: 5.9, attributionControl: false, cooperativeGestures: true, dragRotate: false, pitchWithRotate: false,
      locale: {'CooperativeGesturesHandler.WindowsHelpText': 'Strg und Mausrad zum Zoomen', 'CooperativeGesturesHandler.MacHelpText': '⌘ und Scrollen zum Zoomen', 'CooperativeGesturesHandler.MobileHelpText': 'Mit zwei Fingern bewegen'},
      style: {version: 8, sources: {grau: {type: 'raster', tiles: ['https://mapsneu.wien.gv.at/basemap/bmapgrau/normal/google3857/{z}/{y}/{x}.png'], tileSize: 256, maxzoom: 19, attribution: 'Karte: basemap.at (CC BY 4.0)'}},
        layers: [{id: 'paper', type: 'background', paint: {'background-color': '#EAE7DF'}}, {id: 'grau', type: 'raster', source: 'grau', paint: {'raster-opacity': 1, 'raster-saturation': -.4, 'raster-contrast': .15}}]}})
  } catch { return }
  map.addControl(new maplibregl.AttributionControl({compact: true}), 'bottom-right')
  map.once('style.load', () => {
    ready = true
    map.addSource('ev', {type: 'geojson', data: data()})
    map.addLayer({id: 'ev', type: 'circle', source: 'ev', paint: {'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 3.2, 10, 6], 'circle-color': ['match', ['get', 'klasse'], ...Object.entries(COLORS).flat(), '#45535F'],
      'circle-stroke-color': '#fff', 'circle-stroke-width': .8, 'circle-opacity': .85}})
    filter()
    map.getContainer().querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
  })
})
onBeforeUnmount(() => map?.remove())
watch(() => props.year, filter)
defineExpose({COLORS})
</script>
<template><div ref="el" class="evmap" role="img" :aria-label="`Karte Österreichs mit ${points.length} dokumentierten Rutschungen${year ? ' im Jahr ' + year : ''}`"></div></template>
<style>.evmap{position:absolute;inset:0}</style>
