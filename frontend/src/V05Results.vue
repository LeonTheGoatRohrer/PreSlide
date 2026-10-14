<script setup>
import {ref,computed,onMounted,onBeforeUnmount,watch,nextTick} from 'vue'
import * as maplibregl from 'maplibre-gl'
import SectionGuide from './SectionGuide.vue'
import 'maplibre-gl/dist/maplibre-gl.css'

const data=ref(null),error=ref(''),exampleId=ref(''),mode=ref('example'),selected=ref('Ereignishang')
const container=ref(null)
let map,markers=[],ready=false

const n=(v,d=3)=>v==null?'–':Number(v).toLocaleString('de-AT',{minimumFractionDigits:d,maximumFractionDigits:d})
const pct=v=>v==null?'–':Math.round(v*100)+' %'
const signed=(v,d=3)=>(v>0?'+':'')+n(v,d)
const date=s=>new Date(s+'T12:00:00').toLocaleDateString('de-AT',{day:'2-digit',month:'2-digit',year:'numeric'})
const state=s=>s?.replace('Kaernten','Kärnten').replace('Oberoesterreich','Oberösterreich').replace('Niederoesterreich','Niederösterreich')
const models={conditional_logit:'Bedingte logistische Regression',hist_gradient_boosting:'Gradient Boosting'}
const variants={static:'Gelände, Landbedeckung, Geologie',temporal:'nur Wetter',combined:'Gelände + Wetter'}
const lc={lc_forest:'Wald',lc_grass_shrub:'Grünland/Strauch',lc_agriculture:'Landwirtschaft',lc_open_bare:'Fels/offen',lc_artificial_water_other:'Siedlung/Wasser/Sonstiges'}
const geo={geo_carbonate:'Karbonat',geo_clastic_rock:'Klastisches Gestein',geo_unconsolidated:'Lockermaterial',geo_low_grade_metamorphic:'Niedriggradig metamorph',geo_crystalline_other:'Kristallin/Sonstiges'}
const feat={elevation:'Höhe',rain_max_hour_3d:'max. Stundenregen 3 T.',rain_sum_30d:'Regen 30 T.',twi:'Feuchteindex (TWI)',log1p_rain_sum_3d_x_slope:'Regen 3 T. × Neigung',rain_sum_7d:'Regen 7 T.',temperature_mean_1d:'Temperatur 1 T.',rain_sum_14d:'Regen 14 T.',slope:'Neigung',roughness_tri:'Rauigkeit',lc_forest:'Wald',tpi_150m:'Hanglage 150 m',tpi_500m:'Hanglage 500 m',temperature_mean_7d:'Temperatur 7 T.',rain_sum_60d:'Regen 60 T.',temperature_mean_60d:'Temperatur 60 T.',rain_sum_3d:'Regen 3 T.',rain_sum_1d:'Regen 1 T.'}

onMounted(async()=>{
  try{const r=await fetch('/api/results_v05');if(!r.ok)throw Error('V0.5-Ergebnisse nicht verfügbar ('+r.status+').');data.value=await r.json();exampleId.value=data.value.examples[0].id;await nextTick();initMap()}
  catch(e){error.value=e.message}
})
onBeforeUnmount(()=>{markers.forEach(m=>m.remove());map?.remove()})

const example=computed(()=>data.value?.examples.find(e=>e.id===exampleId.value))
const sortedSamples=computed(()=>example.value?[...example.value.samples].sort((a,b)=>a.rank_combined-b.rank_combined):[])
const rows=computed(()=>Object.entries(data.value?.purged||{}).map(([k,v])=>{const [m,f]=k.split('/');return {key:k,model:models[m],variant:variants[f],...v,unpurged:data.value.unpurged[k]}}))
const cv=computed(()=>data.value?.control_variants)
const variantBars=computed(()=>!cv.value?[]:[
  {key:'a_matched_5',label:'5 ähnliche (gematchte) Hänge',sub:'bisherige Aufgabe V0–V0.4 · 1 aus 6'},
  {key:'b_unmatched_first_5',label:'5 zufällige Umgebungshänge',sub:'1 aus 6'},
  {key:'c_unmatched_10',label:'10 zufällige Umgebungshänge',sub:'V0.5 · 1 aus 11'}].map(v=>({...v,static:cv.value[v.key].static.local_auc_units,combined:cv.value[v.key].combined.local_auc_units,top1:cv.value[v.key].combined.top1_units,chance:cv.value[v.key].chance.top1})))
const top1Note=computed(()=>{
  const v=variantBars.value;if(v.length<3)return ''
  const [a,,c]=v
  return `Beispiel „Platz 1 getroffen“: Bei 5 ähnlichen Hängen (6 Hänge) ist Zufall ${pct(a.chance)}, bei 10 zufälligen (11 Hänge) nur ${pct(c.chance)} – es gibt fast doppelt so viele Hänge, die man schlagen muss. Gemessen an der Zufallslinie ist ein Treffer von ${pct(c.top1)} also mehr wert, als die nackte Zahl vermuten lässt. Gleichzeitig sind zufällige Hänge leichter vom Rutschhang zu unterscheiden: Die lokale AUC steigt von ${n(a.combined)} auf ${n(c.combined)}, ohne dass das Modell besser wurde.`
})
const dist=computed(()=>data.value?.distributions)
const lcRows=computed(()=>!dist.value?[]:Object.keys(lc).map(k=>({label:lc[k],p:dist.value.categorical.land_cover_class.positive[k]||0,c:dist.value.categorical.land_cover_class.control[k]||0})))
const coef=computed(()=>Object.entries(data.value?.coefficients||{}).map(([k,v])=>({k:feat[k]||k,v})))
const maxCoef=computed(()=>Math.max(...coef.value.map(c=>Math.abs(c.v)),1))
const rankColor=r=>r<=1.5?'#c2410c':r<=3?'#ea8a3c':r<=6?'#9ca3af':'#4b5563'

function initMap(){
  map=new maplibregl.Map({container:container.value,attributionControl:false,center:[13.5,47.5],zoom:6.3,
    style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,maxzoom:17}},
      layers:[{id:'bg',type:'background',paint:{'background-color':'#f2f1ee'}},{id:'osm',type:'raster',source:'osm',paint:{'raster-saturation':-0.6,'raster-opacity':0.85}}]}})
  map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-right')
  map.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left')
  map.on('load',()=>{ready=true;draw()})
}
function circle(lon,lat,km){const pts=[];for(let i=0;i<=72;i++){const a=i/72*2*Math.PI;pts.push([lon+km/(111.32*Math.cos(lat*Math.PI/180))*Math.cos(a),lat+km/110.57*Math.sin(a)])}return pts}
function clear(){markers.forEach(m=>m.remove());markers=[];for(const id of ['ring','ringline'])if(map.getLayer(id))map.removeLayer(id);if(map.getSource('ring'))map.removeSource('ring')}
function draw(){
  if(!ready||!data.value)return
  clear()
  if(mode.value==='overview'){
    data.value.overview.forEach(e=>{const b=document.createElement('button');b.className='v05-dot';b.style.background=rankColor(e.rank_combined)
      b.title=`${e.id} · ${state(e.state)} · ${date(e.date)} · Rang ${n(e.rank_combined,1)} von 11`;b.setAttribute('aria-label',b.title)
      b.onclick=()=>{if(data.value.examples.some(x=>x.id===e.id)){exampleId.value=e.id;mode.value='example'}}
      markers.push(new maplibregl.Marker({element:b}).setLngLat([e.longitude,e.latitude]).addTo(map))})
    map.fitBounds([[9.4,46.3],[17.2,49.1]],{padding:20,duration:500});return
  }
  const e=example.value,p=e.samples[0]
  map.addSource('ring',{type:'geojson',data:{type:'FeatureCollection',features:[0.75,10].map(km=>({type:'Feature',properties:{},geometry:{type:'LineString',coordinates:circle(p.longitude,p.latitude,km)}}))}})
  map.addLayer({id:'ringline',type:'line',source:'ring',paint:{'line-color':'#002fa7','line-width':1.2,'line-dasharray':[3,3],'line-opacity':.7}})
  e.samples.forEach(s=>{const b=document.createElement('button');b.className='v05-pt'+(s.positive?' pos':'')+(s.name===selected.value?' sel':'')
    b.style.background=s.positive?'#002fa7':rankColor(s.rank_combined);b.textContent=s.positive?'P':s.name.replace('Kontrolle ','')
    b.title=`${s.name}: Modellrang ${n(s.rank_combined,1)} · ${n(s.elevation,0)} m · ${n(s.slope,1)}° · ${lc[s.land_cover_class]||'–'}`;b.setAttribute('aria-label',b.title)
    b.onclick=()=>{selected.value=s.name}
    markers.push(new maplibregl.Marker({element:b}).setLngLat([s.longitude,s.latitude]).addTo(map))})
  const r=circle(p.longitude,p.latitude,10.3),bb=new maplibregl.LngLatBounds();r.forEach(x=>bb.extend(x));map.fitBounds(bb,{padding:20,duration:500})
}
watch([exampleId,mode,selected],draw)
</script>

<template>
  <section id="v05" class="section results v05">
    <div class="section-heading"><div><p class="section-number">07 — Neue Version V0.5 (getrennt von V0–V0.4)</p><h2>Der gemeldete Hang gegen seine Umgebung.</h2></div></div>
    <p v-if="error" class="section-intro">{{error}}</p>
    <template v-if="data">
      <SectionGuide kind="Teil B · Ergebnisse" what="Dieselben Ereignisse, aber andere Vergleichshänge: zehn zufällige Hänge aus der Umgebung statt fünf möglichst ähnliche." see="Zuerst drei Balkenpaare mit derselben Auswertung bei verschiedenen Vergleichshängen, danach Unterschiede der Hänge, eine Karte, die Modelltabelle und die Gewichte des Modells." why="Zahlen aus verschiedenen Aufgaben lassen sich nicht direkt vergleichen. Mit mehr Vergleichshängen ändert sich der Zufallswert (Platz 1: 1 von 11 statt 1 von 6), und zufällige Hänge sind leichter zu unterscheiden als Zwillingshänge." take="Höhere AUC-Werte hier bedeuten keine bessere Vorhersage, sondern eine leichtere Aufgabe. Ein niedriger wirkender Platz-1-Wert ist bei 11 statt 6 Hängen besser, als er aussieht. Ein Zusatznutzen des Wetters ist auch hier nicht nachweisbar."/>
      <p class="section-intro">Bisher wurde jeder Rutschungshang mit fünf <b>möglichst ähnlichen</b> Nachbarhängen verglichen (gleiche Neigung, Höhe, Ausrichtung). V0.5 vergleicht ihn mit <b>zehn zufällig gezogenen</b> Hängen 0,75–10 km um ihn — ohne Ähnlichkeitsbedingung. Daten, Merkmale und Modell sind dieselben wie in V0.4; neu ist nur die Auswahl der Vergleichshänge.</p>
      <div class="v05-warn"><b>Wichtig zum Lesen:</b> Die höheren Werte bedeuten <b>keine bessere Vorhersage</b>. Zufällige Umgebungshänge sind leichter vom Rutschhang zu unterscheiden als ähnliche Zwillingshänge. Alle Ereignisse waren schon in V0.4 ausgewertet; dies ist eine erklärende Kreuzvalidierung, kein neuer unabhängiger Test.</div>

      <div class="stats" aria-label="V0.5-Umfang">
        <div><b>{{data.cohort.events}}</b><span>Ereignisgruppen</span></div>
        <div><b>{{data.cohort.samples.toLocaleString('de-AT')}}</b><span>Hänge insgesamt</span></div>
        <div><b>10</b><span>Vergleichshänge je Ereignis</span></div>
        <div><b>{{data.cohort.units}}</b><span>unabhängige Einheiten</span></div>
      </div>

      <h3>Die eigentliche Erklärung: dieselben Ereignisse, andere Vergleichshänge</h3>
      <p class="section-intro">Gleiches Modell (Gelände + Wetter), gleiche 418 Ereignisse, gleiche räumlich bereinigte Kreuzvalidierung. Nur die Vergleichshänge unterscheiden sich.</p>
      <div class="v05-variants">
        <div v-for="v in variantBars" :key="v.key" class="v05-variant">
          <div class="v05-vlabel"><b>{{v.label}}</b><span>{{v.sub}}</span></div>
          <div class="v05-bar"><span class="lbl">lokale AUC</span><div class="track"><div class="fill" :style="{width:(v.combined*100)+'%'}"></div><div class="chance" style="left:50%" title="Zufall 0,5"></div></div><b>{{n(v.combined)}}</b></div>
          <div class="v05-bar"><span class="lbl">Platz 1 getroffen</span><div class="track"><div class="fill top" :style="{width:(v.top1*100)+'%'}"></div><div class="chance" :style="{left:(v.chance*100)+'%'}" :title="'Zufall '+pct(v.chance)"></div></div><b>{{pct(v.top1)}}</b></div>
          <small>Zufall: AUC 0,5 · Platz 1 in {{pct(v.chance)}} der Fälle</small>
        </div>
      </div>
      <div class="v05-note"><b>Zahlen richtig einordnen</b><p>{{top1Note}}</p></div>
      <p class="section-intro">„Platz 1 getroffen“: Anteil der Ereignisse, bei denen das Modell den echten Rutschhang vor alle Vergleichshänge setzt. Der Sprung von der ersten zur zweiten Zeile entsteht allein durch leichtere Vergleichshänge — nicht durch ein besseres Modell.</p>

      <div class="howto">
        <h3>Ergebnis V0.5 (registrierter Hauptwert)</h3>
        <p>Bedingte logistische Regression, Gelände + Wetter: lokale AUC <b>{{n(data.primary.median)}}</b> (fünf Wiederholungen {{n(data.primary.range[0])}}–{{n(data.primary.range[1])}}). Zufall 0,5; die einfache Regel „steilerer Hang zuerst“ erreicht {{n(data.primary.slope_rule)}}.</p>
        <p><b>Wetter hilft nicht nachweisbar:</b> Gelände + Wetter minus nur Gelände = {{signed(data.primary.combined_minus_static_rep1_bootstrap.mean)}} (95 %: {{signed(data.primary.combined_minus_static_rep1_bootstrap.ci95[0])}} bis {{signed(data.primary.combined_minus_static_rep1_bootstrap.ci95[1])}}), in allen fünf Wiederholungen negativ.</p>
      </div>

      <h3>Woran sich die Hänge unterscheiden</h3>
      <div class="v05-dist">
        <div class="howto"><p>Höhe (Median)</p><p><b>{{n(dist.numeric.elevation.positive['50%'],0)}} m</b> Rutschhang · <b>{{n(dist.numeric.elevation.control['50%'],0)}} m</b> Umgebung</p>
          <p>Neigung (Median)</p><p><b>{{n(dist.numeric.slope.positive['50%'],1)}}°</b> Rutschhang · <b>{{n(dist.numeric.slope.control['50%'],1)}}°</b> Umgebung</p>
          <small>Gemeldete Rutschungen liegen tiefer, aber kaum steiler als der Hintergrund.</small></div>
        <div><p class="v05-legend"><span class="sw p"></span>Rutschhänge <span class="sw c"></span>Umgebungshänge</p>
          <div v-for="r in lcRows" :key="r.label" class="v05-lc"><span>{{r.label}}</span>
            <div class="pair"><div class="b p" :style="{width:(r.p*100)+'%'}"></div><div class="b c" :style="{width:(r.c*100)+'%'}"></div></div><b>{{pct(r.p)}} / {{pct(r.c)}}</b></div></div>
      </div>
      <p class="section-intro">Rutschhänge liegen deutlich seltener im Wald und häufiger auf Grünland und Siedlungsflächen. Das kann echte Anfälligkeit sein — aber auch daran liegen, dass Rutschungen an Straßen und Häusern eher entdeckt und gemeldet werden. Beides lässt sich mit diesen Daten nicht trennen.</p>

      <h3>Karte</h3>
      <div class="v05-controls">
        <div class="segmented" aria-label="Kartenansicht"><button :class="{active:mode==='example'}" @click="mode='example'">Ein Ereignis mit 10 Vergleichshängen</button><button :class="{active:mode==='overview'}" @click="mode='overview'">Alle {{data.overview.length}} Ereignisse</button></div>
        <div v-if="mode==='example'" class="case-picker"><label for="v05ex">Beispiel</label><select id="v05ex" v-model="exampleId"><option v-for="e in data.examples" :key="e.id" :value="e.id">{{e.id}} · {{state(e.state)}} · {{date(e.date)}}</option></select></div>
      </div>
      <div class="v05-mapwrap">
        <div ref="container" class="v05-map" aria-label="Karte der V0.5-Ereignisse und Vergleichshänge"></div>
        <div class="map-key v05-key"><template v-if="mode==='example'"><span class="sw" style="background:#002fa7"></span>Rutschhang (P) · Vergleichshänge nach Modellrang: <span class="sw" style="background:#c2410c"></span>1 <span class="sw" style="background:#ea8a3c"></span>2–3 <span class="sw" style="background:#9ca3af"></span>4–6 <span class="sw" style="background:#4b5563"></span>7–11 · gestrichelt: 0,75- und 10-km-Ring</template>
          <template v-else>Farbe = Rang des echten Rutschhangs unter seinen 11 Hängen: <span class="sw" style="background:#c2410c"></span>1 <span class="sw" style="background:#ea8a3c"></span>2–3 <span class="sw" style="background:#9ca3af"></span>4–6 <span class="sw" style="background:#4b5563"></span>7–11</template></div>
        <div class="map-attribution">Karte © OpenStreetMap-Mitwirkende</div>
      </div>
      <p v-if="mode==='overview'" class="section-intro">Jeder Punkt ist ein gemeldetes Ereignis. Die Ränge stammen von Modellen, die das Ereignis nicht im Training hatten (Wiederholung 1). Klick auf ein Beispiel-Ereignis öffnet die Einzelansicht.</p>
      <template v-if="mode==='example'&&example">
        <p class="section-intro">Ereignis {{example.id}} ({{state(example.state)}}, {{date(example.date)}}): Das Modell setzt den echten Rutschhang auf <b>Rang {{n(example.rank_combined,1)}} von 11</b> (nur Gelände: Rang {{n(example.rank_static,1)}}). Beispiele sind nach Bundesland aus den Ereignis-IDs gewählt, nicht nach gutem Ergebnis.</p>
        <table class="v05-table"><thead><tr><th>Modellrang</th><th>Hang</th><th>Entfernung</th><th>Höhe</th><th>Neigung</th><th>Landbedeckung</th><th>Geologie</th><th>Regen 7 T.</th><th>Regen 30 T.</th></tr></thead>
          <tbody><tr v-for="s in sortedSamples" :key="s.name" :class="{pos:s.positive,sel:s.name===selected}" @click="selected=s.name">
            <td>{{n(s.rank_combined,1)}}</td><td>{{s.name}}</td><td>{{s.positive?'–':n(s.distance_to_positive_m/1000,1)+' km'}}</td><td>{{n(s.elevation,0)}} m</td><td>{{n(s.slope,1)}}°</td><td>{{lc[s.land_cover_class]||'–'}}</td><td>{{geo[s.geology_class]||'–'}}</td><td>{{n(s.rain_sum_7d,1)}} mm</td><td>{{n(s.rain_sum_30d,1)}} mm</td></tr></tbody></table>
      </template>

      <h3>Alle Modelle</h3>
      <table class="v05-table"><thead><tr><th>Modell</th><th>Merkmale</th><th>lokale AUC</th><th>Spanne</th><th>Platz 1</th><th>Top 3</th><th>mittl. Rang</th><th>ohne räuml. Bereinigung</th></tr></thead>
        <tbody><tr v-for="r in rows" :key="r.key"><td>{{r.model}}</td><td>{{r.variant}}</td><td>{{n(r.local_auc_units)}}</td><td>{{n(r.min_local_auc_units)}}–{{n(r.max_local_auc_units)}}</td><td>{{pct(r.top1_units)}}</td><td>{{pct(r.top3_units)}}</td><td>{{n(r.mean_rank_units,2)}}</td><td>{{n(r.unpurged)}}</td></tr>
          <tr class="ref"><td>Referenz</td><td>steilerer Hang zuerst</td><td>{{n(data.slope_rule.local_auc_units)}}</td><td>–</td><td>{{pct(data.slope_rule.top1_units)}}</td><td>{{pct(data.slope_rule.top3_units)}}</td><td>{{n(data.slope_rule.mean_rank_units,2)}}</td><td>–</td></tr>
          <tr class="ref"><td>Zufall</td><td>–</td><td>0,500</td><td>–</td><td>{{pct(data.chance.top1)}}</td><td>{{pct(data.chance.top3)}}</td><td>6,00</td><td>–</td></tr></tbody></table>
      <p class="section-intro">Jede unabhängige Einheit zählt gleich. „Räumlich bereinigt“: Trainingsgebiete, die näher als 1 km an einem geprüften Hang liegen, werden aus dem Training entfernt. „Nur Wetter“ liegt hier über Zufall, weil Temperatur und Regen von der Höhe abhängen — das ist kein reines Wettersignal.</p>

      <h3>Worauf sich das Modell am stärksten stützt</h3>
      <div class="v05-coef"><div v-for="c in coef" :key="c.k" class="row"><span>{{c.k}}</span><div class="axis"><div class="b" :class="c.v<0?'neg':'posv'" :style="c.v<0?{right:'50%',width:(Math.abs(c.v)/maxCoef*50)+'%'}:{left:'50%',width:(c.v/maxCoef*50)+'%'}"></div></div><b>{{signed(c.v,2)}}</b></div></div>
      <p class="section-intro">Standardisierte Gewichte des Modells auf allen Daten: positiv = spricht eher für den Rutschhang, negativ = eher für einen Vergleichshang. Das zeigt, worauf sich das Modell stützt — nicht, was Rutschungen verursacht.</p>
    </template>
  </section>
</template>

<style scoped>
.v05 h3{margin-top:2rem}
.v05-warn{border-left:4px solid #c2410c;background:#fff7ed;padding:.8rem 1rem;margin:1rem 0;font-size:.95rem}
.v05-note{border-left:4px solid #002fa7;background:#eef2fc;padding:.8rem 1rem;margin:1rem 0;font-size:.95rem;line-height:1.55}.v05-note b{display:block;margin-bottom:.25rem}.v05-note p{margin:0}
.v05-variants{display:grid;gap:.8rem;margin:.6rem 0}
.v05-variant{border:1px solid var(--line,#ddd);padding:.7rem .9rem;border-radius:6px}
.v05-vlabel{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin-bottom:.4rem}.v05-vlabel span{color:#666;font-size:.85rem}
.v05-bar{display:grid;grid-template-columns:9.5rem 1fr 3.6rem;align-items:center;gap:.6rem;margin:.25rem 0;font-size:.9rem}
.v05-bar .lbl{color:#555}.v05-bar b{text-align:right}
.track{position:relative;height:.9rem;background:#eef0f4;border-radius:3px}
.fill{position:absolute;inset:0 auto 0 0;background:#002fa7;border-radius:3px}.fill.top{background:#c2410c}
.chance{position:absolute;top:-3px;bottom:-3px;width:2px;background:#111}
.v05-variant small{color:#666}
.v05-dist{display:grid;grid-template-columns:1fr 1.4fr;gap:1.2rem;align-items:start}
.v05-legend{font-size:.85rem;color:#555}.sw{display:inline-block;width:.8rem;height:.8rem;border-radius:2px;margin:0 .25rem 0 .6rem;vertical-align:-1px}
.sw.p,.b.p{background:#002fa7}.sw.c,.b.c{background:#b8c0cc}
.v05-lc{display:grid;grid-template-columns:11rem 1fr 6.5rem;gap:.5rem;align-items:center;font-size:.88rem;margin:.3rem 0}.v05-lc b{text-align:right;font-weight:600}
.pair .b{height:.45rem;margin:1px 0;border-radius:2px}
.v05-controls{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;align-items:end;margin:.5rem 0}
.v05-mapwrap{position:relative}.v05-map{height:460px;border:1px solid var(--line,#ddd);border-radius:6px}
.v05-key{position:static;margin-top:.4rem;font-size:.82rem}
.v05-table{width:100%;border-collapse:collapse;margin:.5rem 0 1rem;font-size:.9rem}
.v05-table th,.v05-table td{padding:.35rem .5rem;border-bottom:1px solid var(--line,#ddd);text-align:left}
.v05-table tr.pos td{background:#e8edfb;font-weight:600}.v05-table tr.sel td{outline:1px solid #002fa7}.v05-table tr.ref td{color:#666}
.v05-coef .row{display:grid;grid-template-columns:12rem 1fr 3.5rem;gap:.6rem;align-items:center;font-size:.88rem;margin:.25rem 0}.v05-coef b{text-align:right}
.axis{position:relative;height:.7rem;border-left:0;background:linear-gradient(90deg,transparent calc(50% - 1px),#999 calc(50% - 1px),#999 calc(50% + 1px),transparent calc(50% + 1px))}
.axis .b{position:absolute;top:0;bottom:0;border-radius:2px}.axis .posv{background:#c2410c}.axis .neg{background:#4b5563}
:global(.v05-pt){width:22px;height:22px;border-radius:50%;border:2px solid #fff;color:#fff;font:600 11px/18px system-ui;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.4);padding:0}
:global(.v05-pt.pos){width:28px;height:28px;font-size:13px;line-height:24px;z-index:2}
:global(.v05-pt.sel){outline:3px solid #111}
:global(.v05-dot){width:10px;height:10px;border-radius:50%;border:1px solid #fff;padding:0;cursor:pointer}
@media (max-width:700px){.v05-dist{grid-template-columns:1fr}.v05-bar{grid-template-columns:6.5rem 1fr 3rem;font-size:.8rem}.v05-lc{grid-template-columns:7rem 1fr 5.5rem;font-size:.8rem}
  .v05-table{display:block;overflow-x:auto;font-size:.8rem}.v05-coef .row{grid-template-columns:8rem 1fr 3rem;font-size:.8rem}.v05-map{height:360px}}
</style>
