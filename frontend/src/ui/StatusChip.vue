<script setup>
// Study status as a compact chip; the status vocabulary is fixed so studies are never mixed.
const props = defineProps({status: {type: String, required: true}})
const known = {
  versiegelt: {label: 'Versiegelter Test', cls: 'sealed'},
  explorativ: {label: 'Explorativ', cls: 'expl'},
  demonstration: {label: 'Demonstration', cls: 'demo'},
  anwendung: {label: 'Anwendung', cls: 'demo'},
  eingefroren: {label: 'Eingefroren', cls: 'sealed'},
  registriert: {label: 'Registriert, kein Ergebnis', cls: 'plan'},
  plan: {label: 'Plan', cls: 'plan'},
  abgeschlossen: {label: 'Abgeschlossen', cls: 'sealed'},
  lokal: {label: 'Bericht nur lokal', cls: 'plan'},
}
const s = known[props.status] ?? {label: props.status, cls: 'plan'}
</script>
<template><span class="chip" :class="'chip-' + s.cls">{{ s.label }}</span></template>
<style>
.chip{display:inline-flex;align-items:center;gap:6px;height:26px;padding:0 10px;border-radius:999px;font:500 11.5px/1 var(--f-mono);letter-spacing:.04em;white-space:nowrap;border:1px solid}
.chip::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor}
.chip-sealed{color:var(--moss);border-color:color-mix(in srgb,var(--moss) 40%,transparent);background:var(--moss-soft)}
.chip-expl{color:#7A4B12;border-color:#E6C9A0;background:#FBF1E3}
.chip-demo{color:#244A6B;border-color:#BFD6E2;background:#E9F2F6}
.chip-plan{color:var(--ink-2);border-color:var(--line-2);background:var(--paper)}
.dark .chip{background:transparent}
.dark .chip-sealed{color:#B9D3B2;border-color:rgb(185 211 178 / .4)}
.dark .chip-expl{color:#F1C995;border-color:rgb(241 201 149 / .4)}
.dark .chip-demo,.dark .chip-plan{color:var(--glacier);border-color:rgb(141 182 199 / .4)}
</style>
