<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, defineAsyncComponent } from 'vue'
import ProjectPage from './ProjectPage.vue'
import { resolveRoute, pages } from './navigation.js'
const MethodPage = defineAsyncComponent(() => import('./MethodPage.vue'))
const ResultsPage = defineAsyncComponent(() => import('./ResultsPage.vue'))
const route = ref(resolveRoute(location.hash))
const initialCase = ref(''), heading = ref(null)
async function changed() {
  route.value = resolveRoute(location.hash)
  document.title = `PreSlide · ${pages.find(p => p.id === route.value.page).label}`
  await nextTick()
  if(!route.value.section){window.scrollTo({top:0,behavior:'instant'});heading.value?.focus({preventScroll:true})}
}
function showCase(id) { initialCase.value = id; location.hash = '/vorgehen/beispiel' }
onMounted(() => { window.addEventListener('hashchange', changed); changed() })
onBeforeUnmount(() => window.removeEventListener('hashchange', changed))
</script>
<template>
  <a class="skip-link" href="#inhalt" @click.prevent="heading?.focus()">Zum Inhalt</a>
  <header class="site-header">
    <a class="brand" href="#/projekt" aria-label="PreSlide – Projekt"><svg width="34" height="32" viewBox="0 0 36 32" fill="none" aria-hidden="true"><path d="M2 27 14 6l8 13 4-6 8 14M8 27l7-12 8 12" stroke="currentColor" stroke-width="2.5"/></svg>PreSlide<span class="brand-dot">.</span></a>
    <nav aria-label="Hauptnavigation"><a v-for="(p,i) in pages" :key="p.id" :href="'#/'+p.id" :aria-current="route.page===p.id?'page':undefined"><span class="nav-index">0{{i+1}}</span>{{p.label}}</a></nav>
    <span class="header-caption">Hangrutschungen verstehen<br>Forschung aus Österreich</span>
  </header>
  <main id="inhalt" ref="heading" tabindex="-1" class="site-main"><ProjectPage v-if="route.page==='projekt'"/><MethodPage v-else-if="route.page==='vorgehen'" :initial-case="initialCase" :section="route.section"/><ResultsPage v-else :section="route.section" @show-case="showCase"/></main>
  <footer class="site-footer"><a class="footer-brand" href="#/projekt">PreSlide.</a><p>Retrospektive Forschung · Österreich<br>Lokale Demonstration · Stand 14. Oktober 2026</p><span>Erkenntnis vor Kennzahl.</span></footer>
</template>
