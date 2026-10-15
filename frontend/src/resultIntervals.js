// Presentation only: preserve the stored interval type and the exact model/run identity.
export function comparisonInterval(bundle, run, variant) {
  if (!['v04_test','v05_cv'].includes(run)) return null
  const row=bundle?.rows?.find(r=>r.run===run&&r.model_key==='conditional_logit'&&r.variant===variant)
  if(!row?.local_auc_range)return null
  return {range:row.local_auc_range,label:run==='v04_test'?'95-%-Unsicherheitsintervall':'Spanne der fünf Wiederholungen (kein Konfidenzintervall)'}
}
