"""Independent final artifact checks; never trains models or touches original state."""
import ast
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

from .common import read_json,write_json
from .stability import prepare,LOCAL,REPORT,ROOT,KEYS,sha,matrix,event_scores,score,assert_split


def assert_metrics(data,probabilities,reported):
    result=score(data,probabilities)
    for key,value in result.items():
        other=reported[key]
        if isinstance(other,str) and key=='confusion_matrix':other=ast.literal_eval(other)
        np.testing.assert_allclose(value,other,rtol=1e-10,atol=1e-12,err_msg=key)
    # Independent pooled metric calls protect probability orientation and extraction.
    np.testing.assert_allclose(reported['roc_auc'],roc_auc_score(data.label,probabilities))
    np.testing.assert_allclose(reported['average_precision'],average_precision_score(data.label,probabilities))


def verify():
    dev,splits,config,directory=prepare()
    original=pd.read_parquet(directory/'evaluation_dataset.parquet')
    test_ids=set(original.loc[original.partition=='test','sample_id'])
    source=dev.set_index('sample_id',drop=False)
    manifests=sorted((LOCAL/'fits').rglob('complete.json'))
    if len(manifests)!=440:raise ValueError(f'Expected 440 fits including diagnostics, got {len(manifests)}')
    primary_parts=[];diagnostic_parts=[]
    for idx,path in enumerate(manifests):
        meta=read_json(path);spec=meta['spec'];ctx=spec['context']
        for name,value in meta['sha256'].items():
            if sha(path.parent/name)!=value:raise ValueError('Fit checkpoint hash mismatch')
        train=source.loc[spec['train_ids']];held=source.loc[spec['evaluation_ids']]
        assert_split(train,held)
        assert not test_ids & set(spec['train_ids']+spec['evaluation_ids'])
        official=splits[(splits.repetition==ctx['repetition'])&(splits.fold==ctx['fold'])]
        assert set(official.sample_id)==set(held.sample_id)
        alltrain=dev[~dev.sample_id.isin(held.sample_id)]
        if ctx.get('analysis')=='learning':
            groups=np.random.default_rng(ctx['seed']*100+ctx['fold']).permutation(sorted(alltrain.dependence_cluster.unique()))
            wanted=groups[:int(np.ceil(len(groups)*ctx['fraction']))]
            assert set(train.sample_id)==set(alltrain[alltrain.dependence_cluster.isin(wanted)].sample_id)
        else:assert set(train.sample_id)==set(alltrain.sample_id)
        p=pd.read_parquet(path.parent/'predictions.parquet')
        for key in KEYS:
            assert p[key].tolist()==held[key].tolist(),key
        assert_metrics(p,p.probability,read_json(path.parent/'metrics.json'))
        fitted=joblib.load(path.parent/'model.joblib');model=fitted['model']
        assert fitted['columns']==spec['columns']
        if spec['model']=='logistic_regression':
            x=matrix(train,spec['columns'])
            np.testing.assert_allclose(model.steps[0][1].mean_,x.mean().to_numpy(),rtol=1e-12,atol=1e-10)
            np.testing.assert_allclose(model.steps[0][1].var_,x.var(ddof=0).to_numpy(),rtol=1e-10,atol=1e-8)
        # All stored predictions must equal their saved model's positive-class probability.
        if hasattr(model,'n_jobs'):model.n_jobs=1
        with threadpool_limits(limits=2):
            predicted=model.predict_proba(matrix(held,spec['columns']))[:,list(model.classes_).index(1)]
        np.testing.assert_allclose(p.probability,predicted,rtol=1e-12,atol=1e-12)
        (diagnostic_parts if 'analysis' in ctx else primary_parts).append(p)
        if (idx+1)%100==0:print(f'VERIFY {idx+1}/{len(manifests)} stored models, preprocessing and metrics',flush=True)
    primary=pd.read_parquet(LOCAL/'primary_predictions.parquet')
    diag=pd.read_parquet(LOCAL/'diagnostic_predictions.parquet')
    sort=['repetition','fold','model','features','sample_id']
    pd.testing.assert_frame_equal(primary.sort_values(sort).reset_index(drop=True),
        pd.concat(primary_parts).sort_values(sort).reset_index(drop=True),check_like=True)
    # Compare diagnostic content independent of traversal/column order and NaN dtypes.
    ds=sort+['analysis','window','fraction']
    pd.testing.assert_frame_equal(diag.sort_values(ds).reset_index(drop=True),
        pd.concat(diagnostic_parts,ignore_index=True).sort_values(ds).reset_index(drop=True),check_like=True)
    assert len(primary)==12150 and len(diag)==17550
    for _,g in primary.groupby(['model','features','repetition']):
        assert len(g)==270 and g.sample_id.nunique()==270
    metric_rows=pd.read_csv(REPORT/'stability_metrics.csv')
    assert len(metric_rows)==45
    for row in metric_rows.to_dict('records'):
        p=primary[(primary.model==row['model'])&(primary.features==row['features'])&(primary.repetition==row['repetition'])]
        assert_metrics(p,p.probability,row)
    for row in pd.read_csv(REPORT/'fold_metrics.csv').to_dict('records'):
        p=primary[(primary.model==row['model'])&(primary.features==row['features'])&(primary.repetition==row['repetition'])&(primary.fold==row['fold'])]
        assert_metrics(p,p.probability,row)
    for row in pd.read_csv(REPORT/'performance_deltas.csv').to_dict('records'):
        m=metric_rows[(metric_rows.model==row['model'])&(metric_rows.repetition==row['repetition'])].set_index('features')
        for key,value in row.items():
            if key not in ['model','repetition']:np.testing.assert_allclose(value,m.loc['combined',key]-m.loc['static',key],atol=1e-12)
    saved_events=pd.read_parquet(LOCAL/'event_results.parquet')
    for keys,g in primary.groupby(['repetition','model','features']):
        event=event_scores(g,g.probability).sort_values('event_group_id').reset_index(drop=True)
        saved=saved_events[(saved_events.repetition==keys[0])&(saved_events.model==keys[1])&(saved_events.features==keys[2])].sort_values('event_group_id').reset_index(drop=True)
        pd.testing.assert_frame_equal(event,saved[event.columns])
    for file,analysis in [('weather_window_ablation.csv','ablation'),('learning_curve.csv','learning'),('interaction_metrics.csv','interactions')]:
        for row in pd.read_csv(REPORT/file).to_dict('records'):
            if analysis=='learning':row['features']='combined'
            if (analysis=='ablation' and row['window']=='full') or (analysis=='learning' and row['fraction']==1) or (analysis=='interactions' and row['features']!='combined_interactions'):
                data=primary
            else:data=diag[diag.analysis==analysis]
            p=data[(data.repetition==row['repetition'])&(data.model==row['model'])&(data.features==row['features'])]
            if analysis=='ablation' and row['window']!='full':p=p[p.window==row['window']]
            if analysis=='learning' and row['fraction']!=1:p=p[p.fraction==row['fraction']]
            assert len(p)==270
            assert_metrics(p,p.probability,row)
    imp=pd.read_csv(REPORT/'feature_importance_repetitions.csv')
    for row in pd.read_csv(REPORT/'feature_stability.csv').to_dict('records'):
        vals=imp[(imp.model==row['model'])&(imp.feature==row['feature'])&(imp.kind==row['kind'])].value
        assert len(vals)==5
        np.testing.assert_allclose([row['median'],row['minimum'],row['maximum']],[vals.median(),vals.min(),vals.max()],atol=1e-12)
    # Aggregated public result contains no restricted identifiers.
    public=read_json(REPORT/'public_summary.json');serialized=json.dumps(public)
    for forbidden in ['sample_id','event_group_id','dependence_cluster','latitude','longitude']:
        assert forbidden not in serialized
    for event in original.event_group_id:
        assert event not in serialized
    for name in public['figures']:
        assert (REPORT/(name+'.png')).read_bytes().startswith(b'\x89PNG')
        assert (REPORT/(name+'.svg')).is_file()
    for filename in ['RESULTS.md','LIMITATIONS.md']:
        assert (ROOT/filename).read_bytes().startswith((LOCAL/'original_docs'/filename).read_bytes())
    assert read_json(REPORT/'pipeline_audit.json')['status']=='PASS'
    # Recheck original hashes after all verification, including every original matching checkpoint.
    prepare()
    result={'status':'PASS','primary_fits':len(primary_parts),'diagnostic_fits':len(diagnostic_parts),
        'stored_predictions_reproduced':len(primary)+len(diag),'original_test_overlap':0,
        'original_artifacts_unchanged':True,'training_only_preprocessing':True,'identical_outer_splits':True,
        'checks':['all stored model probabilities reproduced','all primary fold/repetition metrics recomputed',
                  'all ablation/learning/interaction repetition metrics recomputed','all pairwise rankings recomputed',
                  'feature stability aggregation checked','all model checkpoint hashes verified','original artifacts and reports preserved',
                  'public summary has no source/sample identifiers','all seven figures present']}
    write_json(REPORT/'verification.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':verify()
