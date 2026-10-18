<script setup>
// Start page: a real, cached Hang-Check result of the first example area. Shown only when it exists;
// without the Hang-Check API the section is left out instead of showing a placeholder.
import {ref, onMounted, defineAsyncComponent} from 'vue'
import {loadExamples} from '../places.js'
import {runCheck, requestBody, normalize, km} from '../check.js'
import {openCheck} from '../session.js'
import {vReveal} from '../ui/motion.js'
const TerrainMap = defineAsyncComponent(() => import('./TerrainMap.vue'))
const example = ref(null), result = ref(null), visible = ref(false), host = ref(null)
onMounted(async () => {
  let ex
  try { ex = (await loadExamples()).examples[0] } catch { return }
  if (!ex) return
  // Request only when the section comes near the viewport, so the start page itself stays light.
  const io = new IntersectionObserver(async ([e]) => {
    if (!e.isIntersecting) return
    io.disconnect()
    const r = await runCheck(requestBody(ex, ex.radius_m ?? 2000, true))
    if (!r.ok) return
    example.value = ex; result.value = {raw: r.data, ...normalize(r.data, ex)}; visible.value = true
  }, {rootMargin: '400px 0px'})
  io.observe(host.value)
})
</script>
<template>
  <div ref="host">
    <section v-if="visible" class="section live" aria-labelledby="live-title">
      <div class="wrap live-grid">
        <div class="live-text">
          <p class="eyebrow" v-reveal>Echtes Beispiel</p>
          <h2 id="live-title" v-reveal="1">{{ example.name }}, {{ km(example.radius_m ?? 2000) }} Umkreis.</h2>
          <p class="lead" v-reveal="2">Rot und Orange sind die Hänge, die sich im Gelände am deutlichsten von ihrer Umgebung abheben. Die Nummern sind die fünf Prüfpunkte, mit denen eine Begehung beginnen würde.</p>
          <p class="note" v-reveal="3">Berechnet mit dem eingefrorenen Geländemodell, aus dem gespeicherten Ergebnis. Nicht markiert heißt nicht sicher.</p>
          <button type="button" class="btn btn-primary" v-reveal="4" @click="openCheck({...example}, {rain: true})">Im Hang-Check öffnen</button>
        </div>
        <div class="live-map card" v-reveal="1">
          <TerrainMap embedded :centre="example" :radius-m="example.radius_m ?? 2000" :cells="result.cells" :max-d="result.maxD" :points="result.points"/>
        </div>
      </div>
    </section>
  </div>
</template>
<style>
.live-grid{display:grid;grid-template-columns:5fr 7fr;gap:clamp(32px,5vw,72px);align-items:center}
.live-text h2{margin-bottom:22px}
.live-text .note{margin:18px 0 28px}
.live-map{position:relative;aspect-ratio:4/3;overflow:hidden}
@media (max-width:860px){.live-grid{grid-template-columns:1fr}.live-map{order:-1;aspect-ratio:1/1}}
</style>
