<script setup>
import {ref,computed,onMounted,onBeforeUnmount,watch} from 'vue'
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import {useResource} from './useResource.js'
import WirkungsketteView from './wirkungskette/WirkungsketteView.vue'
maplibregl.setWorkerUrl(workerUrl)

// Ereignisübersicht (read-only) plus die Wirkungskette des Demogebiets (eigene Komponente unter ./wirkungskette).
const {data,error,loading,reload}=useResource('/api/pruefgebiete')
const container=ref(null),mapWarning=ref('')
const shown=ref({Hangmure:true,'Hangmure gemischt':true,Lockergesteinsrutschung:true})
const classes=[
  {key:'Hangmure',color:'#b3261e',text:'Hangmure'},
  {key:'Hangmure gemischt',color:'#d88a00',text:'Hangmure gemischt mit Rutschung'},
  {key:'Lockergesteinsrutschung',color:'#5b6b7a',text:'Lockergesteinsrutschung (keine Mure)'},
]
const n=v=>v==null?'–':Number(v).toLocaleString('de-AT')
const date=s=>s?new Date(s+'T12:00:00').toLocaleDateString('de-AT',{day:'2-digit',month:'2-digit',year:'numeric'}):'–'
const dateSpan=c=>c.first_day===c.last_day?date(c.first_day):`${date(c.first_day)} bis ${date(c.last_day)}`
const topClusters=computed(()=>(data.value?.cluster||[]).slice(0,10))
const counts=computed(()=>data.value?.zaehlung||{})
const processCounts=computed(()=>data.value?.prozessklassen||{})

let map,ready=false,disposed=false
function layerId(key){return 'pts-'+key.replace(/\s+/g,'-')}
function geojson(){
  return {type:'FeatureCollection',features:(data.value?.punkte||[]).map(p=>({type:'Feature',properties:{klasse:p.klasse,id:p.id,tag:p.tag,cluster:p.cluster},geometry:{type:'Point',coordinates:[p.lon,p.lat]}}))}
}
function draw(){
  if(!ready||!data.value)return
  if(!map.getSource('events'))map.addSource('events',{type:'geojson',data:geojson()})
  else map.getSource('events').setData(geojson())
  for(const c of classes){
    const id=layerId(c.key)
    if(!map.getLayer(id)){
      map.addLayer({id,type:'circle',source:'events',filter:['==',['get','klasse'],c.key],
        paint:{'circle-radius':['interpolate',['linear'],['zoom'],5,3,10,6],'circle-color':c.color,'circle-stroke-color':'#ffffff','circle-stroke-width':1,'circle-opacity':.85}})
    }
  }
  fit()
  applyFilter()
}
function fit(){
  if(!map||!data.value?.punkte?.length)return
  const bounds=new maplibregl.LngLatBounds()
  data.value.punkte.forEach(p=>bounds.extend([p.lon,p.lat]))
  map.fitBounds(bounds,{padding:40,duration:0,maxZoom:9})
}
function applyFilter(){
  if(!map||!ready)return
  for(const c of classes){
    const id=layerId(c.key)
    if(map.getLayer(id))map.setLayoutProperty(id,'visibility',shown.value[c.key]?'visible':'none')
  }
}
watch(data,draw)
watch(shown,applyFilter,{deep:true})
onMounted(()=>{
  map=new maplibregl.Map({container:container.value,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#f7f7f8'}}]},center:[14.5,47.6],zoom:6,locale:{'NavigationControl.ZoomIn':'Vergrößern','NavigationControl.ZoomOut':'Verkleinern'},attributionControl:false})
  map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right')
  map.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left')
  map.on('load',()=>{ready=true;if(!disposed)draw()})
  map.on('error',()=>{mapWarning.value='Der Kartenhintergrund konnte nicht geladen werden. Die Ereignispunkte bleiben über die Tabellen lesbar.'})
})
onBeforeUnmount(()=>{disposed=true;map?.remove()})
</script>
<template>
  <div class="pg">
    <header class="pg-head">
      <p class="pg-kicker">Demonstration · retrospektiv · ein Demogebiet</p>
      <h1 tabindex="-1">Prüfgebiete und mögliche Fließwege</h1>
      <p class="pg-lead">Diese Seite führt an einem Demogebiet vom Hang bis zur Straße: relative Prüfpunkte aus dem Gelände, ein Auslaufszenario von einem Anrisspunkt und die Infrastruktur, die in diesem Szenario liegt. Darunter steht, wo die dokumentierten Ereignisse im Datensatz liegen.</p>
    </header>

    <section class="pg-block" aria-labelledby="pg-steps">
      <h2 id="pg-steps">Die Frage in drei Schritten</h2>
      <ol class="pg-steps">
        <li><strong>Prüfpunkte aus Hangbedingungen</strong><span class="pg-status is-demo">Demonstration</span><p>Relative Rangfolge der Hangzellen im gewählten Umkreis aus dem eingefrorenen V0.4-Geländemodell. Eine Rangfolge, keine Eintrittsangabe.</p></li>
        <li><strong>Fließweg vom Anrisspunkt</strong><span class="pg-status is-ill">Unvalidierte Illustration</span><p>Abwärtsroute nach steilstem Gefälle und vier Reichweitenannahmen aus der Literatur. Das Inventar enthält keine Auslaufreferenzen, deshalb ist nichts davon geprüft.</p></li>
        <li><strong>Prüfpriorität</strong><span class="pg-status">Bewusst nicht kombiniert</span><p>Beide Teile bleiben getrennt sichtbar. Eine Gesamtstufe wäre erst sinnvoll, wenn mindestens eine Komponente an unabhängigen Referenzen geprüft ist.</p></li>
      </ol>
    </section>

    <section class="pg-block pg-chain">
      <WirkungsketteView />
    </section>

    <section class="pg-block" aria-labelledby="pg-data">
      <h2 id="pg-data">Datenlage</h2>
      <p v-if="loading" class="pg-note">Ereignisübersicht wird geladen …</p>
      <p v-else-if="error" class="pg-warn" role="alert">{{error}} <button type="button" @click="reload">Erneut laden</button></p>
      <template v-else-if="data">
        <dl class="pg-stats">
          <div><dt>Positive Ereignisse</dt><dd>{{n(counts.positive_ereignisse)}}</dd></div>
          <div><dt>davon Hangmuren</dt><dd>{{n(counts.hangmuren)}}</dd></div>
          <div><dt>Zeitliche Episoden</dt><dd>{{n(counts.episoden)}}</dd></div>
          <div><dt>Räumliche Cluster (5 km)</dt><dd>{{n(counts.cluster)}}</dd></div>
        </dl>
        <h3>Gemeldete Prozesse</h3>
        <ul class="pg-proc">
          <li v-for="c in classes" :key="c.key"><span class="pg-dot" :style="{background:c.color}"></span>{{c.text}}: <strong>{{n(processCounts[c.key])}}</strong></li>
        </ul>
        <h3>Dichteste Cluster</h3>
        <p class="pg-note">Ein Cluster kann zu einem einzigen Sturm gehören. Die Zahl der Ereignisse ist dann keine Zahl unabhängiger Beobachtungen.</p>
        <div class="pg-table-wrap">
          <table class="pg-table">
            <thead><tr><th scope="col">Cluster</th><th scope="col">Zeitraum</th><th scope="col">Ereignisse</th><th scope="col">davon Hangmuren</th><th scope="col">Lage (Breite, Länge)</th></tr></thead>
            <tbody>
              <tr v-for="c in topClusters" :key="c.id">
                <td>{{c.id}}</td><td>{{dateSpan(c)}}</td><td>{{n(c.n_positive)}}</td><td>{{n(c.n_hangmure)}}</td><td>{{c.lat.toFixed(3)}}, {{c.lon.toFixed(3)}}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <h3>Hinweise zur Lesart</h3>
        <ul class="pg-caveats"><li v-for="h in data.hinweise" :key="h">{{h}}</li></ul>
      </template>
    </section>

    <section class="pg-block" aria-labelledby="pg-map">
      <h2 id="pg-map">Karte der dokumentierten Ereignisse</h2>
      <fieldset class="pg-filter">
        <legend>Anzeigen</legend>
        <label v-for="c in classes" :key="c.key"><input type="checkbox" v-model="shown[c.key]"> <span class="pg-dot" :style="{background:c.color}"></span>{{c.text}}</label>
      </fieldset>
      <div ref="container" class="pg-map" aria-label="Karte der dokumentierten Ereignispunkte"></div>
      <p v-if="mapWarning" class="pg-warn" role="alert">{{mapWarning}}</p>
      <p class="pg-note">Jeder Punkt ist eine dokumentierte Ereignisstelle mit Positionsunsicherheit, kein Anrisspolygon.</p>
    </section>

  </div>
</template>
<style scoped>
.pg{max-width:1240px;margin:0 auto;padding:0 16px;color:inherit}
.pg-head{padding:32px 0 8px}
.pg-kicker{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;opacity:.7;margin:0 0 6px}
.pg-head h1{font-size:1.9rem;margin:0 0 10px}
.pg-lead{font-size:1.02rem;max-width:62ch;margin:0}
.pg-block{margin:28px 0;padding-top:8px;border-top:1px solid rgba(127,127,127,.25)}
.pg-block h2{font-size:1.3rem;margin:8px 0 12px}
.pg-block h3{font-size:1.02rem;margin:18px 0 8px}
.pg-note{font-size:.92rem;opacity:.85;max-width:70ch}
.pg-warn{color:#8a1c12;font-size:.92rem}
.pg-steps{padding-left:0;list-style:none;display:grid;gap:12px;counter-reset:s}
.pg-steps li{border:1px solid rgba(127,127,127,.3);border-radius:8px;padding:12px 14px;display:grid;gap:4px}
.pg-status{justify-self:start;font-size:.78rem;padding:2px 8px;border-radius:999px;background:rgba(127,127,127,.18)}
.pg-steps p{margin:0;font-size:.95rem}
.pg-status.is-demo{background:#7a1e481f;color:#7a1e48}
.pg-status.is-ill{background:#002fa71a;color:#002fa7}
.pg-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0}
.pg-stats div{border:1px solid rgba(127,127,127,.3);border-radius:8px;padding:10px 12px}
.pg-stats dt{font-size:.82rem;opacity:.75}
.pg-stats dd{margin:4px 0 0;font-size:1.5rem;font-variant-numeric:tabular-nums}
.pg-proc{list-style:none;padding:0;margin:0;display:grid;gap:6px}
.pg-dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:middle;border:1px solid #fff}
.pg-table-wrap{overflow-x:auto}
.pg-table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
.pg-table th,.pg-table td{text-align:left;padding:6px 10px;border-bottom:1px solid rgba(127,127,127,.25);white-space:nowrap}
.pg-caveats{padding-left:20px;font-size:.92rem;display:grid;gap:4px}
.pg-filter{border:0;padding:0;margin:0 0 10px;display:flex;flex-wrap:wrap;gap:14px;font-size:.92rem}
.pg-filter legend{font-size:.92rem;padding:0;margin-bottom:4px;opacity:.8}
.pg-filter label{display:inline-flex;align-items:center;cursor:pointer}
.pg-map{height:420px;width:100%;border-radius:8px;overflow:hidden;border:1px solid rgba(127,127,127,.3)}
@media (max-width:480px){.pg-head h1{font-size:1.55rem}.pg-map{height:340px}}
</style>
