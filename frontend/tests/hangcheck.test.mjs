import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createLayerLoader, requestBody, placeKey, classShareText, circle, FALLBACK_HINWEISE, OFFICIAL} from '../src/hangcheck.js'

// The redesign renders the Hang-Check in pages/CheckPage.vue (same helpers, same request).
const page = readFileSync(new URL('../src/pages/CheckPage.vue', import.meta.url), 'utf8')
const helpers = readFileSync(new URL('../src/hangcheck.js', import.meta.url), 'utf8')
const place = {longitude: 10.5617, latitude: 47.1478}

test('switch off: no layer request; switch on: exactly one per place and radius', async () => {
  const calls = []
  const loader = createLayerLoader(async body => { calls.push(body); return {ok: true} })
  assert.equal(await loader.update({on: false, place, radiusM: 2000}), null)
  assert.equal(calls.length, 0)
  await Promise.all([loader.update({on: true, place, radiusM: 2000}), loader.update({on: true, place, radiusM: 2000})])
  assert.equal(calls.length, 1)
  await loader.update({on: false, place, radiusM: 2000})          // switching off again sends nothing
  await loader.update({on: true, place, radiusM: 2000})           // back on: result kept in memory
  assert.equal(calls.length, 1)
  await loader.update({on: true, place, radiusM: 3000})           // new radius = new place query
  assert.equal(calls.length, 2)
})

test('the request carries only position and radius, never weather or the switch', () => {
  assert.deepEqual(Object.keys(requestBody(place, 2000)).sort(), ['latitude', 'longitude', 'radius_m'])
  const fetchCode = page.slice(page.indexOf('async function fetchLayer'), page.indexOf('const loader'))
  assert.match(fetchCode, /body: JSON\.stringify\(body\)/)       // the body is exactly requestBody(...)
  assert.doesNotMatch(fetchCode + helpers.slice(helpers.indexOf('export function requestBody'), helpers.indexOf('export function placeKey')), /starkregen|rain|regen/i)
  assert.doesNotMatch(page, /api\/hangcheck\?/)                     // no query parameter on the layer request
  assert.notEqual(placeKey(place, 2000), placeKey(place, 2500))
  assert.equal(placeKey(null, 2000), '')
})

test('mandatory notice: "Nicht markiert heißt nicht sicher" is on the page, no warning claim', () => {
  assert.ok(page.includes('nicht markiert heißt nicht sicher'))
  assert.equal(FALLBACK_HINWEISE[0].titel, 'Nicht markiert heißt nicht sicher.')
  assert.ok(FALLBACK_HINWEISE[1].titel.includes('keine Warnung'))
  assert.ok(page.includes('Landeswarnzentralen'))
  assert.match(OFFICIAL.geosphere, /^https:\/\/www\.geosphere\.at\//)
})

test('no model metric typed into the page', () => {
  // Visible text only: the template and the strings of the helpers (CSS and JS numbers are not metrics).
  const template = page.slice(page.indexOf('<template>'), page.indexOf('<style'))
  const strings = (helpers.match(/'[^']*'/g) || []).join(' ')
  for (const text of [template, strings])
    assert.doesNotMatch(text, /\b0,\d{2,3}\b|\b0\.\d{3}\b|AUC/, 'metric literal found')
})

test('class shares come from the API class bounds', () => {
  const stufen = [{id: 3, top_fraction: 1}, {id: 1, top_fraction: .05}, {id: 2, top_fraction: .2}]
  assert.equal(classShareText(stufen, 1), '5 %')
  assert.equal(classShareText(stufen, 2), '15 %')
  assert.equal(classShareText(stufen, 9), '')
})

test('radius circle is geodesic: 2 km north and east of the centre', () => {
  const ring = circle(place, 2000, 4).geometry.coordinates[0]
  const R = 6371008.8, rad = d => d * Math.PI / 180
  const north = (ring[0][1] - place.latitude) * rad(1) * R
  const east = (ring[1][0] - place.longitude) * rad(1) * R * Math.cos(rad(place.latitude))
  assert.ok(Math.abs(north - 2000) < 2 && Math.abs(east - 2000) < 5, `${north} ${east}`)
})
