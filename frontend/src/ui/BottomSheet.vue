<script setup>
// Floating panel on wide screens, bottom sheet with three snap heights (Kopf, halb, voll) on phones.
// Drag the handle, or use it with the keyboard: Enter/Space cycles, arrow keys move up and down.
import {ref, computed} from 'vue'
const props = defineProps({label: {type: String, required: true}})
const snaps = ['kopf', 'halb', 'voll'], names = {kopf: 'nur Kopf', halb: 'halbe Höhe', voll: 'volle Höhe'}
const snap = ref('halb'), drag = ref(null)
const style = computed(() => drag.value !== null ? {height: drag.value + 'px', transition: 'none'} : null)
function set(s) { snap.value = s }
function step(dir) { set(snaps[Math.max(0, Math.min(2, snaps.indexOf(snap.value) + dir))]) }
function key(e) {
  if (e.key === 'ArrowUp') { e.preventDefault(); step(1) }
  else if (e.key === 'ArrowDown') { e.preventDefault(); step(-1) }
  else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); set(snaps[(snaps.indexOf(snap.value) + 1) % 3]) }
}
let startY = 0, startH = 0, moved = false
function down(e) {
  const sheet = e.currentTarget.closest('.bs')
  startY = e.clientY; startH = sheet.getBoundingClientRect().height; moved = false
  e.currentTarget.setPointerCapture(e.pointerId)
}
function move(e) {
  if (!e.currentTarget.hasPointerCapture?.(e.pointerId)) return
  const dy = startY - e.clientY
  if (Math.abs(dy) > 6) moved = true
  if (moved) drag.value = Math.max(96, Math.min(window.innerHeight - 80, startH + dy))
}
function up(e) {
  if (!moved) { drag.value = null; return }
  const h = drag.value, vh = window.innerHeight
  drag.value = null
  set(h < vh * .3 ? 'kopf' : h < vh * .72 ? 'halb' : 'voll')
  e.currentTarget.releasePointerCapture?.(e.pointerId)
}
defineExpose({set})
</script>
<template>
  <aside class="bs" :class="'bs-' + snap" :style="style" :aria-label="props.label">
    <button type="button" class="bs-handle" :aria-label="`Panelhöhe: ${names[snap]}. Pfeiltasten oder Eingabe ändern die Höhe.`"
            @keydown="key" @click="!moved && set(snaps[(snaps.indexOf(snap) + 1) % 3])" @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up">
      <span aria-hidden="true"></span>
    </button>
    <div class="bs-body"><slot/></div>
  </aside>
</template>
<style>
.bs{position:absolute;z-index:20;left:16px;top:96px;bottom:16px;width:420px;display:flex;flex-direction:column;background:var(--paper);border-radius:20px;box-shadow:var(--shadow-lift),0 0 0 1px var(--line)}
.bs-handle{display:none}
.bs-body{flex:1;overflow:auto;overscroll-behavior:contain;padding:22px 22px 26px;scrollbar-width:thin}
@media (max-width:759px){
  .bs{position:fixed;left:0;right:0;top:auto;bottom:0;width:auto;border-radius:20px 20px 0 0;transition:height .35s var(--ease);padding-bottom:env(safe-area-inset-bottom)}
  .bs-kopf{height:148px}
  .bs-halb{height:52svh}
  .bs-voll{height:calc(100svh - 88px)}
  .bs-handle{display:flex;justify-content:center;align-items:center;flex:none;height:30px;width:100%;border:0;background:none;cursor:grab;touch-action:none}
  .bs-handle span{width:44px;height:5px;border-radius:3px;background:var(--line-2)}
  .bs-body{padding:4px 16px 20px}
}
@media print{.bs{position:static;width:auto;height:auto!important;box-shadow:none;background:#fff}.bs-handle{display:none}.bs-body{overflow:visible;padding:0}}
</style>
