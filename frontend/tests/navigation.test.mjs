import test from 'node:test'
import assert from 'node:assert/strict'
import {mainNav,researchPages,pages,resolveRoute,activeNav,isResearch,pageTitle} from '../src/navigation.js'

test('jury entry first, research area last, start page as safe default',()=>{
  assert.deepEqual(mainNav.map(p=>p.id),['start','hangcheck','pruefgebiete','befunde','methodik','forschung'])
  assert.deepEqual(researchPages.map(p=>p.id),['projekt','vorgehen','ergebnisse','hangkarte'])
  for(const {id} of pages) assert.deepEqual(resolveRoute('#/'+id),{page:id,section:''})
  for(const hash of ['', '#', '#/', '#/unbekannt']) assert.deepEqual(resolveRoute(hash),{page:'start',section:''})
  assert.equal(pageTitle('pruefgebiete'),'Demo: Prüfgebiete')
})

test('research pages are highlighted under "Forschung" and keep their own addresses',()=>{
  for(const {id} of researchPages){ assert.equal(activeNav(id),'forschung'); assert.equal(isResearch(id),true) }
  for(const id of ['start','hangcheck','pruefgebiete','befunde','methodik']){ assert.equal(activeNav(id),id); assert.equal(isResearch(id),false) }
  assert.deepEqual(resolveRoute('#/forschung/vorgehen'),{page:'vorgehen',section:''})
  assert.deepEqual(resolveRoute('#/forschung'),{page:'forschung',section:''})
})

// Every bookmark that existed before the jury restructuring must reach the same content as before.
const oldBookmarks={
  '#v05':{page:'ergebnisse',section:'v05'},
  '#v04':{page:'ergebnisse',section:'v04'},
  '#benchmarks':{page:'ergebnisse',section:'vergleich'},
  '#experiment':{page:'vorgehen',section:'beispiel'},
  '#wetter':{page:'vorgehen',section:'beispiel'},
  '#warum':{page:'vorgehen',section:''},
  '#methodik':{page:'vorgehen',section:'quellen'},
  '#einzelfaelle':{page:'ergebnisse',section:'historie'},
  '#ergebnisse':{page:'ergebnisse',section:'historie'},
  '#/projekt':{page:'projekt',section:''},
  '#/vorgehen':{page:'vorgehen',section:''},
  '#/vorgehen/beispiel':{page:'vorgehen',section:'beispiel'},
  '#/vorgehen/quellen':{page:'vorgehen',section:'quellen'},
  '#/ergebnisse':{page:'ergebnisse',section:''},
  '#/ergebnisse/v04':{page:'ergebnisse',section:'v04'},
  '#/ergebnisse/v05':{page:'ergebnisse',section:'v05'},
  '#/ergebnisse/vergleich':{page:'ergebnisse',section:'vergleich'},
  '#/ergebnisse/historie':{page:'ergebnisse',section:'historie'},
  '#/pruefgebiete':{page:'pruefgebiete',section:''},
}
test('old bookmarks and hash routes keep their content destination',()=>{
  for(const [hash,target] of Object.entries(oldBookmarks)) assert.deepEqual(resolveRoute(hash),target,hash)
})

test('the new "#/methodik" page and the old "#methodik" bookmark stay distinct',()=>{
  assert.deepEqual(resolveRoute('#/methodik'),{page:'methodik',section:''})
  assert.notDeepEqual(resolveRoute('#methodik'),resolveRoute('#/methodik'))
})
