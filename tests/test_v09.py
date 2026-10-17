"""V0.9 safety tests: dates, process tokens, shifted t0, near-duplicates, unseen blocks, purge, units, write guard."""
import json
import subprocess
import sys
from datetime import date

import numpy as np
import pandas as pd
import pytest

from preslide.sources import ROOT
from preslide.terrain import PROJECT
from preslide.v04.weather import admissible
from preslide.v09 import audit, cohort, experiment
from preslide.v09.paths import guard
from preslide.v09.pipeline import validate_v09

TOKENS = ['Rutschung (klein|mittel|gross) \\(.*\\)', 'Erdstrom', 'Schuttstrom']
CFG = {'cohorts': {'kaernten': {'t0_shift_days': 3}}}


# ---------- Kärnten dates and process tokens ----------

@pytest.mark.parametrize('text, expected', [
    ('17.11.19 00:00:00,000000', date(2019, 11, 17)),
    ('01.10.93 00:00:00,000000', date(1993, 10, 1)),
    ('01.01.26 00:00:00,000000', date(2026, 1, 1)),      # pivot boundary: 26 -> 2026
    ('01.01.27 00:00:00,000000', date(1927, 1, 1)),      # 27 -> 1927
    ('31.02.19 00:00:00,000000', None),                  # impossible calendar day
    ('', None), (None, None), ('2019-11-17', None),
])
def test_two_digit_year_parser(text, expected):
    assert cohort.parse_ktn_day(text, 26) == expected


@pytest.mark.parametrize('value, ok', [
    ('Rutschung klein (bis 250m²)', True),
    ('Erdstrom; Rutschung mittel (bis 1000m²)', True),
    ('Rutschung gross (> 1000m²)', True),
    ('Schuttstrom', True),
    ('Erdstrom; Steinschlag (Sturzm. - 100m³)', False),   # mixed with rockfall
    ('Mure', False),                                       # ambiguous hillslope/torrent
    ('Erdfall', False), ('keine Angabe', False), ('', False), (None, False),
    ('Rutschung', False),                                  # no size class: not a registered token
])
def test_kaernten_process_tokens(value, ok):
    assert cohort.ktn_process_ok(value, TOKENS) is ok


def test_shifted_t0_is_local_midnight_three_days_before_in_both_seasons():
    assert cohort.shifted_t0(date(2019, 11, 17), 3) == ('2019-11-14', '2019-11-14T00:00:00+01:00', '2019-11-13T23:00:00Z')
    assert cohort.shifted_t0(date(2023, 8, 5), 3) == ('2023-08-02', '2023-08-02T00:00:00+02:00', '2023-08-01T22:00:00Z')


@pytest.mark.parametrize('days_late', [0, 1, 2, 3])
def test_shifted_t0_admits_no_hour_of_the_true_failure_day(days_late):
    """A record reported up to three days late: no admissible INCA hour lies on or after the true failure day."""
    reported = date(2023, 8, 5)
    true_start = pd.Timestamp(date.fromordinal(reported.toordinal() - days_late).isoformat(), tz='Europe/Vienna').tz_convert('UTC')
    t0 = pd.Timestamp(cohort.shifted_t0(reported, 3)[2])
    hours = pd.date_range(t0 - pd.Timedelta(days=61), t0 + pd.Timedelta(days=5), freq='h')
    used = hours[admissible(hours, t0, pd.Timedelta(days=60))]
    assert len(used) > 0 and (used + pd.Timedelta(hours=1) <= true_start).all()


# ---------- near duplicates (metric CRS) ----------

def metric(lon, lat):
    return np.array([PROJECT.transform(lon, lat)])


def test_near_in_time_uses_metres_and_days():
    lon, lat = 14.0, 47.0
    x, y = PROJECT.transform(lon, lat)
    ref = np.array([[x + 999.0, y], [x + 1001.0, y + 5000.0]])
    xy = np.array([[x, y]])
    assert cohort.near_in_time(xy, np.array([100]), ref, np.array([103, 100]), 1000, 3).tolist() == [True]
    assert cohort.near_in_time(xy, np.array([100]), ref, np.array([104, 100]), 1000, 3).tolist() == [False]
    assert cohort.near_in_time(xy, np.array([100]), ref[1:], np.array([100]), 1000, 3).tolist() == [False]


def test_epsg31287_distance_is_metric_not_degrees():
    a, b = metric(14.0, 47.0), metric(14.0, 47.01)          # 0.01 deg latitude ~ 1112 m
    assert 1100 < np.linalg.norm(a - b) < 1125


# ---------- unseen blocks ----------

def frame(rows):
    return pd.DataFrame(rows, columns=['event_id', 'event_day', 'x', 'y'])


def test_unseen_blocks_marks_same_episode_and_location_links():
    seen = frame([('S1', '2020-06-01', 0.0, 0.0)])
    new = frame([('N_same_episode', '2020-06-03', 200000.0, 0.0),      # 2 days later, far away: same Austria-wide episode
                 ('N_location', '2023-01-01', 1500.0, 0.0),           # other year, 1.5 km from a seen positive
                 ('N_free', '2021-09-01', 300000.0, 0.0)])            # unrelated
    out = cohort.unseen_blocks(seen, new, 2000).set_index('event_id').seen_block.to_dict()
    assert out == {'N_same_episode': True, 'N_location': True, 'N_free': False}


def test_unseen_blocks_chain_through_new_events():
    seen = frame([('S1', '2020-06-01', 0.0, 0.0)])
    new = frame([('N_bridge', '2020-06-04', 100000.0, 0.0), ('N_far', '2020-06-07', 400000.0, 0.0)])
    out = cohort.unseen_blocks(seen, new, 2000).set_index('event_id').seen_block
    assert out.all()                                                   # 3-day gaps chain both into the seen episode


# ---------- spatial purge and units ----------

def samples(gid, day, positive_xy, controls_xy):
    rows = [{'event_group_id': gid, 'event_day': day, 'x': positive_xy[0], 'y': positive_xy[1], 'label': 1}]
    rows += [{'event_group_id': gid, 'event_day': day, 'x': x, 'y': y, 'label': 0} for x, y in controls_xy]
    return pd.DataFrame(rows)


def test_seen_location_purge_is_positive_involving():
    v04 = samples('V04', '2020-01-01', (0, 0), [(5000, 0)] * 5)
    near_positive = samples('A', '2022-05-01', (900, 0), [(20000, 0)] * 5)          # positive 900 m from V0.4 positive
    near_control = samples('B', '2022-05-01', (50000, 0), [(5000, 900)] + [(60000, 0)] * 4)   # control-control 900 m
    far = samples('C', '2022-05-01', (100000, 0), [(110000, 0)] * 5)
    v09 = pd.concat([near_positive, near_control, far], ignore_index=True)
    assert experiment.seen_location_groups(v09, v04, 1000) == {'A'}


def test_seen_location_purge_rejects_shared_ids():
    a = samples('X', '2022-05-01', (0, 0), [(1, 1)] * 5)
    with pytest.raises(ValueError):
        experiment.seen_location_groups(a, a, 1000)


def test_unit_table_links_episode_and_keeps_single_groups():
    s = pd.concat([samples('A', '2022-05-01', (0, 0), [(3000, 0)] * 5),
                   samples('B', '2022-05-03', (300000, 0), [(303000, 0)] * 5),    # same episode -> same unit
                   samples('C', '2023-07-01', (600000, 0), [(603000, 0)] * 5)],   # alone
                  ignore_index=True)
    u = experiment.unit_table(s, 2000, 400).unit
    assert u['A'] == u['B'] and u['C'] != u['A'] and u.nunique() == 2


# ---------- V0.9 dataset invariants ----------

def group(cohort_name, reported, t0_utc, tq='day'):
    return pd.DataFrame({'event_group_id': ['G'] * 6, 'cohort': [cohort_name] * 6, 'reported_day': [reported] * 6,
                         't0_utc': [t0_utc] * 6, 'time_quality': [tq] * 6, 'label': [1, 0, 0, 0, 0, 0]})


def test_validate_v09_accepts_correct_t0_rules():
    assert validate_v09(group('kaernten', '2019-11-17', '2019-11-13T23:00:00Z'), CFG)['v09_checks'] == 'PASS'
    assert validate_v09(group('media', '2020-06-21', '2020-06-21T10:00:00Z', 'daypart'), CFG)['v09_checks'] == 'PASS'


@pytest.mark.parametrize('bad', [
    group('kaernten', '2019-11-17', '2019-11-16T23:00:00Z'),          # unshifted: reported-day midnight
    group('kaernten', '2019-11-17', '2019-11-14T23:00:00Z'),          # two days only
    group('kaernten', '2019-11-17', '2019-11-13T23:00:00Z', 'clock'),  # time quality must be 'day'
    group('media', '2020-06-21', '2020-06-22T10:00:00Z', 'daypart'),  # t0 after the reported day
])
def test_validate_v09_rejects_injected_bugs(bad):
    with pytest.raises(ValueError):
        validate_v09(bad, CFG)


# ---------- process audit ----------

def test_wilson_gate():
    cfg = {'process_audit': {'quality_gate': 'rule'}}
    assert audit.gate(['slide_confirmed'] * 20, cfg)['passes']
    assert 0.16 < audit.wilson_upper(0, 20) < 0.17
    assert not audit.gate(['slide_confirmed'] * 17 + ['other_process'] * 3, cfg)['passes']   # upper ~0.36
    assert not audit.gate(['slide_confirmed'] * 19 + ['not_found'] * 30, cfg)['passes']     # n < 20
    assert audit.gate(['slide_confirmed'] * 20 + ['ambiguous', 'not_found', 'date_conflict'], cfg)['n_verifiable'] == 20


def test_audit_validation_rejects_incomplete_or_unknown():
    cfg = {'process_audit': {'categories': {'slide_confirmed': '', 'not_found': '', 'other_process': ''}}}
    events = [{'event_id': 'a'}, {'event_id': 'b'}]
    good = [{'event_id': e, 'category': 'not_found', 'urls': [], 'publisher': None, 'publication_date': None,
             'retrieved_utc': 'x', 'paraphrase': 'x'} for e in ('a', 'b')]
    assert audit.validate(good, cfg, events)
    with pytest.raises(ValueError):
        audit.validate(good[:1], cfg, events)                                  # missing event
    with pytest.raises(ValueError):
        audit.validate([{**good[0], 'category': 'maybe'}, good[1]], cfg, events)
    with pytest.raises(ValueError):
        audit.validate([{**good[0], 'category': 'slide_confirmed'}, good[1]], cfg, events)   # evidence without URL


# ---------- write guard and binding ----------

def test_guard_refuses_v04_and_baseline_paths():
    for p in (ROOT / 'data/v04/cache/x', ROOT / 'reports/v04', ROOT / 'data/processed/x', ROOT / 'models/v04/y'):
        with pytest.raises(RuntimeError):
            guard(p)


def test_bound_v04_code_cannot_write_to_v04():
    """In a fresh interpreter: after bind(), V0.4 terrain writes go to data/v09 and a data/v04 write raises."""
    code = ("import json; from preslide.v09.bind import bind; from preslide.v04 import terrain, weather, context, http; bind();"
            "from preslide.v09 import http as h9; from preslide.sources import ROOT\n"
            "ok = str(terrain.CACHE).replace('\\\\', '/').endswith('data/v09/cache')\n"
            "same = weather.cached_json is h9.cached_json and context.cached_json is h9.cached_json and http.cached_json is h9.cached_json\n"
            "try:\n terrain.guard(ROOT / 'data/v04/cache/terrain'); refused = False\nexcept RuntimeError:\n refused = True\n"
            "print(json.dumps([ok, same, refused]))")
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert json.loads(out.stdout.strip().splitlines()[-1]) == [True, True, True], out.stderr
