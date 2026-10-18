"""susceptibility_v02 pre-registered sensitivity 'sensitivity_gorkha_20km' (exploratory: Gorkha is seen data).

  python -I scripts/run_susceptibility_v02.py sensitivity --pilot   (50 resamples, nothing written)
  python -I scripts/run_susceptibility_v02.py sensitivity           (write-once predictions + report)

Spatial block CV inside gorkha_2015 with 5 km and 20 km blocks on the same v01 samples and the same code, so the
comparison is paired. Models and hyperparameters as registered (v01 Amendment 3); reuses the v01 evaluation helpers.
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ..common import read_json, write_json
from ..v04.pipeline import load, save
from .evaluate import block_folds, block_weights, bootstrap_aucs, interval, make, purge
from .v02 import DATA, REPORT, ROOT, config, guard
from .v02_phase1 import v01_samples

DATASET = 'gorkha_2015'
PGA = 'log10_pga_pctg'
# Values of the registered design text (config 'sensitivity_gorkha_20km'); a test checks they still appear there.
DESIGN = {'block_sizes_m': (5000, 20000), 'folds': 5, 'purge_m': 1000, 'n_resamples': 2000, 'min_blocks_with_positives': 25}
PAIRS = (('EQ_TERRAIN', 'slope_only'), ('EQ_TERRAIN_PGA', 'slope_pga_logistic'))
OUT = DATA / 'predictions' / 'sensitivity_gorkha_oof.parquet'


def model_table(cfg):
    """Registered models of the sensitivity: name -> (model family, feature columns)."""
    terrain = list(cfg['features_terrain'])
    return {'EQ_TERRAIN': ('hist_gradient_boosting', terrain),
            'EQ_TERRAIN_PGA': ('hist_gradient_boosting', terrain + [PGA]),
            'slope_only': ('logistic_regression', ['slope_deg']),
            'slope_pga_logistic': ('logistic_regression', ['slope_deg', PGA])}


def model_spec(cfg):
    """v02 model_spec, checked against v01 Amendment 3 (registered as unchanged), in the form evaluate.make expects."""
    spec = cfg['model_spec']
    v01 = read_json(ROOT / 'reports/susceptibility_v01/AMENDMENT_3.json')['add']['model_spec']['value']
    if spec['hist_gradient_boosting'] != v01['hist_gradient_boosting'] or any(
            spec['logistic_regression'][k] != v01['logistic_regression'][k] for k in v01['logistic_regression']):
        raise RuntimeError('v02 hyperparameters differ from susceptibility_v01 Amendment 3')
    return {'hist_gradient_boosting': spec['hist_gradient_boosting'], 'logistic_regression': dict(v01['logistic_regression'])}


def block_ids(x, y, size_m, dataset=DATASET):
    """Square blocks on the working CRS grid (same formula as v01 sampling)."""
    return np.array([f'{dataset}:{int(math.floor(a / size_m))}:{int(math.floor(b / size_m))}' for a, b in zip(x, y)])


def cross_validate(d, blocks, cfg, models, spec, folds_k, purge_m):
    """Out-of-fold scores; whole blocks per fold, training samples closer than purge_m to any test sample removed."""
    seed = cfg['seeds']['folds']
    folds = block_folds(blocks, folds_k, seed)
    oof = {k: np.full(len(d), np.nan) for k in models}
    purged = []
    for f in range(folds_k):
        test = d[folds == f]
        train = purge(d[folds != f], test, purge_m)
        purged.append(int((folds != f).sum() - len(train)))
        for name, (family, cols) in models.items():
            m = make(family, spec, seed)
            m.fit(train[cols], train['label'])
            oof[name][test.index] = m.predict_proba(test[cols])[:, 1]
    return folds, oof, purged


def interpretation(d5, d20_point, d20_interval, dpga5):
    """Pre-registered interpretation rule of the sensitivity (config 'interpretation_fixed_in_advance')."""
    proximity = bool(d20_point < 0.5 * d5 or (d20_interval[0] <= 0 <= d20_interval[1]))
    shaking = bool(dpga5 < 0.5 * d5)
    return {'spatial_proximity_share_large': proximity, 'largely_explained_by_modelled_shaking': shaking,
            'conditions': {'d20_below_half_d5': bool(d20_point < 0.5 * d5),
                           'd20_interval_includes_0': bool(d20_interval[0] <= 0 <= d20_interval[1]),
                           'pga_difference_5km_below_half_terrain_difference_5km': shaking}}


def run_block_size(d, size_m, cfg, models, spec, n_boot, k):
    blocks = block_ids(d.x, d.y, size_m)
    folds, oof, purged = cross_validate(d, blocks, cfg, models, spec, DESIGN['folds'], DESIGN['purge_m'])
    y = d.label.to_numpy()
    w = block_weights(blocks, n_boot, np.random.default_rng([cfg['seeds']['bootstrap'], k]))
    boot = bootstrap_aucs(y, oof, w)
    auc = {m: float(roc_auc_score(y, s)) for m, s in oof.items()}
    pos_blocks = pd.Series(blocks[y == 1]).value_counts()
    res = {'block_size_m': size_m, 'folds': DESIGN['folds'], 'purge_m': DESIGN['purge_m'],
           'blocks_with_samples': int(len(set(blocks))), 'blocks_with_positives': int(len(pos_blocks)),
           'interval_stable': bool(len(pos_blocks) >= DESIGN['min_blocks_with_positives']),
           'samples_per_fold': [int((folds == f).sum()) for f in range(DESIGN['folds'])],
           'positives_per_fold': [int(y[folds == f].sum()) for f in range(DESIGN['folds'])],
           'purged_training_samples_per_fold': purged,
           'auc': {m: {'point': auc[m], 'interval_95': interval(boot[m])} for m in models},
           'differences': {f'{a} - {b}': {'point': auc[a] - auc[b], 'interval_95': interval(boot[a] - boot[b])}
                           for a, b in PAIRS},
           'largest_block_positive_share': float(pos_blocks.iloc[0] / pos_blocks.sum())}
    if res['largest_block_positive_share'] > 0.2:
        keep = blocks != pos_blocks.index[0]
        res['without_largest_block'] = {m: float(roc_auc_score(y[keep], s[keep])) for m, s in oof.items()}
    return res, blocks, folds, oof


def run(pilot=False):
    cfg = config()
    if not pilot and OUT.exists():
        raise RuntimeError(f'{OUT} exists; the sensitivity is computed once (write-once)')
    reg = cfg['sensitivity_gorkha_20km']
    frame, side = v01_samples(DATASET)
    pga = load(DATA / 'features' / f'{DATASET}_pga.parquet')
    if pga is None:
        raise RuntimeError('PGA features missing (run the pga stage first)')
    d = frame.merge(pga[['sample_id', PGA]], on='sample_id', how='left', validate='one_to_one')
    if len(d) != len(frame) or not (d.sample_id.to_numpy() == frame.sample_id.to_numpy()).all():
        raise RuntimeError('PGA join changed the sample table')
    if not (block_ids(d.x, d.y, DESIGN['block_sizes_m'][0]) == d.block_id.to_numpy()).all():
        raise RuntimeError('recomputed 5 km blocks differ from the v01 block ids')
    models, spec = model_table(cfg), model_spec(cfg)
    n_boot = 50 if pilot else DESIGN['n_resamples']
    per, preds = {}, d[['sample_id', 'label', 'x', 'y']].copy()
    oofs, blocks_by = {}, {}
    for k, size in enumerate(DESIGN['block_sizes_m']):
        res, blocks, folds, oof = run_block_size(d, size, cfg, models, spec, n_boot, k)
        key = f'{size // 1000}km'
        per[key], oofs[key], blocks_by[key] = res, oof, blocks
        preds[f'block_{key}'], preds[f'fold_{key}'] = blocks, folds
        for m, s in oof.items():
            preds[f'score_{key}_{m}'] = s
    d5 = per['5km']['differences']['EQ_TERRAIN - slope_only']
    d20 = per['20km']['differences']['EQ_TERRAIN - slope_only']
    dpga5 = per['5km']['differences']['EQ_TERRAIN_PGA - slope_pga_logistic']
    rule = interpretation(d5['point'], d20['point'], d20['interval_95'], dpga5['point'])
    # Additional descriptive quantity (not part of the fixed rule): d20 - d5/2 with 20 km blocks resampled for both
    # CVs at once; 5 km blocks nest exactly in 20 km blocks, so this resampling respects both.
    y = d.label.to_numpy()
    w = block_weights(blocks_by['20km'], n_boot, np.random.default_rng([cfg['seeds']['bootstrap'], 2]))
    b5, b20 = bootstrap_aucs(y, oofs['5km'], w), bootstrap_aucs(y, oofs['20km'], w)
    paired = (b20['EQ_TERRAIN'] - b20['slope_only']) - 0.5 * (b5['EQ_TERRAIN'] - b5['slope_only'])
    result = {
        'version': 'susceptibility_v02', 'analysis': 'sensitivity_gorkha_20km',
        'status': 'EXPLORATORY (Gorkha is seen data in susceptibility_v01); pre-registered, not a gate, not confirmatory',
        'pilot': pilot, 'computed_at_utc': datetime.now(timezone.utc).isoformat(),
        'registered_design': reg,
        'inputs': {'samples': f'data/susceptibility_v01/samples/{DATASET}.parquet', 'samples_sha256': side['sha256'],
                   'n_samples': len(d), 'n_positives': int(y.sum()), 'n_background': int((y == 0).sum()),
                   'pga_feature': f'data/susceptibility_v02/features/{DATASET}_pga.parquet',
                   'pga_nan': int(d[PGA].isna().sum()),
                   'shakemap': read_json(DATA / 'raw' / f'shakemap_{DATASET}' / 'provenance.json')['sha256']},
        'models': {m: {'family': f, 'features': c} for m, (f, c) in models.items()},
        'hyperparameters': spec, 'seeds': {'folds': cfg['seeds']['folds'], 'bootstrap': cfg['seeds']['bootstrap']},
        'n_resamples': n_boot, 'per_block_size': per,
        'interpretation_rule': reg['interpretation_fixed_in_advance'],
        'interpretation_inputs': {'d5_EQ_TERRAIN_minus_slope': d5['point'], 'd20_EQ_TERRAIN_minus_slope': d20['point'],
                                  'd20_interval_95': d20['interval_95'],
                                  'd5_EQ_TERRAIN_PGA_minus_slope_pga': dpga5['point'],
                                  'ratio_d20_to_d5': d20['point'] / d5['point'] if d5['point'] else None,
                                  'ratio_pga_to_terrain_5km': dpga5['point'] / d5['point'] if d5['point'] else None},
        'interpretation': rule,
        'additional_descriptive': {
            'quantity': 'd20 - 0.5 * d5 (EQ_TERRAIN - slope_only), 20 km blocks resampled jointly for both CVs; not part of the '
                        'registered rule',
            'point': d20['point'] - 0.5 * d5['point'], 'interval_95': interval(paired)},
        'independent_units': {'5km_blocks_with_samples': per['5km']['blocks_with_samples'],
                              '20km_blocks_with_samples': per['20km']['blocks_with_samples'],
                              'events': 1, 'note': 'one earthquake; blocks are spatial resampling units, not independent events'},
        'counted_comparisons': ['AUC of 4 models x 2 block sizes', 'EQ_TERRAIN - slope_only at 5 km and 20 km',
                                'EQ_TERRAIN_PGA - slope_pga_logistic at 5 km and 20 km',
                                'rule: d20 vs d5/2 and d20 interval vs 0', 'rule: PGA difference vs terrain difference at 5 km',
                                'additional descriptive d20 - d5/2'],
    }
    if not pilot:
        guard(OUT.parent)
        save(preds, OUT, {'analysis': 'sensitivity_gorkha_20km', 'samples_sha256': side['sha256']})
        write_json(guard(REPORT) / 'sensitivity_gorkha_20km.json', result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', action='store_true')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    res = run(a.pilot)
    show = {k: res[k] for k in ('interpretation_inputs', 'interpretation', 'additional_descriptive')}
    show['per_block_size'] = {k: {kk: v[kk] for kk in ('blocks_with_positives', 'interval_stable', 'auc', 'differences')}
                              for k, v in res['per_block_size'].items()}
    print(json.dumps(show, indent=1))


if __name__ == '__main__':
    main()
