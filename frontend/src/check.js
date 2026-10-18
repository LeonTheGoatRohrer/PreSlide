// Pure helpers of the Hang-Check page (unit-tested without a browser).
// The heavy-rain switch only selects the view: it never adds a parameter to the request.
import {distanceM} from './hangkarte.js'

export const RADIUS = {min: 1000, max: 3000, step: 500, default: 2000}

export function clampRadius(value, limits = RADIUS) {
  const v = Number(value)
  if (!Number.isFinite(v)) return limits.default
  const stepped = Math.round((v - limits.min) / limits.step) * limits.step + limits.min
  return Math.min(limits.max, Math.max(limits.min, stepped))
}

/** Page state from the address (#/check?lon=…&lat=…&r=…&regen=1). Invalid coordinates give no place. */
export function readParams(params = {}, limits = RADIUS) {
  const lon = Number(params.lon), lat = Number(params.lat)
  const place = params.lon != null && params.lat != null && Number.isFinite(lon) && Number.isFinite(lat)
    ? {id: 'url', name: params.ort || 'Gewählter Punkt', label: params.ort || 'Gewählter Punkt', region: '', longitude: lon, latitude: lat, radius_m: null}
    : null
  return {place, radius: params.r != null ? clampRadius(params.r, limits) : limits.default, rain: params.regen === '1'}
}

/** Turns a Hang-Check response into its result, or throws a CheckFailure (kind + German message).
 * Failures are thrown so the Hang-Check layer loader never keeps them as a result. */
export class CheckFailure extends Error {
  constructor(kind, message) { super(message); this.kind = kind }
}
export async function readCheck(r) {
  let json = null
  try { json = await r.json() } catch { /* error bodies may be empty */ }
  if (r.ok && json) return json
  const detail = typeof json?.detail === 'string' ? json.detail : ''
  if (r.status === 503) throw new CheckFailure('busy', 'Gerade läuft eine andere Berechnung. Gleich noch einmal versuchen.')
  if (r.status === 422) throw new CheckFailure('outside', detail || 'Dieser Ort lässt sich nicht prüfen. Wähle einen Ort in Österreich.')
  if (r.status === 404) throw new CheckFailure('missing', 'Der Hang-Check-Rechner ist in diesem Stand der Seite noch nicht eingebunden.')
  throw new CheckFailure('error', `Der Hang-Check ist gerade nicht erreichbar (HTTP ${r.status}).`)
}
export const OFFLINE = () => new CheckFailure('offline', 'Keine Verbindung zum lokalen Talwacht-Server.')

/** Adds the distance from the centre to every cell (for the radial reveal) and normalises the review points. */
export function normalize(json, centre) {
  const features = (json?.zellen?.features ?? []).filter(f => f?.properties && [1, 2].includes(f.properties.stufe)).map(f => {
    const ring = f.geometry?.coordinates?.[0] ?? []
    const n = Math.max(1, ring.length - 1)
    const c = ring.slice(0, n).reduce((a, p) => ({longitude: a.longitude + p[0] / n, latitude: a.latitude + p[1] / n}), {longitude: 0, latitude: 0})
    return {...f, properties: {...f.properties, d: Math.round(distanceM(centre, c))}}
  })
  const points = (json?.pruefpunkte ?? []).filter(p => Number.isFinite(p.longitude) && Number.isFinite(p.latitude))
  return {cells: {type: 'FeatureCollection', features}, points, maxD: Math.max(1, ...features.map(f => f.properties.d))}
}

export const coord = v => v.toLocaleString('de-AT', {minimumFractionDigits: 5, maximumFractionDigits: 5})
/** Zoom so that the radius fills the visible map comfortably. */
export const zoomFor = radiusM => 14.6 - Math.log2(radiusM / 1000)

/** Flow paths are loaded when the heavy-rain view is on or when one review point is asked about. */
export const wantFlows = (rain, askedNr) => !!rain || askedNr != null

/**
 * GET /api/hangcheck/fliesswege → per review point the short (median reach) and long (largest observed reach)
 * scenario, plus map features. Paths without coordinates are dropped, never drawn as guessed lines.
 */
export function normalizeFlows(json) {
  const byNr = {}, features = []
  for (const f of json?.fliesswege ?? []) {
    const sorted = [...(f.szenarien ?? [])].sort((a, b) => a.reichweite_m - b.reichweite_m)
    const [kurz, lang] = [sorted[0] ?? null, sorted.at(-1) ?? null]
    byNr[f.nr] = {nr: f.nr, kurz, lang: lang !== kurz ? lang : null}
    if (lang?.korridor?.coordinates?.[0]?.length > 3) features.push({type: 'Feature', properties: {nr: f.nr, art: 'korridor'}, geometry: lang.korridor})
    for (const [art, sc] of [['lang', lang], ['kurz', kurz]])
      if (sc?.weg?.length > 1) features.push({type: 'Feature', properties: {nr: f.nr, art}, geometry: {type: 'LineString', coordinates: sc.weg}})
  }
  return {byNr, features, typen: json?.typen ?? {}, hinweis: json?.hinweis ?? '', osm: json?.osm ?? null}
}

/** Map features to draw: all paths in the heavy-rain view, otherwise only the asked point's path. */
export function flowsToShow(flows, rain, askedNr) {
  if (!flows) return {type: 'FeatureCollection', features: []}
  const features = rain ? flows.features : flows.features.filter(f => f.properties.nr === askedNr)
  return {type: 'FeatureCollection', features}
}
