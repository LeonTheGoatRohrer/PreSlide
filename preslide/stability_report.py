"""Generate scientific figures and conclusions directly from saved results."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .common import read_json, write_json
from .stability import LOCAL, REPORT, ROOT, sha
from .stability_analysis import table, METRICS

NAMES={'logistic_regression':'Logistische Regression','random_forest':'Random Forest','gradient_boosting':'Gradient Boosting'}
FEATURES={'static':'Gelände','temporal':'Wetter','combined':'Gelände + Wetter'}
COLORS={'static':'#777777','temporal':'#168578','combined':'#003da5'}
LABELS={'average_precision':'Average Precision','roc_auc':'ROC AUC','within_group_auc':'AUC innerhalb Ereignisgruppe'}
FIGURES=['A_performance','B_weather_delta','C_event_ranks','D_learning_curve','E_weather_differences','F_feature_stability','G_storm_sensitivity']


def finish(fig,name,footnote):
    fig.text(.01,.01,footnote,fontsize=8,color='#444444')
    fig.tight_layout(rect=(0,.07,1,.92))
    fig.savefig(REPORT/(name+'.png'),dpi=170,facecolor='white')
    fig.savefig(REPORT/(name+'.svg'),facecolor='white')
    plt.close(fig)


def figures(metrics,deltas,lc,importance):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold',
                         'axes.grid':True,'grid.alpha':.18,'font.family':'DejaVu Sans'})
    fig,axes=plt.subplots(3,3,figsize=(13,10))
    for i,name in enumerate(NAMES):
        for j,metric in enumerate(LABELS):
            ax=axes[i,j]
            for features in FEATURES:
                g=metrics[(metrics.model==name)&(metrics.features==features)].sort_values('repetition')
                ax.plot(g.repetition,g[metric],marker={'static':'o','temporal':'^','combined':'s'}[features],color=COLORS[features],label=FEATURES[features])
            ax.axhline(1/6 if metric=='average_precision' else .5,color='black',linestyle=':',label='Referenz' if i==j==0 else None)
            ax.set_title(NAMES[name]+'\n'+LABELS[metric]);ax.set_xticks(range(1,6));ax.set_xlabel('Wiederholung')
            if i==j==0: ax.legend(fontsize=8)
    fig.suptitle('A · Alle Modelle und Merkmalsvarianten',fontsize=16)
    finish(fig,'A_performance','45 Ereignisse · 16 Abhängigkeitsgruppen · 270 Proben je Wiederholung. Fünf Aufteilungen derselben Daten; keine unabhängigen Replikate.')
    fig,axes=plt.subplots(1,3,figsize=(13,4.5))
    for ax,metric in zip(axes,LABELS):
        for i,name in enumerate(NAMES):
            vals=deltas[deltas.model==name][metric].to_numpy()
            ax.scatter(np.arange(5)*.035+i-.07,vals,s=30,color='#003da5')
            ax.plot([i-.18,i+.18],[np.median(vals)]*2,color='black',lw=2)
        ax.axhline(0,color='black',ls=':');ax.set_xticks(range(3),['LR','RF','Boosting']);ax.set_title('Δ '+LABELS[metric])
    fig.suptitle('B · Gelände + Wetter minus Gelände',fontsize=16)
    finish(fig,'B_weather_delta','Jeder Punkt: eine Wiederholung; Aufteilung je Wiederholung für alle Varianten identisch. Schwarz: Median. Positiv = Verbesserung. 45 Ereignisse / 16 Gruppen.')
    e=pd.read_parquet(LOCAL/'event_results.parquet')
    fig,axes=plt.subplots(3,3,figsize=(13,10))
    for i,name in enumerate(NAMES):
        g=e[e.model==name]
        for features in FEATURES:
            h=g[g.features==features]
            for j,(column,bins) in enumerate([('controls_beaten',np.arange(-.5,6.5,1)),('positive_rank',np.arange(.75,6.5,.5))]):
                counts=[]
                for _,r in h.groupby('repetition'):
                    counts.append(np.histogram(r[column],bins=bins)[0])
                counts=np.array(counts);x=(bins[1:]+bins[:-1])/2
                axes[i,j].plot(x,counts.mean(axis=0),marker={'static':'o','temporal':'^','combined':'s'}[features],markersize=3,color=COLORS[features],label=FEATURES[features])
                axes[i,j].fill_between(x,counts.min(axis=0),counts.max(axis=0),alpha=.10,color=COLORS[features])
        h=g[g.features=='combined'];bins=np.arange(-5.25,5.75,.5)
        counts=np.array([np.histogram(r.weather_rank_delta,bins=bins)[0] for _,r in h.groupby('repetition')])
        axes[i,2].bar((bins[1:]+bins[:-1])/2,counts.mean(axis=0),width=.4,color='#003da5')
        axes[i,2].vlines((bins[1:]+bins[:-1])/2,counts.min(axis=0),counts.max(axis=0),color='#444444',lw=1)
        axes[i,2].axvline(0,color='black',ls=':')
        for j,title in enumerate(['Kontrollen strikt übertroffen','Rang des Ereignishangs','Ranggewinn durch Wetter']):
            axes[i,j].set_title(NAMES[name]+'\n'+title);axes[i,j].set_ylabel('Ereignisse je Wiederholung')
        axes[i,0].set_xticks(range(6));axes[i,1].set_xticks(range(1,7))
    axes[0,0].legend(fontsize=8)
    fig.suptitle('C · Lokaler Vergleich mit fünf Kontrollen',fontsize=16)
    finish(fig,'C_event_ranks','Mittel und Min–Max über fünf Wiederholungen, je 45 Ereignisse. Gleichstände: mittlerer Rang, halber Paarvergleich; „übertroffen“ zählt nur strikte Siege.')
    fig,axes=plt.subplots(1,3,figsize=(13,4.5))
    for ax,metric in zip(axes,LABELS):
        for name,color in [('logistic_regression','#003da5'),('random_forest','#168578'),('gradient_boosting','#168578')]:
            g=lc[lc.model==name]
            if g.empty: continue
            agg=g.groupby('training_clusters_per_fold')[metric].agg(['median','min','max'])
            ax.plot(agg.index,agg['median'],marker='o' if name=='logistic_regression' else 's',color=color,label=NAMES[name]);ax.fill_between(agg.index,agg['min'],agg['max'],alpha=.12,color=color)
        ax.axhline(1/6 if metric=='average_precision' else .5,color='black',ls=':');ax.set_xticks([3,6,9,12]);ax.set_xlabel('Trainingsgruppen je Fold');ax.set_title(LABELS[metric])
    axes[0].legend(fontsize=8);fig.suptitle('D · Gruppierte Lernkurve — explorativ',fontsize=16)
    finish(fig,'D_learning_curve','Median und Spannweite über fünf Wiederholungen. Je Fold dieselben vier Bewertungsgruppen; verschachtelte Trainingsgruppen. Baumwahl aus Entwicklungsdaten.')
    w=pd.read_csv(REPORT/'weather_distinguishability.csv')
    features=list(dict.fromkeys(w.feature))
    fig,ax=plt.subplots(figsize=(11,7))
    ax.boxplot([w[w.feature==f].mean_difference_over_dev_sd for f in features],orientation='horizontal',tick_labels=features,showfliers=True)
    ax.axvline(.01,color='#003da5',ls=':',label='Nähe-Schwelle 0,01');ax.set_xlabel('Mittlere absolute Differenz zu fünf Kontrollen / Entwicklungs-SD');ax.legend()
    fig.suptitle('E · Wetterunterschiede innerhalb der Ereignisgruppen',fontsize=16)
    finish(fig,'E_weather_differences','45 Ereignisse je Merkmal; Box: Median und IQR, Whisker: 1,5×IQR. INCA: 1 km / 1 h. Verschiedene Werte belegen noch kein Vorhersagesignal.')
    fig,axes=plt.subplots(1,3,figsize=(15,9),sharey=True)
    features=list(dict.fromkeys(importance.feature))
    for ax,name in zip(axes,NAMES):
        kind='standardized_coefficient' if name=='logistic_regression' else 'within_event_permutation'
        g=importance[(importance.model==name)&(importance.kind==kind)].set_index('feature').loc[features]
        y=np.arange(len(features));ax.hlines(y,g.minimum,g.maximum,color='#9cabc8');ax.scatter(g['median'],y,color='#003da5',s=24)
        ax.axvline(0,color='black',ls=':');ax.set_yticks(y,features);ax.set_title(NAMES[name]);ax.set_xlabel('Standardisierter Koeffizient' if name=='logistic_regression' else 'AP-Abfall: Permutation innerhalb Ereignis')
    axes[0].invert_yaxis();fig.suptitle('F · Merkmalsstabilität: Median und Spannweite',fontsize=16)
    finish(fig,'F_feature_stability','Alle 22 Merkmale · fünf Wiederholungen · vier Folds je Wiederholung. Permutation je Fold dreimal; keine Konfidenzintervalle und keine Kausalität.')
    storm=pd.read_csv(REPORT/'storm_deltas.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,metric in zip(axes,['average_precision_delta','within_group_auc_delta']):
        for i,name in enumerate(NAMES):
            for shift,method,color in [(-.12,'event_weighted','#777777'),(.12,'dependency_balanced','#003da5')]:
                vals=storm[(storm.model==name)&(storm.method==method)][metric].to_numpy()
                ax.scatter(np.arange(5)*.02+i+shift-.04,vals,color=color,s=30,marker='o' if method=='event_weighted' else 's',label={'event_weighted':'Ereignisse gleich gewichtet','dependency_balanced':'Gruppen gleich gewichtet'}[method] if i==0 else None)
                ax.plot([i+shift-.08,i+shift+.08],[np.median(vals)]*2,color='black',lw=2)
        ax.axhline(0,color='black',ls=':');ax.set_xticks(range(3),['LR','RF','Boosting']);ax.set_title('Δ AP' if metric.startswith('average') else 'Δ AUC innerhalb Ereignis')
    axes[0].legend(fontsize=8);fig.suptitle('G · Gleiches Gewicht je Abhängigkeitsgruppe',fontsize=16)
    finish(fig,'G_storm_sensitivity','45 Ereignisse / 16 Gruppen. Jeder Punkt: eine Wiederholung; Median schwarz. Nur Bewertungsgewichte geändert; Training bleibt unverändert.')


def generate(dev,config):
    metrics=pd.read_csv(REPORT/'stability_metrics.csv');deltas=pd.read_csv(REPORT/'performance_deltas.csv')
    lc=pd.read_csv(REPORT/'learning_curve.csv');importance=pd.read_csv(REPORT/'feature_stability.csv')
    figures(metrics,deltas,lc,importance)
    ds=pd.read_csv(REPORT/'delta_summary.csv');consistency=pd.read_csv(REPORT/'event_consistency.csv')
    weather=read_json(REPORT/'weather_summary.json');storm=pd.read_csv(REPORT/'storm_deltas.csv')
    positions=pd.read_csv(REPORT/'position_offset_summary.csv');corr=pd.read_csv(REPORT/'matching_correlations.csv')
    boot=pd.read_csv(REPORT/'paired_bootstrap.csv')
    def delta(name,metric):return ds[(ds.model==name)&(ds.metric==metric)].iloc[0]
    def fmtrow(row):return f"{row['median']:+.3f} [{row['minimum']:+.3f}, {row['maximum']:+.3f}]; {int(row.improved_repetitions)}/5 verbessert"
    comparisons=[]
    for name in NAMES:
        comparisons.append({'Modell':NAMES[name],'Δ AP: Median [Min, Max]':fmtrow(delta(name,'average_precision')),
                            'Δ lokale AUC: Median [Min, Max]':fmtrow(delta(name,'within_group_auc'))})
    pairedtable=pd.DataFrame(comparisons)
    stable=importance[(importance.kind=='within_event_permutation')&(importance.repetitions_above_005>=4)].sort_values(['model','median'],ascending=[True,False])
    coefficients=importance[(importance.kind=='standardized_coefficient')&(importance.sign_consistency==1)].sort_values('median')
    cluster_sizes=pd.read_csv(REPORT/'storm_cluster_sizes.csv')
    max_cluster=int(cluster_sizes.events.max())
    balanced=storm[storm.method=='dependency_balanced'].groupby('model')[['average_precision_delta','within_group_auc_delta']].median()
    lr_rho=float(corr[(corr.model=='logistic_regression')&(corr.features=='combined')&(corr.matching_measure=='matching_score')&(corr.outcome=='positive_rank')].spearman_rho.iloc[0])
    next_priority='Zusätzliche unabhängige Wetter- und Ereignisepisoden mit verifizierten Ereignispositionen als vorab festgelegten externen Prüfbestand gewinnen.'
    conclusion='Ein robuster zusätzlicher Wetternutzen ist nicht belegt. Baumverfahren verbessern teilweise die lokale Rangfolge, erreichen jedoch keine konsistente Verbesserung der Average Precision; die logistische Regression profitiert lokal nicht.'
    qa=[]
    qa.append(('1. Verbessert Wetter wiederholt die Leistung gegenüber Gelände?',conclusion+'\n\n'+table(pairedtable)))
    rf=delta('random_forest','within_group_auc');lr=delta('logistic_regression','within_group_auc')
    rf_events=consistency[consistency.model=='random_forest'].iloc[0]
    qa.append(('2. Ist ein Nutzen im lokalen Vergleich sichtbar?',f'Beim Random Forest beträgt die mediane lokale AUC-Differenz {rf["median"]:+.3f}, mit Verbesserung in {int(rf.improved_repetitions)}/5 Wiederholungen. {int(rf_events.improved_at_least_three)}/45 Ereignisse gewinnen in mindestens drei Wiederholungen Rangplätze, {int(rf_events.worsened_at_least_three)}/45 verlieren. Bei LR verbessert sich die mittlere lokale AUC in {int(lr.improved_repetitions)}/5 Wiederholungen. Ein einzelner konsistenter Nutzen für alle Ereignisse liegt nicht vor.'))
    rf_absolute=metrics[metrics.model=='random_forest'].groupby('features').within_group_auc.median()
    title,answer=qa[-1]
    qa[-1]=(title,answer+f' Wichtig: Die RF-Baseline Gelände liegt bei einer medianen lokalen AUC von {rf_absolute["static"]:.3f}, das kombinierte Modell bei {rf_absolute["combined"]:.3f}. Der positive Unterschied gegenüber einer schwachen Baseline belegt daher keine verlässliche Leistung oberhalb Zufall. Matching-Asymmetrie ist eine plausible, hier nicht bewiesene Erklärung.')
    qa.append(('3. Ist das Ergebnis über Gruppenaufteilungen stabil?','Nein als allgemeiner Wetternachweis: Modell, Metrik und Aufteilung liefern unterschiedliche Antworten. Die Intervalle der AP-Differenz und der lokalen AUC-Differenz überdecken für alle drei Modelle null. Der RF-ROC-AUC-Bootstrap liegt oberhalb null, ist aber eine explorative Auswertung gemittelter OOF-Scores mit fixierten Modellen; daraus folgt kein allgemeiner oder unabhängiger Validierungsnachweis.\n\n'+table(boot[['model','metric','lower_025','upper_975']])))
    qa.append(('4. Sind die Wetterwerte innerhalb lokaler Gruppen ausreichend verschieden?',f'Es gibt messbare Variation: {weather["same_positive_control_cell_pairs"]}/{weather["total_pairs"]} Positiv-Kontroll-Paare nutzen dieselbe Rasterzelle; {weather["events_all_features_exactly_identical"]}/{weather["events"]} Gruppen sind in allen 18 Merkmalen identisch. {weather["events_nearly_equal_at_least_16_of_18_features"]} Gruppen erfüllen das Nähe-Kriterium für mindestens 16 Merkmale. Das widerlegt eine allgemeine versehentliche Gleichsetzung der Wetterdaten, belegt aber keine ausreichende physikalische Auflösung auf Hangniveau. Ein 1-km-Produkt kann lokale Prozesse glätten.'))
    learning=lc.groupby(['model','fraction'])[['average_precision','within_group_auc']].median().reset_index()
    qa.append(('5. Begrenzt die Datensatzgröße die Leistung?','Die Lernkurven zeigen keinen durchgehend steigenden Verlauf. Mehr Gruppen mit genau derselben Information garantieren daher keine Verbesserung. Mit nur 16 Abhängigkeitsgruppen bleibt die Schätzung unsicher; Stichprobenumfang, Diversität und Informationsgehalt lassen sich hier nicht trennen. Keine Hochrechnung einer zukünftigen AUC.\n\n'+table(learning)))
    qa.append(('6. Dominieren wenige Stürme das Resultat?',f'Die größte Abhängigkeitsgruppe enthält {max_cluster}/45 Ereignisse ({max_cluster/45:.1%}). Das ist eine starke Gewichtskonzentration. Bei gleicher Gruppengewichtung beträgt der mediane RF-Wetternutzen Δ AP {balanced.loc["random_forest","average_precision_delta"]:+.3f} und Δ lokale AUC {balanced.loc["random_forest","within_group_auc_delta"]:+.3f}. Der lokale RF-Nutzen verschwindet damit nicht vollständig; große Cluster allein erklären ihn nicht. Die Sensitivität ändert nur Bewertungsgewichte, nicht ihren Einfluss im Training. Gruppen sind keine meteorologisch bestätigten Sturmidentitäten.'))
    qa.append(('7. Erklärt Matchingqualität einen Teil der scheinbaren Leistung?',f'Für LR korreliert schlechteres Matching mit besserem kombinierten Ereignisrang (Spearman ρ={lr_rho:.3f}, 45 Ereignisse / 16 Cluster). Das ist vereinbar mit ausnutzbaren Geländeunterschieden. Der Zusammenhang ist nicht bei allen Modellen gleich und beweist keinen Mechanismus. Alle Matchingmaße und Varianten wurden berichtet, keine Ereignisse entfernt.'))
    qa.append(('8. Wirkt sich Positionsunsicherheit materiell aus?',f'Geländezuordnung ist empfindlich: {int(positions.events_exceeding_5deg.sum())}/45 Ereignisse überschreiten bei den vorhandenen Positionsverschiebungen die 5°-Matchinggrenze. Die 100-m-Kategorie betrifft {int(positions.loc[positions.source_category_upper_m==100,"events"].iloc[0])} Ereignisse; die präziseste Kategorie nur {int(positions.loc[positions.source_category_upper_m==5,"events"].iloc[0])}. Modellverhalten unterscheidet sich zwischen Kategorien, aber ein kausaler oder zuverlässig quantifizierter Leistungsverlust ist wegen kleiner, konfundierter Gruppen nicht bestimmbar.'))
    featuretext='Merkmale mit innerhalb-Ereignis-Permutationsabfall >0,005 AP in mindestens vier Wiederholungen:\n\n'
    featuretext+=table(stable[['model','feature','median','minimum','maximum','repetitions_above_005']]) if len(stable) else 'Kein Merkmal erfüllt dieses vorab festgelegte deskriptive Kriterium.'
    featuretext+='\n\nLR mit in allen fünf Wiederholungen gleichem Koeffizientenvorzeichen:\n\n'+table(coefficients[['feature','median','minimum','maximum','sign_consistency']])
    featuretext+='\n\nAlle Merkmale stehen in feature_stability.csv. Vorzeichenstabilität bedeutet weder positiven Vorhersagenutzen noch Kausalität. Kumulierte Wetterfenster sind korreliert; schwache Modellleistung begrenzt die Interpretierbarkeit.'
    qa.append(('9. Welche Merkmale sind wiederholt nützlich?',featuretext))
    qa.append(('10. Was ist die stärkste wissenschaftlich tragfähige Aussage?','Im festgelegten österreichischen Entwicklungsbestand liefern die vorhandenen Wettermerkmale modellabhängige Hinweise auf veränderte lokale Rangfolgen. Ein stabiler zusätzlicher Vorhersagenutzen über Gelände hinaus und eine Übertragbarkeit auf unabhängige Ereignisse sind nicht nachgewiesen. Dieser Befund beweist weder die Abwesenheit physikalischer Vorläufersignale noch die Unbrauchbarkeit von Wetterdaten.'))
    text='# PreSlide V0.2 — Stabilität und Signaldiagnose\n\n'
    text+='**'+conclusion+'**\n\n'
    text+='Entwicklungsanalyse, keine neue unabhängige Testbestätigung. 45 Ereignisse, 225 Pseudo-Negative, 270 Proben, 16 unverändert übernommene Abhängigkeitsgruppen. Ursprünglicher Test: 15 Ereignisse / 4 Gruppen, vollständig ausgeschlossen. Steiermark wurde nicht erneut bewertet; der autorisierte Entwicklungsbestand kann Steiermark-Ereignisse enthalten. Keine Auswahlentscheidung verwendet geografische Testergebnisse.\n\n'
    text+='## Protokoll und Integrität\n\nDer V0.1-Plan wurde im Chat „Build PreSlide V0 prototype“ (01a139ac-c4da-7380-b055-32d2cf32a148, Schlussantwort 01a139fb-4aa0-7a63-9e05-4f04fe41bedf) gefunden und vollständig gelesen. Er lag vorher nicht als Projektdatei vor. Seine Vorgaben und die V0.2-Diagnosen stehen vor dem ersten Training eingefroren in config/stability_v02.json. Seeds 11/23/37/51/71; vier Folds; unveränderte Modellparameter und Modellseed 42. Alle 180 Haupttrainings abgeschlossen; Pilot mit neun Varianten geprüft.\n\n'
    text+='Kennzahlen je Wiederholung werden aus allen vier OOF-Vorhersagesätzen berechnet, nicht aus dem Mittel der Fold-APs. Alle Varianten nutzen identische Aufteilungen. Pooled OOF-Werte können zusätzlich durch unterschiedliche Score-Skalierung zwischen Folds beeinflusst sein; lokale Vergleiche nutzen stets dasselbe Modell. Schwelle 0,5 unverändert. Gleichstände: 0,5 Paarcredit, mittlerer Rang und anteilige Erstplatzierung. Strikt übertroffene Kontrollen zählen Gleichstände nicht als Sieg. Ranggewinn = Geländerang − kombinierter Rang.\n\n'
    text+='Prüfsummen schützen Originaldatensatz, Matching, Modelle, Testvorhersagen und Berichte. Alle 270 Entwicklungs-Merkmalsvektoren wurden aus lokalen Original-Wetterantworten nachgerechnet; keine Abweichung. Keine Daten neu beschafft, keine Gruppen neu berechnet, keine Kontrollen entfernt. Raw-Cache-, CRS-, Datum-, Label- und Ausschlussprüfungen bestanden. Wissenschaftliche Restunsicherheiten bleiben bestehen.\n\n'
    text+='## Die zehn wissenschaftlichen Fragen\n\n'
    for title,answer in qa:text+='### '+title+'\n\n'+answer+'\n\n'
    text+='## Genau eine nächste Forschungspriorität\n\n**'+next_priority+'**\n\nBegründung: modellabhängiges Signal, nicht monoton steigende Lernkurven und starke Konzentration auf wenige Abhängigkeitsgruppen. Ziel ist zunächst eine belastbarere unabhängige Prüfung; ein höherer Messwert durch zusätzliche Daten wird nicht versprochen. Die bisherigen Entwicklungs- und Testdaten bleiben dafür beobachtete historische Experimente.\n\n'
    text+='## Vollständige Ergebnisse und Zusatzdiagnosen\n\n'
    ablation=pd.read_csv(REPORT/'weather_window_ablation.csv')
    interactions=pd.read_csv(REPORT/'interaction_metrics.csv')
    text+='### Feste Wetterfenster und Interaktionen (explorativ)\n\n'
    text+='Alle Fenster wurden mit logistischer Regression auf denselben Aufteilungen geprüft. immediate = 1/3 Tage, short = 7/14 Tage, antecedent = 30/60 Tage, full = alle Fenster. Die Fenster sind kumulativ und überlappen; die Tabelle erlaubt keine isolierte kausale Zuordnung zu einem Zeitraum. Medianwerte über fünf Wiederholungen:\n\n'
    text+=table(ablation.groupby(['features','window'])[['average_precision','within_group_auc']].median().reset_index())+'\n\n'
    text+='Kein Fenster wird nach diesen Ergebnissen zum neuen Hauptmodell erklärt. Die drei festgelegten Wetter-Gelände-Produkte verändern die LR-Ergebnisse wie folgt:\n\n'
    comparison=pd.concat([metrics[(metrics.model=='logistic_regression')&(metrics.features=='combined')],interactions])
    text+=table(comparison.groupby('features')[['average_precision','within_group_auc']].median().reset_index())+'\n\n'
    text+='Die Interaktionen erhöhen die mediane AP geringfügig, verschlechtern jedoch die lokale Rangfolge. Das ist kein konsistenter Leistungsgewinn und begründet keine zusätzliche Suche nach günstigen Interaktionen. Alle Wiederholungen bleiben in den zugehörigen CSV-Dateien dokumentiert.\n\n'
    text+=table(metrics[['repetition','model','features','average_precision','roc_auc','within_group_auc','positive_rank','top1_fractional']])+'\n\n'
    for file in ['weather_distinguishability.md','exploratory_protocol.md','feature_stability.md','storm_sensitivity.md','matching_diagnostics.md','position_uncertainty.md']:
        text+=f'- [{file}]({file})\n'
    text+='\nAlle vorgegebenen Fenster, Lernanteile, Interaktionen und Merkmale stehen in CSV-Dateien, auch bei ungünstigen Resultaten. Wiederholungen sind keine unabhängigen Studien. Bootstrap: 1.000 gepaarte Clusterziehungen gemittelter OOF-Scores, fixe Modelle, keine vollständige Trainingsunsicherheit. Kein Test der 20 Folds als unabhängige Beobachtungen. Keine Kausalbehauptung.\n\n'
    for name in FIGURES:text+=f'![{name}]({name}.png)\n\n'
    text+='## Reproduktion und Datenzugriff\n\nMit vorhandenen lokalen Snapshots: `python -m preslide.stability --pilot`, `--primary`, `--diagnostics`; danach `python -m preslide.stability_analysis --base`, `--importance --pilot`, `--importance`, `--final`; `python -m preslide.stability_verify`. Gültige Fit- und Importance-Checkpoints werden wiederverwendet. Originaldaten nie mit einem neuen Pipeline-/Evaluation-Aufruf überschreiben.\n\nLokale Vorhersagen/Modelle/Trainings-IDs liegen unter data/analysis/stability_v02. Ereignisweise CSVs im Berichtsordner sind lokale Diagnoseartefakte und ausdrücklich von Paketen ausgeschlossen. Die Web-API stellt ausschließlich freigegebene Aggregatwerte und sieben feste Abbildungen bereit. Kein öffentliches Deployment.\n'
    (REPORT/'summary.md').write_text(text,encoding='utf-8')
    # Small aggregate-only payload. Never source IDs, dates, coordinates or per-event predictions.
    payload={'version':'V0.2','status':'verified_development_analysis','events':45,'controls':225,'samples':270,'clusters':16,
             'repetitions':5,'folds':4,'primary_fits':180,'original_test_excluded':True,
             'conclusion':conclusion,'next_priority':next_priority,
             'models':[{'model':name,**{metric:float(metrics[(metrics.model==name)&(metrics.features=='combined')][metric].median()) for metric in LABELS},
                        'ap_delta':float(delta(name,'average_precision')['median']),
                        'ap_improved_repetitions':int(delta(name,'average_precision').improved_repetitions),
                        'local_auc_delta':float(delta(name,'within_group_auc')['median']),
                        'local_improved_repetitions':int(delta(name,'within_group_auc').improved_repetitions)} for name in NAMES],
             'weather':weather,'figures':FIGURES}
    write_json(REPORT/'public_summary.json',payload)
    # Preserve original prose as a byte-for-byte prefix and a local snapshot; append new version only.
    for filename,section in [('RESULTS.md','\n\n## V0.2 development stability — separate experiment\n\n'+conclusion+'\n\n'+table(pairedtable)+'\n\nAll 180 planned primary fits completed on 45 development events / 16 frozen clusters. Original test and Steiermark results above remain unchanged. See [complete V0.2 report](reports/stability_v02/summary.md).\n'),
                             ('LIMITATIONS.md','\n\n## V0.2 development diagnostics\n\nFive repeated grouped partitions reuse 45 events in only 16 dependency clusters; they are not independent validation. The largest cluster contains '+str(max_cluster)+' events. Weather benefit is model/metric dependent. Learning curves are non-monotonic; more rows with the same information need not improve generalization. The RF learning curve uses development-selected model family. Correlated windows and small position/state subgroups limit interpretation. Cluster-balanced evaluation does not remove large-cluster training influence. Pooled cross-fitted scores may differ in calibration between folds. Exploratory fixed-model bootstrap intervals omit retraining uncertainty. Full diagnostics and the single next research priority are in reports/stability_v02/summary.md.\n')]:
        oldpath=LOCAL/'original_docs'/filename;oldpath.parent.mkdir(parents=True,exist_ok=True)
        if not oldpath.exists():oldpath.write_bytes((ROOT/filename).read_bytes())
        current=(ROOT/filename).read_bytes()
        heading=section.strip().split('\n',1)[0].encode('utf-8')
        start=current.find(heading)
        original=oldpath.read_bytes()
        if start >= 0 and not current.startswith(original):
            # A Windows editor may normalize line endings. Restore original bytes
            # only when the historical prose is otherwise exactly identical.
            normalize=lambda value:value.replace(b'\r\n',b'\n').strip()
            if normalize(current[:start])==normalize(original):
                current=original+b'\n\n'+current[start:]
                start=current.find(heading)
        if start < 0:
            updated=current+section.encode('utf-8')
        else:
            end=current.find(b'\n## ',start+len(heading))
            end=len(current) if end < 0 else end
            updated=current[:start]+section.strip().encode('utf-8')+b'\n\n'+current[end:]
        if not updated.startswith(oldpath.read_bytes()):
            raise ValueError(f'Original documentation prefix changed: {filename}')
        (ROOT/filename).write_bytes(updated)
    print('Generated summary, all seven PNG/SVG scientific figures, aggregate-only UI payload.',flush=True)
