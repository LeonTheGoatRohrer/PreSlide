// Pure helpers of the study atlas (GET /api/studien). Values are only formatted, never derived or filled.
import {fmt} from './metricDefinitions.js'

const signed = v => (v > 0 ? '+' : v < 0 ? '−' : '±') + fmt(Math.abs(v))
const pct = v => (v * 100).toLocaleString('de-AT', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + ' %'
export const FORMAT = {
  auc: v => fmt(v), delta: signed, anteil: pct,
  zahl: v => Math.round(v).toLocaleString('de-AT'),
  faktor: v => v.toLocaleString('de-AT', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + '×',
  p: v => fmt(v, 3),
}
export const formatValue = (art, v) => (FORMAT[art] ?? FORMAT.auc)(v)

/** Scale of the interval plot per kind of figure; widened so the stored interval is always inside. */
export function plotScale(fig) {
  if (!fig?.intervall || !['auc', 'delta', 'anteil'].includes(fig.art)) return null
  const base = {auc: [0.3, 1], delta: [-0.25, 0.25], anteil: [0, 1]}[fig.art]
  const lo = Math.min(base[0], fig.intervall[0]), hi = Math.max(base[1], fig.intervall[1])
  return {min: lo, max: hi, reference: fig.bezug ?? (fig.art === 'delta' ? 0 : fig.art === 'auc' ? 0.5 : null)}
}

/** Studies of the chosen group (all for '' ), sorted by date then registry order. */
export function filterStudies(studies, group) {
  return studies.map((s, i) => ({s, i})).filter(({s}) => !group || (s.gruppen ?? []).includes(group))
    .sort((a, b) => (a.s.datum ?? '').localeCompare(b.s.datum ?? '') || a.i - b.i).map(({s}) => s)
}

/** Which study an address anchor opens (#/studien#v04): its id or one of its registered anchors. */
export function studyForAnchor(studies, anchor) {
  if (!anchor) return null
  return studies.find(s => s.id === anchor || (s.anker ?? []).includes(anchor)) ?? null
}

export function headline(study) {
  return (study.kennzahlen ?? []).find(f => f.verfuegbar) ?? null
}
