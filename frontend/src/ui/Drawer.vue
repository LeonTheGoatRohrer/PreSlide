<script setup>
// Side drawer (full screen on phones) for one study: modal, focus kept inside, Esc or the close button returns.
import {ref, onMounted, onBeforeUnmount, nextTick} from 'vue'
const props = defineProps({label: {type: String, required: true}})
const emit = defineEmits(['close'])
const panel = ref(null)
let before = null
function key(e) {
  if (e.key === 'Escape') { e.preventDefault(); emit('close') }
  if (e.key !== 'Tab') return
  const f = [...panel.value.querySelectorAll('a[href],button:not([disabled]),input,select,summary,[tabindex="0"]')].filter(el => el.offsetParent)
  if (!f.length) return
  if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f.at(-1).focus() }
  else if (!e.shiftKey && document.activeElement === f.at(-1)) { e.preventDefault(); f[0].focus() }
}
onMounted(async () => { before = document.activeElement; document.documentElement.style.overflow = 'hidden'; await nextTick(); panel.value?.focus() })
onBeforeUnmount(() => { document.documentElement.style.overflow = ''; before?.focus?.() })
</script>
<template>
  <div class="dr-scrim" @pointerdown.self="emit('close')">
    <div ref="panel" class="dr" role="dialog" aria-modal="true" :aria-label="props.label" tabindex="-1" @keydown="key">
      <button type="button" class="dr-close" @click="emit('close')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg><span>Schließen</span></button>
      <slot/>
    </div>
  </div>
</template>
<style>
.dr-scrim{position:fixed;inset:0;z-index:70;background:rgb(14 24 34 / .45);backdrop-filter:blur(3px);animation:fade .2s}
.dr{position:absolute;top:0;right:0;bottom:0;width:min(920px,100%);background:var(--paper);overflow:auto;overscroll-behavior:contain;outline:none;box-shadow:-30px 0 60px -30px rgb(14 24 34 / .5);animation:dr-in .38s var(--ease)}
.dr-close{position:sticky;top:12px;float:right;z-index:3;margin:12px 12px 0 0;display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:0 14px;border-radius:12px;border:1px solid var(--line-2);background:var(--card);font-weight:600;box-shadow:var(--shadow)}
.dr-close svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2}
@keyframes dr-in{from{transform:translateX(40px);opacity:0}}
@media (prefers-reduced-motion:reduce){.dr{animation:none}}
</style>
