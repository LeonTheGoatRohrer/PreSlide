"""Frozen feature whitelist and storm/location grouped evaluation."""
import numpy as np
import pandas as pd
import joblib
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score,average_precision_score,precision_score,recall_score,f1_score,balanced_accuracy_score,confusion_matrix,brier_score_loss
from .common import read_json,write_json,digest
from .sources import ROOT
from .pipeline import STATIC,validate_dataset
from .weather import TEMPORAL

FEATURE_SETS={'static':STATIC,'temporal':TEMPORAL,'combined':STATIC+TEMPORAL}

def dependent_clusters(data):
    events=data[data.label==1].sort_values('event_group_id').reset_index(drop=True)
    ids=events.event_group_id.tolist();index={v:i for i,v in enumerate(ids)};parent=list(range(len(ids)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=root(a),root(b)
        if a!=b: parent[max(a,b)]=min(a,b)
    dates=pd.to_datetime(events.event_date).to_numpy()
    xy=events[['x','y']].to_numpy()
    for i in range(len(ids)):
        for j in range(i):
            # National storm episode guard, plus repeat/nearby positive locations across dates.
            if abs((dates[i]-dates[j])/np.timedelta64(1,'D'))<=3 or np.linalg.norm(xy[i]-xy[j])<2000:
                union(i,j)
    # Keep all reused/near-overlapping sample patches together, irrespective of event date.
    pairs=cKDTree(data[['x','y']].to_numpy()).query_pairs(400)
    groups=data.event_group_id.to_numpy()
    for a,b in pairs: union(index[groups[a]],index[groups[b]])
    mapping={v:f'cluster_{root(i):03d}' for i,v in enumerate(ids)}
    return data.event_group_id.map(mapping)

def grouped_split(data,seed=42):
    clusters=data.dependence_cluster
    if clusters.nunique()<3: raise ValueError('At least three independent clusters required')
    trainval,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=seed).split(data,groups=clusters))
    trainlocal,vallocal=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=seed).split(data.iloc[trainval],groups=clusters.iloc[trainval]))
    split=np.full(len(data),'test',dtype=object)
    split[trainval[trainlocal]]='train';split[trainval[vallocal]]='validation'
    result=pd.Series(split,index=data.index)
    for column in ['event_group_id','dependence_cluster']:
        if data.assign(partition=result).groupby(column).partition.nunique().max()!=1:
            raise ValueError('Group leakage')
    return result

def make_model(name):
    if name=='logistic_regression':
        return make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',C=1,max_iter=3000,random_state=42))
    if name=='random_forest':
        return RandomForestClassifier(n_estimators=200,min_samples_leaf=3,max_features='sqrt',class_weight='balanced',random_state=42,n_jobs=2)
    return HistGradientBoostingClassifier(max_iter=150,max_leaf_nodes=7,min_samples_leaf=10,l2_regularization=1,class_weight='balanced',random_state=42)

def metrics(data,p):
    y=data.label.to_numpy();pred=(p>=.5).astype(int)
    within=[];top=[]
    for _,indices in data.reset_index(drop=True).groupby('event_group_id').groups.items():
        ii=np.array(list(indices));s=p[ii];labels=y[ii];pos=s[labels==1][0];neg=s[labels==0]
        within.append(float(np.mean((pos>neg)+.5*(pos==neg))))
        top.append(float(1/np.sum(s==s.max()) if pos==s.max() else 0))
    return {'roc_auc':float(roc_auc_score(y,p)),'average_precision':float(average_precision_score(y,p)),
            'precision':float(precision_score(y,pred,zero_division=0)),'recall':float(recall_score(y,pred,zero_division=0)),
            'f1':float(f1_score(y,pred,zero_division=0)),'balanced_accuracy':float(balanced_accuracy_score(y,pred)),
            'brier':float(brier_score_loss(y,p)),'confusion_matrix':confusion_matrix(y,pred,labels=[0,1]).tolist(),
            'within_group_auc':float(np.mean(within)),'top1_fractional':float(np.mean(top)),
            'events':int(data.event_group_id.nunique()),'clusters':int(data.dependence_cluster.nunique())}

def bootstrap_ci(data,p,repeats=500):
    rng=np.random.default_rng(42);groups=data.dependence_cluster.unique()
    if len(groups)<2: return {'warning':'Fewer than two test clusters; interval not estimable'}
    mapping={g:np.flatnonzero(data.dependence_cluster.to_numpy()==g) for g in groups}
    auc=[];ap=[]
    for _ in range(repeats):
        ii=np.concatenate([mapping[g] for g in rng.choice(groups,len(groups),replace=True)])
        auc.append(roc_auc_score(data.label.to_numpy()[ii],p[ii]));ap.append(average_precision_score(data.label.to_numpy()[ii],p[ii]))
    return {'method':'500 cluster bootstrap resamples, fixed fitted model, descriptive 95% percentile interval',
            'roc_auc':np.quantile(auc,[.025,.975]).tolist(),'average_precision':np.quantile(ap,[.025,.975]).tolist()}

def run_evaluation():
    latest=read_json(ROOT/'data/processed/latest.json')
    directory=ROOT/'data/processed'/latest['identity']
    data=pd.read_parquet(directory/latest['dataset']);validate_dataset(data,latest['config'])
    data['dependence_cluster']=dependent_clusters(data)
    data['partition']=grouped_split(data)
    pilot=data.event_group_id.nunique()<30
    reportdir=ROOT/'reports'/('pilot' if pilot else 'experiment');reportdir.mkdir(parents=True,exist_ok=True)
    modeldir=ROOT/'models'/latest['identity'];modeldir.mkdir(parents=True,exist_ok=True)
    data.to_parquet(directory/'evaluation_dataset.parquet',index=False)
    splits={p:{'events':int(d.event_group_id.nunique()),'clusters':int(d.dependence_cluster.nunique()),'samples':len(d)} for p,d in data.groupby('partition')}
    results={'status':'SMOKE_TEST_ONLY' if pilot else 'EXPLORATORY_RESEARCH','dataset_identity':latest['identity'],
             'dataset_hash':digest(data[STATIC+TEMPORAL+['sample_id']].to_dict('records')),
             'split':splits,'feature_sets':FEATURE_SETS,'threshold':.5,'models':[],
             'independence_rule':'event groups; dates <=3d anywhere in Austria; positives <2km; any sample overlap <400m; transitive union',
             'limitations':['Exploratory retrospective matched case-control study, not prospective hazard probability.',
                            '102 initial candidates are not 102 independent storms.',
                            'Unknown specific Naturgefahren Test reuse license; local research authorization only.']}
    train=data[data.partition=='train'];val=data[data.partition=='validation'];test=data[data.partition=='test']
    results['chance_test']=metrics(test,np.full(len(test),train.label.mean()))
    names=['logistic_regression'] if pilot else ['logistic_regression','random_forest','gradient_boosting']
    predictions=[]
    for name in names:
        for featureset,columns in FEATURE_SETS.items():
            print('FIT',name,featureset,flush=True)
            model=make_model(name);model.fit(train[columns],train.label)
            vp=model.predict_proba(val[columns])[:,1];tp=model.predict_proba(test[columns])[:,1]
            record={'model':name,'features':featureset,'validation':metrics(val,vp),'test':metrics(test,tp)}
            if not pilot: record['test_interval']=bootstrap_ci(test,tp)
            results['models'].append(record)
            joblib.dump({'model':model,'features':columns,'training_sample_ids':train.sample_id.tolist(),
                         'config':latest['config'],'dataset_hash':results['dataset_hash']},modeldir/f'{name}_{featureset}.joblib')
            predictions.extend([{'sample_id':s,'model':name,'features':featureset,'probability_case_control':float(p)} for s,p in zip(test.sample_id,tp)])
            if featureset=='combined':
                importance=permutation_importance(model,val[columns],val.label,n_repeats=10,random_state=42,scoring='average_precision',n_jobs=1)
                record['validation_permutation_importance']=[{'feature':f,'mean':float(m),'std':float(s)} for f,m,s in zip(columns,importance.importances_mean,importance.importances_std)]
    pd.DataFrame(predictions).to_parquet(directory/'test_predictions.parquet',index=False)
    if not pilot:
        # Region selected by event count before model scores; all dependence clusters and 20km border neighbors purged.
        positives=data[data.label==1]
        state=positives.state.value_counts().index[0]
        geographic_test=data[data.state==state]
        geographic_train=data[(data.state!=state)&~data.dependence_cluster.isin(geographic_test.dependence_cluster)]
        nearest=cKDTree(geographic_test[['x','y']].to_numpy()).query(geographic_train[['x','y']].to_numpy())[0]
        invalid=set(geographic_train.loc[nearest<20000,'event_group_id'])
        geographic_train=geographic_train[~geographic_train.event_group_id.isin(invalid)]
        geographic={'held_out_state':state,'train_events':int(geographic_train.event_group_id.nunique()),
                    'test_events':int(geographic_test.event_group_id.nunique()),'purge_m':20000,'models':[]}
        if geographic_train.event_group_id.nunique()>=10 and geographic_test.event_group_id.nunique()>=10:
            for name in names:
                for featureset,columns in FEATURE_SETS.items():
                    model=make_model(name);model.fit(geographic_train[columns],geographic_train.label)
                    p=model.predict_proba(geographic_test[columns])[:,1]
                    geographic['models'].append({'model':name,'features':featureset,'test':metrics(geographic_test,p)})
        else: geographic['limitation']='Insufficient independent training/test events after purging; no geographic score claimed'
        results['geographic_holdout']=geographic
    controls=data[data.label==0]
    results['matching']={c:{'median':float(controls[c].median()),'max':float(controls[c].max()),'p95':float(controls[c].quantile(.95))}
         for c in ['distance_to_positive_m','slope_difference_deg','elevation_difference_m','aspect_difference_deg']}
    results['weather']={'groups_identical_60d_rain':int((data.groupby('event_group_id').rain_sum_60d.nunique()==1).sum()),
                       'unique_grid_cells':len(data[['weather_grid_lon','weather_grid_lat']].drop_duplicates()),'retained_hours':1438}
    write_json(reportdir/'metrics.json',results)
    write_json(directory/'evaluation.json',{'report':str(reportdir/'metrics.json'),'pilot':pilot})
    print('RESULTS',reportdir/'metrics.json',splits,flush=True)
    return results
