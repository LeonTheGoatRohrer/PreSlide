// In-memory hand-over between pages (never persisted): a browser location must not enter the address.
import {checkHash} from './places.js'
let pending = null
export function openCheck(place, {radiusM = null, rain = false} = {}) {
  pending = place?.private ? place : null
  location.hash = checkHash(place, radiusM ?? place?.radius_m ?? null, rain)
}
export function takePendingPlace() {
  const p = pending
  pending = null
  return p
}
