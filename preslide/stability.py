"""Frozen development-only repeated grouped experiment with validated checkpoints.

Run: python -m preslide.stability --pilot / --primary / --diagnostics.
Original experiment files are read only. Record-level outputs remain local.
"""
import argparse
import hashlib
import inspect
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits
from sklearn.metrics import average_precision_score

from .common import read_json, write_json, digest
from .sources import ROOT
from .pipeline import STATIC, validate_dataset
from .weather import TEMPORAL
from .evaluation import FEATURE_SETS, make_model, metrics

CONFIG = ROOT / 'config/stability_v02.json'
LOCAL = ROOT / 'data/analysis/stability_v02'
REPORT = ROOT / 'reports/stability_v02'
KEYS = ['sample_id', 'event_group_id', 'dependence_cluster', 'label']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def development(data):
    """Keep frozen cluster membership, including links through excluded records."""
    if not set(data.partition).issubset({'train', 'validation', 'test'}):
        raise ValueError('Unknown original partition')
    for col in ['event_group_id', 'dependence_cluster']:
        if data.groupby(col).partition.nunique().max() != 1:
            raise ValueError('Original group crosses partitions')
    dev = data[data.partition.isin(['train', 'validation'])].copy().reset_index(drop=True)
    test = data[data.partition == 'test']
    for col in ['sample_id', 'event_group_id', 'dependence_cluster']:
        if set(dev[col]) & set(test[col]):
            raise ValueError('Original test overlap: ' + col)
    if not set(dev.label.unique()) == {0, 1}:
        raise ValueError('Nonbinary labels')
    for _, g in dev.groupby('event_group_id'):
        if len(g) != 6 or g.label.sum() != 1 or g.event_date.nunique() != 1:
            raise ValueError('Invalid development event')
    return dev


def split_table(dev, config):
    groups = np.array(sorted(dev.dependence_cluster.unique()))
    rows = []
    for rep, seed in enumerate(config['seeds'], 1):
        for fold, held in enumerate(np.array_split(np.random.default_rng(seed).permutation(groups), config['folds']), 1):
            part = dev.loc[dev.dependence_cluster.isin(held), KEYS].copy()
            part['repetition'], part['seed'], part['fold'] = rep, seed, fold
            rows.append(part)
    return pd.concat(rows, ignore_index=True)


def assert_split(train, held):
    for key in ['sample_id', 'event_group_id', 'dependence_cluster']:
        if set(train[key]) & set(held[key]):
            raise ValueError('Training/evaluation overlap: ' + key)
    if 'test' in set(train.partition) | set(held.partition):
        raise ValueError('Original test used')


def prepare():
    config = read_json(CONFIG)
    directory = ROOT / 'data/processed' / config['dataset_identity']
    original = pd.read_parquet(directory / 'evaluation_dataset.parquet')
    dev = development(original)
    if (len(dev), dev.event_group_id.nunique(), dev.dependence_cluster.nunique()) != (270, 45, 16):
        raise ValueError('Unexpected development cohort')
    validate_dataset(dev, read_json(directory / 'inputs.json')['config'])
    # Preserve original dataset, matching, predictions, reports, models and algorithm.
    protected = list(directory.rglob('*')) + list((ROOT/'models'/config['dataset_identity']).glob('*'))
    protected += list((ROOT/'reports/experiment').glob('*'))
    protected += [ROOT/'data/processed/latest.json', ROOT/'config/experiment.json',
                  ROOT/'preslide/evaluation.py', ROOT/'preslide/pipeline.py', ROOT/'preslide/weather.py',
                  ROOT/'preslide/matching.py']
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(protected) if p.is_file()}
    LOCAL.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    frozen_path = LOCAL / 'original_manifest.json'
    if frozen_path.exists():
        if read_json(frozen_path)['sha256'] != hashes:
            raise ValueError('Protected original artifact changed')
    else:
        write_json(frozen_path, {'sha256': hashes, 'original_partitions': original[KEYS+['partition']].to_dict('records'),
                                'features': FEATURE_SETS, 'python': platform.python_version(), 'sklearn': sklearn.__version__,
                                'models': {n: str(make_model(n).get_params()) for n in config['models']}})
    # Check pre-existing per-event checkpoint hashes, not just our new snapshot.
    for meta in (directory/'events').glob('*/complete.json'):
        for name, value in read_json(meta)['sha256'].items():
            if sha(meta.parent/name) != value:
                raise ValueError('Original event checksum mismatch')
    old = read_json(ROOT/'reports/experiment/metrics.json')
    if old['dataset_hash'] != digest(original[STATIC+TEMPORAL+['sample_id']].to_dict('records')):
        raise ValueError('Original dataset feature checksum mismatch')
    write_json(LOCAL/'protocol.json', config) if not (LOCAL/'protocol.json').exists() else None
    if read_json(LOCAL/'protocol.json') != config:
        raise ValueError('Frozen protocol changed; new experiment version required')
    splits = split_table(dev, config)
    split_path = LOCAL/'splits.parquet'
    if split_path.exists():
        pd.testing.assert_frame_equal(pd.read_parquet(split_path), splits)
    else:
        splits.to_parquet(split_path, index=False)
    return dev, splits, config, directory


def event_scores(frame, probabilities):
    frame = frame[KEYS].copy()
    frame['score'] = np.asarray(probabilities)
    rows = []
    for event, g in frame.groupby('event_group_id'):
        if len(g) != 6 or g.label.sum() != 1:
            raise ValueError('Pairwise metrics require one positive and five controls')
        pos = g.loc[g.label == 1, 'score'].iloc[0]
        neg = g.loc[g.label == 0, 'score'].to_numpy()
        wins, ties, losses = int((pos > neg).sum()), int((pos == neg).sum()), int((pos < neg).sum())
        rows.append({'event_group_id': event, 'dependence_cluster': g.dependence_cluster.iloc[0],
                     'controls_beaten': wins, 'controls_tied': ties, 'positive_rank': 1 + losses + .5*ties,
                     'pairwise_auc': (wins+.5*ties)/5, 'top1_fractional': 1/(ties+1) if losses == 0 else 0,
                     'positive_score': pos})
    return pd.DataFrame(rows)


def score(frame, p):
    result = metrics(frame, np.asarray(p))
    result.update(event_scores(frame, p)[['controls_beaten', 'positive_rank']].mean().to_dict())
    return result


def matrix(frame, columns):
    result = frame[STATIC+TEMPORAL].copy()
    for name in columns:
        if '__x__' in name:
            a, b = name.split('__x__')
            result[name] = result[a]*result[b]
    return result[columns]


def fit_checkpoint(train, held, name, columns, run_key, context):
    assert_split(train, held)
    directory = LOCAL/'fits'/run_key/name
    directory.mkdir(parents=True, exist_ok=True)
    spec = {'train_ids': train.sample_id.tolist(), 'evaluation_ids': held.sample_id.tolist(),
            'train_events': sorted(train.event_group_id.unique()), 'train_clusters': sorted(train.dependence_cluster.unique()),
            'held_clusters': sorted(held.dependence_cluster.unique()), 'columns': columns, 'model': name,
            'context': context, 'protocol_hash': sha(CONFIG), 'original_manifest_hash': sha(LOCAL/'original_manifest.json'),
            'model_code': inspect.getsource(make_model), 'matrix_code': inspect.getsource(matrix),
            'sklearn': sklearn.__version__}
    manifest = directory/'complete.json'
    if manifest.exists():
        meta = read_json(manifest)
        if meta['spec'] != spec:
            raise ValueError('Checkpoint configuration mismatch: '+run_key)
        for f, checksum in meta['sha256'].items():
            if sha(directory/f) != checksum:
                raise ValueError('Checkpoint integrity failure')
        return pd.read_parquet(directory/'predictions.parquet'), directory
    model = make_model(name)
    xtrain, xtest = matrix(train, columns), matrix(held, columns)
    with threadpool_limits(limits=2):
        model.fit(xtrain, train.label)
        if list(model.classes_) != [0, 1]:
            raise ValueError('Unexpected class orientation')
        p = model.predict_proba(xtest)[:, 1]
    if name == 'logistic_regression':
        np.testing.assert_allclose(model.steps[0][1].mean_, xtrain.mean(axis=0), rtol=1e-12, atol=1e-10)
    if not np.isfinite(p).all() or not ((p >= 0) & (p <= 1)).all():
        raise ValueError('Invalid probabilities')
    predictions = held[KEYS].copy()
    predictions['probability'] = p
    for key, value in context.items():
        predictions[key] = value
    predictions['model'] = name
    predictions.to_parquet(directory/'predictions.parquet', index=False)
    joblib.dump({'model': model, 'columns': columns}, directory/'model.joblib')
    write_json(directory/'metrics.json', score(held, p))
    write_json(manifest, {'spec': spec, 'sha256': {f: sha(directory/f) for f in ['predictions.parquet', 'model.joblib', 'metrics.json']}})
    return predictions, directory


def folds(dev, splits):
    for (rep, seed, fold), ids in splits.groupby(['repetition', 'seed', 'fold'], sort=True):
        held = dev[dev.sample_id.isin(ids.sample_id)].copy()
        train = dev[~dev.sample_id.isin(ids.sample_id)].copy()
        assert_split(train, held)
        yield int(rep), int(seed), int(fold), train, held


def primary(dev, splits, config, pilot=False):
    records = []
    for rep, seed, fold, train, held in folds(dev, splits):
        for name in config['models']:
            for feature_set, columns in FEATURE_SETS.items():
                context = {'repetition': rep, 'seed': seed, 'fold': fold, 'features': feature_set}
                pred, _ = fit_checkpoint(train, held, name, columns, f'primary/r{rep}_f{fold}/{feature_set}', context)
                records.append(pred)
        print(f'PRIMARY repetition {rep}/5 fold {fold}/4 verified; {len(train)} train, {len(held)} evaluation', flush=True)
        if pilot:
            write_json(LOCAL/'pilot_verified.json', {'repetition': rep, 'fold': fold, 'fits': 9,
                       'group_separation': True, 'training_only_scaling': True, 'finite_predictions': True})
            return
    pred = pd.concat(records, ignore_index=True)
    if len(pred) != len(dev)*5*9 or pred.groupby(['repetition','model','features']).sample_id.nunique().ne(len(dev)).any():
        raise ValueError('Incomplete primary OOF coverage')
    pred.to_parquet(LOCAL/'primary_predictions.parquet', index=False)
    write_json(LOCAL/'primary_complete.json', {'fits': 180, 'prediction_rows': len(pred), 'sha256': sha(LOCAL/'primary_predictions.parquet')})


def diagnostics(dev, splits, config):
    pred = pd.read_parquet(LOCAL/'primary_predictions.parquet')
    # Model choice is solely development OOF performance and is documented as selection-biased.
    tree_scores = {}
    for name in ['random_forest', 'gradient_boosting']:
        tree_scores[name] = float(np.median([average_precision_score(g.label, g.probability)
                                  for _,g in pred[(pred.model==name)&(pred.features=='combined')].groupby('repetition')]))
    selected = max(tree_scores, key=tree_scores.get)
    write_json(LOCAL/'learning_tree_selection.json', {'selected': selected, 'development_median_AP': tree_scores,
                'limitation': 'Selection and learning curves reuse development outcomes; exploratory, not independent validation.'})
    records = []
    for rep, seed, fold, train, held in folds(dev, splits):
        context = {'repetition': rep, 'seed': seed, 'fold': fold}
        for window, days in config['weather_windows'].items():
            if window == 'full':
                continue  # Exact primary predictions reused by reporting.
            weather = [c for c in TEMPORAL if int(c.rsplit('_', 1)[1][:-1]) in days]
            for features, columns in [('temporal', weather), ('combined', STATIC+weather)]:
                p,_ = fit_checkpoint(train, held, 'logistic_regression', columns,
                         f'ablation/r{rep}_f{fold}/{window}_{features}',
                         {**context, 'features': features, 'analysis': 'ablation', 'window': window})
                records.append(p)
        columns = STATIC+TEMPORAL+['__x__'.join(pair) for pair in config['interactions']]
        p,_ = fit_checkpoint(train, held, 'logistic_regression', columns, f'interactions/r{rep}_f{fold}',
                    {**context, 'features': 'combined_interactions', 'analysis': 'interactions'})
        records.append(p)
        # Nested groups within each unchanged outer-training set, all holdouts identical.
        order = np.random.default_rng(seed*100+fold).permutation(sorted(train.dependence_cluster.unique()))
        for fraction in config['learning_fractions']:
            if fraction == 1:
                continue
            count = max(1, int(np.ceil(len(order)*fraction)))
            subset = train[train.dependence_cluster.isin(order[:count])]
            for name in ['logistic_regression', selected]:
                p,_ = fit_checkpoint(subset, held, name, FEATURE_SETS['combined'],
                        f'learning/r{rep}_f{fold}/fraction_{fraction}',
                        {**context, 'features': 'combined', 'analysis': 'learning', 'fraction': fraction,
                         'training_clusters': count, 'training_events': int(subset.event_group_id.nunique())})
                records.append(p)
        print(f'DIAGNOSTICS repetition {rep}/5 fold {fold}/4 verified', flush=True)
    pd.concat(records, ignore_index=True).to_parquet(LOCAL/'diagnostic_predictions.parquet', index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--primary', action='store_true')
    parser.add_argument('--diagnostics', action='store_true')
    args = parser.parse_args()
    dev, splits, config, _ = prepare()
    if args.pilot:
        primary(dev, splits, config, pilot=True)
    elif args.primary:
        if not (LOCAL/'pilot_verified.json').exists():
            raise RuntimeError('Run and inspect --pilot first')
        primary(dev, splits, config)
    elif args.diagnostics:
        diagnostics(dev, splits, config)
    else:
        print('Frozen development data and original artifact checksums verified.')


if __name__ == '__main__':
    main()
