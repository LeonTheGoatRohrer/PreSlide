import test from 'node:test'
import assert from 'node:assert/strict'
import {comparisonInterval} from '../src/resultIntervals.js'
test('uncertainty belongs to the exact run, model, and feature variant',()=>{
  const bundle={rows:[
    {run:'v04_test',model_key:'hist_gradient_boosting',variant:'static',local_auc_range:[0.1,0.2]},
    {run:'v04_test',model_key:'conditional_logit',variant:'static',local_auc_range:[0.3,0.4]},
    {run:'v05_cv',model_key:'conditional_logit',variant:'static',local_auc_range:[0.5,0.6]},
  ]}
  assert.deepEqual(comparisonInterval(bundle,'v04_test','static'),{range:[0.3,0.4],label:'95-%-Unsicherheitsintervall'})
  const repeated=comparisonInterval(bundle,'v05_cv','static')
  assert.deepEqual(repeated.range,[0.5,0.6])
  assert.match(repeated.label,/kein Konfidenzintervall/)
  assert.equal(comparisonInterval(bundle,'v04_test','temporal'),null)
  assert.equal(comparisonInterval(null,'v04_test','static'),null)
  assert.equal(comparisonInterval(bundle,'unbekannt','static'),null)
})
