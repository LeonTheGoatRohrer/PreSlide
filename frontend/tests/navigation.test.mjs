import test from 'node:test'
import assert from 'node:assert/strict'
import {mainNav, primaryAction, pages, resolveRoute, parseHash, pageTitle} from '../src/navigation.js'

test('four questions in the menu plus one main action; no research menu, no sub-page bar', () => {
  assert.deepEqual(mainNav.map(p => p.id), ['so-funktionierts', 'belastbar', 'studien', 'ueber'])
  assert.equal(primaryAction.id, 'check')
  for (const id of ['forschung', 'projekt', 'vorgehen', 'ergebnisse', 'hangkarte', 'befunde', 'methodik', 'pruefgebiete'])
    assert.equal(pages.includes(id), false, id)
  for (const id of pages) assert.equal(resolveRoute(id === 'start' ? '#/' : '#/' + id).page, id)
  for (const hash of ['', '#', '#/']) assert.deepEqual(resolveRoute(hash), {page: 'start', anchor: '', params: {}, redirect: null})
  assert.equal(resolveRoute('#/unbekannt').page, 'start')
  assert.equal(resolveRoute('#/unbekannt').redirect, '#/')
  assert.equal(pageTitle('studien'), 'Studienatlas')
})

test('state of the Hang-Check lives in the address', () => {
  const r = resolveRoute('#/check?lon=10.56170&lat=47.14780&r=1500&regen=1')
  assert.equal(r.page, 'check')
  assert.deepEqual(r.params, {lon: '10.56170', lat: '47.14780', r: '1500', regen: '1'})
  assert.equal(r.redirect, null)
  assert.deepEqual(parseHash('#/studien#v04'), {path: 'studien', anchor: 'v04', params: {}})
})

// Every address that existed before the redesign must reach the place where its content lives now.
const oldAddresses = {
  '#/start': '#/', '#/hangcheck': '#/check', '#/hangkarte': '#/check',
  '#/pruefgebiete': '#/so-funktionierts#wirkungskette', '#/befunde': '#/belastbar', '#/methodik': '#/so-funktionierts',
  '#/forschung': '#/studien', '#/projekt': '#/studien#kernfrage', '#/vorgehen': '#/studien#baseline',
  '#/vorgehen/beispiel': '#/studien#baseline', '#/vorgehen/quellen': '#/studien#v04',
  '#/ergebnisse': '#/studien', '#/ergebnisse/v04': '#/studien#v04', '#/ergebnisse/v05': '#/studien#v05',
  '#/ergebnisse/vergleich': '#/studien#vergleich', '#/ergebnisse/historie': '#/studien#baseline',
  '#/forschung/vorgehen': '#/studien#baseline', '#/forschung/hangkarte': '#/check',
  '#v05': '#/studien#v05', '#v04': '#/studien#v04', '#benchmarks': '#/studien#vergleich',
  '#experiment': '#/studien#baseline', '#wetter': '#/studien#baseline', '#warum': '#/studien#baseline',
  '#methodik': '#/studien#v04', '#einzelfaelle': '#/studien#baseline', '#ergebnisse': '#/studien#baseline',
}
test('old addresses redirect to their new place', () => {
  for (const [hash, target] of Object.entries(oldAddresses)) {
    const r = resolveRoute(hash)
    assert.equal(r.redirect, target, hash)
    assert.equal(resolveRoute(target).redirect, null, target)
  }
  // Query parameters survive a redirect (e.g. a shared Hangkarte link).
  assert.equal(resolveRoute('#/hangcheck?lon=10.5&lat=47.1').redirect, '#/check?lon=10.5&lat=47.1')
})
