<script setup>
// Floating navigation: transparent on the hero, paper with blur after 40 px; compact on the Hang-Check.
import {ref, computed, watch, onMounted, onBeforeUnmount, nextTick} from 'vue'
import {mainNav, primaryAction, href} from '../navigation.js'
import Signet from './Signet.vue'
const props = defineProps({page: {type: String, required: true}, hero: Boolean, compact: Boolean})
const emit = defineEmits(['search'])
const scrolled = ref(false), menu = ref(false)
const links = ref([]), list = ref(null), bar = ref({x: 0, w: 0, on: false}), menuBtn = ref(null), sheet = ref(null)
const onHero = computed(() => props.hero && !scrolled.value && !menu.value)

function onScroll() { scrolled.value = window.scrollY > 40 }
function measure() {
  const i = mainNav.findIndex(p => p.id === props.page), el = links.value[i]
  if (!el || !list.value) { bar.value = {...bar.value, on: false}; return }
  const a = el.getBoundingClientRect(), b = list.value.getBoundingClientRect()
  bar.value = {x: a.left - b.left, w: a.width, on: true}
}
function back() { if (history.length > 1) history.back(); else location.hash = '#/' }
function key(e) {
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable
  if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) { e.preventDefault(); emit('search') }
  if (e.key === 'Escape' && menu.value) { menu.value = false; menuBtn.value?.focus() }
}
watch(() => props.page, async () => { menu.value = false; await nextTick(); measure() })
watch(menu, async open => {
  document.documentElement.style.overflow = open ? 'hidden' : ''
  if (open) { await nextTick(); sheet.value?.querySelector('a')?.focus() }
})
onMounted(() => {
  onScroll(); measure()
  window.addEventListener('scroll', onScroll, {passive: true}); window.addEventListener('resize', measure); window.addEventListener('keydown', key)
  document.fonts?.ready.then(measure)
})
onBeforeUnmount(() => { window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', measure); window.removeEventListener('keydown', key); document.documentElement.style.overflow = '' })
</script>

<template>
  <header class="nav" :class="{'on-hero': onHero, compact, open: menu}">
    <div class="nav-bar">
      <a class="nav-brand" :href="href('start')" aria-label="Talwacht – Startseite"><Signet/><span>Talwacht</span></a>

      <template v-if="compact">
        <button type="button" class="nav-tool" @click="back"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5 8 12l7 7"/></svg><span>Zurück</span></button>
      </template>
      <template v-else>
        <nav class="nav-links" aria-label="Hauptnavigation">
          <ul ref="list">
            <li v-for="(p, i) in mainNav" :key="p.id"><a :ref="el => (links[i] = el)" :href="href(p.id)" :aria-current="page === p.id ? 'page' : undefined">{{ p.label }}</a></li>
          </ul>
          <span class="nav-mark" :class="{on: bar.on}" :style="{transform: `translateX(${bar.x}px)`, width: bar.w + 'px'}" aria-hidden="true"></span>
        </nav>
        <div class="nav-actions">
          <button type="button" class="nav-search" aria-label="Ort suchen (Taste / oder Strg+K)" title="Ort suchen ( / )" @click="emit('search')">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg>
          </button>
          <a class="btn btn-primary nav-cta" :href="href(primaryAction.id)" :aria-current="page === 'check' ? 'page' : undefined">{{ primaryAction.label }}</a>
          <button ref="menuBtn" type="button" class="nav-menu" :aria-expanded="menu" aria-controls="nav-sheet" @click="menu = !menu">
            <span class="sr-only">{{ menu ? 'Menü schließen' : 'Menü öffnen' }}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path v-if="!menu" d="M4 8h16M4 16h16"/><path v-else d="m6 6 12 12M18 6 6 18"/></svg>
          </button>
        </div>
      </template>
    </div>

    <div v-if="menu" id="nav-sheet" ref="sheet" class="nav-sheet" role="dialog" aria-modal="true" aria-label="Menü">
      <a :href="href('start')">Start</a>
      <a v-for="p in mainNav" :key="p.id" :href="href(p.id)" :aria-current="page === p.id ? 'page' : undefined">{{ p.label }}</a>
      <a class="btn btn-primary" :href="href('check')">Hang prüfen</a>
    </div>
  </header>
</template>

<style>
.nav{position:fixed;z-index:50;top:16px;left:0;right:0;padding:0 var(--gutter);pointer-events:none}
.nav-bar{pointer-events:auto;max-width:1200px;margin:0 auto;height:var(--nav-h);display:flex;align-items:center;gap:20px;padding:0 10px 0 18px;border-radius:16px;
  background:rgb(245 243 238 / .82);backdrop-filter:blur(14px) saturate(1.2);-webkit-backdrop-filter:blur(14px) saturate(1.2);
  box-shadow:0 1px 0 rgb(255 255 255 / .6) inset,0 10px 30px -14px rgb(19 32 43 / .3),0 0 0 1px var(--line);
  transition:background-color .2s,box-shadow .2s,color .2s;color:var(--ink)}
.on-hero .nav-bar{background:transparent;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none;color:#fff}
.nav-brand{display:inline-flex;align-items:center;gap:10px;text-decoration:none;font:650 1.3rem/1 var(--f-display);font-stretch:125%;letter-spacing:-.02em;min-height:44px}
.nav-brand .signet{width:34px;height:28px;color:var(--moss)}
.on-hero .nav-brand .signet{color:#fff}
.nav-links{position:relative;margin-left:auto}
.nav-links ul{display:flex;gap:4px;list-style:none;margin:0;padding:0}
.nav-links a{display:flex;align-items:center;height:44px;padding:0 14px;border-radius:10px;text-decoration:none;font-weight:500;font-size:.98rem;transition:background-color .2s}
.nav-links a:hover{background:rgb(19 32 43 / .06)}
.on-hero .nav-links a:hover{background:rgb(255 255 255 / .12)}
.nav-links a[aria-current]{font-weight:600}
.nav-mark{position:absolute;left:0;bottom:2px;height:2px;border-radius:2px;background:var(--moss);opacity:0;transition:transform .35s var(--ease),width .35s var(--ease),opacity .2s}
.nav-mark.on{opacity:1}
.on-hero .nav-mark{background:#fff}
.nav-actions{display:flex;align-items:center;gap:8px}
.nav-search,.nav-menu,.nav-tool{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-width:44px;height:44px;border-radius:10px;border:0;background:none;color:inherit;font-weight:600}
.nav-search:hover,.nav-menu:hover,.nav-tool:hover{background:rgb(19 32 43 / .06)}
.on-hero .nav-search:hover,.on-hero .nav-menu:hover{background:rgb(255 255 255 / .12)}
.nav-search svg,.nav-menu svg,.nav-tool svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}
.nav-tool{padding:0 12px}
.compact .nav-bar{max-width:none}
.nav-cta{min-height:44px;padding:0 18px}
.nav-menu{display:none}
.nav-sheet{pointer-events:auto;position:fixed;inset:0;top:0;z-index:-1;background:var(--paper);padding:112px var(--gutter) 32px;display:flex;flex-direction:column;gap:4px;animation:sheet-in .3s var(--ease)}
.nav-sheet a{font:650 2rem/1.1 var(--f-display);font-stretch:118%;letter-spacing:-.02em;text-decoration:none;padding:14px 4px;border-bottom:1px solid var(--line)}
.nav-sheet a[aria-current]{color:var(--moss)}
.nav-sheet .btn{margin-top:24px;font:600 1.1rem/1 var(--f-text);border:0;min-height:56px}
@keyframes sheet-in{from{opacity:0;transform:translateY(-8px)}}
@media (max-width:960px){
  .nav-links{display:none}
  .nav-actions{margin-left:auto}
  .nav-menu{display:inline-flex}
}
@media (max-width:420px){
  .nav-search{display:none}
  .nav-brand span{font-size:1.15rem}
  .nav-cta{padding:0 14px}
  .nav-tool span{display:none}
}
@media print{.nav{display:none}}
</style>
