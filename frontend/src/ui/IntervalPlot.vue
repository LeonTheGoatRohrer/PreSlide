<script setup>
// Point estimate with its interval on a fixed scale and a dashed reference (chance or zero).
// The interval is required by design: a value without uncertainty is not drawn as a result.
import {computed} from 'vue'
import {fmt} from '../metricDefinitions.js'
const props = defineProps({
  value: {type: Number, required: true},
  interval: {type: Array, required: true},
  reference: {type: Number, default: 0.5},
  referenceLabel: {type: String, default: 'Zufall'},
  min: {type: Number, default: 0.3},
  max: {type: Number, default: 1},
  signed: {type: Boolean, default: false},
  tone: {type: String, default: 'moss'},
  label: {type: String, required: true},
})
const pct = v => Math.min(100, Math.max(0, (v - props.min) / (props.max - props.min) * 100))
const show = v => (props.signed && v > 0 ? '+' : '') + fmt(v)
const spans = computed(() => props.interval[0] <= props.reference && props.interval[1] >= props.reference)
const aria = computed(() => `${props.label}: ${show(props.value)}, Intervall ${show(props.interval[0])} bis ${show(props.interval[1])}, ${props.referenceLabel} ${show(props.reference)}${spans.value ? ', Intervall schließt den Bezugswert ein' : ''}`)
</script>
<template>
  <div class="ivp" :class="['ivp-' + tone, {spans}]">
    <div class="ivp-track" role="img" :aria-label="aria">
      <span class="ivp-ref" :style="{left: pct(reference) + '%'}"></span>
      <span class="ivp-ci" :style="{left: pct(interval[0]) + '%', width: (pct(interval[1]) - pct(interval[0])) + '%'}"></span>
      <span class="ivp-dot" :style="{left: pct(value) + '%'}"></span>
    </div>
    <div class="ivp-axis" aria-hidden="true">
      <span>{{ show(min) }}</span>
      <span class="ivp-ref-label" :style="{left: pct(reference) + '%'}">{{ referenceLabel }} {{ show(reference) }}</span>
      <span>{{ show(max) }}</span>
    </div>
  </div>
</template>
<style>
.ivp{--c:var(--moss);width:100%;padding-top:6px}
.ivp-grey{--c:var(--ink-2)}
.ivp-glacier{--c:var(--glacier)}
.ivp-track{position:relative;height:28px}
.ivp-track::before{content:'';position:absolute;left:0;right:0;top:50%;height:1px;background:var(--line-2)}
.ivp-ci{position:absolute;top:50%;height:10px;transform:translateY(-50%);background:color-mix(in srgb,var(--c) 26%,transparent);border-left:2px solid var(--c);border-right:2px solid var(--c);border-radius:2px}
.ivp-dot{position:absolute;top:50%;width:16px;height:16px;border-radius:50%;background:var(--c);transform:translate(-50%,-50%);box-shadow:0 0 0 3px var(--card)}
.ivp-ref{position:absolute;top:0;bottom:0;width:0;border-left:1.5px dashed var(--ink-2)}
.ivp-axis{position:relative;display:flex;justify-content:space-between;margin-top:6px;font:400 12.5px/1.2 var(--f-mono);color:var(--ink-2);font-variant-numeric:tabular-nums}
.ivp-ref-label{position:absolute;top:0;transform:translateX(-50%);white-space:nowrap;background:inherit}
.dark .ivp-track::before{background:rgb(255 255 255 / .2)}
.dark .ivp-dot{box-shadow:0 0 0 3px var(--slate-700)}
.dark .ivp-ref{border-color:var(--on-dark-2)}
.dark .ivp-axis{color:var(--on-dark-2)}
</style>
