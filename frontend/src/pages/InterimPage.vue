<script setup>
// Interim (milestones 1–3 of the redesign): the earlier pages, unchanged in content, at their new addresses.
// Each one is replaced by its redesigned page in a later milestone and then deleted.
import {defineAsyncComponent, ref} from 'vue'
import '../legacy.css'
defineProps({which: {type: String, required: true}, anchor: {type: String, default: ''}})
const MethodikPage = defineAsyncComponent(() => import('../MethodikPage.vue'))
const PruefgebietePage = defineAsyncComponent(() => import('../PruefgebietePage.vue'))
const BefundePage = defineAsyncComponent(() => import('../BefundePage.vue'))
const ProjectPage = defineAsyncComponent(() => import('../ProjectPage.vue'))
const MethodPage = defineAsyncComponent(() => import('../MethodPage.vue'))
const ResultsPage = defineAsyncComponent(() => import('../ResultsPage.vue'))
const initialCase = ref('')
function showCase(id) { initialCase.value = id; location.hash = '#/studien#baseline' }
</script>
<template>
  <div class="legacy interim">
    <main>
      <template v-if="which === 'so-funktionierts'"><MethodikPage/><div id="wirkungskette"><PruefgebietePage/></div></template>
      <BefundePage v-else-if="which === 'belastbar'"/>
      <template v-else-if="which === 'studien'">
        <div id="kernfrage"><ProjectPage/></div>
        <div id="baseline"><MethodPage :initial-case="initialCase" :section="anchor === 'baseline' ? 'beispiel' : ''"/></div>
        <span id="v04"></span><span id="v05"></span><span id="vergleich"></span>
        <ResultsPage :section="['v04', 'v05', 'vergleich'].includes(anchor) ? anchor : ''" @show-case="showCase"/>
      </template>
    </main>
  </div>
</template>
<style>.interim{padding-top:96px;background:#fff}</style>
