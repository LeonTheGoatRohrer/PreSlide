"""Case and reference windows per event, and every registered comparison (config/extremwetter_v01.json)."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import design as D

PS = (0.95, 0.99)


@dataclass
class Matrices:
    years: np.ndarray                 # reference years, e.g. 1961..2025
    event_years: np.ndarray           # (n,)
    allowed: np.ndarray               # (n, years, offsets) not event year and not inventory-excluded
    inventory_excluded: np.ndarray    # (n, years, offsets)
    cases: dict                       # combo -> (n,)
    refs: dict                        # combo -> (n, years, offsets), NaN outside the series


def combos(cfg: dict) -> list[tuple[int, int]]:
    """(window_days, last_label_offset_days) pairs needed by the registered comparisons."""
    ends = [v['last_label_offset_days'] for v in cfg['exposure']['window_end'].values()]
    out = [(k, e) for e in ends for k in cfg['exposure']['windows_days']]
    p = cfg['exposure']['placebo']
    return out + [(p['window_days'], p['last_label_offset_days'])]


def build(events: pd.DataFrame, series: dict, intervals: dict, cfg: dict) -> Matrices:
    ref = cfg['reference']
    years = np.arange(ref['years']['sensitivity_full_series'][0], ref['years']['primary'][1] + 1)
    half, days = 15, ref['documented_event_exclusion']['days']
    n, cs = len(events), combos(cfg)
    cases = {c: np.full(n, np.nan) for c in cs}
    refs = {c: np.full((n, len(years), 2 * half + 1), np.nan) for c in cs}
    allowed = np.zeros((n, len(years), 2 * half + 1), bool)
    inv = np.zeros_like(allowed)
    for i, row in enumerate(events.itertuples()):
        first, values = series[row.event_group_id][:2]
        anchors = D.anchor_grid(row.event_day, list(years), half)
        inv[i] = D.excluded_by_inventory(anchors, intervals[row.event_group_id], days)
        allowed[i] = ~inv[i] & (years != row.event_day.year)[:, None]
        case_anchor = np.array([[row.event_day]], dtype=object)
        for c in cs:
            x = D.window_sums(first, values, case_anchor, *c)[0, 0]
            if not np.isfinite(x):
                raise ValueError(f'case window outside series: {row.event_group_id} {c}')
            cases[c][i] = x
            refs[c][i] = D.window_sums(first, values, anchors, *c)
    return Matrices(years, np.array([d.year for d in events.event_day]), allowed, inv, cases, refs)


def event_scores(m: Matrices, combo, year_range, minimum: int):
    """Per-event PR, exceedance and expected exceedance; plus leave-one-out grids for the null."""
    ymask = (m.years >= year_range[0]) & (m.years <= year_range[1])
    n = len(m.event_years)
    out = {'pr': np.full(n, np.nan), 'n_ref': np.zeros(n, int), 'reason': np.full(n, '', object)}
    for p in PS:
        out[f'exc{p}'] = np.full(n, np.nan)
        out[f'exp{p}'] = np.full(n, np.nan)
    shape = m.allowed.shape[1:]
    loo = {'pr': np.full((n,) + shape, np.nan), **{p: np.full((n,) + shape, np.nan) for p in PS}}
    valid_all = np.zeros_like(m.allowed)
    for i in range(n):
        r = m.refs[combo][i]
        valid = m.allowed[i] & ymask[:, None] & np.isfinite(r)
        out['n_ref'][i] = valid.sum()
        if valid.sum() < minimum:
            out['reason'][i] = 'too_few_reference_windows'
            continue
        valid_all[i] = valid
        values, x = r[valid], m.cases[combo][i]
        out['pr'][i] = D.percentile_rank(x, values)
        for p in PS:
            out[f'exc{p}'][i] = D.exceeds(x, values, p)
            out[f'exp{p}'][i] = D.expected_exceedance(values, p)
        pr, exc = D.leave_one_out_scores(values, PS)
        loo['pr'][i][valid] = pr
        for p in PS:
            loo[p][i][valid] = exc[p]
    return out, loo, valid_all


def _finite(value):
    """JSON-safe number: +inf (all cases above Q_p) becomes None."""
    return float(value) if np.isfinite(value) else None


def _stats(scores, idx, w):
    s = {'mean_pr': D.weighted_mean(scores['pr'][idx], w)}
    for p in PS:
        share = D.weighted_mean(scores[f'exc{p}'][idx], w)
        expected = D.weighted_mean(scores[f'exp{p}'][idx], w)
        s[f'share_q{round(p * 100)}'] = share
        s[f'expected_q{round(p * 100)}'] = expected
        s[f'rate_ratio_q{round(p * 100)}'] = D.rate_ratio(share, expected)
    return s


def evaluate(m: Matrices, events: pd.DataFrame, combo, year_range, subset: np.ndarray, weighting: str, cfg: dict) -> dict:
    st = cfg['statistics']
    scores, loo, valid = event_scores(m, combo, year_range, cfg['reference']['minimum_reference_windows'])
    use = subset & np.isfinite(scores['pr'])
    excluded = {'too_few_reference_windows': int((subset & ~np.isfinite(scores['pr'])).sum())}
    idx = np.flatnonzero(use)
    episodes = events.episode.to_numpy()[idx]
    w = D.episode_weights(episodes, weighting)
    observed = _stats(scores, idx, w)

    # episode bootstrap (whole episodes resampled)
    boot = []
    for draw, _ in D.bootstrap_indices(episodes, st['bootstrap']['draws'], st['bootstrap']['seed']):
        boot.append(_stats(scores, idx[draw], w[draw]))
    boot = pd.DataFrame(boot)

    # pseudo-case null: one common reference cell per episode, ranked leave-one-out
    rng = np.random.default_rng(st['null']['seed'])
    draws = st['null']['draws']
    flat_pr = loo['pr'][idx].reshape(len(idx), -1)
    flat_exc = {p: loo[p][idx].reshape(len(idx), -1) for p in PS}
    null_pr = np.zeros((draws, len(idx)))
    null_exc = {p: np.zeros((draws, len(idx))) for p in PS}
    for e in np.unique(episodes):
        members = np.flatnonzero(episodes == e)
        cells = np.flatnonzero(valid[idx[members]].reshape(len(members), -1).all(axis=0))
        if len(cells) == 0:
            raise ValueError(f'no common reference cell for episode {e}')
        pick = cells[rng.integers(len(cells), size=draws)]
        null_pr[:, members] = flat_pr[members][:, pick].T
        for p in PS:
            null_exc[p][:, members] = flat_exc[p][members][:, pick].T
    null_mean = null_pr @ w / w.sum()
    row = {
        'window_days': combo[0], 'last_label_offset_days': combo[1], 'years': list(year_range), 'weighting': weighting,
        'n_events': int(len(idx)), 'n_episodes': int(len(np.unique(episodes))), 'excluded_events': excluded,
        'median_reference_windows': int(np.median(scores['n_ref'][idx])),
        'mean_pr': observed['mean_pr'],
        'mean_pr_ci95': [float(boot.mean_pr.quantile(0.025)), float(boot.mean_pr.quantile(0.975))],
        'null_mean_pr': float(null_mean.mean()),
        'null_mean_pr_95': [float(np.quantile(null_mean, 0.025)), float(np.quantile(null_mean, 0.975))],
        'p_one_sided': float((1 + (null_mean >= observed['mean_pr'] - 1e-12).sum()) / (1 + draws)),
    }
    for p in PS:
        q = round(p * 100)
        null_share = null_exc[p] @ w / w.sum()
        rr = boot[f'rate_ratio_q{q}']
        # infinite ratios (every resampled event above Q_p) stay +inf (no interpolation), written as null
        lo_rr, hi_rr = (float(np.quantile(rr, a, method='inverted_cdf')) for a in (0.025, 0.975))
        row.update({
            f'share_q{q}': observed[f'share_q{q}'],
            f'share_q{q}_ci95': [float(boot[f'share_q{q}'].quantile(0.025)), float(boot[f'share_q{q}'].quantile(0.975))],
            f'expected_q{q}': observed[f'expected_q{q}'],
            f'null_share_q{q}_95': [float(np.quantile(null_share, 0.025)), float(np.quantile(null_share, 0.975))],
            f'p_share_q{q}_one_sided': float((1 + (null_share >= observed[f'share_q{q}'] - 1e-12).sum()) / (1 + draws)),
            f'rate_ratio_q{q}': _finite(observed[f'rate_ratio_q{q}']),
            f'rate_ratio_q{q}_ci95': [_finite(lo_rr), _finite(hi_rr)],
            f'rate_ratio_q{q}_bootstrap_infinite': int(np.isinf(boot[f'rate_ratio_q{q}']).sum()),
        })
    return row, scores


def settings(cfg: dict, events: pd.DataFrame) -> list[dict]:
    """The 51 registered comparison rows (10 settings x 5 windows + placebo)."""
    yr = cfg['reference']['years']
    ends = cfg['exposure']['window_end']
    allv = np.ones(len(events), bool)
    base = {'years': tuple(yr['primary']), 'end': ends['primary']['last_label_offset_days'], 'subset': allv, 'weighting': 'episode'}
    variants = [
        ('primary', {}),
        ('events_weighted', {'weighting': 'event'}),
        ('without_stanz', {'subset': ~events.stanz.to_numpy()}),
        ('hangmure', {'subset': (events.process_class == 'Hangmure').to_numpy()}),
        ('hangmure_gemischt', {'subset': (events.process_class == 'Hangmure gemischt').to_numpy()}),
        ('lockergesteinsrutschung', {'subset': (events.process_class == 'Lockergesteinsrutschung').to_numpy()}),
        ('reference_1961_2025', {'years': tuple(yr['sensitivity_full_series'])}),
        ('reference_2011_2025', {'years': tuple(yr['sensitivity_recent'])}),
        ('end_minus1_may_contain_post_t0', {'end': ends['secondary_previous_day']['last_label_offset_days']}),
        ('end_0_contains_post_t0', {'end': ends['secondary_event_day']['last_label_offset_days']}),
    ]
    out = []
    for name, change in variants:
        for k in cfg['exposure']['windows_days']:
            s = {**base, **change}
            out.append({'setting': name, 'combo': (k, s['end']), **s})
    p = cfg['exposure']['placebo']
    out.append({'setting': 'placebo', 'combo': (p['window_days'], p['last_label_offset_days']), **base})
    return out
