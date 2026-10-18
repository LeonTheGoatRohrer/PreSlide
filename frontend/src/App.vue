<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, defineAsyncComponent } from 'vue'
import StartPage from './StartPage.vue'
import { resolveRoute, mainNav, researchPages, activeNav, isResearch, pageTitle } from './navigation.js'
const ProjectPage = defineAsyncComponent(() => import('./ProjectPage.vue'))
const MethodPage = defineAsyncComponent(() => import('./MethodPage.vue'))
const ResultsPage = defineAsyncComponent(() => import('./ResultsPage.vue'))
const PruefgebietePage = defineAsyncComponent(() => import('./PruefgebietePage.vue'))
const BefundePage = defineAsyncComponent(() => import('./BefundePage.vue'))
const MethodikPage = defineAsyncComponent(() => import('./MethodikPage.vue'))
const ForschungPage = defineAsyncComponent(() => import('./ForschungPage.vue'))
const route = ref(resolveRoute(location.hash))
const initialCase = ref(''), heading = ref(null)
const current = computed(() => activeNav(route.value.page))
async function changed() {
  route.value = resolveRoute(location.hash)
  document.title = `Talwacht · ${pageTitle(route.value.page)}`
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
    <a class="brand" href="#/start" aria-label="Talwacht – Startseite"><svg width="34" height="32" viewBox="0 0 36 32" fill="none" aria-hidden="true"><path d="M2 27 14 6l8 13 4-6 8 14M8 27l7-12 8 12" stroke="currentColor" stroke-width="2.5"/></svg>Talwacht<span class="brand-dot">.</span></a>
    <nav class="main-nav" aria-label="Hauptnavigation"><a v-for="p in mainNav" :key="p.id" :href="'#/'+p.id" :aria-current="current===p.id?'page':undefined"><span :class="{'nav-long':p.short}">{{p.label}}</span><span v-if="p.short" class="nav-short">{{p.short}}</span></a></nav>
    <span class="header-caption">Forschungsprototyp<br>Österreich</span>
  </header>
  <nav v-if="isResearch(route.page)" class="research-bar" aria-label="Forschungsbereich">
    <a href="#/forschung" :aria-current="route.page==='forschung'?'page':undefined">Forschungsbereich</a>
    <a v-for="p in researchPages" :key="p.id" :href="'#/'+p.id" :aria-current="route.page===p.id?'page':undefined">{{p.label}}</a>
  </nav>
  <main id="inhalt" ref="heading" tabindex="-1" class="site-main">
    <StartPage v-if="route.page==='start'"/>
    <PruefgebietePage v-else-if="route.page==='pruefgebiete'"/>
    <BefundePage v-else-if="route.page==='befunde'"/>
    <MethodikPage v-else-if="route.page==='methodik'"/>
    <ForschungPage v-else-if="route.page==='forschung'"/>
    <ProjectPage v-else-if="route.page==='projekt'"/>
    <MethodPage v-else-if="route.page==='vorgehen'" :initial-case="initialCase" :section="route.section"/>
    <ResultsPage v-else :section="route.section" @show-case="showCase"/>
  </main>
  <footer class="site-footer"><a class="footer-brand" href="#/start">Talwacht.</a><p>Retrospektive Forschung · Österreich<br>Lokale Demonstration · Stand 18. Oktober 2026</p><span>Erkenntnis vor Kennzahl.</span></footer>
</template>
