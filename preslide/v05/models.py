"""V0.5 models: conditional logit (primary, strict convergence) and histogram gradient boosting, explicit allowlist.

All preprocessing is fit on the rows passed as training data only. Scores rank within event groups.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.ensemble import HistGradientBoostingClassifier

from ..v04.models import GroupPreprocessor, group_softmax
from ..v04.context import LC_CLASSES, GEO_CLASSES

MODELS = ['conditional_logit', 'hist_gradient_boosting']
VARIANTS = ['static', 'temporal', 'combined']


def add_one_hot(data):
    data = data.copy()
    for c in LC_CLASSES:
        data[c] = np.where(data.land_cover_class.isna(), np.nan, (data.land_cover_class == c).astype(float))
    for c in GEO_CLASSES:
        data[c] = np.where(data.geology_class.isna(), np.nan, (data.geology_class == c).astype(float))
    return data


def interaction_columns(data, cfg):
    out = {}
    for rain, x in cfg['features']['interactions_conditional_logit_combined']:
        out[f'log1p_{rain}_x_{x}'] = np.log1p(data[rain]) * data[x]
    return pd.DataFrame(out, index=data.index)


def columns(variant, model, cfg, drop=()):
    f = cfg['features']
    cols = {'static': f['static'], 'temporal': f['temporal'], 'combined': f['static'] + f['temporal']}[variant]
    if variant == 'combined' and model == 'conditional_logit':
        cols = cols + [f'log1p_{r}_x_{x}' for r, x in f['interactions_conditional_logit_combined']]
    cols = [c for c in cols if c not in drop]
    check_allowlist(cols, cfg)
    return cols


def check_allowlist(cols, cfg):
    f = cfg['features']
    allowed = set(f['static']) | set(f['temporal']) | {f'log1p_{r}_x_{x}' for r, x in f['interactions_conditional_logit_combined']}
    forbidden = {c for c in f['forbidden_predictors'] if ' ' not in c}
    bad = [c for c in cols if c not in allowed or c in forbidden or c.endswith(('_offset_m', '_last_day', '_status'))]
    if bad:
        raise ValueError(f'Columns outside the registered predictor allowlist: {bad}')


class ConditionalLogit:
    """Stratified (1:k) logistic likelihood, L2-penalised, L-BFGS-B; registered convergence rule (config/v05.json)."""

    def __init__(self, l2=1.0):
        self.l2 = l2

    def fit(self, X, y, groups, weights):
        groups = np.asarray(groups)
        order = np.argsort(groups, kind='stable')
        X, y, groups = X[order], np.asarray(y)[order], groups[order]
        _, start = np.unique(groups, return_index=True)
        bounds = list(zip(start, list(start[1:]) + [len(groups)]))
        if any(y[s:e].sum() != 1 for s, e in bounds):
            raise ValueError('Each stratum needs exactly one positive')
        gw = np.array([weights[groups[s]] for s, _ in bounds])
        pos = np.array([s + int(np.flatnonzero(y[s:e])[0]) for s, e in bounds])
        seg = np.repeat(np.arange(len(bounds)), [e - s for s, e in bounds])

        def objective(beta):
            eta = X @ beta
            m = np.maximum.reduceat(eta, start)
            ex = np.exp(eta - m[seg])
            denom = np.add.reduceat(ex, start)
            ll = np.sum(gw * (eta[pos] - (m + np.log(denom))))
            p = ex / denom[seg]
            expected = np.add.reduceat(X * p[:, None], start, axis=0)
            grad = (gw[:, None] * (X[pos] - expected)).sum(0)
            return -ll + 0.5 * self.l2 * beta @ beta, -grad + self.l2 * beta

        result = minimize(objective, np.zeros(X.shape[1]), jac=True, method='L-BFGS-B', options={'maxiter': 2000})
        value, grad = objective(result.x)
        self.max_abs_gradient_ = float(np.max(np.abs(grad)))
        self.converged_ = bool(result.success) or (
            'ABNORMAL' in str(result.message) and self.max_abs_gradient_ <= 1e-4 * max(1.0, abs(value)))
        if not self.converged_:
            raise RuntimeError(f'Conditional logit did not converge: {result.message} (max|grad| {self.max_abs_gradient_:.2e})')
        self.coef_, self.message_ = result.x, str(result.message)
        return self

    def decision_function(self, X):
        return X @ self.coef_


def train_weights(frame):
    """1/sqrt(n) per event group, n = events of its independence unit in this training frame."""
    gu = frame.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
    counts = gu.value_counts()
    return gu.map(lambda u: 1 / np.sqrt(counts[u]))


def fit_predict(name, train, test, cols, cfg):
    """Returns (scores for test rows, fitted bundle). Preprocessing fit on `train` only."""
    weights = train_weights(train)
    m = cfg['models']
    Xtr, Xte = train[cols], test[cols]
    if name == 'conditional_logit':
        pre = GroupPreprocessor().fit(Xtr, train.event_group_id)
        model = ConditionalLogit(m['conditional_logit']['l2']).fit(pre.transform(Xtr, train.event_group_id), train.label,
                                                                   train.event_group_id, weights)
        score = group_softmax(model.decision_function(pre.transform(Xte, test.event_group_id)), test.event_group_id)
        return score, {'preprocessor': pre, 'model': model, 'columns': cols}
    p = m['hist_gradient_boosting']
    model = HistGradientBoostingClassifier(max_iter=p['max_iter'], max_leaf_nodes=p['max_leaf_nodes'],
                                           min_samples_leaf=p['min_samples_leaf'], l2_regularization=p['l2_regularization'],
                                           class_weight=p['class_weight'], random_state=p['random_state'])
    model.fit(Xtr.to_numpy(float), train.label, sample_weight=train.event_group_id.map(weights).to_numpy())
    return model.predict_proba(Xte.to_numpy(float))[:, 1], {'model': model, 'columns': cols}
