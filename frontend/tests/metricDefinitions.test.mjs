// Scientific wording guards for the central explanation texts (run: npm test).
import test from 'node:test'
import assert from 'node:assert/strict'
import { metricDefinitions, explain } from '../src/metricDefinitions.js'

test('every definition answers what it is; metrics state reference and direction', () => {
  for (const [key, d] of Object.entries(metricDefinitions)) {
    assert.ok(d.label && d.what, key)
    if (d.interpret) assert.ok(d.reference, key + ' needs a reference value')
  }
})

test('chance references are correct', () => {
  assert.match(metricDefinitions.rocAuc.reference, /0,5/)
  assert.match(metricDefinitions.withinGroupAuc.reference, /0,5/)
  assert.match(metricDefinitions.firstPlaceRate.reference, /16,7/)
  assert.match(metricDefinitions.controlsBeaten.reference, /2,5/)
  assert.match(metricDefinitions.positiveRank.reference, /3,5/)
  assert.match(metricDefinitions.averagePrecision.reference, /0,167/)
})

test('readings depend on the value and stay conservative', () => {
  assert.match(explain('rocAuc', 0.52).reading, /nahe am Zufallsniveau/)
  assert.match(explain('rocAuc', 0.72).reading, /weit von einer perfekten Trennung/)
  assert.match(explain('rocAuc', 0.40).reading, /unter dem Zufallsniveau/)
  assert.match(explain('averagePrecision', 0.17, { chance: 1 / 6 }).reading, /nahe an der Zufallsreferenz/)
  assert.equal(explain('controlsBeaten', 4).reading,
    'Der echte Rutschungshang erhielt einen höheren Modellwert als 4 seiner 5 ähnlichen Vergleichshänge. Bei einer perfekten lokalen Rangfolge wären es 5 von 5.')
  assert.match(explain('positiveRank', 2).reading, /an zweiter Stelle/)
  for (const v of [0.3, 0.5, 0.6, 0.7, 0.9]) {
    const text = explain('rocAuc', v).reading.toLowerCase()
    for (const word of ['exzellent', 'hervorragend', 'zuverlässig', 'garantiert']) assert.ok(!text.includes(word), `${word} in ${text}`)
  }
})

test('model scores are never described as probabilities in percent', () => {
  const d = metricDefinitions.modelScore
  assert.match(d.warning, /Keine Rutschungswahrscheinlichkeit/)
  assert.equal(explain('modelScore', 0.72).value, '0,720')
  assert.equal(explain('modelScore', 0.72).reading, null)
})

test('unknown terms fail loudly', () => assert.throws(() => explain('nope', 1)))
