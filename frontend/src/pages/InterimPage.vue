<script setup>
// Interim (milestones 1–3 of the redesign): the earlier pages, unchanged in content, at their new addresses.
// Each one is replaced by its redesigned page in a later milestone and then deleted.
import {defineAsyncComponent} from 'vue'
import '../legacy.css'
defineProps({which: {type: String, required: true}})
const MethodikPage = defineAsyncComponent(() => import('../MethodikPage.vue'))
const PruefgebietePage = defineAsyncComponent(() => import('../PruefgebietePage.vue'))
const BefundePage = defineAsyncComponent(() => import('../BefundePage.vue'))
</script>
<template>
  <div class="legacy interim">
    <main>
      <template v-if="which === 'so-funktionierts'"><MethodikPage/><div id="wirkungskette"><PruefgebietePage/></div></template>
      <BefundePage v-else-if="which === 'belastbar'"/>
    </main>
  </div>
</template>
<style>.interim{padding-top:96px;background:#fff}</style>
