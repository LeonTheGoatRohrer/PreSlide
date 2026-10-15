"""Hydrological summaries of an hourly INCA rain series before t0 (pure functions, config/v06.json).

Only hours admissible under the V0.4 boundary rule (T + 1 h < t0, T - 1 h >= t0 - 60 d) are ever read.
"""
import numpy as np
import pandas as pd

from ..v04.weather import admissible, expected_hours

WINDOW = pd.Timedelta(days=60)


def window_rain(times: pd.DatetimeIndex, rain, t0_utc: pd.Timestamp) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """The complete admissible 60-day hourly rain (ValueError when incomplete or implausible)."""
    times = pd.DatetimeIndex(times)
    if times.tz is None or times.has_duplicates or not times.is_monotonic_increasing:
        raise ValueError('Weather timestamps must be unique, sorted and timezone-aware')
    keep = admissible(times, t0_utc, WINDOW)
    if not times[keep].equals(expected_hours(t0_utc, WINDOW)):
        raise ValueError('incomplete_weather_timestamps:60d')
    r = np.asarray(rain, float)[keep]
    if not np.isfinite(r).all() or np.any((r < 0) | (r > 500)):
        raise ValueError('missing_or_implausible_rain:60d')
    return times[keep], r


def api(r: np.ndarray, half_life_days: float) -> float:
    k = 0.5 ** (1.0 / (24.0 * half_life_days))
    value = 0.0
    for x in r:
        value = k * value + x
    return float(value)


def max_rolling_sum(r: np.ndarray, hours: int) -> tuple[float, int]:
    """Maximum rolling sum over `hours` consecutive hours and the number of hours after the maximising interval (latest on ties)."""
    sums = np.convolve(r, np.ones(hours), mode='valid')
    best = float(sums.max())
    end = int(np.flatnonzero(sums >= best - 1e-12)[-1]) + hours      # index one past the last hour of the interval
    return best, len(r) - end


def blocks_24h(r: np.ndarray) -> np.ndarray:
    n = (len(r) // 24) * 24
    return r[len(r) - n:].reshape(-1, 24).sum(axis=1)


def longest_run(mask: np.ndarray) -> int:
    best = run = 0
    for flag in mask:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def hydro_features(times, rain, t0_utc, cfg: dict, swe_melt: dict | None = None, rain_sums: dict | None = None) -> dict:
    """cfg = config['hydrology']; swe_melt/rain_sums: existing V0.4 features keyed '3d','7d','14d' for available water."""
    _, r = window_rain(times, rain, pd.Timestamp(t0_utc))
    out = {f'api_hl{d}d': api(r, d) for d in cfg['api_half_lives_days']}
    for h in cfg['max_sum_hours']:
        out[f'max_sum_{h}h'], out[f'max_sum_{h}h_hours_before_t0'] = max_rolling_sum(r, h)
    daily = blocks_24h(r)
    for thr in cfg['wet_day_thresholds_mm']:
        for w in cfg['wet_day_windows_days']:
            out[f'wet_days_ge{thr}mm_{w}d'] = int((daily[-w:] >= thr).sum())
    dry = r < cfg['dry_hour_threshold_mm']
    out['longest_dry_spell_h_60d'] = longest_run(dry)
    out['current_dry_spell_h'] = _leading_run(dry[::-1])
    for n in ('3d', '7d', '14d'):
        melt = (swe_melt or {}).get(n, np.nan)
        rs = (rain_sums or {}).get(n, np.nan)
        out[f'available_water_{n}'] = float(rs + melt) if np.isfinite(melt) and np.isfinite(rs) else np.nan
    return out


def _leading_run(mask: np.ndarray) -> int:
    """Length of the initial run of True values."""
    return int(len(mask) if mask.all() else np.argmin(mask))
