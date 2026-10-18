// Pure helpers for the Wirkungskette view (no DOM, no fetch): testable with node --test.

export const RADIUS = {min: 1000, max: 10000, step: 1000, initial: 3000}

// Every map layer carries one of three labels; the label says what kind of statement the layer makes.
export const LAYER_KIND = {
  pruefstufen: {tag: 'Befund', text: 'Relative Rangfolge aus dem eingefrorenen Geländemodell'},
  ereignisse: {tag: 'Befund', text: 'Dokumentierte Ereignisstellen vom 25.07.2016'},
  route: {tag: 'Szenario', text: 'Abwärtsroute nach steilstem Gefälle (D8)'},
  auslauf: {tag: 'Szenario', text: 'Vier Reichweitenannahmen aus der Literatur, nicht geprüft'},
  infrastruktur: {tag: 'Szenario', text: 'Liegt räumlich im Auslaufszenario'},
  relief: {tag: 'Illustration', text: 'Schummerung aus dem 30-m-Geländemodell'},
  hoehenlinien: {tag: 'Illustration', text: 'Höhenlinien alle 50 m'},
}

export const CLASS_COLORS = {1: '#7a1e48', 2: '#c4523a', 3: '#e9a85c', 4: '#f0e2c4'}
export const NOT_ASSESSED_COLOR = '#78828c'

export const INFRA = [
  {key: 'gebaeude', label: 'Gebäude', unit: 'Stück'},
  {key: 'strasse', label: 'Straßen', unit: 'Abschnitte'},
  {key: 'weg', label: 'Forst- und Feldwege', unit: 'Abschnitte'},
  {key: 'bahn', label: 'Bahn', unit: 'Abschnitte'},
]

export const STATUS_SHORT = {
  gestoppt: 'endet im Gebiet',
  rand: 'Rand erreicht, Ende unbekannt',
  nodata: 'Höhenlücke, nicht beurteilbar',
  senke: 'endet in einer Senke',
  max_laenge: 'Höchstlänge erreicht',
}

export const REASON_TEXT = {
  slope_below_minimum: 'flacher als 5° (außerhalb des Modellbereichs)',
  catchment_truncated: 'Einzugsgebiet am Rand abgeschnitten',
  outside_austria: 'außerhalb Österreichs',
  terrain_not_computable: 'Gelände nicht berechenbar',
  elevation_out_of_range: 'Höhe außerhalb des Modellbereichs',
  no_land_cover: 'Landbedeckung nicht eindeutig',
  no_geology: 'Geologie nicht eindeutig',
}

const nf0 = new Intl.NumberFormat('de-AT', {maximumFractionDigits: 0})
const nf1 = new Intl.NumberFormat('de-AT', {maximumFractionDigits: 1, minimumFractionDigits: 1})

export function count(v) { return v == null || !Number.isFinite(Number(v)) ? '–' : nf0.format(Number(v)) }
export function percent(share) { return share == null || !Number.isFinite(share) ? '–' : `${nf1.format(share * 100)} %` }
export function meters(v) {
  if (v == null || !Number.isFinite(v)) return '–'
  return v >= 1000 ? `${nf1.format(v / 1000)} km` : `${nf0.format(v)} m`
}

export function clampRadius(value) {
  const v = Math.round(Number(value) / RADIUS.step) * RADIUS.step
  if (!Number.isFinite(v)) return RADIUS.initial
  return Math.min(RADIUS.max, Math.max(RADIUS.min, v))
}

// Shortest and longest scenario reach; only scenarios that stopped inside the area bound the band from above.
export function scenarioBand(szenarien) {
  const list = (szenarien || []).filter(s => Number.isFinite(s.laenge_m))
  if (!list.length) return null
  const lengths = list.map(s => s.laenge_m)
  const open = list.filter(s => s.status !== 'gestoppt')
  return {min: Math.min(...lengths), max: Math.max(...lengths), offen: open.map(s => s.id)}
}

// Infrastructure counts of the band: first scenario (shortest) and widest reach (any scenario).
export function infraBand(szenarien) {
  const out = {}
  for (const i of INFRA) {
    const values = (szenarien || []).map(s => s.infrastruktur?.[i.key]?.anzahl ?? 0)
    out[i.key] = values.length ? {min: Math.min(...values), max: Math.max(...values)} : {min: 0, max: 0}
  }
  return out
}

// Compact range text: "0" or "2–13".
export function rangeText(r) { return r.min === r.max ? count(r.min) : `${count(r.min)}–${count(r.max)}` }

// Profile chart geometry in SVG units. x = horizontal distance, y = elevation (up).
export function profileGeometry(profil, szenarien, {width = 900, height = 260, pad = {l: 52, r: 16, t: 18, b: 34}} = {}) {
  const d = profil?.distanz_m || [], z = profil?.hoehe_m || []
  if (d.length < 2 || d.length !== z.length) return null
  const energy = (szenarien || []).flatMap(s => s.energielinie_m || [])
  const zMin = Math.min(...z), zMax = Math.max(...z, ...energy)
  const span = Math.max(zMax - zMin, 10)
  const lo = zMin - span * 0.08, hi = zMax + span * 0.06
  const xMax = d[d.length - 1]
  const X = v => pad.l + (v / xMax) * (width - pad.l - pad.r)
  const Y = v => pad.t + (1 - (v - lo) / (hi - lo)) * (height - pad.t - pad.b)
  const line = d.map((v, i) => `${i ? 'L' : 'M'}${X(v).toFixed(1)},${Y(z[i]).toFixed(1)}`).join('')
  const area = `${line}L${X(xMax).toFixed(1)},${Y(lo).toFixed(1)}L${X(0).toFixed(1)},${Y(lo).toFixed(1)}Z`
  const energyLines = (szenarien || []).filter(s => s.energielinie_m?.length).map(s => ({
    id: s.id,
    path: s.energielinie_m.map((v, i) => `${i ? 'L' : 'M'}${X(d[i]).toFixed(1)},${Y(v).toFixed(1)}`).join(''),
  }))
  const at = dist => { // elevation on the profile at a distance (linear between samples)
    let i = d.findIndex(v => v >= dist)
    if (i <= 0) return z[Math.max(i, 0)]
    const f = (dist - d[i - 1]) / (d[i] - d[i - 1] || 1)
    return z[i - 1] + f * (z[i] - z[i - 1])
  }
  const stops = (szenarien || []).map(s => ({id: s.id, x: X(Math.min(s.laenge_m, xMax)), y: Y(at(Math.min(s.laenge_m, xMax))), status: s.status, label: s.bezeichnung}))
  const ticks = niceTicks(0, xMax, 5).map(v => ({v, x: X(v)}))
  const yTicks = niceTicks(lo, hi, 4).map(v => ({v, y: Y(v)}))
  return {width, height, pad, X, Y, line, area, energyLines, stops, ticks, yTicks, xMax, lo, hi}
}

export function niceTicks(a, b, n) {
  const raw = (b - a) / Math.max(n, 1)
  const mag = 10 ** Math.floor(Math.log10(raw || 1))
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || raw
  const out = []
  for (let v = Math.ceil(a / step) * step; v <= b + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000)
  return out
}

// Words that must never describe these layers (relative ranks and scenarios are neither probabilities nor risk).
export const FORBIDDEN_WORDS = /wahrscheinlich|risiko|gefährd|gefaehrd/i
