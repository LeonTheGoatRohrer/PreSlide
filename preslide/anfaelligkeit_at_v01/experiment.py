"""Leave-one-area-out evaluation (config models, evaluation). Units of resampling are evaluation areas.

  python -m preslide.anfaelligkeit_at_v01 experiment --variant srtm|skadi [--areas N]
"""
import json

import joblib
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from ..common import write_json
from .context import GEO, LC, one_hot
from .paths import DATA, MODELS, REPORT, config, guard, load, save
from .pipeline import tag
from .terrain import TERRAIN

FEATURE_SETS = {'slope_only': ['slope'], 'terrain_geology': TERRAIN + GEO, 'terrain_geology_landcover': TERRAIN + GEO + LC}
FORBIDDEN_EXACT = ('x', 'y', 'lon', 'lat', 'longitude', 'latitude')
FORBIDDEN_PARTS = ('area_id', 'project', 'year', 'dist_', 'inventory', 'neighbo', 'count', 'label', 'object', 'sample', 'state')


def check_features(columns) -> None:
    """Registered prohibition: no coordinates, identifiers, years, infrastructure or other-event features."""
    bad = [c for c in columns if c.lower() in FORBIDDEN_EXACT or any(t in c.lower() for t in FORBIDDEN_PARTS)]
    if bad:
        raise ValueError(f'forbidden model features: {bad}')


def assemble(variant: str, areas: int = 0) -> pd.DataFrame:
    t = tag(variant, areas)
    samples = load(DATA / f'samples_{t}.parquet')
    ctx = load(DATA / f'context_{t}.parquet')
    infra = load(DATA / f'infra_{t}.parquet')
    if samples is None or ctx is None or infra is None:
        raise RuntimeError(f'missing checkpoints for {t}')
    data = samples.merge(ctx, on='sample_id', how='left', validate='1:1').merge(infra, on='sample_id', how='left', validate='1:1')
    if len(data) != len(samples) or data.sample_id.duplicated().any():
        raise ValueError('sample join changed the row count')
    data = pd.concat([data, one_hot(data.geology_class, GEO), one_hot(data.land_cover_class, LC)], axis=1)
    return data


# ---------- models ----------

def fit_hgb(X, y, w, params):
    p = dict(params)
    model = HistGradientBoostingClassifier(**p)
    model.fit(X, y, sample_weight=w)
    return model


class LinearModel:
    """Training-median imputation + missing indicators + standardisation + logistic regression (all fit on training)."""

    def __init__(self, params):
        self.params = params

    def fit(self, X, y, w):
        X = np.asarray(X, float)
        self.median = np.nanmedian(X, axis=0)
        self.median = np.where(np.isfinite(self.median), self.median, 0.0)
        self.flag = np.isnan(X).any(axis=0)
        Z = self._design(X, fit=True)
        self.model = LogisticRegression(C=self.params['C'], class_weight=self.params['class_weight'], max_iter=self.params['max_iter'])
        self.model.fit(Z, y, sample_weight=w)
        return self

    def _design(self, X, fit=False):
        miss = np.isnan(X)
        Z = np.where(miss, self.median, X)
        Z = np.column_stack([Z, miss[:, self.flag].astype(float)])
        if fit:
            self.mean, self.sd = Z.mean(axis=0), Z.std(axis=0)
            self.sd = np.where(self.sd > 0, self.sd, 1.0)
        return (Z - self.mean) / self.sd

    def score(self, X):
        return self.model.decision_function(self._design(np.asarray(X, float)))


def area_weights(train: pd.DataFrame) -> np.ndarray:
    n_pos = train[train.label == 1].area_id.value_counts()
    return (1.0 / np.sqrt(train.area_id.map(n_pos).fillna(1).clip(lower=1))).to_numpy()


def purge(train: pd.DataFrame, test: pd.DataFrame, radius_m: float) -> pd.DataFrame:
    """Drop every training sample within radius_m (EPSG:31287 metres) of any held-out sample."""
    d, _ = cKDTree(test[['x', 'y']].to_numpy(float)).query(train[['x', 'y']].to_numpy(float), k=1)
    return train[d > radius_m]


def folds(data: pd.DataFrame, eval_areas, radius_m: float):
    """(area, train, test): the whole held-out area is test; training never contains it or anything within radius_m."""
    for a in eval_areas:
        test = data[data.area_id == a]
        train = purge(data[data.area_id != a], test, radius_m)
        yield a, train, test


def score_models(train, test, cfg, sets=('slope_only', 'terrain_geology')):
    """Fit hgb and lr for each feature set on train, return {(model, set): scores on test, ...} and fitted models."""
    w, y = area_weights(train), train.label.to_numpy()
    out, fitted = {('slope_rule', 'slope_only'): test.slope.to_numpy(float)}, {}
    for s in sets:
        cols = FEATURE_SETS[s]
        check_features(cols)
        hgb = fit_hgb(train[cols].to_numpy(float), y, w, cfg['models']['hist_gradient_boosting'])
        out[('hgb', s)] = hgb.predict_proba(test[cols].to_numpy(float))[:, 1]
        fitted[('hgb', s)] = hgb
        if s != 'slope_only':
            lr = LinearModel(cfg['models']['logistic_regression']).fit(train[cols].to_numpy(float), y, w)
            out[('lr', s)] = lr.score(test[cols].to_numpy(float))
            fitted[('lr', s)] = lr
    return out, fitted


# ---------- metrics ----------

def area_metrics(y: np.ndarray, s: np.ndarray) -> dict:
    pos, bg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(bg) == 0:
        return {'auc': np.nan, 'ap': np.nan, 'capture_top20': np.nan}
    return {'auc': float(roc_auc_score(y, s)), 'ap': float(average_precision_score(y, s)),
            'capture_top20': float(np.mean(pos > np.quantile(bg, 0.8)))}


def per_area(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (a, m, s), g in pred.groupby(['area_id', 'model', 'feature_set']):
        rows.append({'area_id': a, 'model': m, 'feature_set': s, 'n_pos': int(g.label.sum()), 'n_bg': int((g.label == 0).sum()),
                     **area_metrics(g.label.to_numpy(), g.score.to_numpy())})
    return pd.DataFrame(rows)


def bootstrap_mean(values: np.ndarray, draws: int, seed: int) -> dict:
    values = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(len(values), size=(draws, len(values)))
    boot = values[idx].mean(axis=1)
    return {'mean': float(values.mean()), 'ci95': [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            'n_areas': int(len(values))}


def summarise(table: pd.DataFrame, cfg: dict, reference=('hgb', 'slope_only')) -> dict:
    """Area-equal-weighted means with area-bootstrap intervals, and paired differences to the reference model."""
    b = cfg['evaluation']['bootstrap']
    out = {}
    wide = table.pivot_table(index='area_id', columns=['model', 'feature_set'], values=['auc', 'ap', 'capture_top20'])
    ref = wide['auc'][reference]
    for key in wide['auc'].columns:
        name = f'{key[0]}:{key[1]}'
        out[name] = {m: bootstrap_mean(wide[m][key].dropna().to_numpy(), b['draws'], b['seed']) for m in ('auc', 'ap', 'capture_top20')}
        if key != reference:
            diff = (wide['auc'][key] - ref).dropna()
            out[name]['auc_minus_' + ':'.join(reference)] = bootstrap_mean(diff.to_numpy(), b['draws'], b['seed'])
    return out


def verdict(primary: dict) -> dict:
    lo_d, hi_d = primary['diff']['ci95']
    lo_a = primary['auc']['ci95'][0]
    return {'better_than_slope_alone': bool(lo_d > 0), 'above_chance': bool(lo_a > 0.5),
            'statement': ('besser als die Neigung allein' if lo_d > 0 else 'kein belegter Vorteil gegenüber der Neigung allein')}


def permutation_importance(train, test, cfg, seed=20261018, repeats=3) -> dict:
    """AUC drop on the held-out area when a feature group is permuted (primary model, descriptive)."""
    cols = FEATURE_SETS['terrain_geology']
    model = fit_hgb(train[cols].to_numpy(float), train.label.to_numpy(), area_weights(train), cfg['models']['hist_gradient_boosting'])
    X, y = test[cols].to_numpy(float), test.label.to_numpy()
    base = roc_auc_score(y, model.predict_proba(X)[:, 1])
    groups = {c: [c] for c in TERRAIN if c not in ('aspect_sin', 'aspect_cos')}
    groups['aspect'] = ['aspect_sin', 'aspect_cos']
    groups['geology'] = GEO
    rng = np.random.default_rng(seed)
    out = {}
    for g, members in groups.items():
        j = [cols.index(m) for m in members]
        drops = []
        for _ in range(repeats):
            Xp = X.copy()
            Xp[:, j] = X[rng.permutation(len(X))][:, j]
            drops.append(base - roc_auc_score(y, model.predict_proba(Xp)[:, 1]))
        out[g] = float(np.mean(drops))
    return out


# ---------- run ----------

def run(variant: str, areas: int = 0) -> dict:
    cfg = config()
    t = tag(variant, areas)
    data = assemble(variant, areas)
    radius = cfg['evaluation']['spatial_purge_m']
    eval_areas = sorted(data[data.area_status == 'evaluation'].area_id.unique())
    n_pos = data[data.label == 1].area_id.value_counts()
    largest = max(eval_areas, key=lambda a: (n_pos[a], a))
    preds, importance, fold_info = [], {}, {}
    models_dir = guard(MODELS / t)
    for a, train, test in folds(data, eval_areas, radius):
        scores, fitted = score_models(train, test, cfg)
        for (m, s), v in scores.items():
            preds.append(pd.DataFrame({'sample_id': test.sample_id.to_numpy(), 'area_id': a, 'label': test.label.to_numpy(),
                                       'model': m, 'feature_set': s, 'score': v}))
        importance[a] = permutation_importance(train, test, cfg)
        fold_info[a] = {'train_samples': int(len(train)), 'train_positives': int(train.label.sum()),
                        'purged_samples': int((data.area_id != a).sum() - len(train)), 'test_samples': int(len(test))}
        if a == largest:
            joblib.dump({'models': fitted, 'features': FEATURE_SETS, 'held_out_area': a}, models_dir / 'demo_fold.joblib')
        print(f'{a:50s} train {len(train):6d} purged {fold_info[a]["purged_samples"]:5d} test {len(test):5d}', flush=True)
    pred = pd.concat(preds, ignore_index=True)
    table = per_area(pred)
    summary = summarise(table, cfg)
    prim_key = 'hgb:terrain_geology'
    primary = {'auc': summary[prim_key]['auc'], 'diff': summary[prim_key]['auc_minus_hgb:slope_only']}
    results = {'variant': variant, 'tag': t, 'evaluation_areas': eval_areas, 'n_evaluation_areas': len(eval_areas),
               'primary_model': prim_key, 'primary': primary, 'verdict': verdict(primary), 'summary': summary,
               'fold_info': fold_info, 'largest_area': largest}
    # secondary 2: pooled AUC; 3: without largest area
    results['pooled_auc'] = {f'{m}:{s}': float(roc_auc_score(g.label, g.score)) for (m, s), g in pred.groupby(['model', 'feature_set'])}
    if len(eval_areas) > 2:
        results['without_largest_area'] = summarise(table[table.area_id != largest], cfg)
    # secondary 8, 9: reporting bias
    results['reporting_bias'] = reporting_bias(data, pred, eval_areas, cfg)
    # secondary 10: DEM date description
    years = data[data.label == 1].groupby('area_id').year.agg(lambda s: s.dropna().min() if s.notna().all() else np.nan)
    late = [a for a in eval_areas if pd.notna(years.get(a)) and years[a] >= 2017]
    wide = table[(table.model == 'hgb')].pivot(index='area_id', columns='feature_set', values='auc')
    results['dem_date_description'] = {'areas_year_ge_2017': late,
                                       'mean_auc_diff_late': float((wide.terrain_geology - wide.slope_only)[late].mean()) if late else None,
                                       'mean_auc_diff_other': float((wide.terrain_geology - wide.slope_only).drop(late).mean())}
    # secondary 11: permutation importance (mean over areas)
    imp = pd.DataFrame(importance).T
    results['permutation_importance_mean'] = imp.mean().sort_values(ascending=False).round(4).to_dict()
    # secondary 7: land cover
    results['land_cover'] = land_cover_analysis(data, cfg, radius)
    out = REPORT if not areas else DATA / 'pilot'
    save(pred, DATA / f'predictions_{t}.parquet', {'variant': variant})
    save(table, DATA / f'area_table_{t}.parquet', {'variant': variant})
    guard(out)
    write_json(out / f'results_{t}.json', results)
    table.round(4).to_csv(out / f'area_table_{t}.csv', index=False)
    imp.round(4).to_csv(out / f'importance_{t}.csv')
    print(json.dumps({'primary': primary, 'verdict': results['verdict']}, indent=1))
    return results


def reporting_bias(data, pred, eval_areas, cfg) -> dict:
    out = {}
    rows = []
    for a in eval_areas:
        g = data[data.area_id == a]
        rows.append({'area_id': a, 'model': 'infra_distance', 'feature_set': 'distance_only', 'n_pos': int(g.label.sum()),
                     'n_bg': int((g.label == 0).sum()),
                     **area_metrics(g.label.to_numpy(), -np.log10(1 + g.dist_infrastructure_m.to_numpy(float)))})
    dist_table = pd.DataFrame(rows)
    b = cfg['evaluation']['bootstrap']
    out['distance_only_auc'] = bootstrap_mean(dist_table.auc.to_numpy(), b['draws'], b['seed'])
    out['distance_only_per_area'] = dist_table.set_index('area_id').auc.round(4).to_dict()
    far_ids = set(data.loc[data.dist_infrastructure_m >= 200, 'sample_id'])
    far = pred[pred.sample_id.isin(far_ids) & (pred.model == 'hgb')]
    t = per_area(far)
    ok = t[(t.n_pos >= 5) & (t.n_bg >= 5)]
    keep = ok.groupby('area_id').size()
    ok = ok[ok.area_id.isin(keep[keep == keep.max()].index)] if len(ok) else ok
    out['far_from_infrastructure_200m'] = {'areas': sorted(ok.area_id.unique().tolist()),
                                          'positives_share_far': float(data[(data.label == 1)].dist_infrastructure_m.ge(200).mean()),
                                          'background_share_far': float(data[(data.label == 0)].dist_infrastructure_m.ge(200).mean())}
    if ok.area_id.nunique() >= 3:
        out['far_from_infrastructure_200m']['summary'] = summarise(ok, cfg)
        out['far_from_infrastructure_200m']['per_area'] = ok.round(4).to_dict('records')
    return out


def land_cover_analysis(data, cfg, radius) -> dict:
    sub = data[data.clc_vintage.notna()]
    eval_areas = sorted(sub[sub.area_status == 'evaluation'].area_id.unique())
    if len(eval_areas) < 3:
        return {'evaluation_areas': eval_areas, 'note': 'fewer than 3 land-cover evaluation areas'}
    preds = []
    for a, train, test in folds(sub, eval_areas, radius):
        scores, _ = score_models(train, test, cfg, sets=('slope_only', 'terrain_geology', 'terrain_geology_landcover'))
        for (m, s), v in scores.items():
            preds.append(pd.DataFrame({'sample_id': test.sample_id.to_numpy(), 'area_id': a, 'label': test.label.to_numpy(),
                                       'model': m, 'feature_set': s, 'score': v}))
    table = per_area(pd.concat(preds, ignore_index=True))
    b = cfg['evaluation']['bootstrap']
    out = {'evaluation_areas': eval_areas, 'vintages': sub.groupby('area_id').clc_vintage.first().to_dict(),
           'lc_missing_samples': int(sub.land_cover_class.isna().sum()), 'summary': summarise(table, cfg)}
    for m in ('hgb', 'lr'):
        w = table[table.model == m].pivot(index='area_id', columns='feature_set', values='auc')
        out[f'{m}_landcover_minus_terrain_geology'] = bootstrap_mean((w.terrain_geology_landcover - w.terrain_geology).dropna().to_numpy(),
                                                                     b['draws'], b['seed'])
    out['per_area'] = table.round(4).to_dict('records')
    return out
