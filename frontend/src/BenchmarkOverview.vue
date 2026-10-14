<script setup>
import {ref,computed,onMounted} from 'vue'
const data=ref(null),error=ref(''),metric=ref('local_auc'),family=ref('all'),showTable=ref(false),tip=ref(null)
const VAR=[{key:'static',label:'Gelände',shape:'circle'},{key:'temporal',label:'Wetter',shape:'square'},{key:'combined',label:'Kombiniert',shape:'diamond'}]
const ORDER=['Bedingte log. Regression','Logistische Regression','Random Forest','Gradient Boosting']
const n=(v,d=3)=>v==null?'–':Number(v).toLocaleString('de-AT',{minimumFractionDigits:d,maximumFractionDigits:d})
onMounted(async()=>{try{const r=await fetch('/api/benchmarks');if(!r.ok)throw Error('Benchmarks nicht verfügbar ('+r.status+').');data.value=await r.json()}catch(e){error.value=e.message}})
const families=computed(()=>[...new Set((data.value?.rows||[]).map(r=>r.model))].sort((a,b)=>ORDER.indexOf(a)-ORDER.indexOf(b)))
const scale=computed(()=>metric.value==='local_auc'?{lo:.3,hi:1,ticks:[.3,.4,.5,.6,.7,.8,.9,1],chance:.5}:{lo:0,hi:.7,ticks:[0,.1,.2,.3,.4,.5,.6,.7],chance:null})
const pct=v=>Math.max(0,Math.min(100,(v-scale.value.lo)/(scale.value.hi-scale.value.lo)*100))+'%'
// One block per run, one row per model inside it; variants are three marks on the same row.
const blocks=computed(()=>(data.value?.runs||[]).map(run=>{
  const rows=data.value.rows.filter(r=>r.run===run.id&&(family.value==='all'||r.model===family.value))
  const models=[...new Set(rows.map(r=>r.model))].sort((a,b)=>ORDER.indexOf(a)-ORDER.indexOf(b)).map(model=>{
    const marks=VAR.map((v,i)=>{const r=rows.find(x=>x.model===model&&x.variant===v.key);if(!r||r[metric.value]==null)return null
      return{...r,...v,value:r[metric.value],lane:i,range:metric.value==='local_auc'?r.local_auc_range:null}}).filter(Boolean)
    const chance=metric.value==='top1'?rows.find(x=>x.model===model)?.top1_chance:null
    return{model,marks,chance}
  }).filter(m=>m.marks.length)
  const refs=(data.value.references||[]).filter(x=>x.run===run.id&&x[metric.value]!=null)
  return{...run,models,refs}
}).filter(b=>b.models.length))
function show(e,m,run){const box=e.currentTarget.closest('.bm-chart').getBoundingClientRect(),t=e.currentTarget.getBoundingClientRect()
  tip.value={x:t.left-box.left+t.width/2,y:t.top-box.top,m,run}}
const tableRows=computed(()=>blocks.value.flatMap(b=>b.models.flatMap(m=>m.marks.map(k=>({run:b.label,controls:b.controls,units:b.units,events:b.events,model:m.model,variant:k.label,auc:k.local_auc,range:k.local_auc_range,top1:k.top1,chance:k.top1_chance})))))
</script>

<template>
  <section id="benchmarks" class="section benchmarks">
    <div class="section-heading"><div><p class="section-number">Überblick — Alle bisherigen Modellläufe</p><h2>Wie gut liefen die Modelle bisher?</h2></div></div>
    <p v-if="error" class="section-intro">{{error}}</p>
    <template v-if="data">
      <p class="section-intro">Jede Zeile ist ein gespeicherter Modelllauf aus V0 bis V0.5, nichts wurde neu gerechnet. Die „lokale AUC“ sagt, wie oft der echte Rutschungshang höher eingestuft wurde als ein Vergleichshang derselben Gruppe (0,5 = Zufall, 1 = immer richtig). „Top-1“ ist der Anteil, in dem der echte Hang auf Platz 1 landet.</p>
      <div class="bm-controls" role="group" aria-label="Diagrammoptionen">
        <div class="segmented"><button :class="{active:metric==='local_auc'}" @click="metric='local_auc'">Lokale AUC</button><button :class="{active:metric==='top1'}" @click="metric='top1'">Top-1</button></div>
        <label>Modell <select v-model="family"><option value="all">Alle Modelle</option><option v-for="f in families" :key="f" :value="f">{{f}}</option></select></label>
        <button class="bm-toggle" @click="showTable=!showTable">{{showTable?'Diagramm zeigen':'Als Tabelle zeigen'}}</button>
      </div>
      <div class="bm-legend" aria-label="Legende">
        <span v-for="v in VAR" :key="v.key"><i :class="['bm-mark',v.shape,v.key]"></i>{{v.label}}</span>
        <span><i class="bm-range-key"></i>Spannweite / 95 %-Intervall</span>
        <span v-if="metric==='local_auc'"><i class="bm-chance-key"></i>Zufall (0,5)</span>
        <span v-else><i class="bm-chance-tick"></i>Zufall je Lauf (1/6 bzw. 1/11)</span>
      </div>

      <div v-if="!showTable" class="bm-chart" @mouseleave="tip=null">
        <div class="bm-axis"><div class="bm-label"></div><div class="bm-track"><span v-for="t in scale.ticks" :key="t" :style="{left:pct(t)}">{{n(t,1)}}</span></div></div>
        <div v-for="b in blocks" :key="b.id" :class="['bm-block',{unmatched:!b.comparable}]">
          <div class="bm-run"><b>{{b.label}}</b><span>{{b.evaluation}} · {{b.controls}} Kontrollen · {{b.events}} Ereignisse<template v-if="b.units"> · {{b.units}} unabhängige Einheiten</template></span>
            <em v-if="!b.comparable">Andere, leichtere Aufgabe – nicht direkt mit den gematchten Läufen vergleichbar</em></div>
          <div v-for="m in b.models" :key="m.model" class="bm-row">
            <div class="bm-label">{{m.model}}</div>
            <div class="bm-track">
              <i v-for="t in scale.ticks" :key="t" class="bm-grid" :style="{left:pct(t)}"></i>
              <i v-if="scale.chance" class="bm-chance" :style="{left:pct(scale.chance)}"></i>
              <i v-if="m.chance" class="bm-chance-tick" :style="{left:pct(m.chance)}" :title="'Zufall '+n(m.chance)"></i>
              <template v-for="k in m.marks" :key="k.key">
                <i v-if="k.range" :class="['bm-range',k.key]" :style="{left:pct(k.range[0]),width:`calc(${pct(k.range[1])} - ${pct(k.range[0])})`,top:(8+k.lane*9)+'px'}"></i>
                <button :class="['bm-mark',k.shape,k.key]" :style="{left:pct(k.value),top:(8+k.lane*9)+'px'}"
                  :aria-label="`${b.label}, ${m.model}, ${k.label}: ${n(k.value)}`" @mouseenter="show($event,k,b)" @focus="show($event,k,b)" @blur="tip=null"></button>
              </template>
            </div>
          </div>
          <div v-for="r in b.refs" :key="r.label" class="bm-row ref">
            <div class="bm-label">{{r.label}}</div>
            <div class="bm-track"><i v-if="scale.chance" class="bm-chance" :style="{left:pct(scale.chance)}"></i><i class="bm-ref" :style="{left:pct(r[metric])}" :title="n(r[metric])"></i><small :style="{left:pct(r[metric])}">{{n(r[metric])}}</small></div>
          </div>
        </div>
        <div v-if="tip" class="bm-tip" :style="{left:tip.x+'px',top:tip.y+'px'}" role="status">
          <b>{{tip.m.model}} · {{tip.m.label}}</b>
          <span>{{tip.run.label}}</span>
          <span>Lokale AUC {{n(tip.m.local_auc)}}<template v-if="tip.m.local_auc_range"> ({{n(tip.m.local_auc_range[0])}}–{{n(tip.m.local_auc_range[1])}}, {{tip.run.interval}})</template></span>
          <span>Top-1 {{n(tip.m.top1)}} <template v-if="tip.m.top1!=null">(Zufall {{n(tip.m.top1_chance)}})</template></span>
          <span>Gewichtung {{tip.run.weighting}}</span>
        </div>
      </div>

      <table v-else class="bm-table">
        <thead><tr><th>Lauf</th><th>Kontrollen</th><th>Ereignisse / Einheiten</th><th>Modell</th><th>Merkmale</th><th>lokale AUC</th><th>Intervall</th><th>Top-1</th><th>Zufall Top-1</th></tr></thead>
        <tbody><tr v-for="(r,i) in tableRows" :key="i"><td>{{r.run}}</td><td>{{r.controls}}</td><td>{{r.events}} / {{r.units??'–'}}</td><td>{{r.model}}</td><td>{{r.variant}}</td><td>{{n(r.auc)}}</td><td>{{r.range?n(r.range[0])+'–'+n(r.range[1]):'–'}}</td><td>{{n(r.top1)}}</td><td>{{n(r.chance)}}</td></tr></tbody>
      </table>

      <div class="bm-notes">
        <p><b>So liest man das:</b> Je weiter rechts, desto besser. Aussagekräftig sind vor allem Läufe mit vielen unabhängigen Einheiten und einem echten, vorher unberührten Test (V0.4 versiegelt). V0 und V0.2 beruhen auf nur 4 bzw. 16 Einheiten und schwanken stark.</p>
        <p><b>V0.5 ist eine andere Aufgabe:</b> Dort wird gegen zehn zufällige statt fünf ähnliche Nachbarhänge verglichen. Dieselben Ereignisse mit gematchten Kontrollen (Zeile darunter) liegen wieder bei rund 0,70. Der Sprung kommt von der leichteren Aufgabe, nicht von einem besseren Modell.</p>
        <p><b>Wetter:</b> Ein belegter Zusatznutzen des Wetters (Raute gegenüber Kreis) wurde in keiner Version gefunden. {{data.note}}</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.benchmarks{--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a}
.bm-controls{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin:18px 0 10px;font-size:13px}
.bm-controls select{margin-left:6px;font:inherit;padding:4px 6px}
.bm-toggle{font:inherit;font-size:13px;background:none;border:1px solid var(--line);padding:5px 10px;cursor:pointer}
.bm-legend{display:flex;flex-wrap:wrap;gap:18px;font-size:12.5px;color:#202025;margin:6px 0 14px}
.bm-legend span{display:inline-flex;align-items:center;gap:7px}
.bm-legend .bm-mark{position:relative;transform:none;cursor:default}.bm-legend .bm-mark::after{display:none}.bm-legend .bm-mark.diamond{transform:rotate(45deg)}
.bm-chart{position:relative;font-size:12.5px;padding-right:16px}
.bm-axis,.bm-row{display:grid;grid-template-columns:200px 1fr;gap:14px;align-items:center}
.bm-axis .bm-track{height:18px;border-bottom:1px solid var(--line)}
.bm-axis span{position:absolute;transform:translateX(-50%);font-size:11px;color:var(--muted);bottom:3px}
.bm-block{padding:14px 0 6px;border-bottom:1px solid var(--line)}
.bm-block.unmatched{background:repeating-linear-gradient(135deg,transparent 0 9px,#f4f4f6 9px 10px)}
.bm-run{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;margin-bottom:6px}
.bm-run b{font-size:14px}.bm-run span{color:var(--muted);font-size:12px}
.bm-run em{flex-basis:100%;font-style:normal;font-size:12px;color:#202025;border-left:2px solid var(--blue);padding-left:8px}
.bm-label{color:#202025;font-size:12.5px}
.bm-track{position:relative;height:36px}
.bm-row.ref .bm-track{height:22px}
.bm-grid{position:absolute;top:0;bottom:0;width:1px;background:#efeff2}
.bm-chance{position:absolute;top:0;bottom:0;width:0;border-left:1.5px dashed #6b6b74}
.bm-chance-tick{position:absolute;top:4px;bottom:4px;width:2px;background:#6b6b74;transform:translateX(-1px)}
.bm-range{position:absolute;height:2px;margin-top:-1px;opacity:.55}
.bm-range.static{background:var(--s1)}.bm-range.temporal{background:var(--s2)}.bm-range.combined{background:var(--s3)}
.bm-mark{position:absolute;width:10px;height:10px;padding:0;border:2px solid #fff;transform:translate(-50%,-50%);cursor:pointer;box-sizing:content-box;display:inline-block}
.bm-mark::after{content:'';position:absolute;inset:-6px}
.bm-mark.circle{border-radius:50%}.bm-mark.diamond{transform:translate(-50%,-50%) rotate(45deg);width:9px;height:9px}
.bm-mark.static{background:var(--s1)}.bm-mark.temporal{background:var(--s2)}.bm-mark.combined{background:var(--s3)}
.bm-mark:focus-visible{outline:2px solid #202025;outline-offset:2px}
.bm-ref{position:absolute;top:5px;width:10px;height:10px;border:2px solid #202025;border-radius:50%;background:#fff;transform:translateX(-50%)}
.bm-row.ref small{position:absolute;top:4px;margin-left:10px;font-size:11px;color:var(--muted)}
.bm-range-key{display:inline-block;width:22px;height:2px;background:#6b6b74}
.bm-chance-key{display:inline-block;width:0;height:14px;border-left:1.5px dashed #6b6b74}
.bm-legend .bm-chance-tick{position:static;display:inline-block;height:12px;transform:none}
.bm-tip{position:absolute;z-index:5;transform:translate(-50%,calc(-100% - 10px));background:#202025;color:#fff;padding:8px 10px;font-size:12px;line-height:1.5;display:flex;flex-direction:column;min-width:220px;pointer-events:none}
.bm-table{width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0 16px}
.bm-table th,.bm-table td{padding:5px 6px;border-bottom:1px solid var(--line);text-align:left}
.bm-table td:nth-child(n+6),.bm-table th:nth-child(n+6){text-align:right}
.bm-notes{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;margin-top:22px}
.bm-notes p{font-size:13px;line-height:1.6;color:#202025;margin:0}
@media(max-width:800px){.bm-axis,.bm-row{grid-template-columns:1fr;gap:2px}.bm-axis .bm-label{display:none}.bm-notes{grid-template-columns:1fr}
  .bm-table{display:block;overflow-x:auto;font-size:11.5px}}
</style>
