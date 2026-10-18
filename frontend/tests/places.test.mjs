import test from 'node:test'
import assert from 'node:assert/strict'
import {toPlace, checkHash, searchPlaces, insideAustriaBox} from '../src/places.js'

test('place entries without finite coordinates are dropped, never guessed', () => {
  assert.equal(toPlace({name: 'Landeck', longitude: 'x', latitude: 47.1}), null)
  assert.equal(toPlace({longitude: 10.5, latitude: 47.1}), null)
  const p = toPlace({kennziffer: '70608', name: 'Landeck', bundesland: 'Tirol', longitude: 10.566, latitude: 47.139, anzeige: 'Landeck (Tirol)'})
  assert.deepEqual([p.id, p.label, p.region], ['70608', 'Landeck (Tirol)', 'Tirol'])
})

test('a browser location never enters the address; a chosen municipality does', () => {
  const own = {private: true, name: 'Mein Standort', longitude: 11.39, latitude: 47.26}
  assert.equal(checkHash(own, 2000, true), '#/check?r=2000&regen=1')
  const town = {name: 'Landeck', longitude: 10.56612, latitude: 47.13901}
  assert.equal(checkHash(town, 1500, false), '#/check?lon=10.56612&lat=47.13901&ort=Landeck&r=1500')
})

test('search: short queries send nothing; missing endpoint is reported, not faked', async () => {
  let calls = 0
  const none = await searchPlaces('L', async () => { calls++ })
  assert.deepEqual(none, {places: [], unavailable: false}); assert.equal(calls, 0)
  const missing = await searchPlaces('Lan', async () => ({status: 404, ok: false}))
  assert.deepEqual(missing, {places: [], unavailable: true})
  await assert.rejects(searchPlaces('Lan', async () => ({status: 500, ok: false})), /HTTP 500/)
  const found = await searchPlaces('Lan', async url => {
    assert.match(url, /^\/api\/hangcheck\/orte\?q=Lan$/)
    return {status: 200, ok: true, json: async () => ({orte: [{name: 'Landeck', bundesland: 'Tirol', longitude: 10.56, latitude: 47.14}, {name: 'kaputt'}]})}
  })
  assert.equal(found.places.length, 1)
})

test('Austria bounding box guards the location button', () => {
  assert.equal(insideAustriaBox(13.3, 47.6), true)
  assert.equal(insideAustriaBox(8.5, 47.4), false)
  assert.equal(insideAustriaBox(NaN, 47), false)
})
