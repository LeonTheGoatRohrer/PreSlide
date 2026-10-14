<script setup>
import { computed, ref } from 'vue'
const selected = ref('B_weather_delta')
const items = {
  A_performance: ['Alle fünf Wiederholungen', 'Alle drei Modellfamilien und Merkmalsvarianten. Referenz: AP 0,167, AUC 0,5.', 13, 10],
  B_weather_delta: ['Zusätzlicher Wetternutzen', 'Gelände plus Wetter minus Gelände. Jeder Punkt: eine Wiederholung; schwarze Linie: Median. Positives Δ bedeutet Verbesserung.', 13, 4.5],
  C_event_ranks: ['Ereignisränge und Kontrollen', '45 Ereignisse pro Wiederholung, fünf Kontrollen je Ereignis. Rang eins ist der beste Rang. Gleichstände erhalten mittlere Ränge.', 13, 10],
  D_learning_curve: ['Lernkurve · explorativ', 'Drei, sechs, neun oder zwölf Trainingsgruppen je Fold. Bewertungsgruppen bleiben gleich. Linie: Median; Fläche: Spannweite über fünf Wiederholungen.', 13, 4.5],
  E_weather_differences: ['Wetterunterschiede · explorativ', 'Mittlere absolute Differenz zu fünf Kontrollen, normiert durch die Merkmalsstreuung. Verschiedene Werte belegen noch keinen Vorhersagenutzen.', 11, 7],
  F_feature_stability: ['Merkmalsstabilität · explorativ', 'Alle 22 Merkmale: Median und Spannweite. Bäume: AP-Abfall beim Durchmischen innerhalb jeder Ereignisgruppe. Regression: standardisierte Koeffizienten.', 15, 9],
  G_storm_sensitivity: ['Clustereinfluss · explorativ', 'Wetternutzen bei gleichem Gewicht je Ereignis und je Abhängigkeitsgruppe. Nur Bewertungsgewichte ändern sich; die Modelle bleiben unverändert.', 11, 4.5],
}
const current = computed(() => items[selected.value])
</script>

<template>
  <div class="stability-figures">
    <div class="figure-controls"><div class="case-picker"><label for="scientific-figure">Wissenschaftliche Abbildung</label><select id="scientific-figure" v-model="selected"><option v-for="(item,key) in items" :key="key" :value="key">{{item[0]}}</option></select></div><a :href="`/api/stability/figures/${selected}.png`" target="_blank" rel="noopener">In voller Größe öffnen</a></div>
    <figure><img :key="selected" :src="`/api/stability/figures/${selected}.png`" :width="current[2]*170" :height="current[3]*170" :alt="current[0]+'. '+current[1]" loading="lazy"/><figcaption>{{current[1]}} Alle Wiederholungen verwenden dieselben 45 Entwicklungsereignisse in 16 Abhängigkeitsgruppen; keine unabhängige Testbestätigung.</figcaption></figure>
  </div>
</template>

<style scoped>
.stability-figures{margin-top:32px}.figure-controls{display:flex;justify-content:space-between;align-items:end;gap:24px;margin-bottom:22px}.figure-controls a{min-height:44px;display:flex;align-items:center;font-size:13px;color:var(--blue)}.figure-controls select{min-height:44px;font-size:14px}.stability-figures figure{margin:0;padding:14px;border:1px solid var(--line);background:#fff}.stability-figures img{display:block;width:100%;height:auto}.stability-figures figcaption{font-size:14px;line-height:1.7;max-width:950px;padding:16px 4px 4px}@media(max-width:720px){.figure-controls{display:block}.figure-controls a{margin-top:12px}.stability-figures figure{padding:7px}}
</style>
