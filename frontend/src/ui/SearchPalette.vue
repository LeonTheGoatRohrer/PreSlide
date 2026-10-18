<script setup>
// Command palette (/ or Ctrl+K): jump straight to a place in the Hang-Check, or to a page.
import {ref, onMounted, onBeforeUnmount} from 'vue'
import PlaceSearch from './PlaceSearch.vue'
import {mainNav, href} from '../navigation.js'
const emit = defineEmits(['close', 'select'])
const dialog = ref(null)
let before = null
function key(e) {
  if (e.key === 'Escape') { e.preventDefault(); emit('close') }
  if (e.key === 'Tab') {
    const f = [...dialog.value.querySelectorAll('input,button,a[href]')].filter(el => !el.disabled && el.offsetParent)
    if (!f.length) return
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f.at(-1).focus() }
    else if (!e.shiftKey && document.activeElement === f.at(-1)) { e.preventDefault(); f[0].focus() }
  }
}
onMounted(() => { before = document.activeElement; document.documentElement.style.overflow = 'hidden' })
onBeforeUnmount(() => { document.documentElement.style.overflow = ''; before?.focus?.() })
</script>
<template>
  <div class="pal-scrim" @pointerdown.self="emit('close')">
    <div ref="dialog" class="pal" role="dialog" aria-modal="true" aria-labelledby="pal-title" @keydown="key">
      <div class="pal-head"><h2 id="pal-title">Ort prüfen</h2><button type="button" class="pal-close" @click="emit('close')"><span class="sr-only">Schließen</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button></div>
      <PlaceSearch autofocus compact @select="p => emit('select', p)"/>
      <nav class="pal-pages" aria-label="Seiten">
        <a v-for="p in mainNav" :key="p.id" :href="href(p.id)" @click="emit('close')">{{ p.label }}</a>
      </nav>
      <p class="pal-hint"><kbd>/</kbd> oder <kbd>Strg</kbd>+<kbd>K</kbd> öffnet diese Suche · <kbd>Esc</kbd> schließt</p>
    </div>
  </div>
</template>
<style>
.pal-scrim{position:fixed;inset:0;z-index:80;background:rgb(14 24 34 / .5);backdrop-filter:blur(4px);display:grid;place-items:start center;padding:12vh var(--gutter) 0;animation:fade .2s}
.pal{width:min(640px,100%);background:var(--paper);border-radius:20px;box-shadow:var(--shadow-lift);padding:20px;animation:pal-in .3s var(--ease)}
.pal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.pal-head h2{font-size:1.4rem}
.pal-close{width:44px;height:44px;border:0;border-radius:10px;background:none;display:grid;place-items:center}
.pal-close:hover{background:var(--paper-2)}
.pal-close svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2}
.pal .ps{max-width:none}
.pal-pages{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.pal-pages a{min-height:40px;display:inline-flex;align-items:center;padding:0 14px;border-radius:999px;border:1px solid var(--line-2);text-decoration:none;font-weight:500}
.pal-pages a:hover{border-color:var(--ink)}
.pal-hint{margin-top:16px;font-size:.85rem;color:var(--ink-2)}
kbd{font:500 12px/1 var(--f-mono);padding:3px 6px;border-radius:5px;border:1px solid var(--line-2);background:var(--card)}
@keyframes fade{from{opacity:0}}
@keyframes pal-in{from{opacity:0;transform:translateY(-10px) scale(.98)}}
</style>
