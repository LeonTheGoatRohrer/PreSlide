<script setup>
// Counts a stored value up once when it becomes visible; the final text is always the exact formatted value.
import {ref, onMounted, onBeforeUnmount, watch} from 'vue'
import {countUp} from './motion.js'
const props = defineProps({value: {type: Number, required: true}, format: {type: Function, required: true}})
const shown = ref(props.format(props.value)), el = ref(null)
let stop = () => {}, io = null, done = false
function run() {
  if (done) return
  done = true
  stop = countUp(props.value, v => { shown.value = props.format(v) })
  setTimeout(() => { shown.value = props.format(props.value) }, 1300)
}
onMounted(() => {
  if (typeof IntersectionObserver === 'undefined') return
  shown.value = props.format(0)
  io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { run(); io.disconnect() } }, {threshold: .4})
  io.observe(el.value)
})
watch(() => props.value, () => { shown.value = props.format(props.value) })
onBeforeUnmount(() => { stop(); io?.disconnect() })
</script>
<template><span ref="el" class="count-up" :aria-label="format(value)"><span aria-hidden="true">{{ shown }}</span></span></template>
