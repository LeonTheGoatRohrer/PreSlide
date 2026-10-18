<script setup>
import {computed, ref, onMounted, onBeforeUnmount} from 'vue'
import {profileGeometry, meters, count, STATUS_SHORT} from './chain.js'

const props = defineProps({chain: {type: Object, required: true}, selected: {type: String, default: ''}})
const emit = defineEmits(['select'])
const box = ref(null), width = ref(900)
let observer
onMounted(() => {
  observer = new ResizeObserver(([entry]) => { width.value = Math.max(260, Math.round(entry.contentRect.width)) })
  if (box.value) { width.value = Math.max(260, Math.round(box.value.clientWidth || 900)); observer.observe(box.value) }
})
onBeforeUnmount(() => observer?.disconnect())
// Real pixel width -> text keeps its size on phones (no stretched viewBox).
const g = computed(() => profileGeometry(props.chain.profil, props.chain.szenarien,
  {width: width.value, height: width.value < 520 ? 210 : 250, pad: {l: width.value < 520 ? 40 : 52, r: 12, t: 70, b: 30}}))
const band = computed(() => {
  if (!g.value) return null
  const xs = g.value.stops.map(s => s.x)
  return {x: Math.min(...xs), w: Math.max(...xs) - Math.min(...xs)}
})
const sinks = computed(() => {
  if (!g.value) return []
  return (props.chain.route.senken_distanz_m || []).filter(d => d <= g.value.xMax).map(d => g.value.X(d))
})
// One label row per scenario (sorted by reach) so close stops never overlap; right half labels end at the line.
const stopRows = computed(() => (g.value?.stops || []).slice().sort((a, b) => a.x - b.x)
  .map((s, i) => ({...s, row: i, end: s.x > g.value.width * 0.6})))
const summary = computed(() => {
  const c = props.chain
  const parts = c.szenarien.map(s => `${s.bezeichnung}: ${meters(s.laenge_m)}, ${STATUS_SHORT[s.status]}`)
  return `Geländeschnitt von ${c.anriss.bezeichnung}, Anriss auf ${count(c.anriss.hoehe_m)} m. ${parts.join('; ')}.`
})
</script>
<template>
  <figure class="wk-profile">
    <figcaption>
      <span class="wk-tag" data-kind="Szenario">Szenario</span>
      Geländeschnitt entlang der Abwärtsroute
      <small>Höhe über dem Meer, horizontale Entfernung vom Anrisspunkt</small>
    </figcaption>
    <div ref="box" class="wk-svgbox"><svg v-if="g" :viewBox="`0 0 ${g.width} ${g.height}`" :width="g.width" :height="g.height" role="img" :aria-label="summary">
      <defs>
        <pattern id="wk-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" class="wk-hatch-line" />
        </pattern>
      </defs>
      <g class="wk-grid">
        <line v-for="t in g.yTicks" :key="'y'+t.v" :x1="g.pad.l" :x2="g.width - g.pad.r" :y1="t.y" :y2="t.y" />
      </g>
      <rect v-if="band" class="wk-band" :x="band.x" :y="g.pad.t" :width="Math.max(band.w, 2)" :height="g.height - g.pad.t - g.pad.b" />
      <path :d="g.area" class="wk-ground" />
      <path :d="g.area" fill="url(#wk-hatch)" />
      <path :d="g.line" class="wk-surface" />
      <path v-for="e in g.energyLines" :key="e.id" :d="e.path" class="wk-energy" :class="{on: selected === e.id}" />
      <g class="wk-sinks"><line v-for="(x, i) in sinks" :key="i" :x1="x" :x2="x" :y1="g.height - g.pad.b" :y2="g.height - g.pad.b + 5" /></g>
      <g v-for="s in stopRows" :key="s.id" class="wk-stop" :class="{on: selected === s.id, open: s.status !== 'gestoppt'}"
         @click="emit('select', s.id)">
        <line :x1="s.x" :x2="s.x" :y1="s.y" :y2="8 + s.row * 15" />
        <circle :cx="s.x" :cy="s.y" r="4" />
        <text :x="s.end ? s.x - 4 : s.x + 4" :y="12 + s.row * 15" :text-anchor="s.end ? 'end' : 'start'">{{ s.label }}</text>
      </g>
      <circle :cx="g.X(0)" :cy="g.Y(chain.profil.hoehe_m[0])" r="5.5" class="wk-release" />
      <g class="wk-axis">
        <text v-for="t in g.ticks" :key="'x'+t.v" :x="t.x" :y="g.height - 10" text-anchor="middle">{{ meters(t.v) }}</text>
        <text v-for="t in g.yTicks" :key="'yl'+t.v" :x="g.pad.l - 6" :y="t.y + 3" text-anchor="end">{{ count(t.v) }}</text>
      </g>
    </svg></div>
    <p v-if="!g" class="wk-note">Für diesen Punkt ist kein Höhenprofil berechenbar.</p>
    <ul class="wk-profile-key">
      <li><i class="k-surface"></i>Gelände (30-m-Modell)</li>
      <li><i class="k-energy"></i>Energielinien 11° und 7°</li>
      <li><i class="k-band"></i>Spanne der vier Szenarien</li>
      <li v-if="sinks.length"><i class="k-sink"></i>rechnerisch gefüllte Senke</li>
    </ul>
  </figure>
</template>
<style scoped>
.wk-profile{margin:0;border:1px solid var(--line);background:#fff}
figcaption{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;padding:14px 16px 0;font-size:14px;font-weight:500}
figcaption small{font-weight:400;font-size:11px;color:var(--muted);flex-basis:100%}
svg{display:block}
.wk-svgbox{width:100%;overflow:hidden}
.wk-grid line{stroke:#ececef;stroke-width:1}
.wk-band{fill:#002fa7;opacity:.08}
.wk-ground{fill:#efeee9}
.wk-hatch-line{stroke:#c9c6bc;stroke-width:1}
.wk-surface{fill:none;stroke:#202025;stroke-width:1.6;vector-effect:non-scaling-stroke}
.wk-energy{fill:none;stroke:#002fa7;stroke-width:1.2;stroke-dasharray:5 4;opacity:.55;vector-effect:non-scaling-stroke}
.wk-energy.on{opacity:1;stroke-width:2}
.wk-sinks line{stroke:#8a6d1f;stroke-width:1.5}
.wk-stop{cursor:pointer}
.wk-stop line{stroke:#002fa7;stroke-width:1;stroke-dasharray:2 2;vector-effect:non-scaling-stroke}
.wk-stop circle{fill:#fff;stroke:#002fa7;stroke-width:2}
.wk-stop.open circle{stroke-dasharray:2 2}
.wk-stop.on circle{fill:#002fa7}
.wk-stop text{font-size:11px;fill:#002fa7}
.wk-stop.on text{font-weight:600}
.wk-release{fill:#7a1e48;stroke:#fff;stroke-width:2}
.wk-axis text{font-size:10px;fill:#6b6b74}
.wk-note{padding:16px;font-size:13px;color:var(--muted)}
.wk-profile-key{list-style:none;margin:0;padding:8px 16px 14px;display:flex;flex-wrap:wrap;gap:6px 18px;font-size:11px;color:var(--muted)}
.wk-profile-key i{display:inline-block;width:18px;height:10px;margin-right:6px;vertical-align:-1px}
.k-surface{border-bottom:2px solid #202025;height:6px!important;background:repeating-linear-gradient(45deg,#efeee9 0 3px,#c9c6bc 3px 4px)}
.k-energy{border-top:2px dashed #002fa7;height:0!important;vertical-align:3px!important}
.k-band{background:#002fa714}
.k-sink{width:2px!important;background:#8a6d1f}
.wk-tag{font-size:10px;letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border:1px solid currentColor;color:#002fa7;font-weight:600}

</style>
