"""Within-group ranking metrics for one positive among k controls (any fixed k), with exact tie handling.

With a = controls scored strictly higher and t = controls tied with the positive, a random order of the tie
block gives: top-k = clip((k - a)/(t + 1), 0, 1); mean rank = 1 + a + t/2; MRR = mean_j 1/(1 + a + j), j = 0..t;
local AUC = (controls lower + 0.5 t)/k. A constant score therefore yields exactly the chance values.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

METRICS = ['local_auc', 'top1', 'top3', 'mean_rank', 'mrr']


def rank_metrics(pos, neg):
    neg = np.asarray(neg, float)
    a, t = int(np.sum(neg > pos)), int(np.sum(neg == pos))
    lower = int(np.sum(neg < pos))
    n = len(neg)
    return {'local_auc': (lower + 0.5 * t) / n,
            'top1': float(np.clip((1 - a) / (t + 1), 0, 1)),
            'top3': float(np.clip((3 - a) / (t + 1), 0, 1)),
            'mean_rank': 1 + a + t / 2,
            'mrr': float(np.mean([1.0 / (1 + a + j) for j in range(t + 1)])),
            'controls_above': a, 'controls_tied': t}


def chance(k):
    return {'local_auc': 0.5, 'top1': 1 / (k + 1), 'top3': min(3, k + 1) / (k + 1), 'mean_rank': (k + 2) / 2,
            'mrr': float(np.mean([1.0 / r for r in range(1, k + 2)])), 'pooled_ap_prevalence': 1 / (k + 1)}


def group_ranks(frame, score, k):
    """Per event group metrics; every group must have exactly one positive and k controls."""
    f = frame[['event_group_id', 'label']].assign(score=np.asarray(score, float))
    if not np.isfinite(f.score).all():
        raise ValueError('Non-finite scores')
    rows = []
    for gid, g in f.groupby('event_group_id', sort=True):
        pos = g.score[g.label == 1].to_numpy()
        neg = g.score[g.label == 0].to_numpy()
        if len(pos) != 1 or len(neg) != k:
            raise ValueError(f'Invalid group {gid}: {len(pos)} positives, {len(neg)} controls (expected 1 and {k})')
        rows.append({'event_group_id': gid, **rank_metrics(pos[0], neg)})
    return pd.DataFrame(rows)


def unit_weights(groups_units):
    """Each independence unit gets total weight 1, shared equally by its event groups."""
    counts = groups_units.value_counts()
    return groups_units.map(lambda u: 1.0 / counts[u])


def summarize(ranks, units):
    """units: Series event_group_id -> independence unit."""
    r = ranks.merge(units.rename('unit'), left_on='event_group_id', right_index=True, how='left')
    if r.unit.isna().any():
        raise ValueError('Group without independence unit')
    w = unit_weights(r.set_index('event_group_id').unit).to_numpy()
    out = {f'{m}_units': float(np.average(r[m], weights=w)) for m in METRICS}
    out.update({f'{m}_events': float(r[m].mean()) for m in METRICS})
    out.update(events=int(len(r)), units=int(r.unit.nunique()))
    return out


def pooled_ap(frame, score):
    return float(average_precision_score(frame.label, score))


def bootstrap(ranks_by_variant, units, draws, seed, metric='local_auc'):
    """Unit bootstrap of the unit-weighted metric for each variant and paired differences (same draws)."""
    rng = np.random.default_rng(seed)
    ids = sorted(units.unique())
    members = {u: units.index[units == u].tolist() for u in ids}
    tables = {k: v.set_index('event_group_id')[metric] for k, v in ranks_by_variant.items()}
    samples = {k: np.empty(draws) for k in tables}
    for d in range(draws):
        chosen = rng.choice(ids, len(ids), replace=True)
        gids, weights = [], []
        for u in chosen:
            gids += members[u]
            weights += [1.0 / len(members[u])] * len(members[u])
        for k, t in tables.items():
            samples[k][d] = float(np.average(t.loc[gids].to_numpy(), weights=weights))
    out = {k: {'ci95': np.quantile(v, [.025, .975]).tolist()} for k, v in samples.items()}
    keys = list(tables)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            d = samples[b] - samples[a]
            out[f'{b}_minus_{a}'] = {'mean': float(d.mean()), 'ci95': np.quantile(d, [.025, .975]).tolist(),
                                     'share_above_zero': float((d > 0).mean())}
    return out
