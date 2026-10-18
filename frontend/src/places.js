// Offline place search and example areas of the Hang-Check (GET /api/hangcheck/orte, /beispiele).
// Nothing is sent to an external geocoder; the browser location is only used to pick a map point.
const AUSTRIA = {west: 9.4, east: 17.3, south: 46.3, north: 49.1}

export function insideAustriaBox(lon, lat) {
  return Number.isFinite(lon) && Number.isFinite(lat) && lon >= AUSTRIA.west && lon <= AUSTRIA.east && lat >= AUSTRIA.south && lat <= AUSTRIA.north
}

/** Normalise one place entry of the API; entries without finite coordinates are dropped, never guessed. */
export function toPlace(e) {
  const lon = Number(e?.longitude), lat = Number(e?.latitude)
  if (!e?.name || !Number.isFinite(lon) || !Number.isFinite(lat)) return null
  return {id: String(e.kennziffer ?? e.id ?? e.name), name: e.name, region: e.bundesland ?? '', label: e.anzeige ?? (e.bundesland ? `${e.name} (${e.bundesland})` : e.name),
    longitude: lon, latitude: lat, radius_m: Number.isFinite(Number(e.radius_m)) ? Number(e.radius_m) : null}
}

/** Up to ten municipalities for a query. Returns {places, unavailable}; unavailable = the search endpoint is not part of this build. */
export async function searchPlaces(query, fetcher = fetch) {
  const q = query.trim()
  if (q.length < 2) return {places: [], unavailable: false}
  const r = await fetcher('/api/hangcheck/orte?q=' + encodeURIComponent(q))
  if (r.status === 404) return {places: [], unavailable: true}
  if (!r.ok) throw new Error(`Ortssuche gerade nicht erreichbar (HTTP ${r.status}).`)
  const json = await r.json()
  return {places: (json.orte ?? []).map(toPlace).filter(Boolean), unavailable: false}
}

let examplesCache = null
/** The three example areas (Hang-Check config; the Hangkarte lists the same three areas). */
export async function loadExamples(fetcher = fetch) {
  if (examplesCache) return examplesCache
  let r = await fetcher('/api/hangcheck/beispiele')
  if (r.ok) {
    const json = await r.json()
    examplesCache = {examples: (json.beispiele ?? []).map(toPlace).filter(Boolean), meta: json}
    return examplesCache
  }
  r = await fetcher('/api/hangkarte/examples')
  if (!r.ok) throw new Error(`Beispielgebiete nicht verfügbar (HTTP ${r.status}).`)
  const json = await r.json()
  examplesCache = {examples: (json.examples ?? []).map(toPlace).filter(Boolean), meta: null}
  return examplesCache
}

/** Browser location for map selection only: never stored, logged or put into the address. */
export function locate() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Dieser Browser kann den Standort nicht bestimmen.'))
    navigator.geolocation.getCurrentPosition(
      p => insideAustriaBox(p.coords.longitude, p.coords.latitude)
        ? resolve({id: 'standort', name: 'Mein Standort', label: 'Mein Standort', region: '', longitude: p.coords.longitude, latitude: p.coords.latitude, radius_m: null, private: true})
        : reject(new Error('Dein Standort liegt außerhalb Österreichs. Wähle einen Ort in Österreich.')),
      e => reject(new Error(e.code === 1 ? 'Standortfreigabe abgelehnt. Gib stattdessen einen Ort ein.' : 'Standort konnte nicht bestimmt werden.')),
      {enableHighAccuracy: false, timeout: 10000, maximumAge: 600000})
  })
}

/** Address of the Hang-Check for a place. A private browser location is never written into the address. */
export function checkHash(place, radiusM, rain) {
  const p = new URLSearchParams()
  if (place && !place.private) {
    p.set('lon', place.longitude.toFixed(5)); p.set('lat', place.latitude.toFixed(5))
    if (place.name) p.set('ort', place.name)
  }
  if (radiusM) p.set('r', String(radiusM))
  if (rain) p.set('regen', '1')
  const q = p.toString()
  return '#/check' + (q ? '?' + q : '')
}
