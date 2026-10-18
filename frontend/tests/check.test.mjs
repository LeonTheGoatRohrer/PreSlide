import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {readCheck, CheckFailure, readParams, clampRadius, normalize} from '../src/check.js'
import {createLayerLoader} from '../src/hangcheck.js'

const place = {name: 'Stanz bei Landeck', longitude: 10.5617, latitude: 47.1478}

test('failures are thrown with a kind and a German message, so the layer loader never keeps them', async () => {
  const reply = (status, json, ok = false) => ({ok, status, json: async () => json})
  await assert.rejects(readCheck(reply(503, {})), e => e instanceof CheckFailure && e.kind === 'busy')
  await assert.rejects(readCheck(reply(422, {detail: 'Der Ort liegt außerhalb Österreichs.'})), {kind: 'outside', message: 'Der Ort liegt außerhalb Österreichs.'})
  await assert.rejects(readCheck(reply(404, null)), {kind: 'missing'})
  await assert.rejects(readCheck({ok: false, status: 500, json: async () => { throw Error('x') }}), {kind: 'error'})
  assert.deepEqual(await readCheck(reply(200, {pruefpunkte: []}, true)), {pruefpunkte: []})
  // A failed request is retried by the shared loader instead of being served from memory.
  let calls = 0
  const loader = createLayerLoader(async () => { calls++; if (calls === 1) throw new CheckFailure('busy', 'x'); return {ok: true} })
  await assert.rejects(loader.update({on: true, place, radiusM: 2000}))
  assert.deepEqual(await loader.update({on: true, place, radiusM: 2000}), {ok: true})
  assert.equal(calls, 2)
})

test('address state: radius snapped to the allowed steps, invalid coordinates give no place', () => {
  assert.equal(clampRadius(2600), 2500)
  assert.equal(clampRadius(99999), 3000)
  assert.equal(clampRadius('x'), 2000)
  assert.deepEqual(readParams({lon: 'a', lat: '47'}).place, null)
  const s = readParams({lon: '10.5617', lat: '47.1478', r: '1500', regen: '1', ort: 'Stanz'})
  assert.deepEqual([s.place.name, s.radius, s.rain], ['Stanz', 1500, true])
  assert.equal(readParams({}).rain, false)
})

test('only marked cells are drawn; distance for the radial reveal is in metres', () => {
  const sq = (lon, lat) => ({type: 'Polygon', coordinates: [[[lon, lat], [lon + .001, lat], [lon + .001, lat + .001], [lon, lat + .001], [lon, lat]]]})
  const n = normalize({zellen: {features: [{properties: {stufe: 1}, geometry: sq(10.5617, 47.1478)}, {properties: {stufe: 3}, geometry: sq(10.57, 47.15)}]},
    pruefpunkte: [{nr: 1, longitude: 10.56, latitude: 47.14}, {nr: 2, longitude: null, latitude: 47}]}, place)
  assert.equal(n.cells.features.length, 1)
  assert.ok(n.cells.features[0].properties.d < 100)
  assert.equal(n.points.length, 1)
})

test('the notice block is part of the page, not only a tooltip', () => {
  const page = readFileSync(new URL('../src/pages/CheckPage.vue', import.meta.url), 'utf8')
  assert.match(page, /nicht markiert heißt nicht sicher/i)
  assert.match(page, /v-for="h in notice"/)
  assert.ok(page.includes('class="cp-notice"'))
})
