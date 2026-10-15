<script setup>
// Sticky "on this page" bar: jump links (buttons, because the URL hash is used for page routing) + current-section highlight.
import { ref, onMounted, onBeforeUnmount } from 'vue'
const props = defineProps({ items: { type: Array, required: true } })
const current = ref(props.items[0]?.id)
let observer
function go(id) {
  const el = document.getElementById(id)
  if (!el) return
  el.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' })
  current.value = id
}
onMounted(() => {
  if (!('IntersectionObserver' in window)) return
  observer = new IntersectionObserver(entries => {
    const seen = entries.filter(e => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
    if (seen) current.value = seen.target.id
  }, { rootMargin: '-90px 0px -60% 0px' })
  props.items.forEach(i => { const el = document.getElementById(i.id); if (el) observer.observe(el) })
})
onBeforeUnmount(() => observer?.disconnect())
</script>
<template>
  <nav class="section-nav" aria-label="Auf dieser Seite">
    <span class="section-nav-label">Auf dieser Seite</span>
    <button v-for="i in items" :key="i.id" type="button" :aria-current="current === i.id ? 'true' : undefined" @click="go(i.id)">{{ i.label }}</button>
  </nav>
</template>
