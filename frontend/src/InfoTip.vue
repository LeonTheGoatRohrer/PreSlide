<script setup>
// One explanation pattern for the whole UI: hover (desktop), keyboard focus, tap/click (touch), Esc to close.
import { computed, ref, onBeforeUnmount, nextTick } from 'vue'
import { explain } from './metricDefinitions.js'

const props = defineProps({
  term: { type: String, required: true },
  value: { type: [Number, String], default: null },
  ctx: { type: Object, default: () => ({}) },
  label: { type: String, default: null },  // visible text; defaults to the definition's label; '' = icon only
})
const info = computed(() => explain(props.term, props.value, props.ctx))
const open = ref(false), pinned = ref(false), alignRight = ref(false), sheet = ref(false)
const root = ref(null)
const id = 'tip-' + Math.random().toString(36).slice(2, 9)
const shown = computed(() => props.label === null ? info.value.label : props.label)

async function show() {
  open.value = true
  await nextTick()
  const r = root.value?.getBoundingClientRect()
  sheet.value = window.innerWidth < 600
  alignRight.value = !!r && r.left + 320 > window.innerWidth
}
function hide() { if (!pinned.value) open.value = false }
function close() { pinned.value = false; open.value = false }
function toggle() {
  if (pinned.value) return close()
  pinned.value = true; show()
  document.addEventListener('pointerdown', outside, true)
}
function outside(e) { if (!root.value?.contains(e.target)) { close(); document.removeEventListener('pointerdown', outside, true) } }
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside, true))
</script>

<template>
  <span ref="root" class="infotip" @mouseenter="show" @mouseleave="hide" @keydown.esc.stop="close">
    <span v-if="shown" class="infotip-text">{{ shown }}</span>
    <button type="button" class="infotip-btn" :aria-label="`Erklärung: ${info.label}`" :aria-expanded="open" :aria-describedby="open ? id : undefined"
            @click.stop="toggle" @focus="show" @blur="hide">
      <svg width="13" height="13" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 7v4.5M8 4.6v.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
    </button>
    <span v-show="open" :id="id" :role="pinned ? 'dialog' : 'tooltip'" :aria-label="pinned ? info.label : undefined" class="infotip-pop" :class="{ right: alignRight, sheet }">
      <strong class="infotip-title">{{ info.label }}</strong>
      <span class="infotip-what">{{ info.what }}</span>
      <span v-if="info.value" class="infotip-current"><b>Aktueller Wert: {{ info.value }}</b><template v-if="info.reading"> – {{ info.reading }}</template></span>
      <span v-if="info.reference" class="infotip-meta"><i>Referenz</i>{{ info.reference }}</span>
      <span v-if="info.direction" class="infotip-meta"><i>Richtung</i>{{ info.direction }}</span>
      <span v-if="info.warning" class="infotip-warning">{{ info.warning }}</span>
      <button v-if="pinned || sheet" type="button" class="infotip-close" @click.stop="close">Schließen</button>
    </span>
  </span>
</template>

<style>
span.infotip{position:relative;display:inline-flex!important;align-items:center;gap:4px;vertical-align:baseline}
span.infotip-text{display:inline!important}
.infotip-btn{border:0;background:none;padding:2px;margin:-2px 0;color:var(--ink-2);display:inline-flex;align-items:center;min-width:22px;min-height:22px;justify-content:center;border-radius:50%}
.infotip-btn:hover,.infotip-btn[aria-expanded=true]{color:var(--moss)}
.infotip-btn:focus-visible{outline-offset:1px}
.infotip-pop{position:absolute;z-index:50;top:calc(100% + 8px);left:-8px;width:min(320px,86vw);background:var(--card);border:1px solid var(--line);border-radius:12px;border-top:2px solid var(--moss);box-shadow:0 10px 30px rgba(20,20,40,.14);padding:14px 16px 12px;display:flex;flex-direction:column;gap:8px;text-align:left;font-size:14px;line-height:1.55;color:var(--ink);font-weight:400;letter-spacing:0;text-transform:none;white-space:normal}
.infotip-pop.right{left:auto;right:-8px}
.infotip-pop strong.infotip-title{display:block;font-size:13px;line-height:1.4;letter-spacing:0;margin:0;font-weight:600;color:var(--moss)}
.infotip-current{background:var(--paper);padding:7px 9px}
.infotip-current b{font-weight:600}
.infotip-meta{color:#3c3c44}.infotip-meta i{font-style:normal;display:block;font-size:10px;letter-spacing:.8px;text-transform:uppercase;color:var(--ink-2)}
.infotip-warning{color:#6b4a00;border-left:2px solid #d9a300;padding-left:8px}
.infotip-close{align-self:flex-end;border:1px solid var(--line);background:#fff;font-size:11px;padding:6px 10px;min-height:32px}
.infotip-pop.sheet{position:fixed;top:auto;left:12px;right:12px;bottom:12px;width:auto;max-height:70vh;overflow:auto}
</style>
