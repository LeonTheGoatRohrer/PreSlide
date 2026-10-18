import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync, readdirSync} from 'node:fs'
import {RADIUS, clampRadius, scenarioBand, infraBand, rangeText, profileGeometry, niceTicks, meters, LAYER_KIND, FORBIDDEN_WORDS} from '../src/wirkungskette/chain.js'

test('radius is clamped to 1-10 km in 1 km steps', () => {
  assert.equal(clampRadius(250), RADIUS.min)
  assert.equal(clampRadius(99999), RADIUS.max)
  assert.equal(clampRadius(3400), 3000)
  assert.equal(clampRadius('abc'), RADIUS.initial)
})

const sc = [
  {id: 'reach_45m', laenge_m: 30, status: 'gestoppt', infrastruktur: {gebaeude: {anzahl: 0}, strasse: {anzahl: 1}, weg: {anzahl: 0}, bahn: {anzahl: 0}}},
  {id: 'reach_467m', laenge_m: 460, status: 'gestoppt', infrastruktur: {gebaeude: {anzahl: 5}, strasse: {anzahl: 7}, weg: {anzahl: 2}, bahn: {anzahl: 0}}},
  {id: 'energy_7deg', laenge_m: 1200, status: 'rand', infrastruktur: {gebaeude: {anzahl: 13}, strasse: {anzahl: 9}, weg: {anzahl: 5}, bahn: {anzahl: 1}}},
]

test('scenario band spans all scenarios and names the open ones', () => {
  assert.deepEqual(scenarioBand(sc), {min: 30, max: 1200, offen: ['energy_7deg']})
  assert.equal(scenarioBand([]), null)
})

test('infrastructure band is min-max over scenarios', () => {
  const b = infraBand(sc)
  assert.deepEqual(b.gebaeude, {min: 0, max: 13})
  assert.equal(rangeText(b.bahn), '0–1')
  assert.equal(rangeText({min: 4, max: 4}), '4')
})

test('profile geometry maps distance and height monotonically and keeps stops on the axis', () => {
  const profil = {distanz_m: [0, 30, 60, 90, 120], hoehe_m: [900, 880, 850, 840, 838]}
  const g = profileGeometry(profil, [{id: 'a', laenge_m: 60, status: 'gestoppt', bezeichnung: 'A', energielinie_m: [900, 885, 860]}], {width: 600, height: 200})
  assert.ok(g.X(0) < g.X(60) && g.X(60) < g.X(120))
  assert.ok(g.Y(900) < g.Y(838))              // higher terrain is drawn higher (smaller y)
  assert.equal(g.stops[0].x, g.X(60))
  assert.ok(g.line.startsWith('M'))
  assert.equal(profileGeometry({distanz_m: [0], hoehe_m: [1]}, []), null)
})

test('ticks and metre formatting', () => {
  assert.deepEqual(niceTicks(0, 1000, 5), [0, 200, 400, 600, 800, 1000])
  assert.equal(meters(1500), '1,5 km')
  assert.equal(meters(45), '45 m')
})

test('every map layer carries one of the three statement kinds', () => {
  for (const v of Object.values(LAYER_KIND)) assert.ok(['Befund', 'Szenario', 'Illustration'].includes(v.tag))
})

test('no probability, risk or endangerment wording in the Prüfgebiete and Wirkungskette views', () => {
  const files = ['src/PruefgebietePage.vue', ...readdirSync('src/wirkungskette').map(f => `src/wirkungskette/${f}`)]
  for (const f of files) {
    const text = readFileSync(f, 'utf8').split('\n').filter(l => !l.includes('export const FORBIDDEN_WORDS')).join('\n')
    assert.ok(!FORBIDDEN_WORDS.test(text), `${f} uses a forbidden word`)
  }
})
