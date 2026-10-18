<script setup>
// Point estimate with its interval on a fixed scale and a dashed reference (chance or zero).
// The interval is required by design: a value without uncertainty is not drawn as a result.
import { computed } from 'vue'
import { fmt } from './metricDefinitions.js'
const props = defineProps({
  value: { type: Number, required: true },
  interval: { type: Array, required: true },
  reference: { type: Number, default: 0.5 },
  referenceLabel: { type: String, default: 'Zufall' },
  min: { type: Number, default: 0.3 },
  max: { type: Number, default: 1 },
  signed: { type: Boolean, default: false },
  tone: { type: String, default: 'blue' },
  label: { type: String, required: true },
})
const pct = v => Math.min(100, Math.max(0, (v - props.min) / (props.max - props.min) * 100))
const show = v => (props.signed && v > 0 ? '+' : '') + fmt(v)
const spansReference = computed(() => props.interval[0] <= props.reference && props.interval[1] >= props.reference)
const aria = computed(() => `${props.label}: ${show(props.value)}, Intervall ${show(props.interval[0])} bis ${show(props.interval[1])}, ${props.referenceLabel} ${show(props.reference)}${spansReference.value ? ', Intervall schließt den Bezugswert ein' : ''}`)
</script>
<template>
  <div class="ip" :class="['ip-' + tone, { 'ip-spans': spansReference }]">
    <div class="ip-track" role="img" :aria-label="aria">
      <span class="ip-ref" :style="{ left: pct(reference) + '%' }"></span>
      <span class="ip-ci" :style="{ left: pct(interval[0]) + '%', width: (pct(interval[1]) - pct(interval[0])) + '%' }"></span>
      <span class="ip-dot" :style="{ left: pct(value) + '%' }"></span>
    </div>
    <div class="ip-axis" aria-hidden="true">
      <span>{{ show(min) }}</span>
      <span class="ip-ref-label" :style="{ left: pct(reference) + '%' }">{{ referenceLabel }} {{ show(reference) }}</span>
      <span>{{ show(max) }}</span>
    </div>
  </div>
</template>
