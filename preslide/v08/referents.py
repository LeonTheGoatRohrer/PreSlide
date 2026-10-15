"""Referent times and inventory-based exclusion for the case-crossover (pure functions, config/v08.json)."""
from datetime import date, timedelta
from typing import Optional

import pandas as pd

TZ = 'Europe/Vienna'
PROCESS_GROUPS = ('Gleiten/Rutschen', 'Fliessen', 'Massenbewegung (unklarer Typ)')


def referent_times(t0_utc: pd.Timestamp, offsets_days: list[int]) -> list[pd.Timestamp]:
    """t0 shifted by whole days at the identical UTC clock time (timezone-aware)."""
    t0 = pd.Timestamp(t0_utc)
    if t0.tzinfo is None:
        raise ValueError('t0 must be timezone-aware')
    return [t0 + pd.Timedelta(days=int(o)) for o in offsets_days]


def local_day(ts: pd.Timestamp) -> date:
    return pd.Timestamp(ts).tz_convert(TZ).date()


def record_interval(attrs: dict) -> Optional[tuple[date, date]]:
    """Widest consistent local-day interval of an inventory record, or None if it has no usable date."""
    s, e = attrs.get('Date_Anfan'), attrs.get('Date_End_a')
    if s is not None and e is not None:
        a, b = (pd.Timestamp(v, unit='ms', tz='UTC').tz_convert(TZ).date() for v in (s, e))
        return (a, b) if a <= b else None
    y, m, d = (attrs.get(k) for k in ('EREIGNIS_J', 'EREIGNIS_M', 'EREIGNIS_T'))
    if not y:
        return None
    try:
        if m and d:
            return date(int(y), int(m), int(d)), date(int(y), int(m), int(d))
        if m:
            first = date(int(y), int(m), 1)
            nxt = date(int(y) + (m == 12), int(m) % 12 + 1, 1)
            return first, nxt - timedelta(days=1)
        return date(int(y), 1, 1), date(int(y), 12, 31)
    except ValueError:
        return None


def overlaps_referent(interval: tuple[date, date], referent_day: date, slack_days: int = 1) -> bool:
    lo, hi = referent_day - timedelta(days=slack_days), referent_day + timedelta(days=slack_days)
    return interval[0] <= hi and interval[1] >= lo


def blocked_referents(near_intervals: list[Optional[tuple[date, date]]], referent_days: list[date]) -> list[bool]:
    """True for referent days overlapped by at least one dated inventory record near the slope."""
    dated = [iv for iv in near_intervals if iv is not None]
    return [any(overlaps_referent(iv, d) for iv in dated) for d in referent_days]


def local_midnight_utc(day: date) -> pd.Timestamp:
    return pd.Timestamp(day.isoformat(), tz=TZ).tz_convert('UTC')


def side(offset_days: int) -> str:
    return 'before' if offset_days < 0 else 'after'

