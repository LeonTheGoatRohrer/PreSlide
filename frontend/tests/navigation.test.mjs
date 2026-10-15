import test from 'node:test'
import assert from 'node:assert/strict'
import {pages,resolveRoute} from '../src/navigation.js'

test('all three pages support direct links and a safe default',()=>{
  assert.deepEqual(pages.map(p=>p.label),['Projekt','Vorgehen','Ergebnisse'])
  for(const {id} of pages) assert.deepEqual(resolveRoute('#/'+id),{page:id,section:''})
  for(const hash of ['', '#', '#/unbekannt']) assert.equal(resolveRoute(hash).page,'projekt')
})
test('old bookmarks retain their content destination',()=>{
  assert.deepEqual(resolveRoute('#v05'),{page:'ergebnisse',section:'v05'})
  assert.deepEqual(resolveRoute('#experiment'),{page:'vorgehen',section:'beispiel'})
  assert.deepEqual(resolveRoute('#einzelfaelle'),{page:'ergebnisse',section:'historie'})
  assert.deepEqual(resolveRoute('#ergebnisse'),{page:'ergebnisse',section:'historie'})
  assert.deepEqual(resolveRoute('#/ergebnisse'),{page:'ergebnisse',section:''})
})
test('links to details preserve the requested panel',()=>{
  assert.deepEqual(resolveRoute('#/vorgehen/beispiel'),{page:'vorgehen',section:'beispiel'})
  assert.deepEqual(resolveRoute('#/ergebnisse/vergleich'),{page:'ergebnisse',section:'vergleich'})
})
