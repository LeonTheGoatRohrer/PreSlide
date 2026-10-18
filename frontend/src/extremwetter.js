// Tolerant reader for GET /api/extremwetter (delivered by the Extremwetter session).
// The final field names are agreed later; until then only figures that carry a label, a finite
// value and a finite two-sided interval are shown. Anything else is counted, never guessed.
const finite = v => typeof v === 'number' && Number.isFinite(v)
const first = (item, keys) => keys.map(k => item?.[k]).find(v => v != null)

export function extremwetterFigures(bundle) {
  const list = first(bundle, ['kernzahlen', 'key_figures', 'figures'])
  if (!Array.isArray(list)) return { figures: [], skipped: 0 }
  const figures = []
  for (const item of list) {
    const label = first(item, ['label', 'bezeichnung', 'name'])
    const value = first(item, ['wert', 'value'])
    const interval = first(item, ['intervall', 'ci95', 'interval'])
    if (typeof label !== 'string' || !finite(value) || !Array.isArray(interval) || interval.length !== 2 || !interval.every(finite) || interval[0] > interval[1]) continue
    figures.push({ label, value, interval, unit: first(item, ['einheit', 'unit']) || '', note: first(item, ['hinweis', 'note']) || '' })
  }
  return { figures, skipped: list.length - figures.length }
}

// 503 is the agreed signal for "analysis not finished yet"; every other failure is a real error.
export function extremwetterState({ loading, status, data }) {
  if (loading) return 'loading'
  if (data) return 'ready'
  if (status === 503) return 'pending'
  if (status === 404) return 'missing'  // endpoint not part of this build yet
  return 'error'
}
