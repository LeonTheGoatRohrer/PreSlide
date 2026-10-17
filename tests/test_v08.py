from datetime import date

import pandas as pd
import pytest

from preslide.v08 import referents as RF


def test_referent_times_keep_clock_time_and_are_symmetric():
    t0 = pd.Timestamp('2022-08-05T10:00:00Z')
    ts = RF.referent_times(t0, [-56, -28, 28, 56])
    assert [t.hour for t in ts] == [10] * 4 and ts[1] == t0 - pd.Timedelta(days=28) and ts[2] == t0 + pd.Timedelta(days=28)
    with pytest.raises(ValueError):
        RF.referent_times(pd.Timestamp('2022-08-05T10:00:00'), [28])


def test_record_interval_prefers_structured_interval_then_widest_calendar_range():
    ms = lambda s: int(pd.Timestamp(s, tz='UTC').timestamp() * 1000)   # noqa: E731
    assert RF.record_interval({'Date_Anfan': ms('2009-06-23T00:00'), 'Date_End_a': ms('2009-06-30T00:00')}) == (date(2009, 6, 23), date(2009, 6, 30))
    assert RF.record_interval({'EREIGNIS_J': 2009, 'EREIGNIS_M': 6, 'EREIGNIS_T': None}) == (date(2009, 6, 1), date(2009, 6, 30))
    assert RF.record_interval({'EREIGNIS_J': 2009, 'EREIGNIS_M': 12}) == (date(2009, 12, 1), date(2009, 12, 31))
    assert RF.record_interval({'EREIGNIS_J': 2009}) == (date(2009, 1, 1), date(2009, 12, 31))
    assert RF.record_interval({'EREIGNIS_J': 2009, 'EREIGNIS_M': 2, 'EREIGNIS_T': 30}) is None
    assert RF.record_interval({}) is None


def test_inventory_exclusion_boundaries():
    iv = (date(2020, 8, 10), date(2020, 8, 12))
    assert RF.overlaps_referent(iv, date(2020, 8, 9)) and RF.overlaps_referent(iv, date(2020, 8, 13))     # +-1 day slack
    assert not RF.overlaps_referent(iv, date(2020, 8, 8)) and not RF.overlaps_referent(iv, date(2020, 8, 14))
    assert RF.blocked_referents([None, iv], [date(2020, 8, 11), date(2020, 9, 11)]) == [True, False]
    assert RF.blocked_referents([None], [date(2020, 8, 11)]) == [False]         # undated records cannot block


def test_local_day_uses_vienna_time():
    assert RF.local_day(pd.Timestamp('2022-08-05T22:30:00Z')) == date(2022, 8, 6)
    assert RF.local_midnight_utc(date(2022, 8, 6)) == pd.Timestamp('2022-08-05T22:00:00Z')
