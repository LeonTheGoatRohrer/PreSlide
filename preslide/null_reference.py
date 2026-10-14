"""V0.3 exploratory null reference for the frozen V0.2 development CV (config/null_v03.json).

Within-group label permutation keeps the matched design, the frozen folds and the unchanged models,
so it shows which development metric values this exact pipeline yields without label information.
Run: python -m preslide.null_reference [--draws N] [--jobs J]   (checkpointed per draw; resumable)
"""
import argparse
import json

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score, roc_auc_score
from threadpoolctl import threadpool_limits

from .common import read_json, write_json
from .evaluation import FEATURE_SETS, make_model
from .sources import ROOT
from .stability import development, folds, matrix

CONFIG = ROOT / 'config/null_v03.json'
LOCAL = ROOT / 'data/analysis/null_v03'
REPORT = ROOT / 'reports/null_v03'
STAB = ROOT / 'data/analysis/stability_v02'


def load():
    config = read_json(CONFIG)
    data = pd.read_parquet(ROOT / 'data/processed' / config['dataset_identity'] / 'evaluation_dataset.parquet')
    dev = development(data)
    splits = pd.read_parquet(STAB / 'splits.parquet')
    if set(splits.sample_id) != set(dev.sample_id):
        raise ValueError('Frozen splits do not match development cohort')
    return config, dev, splits


def permuted_labels(dev, draw, seed):
    """Draw 0 = true labels; otherwise one random pseudo-positive per event group."""
    if draw == 0:
        return dev.label.to_numpy()
    rng = np.random.default_rng([seed, draw])
    labels = np.zeros(len(dev), dtype=int)
    for _, idx in dev.groupby('event_group_id', sort=True).indices.items():
        labels[rng.choice(idx)] = 1
    return labels


def within_group(groups, labels, p):
    frame = pd.DataFrame({'g': groups, 'y': labels, 'p': p})
    auc = []
    for _, d in frame.groupby('g', sort=False):
        pos = d.p[d.y == 1].iloc[0]
        neg = d.p[d.y == 0].to_numpy()
        auc.append(np.mean((pos > neg) + 0.5 * (pos == neg)))
    return float(np.mean(auc))


def run_draw(draw, config, dev, splits):
    path = LOCAL / f'draw_{draw:03d}.parquet'
    if path.exists():
        return pd.read_parquet(path)
    work = dev.copy()
    work['label'] = permuted_labels(dev, draw, config['master_seed'])
    if (work.groupby('event_group_id').label.sum() != 1).any():
        raise ValueError('Permutation broke one-positive-per-group')
    rows = []
    with threadpool_limits(limits=1):
        oof = {}
        for rep, _seed, _fold, train, held in folds(work, splits):
            for name in config['models']:
                for fs in config['feature_sets']:
                    model = make_model(name)
                    if name == 'random_forest':
                        model.set_params(n_jobs=1)  # identical trees; parallelism is across draws
                    model.fit(matrix(train, FEATURE_SETS[fs]), train.label)
                    if list(model.classes_) != [0, 1]:
                        raise ValueError('Unexpected class orientation')
                    p = model.predict_proba(matrix(held, FEATURE_SETS[fs]))[:, 1]
                    oof.setdefault((rep, name, fs), []).append(held[['sample_id', 'event_group_id', 'label']].assign(p=p))
    for (rep, name, fs), parts in oof.items():
        d = pd.concat(parts)
        rows.append({'draw': draw, 'repetition': rep, 'model': name, 'features': fs,
                     'within_group_auc': within_group(d.event_group_id.to_numpy(), d.label.to_numpy(), d.p.to_numpy()),
                     'average_precision': average_precision_score(d.label, d.p), 'roc_auc': roc_auc_score(d.label, d.p)})
    result = pd.DataFrame(rows)
    LOCAL.mkdir(parents=True, exist_ok=True)
    result.to_parquet(path, index=False)
    return result


def identity_check(draw0):
    ref = pd.read_csv(ROOT / 'reports/stability_v02/stability_metrics.csv')
    m = draw0.merge(ref, on=['repetition', 'model', 'features'], suffixes=('', '_v02'))
    if len(m) != 45:
        raise ValueError('Identity draw incomplete')
    worst = max(float((m[k] - m[k + '_v02']).abs().max()) for k in ('within_group_auc', 'average_precision', 'roc_auc'))
    if worst > 1e-9:
        raise ValueError(f'Identity draw does not reproduce V0.2 metrics (max diff {worst})')
    return worst


def summarise(all_draws, config):
    metrics = ['within_group_auc', 'average_precision', 'roc_auc']
    med = all_draws.groupby(['draw', 'model', 'features'])[metrics].median().reset_index()
    # Deltas per repetition first, then median over repetitions (as in V0.2 delta_summary)
    wide = all_draws.pivot_table(index=['draw', 'model', 'repetition'], columns='features', values=metrics)
    deltas = []
    for metric in ('within_group_auc', 'average_precision'):
        for other in ('combined', 'temporal'):
            s = (wide[(metric, other)] - wide[(metric, 'static')]).groupby(['draw', 'model']).median().rename('value').reset_index()
            s['statistic'] = f'delta_{other}_minus_static_{metric}'
            deltas.append(s)
    long = pd.concat([med.melt(id_vars=['draw', 'model', 'features'], var_name='metric').assign(
        statistic=lambda x: x.features + '_' + x.metric)[['draw', 'model', 'statistic', 'value']],
        pd.concat(deltas)[['draw', 'model', 'statistic', 'value']]])
    rows = []
    for (model, stat), d in long.groupby(['model', 'statistic']):
        obs = float(d.loc[d.draw == 0, 'value'].iloc[0])
        null = d.loc[d.draw > 0, 'value'].to_numpy()
        rows.append({'model': model, 'statistic': stat, 'observed': obs, 'null_median': float(np.median(null)),
                     'null_p05': float(np.quantile(null, .05)), 'null_p95': float(np.quantile(null, .95)),
                     'p_upper': (1 + int((null >= obs - 1e-12).sum())) / (1 + len(null)),
                     'p_lower': (1 + int((null <= obs + 1e-12).sum())) / (1 + len(null)), 'draws': len(null)})
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draws', type=int, default=None)
    parser.add_argument('--jobs', type=int, default=6)
    args = parser.parse_args()
    config, dev, splits = load()
    n = config['permutations'] if args.draws is None else args.draws
    draw0 = run_draw(0, config, dev, splits)
    print('identity check max diff', identity_check(draw0), flush=True)
    results = Parallel(n_jobs=args.jobs, verbose=5)(delayed(run_draw)(d, config, dev, splits) for d in range(1, n + 1))
    all_draws = pd.concat([draw0] + results, ignore_index=True)
    summary = summarise(all_draws, config)
    REPORT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(REPORT / 'null_summary.csv', index=False)
    write_json(REPORT / 'null_summary.json', {'version': config['version'], 'draws': n, 'identity_reproduces_v02': True,
                                              'rows': json.loads(summary.round(4).to_json(orient='records'))})
    print(summary.round(3).to_string())


if __name__ == '__main__':
    main()
