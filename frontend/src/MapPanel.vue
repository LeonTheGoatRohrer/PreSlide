<script setup>
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
maplibregl.setWorkerUrl(workerUrl)
const props=defineProps({event:Object,selected:String})
const emit=defineEmits(['select'])
const container=ref(null),warning=ref('')
let map,markers=[],ready=false
function fit(){
  if(!map||!props.event)return
  const bounds=new maplibregl.LngLatBounds()
  props.event.samples.forEach(p=>bounds.extend([p.longitude,p.latitude]))
  map.fitBounds(bounds,{padding:70,duration:550,maxZoom:13})
}
function draw(){
  if(!ready||!props.event)return
  markers.forEach(m=>m.remove());markers=[]
  const e=props.event,p=e.samples[0]
  if(map.getLayer('terrain'))map.removeLayer('terrain')
  if(map.getSource('terrain'))map.removeSource('terrain')
  map.addSource('terrain',{type:'image',url:e.terrain_url,coordinates:e.terrain_corners})
  map.addLayer({id:'terrain',type:'raster',source:'terrain',paint:{'raster-opacity':1,'raster-fade-duration':0}},map.getLayer('connections')?'connections':undefined)
  const lines={type:'FeatureCollection',features:e.samples.slice(1).map(s=>({type:'Feature',properties:{},geometry:{type:'LineString',coordinates:[[p.longitude,p.latitude],[s.longitude,s.latitude]]}}))}
  if(map.getSource('connections'))map.getSource('connections').setData(lines)
  else{
    map.addSource('connections',{type:'geojson',data:lines})
    map.addLayer({id:'connections',type:'line',source:'connections',paint:{'line-color':'#002fa7','line-width':1.2,'line-opacity':.5,'line-dasharray':[3,3]}})
  }
  e.samples.forEach((s,i)=>{
    const b=document.createElement('button');b.className='map-point'+(s.positive?' positive':'')
    b.textContent=s.positive?'P':String(i);b.title=`${s.name}: ${s.slope}° Neigung, ${s.elevation} m Höhe`
    b.setAttribute('aria-label',b.title);b.onclick=()=>emit('select',s.name)
    markers.push(new maplibregl.Marker({element:b}).setLngLat([s.longitude,s.latitude]).addTo(map))
  })
  highlight();fit()
}
function highlight(){markers.forEach((m,i)=>m.getElement().classList.toggle('selected',props.event.samples[i].name===props.selected))}
onMounted(()=>{
  map=new maplibregl.Map({container:container.value,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#f7f7f8'}}]},center:[13.5,47.5],zoom:6,attributionControl:false})
  map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right')
  map.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left')
  map.on('load',()=>{ready=true;draw()})
  map.on('error',()=>{warning.value='Die Geländekarte konnte nicht vollständig geladen werden. Die Messwerte stehen in der Tabelle.'})
})
watch(()=>props.event,draw);watch(()=>props.selected,highlight)
onBeforeUnmount(()=>{markers.forEach(m=>m.remove());map?.remove()})
</script>
<template>
  <div class="map-wrap">
    <div ref="container" class="terrain-map" aria-label="Interaktive Karte: Ereignishang und fünf lokale Kontrollen"></div>
    <button class="map-reset" @click="fit">Alle Hänge zeigen</button>
    <div class="map-key"><span class="point-key positive"></span>Ereignishang <span class="point-key"></span>Kontrollen</div>
    <p v-if="warning" class="map-warning" role="alert">{{warning}}</p>
    <div class="map-attribution">Gelände: Mapzen · © offene Daten Österreichs · EU-DEM / Copernicus · USGS</div>
  </div>
</template>
