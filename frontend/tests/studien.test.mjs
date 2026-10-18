import test from 'node:test'
import assert from 'node:assert/strict'
import {filterStudies, studyForAnchor, headline, formatValue, plotScale} from '../src/studien.js'

const studies = [
  {id: 'v05', datum: '2026-10-14', gruppen: ['kern', 'wetter'], kennzahlen: [{verfuegbar: false, grund: 'x'}, {verfuegbar: true, art: 'auc', wert: 0.85}]},
  {id: 'v04', anker: ['methodik'], datum: '2026-10-14', gruppen: ['kern'], kennzahlen: []},
  {id: 'extremwetter', datum: '2026-10-18', gruppen: ['wetter'], kennzahlen: []},
  {id: 'v06', datum: '2026-10-15', gruppen: ['wetter'], kennzahlen: []},
]

test('timeline order by date keeps registry order on equal dates; filter by group', () => {
  assert.deepEqual(filterStudies(studies, '').map(s => s.id), ['v05', 'v04', 'v06', 'extremwetter'])
  assert.deepEqual(filterStudies(studies, 'wetter').map(s => s.id), ['v05', 'v06', 'extremwetter'])
})

test('old anchors open the matching study; unknown anchors open nothing', () => {
  assert.equal(studyForAnchor(studies, 'v04').id, 'v04')
  assert.equal(studyForAnchor(studies, 'methodik').id, 'v04')
  assert.equal(studyForAnchor(studies, 'nichts'), null)
  assert.equal(studyForAnchor(studies, ''), null)
})

test('the card headline is the first available stored figure, never an unavailable one', () => {
  assert.equal(headline(studies[0]).wert, 0.85)
  assert.equal(headline(studies[1]), null)
})

test('formatting only formats; the interval always fits on the plot scale', () => {
  assert.equal(formatValue('auc', 0.7506), '0,751')
  assert.equal(formatValue('delta', -0.023), '−0,023')
  assert.equal(formatValue('anteil', 0.2462), '24,6 %')
  const s = plotScale({art: 'delta', intervall: [-0.3, 0.1]})
  assert.ok(s.min <= -0.3 && s.max >= 0.1)
  assert.equal(s.reference, 0)
  assert.equal(plotScale({art: 'auc'}), null)
  assert.equal(plotScale({art: 'faktor', intervall: [2, 11]}), null)
})
