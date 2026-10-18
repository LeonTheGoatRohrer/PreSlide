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

/** The request body, or null when nothing may be requested (no place, or the switch is off). */
export function requestBody(place, radiusM, rain) {
  if (!rain || !place) return null
  return {longitude: Number(place.longitude.toFixed(5)), latitude: Number(place.latitude.toFixed(5)), radius_m: radiusM}
}

/** POST /api/hangcheck. Failures become a kind plus a German message; nothing is replaced by a fallback value. */
export async function runCheck(body, fetcher = fetch) {
  let r
  try {
    r = await fetcher('/api/hangcheck', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
  } catch {
    return {ok: false, kind: 'offline', message: 'Keine Verbindung zum lokalen Talwacht-Server.'}
  }
  let json = null
  try { json = await r.json() } catch { /* error bodies may be empty */ }
  if (r.ok && json) return {ok: true, data: json}
  const detail = typeof json?.detail === 'string' ? json.detail : ''
  if (r.status === 503) return {ok: false, kind: 'busy', message: 'Gerade läuft eine andere Berechnung. Gleich noch einmal versuchen.'}
  if (r.status === 422) return {ok: false, kind: 'outside', message: detail || 'Dieser Ort lässt sich nicht prüfen. Wähle einen Ort in Österreich.'}
  if (r.status === 404) return {ok: false, kind: 'missing', message: 'Der Hang-Check-Rechner ist in diesem Stand der Seite noch nicht eingebunden.'}
  return {ok: false, kind: 'error', message: `Der Hang-Check ist gerade nicht erreichbar (HTTP ${r.status}).`}
}

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

/** Geodesic circle (spherical destination formula) as a closed GeoJSON ring; no metres on degrees. */
export function circleRing(centre, radiusM, steps = 96) {
  const R = 6371008.8, rad = Math.PI / 180, d = radiusM / R
  const lat1 = centre.latitude * rad, lon1 = centre.longitude * rad
  const ring = []
  for (let i = 0; i <= steps; i++) {
    const b = (i % steps) / steps * 2 * Math.PI
    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b))
    const lon2 = lon1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2))
    ring.push([+(lon2 / rad).toFixed(6), +(lat2 / rad).toFixed(6)])
  }
  return ring
}

export const km = m => (m / 1000).toLocaleString('de-AT', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + ' km'
export const coord = v => v.toLocaleString('de-AT', {minimumFractionDigits: 5, maximumFractionDigits: 5})
/** Zoom so that the radius fills the visible map comfortably. */
export const zoomFor = radiusM => 14.6 - Math.log2(radiusM / 1000)
