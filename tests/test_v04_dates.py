"""V0.4 date/time parser: day known vs. time lower bound, never a t0 after the event."""
import pandas as pd
import pytest

from preslide.v04.dates import classify_date

TZ = 'Europe/Vienna'


def record(text, day, start=None, end=None):
    s = pd.Timestamp(start or f'{day} 00:00', tz=TZ)
    e = pd.Timestamp(end or f'{day} 23:59:59', tz=TZ)
    y, m, d = map(int, day.split('-'))
    return {'processTimeOrPeriodInfo': text, 'Ereignisdatum_validFrom': day, 'EREIGNIS_J': y, 'EREIGNIS_M': m,
            'EREIGNIS_T': d, 'Date_Anfan': int(s.value // 10**6), 'Date_End_a': int(e.value // 10**6)}


@pytest.mark.parametrize('text,day,t0,quality', [
    ('25.07.2016, frueher Nachmittag', '2016-07-25', '2016-07-25T12:00', 'daypart'),
    ('22. August 2020, abends', '2020-08-22', '2020-08-22T17:00', 'daypart'),
    ('14.09.18 (Nachmittag, Abend)', '2018-09-14', '2018-09-14T12:00', 'daypart'),
    ('lt. Anwohner Abgang So 15.09.2024 Mittag', '2024-09-15', '2024-09-15T11:00', 'daypart'),
    ('04. August 2023 (zwischen spaetem Vormittag und fruehem Nachmittag)', '2023-08-04', '2023-08-04T06:00', 'daypart'),
    ('22. August 2020, ca. 22:00', '2020-08-22', '2020-08-22T21:00', 'clock'),
    ('19. August 2022 (zwischen ca. 14:30 Uhr und 22:30 Uhr)', '2022-08-19', '2022-08-19T13:00', 'clock'),
    ('17.07.2024, nachts ab 02:00', '2024-07-17', '2024-07-17T01:00', 'clock'),
    ('Ereignis zwischen 8-9 Uhr am 5. August 2023', '2023-08-05', '2023-08-05T07:00', 'clock'),
    ('lt. Anwohner Abgang Mo 16.09.2024, gegen 10h', '2024-09-16', '2024-09-16T09:00', 'clock'),
    ('16. Mai 2023 (spaeter Nachmittag gegen 17:40 Uhr)', '2023-05-16', '2023-05-16T12:00', 'daypart'),
    # Upper bounds and alarm/rain times never move t0 later than midnight.
    ('21. Mai 2024 (vor 18:26, dem Zeitpunkt der Alarmierung der Feuerwehr)', '2024-05-21', '2024-05-21T00:00', 'day'),
    ('02. August 2024 (gegen 18:21 Uhr, dem Zeitpunkt der Alarmierung zu Unwettereinsaetzen)', '2024-08-02', '2024-08-02T00:00', 'day'),
    ('21. Juni 2023 (Starkregen gegen 17:00 Uhr)', '2023-06-21', '2023-06-21T00:00', 'day'),
    ('bemerkt am 04.08.2023 13:00 - 15:00', '2023-08-04', '2023-08-04T00:00', 'day'),
    ('24. August 2023 (spaetestens Abend)', '2023-08-24', '2023-08-24T00:00', 'day'),
    ('lt. Anwohner Abgang Mo 16.09.2024 Frueh - Vormittag', '2024-09-16', '2024-09-16T00:00', 'day'),
    ('17.07.2024, ca. 01:00', '2024-07-17', '2024-07-17T00:00', 'day'),
    ('17. November 2019', '2019-11-17', '2019-11-17T00:00', 'day'),
    ('09. Oktober 2024 (in der Frueh)', '2024-10-09', '2024-10-09T00:00', 'day'),
])
def test_day_known_and_conservative_t0(text, day, t0, quality):
    # Late provider start so that only the narrative bound is tested here.
    r = classify_date(record(text, day, start=f'{day} 23:00'))
    assert r['date_tier'] == 'A_narrative_day' and r['event_day'] == day
    assert r['t0_local'][:16] == t0 and r['time_quality'] == quality


def test_structured_start_caps_t0():
    # The provider's own interval start is earlier than the text bound: use the earlier one.
    r = classify_date(record('25.07.2016, frueher Nachmittag', '2016-07-25', start='2016-07-25 10:30'))
    assert r['t0_local'][:16] == '2016-07-25T10:00'


@pytest.mark.parametrize('text,day,reason', [
    ('12. oder 13. Juni 2018', '2018-06-13', 'uncertain_wording'),
    ('24.07.2016 (Nacht, ev. auch am 25.07.2016)', '2016-07-25', 'uncertain_wording'),
    ('25.07.2016 (frueher Nachmittag) und/oder aelter?', '2016-07-25', 'uncertain_wording'),
    ('08. Juni 2024 (Abend od. Nacht)', '2024-06-08', 'uncertain_wording'),
    ('05.08.2023 ca. 05:45 (Anwohnerinfo); Online-Datum Kleine Zeitung: 06.08.2023', '2023-08-05', 'narrative_day_missing_multiple_or_conflicting'),
    ('16.07.2016', '2016-07-25', 'narrative_day_missing_multiple_or_conflicting'),
    ('sp�ter Nachmittag 29. Juni 2026', '2026-06-29', 'uncertain_wording'),
])
def test_uncertain_or_conflicting_excluded(text, day, reason):
    r = classify_date(record(text, day))
    assert r['date_tier'] == 'excluded' and r['date_reason'] == reason and r['t0_local'] is None


def test_two_day_and_structured_only_are_separate_tiers():
    assert classify_date(record('16./17.07.2024 nachts', '2024-07-17', '2024-07-16 22:00', '2024-07-17 06:00'))['date_tier'] == 'B_two_day_window'
    assert classify_date(record('In der Nacht vom 4. auf den 5.08.2023', '2023-08-05'))['date_tier'] == 'B_two_day_window'
    r = classify_date(record(None, '2024-06-08'))
    assert r['date_tier'] == 'C_structured_day_only' and r['t0_local'] is None


def test_interval_longer_than_day_excluded():
    r = classify_date(record('05. August 2017', '2017-08-05', '2017-08-04 00:00', '2017-08-05 23:59:59'))
    assert r['date_tier'] == 'excluded'


def test_month_level_and_conflicting_fields():
    assert classify_date(record('grossregionales Ereignis Okt. 2018 - sicher', '2018-10-30'))['date_reason'] == 'month_level_text'
    bad = record('05. August 2017', '2017-08-05')
    bad['EREIGNIS_T'] = 6
    assert classify_date(bad)['date_reason'] == 'conflicting_structured_fields'


def test_t0_never_after_text_or_structured_start():
    for text, day in [('22. August 2020, ca. 22:00', '2020-08-22'), ('25.07.2016, frueher Nachmittag', '2016-07-25')]:
        a = record(text, day)
        r = classify_date(a)
        start = pd.Timestamp(a['Date_Anfan'], unit='ms', tz='UTC')
        assert pd.Timestamp(r['t0_local']) <= start
