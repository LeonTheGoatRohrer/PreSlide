"""V0.4 models and group-level metrics. All preprocessing is fit on the training rows only."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from .weather import INCA_FEATURES, SAME_DAY, DAILY_FEATURES
from .context import LC_CLASSES, GEO_CLASSES

TERRAIN = ['elevation', 'slope', 'aspect_sin', 'aspect_cos', 'profile_curvature', 'plan_curvature', 'roughness_tri',
           'tpi_150m', 'tpi_500m', 'relative_position_500m', 'log10_catchment_m2', 'twi']
STATIC = TERRAIN + LC_CLASSES + GEO_CLASSES
INTERACTIONS = [('rain_sum_3d', 'slope'), ('rain_sum_30d', 'log10_catchment_m2'), ('rain_sum_3d', 'profile_curvature')]
MODELS = ['conditional_logit', 'logistic_regression', 'hist_gradient_boosting']
VARIANTS = ['static', 'temporal', 'combined']


def temporal_columns(admitted_daily):
    return INCA_FEATURES + SAME_DAY + [c for c in DAILY_FEATURES if c in admitted_daily]


def add_one_hot(data):
    data = data.copy()
    for c in LC_CLASSES:
        data[c] = np.where(data.land_cover_class.isna(), np.nan, (data.land_cover_class == c).astype(float))
    for c in GEO_CLASSES:
        data[c] = np.where(data.geology_class.isna(), np.nan, (data.geology_class == c).astype(float))
    return data


def interaction_columns(data):
    out = {}
    for rain, x in INTERACTIONS:
        out[f'log1p_{rain}_x_{x}'] = np.log1p(data[rain]) * data[x]
    return pd.DataFrame(out, index=data.index)


class GroupPreprocessor:
    """Linear models: a feature missing in any sample of a group gives that group no contrast (training mean
    for all six); then standardization. Means/SDs come from training rows only."""

    def fit(self, X, groups):
        Xg = self._group_mask(X, groups)
        self.mean_ = Xg.mean(skipna=True).fillna(0.0)
        self.sd_ = Xg.std(skipna=True).replace(0, 1).fillna(1.0)
        return self

    @staticmethod
    def _group_mask(X, groups):
        bad = X.isna().groupby(groups.to_numpy()).transform('any')
        bad.index = X.index
        return X.mask(bad)

    def transform(self, X, groups):
        Xg = self._group_mask(X, groups).fillna(self.mean_)
        return ((Xg - self.mean_) / self.sd_).to_numpy(float)


class ConditionalLogit:
    """Stratified (1:k matched) logistic likelihood, L2-penalised, scipy L-BFGS. Scores rank within groups."""

    def __init__(self, l2=1.0):
        self.l2 = l2

    def fit(self, X, y, groups, weights):
        groups = np.asarray(groups)
        order = np.argsort(groups, kind='stable')
        X, y, groups = X[order], np.asarray(y)[order], groups[order]
        _, start = np.unique(groups, return_index=True)
        bounds = list(zip(start, list(start[1:]) + [len(groups)]))
        gw = np.array([weights[groups[s]] for s, _ in bounds])
        pos = np.array([s + int(np.flatnonzero(y[s:e])[0]) for s, e in bounds])
        if any(y[s:e].sum() != 1 for s, e in bounds):
            raise ValueError('Each stratum needs exactly one positive')
        seg = np.repeat(np.arange(len(bounds)), [e - s for s, e in bounds])

        def objective(beta):
            eta = X @ beta
            m = np.maximum.reduceat(eta, start)
            ex = np.exp(eta - m[seg])
            denom = np.add.reduceat(ex, start)
            lse = m + np.log(denom)
            ll = np.sum(gw * (eta[pos] - lse))
            p = ex / denom[seg]
            expected = np.add.reduceat(X * p[:, None], start, axis=0)
            grad = (gw[:, None] * (X[pos] - expected)).sum(0)
            return -ll + 0.5 * self.l2 * beta @ beta, -grad + self.l2 * beta

        result = minimize(objective, np.zeros(X.shape[1]), jac=True, method='L-BFGS-B', options={'maxiter': 2000})
        if not result.success and 'ABNORMAL' not in str(result.message):
            raise RuntimeError(f'Conditional logit did not converge: {result.message}')
        self.coef_, self.converged_ = result.x, bool(result.success)
        return self

    def decision_function(self, X):
        return X @ self.coef_


def group_softmax(score, groups):
    s = pd.Series(score)
    g = pd.Series(np.asarray(groups))
    return np.exp(s - s.groupby(g).transform(lambda v: logsumexp(v))).to_numpy()


def fit_predict(name, train, test, columns, weight_by_group, cfg):
    """Returns (scores for test rows, fitted object bundle)."""
    Xtr, Xte = train[columns], test[columns]
    gtr, gte = train.event_group_id, test.event_group_id
    w = train.event_group_id.map(weight_by_group).to_numpy()
    if name == 'conditional_logit':
        pre = GroupPreprocessor().fit(Xtr, gtr)
        model = ConditionalLogit(cfg['conditional_logit']['l2']).fit(pre.transform(Xtr, gtr), train.label, gtr, weight_by_group)
        score = group_softmax(model.decision_function(pre.transform(Xte, gte)), gte)
        return score, {'preprocessor': pre, 'model': model}
    if name == 'logistic_regression':
        p = cfg['logistic_regression']
        pre = GroupPreprocessor().fit(Xtr, gtr)
        model = LogisticRegression(C=p['C'], class_weight=p['class_weight'], max_iter=p['max_iter'], random_state=42)
        model.fit(pre.transform(Xtr, gtr), train.label, sample_weight=w)
        return model.predict_proba(pre.transform(Xte, gte))[:, 1], {'preprocessor': pre, 'model': model}
    p = cfg['hist_gradient_boosting']
    model = HistGradientBoostingClassifier(max_iter=p['max_iter'], max_leaf_nodes=p['max_leaf_nodes'],
                                           min_samples_leaf=p['min_samples_leaf'], l2_regularization=p['l2_regularization'],
                                           class_weight=p['class_weight'], random_state=p['random_state'])
    model.fit(Xtr.to_numpy(float), train.label, sample_weight=w)
    return model.predict_proba(Xte.to_numpy(float))[:, 1], {'model': model}


# ---------- metrics ----------

def group_ranks(frame, score):
    """Per event group: positive's fractional rank, local AUC, top-1 share and AP (=1/rank)."""
    f = frame[['event_group_id', 'label']].assign(score=np.asarray(score, float))
    rows = []
    for gid, g in f.groupby('event_group_id', sort=True):
        pos = g.score[g.label == 1].to_numpy()
        neg = g.score[g.label == 0].to_numpy()
        if len(pos) != 1 or len(neg) != 5:
            raise ValueError(f'Invalid group {gid}')
        above, ties = np.sum(neg > pos[0]), np.sum(neg == pos[0])
        rows.append({'event_group_id': gid, 'rank': 1 + above + 0.5 * ties,
                     'local_auc': (np.sum(neg < pos[0]) + 0.5 * ties) / 5,
                     'top1': (1.0 / (1 + ties)) if above == 0 else 0.0,
                     'local_ap': 1.0 / (1 + above + 0.5 * ties)})
    return pd.DataFrame(rows)


def unit_weights_eval(groups_units):
    """Each independence unit gets total weight 1, shared equally by its event groups."""
    counts = groups_units.value_counts()
    return groups_units.map(lambda u: 1.0 / counts[u])


def summarize(ranks, units):
    r = ranks.merge(units.rename('unit'), left_on='event_group_id', right_index=True)
    w = unit_weights_eval(r.set_index('event_group_id').unit).to_numpy()
    out = {f'{m}_weighted': float(np.average(r[m], weights=w)) for m in ('local_auc', 'top1', 'local_ap')}
    out.update({f'{m}_events': float(r[m].mean()) for m in ('local_auc', 'top1', 'local_ap')})
    out.update(events=int(len(r)), units=int(r.unit.nunique()))
    return out


def pooled_ap(frame, score):
    return float(average_precision_score(frame.label, score))


def bootstrap(ranks_by_variant, units, draws, seed):
    """Unit bootstrap of weighted local AUC for each variant and the paired differences (same draws)."""
    rng = np.random.default_rng(seed)
    ids = sorted(units.unique())
    members = {u: units.index[units == u].tolist() for u in ids}
    tables = {k: v.set_index('event_group_id') for k, v in ranks_by_variant.items()}
    samples = {k: [] for k in tables}
    for _ in range(draws):
        chosen = rng.choice(ids, len(ids), replace=True)
        gids, weights = [], []
        for u in chosen:
            gids += members[u]
            weights += [1.0 / len(members[u])] * len(members[u])
        for k, t in tables.items():
            samples[k].append(float(np.average(t.loc[gids, 'local_auc'], weights=weights)))
    out = {k: {'ci95': np.quantile(v, [.025, .975]).tolist()} for k, v in samples.items()}
    keys = list(tables)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            d = np.array(samples[a]) - np.array(samples[b])
            out[f'{a}_minus_{b}'] = {'mean': float(d.mean()), 'ci95': np.quantile(d, [.025, .975]).tolist(),
                                     'share_above_zero': float((d > 0).mean())}
    return out


def random_rank_null(units, draws=10000, seed=7):
    """Chance distribution of the unit-weighted local AUC for these groups (uniform random rank in each group)."""
    rng = np.random.default_rng(seed)
    w = unit_weights_eval(units).to_numpy()
    auc = rng.integers(0, 6, size=(draws, len(units))) / 5
    vals = auc @ (w / w.sum())
    return {'mean': float(vals.mean()), 'q05': float(np.quantile(vals, .05)), 'q95': float(np.quantile(vals, .95)),
            'q025': float(np.quantile(vals, .025)), 'q975': float(np.quantile(vals, .975)), 'samples': vals}
