import test from 'node:test'
import assert from 'node:assert/strict'
import {extremwetterFigures,extremwetterState} from '../src/extremwetter.js'

test('503 means "analysis still running", other failures are errors',()=>{
  assert.equal(extremwetterState({loading:true,status:null,data:null}),'loading')
  assert.equal(extremwetterState({loading:false,status:503,data:null}),'pending')
  assert.equal(extremwetterState({loading:false,status:404,data:null}),'missing')
  assert.equal(extremwetterState({loading:false,status:500,data:null}),'error')
  assert.equal(extremwetterState({loading:false,status:0,data:null}),'error')
  assert.equal(extremwetterState({loading:false,status:200,data:{}}),'ready')
})

test('only figures with label, value and a complete interval are shown',()=>{
  const {figures,skipped}=extremwetterFigures({kernzahlen:[
    {label:'A',wert:0.4,intervall:[0.3,0.5]},
    {label:'ohne Intervall',wert:0.4},
    {label:'halbes Intervall',wert:0.4,intervall:[0.3]},
    {label:'vertauscht',wert:0.4,intervall:[0.5,0.3]},
    {label:'NaN',wert:Number.NaN,intervall:[0.3,0.5]},
    {name:'B',value:1.2,ci95:[1.0,1.5],unit:'mm'},
  ]})
  assert.deepEqual(figures.map(f=>f.label),['A','B'])
  assert.equal(figures[1].unit,'mm')
  assert.equal(skipped,4)
})

test('unknown or empty bundles yield nothing instead of invented numbers',()=>{
  assert.deepEqual(extremwetterFigures(null),{figures:[],skipped:0})
  assert.deepEqual(extremwetterFigures({ergebnis:{wert:1}}),{figures:[],skipped:0})
})
