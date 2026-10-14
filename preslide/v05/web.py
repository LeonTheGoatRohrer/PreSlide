"""data/v05/web/results.json for the local German web demo (aggregates + per-event view, local only).

python -m preslide.v05.web
Examples are chosen from event IDs only (first event per state in the registered pilot order), never by score.
"""
import numpy as np
import pandas as pd

from ..common import read_json, write_json
from .paths import V05_DATA, V05_REPORT, guard
from . import controls as K
from . import metrics as R
from . import pipeline as P

FIELDS = ['elevation', 'slope', 'land_cover_class', 'geology_class', 'distance_to_positive_m', 'rain_sum_7d', 'rain_sum_30d',
          'temperature_mean_7d']


def clean(v):
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else round(float(v), 3)
    if isinstance(v, (np.integer,)):
        return int(v)
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else v


def main():
    r = read_json(V05_REPORT / 'cv_results.json')
    fr = read_json(V05_REPORT / 'COHORT_FREEZE.json')
    data = P.load(P.run_dir() / 'dataset.parquet')
    oof = pd.read_parquet(V05_DATA / 'analysis/oof_purged.parquet')
    oof = oof[(oof.repetition == 1) & (oof.model == 'conditional_logit')]
    score = oof.pivot_table(index='sample_id', columns='variant', values='score')
    ranks = {v: R.group_ranks(oof[oof.variant == v], oof[oof.variant == v].score, 10).set_index('event_group_id') for v in ('static', 'combined')}
    pos = data[data.label == 1].set_index('event_group_id')
    overview = [{'id': g, 'longitude': round(p.longitude, 5), 'latitude': round(p.latitude, 5), 'date': p.event_day, 'state': p.state,
                 'rank_combined': float(ranks['combined'].loc[g, 'mean_rank']), 'auc_combined': float(ranks['combined'].loc[g, 'local_auc'])}
                for g, p in pos.iterrows()]
    order = [e for e in K.pilot_order(pos.index.tolist())]
    picked, states = [], set()
    for e in order:
        if pos.loc[e, 'state'] not in states:
            states.add(pos.loc[e, 'state'])
            picked.append(e)
    examples = []
    for e in picked:
        g = data[data.event_group_id == e].copy()
        g['score_combined'] = g.sample_id.map(score['combined'])
        g['score_static'] = g.sample_id.map(score['static'])
        g['rank_combined'] = g.score_combined.rank(ascending=False, method='average')
        samples = [{'name': 'Ereignishang' if s.label == 1 else f'Kontrolle {int(s.draw_order)}', 'positive': bool(s.label == 1),
                    'longitude': round(s.longitude, 6), 'latitude': round(s.latitude, 6),
                    **{f: clean(s[f]) for f in FIELDS}, 'score_combined': clean(s.score_combined),
                    'rank_combined': clean(s.rank_combined)} for s in g.sort_values('draw_order').itertuples(index=False)
                   for s in [pd.Series(s._asdict())]]
        examples.append({'id': e, 'date': pos.loc[e, 'event_day'], 'state': pos.loc[e, 'state'],
                         'time_quality': pos.loc[e, 'time_quality'], 'samples': samples,
                         'rank_combined': float(ranks['combined'].loc[e, 'mean_rank']),
                         'rank_static': float(ranks['static'].loc[e, 'mean_rank'])})
    web = {'version': 'V0.5', 'generated_from': ['reports/v05/cv_results.json', 'reports/v05/COHORT_FREEZE.json'],
           'cohort': fr['cohort'], 'cv_feasible': fr['cv_feasible'], 'primary': r['primary'], 'chance': r['chance'],
           'purged': {k: v['median'] | {'min_local_auc_units': v['min']['local_auc_units'], 'max_local_auc_units': v['max']['local_auc_units']}
                      for k, v in r['purged'].items()},
           'unpurged': {k: v['median']['local_auc_units'] for k, v in r['unpurged_sensitivity'].items()},
           'slope_rule': r['slope_rule'], 'control_variants': r['control_variants'],
           'land_cover_ablation': r['land_cover_ablation_rep1'], 'stanz': {k: r['stanz_conditional_logit_rep1'][k] for k in ('unit', 'events')} |
           {'combined_all': r['stanz_conditional_logit_rep1']['combined']['all']['local_auc_units'],
            'combined_without': r['stanz_conditional_logit_rep1']['combined']['without_stanz']['local_auc_units']},
           'distributions': r['distributions'], 'coefficients': dict(list(r['conditional_logit_coefficients_all_data']['combined'].items())[:10]),
           'overview': overview, 'examples': examples}
    write_json(guard(V05_DATA / 'web') / 'results.json', web)
    print(f'data/v05/web/results.json: {len(overview)} events, {len(examples)} examples ({", ".join(states)})')


if __name__ == '__main__':
    main()
