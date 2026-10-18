<script setup>
// Accessible combobox for the offline municipality search, plus "Mein Standort" and the example areas.
import {ref, computed, onMounted, onBeforeUnmount, watch} from 'vue'
import {searchPlaces, loadExamples, locate} from '../places.js'
const props = defineProps({tone: {type: String, default: 'light'}, autofocus: Boolean, compact: Boolean, label: {type: String, default: 'Gemeinde oder Ort eingeben'}})
const emit = defineEmits(['select'])
const id = 'ps-' + Math.random().toString(36).slice(2, 8)
const query = ref(''), places = ref([]), examples = ref([]), open = ref(false), active = ref(-1)
const busy = ref(false), message = ref(''), unavailable = ref(false), locating = ref(false)
const input = ref(null), root = ref(null)
let timer = 0, seq = 0, chosen = false

const options = computed(() => query.value.trim().length >= 2 && !unavailable.value
  ? places.value.map(p => ({...p, kind: 'ort'}))
  : examples.value.map(p => ({...p, kind: 'beispiel'})))
const heading = computed(() => query.value.trim().length >= 2 && !unavailable.value ? 'Gemeinden' : 'Beispielgebiete')

watch(query, q => {
  clearTimeout(timer); active.value = -1; message.value = ''
  if (chosen) { chosen = false; busy.value = false; return }   // showing the chosen name is not a new search
  if (q.trim().length < 2) { places.value = []; busy.value = false; return }
  busy.value = true
  timer = setTimeout(async () => {
    const mine = ++seq
    try {
      const r = await searchPlaces(q)
      if (mine !== seq) return
      unavailable.value = r.unavailable; places.value = r.places
      if (r.unavailable) message.value = 'Die Ortssuche ist in diesem Stand noch nicht angebunden. Wähle ein Beispielgebiet oder klicke im Hang-Check auf die Karte.'
      else if (!r.places.length) message.value = `Keine Gemeinde „${q.trim()}“ gefunden. Prüfe die Schreibweise.`
    } catch (e) { if (mine === seq) message.value = e.message }
    finally { if (mine === seq) busy.value = false }
  }, 180)
})

function choose(p) {
  if (!p) return
  open.value = false; chosen = true; query.value = p.kind === 'beispiel' ? p.name : p.label
  emit('select', {...p})
}
function onKey(e) {
  if (e.key === 'ArrowDown') { e.preventDefault(); open.value = true; active.value = Math.min(options.value.length - 1, active.value + 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); active.value = Math.max(0, active.value - 1) }
  else if (e.key === 'Enter') { e.preventDefault(); choose(options.value[active.value >= 0 ? active.value : 0]) }
  else if (e.key === 'Escape') { if (open.value) { e.stopPropagation(); open.value = false } }
}
async function useLocation() {
  locating.value = true; message.value = ''
  try { emit('select', await locate()) } catch (e) { message.value = e.message } finally { locating.value = false }
}
function outside(e) { if (!root.value?.contains(e.target)) open.value = false }
onMounted(async () => {
  document.addEventListener('pointerdown', outside)
  if (props.autofocus) input.value?.focus()
  try { examples.value = (await loadExamples()).examples } catch { /* examples are optional here */ }
})
onBeforeUnmount(() => { document.removeEventListener('pointerdown', outside); clearTimeout(timer) })
defineExpose({focus: () => input.value?.focus()})
</script>

<template>
  <div ref="root" class="ps" :class="['ps-' + tone, {compact}]">
    <div class="ps-row">
      <label class="ps-field" :for="id + '-in'">
        <span class="sr-only">{{ label }}</span>
        <svg class="ps-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg>
        <input :id="id + '-in'" ref="input" v-model="query" type="search" autocomplete="off" spellcheck="false" :placeholder="label"
               role="combobox" :aria-expanded="open && options.length > 0" :aria-controls="id + '-list'" aria-autocomplete="list"
               :aria-activedescendant="active >= 0 ? id + '-o' + active : undefined"
               @focus="open = true" @input="open = true" @keydown="onKey">
        <span v-if="busy" class="ps-spin" aria-hidden="true"></span>
      </label>
      <button type="button" class="ps-locate" :disabled="locating" @click="useLocation">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/><circle cx="12" cy="12" r="7.5"/></svg>
        <span>{{ locating ? 'Ortung …' : 'Mein Standort' }}</span>
      </button>
    </div>
    <div v-show="open && options.length" :id="id + '-list'" class="ps-list" role="listbox" :aria-label="heading">
      <p class="ps-head" aria-hidden="true">{{ heading }}</p>
      <button v-for="(p, i) in options" :id="id + '-o' + i" :key="p.kind + p.id" type="button" role="option" tabindex="-1"
              :aria-selected="i === active" :class="{on: i === active}" @mouseenter="active = i" @click="choose(p)">
        <span class="ps-name">{{ p.name }}</span><span class="ps-meta">{{ p.kind === 'beispiel' ? 'Beispiel' : p.region }}</span>
      </button>
    </div>
    <p v-if="message" class="ps-msg" role="status">{{ message }}</p>
  </div>
</template>

<style>
.ps{position:relative;width:100%;max-width:560px}
.ps-row{display:flex;gap:10px}
.ps-field{position:relative;flex:1;display:flex;align-items:center}
.ps-field input{width:100%;height:56px;border-radius:14px;border:1px solid var(--line-2);background:var(--card);padding:0 44px 0 48px;font-size:1.05rem;color:var(--ink);box-shadow:var(--shadow);-webkit-appearance:none;appearance:none}
.ps-field input::placeholder{color:var(--ink-2);opacity:1}
.ps-field input::-webkit-search-cancel-button{display:none}
.ps-field input:focus-visible{outline:3px solid var(--moss);outline-offset:2px}
.ps-icon{position:absolute;left:16px;width:22px;height:22px;fill:none;stroke:var(--ink-2);stroke-width:2;pointer-events:none}
.ps-spin{position:absolute;right:16px;width:18px;height:18px;border-radius:50%;border:2px solid var(--line-2);border-top-color:var(--moss);animation:ps-spin .8s linear infinite}
@keyframes ps-spin{to{transform:rotate(1turn)}}
.ps-locate{display:inline-flex;align-items:center;gap:8px;height:56px;padding:0 18px;border-radius:14px;border:1px solid var(--line-2);background:var(--card);font-weight:600;white-space:nowrap;box-shadow:var(--shadow)}
.ps-locate svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8}
.ps-locate:disabled{opacity:.7;cursor:progress}
.ps-dark .ps-field input{background:rgb(245 243 238 / .96);border-color:transparent}
.ps-dark .ps-locate{background:rgb(14 24 34 / .5);border-color:rgb(255 255 255 / .35);color:#fff;backdrop-filter:blur(10px);box-shadow:none}
.ps-dark .ps-locate:hover{background:rgb(14 24 34 / .7)}
.ps-dark .ps-msg{color:#fff;background:rgb(14 24 34 / .6);backdrop-filter:blur(8px)}
.ps-list{position:absolute;z-index:60;left:0;right:0;top:calc(100% + 8px);background:var(--card);border-radius:16px;box-shadow:var(--shadow-lift);padding:8px;max-height:min(360px,50vh);overflow:auto}
.ps-head{font:500 11px/1 var(--f-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--ink-2);padding:10px 12px 8px}
.ps-list button{display:flex;width:100%;align-items:baseline;justify-content:space-between;gap:16px;min-height:46px;padding:10px 12px;border:0;border-radius:10px;background:none;text-align:left;color:var(--ink)}
.ps-list button.on{background:var(--paper-2)}
.ps-name{font-weight:600}
.ps-meta{font:400 13px/1.2 var(--f-mono);color:var(--ink-2)}
.ps-msg{margin-top:10px;font-size:.95rem;color:var(--ink-2);padding:8px 12px;border-radius:10px}
.ps.compact .ps-field input,.ps.compact .ps-locate{height:48px;box-shadow:none}
@media (max-width:560px){
  .ps-row{flex-direction:column}
  .ps-locate{height:48px;justify-content:center}
}
</style>
