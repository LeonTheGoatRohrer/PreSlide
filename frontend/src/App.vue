<script setup>
import {ref, computed, onMounted, onBeforeUnmount, nextTick, defineAsyncComponent} from 'vue'
import {resolveRoute, pageTitle} from './navigation.js'
import {openCheck} from './session.js'
import NavBar from './ui/NavBar.vue'
import SiteFooter from './ui/SiteFooter.vue'
import StartPage from './pages/StartPage.vue'
const AboutPage = defineAsyncComponent(() => import('./pages/AboutPage.vue'))
const InterimPage = defineAsyncComponent(() => import('./pages/InterimPage.vue'))
const CheckPage = defineAsyncComponent(() => import('./pages/CheckPage.vue'))
const SearchPalette = defineAsyncComponent(() => import('./ui/SearchPalette.vue'))

const route = ref(resolveRoute(location.hash))
const palette = ref(false), main = ref(null)
const isCheck = computed(() => route.value.page === 'check')
let lastPage = route.value.page

function scrollToAnchor(anchor, smooth) {
  const el = anchor && document.getElementById(anchor)
  if (el) el.scrollIntoView({behavior: smooth ? 'smooth' : 'instant', block: 'start'})
  return !!el
}
async function changed() {
  const next = resolveRoute(location.hash)
  if (next.redirect !== null && next.redirect !== location.hash) history.replaceState(null, '', next.redirect)
  const samePage = next.page === lastPage
  const apply = () => { route.value = next }
  palette.value = false
  // The map page has its own arrival; a cross-fade of the WebGL canvas would only blur it.
  if (!samePage && next.page !== 'check' && lastPage !== 'check' && document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const t = document.startViewTransition(apply)
    t.ready.catch(() => {}); t.finished.catch(() => {})   // an interrupted transition is harmless
    await t.updateCallbackDone.catch(apply)
  } else apply()
  lastPage = next.page
  document.title = `Talwacht · ${pageTitle(next.page)}`
  await nextTick()
  if (next.anchor) {
    // Async pages render after a tick; retry briefly until the anchor exists.
    for (let i = 0; i < 20 && !scrollToAnchor(next.anchor, samePage); i++) await new Promise(r => setTimeout(r, 100))
  } else if (!samePage) {
    window.scrollTo({top: 0, behavior: 'instant'})
    main.value?.focus({preventScroll: true})
  }
}
function selectPlace(p) { palette.value = false; openCheck(p) }
onMounted(() => { window.addEventListener('hashchange', changed); changed() })
onBeforeUnmount(() => window.removeEventListener('hashchange', changed))
</script>

<template>
  <a class="skip" href="#inhalt" @click.prevent="main?.focus()">Zum Inhalt</a>
  <NavBar :page="route.page" :hero="route.page === 'start'" :compact="isCheck" @search="palette = true"/>
  <main id="inhalt" ref="main" tabindex="-1" class="site-main">
    <StartPage v-if="route.page === 'start'"/>
    <CheckPage v-else-if="isCheck" :params="route.params"/>
    <AboutPage v-else-if="route.page === 'ueber'"/>
    <InterimPage v-else :which="route.page" :anchor="route.anchor"/>
  </main>
  <SiteFooter v-if="!isCheck"/>
  <SearchPalette v-if="palette" @close="palette = false" @select="selectPlace"/>
</template>

<style>
.skip{position:fixed;z-index:100;left:16px;top:-60px;padding:12px 16px;border-radius:10px;background:var(--ink);color:#fff;font-weight:600;transition:top .2s}
.skip:focus{top:16px}
.site-main{outline:none;min-height:60vh}
</style>
