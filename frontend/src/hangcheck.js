// Pure helpers of the Hang-Check page (unit-tested without a browser).
// The heavy-rain switch only selects the view: it never adds a parameter to the request.

// URL checked on 2026-10-18 (HTTP 200); the Landeswarnzentralen are named without a link.
export const OFFICIAL = {geosphere: 'https://www.geosphere.at/de'}

// Shown until the API bundle with all four notes has loaded; the API texts replace it.
export const FALLBACK_HINWEISE = [
  {titel: 'Nicht markiert heißt nicht sicher.', text: 'Die Einstufung ist relativ: In jedem Gebiet sind Hänge markiert, auch wenn dort nichts passiert. Auch nicht markierte Hänge können abgehen.'},
  {titel: 'Talwacht ist keine Warnung.', text: 'Aktuelle Unwetterwarnungen geben GeoSphere Austria und die Landeswarnzentralen. Im Notfall: Euronotruf 112, Feuerwehr 122.'},
]

export const STUFE_FARBE = {1: '#c62828', 2: '#ef8f00'}

/** Request body for one place: position and radius only (no weather, no switch state). */
export function requestBody(place, radiusM) {
  return {longitude: Number(place.longitude), latitude: Number(place.latitude), radius_m: Number(radiusM)}
}

export function placeKey(place, radiusM) {
  return place ? `${Number(place.longitude).toFixed(5)}|${Number(place.latitude).toFixed(5)}|${Number(radiusM)}` : ''
}

/**
 * Loads the layer only while the switch is on; one request per place and radius, kept in memory.
 * `fetchLayer(body)` returns a promise of the API result.
 */
export function createLayerLoader(fetchLayer) {
  const results = new Map()
  let pending = null
  return {
    async update({on, place, radiusM}) {
      if (!on || !place) return null
      const key = placeKey(place, radiusM)
      if (results.has(key)) return results.get(key)
      if (pending?.key === key) return pending.promise
      const promise = fetchLayer(requestBody(place, radiusM)).then(r => { results.set(key, r); return r })
        .finally(() => { if (pending?.key === key) pending = null })
      pending = {key, promise}
      return promise
    },
    has: (place, radiusM) => results.has(placeKey(place, radiusM)),
  }
}

/** Share of the class as German percent text from the API class bounds (e.g. "5 %", "15 %"). */
export function classShareText(stufen, id) {
  const sorted = [...(stufen || [])].sort((a, b) => a.top_fraction - b.top_fraction)
  const i = sorted.findIndex(s => s.id === id)
  if (i < 0) return ''
  const share = sorted[i].top_fraction - (i ? sorted[i - 1].top_fraction : 0)
  return Math.round(share * 1000) / 10 + ' %'
}

/** Geodesic circle (spherical earth) as a GeoJSON polygon, for drawing the radius. */
export function circle(place, radiusM, steps = 96) {
  const R = 6371008.8, rad = d => d * Math.PI / 180, deg = r => r * 180 / Math.PI
  const lat1 = rad(place.latitude), lon1 = rad(place.longitude), d = radiusM / R, ring = []
  for (let i = 0; i <= steps; i++) {
    const b = 2 * Math.PI * i / steps
    const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(b))
    const lon2 = lon1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2))
    ring.push([deg(lon2), deg(lat2)])
  }
  return {type: 'Feature', properties: {}, geometry: {type: 'Polygon', coordinates: [ring]}}
}

export const km = m => (Number(m) / 1000).toLocaleString('de-AT', {maximumFractionDigits: 1}) + ' km'
