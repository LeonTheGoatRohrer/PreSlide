"""Generate the aggregate-only web results bundle from machine-readable experiment artifacts.

Nothing is typed in by hand: every number comes from saved predictions/CSVs/JSON. Experiments stay separate:
original frozen test, Steiermark holdout, V0.2 development stability, V0.3 null reference, V0.2 diagnostics.
Per-demo-case rankings use only out-of-training scores (original test model for test cases, V0.2 out-of-fold
scores for development cases). Run: python -m preslide.results_bundle
"""
import numpy as np
import pandas as pd

from .common import read_json, write_json
from .baseline import IDENTITY as BASELINE_IDENTITY
from .sources import ROOT

REPORT_V02 = ROOT / 'reports/stability_v02'
LOCAL_V02 = ROOT / 'data/analysis/stability_v02'
NULL = ROOT / 'reports/null_v03/null_summary.csv'
BUNDLE = ROOT / 'data/web/results.json'
FEATURES = ['static', 'temporal', 'combined']


def spread(values):
    v = np.asarray(values, dtype=float)
    return {'median': float(np.median(v)), 'min': float(v.min()), 'max': float(v.max())}


def ranking(frame, score):
    """Positive vs its five controls; ties count half (same rule as all project metrics)."""
    pos = frame.loc[frame.label == 1, score].iloc[0]
    neg = frame.loc[frame.label == 0, score].to_numpy()
    return {'controls_beaten': int((pos > neg).sum()), 'controls_tied': int((pos == neg).sum()),
            'top1_fractional': float(1/(1+(pos==neg).sum()) if not (neg>pos).any() else 0),
            'rank': 1 + float((neg > pos).sum() + 0.5 * (neg == pos).sum())}


def pairwise_summary(pred, score='p'):
    rows = [ranking(g, score) for _, g in pred.groupby('event_group_id')]
    beaten = np.array([r['controls_beaten'] for r in rows])
    return {'mean_controls_beaten': float(beaten.mean()), 'first_place_rate': float(np.mean([r['top1_fractional'] for r in rows])),
            'beaten_distribution': [int((beaten == k).sum()) for k in range(6)]}


def original(data, metrics):
    test = data[data.partition == 'test']
    preds = pd.read_parquet(ROOT / 'data/processed' / metrics['dataset_identity'] / 'test_predictions.parquet')
    rows = []
    for r in metrics['models']:
        p = preds[(preds.model == r['model']) & (preds.features == r['features'])]
        m = test.merge(p.rename(columns={'probability_case_control': 'p'}), on='sample_id')
        t = r['test']
        rows.append({'model': r['model'], 'features': r['features'], **{k: t[k] for k in
                     ('average_precision', 'roc_auc', 'within_group_auc', 'f1', 'precision', 'recall', 'balanced_accuracy')},
                     **pairwise_summary(m)})
    geo = metrics['geographic_holdout']
    return {'split': metrics['split'], 'chance_average_precision': float(test.label.mean()), 'models': rows,
            'geographic': {'state': geo['held_out_state'], 'train_events': geo['train_events'], 'test_events': geo['test_events'],
                           'purge_m': geo['purge_m'],
                           'models': [{'model': r['model'], 'features': r['features'], **{k: r['test'][k] for k in
                                      ('average_precision', 'roc_auc', 'within_group_auc')}} for r in geo['models']]}}


def stability():
    pp = pd.read_parquet(LOCAL_V02 / 'primary_predictions.parquet')
    per_rep = []
    for (rep, model, fs), d in pp.groupby(['repetition', 'model', 'features']):
        per_rep.append({'repetition': rep, 'model': model, 'features': fs, **pairwise_summary(d, 'probability')})
    per_rep = pd.DataFrame(per_rep)
    metrics = pd.read_csv(REPORT_V02 / 'stability_metrics.csv').merge(per_rep, on=['repetition', 'model', 'features'])
    rows = []
    for (model, fs), d in metrics.groupby(['model', 'features']):
        rows.append({'model': model, 'features': fs, **{k: spread(d[k]) for k in
                     ('average_precision', 'roc_auc', 'within_group_auc', 'mean_controls_beaten', 'first_place_rate')}})
    delta = pd.read_csv(REPORT_V02 / 'delta_summary.csv')
    public = read_json(REPORT_V02 / 'public_summary.json')
    return {'events': public['events'], 'controls': public['controls'], 'clusters': public['clusters'],
            'repetitions': public['repetitions'], 'folds': public['folds'], 'fits': public['primary_fits'],
            'chance_average_precision': 1 / 6, 'conclusion': public['conclusion'], 'models': rows,
            'weather_delta': delta.to_dict('records')}


def null_reference():
    if not NULL.exists():
        return None
    s = pd.read_csv(NULL)
    keep = s[s.statistic.isin([f'{f}_{m}' for f in FEATURES for m in ('within_group_auc', 'average_precision')] +
                              ['delta_combined_minus_static_within_group_auc', 'delta_combined_minus_static_average_precision'])]
    cfg = read_json(ROOT / 'config/null_v03.json')
    conclusion = read_json(ROOT / 'reports/null_v03/null_summary.json').get('conclusion_de')
    return {'draws': int(s.draws.iloc[0]), 'method': cfg['permutation'], 'caveat': cfg['caveat'], 'conclusion': conclusion,
            'rows': keep.to_dict('records')}


def diagnostics():
    lc = pd.read_csv(REPORT_V02 / 'learning_curve.csv')
    ab = pd.read_csv(REPORT_V02 / 'weather_window_ablation.csv')
    st = pd.read_csv(REPORT_V02 / 'storm_sensitivity.csv')
    sizes = pd.read_csv(REPORT_V02 / 'storm_cluster_sizes.csv') if (REPORT_V02 / 'storm_cluster_sizes.csv').exists() else None
    agg = lambda d, keys, cols: [{**dict(zip(keys, k if isinstance(k, tuple) else (k,))), **{c: spread(g[c]) for c in cols}}
                                 for k, g in d.groupby(keys)]
    weather = read_json(REPORT_V02 / 'weather_summary.json')
    return {'learning_curve': agg(lc, ['model', 'fraction'], ['average_precision', 'within_group_auc']),
            'window_ablation': agg(ab, ['features', 'window'], ['average_precision', 'within_group_auc']),
            'storm_sensitivity': agg(st, ['model', 'features', 'method'], ['average_precision', 'within_group_auc']),
            'largest_cluster_events': None if sizes is None else int(sizes.select_dtypes('number').iloc[:, 0].max()),
            'weather_distinguishability': weather}


def case_rankings(data):
    """Map public demo IDs to groups via the positive's coordinates and attach out-of-training rankings."""
    demo = ROOT / 'data/processed' / BASELINE_IDENTITY / 'demo'
    preds = pd.read_parquet(ROOT / 'data/processed' / BASELINE_IDENTITY / 'test_predictions.parquet')
    pp = pd.read_parquet(LOCAL_V02 / 'primary_predictions.parquet')
    oof = pp.groupby(['sample_id', 'model', 'features']).probability.median().reset_index()
    result = {}
    for case in read_json(demo / 'cases.json'):
        detail = read_json(demo / f"{case['id']}.json")
        names = {}
        for s in detail['samples']:
            hit = data[(data.longitude.round(5) == s['longitude']) & (data.latitude.round(5) == s['latitude'])]
            if len(hit) != 1:
                raise ValueError('Demo sample not uniquely matched: ' + case['id'])
            names[hit.sample_id.iloc[0]] = s['name']
        group = data[data.sample_id.isin(names)]
        if group.event_group_id.nunique() != 1 or len(group) != 6:
            raise ValueError('Demo case does not map to one complete group: ' + case['id'])
        partition = group.partition.iloc[0]
        source = preds.rename(columns={'probability_case_control': 'p'}) if partition == 'test' else oof.rename(columns={'probability': 'p'})
        entries = []
        for (model, fs), p in source[source.sample_id.isin(names)].groupby(['model', 'features']):
            g = group.merge(p, on='sample_id')
            order = g.sort_values('p', ascending=False)
            entries.append({'model': model, 'features': fs, **ranking(g, 'p'),
                            'order': [names[s] for s in order.sample_id]})
        result[case['id']] = {'partition': partition,
                              'score_source': 'original_test_model' if partition == 'test' else 'v02_out_of_fold_median_of_5_repetitions',
                              'rankings': entries}
    return result


def event_explorer(data):
    """Per-event error view for all 60 groups: de-identified aliases, no coordinates or source IDs.

    Scores are out-of-training only (original test: frozen V0 model; development: median of the five V0.2
    repetitions). The displayed rank is computed from exactly the displayed scores (ties count half).
    """
    from .baseline import DIAGNOSTICS, SAMPLE_SCORES, SHORT
    diag = pd.read_csv(DIAGNOSTICS).set_index('event_group_id')
    scores = pd.read_csv(SAMPLE_SCORES)
    aliases = read_json(LOCAL_V02 / 'private_event_aliases.json')
    test_events = sorted(diag.index[diag.evaluation == 'original_test'], key=lambda e: (diag.loc[e, 'event_date'], e))
    aliases.update({e: f'TEST-{i:02d}' for i, e in enumerate(test_events, 1)})
    demo_dir = ROOT / 'data/processed' / BASELINE_IDENTITY / 'demo'
    demo = {}
    for case in read_json(demo_dir / 'cases.json'):
        pos = next(x for x in read_json(demo_dir / f"{case['id']}.json")['samples'] if x['positive'])
        hit = data[(data.label == 1) & (data.longitude.round(5) == pos['longitude']) & (data.latitude.round(5) == pos['latitude'])]
        demo[hit.event_group_id.iloc[0]] = case['id']
    clusters = {c: f'G{i:02d}' for i, c in enumerate(data.dependence_cluster.drop_duplicates().sort_values(), 1)}
    events = []
    for event, g in data.groupby('event_group_id'):
        d = diag.loc[event]
        g = g.sort_values('label', ascending=False)
        names = ['Ereignishang'] + [f'Kontrolle {int(s.rsplit("_", 1)[1])}' for s in g.sample_id.iloc[1:]]
        slopes = [{'name': nm, 'positive': bool(r.label), 'slope': round(r.slope, 1), 'elevation': round(r.elevation),
                   'aspect': round(r.aspect), 'distance_km': round(r.distance_to_positive_m / 1000, 2),
                   'rain_7d': round(r.rain_sum_7d, 1), 'rain_30d': round(r.rain_sum_30d, 1), 'rain_max_hour_3d': round(r.rain_max_hour_3d, 1),
                   'temperature_7d': round(r.temperature_mean_7d, 1)} for nm, r in zip(names, g.itertuples())]
        variants = {}
        for model, m in SHORT.items():
            variants[model] = {}
            for feats in FEATURES:
                sc = scores[(scores.event_group_id == event) & (scores.model == model) & (scores.features == feats)].set_index('sample_id')
                variants[model][feats] = {'rank': float(d[f'{m}_{feats}_score_rank']), 'controls_beaten': int(d[f'{m}_{feats}_score_beaten']),
                                          'repetition_rank_min': float(d[f'{m}_{feats}_rank_min']), 'repetition_rank_max': float(d[f'{m}_{feats}_rank_max']),
                                          'scores': [round(float(sc.loc[s, 'score']), 10) for s in g.sample_id]}
        events.append({'alias': aliases[event], 'demo_case': demo.get(event), 'evaluation': 'test' if d.evaluation == 'original_test' else 'development',
                       'event_date': d.event_date, 'state': d.state, 'process_type': d.process_type, 'dependence_group': clusters[d.dependence_cluster],
                       'dependence_group_events': int((data[data.label == 1].dependence_cluster == d.dependence_cluster).sum()),
                       'position_category_m': int(d.source_position_upper_m), 'position_max_slope_change_deg': round(float(d.position_max_slope_change_deg), 1),
                       'matching_score_mean': round(float(d.matching_score_mean), 3), 'control_distance_median_km': round(float(d.control_distance_median_m) / 1000, 2),
                       'weather_std_diff_median': round(float(d.weather_std_diff_median), 3), 'weather_nearly_identical': bool(d.weather_nearly_identical),
                       'slopes': slopes, 'variants': variants})
    events.sort(key=lambda e: (e['evaluation'] != 'test', e['alias']))
    return {'events': events, 'random_rank': 3.5, 'random_controls_beaten': 2.5,
            'score_source': {'test': 'original_frozen_model', 'development': 'v02_out_of_training_median_of_5_repetitions'}}


def build():
    latest = {'identity': BASELINE_IDENTITY}  # pinned: the web demo shows the frozen baseline, not whatever ran last
    data = pd.read_parquet(ROOT / 'data/processed' / latest['identity'] / 'evaluation_dataset.parquet')
    metrics = read_json(ROOT / 'reports/experiment/metrics.json')
    status = read_json(ROOT / 'data/processed' / latest['identity'] / 'status.json')
    status = status['status'] if isinstance(status, dict) else status
    bundle = {'generated_from': 'machine-readable artifacts; see preslide/results_bundle.py',
              'dataset': {'identity': latest['identity'], 'candidates': len(status), 'events': int(data.event_group_id.nunique()),
                          'controls': int((data.label == 0).sum()), 'clusters': int(data.dependence_cluster.nunique()),
                          'retained_hours_60d': int(data.weather_hours_60d.iloc[0])},
              'original_test': original(data, metrics), 'stability_v02': stability(),
              'null_v03': null_reference(), 'diagnostics_v02': diagnostics(), 'cases': case_rankings(data),
              'event_explorer': event_explorer(data)}
    # Outside the run directory: the V0.2 manifest protects every file under data/processed/<identity>/.
    target = BUNDLE
    write_json(target, bundle)
    print('Wrote', target)
    return bundle


if __name__ == '__main__':
    build()
