import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'

// Jury-facing pages describe model values as Prüfstufe, Rangfolge or Szenario. These words would
// suggest calibrated hazard statements that a case-control design cannot make.
const juryFiles=['StartPage.vue','BefundePage.vue','MethodikPage.vue','ForschungPage.vue','ExtremwetterSection.vue','HangProfile.vue','IntervalPlot.vue','App.vue','navigation.js','sources.js']
const banned=/wahrscheinlich|risik|vorhersag|prognos|gefährdet/i

test('jury pages avoid probability, risk and forecast wording',()=>{
  for(const file of juryFiles){
    const text=readFileSync(new URL('../src/'+file,import.meta.url),'utf8')
    const hit=text.match(banned)
    assert.equal(hit,null,`${file}: "${hit?.[0]}"`)
  }
})

test('model numbers on jury pages come from API bundles, not from literals',()=>{
  // The sealed-test values and the pilot value must never be typed into the page source.
  for(const file of ['StartPage.vue','BefundePage.vue','MethodikPage.vue']){
    const text=readFileSync(new URL('../src/'+file,import.meta.url),'utf8')
    for(const literal of ['0,751','0.751','0,633','0,866','0,702','0,604','0,049','0,539','0.539','0,406','0,669'])
      assert.equal(text.includes(literal),false,`${file} contains ${literal}`)
  }
})

test('every problem statement on the start page has a checkable source',async()=>{
  const {problemSources}=await import('../src/sources.js')
  assert.ok(problemSources.length>=3)
  for(const s of problemSources){
    assert.match(s.url,/^https:\/\//)
    assert.ok(s.cite.length>20)
  }
})
