"""Pure case-crossover primitives (config/extremwetter_v01.json). No IO here.

Day labels are SPARTACUS labels: label D = precipitation 07:00 CET D -> 07:00 CET D+1 (06:00 UTC D+1).
An event day E is a local (Europe/Vienna) calendar day; t0 >= local midnight of E.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

TZ = ZoneInfo('Europe/Vienna')
LABEL_END_UTC = timedelta(days=1, hours=6)       # label D valid at D+1 06:00 UTC


def label_valid_utc(label: date) -> datetime:
    """UTC instant at which the SPARTACUS value labelled `label` is complete."""
    return datetime.combine(label, time(0), tzinfo=timezone.utc) + LABEL_END_UTC


def earliest_t0_utc(event_day: date) -> datetime:
    """Earliest possible t0 of an event day: local midnight, in UTC."""
    return datetime.combine(event_day, time(0), tzinfo=TZ).astimezone(timezone.utc)


def window_labels(anchor: date, window_days: int, end_offset_days: int) -> tuple[date, date]:
    """First and last SPARTACUS label of a k-day window whose last label is anchor + end_offset_days."""
    if window_days < 1:
        raise ValueError('window_days must be >= 1')
    last = anchor + timedelta(days=end_offset_days)
    return last - timedelta(days=window_days - 1), last


def shift_year(day: date, year: int) -> date:
    """Same calendar day in another year; 29 February becomes 28 February in non-leap years."""
    try:
        return day.replace(year=year)
    except ValueError:
        return day.replace(year=year, day=28)


def anchor_grid(event_day: date, years: list[int], half_width_days: int) -> np.ndarray:
    """Anchor days [len(years), 2*half_width+1]: event day moved to each year, then offset -h..+h."""
    offsets = range(-half_width_days, half_width_days + 1)
    return np.array([[shift_year(event_day, y) + timedelta(days=o) for o in offsets] for y in years], dtype=object)


def excluded_by_inventory(anchors: np.ndarray, intervals: list[tuple[date, date]], days: int) -> np.ndarray:
    """True where an anchor r has a documented (nearby) record interval [s, e] intersecting [r-days, r+days]."""
    out = np.zeros(anchors.shape, bool)
    if not intervals:
        return out
    starts = np.array([np.datetime64(s) for s, _ in intervals])
    ends = np.array([np.datetime64(e) for _, e in intervals])
    flat = np.array([np.datetime64(a) for a in anchors.ravel()])
    lo, hi = flat - np.timedelta64(days, 'D'), flat + np.timedelta64(days, 'D')
    hit = (starts[None, :] <= hi[:, None]) & (ends[None, :] >= lo[:, None])
    return hit.any(axis=1).reshape(anchors.shape)


def check_series(values: np.ndarray) -> np.ndarray:
    """Daily RR array must be non-empty, finite and within [0, 500] mm; otherwise fail loudly."""
    values = np.asarray(values, float)
    if values.size == 0:
        raise ValueError('empty_weather_series')
    if not np.isfinite(values).all():
        raise ValueError(f'missing_weather_values:{int((~np.isfinite(values)).sum())}')
    if values.min() < 0 or values.max() > 500:
        raise ValueError(f'implausible_weather_values:min={values.min():.2f}_max={values.max():.2f}')
    return values


def window_sums(first_label: date, values: np.ndarray, anchors: np.ndarray, window_days: int,
                end_offset_days: int) -> np.ndarray:
    """Precipitation sums for every anchor; NaN where the window leaves the series. Series must pass check_series."""
    values = check_series(values)
    csum = np.concatenate([[0.0], np.cumsum(values)])
    flat = anchors.ravel()
    last = np.array([(a - first_label).days + end_offset_days for a in flat])
    first = last - (window_days - 1)
    inside = (first >= 0) & (last < len(values))
    out = np.full(len(flat), np.nan)
    out[inside] = csum[last[inside] + 1] - csum[first[inside]]
    return out.reshape(anchors.shape)


def percentile_rank(x: float, reference: np.ndarray) -> float:
    """Mid-rank percentile of x in reference: (#less + 0.5 #equal) / n. Exchangeable x => mean 0.5."""
    reference = np.asarray(reference, float)
    if reference.size == 0 or not np.isfinite(reference).all() or not np.isfinite(x):
        raise ValueError('percentile_rank needs a finite case value and a non-empty finite reference')
    return float(((reference < x).sum() + 0.5 * (reference == x).sum()) / reference.size)


def exceeds(x: float, reference: np.ndarray, p: float) -> bool:
    """x strictly above the linear-interpolated p-quantile of its reference."""
    return bool(x > np.quantile(np.asarray(reference, float), p))


def expected_exceedance(reference: np.ndarray, p: float) -> float:
    """Share of the reference itself above its own p-quantile (null expectation, about 1 - p)."""
    reference = np.asarray(reference, float)
    return float((reference > np.quantile(reference, p)).mean())


def leave_one_out_scores(reference: np.ndarray, ps: tuple[float, ...]) -> tuple[np.ndarray, dict]:
    """For each reference value v_j: PR of v_j among the others, and v_j > Q_p(others) for each p."""
    v = np.asarray(reference, float)
    n = v.size
    if n < 3:
        raise ValueError('need >= 3 reference windows')
    s = np.sort(v)
    less = np.searchsorted(s, v, 'left')
    equal = np.searchsorted(s, v, 'right') - less
    pr = (less + 0.5 * (equal - 1)) / (n - 1)
    j = less + equal - 1                     # remove one copy of v_j (position irrelevant among ties)
    exceed = {}
    for p in ps:
        h = p * (n - 2)
        lo = int(np.floor(h))
        frac = h - lo

        def at(i):
            return np.where(i < j, s[np.minimum(i, n - 1)], s[np.minimum(i + 1, n - 1)])
        q = at(lo) + frac * (at(min(lo + 1, n - 2)) - at(lo))
        exceed[p] = v > q
    return pr, exceed


def episode_weights(episodes: np.ndarray, mode: str) -> np.ndarray:
    """mode 'episode': each episode total weight 1 split over its events; 'event': each event weight 1."""
    episodes = np.asarray(episodes)
    if mode == 'event':
        return np.ones(len(episodes))
    if mode != 'episode':
        raise ValueError(mode)
    _, inverse, counts = np.unique(episodes, return_inverse=True, return_counts=True)
    return 1.0 / counts[inverse]


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(values * weights) / np.sum(weights))


def bootstrap_indices(episodes: np.ndarray, draws: int, seed: int):
    """Yield event index arrays; each draw resamples whole episodes with replacement."""
    episodes = np.asarray(episodes)
    names = np.unique(episodes)
    members = {e: np.flatnonzero(episodes == e) for e in names}
    rng = np.random.default_rng(seed)
    for _ in range(draws):
        chosen = rng.choice(names, size=len(names), replace=True)
        yield np.concatenate([members[e] for e in chosen]), chosen


def rate_ratio(share: float, expected: float) -> float:
    """Case-crossover odds ratio [s/(1-s)] / [q/(1-q)]; inf if every case exceeds."""
    if share >= 1:
        return float('inf')
    return float((share / (1 - share)) / (expected / (1 - expected)))


def holm(pvalues: dict) -> dict:
    """Holm step-down adjusted p-values."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m, running, out = len(items), 0.0, {}
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out
