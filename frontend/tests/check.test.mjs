import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {requestBody, runCheck, readParams, clampRadius, circleRing, normalize} from '../src/check.js'
import {distanceM} from '../src/hangkarte.js'

const place = {name: 'Stanz bei Landeck', longitude: 10.5617, latitude: 47.1478}

test('switch off sends nothing; switch on sends exactly one request with place and radius only', async () => {
  assert.equal(requestBody(place, 1500, false), null)
  assert.equal(requestBody(null, 1500, true), null)
  const calls = []
  const fetcher = async (url, init) => { calls.push({url, body: JSON.parse(init.body)}); return {ok: true, status: 200, json: async () => ({pruefpunkte: []})} }
  const body = requestBody(place, 1500, true)
  const r = await runCheck(body, fetcher)
  assert.equal(r.ok, true)
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/api/hangcheck')
  assert.deepEqual(Object.keys(calls[0].body).sort(), ['latitude', 'longitude', 'radius_m'])   // no rain or switch parameter
})

test('errors stay errors with a German message; nothing is replaced by a fallback value', async () => {
  const reply = (status, json) => async () => ({ok: false, status, json: async () => json})
  assert.equal((await runCheck({}, reply(503, {}))).kind, 'busy')
  const out = await runCheck({}, reply(422, {detail: 'Der Ort liegt außerhalb Österreichs.'}))
  assert.deepEqual([out.kind, out.message], ['outside', 'Der Ort liegt außerhalb Österreichs.'])
  assert.equal((await runCheck({}, reply(404, null))).kind, 'missing')
  assert.equal((await runCheck({}, async () => { throw Error('net') })).kind, 'offline')
  assert.equal('data' in (await runCheck({}, reply(500, {}))), false)
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

test('radius ring is geodesic: every vertex lies at the radius', () => {
  const ring = circleRing(place, 2000)
  assert.deepEqual(ring[0], ring.at(-1))
  for (const [longitude, latitude] of ring) assert.ok(Math.abs(distanceM(place, {longitude, latitude}) - 2000) < 2)
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
  assert.ok(page.includes('Nicht markiert heißt nicht sicher.'))
  assert.ok(page.includes('class="cp-notice"'))
})
