// In-memory hand-over between pages (never persisted): a browser location must not enter the address,
// and the hero hands the "arrival" of its image over to the real map.
import {checkHash} from './places.js'
let pending = null, arrival = false
export function openCheck(place, {radiusM = null, rain = false, fromHero = false} = {}) {
  pending = place?.private ? place : null
  arrival = fromHero
  location.hash = checkHash(place, radiusM ?? place?.radius_m ?? null, rain)
}
export function takePendingPlace() {
  const p = pending
  pending = null
  return p
}
export function takeArrival() {
  const a = arrival
  arrival = false
  return a
}
