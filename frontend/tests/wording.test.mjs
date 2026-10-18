import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync, readdirSync} from 'node:fs'

// User-facing pages describe model values as Prüfstufe, Rangfolge or Szenario. These words would
// suggest calibrated hazard statements that a case-control design cannot make.
const src = new URL('../src/', import.meta.url)
const dir = d => readdirSync(new URL(d, src)).filter(f => /\.(vue|js)$/.test(f)).map(f => d + f)
// Every new page and component is covered automatically; the listed root files are shared by them.
export const juryFiles = [...dir('pages/'), ...dir('ui/'),
  'App.vue', 'navigation.js', 'places.js', 'session.js', 'sources.js', 'InfoTip.vue', 'IntervalPlot.vue',
  'BefundePage.vue', 'MethodikPage.vue', 'ExtremwetterSection.vue']
const banned = /wahrscheinlich|risik|vorhersag|prognos|gefährdet/i
export const bannedWord = text => text.match(banned)?.[0] ?? null

test('user-facing pages avoid probability, risk and forecast wording', () => {
  assert.ok(juryFiles.length > 15)
  for (const file of juryFiles) {
    const hit = bannedWord(readFileSync(new URL(file, src), 'utf8'))
    assert.equal(hit, null, `${file}: "${hit}"`)
  }
})

test('the wording guard fails on an injected forbidden word', () => {
  const page = readFileSync(new URL('pages/StartPage.vue', src), 'utf8')
  assert.equal(bannedWord(page), null)
  assert.equal(bannedWord(page.replace('Wo zuerst hinschauen', 'Risiko: wo zuerst hinschauen')), 'Risik')
})

// The sealed-test values and the pilot value must never be typed into a page source.
const literals = ['0,751', '0.751', '0,633', '0,866', '0,702', '0,604', '0,049', '0,539', '0.539', '0,406', '0,669', '0,770', '0,928', '0,818', '423', '0.7506']
export const metricLiteral = text => literals.find(l => text.includes(l)) ?? null
test('model numbers on user pages come from API bundles, not from literals', () => {
  for (const file of [...dir('pages/'), ...dir('ui/'), 'BefundePage.vue', 'MethodikPage.vue']) {
    const hit = metricLiteral(readFileSync(new URL(file, src), 'utf8'))
    assert.equal(hit, null, `${file} contains ${hit}`)
  }
  assert.equal(metricLiteral('<p>Test 0,751</p>'), '0,751')
})

test('every problem statement has a checkable source', async () => {
  const {problemSources} = await import('../src/sources.js')
  assert.ok(problemSources.length >= 3)
  for (const s of problemSources) {
    assert.match(s.url, /^https:\/\//)
    assert.ok(s.cite.length > 20)
  }
})

test('generated illustrations are labelled wherever they are shown', () => {
  for (const file of dir('pages/')) {
    const text = readFileSync(new URL(file, src), 'utf8')
    const images = (text.match(/\/media\//g) || []).length
    if (!images) continue
    assert.ok(text.includes('KI-generierte Illustration'), `${file} shows generated media without label`)
  }
})
