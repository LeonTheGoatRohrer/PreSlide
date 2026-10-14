"""Diagnostics from frozen OOF predictions; no original test fitting or selection."""
import argparse
from urllib.parse import urlencode

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

from .common import read_json, write_json
from .stability import LOCAL, REPORT, ROOT, KEYS, prepare, folds, sha, score, event_scores, matrix
from .pipeline import STATIC
from .weather import TEMPORAL, features_from_series, expected_times
from .terrain import PROJECT
from .matching import Exclusions, angular_distance

METRICS = ['average_precision','roc_auc','within_group_auc','positive_rank','top1_fractional','controls_beaten']
MATCH = ['slope_difference_deg','elevation_difference_m','aspect_difference_deg','distance_to_positive_m','matching_score']


def csv(frame, name, private=False):
    target = LOCAL if private else REPORT
    frame.to_csv(target/name, index=False)


def table(frame, digits=4):
    """Small dependency-free Markdown formatter."""
    def fmt(v):
        if isinstance(v, (float,np.floating)):
            return '' if not np.isfinite(v) else f'{v:.{digits}f}'
        return str(v)
    return '\n'.join(['| '+' | '.join(frame.columns)+' |', '| '+' | '.join(['---']*len(frame.columns))+' |']+
                     ['| '+' | '.join(fmt(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])


def audit(dev, directory):
    """Recompute all development weather features from immutable local HTTP responses."""
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    check(((dev.label==1)==(dev.sample_type=='POSITIVE')).all(), 'label/type inconsistency')
    check((dev.loc[dev.label==0,'sample_type']=='PSEUDO_NEGATIVE').all(), 'control type inconsistency')
    check(dev.elevation.between(0,4500).all() and dev.slope.between(5,90).all(), 'terrain range')
    x,y = PROJECT.transform(dev.longitude.to_numpy(),dev.latitude.to_numpy())
    check(np.allclose(dev[['x','y']],np.column_stack([x,y]),atol=.001), 'coordinate order/CRS')
    controls=dev[dev.label==0]
    cfg=read_json(directory/'inputs.json')['config']
    check(Exclusions(cfg).allowed(controls[['x','y']].to_numpy()).all(), 'inventory exclusion')
    check(controls.distance_to_positive_m.between(750,10000).all(), 'locality')
    recomputed=0
    for _,g in dev.groupby('event_group_id'):
        pos=g[g.label==1].iloc[0]; c=g[g.label==0]
        check(np.allclose(np.linalg.norm(c[['x','y']].to_numpy()-pos[['x','y']].to_numpy(dtype=float),axis=1),c.distance_to_positive_m), 'distance mismatch')
        check(np.allclose(angular_distance(c.aspect.to_numpy(),pos.aspect),c.aspect_difference_deg), 'circular aspect mismatch')
        meta=read_json(directory/'events'/str(pos.event_group_id)/'weather_validation.json')
        url='https://dataset.api.hub.geosphere.at/v1/timeseries/historical/'+meta['resource']
        url += '?' + urlencode(sorted({'f':'json',**meta['params']}.items()),doseq=True)
        import hashlib
        key=hashlib.sha256(url.encode()).hexdigest()
        rawpath=ROOT/'data/raw/http'/f'{key}.json'
        rawmeta=read_json(rawpath.with_suffix('.meta.json'))
        check(rawmeta['url']==url and rawmeta['sha256']==sha(rawpath), 'raw weather checksum')
        response=read_json(rawpath)
        times=pd.to_datetime(response['timestamps'],utc=True)
        points=response['features']
        cells=np.array([PROJECT.transform(*p['geometry']['coordinates']) for p in points])
        for row in g.itertuples():
            cell=points[int(np.argmin(np.linalg.norm(cells-[row.x,row.y],axis=1)))]
            check(np.allclose(cell['geometry']['coordinates'],[row.weather_grid_lon,row.weather_grid_lat]), 'wrong weather cell')
            p=cell['properties']['parameters']
            values=features_from_series(times,p['RR']['data'],p['T2M']['data'],row.event_date)
            check(np.allclose([values[f] for f in TEMPORAL],[getattr(row,f) for f in TEMPORAL],rtol=1e-12,atol=1e-10), 'weather feature recomputation')
            check(pd.Timestamp(row.weather_first_timestamp)==expected_times(row.event_date,60)[0], 'first timestamp')
            recomputed+=1
    quality=pd.DataFrame([{'feature':c,'minimum':dev[c].min(),'maximum':dev[c].max(),
                          'std':dev[c].std(ddof=0),'unique_values':dev[c].nunique(),
                          'largest_value_fraction':dev[c].value_counts(normalize=True).max()} for c in STATIC+TEMPORAL])
    csv(quality,'feature_quality.csv')
    result={'status':'PASS' if not errors else 'FAIL','errors':errors,'recomputed_weather_samples':recomputed,
            'development_events':int(dev.event_group_id.nunique()),'development_clusters':int(dev.dependence_cluster.nunique()),
            'constant_features':quality.loc[quality['std']==0,'feature'].tolist(),
            'checks':['binary label orientation','one positive + five controls','same t0 and UTC envelopes',
                      'raw-cache checksums','nearest weather cell','all 18 feature recomputations',
                      'CRS round trip','circular aspect','actual inventory exclusions','local controls','original checksums']}
    write_json(REPORT/'pipeline_audit.json',result)
    if errors:
        raise ValueError('Audit failed; original artifacts preserved: '+str(errors))
    print('AUDIT PASS: all 270 development weather feature vectors reproduced from raw caches',flush=True)


def primary_summaries(dev):
    p=pd.read_parquet(LOCAL/'primary_predictions.parquet')
    rows=[];events=[];foldrows=[]
    for (rep,name,features),g in p.groupby(['repetition','model','features']):
        rows.append({'repetition':rep,'model':name,'features':features,**score(g,g.probability)})
        e=event_scores(g,g.probability)
        e['repetition'],e['model'],e['features']=rep,name,features
        events.append(e)
        for fold,h in g.groupby('fold'):
            foldrows.append({'repetition':rep,'fold':fold,'model':name,'features':features,**score(h,h.probability)})
    metrics=pd.DataFrame(rows); e=pd.concat(events,ignore_index=True)
    csv(metrics,'stability_metrics.csv');csv(pd.DataFrame(foldrows),'fold_metrics.csv')
    joined=metrics[metrics.features=='combined'].merge(metrics[metrics.features=='static'],on=['repetition','model'],suffixes=('_combined','_static'))
    deltas=joined[['repetition','model']].copy()
    for metric in METRICS:
        deltas[metric]=joined[metric+'_combined']-joined[metric+'_static']
    csv(deltas,'performance_deltas.csv')
    summary=[]
    for name,g in deltas.groupby('model'):
        for metric in METRICS:
            v=g[metric]
            summary.append({'model':name,'metric':metric,'median':v.median(),'minimum':v.min(),'maximum':v.max(),
                            'improved_repetitions':int((v<0).sum() if metric=='positive_rank' else (v>0).sum()),'repetitions':len(v)})
    csv(pd.DataFrame(summary),'delta_summary.csv')
    ranks=e.pivot(index=['repetition','model','event_group_id'],columns='features',values='positive_rank')
    ranks['weather_rank_delta']=ranks['static']-ranks['combined']  # positive means improved
    e=e.merge(ranks[['weather_rank_delta']].reset_index(),on=['repetition','model','event_group_id'])
    e.to_parquet(LOCAL/'event_results.parquet',index=False)
    aliases={v:f'DEV-{i:03d}' for i,v in enumerate(sorted(dev.event_group_id.unique()),1)}
    write_json(LOCAL/'private_event_aliases.json',aliases)
    export=e.drop(columns='dependence_cluster').copy()
    export['event_group_id']=export.event_group_id.map(aliases)
    csv(export,'event_pairwise_results.csv')
    consistency=e[e.features=='combined'].groupby(['model','event_group_id']).agg(
        improved_repetitions=('weather_rank_delta',lambda x:int((x>0).sum())),
        worsened_repetitions=('weather_rank_delta',lambda x:int((x<0).sum())),
        median_rank_delta=('weather_rank_delta','median')).reset_index()
    counts=consistency.groupby('model').agg(events=('event_group_id','size'),
        improved_all_five=('improved_repetitions',lambda x:int((x==5).sum())),
        improved_at_least_three=('improved_repetitions',lambda x:int((x>=3).sum())),
        worsened_at_least_three=('worsened_repetitions',lambda x:int((x>=3).sum())))
    csv(counts.reset_index(),'event_consistency.csv')
    return metrics,deltas,e


def weather_differences(dev):
    aliases=read_json(LOCAL/'private_event_aliases.json')
    rows=[];pairs=[]
    scales=dev[TEMPORAL].std(ddof=0)
    for event,g in dev.groupby('event_group_id'):
        positive=g[g.label==1].iloc[0];controls=g[g.label==0]
        for feature in TEMPORAL:
            diff=(controls[feature]-positive[feature]).abs()
            sd=float(scales[feature]); tolerance=.01*sd
            rows.append({'event':aliases[event],'feature':feature,'state':positive.state,'year':int(positive.event_date[:4]),
                         'std':g[feature].std(ddof=0),'range':g[feature].max()-g[feature].min(),
                         'mean_absolute_difference':diff.mean(),'max_absolute_difference':diff.max(),
                         'mean_difference_over_dev_sd':diff.mean()/sd if sd>0 else 0,
                         'controls_nearly_equal':int((diff<=tolerance).sum()),
                         'controls_exactly_equal':int((diff==0).sum()),'median_distance_m':controls.distance_to_positive_m.median()})
            for i,c in controls.iterrows():
                pairs.append({'event':aliases[event],'feature':feature,'distance_bin': '<3 km' if c.distance_to_positive_m<3000 else ('3–6 km' if c.distance_to_positive_m<6000 else '6–10 km'),
                              'absolute_difference':abs(c[feature]-positive[feature]),
                              'normalized_difference':abs(c[feature]-positive[feature])/sd if sd else 0,
                              'same_cell':c.weather_grid_lon==positive.weather_grid_lon and c.weather_grid_lat==positive.weather_grid_lat})
    w=pd.DataFrame(rows);pairs=pd.DataFrame(pairs)
    csv(w,'weather_distinguishability.csv')
    for dimension in ['feature','state','year']:
        keys=['feature'] if dimension=='feature' else [dimension,'feature']
        agg=w.groupby(keys).agg(events=('event','nunique'),median_range=('range','median'),median_std=('std','median'),
             median_abs_difference=('mean_absolute_difference','median'),median_normalized_difference=('mean_difference_over_dev_sd','median'),
             groups_four_or_more_controls_nearly_equal=('controls_nearly_equal',lambda x:int((x>=4).sum()))).reset_index()
        csv(agg,f'weather_by_{dimension}.csv')
    csv(pairs.groupby(['feature','distance_bin']).agg(pairs=('event','size'),events=('event','nunique'),
        median_absolute_difference=('absolute_difference','median'),median_normalized_difference=('normalized_difference','median')).reset_index(),'weather_by_distance.csv')
    per_event=w.groupby('event').agg(nearly_identical_features=('controls_nearly_equal',lambda v:int((v>=4).sum())),
                                     identical_features=('range',lambda v:int((v==0).sum())))
    csv(per_event.reset_index(),'weather_by_event.csv')
    info={'events':int(dev.event_group_id.nunique()),'weather_features':len(TEMPORAL),
          'same_positive_control_cell_pairs':int(pairs[pairs.feature==TEMPORAL[0]].same_cell.sum()),
          'total_pairs':int(len(pairs)/len(TEMPORAL)),
          'events_nearly_equal_at_least_16_of_18_features':int((per_event.nearly_identical_features>=16).sum()),
          'events_all_features_exactly_identical':int((per_event.identical_features==18).sum())}
    write_json(REPORT/'weather_summary.json',info)
    text='# Weather distinguishability — development only\n\n'
    text+='Source: [GeoSphere INCA v1](https://data.hub.geosphere.at/dataset/inca-v1-1h-1km), verified 2026-10-14: 1 km × 1 km, hourly, UTC; EPSG:31287; CC BY 4.0. Terrain enters the weather analysis, so weather is not independent of terrain.\n\n'
    text+='Nominal 1/3/7/14/30/60-day windows retain 22/70/166/334/718/1438 hours. “Nearly equal” means absolute difference ≤1% of that feature’s development SD; this descriptive scaling is never used for model preprocessing. A group is nearly equal for a feature if at least four of its five controls meet that threshold. Zero-rain short windows can be naturally identical.\n\n'
    text+=table(pd.DataFrame([info]))+'\n\n'+table(pd.read_csv(REPORT/'weather_by_feature.csv'))
    text+='\n\nAll event-level cases are in the local-only `weather_by_event.csv` and `weather_distinguishability.csv`; all state/year/distance strata are reported. Spatial variation establishes distinguishability of inputs, not useful predictive signal. Near identity can reflect dry weather or spatial smoothing; it does not prove weather is irrelevant. Different grid cells do not establish slope-scale fidelity. This analysis cannot identify whether an unresolved physical precursor exists below 1 km.\n'
    (REPORT/'weather_distinguishability.md').write_text(text,encoding='utf-8')
    return w,info


def importance(dev,splits,config,pilot=False):
    """Reuse saved models; within-group shuffles keep event-scale weather fixed."""
    allrows=[]
    for rep,seed,fold,train,held in folds(dev,splits):
        path=LOCAL/'importance'/f'r{rep}_f{fold}.parquet'
        meta_path=path.with_suffix('.json')
        model_paths=[LOCAL/'fits/primary'/f'r{rep}_f{fold}'/'combined'/name/'model.joblib' for name in config['models']]
        spec={'models':{str(p.relative_to(LOCAL)):sha(p) for p in model_paths},'protocol':sha(ROOT/'config/stability_v02.json')}
        if path.exists() and meta_path.exists():
            meta=read_json(meta_path)
            if meta['spec']!=spec or meta['sha256']!=sha(path):
                raise ValueError('Importance checkpoint changed')
            allrows.append(pd.read_parquet(path))
            if pilot: return
            continue
        rows=[]
        for name,modelpath in zip(config['models'],model_paths):
            fitted=joblib.load(modelpath);model=fitted['model'];columns=fitted['columns']
            x=matrix(held,columns).reset_index(drop=True)
            if name=='logistic_regression':
                for feature,value in zip(columns,model.steps[-1][1].coef_[0]):
                    rows.append({'model':name,'feature':feature,'kind':'standardized_coefficient','value':value})
                continue
            # One worker for cheap prediction calls; learned model is unchanged.
            if hasattr(model,'n_jobs'): model.n_jobs=1
            with threadpool_limits(limits=2):
                base=average_precision_score(held.label,model.predict_proba(x)[:,1])
                indices=list(held.reset_index(drop=True).groupby('event_group_id').indices.values())
                for kind in ['within_event_permutation','global_permutation']:
                    for j,feature in enumerate(columns):
                        drops=[]
                        for repeat in range(config['permutation_repeats']):
                            rng=np.random.default_rng(seed*100000+fold*1000+j*10+repeat)
                            shuffled=x.copy()
                            if kind=='within_event_permutation':
                                for ii in indices:
                                    shuffled.loc[ii,feature]=rng.permutation(x.loc[ii,feature].to_numpy())
                            else:
                                shuffled[feature]=rng.permutation(x[feature].to_numpy())
                            drops.append(base-average_precision_score(held.label,model.predict_proba(shuffled)[:,1]))
                        rows.append({'model':name,'feature':feature,'kind':kind,'value':np.mean(drops)})
            if hasattr(model,'feature_importances_'):
                for feature,value in zip(columns,model.feature_importances_):
                    rows.append({'model':name,'feature':feature,'kind':'native_importance','value':value})
        f=pd.DataFrame(rows);f['repetition']=rep;f['fold']=fold;f['evaluation_samples']=len(held)
        path.parent.mkdir(parents=True,exist_ok=True);f.to_parquet(path,index=False)
        write_json(meta_path,{'spec':spec,'sha256':sha(path)})
        allrows.append(f)
        print(f'IMPORTANCE repetition {rep}/5 fold {fold}/4 checkpoint',flush=True)
        if pilot:return
    raw=pd.concat(allrows,ignore_index=True)
    csv(raw,'feature_importance_folds.csv')
    # Equal fold averaging is explicit; this is importance, not a pooled AP estimate.
    reps=raw.groupby(['repetition','model','feature','kind']).value.mean().reset_index()
    csv(reps,'feature_importance_repetitions.csv')
    summary=reps.groupby(['model','feature','kind']).value.agg(median='median',minimum='min',maximum='max',std='std',
        positive_repetitions=lambda x:int((x>0).sum()),negative_repetitions=lambda x:int((x<0).sum()),
        repetitions_above_005=lambda x:int((x>config['importance_meaningful_ap_drop']).sum())).reset_index()
    summary['sign_consistency']=summary[['positive_repetitions','negative_repetitions']].max(axis=1)/5
    csv(summary,'feature_stability.csv')
    (REPORT/'feature_stability.md').write_text('# Feature stability — exploratory\n\nCombined models, all 20 held-out folds. Three deterministic permutations per feature per fold. The primary shuffle stays within each six-slope event; global row permutation is secondary and can create implausible combinations. Four fold importances are equally averaged per repetition; median/range across five repetitions. These are descriptive, not confidence intervals. An AP drop >0.005 is a predeclared descriptive threshold, not significance.\n\nLR coefficients refer to training-standardized variables; sign consistency is shown without treating magnitude as AP. RF native impurity importance is secondary. Histogram boosting has no public native impurity importance; SHAP was not added. Correlated cumulative windows share signal and individual permutation can underestimate their joint contribution. Importance in weak models does not establish physical irrelevance.\n\nSee [scikit-learn permutation guidance](https://scikit-learn.org/stable/modules/permutation_importance.html). All features and both permutation methods remain in CSVs; figures show all 22 features.\n',encoding='utf-8')


def sensitivity(dev,events):
    p=pd.read_parquet(LOCAL/'primary_predictions.parquet')
    positives=dev[dev.label==1].copy()
    cluster=positives.groupby('dependence_cluster').size().rename('events').reset_index()
    cluster['event_fraction']=cluster.events/len(positives)
    cluster.to_csv(LOCAL/'cluster_sizes.csv',index=False)
    # Public histogram omits source IDs and dates.
    csv(cluster.groupby('events').size().rename('clusters').reset_index(),'storm_cluster_sizes.csv')
    positives.groupby('event_date').size().rename('events').to_csv(LOCAL/'event_date_counts.csv')
    csv(positives.groupby('event_date').size().value_counts().sort_index().rename_axis('events_on_date').rename('dates').reset_index(),'event_date_size_distribution.csv')
    rows=[]
    for (rep,model,features),g in p.groupby(['repetition','model','features']):
        w=1/g.groupby('dependence_cluster').label.transform('size')
        eg=events[(events.repetition==rep)&(events.model==model)&(events.features==features)]
        ordinary=score(g,g.probability)
        balanced={'average_precision':average_precision_score(g.label,g.probability,sample_weight=w),
                  'roc_auc':roc_auc_score(g.label,g.probability,sample_weight=w),
                  'within_group_auc':eg.groupby('dependence_cluster').pairwise_auc.mean().mean(),
                  'positive_rank':eg.groupby('dependence_cluster').positive_rank.mean().mean(),
                  'top1_fractional':eg.groupby('dependence_cluster').top1_fractional.mean().mean()}
        for method,m in [('event_weighted',ordinary),('dependency_balanced',balanced)]:
            rows.append({'repetition':rep,'model':model,'features':features,'method':method,
                         **{key:m[key] for key in balanced}})
    storm=pd.DataFrame(rows);csv(storm,'storm_sensitivity.csv')
    st=storm[storm.features=='static'].merge(storm[storm.features=='combined'],on=['repetition','model','method'],suffixes=('_static','_combined'))
    for key in ['average_precision','within_group_auc']:
        st[key+'_delta']=st[key+'_combined']-st[key+'_static']
    csv(st[['repetition','model','method','average_precision_delta','within_group_auc_delta']],'storm_deltas.csv')
    # Remove each cluster from fixed OOF evaluation only. No retraining/selection.
    loo=[]
    avg=p.groupby(['model','features']+KEYS).probability.mean().reset_index()
    for omitted in sorted(dev.dependence_cluster.unique()):
        for (model,features),g in avg[avg.dependence_cluster!=omitted].groupby(['model','features']):
            loo.append({'omitted_cluster':omitted,'model':model,'features':features,**score(g,g.probability)})
    pd.DataFrame(loo).to_csv(LOCAL/'leave_one_cluster_out_evaluation.csv',index=False)
    text='# Storm/dependency influence — exploratory\n\n'
    text+=f'{len(positives)} events; {len(cluster)} frozen dependency clusters. Largest cluster: {cluster.events.max()} events ({cluster.event_fraction.max():.1%}); effective equal-event cluster count 1/sum(shares²) = {1/(cluster.event_fraction**2).sum():.2f}. Clusters are conservative time/spatial unions, not verified meteorological storm identities.\n\n'
    text+='Primary event-weighted metrics remain unchanged. Diagnostic sample weights give every dependency cluster total weight one; within-event metrics are averaged first by cluster, then across clusters. This changes evaluation influence only. Large clusters may still affect model training. A supplementary leave-one-cluster-out evaluation of fixed mean OOF predictions is local; it is not a retrained leave-storm-out experiment.\n\n'
    text+=table(st.groupby(['model','method'])[['average_precision_delta','within_group_auc_delta']].median().reset_index())+'\n\nFive repeated partitions reuse the same events; they are not five independent storm samples. See all repetitions in storm_deltas.csv.\n'
    (REPORT/'storm_sensitivity.md').write_text(text,encoding='utf-8')
    # One event row per model after averaging OOF diagnostics over repetitions; no repeated-row pseudoreplication.
    matching=dev[dev.label==0].groupby('event_group_id')[MATCH].mean()
    mean=events.groupby(['model','features','event_group_id']).agg(positive_rank=('positive_rank','mean'),controls_beaten=('controls_beaten','mean'),
        positive_score=('positive_score','mean'),weather_rank_delta=('weather_rank_delta','mean')).reset_index()
    mean=mean.merge(matching,on='event_group_id').merge(positives[['event_group_id','source_position_upper_m','state','event_date','dependence_cluster']],on='event_group_id')
    mean['year']=mean.event_date.str[:4]
    correlation=[]
    for (model,features),g in mean.groupby(['model','features']):
        for predictor in MATCH:
            for outcome in ['positive_rank','controls_beaten','positive_score','weather_rank_delta']:
                rho=spearmanr(g[predictor],g[outcome]).statistic if g[outcome].nunique()>1 else np.nan
                correlation.append({'model':model,'features':features,'matching_measure':predictor,'outcome':outcome,'spearman_rho':rho,'events':len(g),'clusters':g.dependence_cluster.nunique()})
    corr=pd.DataFrame(correlation);csv(corr,'matching_correlations.csv')
    for dimension in ['source_position_upper_m','state','year']:
        aggregate=mean.groupby(['model','features',dimension]).agg(events=('event_group_id','nunique'),clusters=('dependence_cluster','nunique'),
           mean_positive_rank=('positive_rank','mean'),mean_controls_beaten=('controls_beaten','mean'),mean_weather_rank_delta=('weather_rank_delta','mean'),
           mean_slope_mismatch=('slope_difference_deg','mean'),mean_distance_m=('distance_to_positive_m','mean')).reset_index()
        csv(aggregate,'position_uncertainty.csv' if dimension=='source_position_upper_m' else f'performance_by_{dimension}.csv')
    combined=corr[(corr.features=='combined')&(corr.outcome.isin(['positive_rank','weather_rank_delta']))]
    (REPORT/'matching_diagnostics.md').write_text('# Matching quality vs performance — exploratory\n\nPer-event mean mismatch across five controls, circular aspect distance, distance in EPSG:31287 metres, and original matching score. Outcomes are averaged over five held-out predictions before association: 45 events, not 225 independent repetitions. Rank delta = terrain rank − combined rank, positive means improvement. For positive rank, negative correlation means more success with worse matching; for rank delta, positive correlation means more weather benefit with worse matching. Scores are case-control scores, not risk.\n\n'+table(combined[['model','matching_measure','outcome','spearman_rho','events','clusters']])+'\n\nAll variants and outcomes remain in matching_correlations.csv. Correlations are descriptive and cluster dependent; no multiple-testing significance or causal claim. No event is removed and no controls are rematched. Small associations cannot exclude selection artifacts; same-location terrain matching omits geology and soils.\n',encoding='utf-8')
    # Merge original offset diagnostic, subset to development only.
    directory=ROOT/'data/processed'/read_json(ROOT/'config/stability_v02.json')['dataset_identity']
    offsets=pd.DataFrame(read_json(directory/'position_sensitivity.json'))
    offsets=offsets[offsets.event_id.isin(positives.event_group_id)]
    offset_summary=offsets.groupby('source_category_upper_m').agg(events=('event_id','size'),median_slope_range=('slope_range_deg','median'),
                    events_exceeding_5deg=('maximum_slope_change_deg',lambda x:int((x>5).sum()))).reset_index()
    csv(offset_summary,'position_offset_summary.csv')
    # Weather differences by source uncertainty category, no category relabeling.
    aliases=read_json(LOCAL/'private_event_aliases.json')
    position_map={aliases[r.event_group_id]:r.source_position_upper_m for r in positives.itertuples()}
    wd=pd.read_csv(REPORT/'weather_distinguishability.csv');wd['source_position_upper_m']=wd.event.map(position_map)
    csv(wd.groupby(['source_position_upper_m','feature']).agg(events=('event','nunique'),median_normalized_difference=('mean_difference_over_dev_sd','median')).reset_index(),'position_weather_differences.csv')
    pos=pd.read_csv(REPORT/'position_uncertainty.csv')
    (REPORT/'position_uncertainty.md').write_text('# Positional uncertainty — exploratory\n\nAccepted source upper-bound categories (5, 20, 100 m) are unchanged and are not independently surveyed accuracy. Sizes are stated for each model/variant; repeated evaluations do not create additional events. Differences may be confounded with region, storm, date and process. No performance-driven quality-threshold changes.\n\n'+table(pos[pos.features=='combined'])+'\n\nOriginal offset diagnostic, restricted to development events:\n\n'+table(offset_summary)+'\n\nFeature-wise weather differences by category are in position_weather_differences.csv. A category association cannot establish that positional error caused poor performance. Small subgroups cannot support a reliable material-effect estimate.\n',encoding='utf-8')
    return storm,corr


def exploratory_tables(dev):
    primary=pd.read_parquet(LOCAL/'primary_predictions.parquet')
    diag=pd.read_parquet(LOCAL/'diagnostic_predictions.parquet')
    selection=read_json(LOCAL/'learning_tree_selection.json')
    full=primary[(primary.model=='logistic_regression') & primary.features.isin(['temporal','combined'])].copy()
    full['window']='full'
    ablation=pd.concat([diag[diag.analysis=='ablation'],full],ignore_index=True)
    rows=[]
    for (rep,model,features,window),g in ablation.groupby(['repetition','model','features','window']):
        rows.append({'repetition':rep,'model':model,'features':features,'window':window,**score(g,g.probability)})
    abl=pd.DataFrame(rows);csv(abl,'weather_window_ablation.csv')
    full=primary[(primary.features=='combined') & primary.model.isin(['logistic_regression',selection['selected']])].copy()
    full['fraction']=1.;full['training_clusters']=12
    counts=dev.groupby('dependence_cluster').size()/6
    for (rep,fold),g in full.groupby(['repetition','fold']):
        full.loc[g.index,'training_events']=int(counts[~counts.index.isin(g.dependence_cluster)].sum())
    learning=pd.concat([diag[diag.analysis=='learning'],full],ignore_index=True)
    rows=[];foldrows=[]
    for (rep,model,fraction),g in learning.groupby(['repetition','model','fraction']):
        rows.append({'repetition':rep,'model':model,'fraction':fraction,'training_clusters_per_fold':int(g.training_clusters.iloc[0]),
                     'min_training_events':int(g.training_events.min()),'max_training_events':int(g.training_events.max()),**score(g,g.probability)})
        for fold,f in g.groupby('fold'):
            foldrows.append({'repetition':rep,'fold':fold,'model':model,'fraction':fraction,'training_clusters':int(f.training_clusters.iloc[0]),
                             'training_events':int(f.training_events.iloc[0]),**score(f,f.probability)})
    lc=pd.DataFrame(rows);csv(lc,'learning_curve.csv');csv(pd.DataFrame(foldrows),'learning_curve_folds.csv')
    interactions=diag[diag.analysis=='interactions']
    rows=[]
    for rep,g in interactions.groupby('repetition'):
        rows.append({'repetition':rep,'model':'logistic_regression','features':'combined_interactions',**score(g,g.probability)})
    reference=pd.read_csv(REPORT/'stability_metrics.csv')
    inter=pd.concat([pd.DataFrame(rows),reference[(reference.model=='logistic_regression')&reference.features.isin(['static','combined'])]],ignore_index=True)
    csv(inter,'interaction_metrics.csv')
    (REPORT/'exploratory_protocol.md').write_text('# Predeclared exploratory diagnostics\n\nWeather ablation: Logistic Regression, weather-only and terrain+weather, all 20 frozen folds; immediate 1–3d, short 7–14d, antecedent 30–60d, full. Existing cumulative features remain unchanged: these are cumulative lookbacks, not disjoint time segments. Full uses saved primary predictions; no window is selected for test evaluation.\n\nLearning curves: Logistic Regression plus '+selection['selected']+' (highest development median combined AP among the two fixed tree families; see local selection checkpoint). Nested 25/50/75/100% of each fold’s 12 training dependency groups = 3/6/9/12 groups; four untouched evaluation groups per fold. All five seeds. 100% means all outer-training groups, not all 16 development groups. OOF metrics pool the four folds per repetition; fractions use identical held-out events. Tree selection uses these same development results, so its curve is exploratory and selection-biased. No precise future-data performance extrapolation.\n\nInteractions: LR combined plus exactly rain_sum_3d×slope, rain_sum_30d×slope and rain_sum_7d×elevation. Products use physical units before training-only standardization; main effects retained. No original test/Steiermark scoring. Tree models already encode implicit nonlinear interactions.\n\nAll 4 windows, all 4 fractions, all repetitions and the interaction comparator are reported, irrespective of result.\n',encoding='utf-8')
    return abl,lc,inter


def bootstrap(config):
    p=pd.read_parquet(LOCAL/'primary_predictions.parquet')
    # Average five held-out predictions for each original sample, then paired cluster resampling.
    avg=p.groupby(['model','features']+KEYS).probability.mean().reset_index()
    rows=[]
    for name,g in avg.groupby('model'):
        a=g[g.features=='static'].sort_values('sample_id').reset_index(drop=True)
        b=g[g.features=='combined'].set_index('sample_id').loc[a.sample_id].reset_index()
        clusters=sorted(a.dependence_cluster.unique())
        mapping={c:np.flatnonzero(a.dependence_cluster.to_numpy()==c) for c in clusters}
        ae=event_scores(a,a.probability).set_index('event_group_id')
        be=event_scores(b,b.probability).set_index('event_group_id')
        diffs={c:(be.loc[ae[ae.dependence_cluster==c].index,'pairwise_auc']-ae.loc[ae.dependence_cluster==c].pairwise_auc).to_numpy() for c in clusters}
        rng=np.random.default_rng(config['bootstrap_seed'])
        values=[]
        for _ in range(config['bootstrap_draws']):
            draw=rng.choice(clusters,len(clusters),replace=True)
            ii=np.concatenate([mapping[c] for c in draw]); y=a.label.to_numpy()[ii]
            ap=a.probability.to_numpy()[ii];bp=b.probability.to_numpy()[ii]
            values.append([average_precision_score(y,bp)-average_precision_score(y,ap),
                           roc_auc_score(y,bp)-roc_auc_score(y,ap),np.concatenate([diffs[c] for c in draw]).mean()])
        for j,metric in enumerate(['average_precision','roc_auc','within_group_auc']):
            lo,hi=np.quantile(np.array(values)[:,j],[.025,.975])
            rows.append({'model':name,'metric':metric,'lower_025':lo,'upper_975':hi,'draws':config['bootstrap_draws'],
                         'clusters':len(clusters),'method':'paired cluster bootstrap of mean OOF scores; fixed models, exploratory'})
    csv(pd.DataFrame(rows),'paired_bootstrap.csv')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',action='store_true')
    parser.add_argument('--importance',action='store_true')
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--final',action='store_true')
    args=parser.parse_args()
    dev,splits,config,directory=prepare()
    if args.base:
        audit(dev,directory)
        _,_,events=primary_summaries(dev)
        weather_differences(dev)
        sensitivity(dev,events)
        bootstrap(config)
    if args.importance:
        importance(dev,splits,config,pilot=args.pilot)
    if args.final:
        exploratory_tables(dev)
        from .stability_report import generate
        generate(dev,config)


if __name__=='__main__':
    main()
