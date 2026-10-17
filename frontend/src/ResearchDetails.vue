<script setup>
import {ref,computed,onMounted} from 'vue'
import MapPanel from './MapPanel.vue'
import StabilityFigures from './StabilityFigures.vue'
import InfoTip from './InfoTip.vue'
import EventExplorer from './EventExplorer.vue'
import SectionGuide from './SectionGuide.vue'
import SatelliteResults from './SatelliteResults.vue'
import {explain} from './metricDefinitions.js'
const props=defineProps({mode:{type:String,default:'method'},initialCase:String})
const emit=defineEmits(['show-case'])
const summary=ref(null),bundle=ref(null),cases=ref([]),event=ref(null),selectedId=ref(''),selectedPoint=ref('Ereignishang')
const loading=ref(true),caseLoading=ref(false),error=ref(''),weatherKind=ref('rain_mm'),model=ref('logistic_regression'),view=ref('test'),day=ref(0)
let request=0
const names={logistic_regression:'Logistische Regression',random_forest:'Random Forest',gradient_boosting:'Gradient Boosting'}
const featureNames={static:'Nur Gelände',temporal:'Nur Wetter',combined:'Gelände + Wetter'}
const partitionNames={train:'Training',validation:'Validierung',test:'Test'}
const reasonNames={insufficient_controls:'Zu wenige passende Kontrollen',missing_weather_values:'Fehlende Wetterwerte',implausible_weather_values:'Negative Niederschlagswerte',positive_dem_slope_below_minimum:'Neigung unter 5°'}
const n=(value,d=3)=>Number(value).toLocaleString('de-AT',{minimumFractionDigits:d,maximumFractionDigits:d})
const date=s=>new Date(s+'T12:00:00').toLocaleDateString('de-AT',{day:'2-digit',month:'2-digit',year:'numeric'})
const state=s=>s?.replace('Kaernten','Kärnten').replace('Oberoesterreich','Oberösterreich').replace('Niederoesterreich','Niederösterreich')
async function get(url){const r=await fetch(url);if(!r.ok)throw Error('Daten konnten nicht geladen werden ('+r.status+').');return r.json()}
async function selectCase(){
  const id=++request;caseLoading.value=true;error.value=''
  try{const result=await get('/api/cases/'+selectedId.value);if(id!==request)return;event.value=result;selectedPoint.value='Ereignishang';day.value=0}
  catch(e){if(id===request)error.value=e.message}
  finally{if(id===request)caseLoading.value=false}
}
async function initialize(){
  loading.value=true;error.value=''
  try{[summary.value,cases.value,bundle.value]=await Promise.all([get('/api/summary'),get('/api/cases'),get('/api/results')]);if(!cases.value.length)throw Error('Keine Demonstrationsbeispiele verfügbar.');selectedId.value=cases.value.some(c=>c.id===props.initialCase)?props.initialCase:cases.value[0].id;await selectCase()}
  catch(e){error.value=e.message}finally{loading.value=false}
}
onMounted(initialize)
async function showCase(id){emit('show-case',id)}
// Dynamic, conservative reading of the currently displayed values (text from metricDefinitions, numbers from the bundle).
const reading=(term,value,ctx)=>explain(term,value,ctx).reading
const focused= computed(()=>event.value?.samples.find(s=>s.name===selectedPoint.value))
const daily=computed(()=>{
  if(!event.value)return[]
  const dates=[...new Set(event.value.history.map(h=>h.date))].sort()
  return dates.map(d=>{
    const rows=event.value.history.filter(h=>h.date===d),p=rows.find(h=>h.name==='Ereignishang'),c=rows.filter(h=>h.name!=='Ereignishang')
    return{date:d,positive:p[weatherKind.value],control:c.reduce((s,h)=>s+h[weatherKind.value],0)/c.length,hours:p.hours}
  })
})
const chart=computed(()=>{
  const vals=daily.value.flatMap(d=>[d.positive,d.control]);if(!vals.length)return {lo:0,hi:1,ticks:[],p:'',c:''}
  const lo=weatherKind.value==='rain_mm'?0:Math.floor(Math.min(...vals)/5)*5
  const hi=Math.max(lo+1,Math.ceil(Math.max(...vals)/5)*5)
  const x=i=>46+i*690/Math.max(1,daily.value.length-1),y=v=>175-(v-lo)/(hi-lo)*145
  return{lo,hi,x,y,p:daily.value.map((d,i)=>`${x(i)},${y(d.positive)}`).join(' '),c:daily.value.map((d,i)=>`${x(i)},${y(d.control)}`).join(' '),ticks:[0,1,2,3].map(i=>({v:lo+(hi-lo)*i/3,y:y(lo+(hi-lo)*i/3)}))}
})
const dayInfo=computed(()=>daily.value[Math.min(day.value,daily.value.length-1)])
const results=computed(()=>{
  const rows=view.value==='test'?summary.value?.models:summary.value?.geographic_holdout.models
  return rows?.filter(r=>r.model===model.value)||[]
})
const order=['static','temporal','combined']
const combinedTest=computed(()=>results.value.find(r=>r.features==='combined'))
const byFeatures=rows=>(rows||[]).filter(r=>r.model===model.value).sort((a,b)=>order.indexOf(a.features)-order.indexOf(b.features))
const originalPairwise=computed(()=>Object.fromEntries(byFeatures(bundle.value?.original_test.models).map(r=>[r.features,r])))
const stabilityRows=computed(()=>byFeatures(bundle.value?.stability_v02.models))
const combinedStability=computed(()=>stabilityRows.value.find(r=>r.features==='combined'))
const stabilityDelta=computed(()=>(bundle.value?.stability_v02.weather_delta||[]).filter(r=>r.model===model.value&&['average_precision','within_group_auc'].includes(r.metric)))
const nullRows=computed(()=>{
  const rows=(bundle.value?.null_v03?.rows||[]).filter(r=>r.model===model.value)
  return rows.sort((a,b)=>a.statistic.localeCompare(b.statistic))
})
const learning=computed(()=>(bundle.value?.diagnostics_v02.learning_curve||[]).filter(r=>r.model===(model.value==='gradient_boosting'?'random_forest':model.value)))
const windows=computed(()=>(bundle.value?.diagnostics_v02.window_ablation||[]).filter(r=>r.features==='temporal'))
const storms=computed(()=>(bundle.value?.diagnostics_v02.storm_sensitivity||[]).filter(r=>r.model===model.value&&r.features==='combined'))
const caseRank=computed(()=>{
  const c=bundle.value?.cases?.[event.value?.id];if(!c)return null
  return{...c,rows:byFeatures(c.rankings)}
})
const statNames={within_group_auc:'AUC innerhalb der Gruppe',average_precision:'Average Precision'}
function nullLabel(s){
  if(s.startsWith('delta_combined_minus_static_'))return 'Zugewinn durch Wetter · '+statNames[s.replace('delta_combined_minus_static_','')]
  const [f,...m]=s.split('_');return featureNames[f]+' · '+statNames[m.join('_')]
}
const windowNames={immediate:'1–3 Tage',short:'7–14 Tage',antecedent:'30–60 Tage',full:'alle Fenster'}
const methodNames={event_weighted:'jedes Ereignis gleich',dependency_balanced:'jede Abhängigkeitsgruppe gleich'}
function nullScale(r){const lo=Math.min(r.null_p05,r.observed),hi=Math.max(r.null_p95,r.observed),pad=(hi-lo)*.35||.05;return[lo-pad,hi+pad]}
const nullPos=(r,v)=>{const[a,b]=nullScale(r);return((v-a)/(b-a)*100)+'%'}
const nullBand=r=>{const[a,b]=nullScale(r);return{left:((r.null_p05-a)/(b-a)*100)+'%',width:((r.null_p95-r.null_p05)/(b-a)*100)+'%'}}
const signed=(v,d=3)=>(v>0?'+':'')+n(v,d)
const importance=computed(()=>summary.value?.models.find(r=>r.model===model.value&&r.features==='combined')?.validation_permutation_importance?.slice().sort((a,b)=>b.mean-a.mean).slice(0,5)||[])
function featureLabel(f){
  return f.replace('rain_sum_','Niederschlag · ').replace('rain_max_hour_','Max. Stundenregen · ').replace('temperature_mean_','Temperatur · ').replace(/ 1d$/,' 1 Tag').replace(/(\d+)d$/,'$1 Tage').replace('elevation','Höhe').replace('slope','Neigung').replace('aspect_sin','Exposition (sin)').replace('aspect_cos','Exposition (cos)')
}
</script>
<template><div class="research-details">
<div v-if="loading" class="loading" role="status">Reale Beispieldaten werden geladen …</div>
<div v-if="error" class="error" role="alert">{{error}} <button @click="initialize">Erneut laden</button></div>
<template v-if="summary && !loading">
<template v-if="mode==='method'">      <section id="experiment" class="section experiment">
        <div class="section-heading"><div><p class="section-number">Reales Beispiel · eingefrorene Baseline</p><h2>Ein Hang im Vergleich.</h2></div><div class="case-picker"><label for="case">Demonstrationsbeispiel</label><select id="case" v-model="selectedId" @change="selectCase" :disabled="caseLoading"><option v-for="c in cases" :value="c.id" :key="c.id">{{c.id}} · {{state(c.state)}} · {{date(c.event_date)}}</option></select></div></div>
        <SectionGuide kind="Teil A · Verstehen" what="Ein Hang mit dokumentierter Rutschung wird mit fünf ähnlichen Nachbarhängen verglichen – alle sechs zum selben Stichtag." see="Links die Karte: P ist der Ereignishang, die Zahlen sind seine Kontrollen. Rechts Neigung, Höhe und Exposition des gewählten Punkts, darunter die Tabelle mit den Abweichungen." why="Die Kontrollen sehen dem Ereignishang topographisch ähnlich. Ein Unterschied im Modell kann also nicht einfach daher kommen, dass ein Hang steiler ist." take="Jede Gruppe ist ein kleines Experiment: ein Hang mit Rutschung gegen fünf ohne dokumentiertes Ereignis – gleiches Datum, ähnliches Gelände."/>
        <p class="section-intro">Fünf räumlich verteilte Beispiele aus dem ausgewerteten Datensatz. Wähle einen Punkt auf der Karte oder einen Hang in der Tabelle.</p>
        <div v-if="event" class="case-grid" :class="{'is-loading':caseLoading}" :aria-busy="caseLoading">
          <div class="map-column"><MapPanel :event="event" :selected="selectedPoint" @select="selectedPoint=$event"/><div class="map-caption"><span>Reales Gelände · 30-m-Raster · Nord oben</span><span>{{state(event.state)}} / {{date(event.event_date)}}</span></div></div>
          <aside class="case-detail"><p class="eyebrow">{{event.id}} · {{partitionNames[event.partition]}}</p><h3>{{focused?.name}}</h3><p class="point-status">{{focused?.positive?'Dokumentiertes Rutschungsereignis':'Lokaler Kontrollhang · Pseudo-negativ'}}</p>
            <dl class="terrain-values"><div><dt>Neigung</dt><dd>{{n(focused?.slope,1)}}<small>°</small></dd></div><div><dt>Höhe</dt><dd>{{n(focused?.elevation,0)}}<small>m</small></dd></div><div><dt>Exposition</dt><dd>{{n(focused?.aspect,0)}}<small>°</small></dd></div></dl>
            <div class="date-rule"><span>Gemeinsamer Stichtag</span><strong>{{date(event.event_date)}}</strong><p>Alle Wettermerkmale enden vor Beginn dieses Tages. Keine Messung vom Ereignistag geht ein.</p></div>
            <p class="uncertainty">Positionskategorie der Quelle: bis {{event.position_category_upper_m}} m. Keine unabhängig bestätigte Vermessungsgenauigkeit.</p>
          </aside>
        </div>
        <div v-if="event" class="table-scroll"><table class="matching-table"><caption>Topographische Übereinstimmung der fünf Kontrollen</caption><thead><tr><th>Hang</th><th>Neigung</th><th>Höhe</th><th>Exposition</th><th>Entfernung</th><th><InfoTip term="slopeDifference" label="Neigungsdifferenz"/></th></tr></thead><tbody><tr v-for="s in event.samples" :key="s.name" :class="{active:selectedPoint===s.name}"><th><button @click="selectedPoint=s.name">{{s.name}}</button></th><td>{{n(s.slope,1)}}°</td><td>{{n(s.elevation,0)}} m</td><td>{{n(s.aspect,0)}}°</td><td>{{s.positive?'—':n(s.distance_m/1000,1)+' km'}}</td><td>{{s.positive?'—':n(s.slope_difference,1)+'°'}}</td></tr></tbody></table></div>
        <details class="disclosure"><summary>Historische Modellränge dieses Beispiels</summary><label class="model-choice">Modell <select v-model="model"><option v-for="(label,key) in names" :value="key" :key="key">{{label}}</option></select></label><div v-if="caseRank" class="case-rank"><div><h3>Wo landet der betroffene Hang?</h3><p>{{names[model]}} · Rang des Ereignishangs unter allen sechs Hängen der Gruppe. {{caseRank.score_source==='original_test_model'?'Bewertet vom ursprünglichen Modell, das diese Gruppe nie gesehen hat (Testgruppe).':'Bewertet ausschließlich von Modellen, die diese Gruppe nicht im Training hatten (Median aus fünf gruppierten Wiederholungen).'}} Modell hier wählbar; historische Baseline.</p></div>
          <div class="rank-rows"><div v-for="r in caseRank.rows" :key="r.features" class="rank-row"><span>{{featureNames[r.features]}}</span><div class="rank-dots" :aria-label="`${r.controls_beaten} von 5 Kontrollen übertroffen`"><i v-for="(name,i) in r.order" :key="name" :class="{pos:name==='Ereignishang'}" :title="`${i+1}. ${name}`"></i></div><InfoTip term="controlsBeaten" :value="r.controls_beaten" :label="`${r.controls_beaten} / 5`"/></div><small>Punkte: alle sechs Hänge nach Modellwert geordnet, links der höchste. Blau = Ereignishang. Einzelfälle sind keine Evidenz; maßgeblich sind die gebündelten Ergebnisse.</small></div></div></details>
      </section>

      <section id="wetter" class="section weather" v-if="event">
        <div class="section-heading"><div><p class="section-number">03 — Die Vorgeschichte</p><h2>Dasselbe Wetterfenster.</h2></div><div class="segmented" aria-label="Wettervariable"><button :class="{active:weatherKind==='rain_mm'}" @click="weatherKind='rain_mm'">Niederschlag</button><button :class="{active:weatherKind==='temperature_c'}" @click="weatherKind='temperature_c'">Temperatur</button></div></div>
        <SectionGuide kind="Teil A · Verstehen" what="Das Wetter der 60 Tage vor dem Ereignis – für den Ereignishang und als Mittel seiner fünf Kontrollen." see="Blaue Linie = Ereignishang, graue Linie = Kontrollen. Mit dem Regler wählst du einen Tag; rechts steht der Tageswert beider." why="Das sind die Rohdaten, aus denen die Wettermerkmale des Modells entstehen (Summen über 1 bis 60 Tage). Man sieht, wie ähnlich oder verschieden die Wetterverläufe der Hänge wirklich sind." take="Liegen beide Linien dicht beieinander, steckt im Wetter wenig Unterscheidendes – genau das prüft die Auswertung im nächsten Abschnitt."/>
        <div class="weather-grid"><div class="chart-area"><div class="chart-legend"><span class="line-key blue"></span>Ereignishang <span class="line-key"></span>Mittel der fünf Kontrollen <span class="chart-unit">{{weatherKind==='rain_mm'?'mm / erfasster Tag':'°C · Tagesmittel'}}</span></div>
          <svg class="weather-chart" viewBox="0 0 770 214" role="img" :aria-label="weatherKind==='rain_mm'?'Niederschlagsverlauf vor dem Ereignis':'Temperaturverlauf vor dem Ereignis'"><g v-for="t in chart.ticks" :key="t.v"><line x1="46" x2="736" :y1="t.y" :y2="t.y" stroke="#dedee2"/><text x="36" :y="t.y+4" text-anchor="end">{{n(t.v,0)}}</text></g><polyline :points="chart.c" fill="none" stroke="#9999a1" stroke-width="2"/><polyline :points="chart.p" fill="none" stroke="#002fa7" stroke-width="2.5"/><line v-if="dayInfo" :x1="chart.x(day)" :x2="chart.x(day)" y1="25" y2="175" stroke="#002fa7" stroke-dasharray="3 4" opacity=".5"/><text x="46" y="203">{{daily[0]?.date&&date(daily[0].date)}}</text><text x="736" y="203" text-anchor="end">{{daily.at(-1)?.date&&date(daily.at(-1).date)}}</text></svg>
          <label class="sr-only" for="day">Tag in der Wetterhistorie auswählen</label><input id="day" class="day-slider" type="range" min="0" :max="daily.length-1" v-model.number="day"/>
        </div><aside class="weather-readout" v-if="dayInfo"><span>{{date(dayInfo.date)}}</span><strong>{{n(dayInfo.positive,1)}}<small>{{weatherKind==='rain_mm'?' mm':' °C'}}</small></strong><p>Ereignishang</p><div><span>Kontrollen im Mittel</span><b>{{n(dayInfo.control,1)}} {{weatherKind==='rain_mm'?'mm':'°C'}}</b></div><small>{{dayInfo.hours}} erfasste Stunden an diesem Tag</small></aside></div>
        <p class="footnote">GeoSphere Austria · INCA, 1 km / 1 h. Randstunden werden vorsorglich ausgelassen. Die nominalen 60 Tage enthalten {{n(bundle?.dataset.retained_hours_60d,0)}} Stunden; die Kurve zeigt daraus berechnete Tageswerte. Historische Analyse, keine damalige Echtzeitprognose.</p>
      </section>

</template>
<template v-else>      <section id="historische-ergebnisse" class="section results">
        <div class="section-heading"><div><p class="section-number">Historisch · Baseline V0–V0.3</p><h2>Signal mit Grenzen.</h2></div><div class="case-picker"><label for="model">Modell vergleichen</label><select id="model" v-model="model"><option v-for="(label,key) in names" :value="key" :key="key">{{label}}</option></select></div></div>
        <SectionGuide kind="Teil B · Ergebnisse" what="Wie gut ordnet ein Modell die sechs Hänge einer Gruppe, sodass der echte Rutschungshang vorne steht?" see="Je Merkmalssatz (nur Gelände, nur Wetter, Gelände + Wetter) eine Zeile, mit der Zufallsreferenz daneben. Die Reiter wechseln zwischen vier getrennten Auswertungen." why="Entscheidend ist nicht eine einzelne Zahl, sondern: Liegt sie über dem Zufall – und hilft das Wetter zusätzlich zum Gelände?" take="Ein belegter Zusatznutzen des Wetters wurde bisher nicht gefunden. Einzelne gute Werte sind bei so wenigen unabhängigen Gruppen kein Beweis."/>
        <div class="howto" aria-labelledby="howto-title"><h3 id="howto-title">So lesen Sie die Ergebnisse</h3><ol>
          <li><b>Ereignis:</b> ein dokumentierter Rutschungshang mit Datum, aus dem österreichischen Ereignisinventar.</li>
          <li><b>Kontrollen:</b> fünf ähnliche Hänge in der Nähe, ohne dokumentiertes Ereignis, untersucht für denselben Zeitraum.</li>
          <li><b>Aufgabe des Modells:</b> die sechs Hänge einer Gruppe so ordnen, dass der echte Rutschungshang vorne steht – ohne diese Gruppe je im Training gesehen zu haben.</li>
          <li><b>Zufall:</b> Ohne jede Information stünde der Rutschungshang im Mittel auf Rang 3,5 und schlüge 2,5 von 5 Kontrollen; AUC-Werte lägen bei 0,5.</li>
          <li><b>Kein Risiko in Prozent:</b> Modellwerte sind Vergleichswerte innerhalb dieses Experiments, keine Wahrscheinlichkeit, dass ein Hang rutscht.</li>
          <li><b>Gelände vs. Gelände + Wetter:</b> Der Vergleich zeigt, ob das Wetter vor dem Ereignis zusätzlich zur Geländeform hilft. Genau das ist die Forschungsfrage.</li>
        </ol><p class="howto-note">Das <span class="infotip-demo">ⓘ</span>-Symbol neben Zahlen und Fachbegriffen erklärt sie – per Mauszeiger, Tastatur (Tab) oder Antippen.</p></div>
        <div class="result-context"><p>Drei getrennte Auswertungen, die nicht vermischt werden: der <strong>ursprüngliche Test</strong> (einmalig, vorab festgelegt), die <strong>Stabilitätsanalyse</strong> auf den Entwicklungsdaten (wiederholte gruppierte Aufteilungen) und <strong>Diagnosen</strong>. Ein robuster Zusatznutzen des Wetters ist bisher <strong>nicht belegt</strong>.</p>
          <div class="segmented tabs" role="group" aria-label="Historische Auswertung"><button :class="{active:view==='test'}" @click="view='test'">Ursprünglicher Test</button><button :class="{active:view==='geographic'}" @click="view='geographic'">Steiermark separat</button><button :class="{active:view==='stability'}" @click="view='stability'">Stabilität V0.2</button><button :class="{active:view==='diagnostics'}" @click="view='diagnostics'">Diagnosen</button></div></div>

        <template v-if="view==='test'||view==='geographic'">
          <p class="test-caption">{{view==='test'?`${summary.split.test.events} Ereignisse in nur ${summary.split.test.clusters} unabhängigen Testgruppen · kein Nachjustieren am Test · hohe Zufallsschwankung`: `${summary.geographic_holdout.test_events} Ereignisse in der Steiermark · ${summary.geographic_holdout.train_events} Trainingsereignisse außerhalb · 20 km Abstand`}}</p>
          <div class="table-scroll"><table class="metrics-table"><caption>{{names[model]}} · vollständiger Merkmalsvergleich</caption><thead><tr><th>Merkmale</th><th><InfoTip term="averagePrecision"/> <small>Zufallsreferenz {{n(bundle?.original_test.chance_average_precision)}}</small></th><th><InfoTip term="rocAuc"/> <small>Zufallsreferenz 0,500</small></th><th><InfoTip term="withinGroupAuc"/> <small>Ereignishang gegen Kontrollen · Zufall 0,500</small></th><th v-if="view==='test'"><InfoTip term="controlsBeaten" label="Übertroffene Kontrollen"/> <small>Mittel, von 5 · Zufall 2,5</small></th><th v-if="view==='test'"><InfoTip term="f1"/></th></tr></thead><tbody><tr v-for="r in results" :key="r.features"><th>{{featureNames[r.features]}}</th><td><div class="metric-bar"><span :style="{width:r.test.average_precision*100+'%'}"></span><b>{{n(r.test.average_precision)}}</b></div></td><td>{{n(r.test.roc_auc)}}</td><td>{{n(r.test.within_group_auc)}}</td><td v-if="view==='test'">{{n(originalPairwise[r.features]?.mean_controls_beaten,2)}}</td><td v-if="view==='test'">{{n(r.test.f1)}}</td></tr></tbody></table></div>
          <p v-if="combinedTest" class="reading"><b>Lesehilfe, Gelände + Wetter:</b> AUC innerhalb der Gruppe {{n(combinedTest.test.within_group_auc)}} – {{reading('withinGroupAuc',combinedTest.test.within_group_auc)}} Average Precision {{n(combinedTest.test.average_precision)}} – {{reading('averagePrecision',combinedTest.test.average_precision,{chance:bundle?.original_test.chance_average_precision})}}</p>
          <p class="footnote">Der ursprüngliche Test enthält nur {{summary.split.test.clusters}} unabhängige Gruppen. Einzelne günstige Werte (etwa beim Random Forest) wiederholen sich in der Stabilitätsanalyse nicht und sind deshalb nicht als bestätigtes Signal zu lesen.</p>
        </template>

        <template v-if="view==='stability'&&bundle">
          <p class="test-caption">{{bundle.stability_v02.events}} Entwicklungsereignisse · {{bundle.stability_v02.clusters}} Abhängigkeitsgruppen · {{bundle.stability_v02.repetitions}} × {{bundle.stability_v02.folds}} gruppierte Aufteilungen · {{bundle.stability_v02.fits}} Trainingsläufe · ursprünglicher Test ausgeschlossen</p>
          <div class="table-scroll"><table class="metrics-table"><caption>{{names[model]}} · Median <InfoTip term="repetitionRange" label="[Minimum – Maximum] über fünf Wiederholungen"/></caption><thead><tr><th>Merkmale</th><th><InfoTip term="averagePrecision"/> <small>Zufallsreferenz {{n(bundle.stability_v02.chance_average_precision)}}</small></th><th><InfoTip term="withinGroupAuc"/> <small>Zufall 0,500</small></th><th><InfoTip term="controlsBeaten" label="Übertroffene Kontrollen"/> <small>Mittel, von 5 · Zufall 2,5</small></th><th><InfoTip term="firstPlaceRate"/> <small>Zufall 16,7 %</small></th></tr></thead><tbody><tr v-for="r in stabilityRows" :key="r.features"><th>{{featureNames[r.features]}}</th><td>{{n(r.average_precision.median)}} <small class="range">[{{n(r.average_precision.min)}} – {{n(r.average_precision.max)}}]</small></td><td>{{n(r.within_group_auc.median)}} <small class="range">[{{n(r.within_group_auc.min)}} – {{n(r.within_group_auc.max)}}]</small></td><td>{{n(r.mean_controls_beaten.median,2)}} <small class="range">[{{n(r.mean_controls_beaten.min,2)}} – {{n(r.mean_controls_beaten.max,2)}}]</small></td><td>{{n(r.first_place_rate.median*100,0)}} %</td></tr></tbody></table></div>
          <p v-if="combinedStability" class="reading"><b>Lesehilfe, Gelände + Wetter:</b> AUC innerhalb der Gruppe im Median {{n(combinedStability.within_group_auc.median)}} – {{reading('withinGroupAuc',combinedStability.within_group_auc.median)}} Ereignishang auf Platz 1: {{n(combinedStability.first_place_rate.median*100,0)}} % – {{reading('firstPlaceRate',combinedStability.first_place_rate.median)}}</p>
          <div class="delta-row"><div v-for="d in stabilityDelta" :key="d.metric"><span><InfoTip term="weatherDelta" :value="d.median" :label="`Gelände + Wetter minus nur Gelände · ${statNames[d.metric]}`"/></span><strong>{{signed(d.median)}}</strong><small>verbessert in {{d.improved_repetitions}} von {{d.repetitions}} Wiederholungen · Spanne {{signed(d.minimum)}} bis {{signed(d.maximum)}}</small></div></div>
          <div v-if="nullRows.length" class="null-block"><h3>Was würde dieselbe Auswertung ohne jede Information ergeben? <InfoTip term="nullBand" label=""/></h3><p>Nullreferenz: In jeder Gruppe wird ein zufälliger der sechs Hänge zum „Ereignis“ erklärt, dann läuft exakt dieselbe gruppierte Auswertung ({{bundle.null_v03.draws}} Zufallsziehungen). Liegt der beobachtete Wert (blau) innerhalb des grauen Bereichs, ist er von Zufall nicht unterscheidbar.</p>
            <div v-for="r in nullRows" :key="r.statistic" class="null-row"><span>{{nullLabel(r.statistic)}}</span><div class="null-scale"><i class="band" :style="nullBand(r)"></i><i class="obs" :style="{left:nullPos(r,r.observed)}"></i></div><b>{{n(r.observed)}}</b><small>Zufall 90 %: {{n(r.null_p05)}} – {{n(r.null_p95)}}</small></div>
            <p v-if="bundle.null_v03.conclusion" class="null-conclusion">{{bundle.null_v03.conclusion}}</p><p class="footnote">Einschränkung: Echte Ereignishänge sind zugleich das Zentrum ihrer Kontrollsuche; diese Struktur fehlt in der Nullreferenz. Abweichungen beim reinen Geländemodell können daher aus dem Design statt aus Rutschungsinformation stammen.</p></div>
          <p class="footnote">Wiederholungen nutzen dieselben {{bundle.stability_v02.events}} Ereignisse und sind keine unabhängigen Studien. Keine Modellparameter wurden verändert.</p>
          <StabilityFigures />
        </template>

        <template v-if="view==='diagnostics'&&bundle">
          <div class="diag-grid">
            <div><h3>Lernkurve</h3><p>Mehr Trainingsgruppen, gleiche Prüfgruppen ({{names[model==='gradient_boosting'?'random_forest':model]}}, Gelände + Wetter). Ein deutlicher Anstieg würde nahelegen, dass mehr Daten derselben Art helfen.</p><table class="mini"><thead><tr><th><InfoTip term="learningFraction" label="Anteil"/></th><th><InfoTip term="averagePrecision" label="AP"/></th><th><InfoTip term="withinGroupAuc" label="AUC i. d. G."/></th></tr></thead><tbody><tr v-for="r in learning" :key="r.fraction"><td>{{n(r.fraction*100,0)}} %</td><td>{{n(r.average_precision.median)}}</td><td>{{n(r.within_group_auc.median)}}</td></tr></tbody></table></div>
            <div><h3>Wetterfenster</h3><p>Nur Wetter, logistische Regression, je Zeitskala.</p><table class="mini"><thead><tr><th>Fenster</th><th><InfoTip term="averagePrecision" label="AP"/></th><th><InfoTip term="withinGroupAuc" label="AUC i. d. G."/></th></tr></thead><tbody><tr v-for="r in windows" :key="r.window"><td>{{windowNames[r.window]}}</td><td>{{n(r.average_precision.median)}}</td><td>{{n(r.within_group_auc.median)}}</td></tr></tbody></table></div>
            <div><h3>Dominieren wenige Unwetter?</h3><p>Größte <InfoTip term="dependencyGroups" :value="bundle.diagnostics_v02.largest_cluster_events" label="Abhängigkeitsgruppe"/>: {{bundle.diagnostics_v02.largest_cluster_events}} von {{bundle.stability_v02.events}} Entwicklungsereignissen. Gelände + Wetter, unterschiedlich gewichtet:</p><table class="mini"><thead><tr><th>Gewichtung</th><th><InfoTip term="averagePrecision" label="AP"/></th><th><InfoTip term="withinGroupAuc" label="AUC i. d. G."/></th></tr></thead><tbody><tr v-for="r in storms" :key="r.method"><td>{{methodNames[r.method]}}</td><td>{{n(r.average_precision.median)}}</td><td>{{n(r.within_group_auc.median)}}</td></tr></tbody></table></div>
            <div><h3>Unterscheiden sich die Wetterdaten überhaupt?</h3><p>{{bundle.diagnostics_v02.weather_distinguishability.same_positive_control_cell_pairs}} von {{bundle.diagnostics_v02.weather_distinguishability.total_pairs}} Ereignis-Kontroll-Paaren teilen dieselbe 1-km-Wetterzelle. Die Werte unterscheiden sich also messbar – ob 1 km ausreicht, um hangspezifische Prozesse abzubilden, ist damit nicht gezeigt.</p></div>
          </div>
        </template>

        <div class="result-bottom"><div><h3>Was misst dieser Vergleich?</h3><p>Average Precision bewertet die Rangfolge bei wenigen positiven Fällen. Die AUC innerhalb einer Gruppe prüft direkt, ob der betroffene Hang höher eingestuft wird als seine fünf Kontrollen.</p><p>Die Modelle liefern <InfoTip term="modelScore" label="Vergleichswerte"/> für dieses Experiment. Daraus lässt sich keine reale Rutschungswahrscheinlichkeit ableiten.</p></div><div class="importance"><h3>Merkmale, auf die sich das Modell stützt <InfoTip term="permutationImportance" label=""/></h3><p>Ursprüngliches Modell: Änderung der Average Precision beim Durchmischen eines Merkmals in der Validierung. Kleine oder negative Werte zeigen keinen verlässlichen Beitrag.</p><div v-for="f in importance" :key="f.feature" class="importance-row"><span>{{featureLabel(f.feature)}}</span><b>{{f.mean>0?'+':''}}{{n(f.mean)}}</b></div><small>Kombiniertes Modell · keine Aussage über Ursachen.</small></div></div>
      </section>

      <section id="einzelfaelle" class="section events" v-if="bundle?.event_explorer">
        <div class="section-heading"><div><p class="section-number">05 — Einzelne Ereignisse</p><h2>Wo das Modell richtig liegt – und wo nicht.</h2></div><div class="case-picker"><label for="model-explorer">Modell</label><select id="model-explorer" v-model="model"><option v-for="(label,key) in names" :value="key" :key="key">{{label}}</option></select></div></div>
        <SectionGuide kind="Teil B · Ergebnisse" what="Dieselbe Auswertung, aufgeschlüsselt Ereignis für Ereignis." see="Pro Ereignis den Rang des echten Hangs unter seinen sechs Hängen und ob das Wetter diesen Rang verbessert hat." why="So erkennt man, ob gute Ergebnisse breit verteilt sind oder von wenigen Fällen oder Unwettern kommen." take="Einzelfälle veranschaulichen, beweisen aber nichts. Maßgeblich sind die gebündelten historischen Gesamtauswertungen."/>
        <p class="section-intro">Für jedes der {{bundle.event_explorer.events.length}} Ereignisse: Welchen Rang erhielt der echte Rutschungshang unter seinen sechs Hängen, und hat das Wetter geholfen? Nur Bewertungen von Modellen, die die jeweilige Gruppe nicht im Training hatten. Zufall: im Mittel Rang 3,5 und 2,5 geschlagene Kontrollen.</p>
        <EventExplorer :explorer="bundle.event_explorer" :model="model" :names="names" :feature-names="featureNames" @show-case="showCase"/>
      </section>

<details class="disclosure"><summary>Satellitenbilder vor und nach bekannten Ereignissen (Pipeline B, getrennt)</summary><SatelliteResults/></details>

<details class="disclosure"><summary>Historische Datenprüfung und Quellen</summary>      <section id="methodik" class="section methodology">
        <div class="section-heading"><div><p class="section-number">Historisch · Qualitätsprüfung der Baseline</p><h2>Jeder Ausschluss bleibt sichtbar.</h2></div><span class="count-label">{{bundle?.dataset.candidates}} Kandidaten → {{summary.complete_events}} vollständige Gruppen</span></div>
        <SectionGuide kind="Teil C · Hintergrund" what="Wie der Datensatz entstand: welche Kandidaten aussortiert wurden, nach welchen festen Regeln, und woher die Daten stammen." see="Links die Ausschlussgründe mit Anzahl, rechts die festen Regeln des Experiments, darunter Quellen und Lizenzhinweise." why="Glaubwürdigkeit: Nichts wurde erfunden, still korrigiert oder nachträglich gelockert, um bessere Zahlen zu bekommen." :take="`${bundle?.dataset.candidates} geprüfte Kandidaten ergaben ${summary.complete_events} vollständige Gruppen aus einem Ereignis und fünf Kontrollen.`"/>
        <div class="method-grid"><div><div class="exclusion" v-for="(count,reason) in summary.exclusions" :key="reason"><span>{{reasonNames[reason]||reason}}</span><b>{{count}}</b></div><p class="footnote">Keine fehlenden Messwerte erfunden. Keine negativen Niederschläge still korrigiert. Keine Auswahlgrenze gelockert.</p></div><div class="safeguards"><h3>Feste Regeln des Experiments</h3><ul><li>6.000 lokale Kandidaten je Ereignis, fünf passende Kontrollhänge.</li><li>Maximal 5° Neigungs-, 150 m Höhen- und 45° Expositionsunterschied.</li><li>Mindestens 400 m zwischen Kontrollen; Ausschlussbereiche um bekannte Rutschungen.</li><li>Ereignis und Kontrollen bleiben gemeinsam in Training, Validierung oder Test.</li><li>Zusätzliche Gruppen für nahe Ereignisdaten und räumliche Überschneidungen.</li></ul></div></div>
        <div class="source-note"><h3>Quelle, Unsicherheit und Nutzung</h3><p><strong>© GeoSphere Austria.</strong> Die detaillierte Ereignisquelle ist als „Naturgefahren Test“ bezeichnet. Ihre spezifische Weiterverwendungslizenz wurde im Audit nicht identifiziert. Die Auslegung der Qualitätsfelder und Ereigniszeitpunkte ist nicht offiziell bestätigt.</p><p>Lokaler, nicht kommerzieller Forschungsprototyp. Diese Ansicht enthält fünf abgeleitete Beispielgruppen, aggregierte Ergebnisse und anonymisierte Ranglisten je Ereignis (ohne Koordinaten und Quellkennungen). Der Rohdatenbestand wird weder veröffentlicht noch als Massenexport angeboten. Kontrollhänge sind nicht nachweislich stabil.</p><p>Geländedaten: Mapzen / Skadi, offene Daten Österreichs, EU-DEM / Copernicus und USGS. Wetter: GeoSphere Austria / INCA, CC BY 4.0. Die Wetterlizenz wird nicht auf den Ereignisbestand übertragen.</p></div>
      </section>
</details></template></template></div></template>
<style>
.why-lead{font-size:18px;line-height:1.6;max-width:900px;margin:0 0 34px;padding-left:18px;border-left:3px solid var(--blue);letter-spacing:-.2px}
.howto{border:1px solid var(--line);padding:20px 24px;margin:6px 0 30px;background:#fafafc}.howto h3{margin:0 0 10px;font-size:15px;font-weight:600}
.howto ol{margin:0;padding-left:20px;display:grid;grid-template-columns:1fr 1fr;gap:8px 40px;font-size:13px;line-height:1.6}.howto b{font-weight:600}
.howto-note{font-size:11px;color:var(--muted);margin:14px 0 0}.infotip-demo{color:var(--blue)}
.reading{font-size:12.5px;line-height:1.7;background:#f3f5fb;padding:10px 14px;margin:18px 0 0;max-width:1050px}.reading b{font-weight:600}
@media(max-width:720px){.howto ol{grid-template-columns:1fr}.why-lead{font-size:16px}}
@media(max-width:420px){.masthead{height:auto;min-height:74px;flex-wrap:wrap;padding-top:15px;padding-bottom:15px;gap:12px}.masthead nav{width:100%;margin-left:0;justify-content:space-between;gap:12px}.masthead nav a{min-height:30px;display:flex;align-items:center}}
</style>
