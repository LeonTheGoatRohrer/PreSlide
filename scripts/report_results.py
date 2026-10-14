"""Aggregate scientific report; never exports raw inventory records."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from preslide.common import read_json,write_json,candidates
from preslide.sources import ROOT
from preslide.terrain import local_terrain,PROJECT,sample

latest=read_json(ROOT/'data/processed/latest.json');directory=ROOT/'data/processed'/latest['identity']
data=pd.read_parquet(directory/'evaluation_dataset.parquet')
report=read_json(ROOT/'reports/experiment/metrics.json')
out=ROOT/'reports/experiment';out.mkdir(exist_ok=True)
reasons=Counter(s['reason'].split(':')[0] for s in latest['status'] if s['status']=='excluded')

# Deterministic geometric perturbation diagnostic, not simulated research samples or model inputs.
lookup={e['event_id']:e for e in candidates()};uncertainty=[]
for row in data[data.label==1].itertuples():
    e=lookup[row.event_group_id];t=local_terrain(e,latest['config']);x,y=PROJECT.transform(e['longitude'],e['latitude'])
    radius=e['position_accuracy_upper_m']
    a=np.linspace(0,2*np.pi,16,endpoint=False)
    xx=x+np.concatenate([.5*radius*np.cos(a),radius*np.cos(a)])
    yy=y+np.concatenate([.5*radius*np.sin(a),radius*np.sin(a)])
    slopes=sample(t,xx,yy)['slope']
    uncertainty.append({'event_id':e['event_id'],'source_category_upper_m':radius,'slope_range_deg':float(np.nanmax(slopes)-np.nanmin(slopes)),
                        'maximum_slope_change_deg':float(np.nanmax(abs(slopes-row.slope))),'any_below_minimum':bool((slopes<5).any())})
write_json(directory/'position_sensitivity.json',uncertainty)
report['position_sensitivity']={'diagnostic':'32 deterministic offsets at half/full source-reported category upper radius; no accuracy distribution inferred',
    'median_slope_range_deg':float(np.median([r['slope_range_deg'] for r in uncertainty])),
    'events_with_slope_change_above_matching_caliper':sum(r['maximum_slope_change_deg']>5 for r in uncertainty),
    'events_with_any_offset_slope_below_5deg':sum(r['any_below_minimum'] for r in uncertainty)}
report['initial_candidates']=102;report['complete_events']=len(uncertainty);report['exclusions']=dict(reasons)
write_json(out/'metrics.json',report)

plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#f5f3eb','axes.facecolor':'#f5f3eb','axes.labelcolor':'#183c34','text.color':'#183c34'})
fig,axes=plt.subplots(1,2,figsize=(11,4.7),layout='constrained')
names=['logistic_regression','random_forest','gradient_boosting'];labels=['Logistische Regression','Random Forest','Gradient Boosting']
colors=['#adb8a8','#d2a052','#196b59']
for k,(metric,title,baseline) in enumerate([('average_precision','Average Precision',1/6),('within_group_auc','AUC innerhalb der Ereignisgruppen',.5)]):
    ax=axes[k]
    for j,feature in enumerate(['static','temporal','combined']):
        vals=[next(r['test'][metric] for r in report['models'] if r['model']==name and r['features']==feature) for name in names]
        ax.bar(np.arange(3)+(j-1)*.23,vals,.23,label=['Gelände','Wetter','Kombiniert'][j],color=colors[j])
    ax.axhline(baseline,color='#a85f47',linestyle='--',linewidth=1,label='Zufallsreferenz')
    ax.set_xticks(np.arange(3),labels,rotation=15,ha='right');ax.set_ylim(0,1);ax.set_title(title,loc='left',fontweight='bold')
    ax.set_ylabel('Zurückgehaltene Testgruppen');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axes[0].legend(fontsize=8,frameon=False)
fig.suptitle('PreSlide · Explorative Auswertung, keine Warnprognose',fontsize=14,fontweight='bold')
fig.savefig(out/'model_comparison.png',dpi=170);plt.close(fig)

controls=data[data.label==0]
fig,axes=plt.subplots(1,3,figsize=(11,3.8),layout='constrained')
for ax,column,label,limit in zip(axes,['slope_difference_deg','elevation_difference_m','aspect_difference_deg'],['Neigungsdifferenz (°)','Höhendifferenz (m)','Expositionsdifferenz (°)'],[5,150,45]):
    ax.hist(controls[column],bins=15,color='#196b59',alpha=.85);ax.axvline(limit,color='#a85f47',linestyle='--')
    ax.set_xlabel(label);ax.set_ylabel('Kontrollen');ax.set_xlim(0,limit*1.05)
fig.suptitle('Topographische Übereinstimmung · feste Auswahlgrenzen',fontweight='bold')
fig.savefig(out/'matching_quality.png',dpi=170);plt.close(fig)

lines=['# Results — executed PreSlide V0 experiment','',f"Run date: 2026-10-14. Dataset identity: `{latest['identity']}`.",'',
       f"**{len(uncertainty)} of 102 candidate events completed, with {len(controls)} matched pseudo-negative controls ({len(data)} samples).** All retained samples have real pre-event terrain and guarded 60-day INCA histories. No synthetic research data.",'',
       '## Exclusions','',* [f'- {reason}: {count} events' for reason,count in reasons.items()], '',
       'No quality threshold was relaxed after inspecting metrics. Negative precipitation is rejected rather than silently clipped. Weather-related exclusions can introduce selection bias by date and region.','',
       '## Frozen split','', '| Partition | Events | Dependence clusters | Samples |','|---|---:|---:|---:|']
for name,s in report['split'].items(): lines.append(f"| {name} | {s['events']} | {s['clusters']} | {s['samples']} |")
lines+=['','Event groups, national 3-day episode clusters, nearby positives and overlapping sample patches remain intact. These clusters are conservative heuristics; residual geographic dependence remains.','',
        '## All planned model comparisons','', '| Model | Features | Test ROC AUC | Test AP | Within-group AUC | F1 |','|---|---|---:|---:|---:|---:|']
for r in report['models']:
    m=r['test'];lines.append(f"| {r['model']} | {r['features']} | {m['roc_auc']:.3f} | {m['average_precision']:.3f} | {m['within_group_auc']:.3f} | {m['f1']:.3f} |")
lines+=['','Chance ROC AUC and within-group AUC: 0.500. Chance AP: 0.167 for the fixed 1:5 design. Threshold is fixed at 0.5. Balanced classifiers are not calibrated population-risk estimators. Full precision/recall, balanced accuracy, confusion matrices, Brier scores, validation scores and cluster-bootstrap intervals are in `reports/experiment/metrics.json`.','',
        '![Model comparison](reports/experiment/model_comparison.png)','', '## Temporal signal','']
for name in names:
    a=next(r for r in report['models'] if r['model']==name and r['features']=='static')['test']
    b=next(r for r in report['models'] if r['model']==name and r['features']=='combined')['test']
    lines.append(f"- {name}: combined minus static AP {b['average_precision']-a['average_precision']:+.3f}; within-group AUC {b['within_group_auc']-a['within_group_auc']:+.3f}.")
lines+=['','These are descriptive differences on one frozen split, not evidence of statistically established precursor detection. No model was selected or tuned using these test results. Temporal-only performance and within-group ranking are necessary checks: pooled AUC can benefit from between-event differences that do not distinguish local slopes.','',
        '## Geographic holdout','',f"Held-out state: {report['geographic_holdout']['held_out_state']}; training events after dependence/border purging: {report['geographic_holdout']['train_events']}; test events: {report['geographic_holdout']['test_events']}.",'']
if report['geographic_holdout']['models']:
    lines+=['| Model | Features | Geographic AP | Geographic within-group AUC |','|---|---|---:|---:|']
    for r in report['geographic_holdout']['models']:
        lines.append(f"| {r['model']} | {r['features']} | {r['test']['average_precision']:.3f} | {r['test']['within_group_auc']:.3f} |")
else: lines.append(report['geographic_holdout']['limitation'])
lines+=['','This is one state-level stress test, not proof of generalization across Austria.','', '## Matching and uncertainty','']
for column,v in report['matching'].items(): lines.append(f"- {column}: median {v['median']:.2f}; 95th percentile {v['p95']:.2f}; maximum {v['max']:.2f}.")
u=report['position_sensitivity']
lines += ['',f"Position diagnostic: 32 offsets within the source-category radius yield a median slope range of {u['median_slope_range_deg']:.1f}°. In {u['events_with_slope_change_above_matching_caliper']} events a sampled offset changes slope by more than the 5° matching caliper. This is a deterministic sensitivity diagnostic, not a surveyed error model. Matching quality is conditional on the reported point.",'',
          '![Matching quality](reports/experiment/matching_quality.png)','',
          '## Provenance and deliverable boundary','',
          '© GeoSphere Austria. Detailed event source: Naturgefahren Test; specific reuse license not identified; QUAL_LAGE/QUAL_PROZ/QUAL_MB and timing interpretations not officially confirmed. Local non-commercial research was authorized by the user. Raw source snapshots and record-level tables are local and ignored; only aggregate results and a small derived demonstration are deliverables. See DATA_SOURCES.md, METHODOLOGY.md and LIMITATIONS.md.']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('REPORT',len(uncertainty),'events',dict(reasons),u,flush=True)
