"""wirkungskette_v02 tests: 2x2 counting, scenario choice, registered event selection and the report's internal
consistency. Synthetic frames below are unit-test fixtures only; they never enter data/ or reports/."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from preslide.terrain import INVERSE, PROJECT
from preslide.wirkungskette import gegenprobe as G
from preslide.wirkungskette.paths import config as config_v01

CFG = G.config()
EV = CFG['events']
DEM_UTC = pd.Timestamp(EV['dem_object_last_modified_utc'])
CX, CY = PROJECT.transform(15.49683, 47.44533)


# ---------- 2x2 counting ----------

def test_table_counts_each_cell():
    t = G.table_2x2([1, 1, 1, 0, 0, 1, 0], [1, 0, 1, 1, 0, 1, 0])
    assert t == {'schaden_ja_szenario_ja': 3, 'schaden_ja_szenario_nein': 1, 'schaden_nein_szenario_ja': 1,
                 'schaden_nein_szenario_nein': 2, 'n': 7}


@pytest.mark.parametrize('seed', range(20))
def test_table_cells_partition_rows_and_margins_match(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(1, 40))
    d, h = rng.integers(0, 2, n), rng.integers(0, 2, n)
    t = G.table_2x2(d, h)
    assert t['schaden_ja_szenario_ja'] + t['schaden_ja_szenario_nein'] + t['schaden_nein_szenario_ja'] + t['schaden_nein_szenario_nein'] == n
    assert t['schaden_ja_szenario_ja'] + t['schaden_ja_szenario_nein'] == int(d.sum())
    assert t['schaden_ja_szenario_ja'] + t['schaden_nein_szenario_ja'] == int(h.sum())


def test_table_is_not_symmetric_in_its_inputs():
    # damage ja / scenario nein must not be confused with damage nein / scenario ja
    t = G.table_2x2([1, 1, 0], [0, 0, 1])
    assert (t['schaden_ja_szenario_nein'], t['schaden_nein_szenario_ja']) == (2, 1)


@pytest.mark.parametrize('damage,hit', [([1, np.nan], [1, 0]), ([1, 0], [1]), ([2, 0], [1, 0]), ([1, 0], [1, -1]), ([[1, 0]], [[1, 0]])])
def test_table_refuses_missing_or_non_binary_values(damage, hit):
    with pytest.raises(ValueError):
        G.table_2x2(damage, hit)


def test_table_on_empty_set_is_all_zero():
    assert G.table_2x2([], [])['n'] == 0


# ---------- scenario choice and hit rule ----------

def _sc(sid, stop, road=0, building=0):
    return {'id': sid, 'stopp_index': stop, 'infrastruktur': {'strasse': {'anzahl': road}, 'gebaeude': {'anzahl': building},
                                                              'weg': {'anzahl': 0}, 'bahn': {'anzahl': 0}}}


def test_shortest_and_longest_follow_stop_index_not_config_order():
    sc = [_sc('reach_45m', 2), _sc('reach_467m', 15), _sc('energy_11deg', 0), _sc('energy_7deg', 30)]
    short, long_ = G.shortest_and_longest(sc)
    assert (short['id'], long_['id']) == ('energy_11deg', 'energy_7deg')


def test_present_needs_at_least_one_feature_of_a_listed_type():
    c = _sc('x', 0, road=0, building=3)['infrastruktur']
    assert not G.present(c, ['strasse'])
    assert G.present(c, ['gebaeude'])
    assert G.present(c, ['strasse', 'gebaeude'])


def test_tables_use_the_registered_scenario_per_event():
    rows = [{'schaden': {'Verkehrsanlagen': 1, 'Bauwerke': 0},
             'szenario': {'kuerzestes': _sc('a', 0, road=0), 'laengstes': _sc('b', 9, road=2)}}]
    t = G.tables(rows, CFG['comparison'])['verkehr_strasse']
    assert t['kuerzestes']['schaden_ja_szenario_nein'] == 1
    assert t['laengstes']['schaden_ja_szenario_ja'] == 1


# ---------- registered event selection ----------

def _offset_lonlat(dx_m):
    lon, lat = INVERSE.transform(CX + dx_m, CY)
    return float(lon), float(lat)


def _event(name, dx_m=1000.0, t0='2018-09-14T09:00:00Z', year=2018, verkehr=1.0, bau=0.0,
           group='Fliessen', qual='Lage relativ genau (20-100m)'):
    lon, lat = _offset_lonlat(dx_m)
    return {'nameOfEvent': name, 'lon': lon, 'lat': lat, 'Date_Anfan': pd.Timestamp(t0).value // 10 ** 6, 'EREIGNIS_J': float(year),
            'Verkehrsanlagen': verkehr, 'Bauwerke': bau, 'Prozessgruppe': group, 'QUAL_LAGE': qual}


def _select(rows, years=(2017, 2018)):
    return G.select_events(pd.DataFrame(rows), CX, CY, EV, DEM_UTC, list(years) if years is not None else None)


def test_selection_keeps_a_valid_event():
    sel, ex = _select([_event('ok')])
    assert list(sel.nameOfEvent) == ['ok'] and sum(ex.values()) == 0


@pytest.mark.parametrize('kwargs,reason', [
    ({'dx_m': 10_050.0}, 'ausserhalb_umkreis'),
    ({'verkehr': np.nan}, 'schadensdetail_leer'),
    ({'bau': np.nan}, 'schadensdetail_leer'),
    ({'t0': EV['dem_object_last_modified_utc']}, 'ereignis_nicht_nach_dem'),      # exactly at the DEM date: not after
    ({'t0': '2015-06-01T00:00:00Z', 'year': 2015}, 'ereignis_nicht_nach_dem'),
    ({'t0': '2016-07-25T09:00:00Z', 'year': 2016}, 'jahr_nicht_im_primaerset'),
    ({'group': 'Stuerzen'}, 'prozess_ausgeschlossen'),
    ({'qual': 'Lage ungenau (100-1000m)'}, 'lage_ungenauer_als_100m'),
    ({'qual': 'Lage sehr ungenau (>1000m)'}, 'lage_ungenauer_als_100m'),
    ({'qual': None}, 'lage_ungenauer_als_100m'),
])
def test_selection_excludes_and_counts_by_reason(kwargs, reason):
    sel, ex = _select([_event('ok'), _event('bad', **kwargs)])
    assert list(sel.nameOfEvent) == ['ok']
    assert ex[reason] == 1 and sum(ex.values()) == 1


def test_selection_boundaries_inside_radius_and_one_second_after_dem():
    t_after = (DEM_UTC + pd.Timedelta(seconds=1)).isoformat()
    sel, _ = _select([_event('edge', dx_m=9_990.0, t0=t_after, year=2016)], years=None)
    assert list(sel.nameOfEvent) == ['edge']


def test_distance_is_metric_not_degrees():
    sel, _ = _select([_event('a', dx_m=4_000.0)])
    assert sel.distance_m.iloc[0] == pytest.approx(4_000.0, abs=1.0)


def test_secondary_set_keeps_all_years_after_dem():
    rows = [_event('y2016', t0='2016-07-25T09:00:00Z', year=2016), _event('y2024', t0='2024-06-02T22:00:00Z', year=2024)]
    assert len(_select(rows)[0]) == 0
    assert sorted(_select(rows, years=None)[0].nameOfEvent) == ['y2016', 'y2024']


def test_selection_refuses_duplicate_ids_and_non_binary_damage():
    with pytest.raises(ValueError):
        _select([_event('dup'), _event('dup')])
    with pytest.raises(ValueError):
        _select([_event('x', verkehr=2.0)])


# ---------- registration ----------

def test_v01_scenarios_and_corridor_are_unchanged():
    rc = config_v01()['runout']
    assert [(s['id'], s.get('reach_m'), s.get('angle_deg')) for s in rc['scenarios']] == [
        ('reach_45m', 45, None), ('reach_467m', 467, None), ('energy_11deg', None, 11), ('energy_7deg', None, 7)]
    assert rc['corridor']['width_m'] == 50 and rc['energy_line']['v_max_m_s'] == 15
    assert set(config_v01()['infrastructure']['types']) == {'gebaeude', 'strasse', 'weg', 'bahn'}


def test_registration_names_twelve_tables_and_no_hit_rate():
    c = CFG['comparison']
    assert len(c['primary_tables']) == 2 and len(c['secondary_tables']) == 1
    assert any('hit rate' in x for x in CFG['not_claimed'])


def test_report_writer_refuses_paths_outside_its_root(monkeypatch):
    monkeypatch.setattr(G, 'REPORT', G.ROOT / 'reports/v04')
    with pytest.raises(RuntimeError):
        G.report_dir()


# ---------- committed report is internally consistent ----------

REPORT_JSON = Path('reports/wirkungskette_v02/gegenprobe.json')


@pytest.mark.skipif(not REPORT_JSON.exists(), reason='report not generated yet')
def test_report_tables_recount_from_its_rows():
    out = json.loads(REPORT_JSON.read_text(encoding='utf-8'))
    for name, st in out['sets'].items():
        assert st['ereignisse'] == len(st['zeilen'])
        assert len({r['id'] for r in st['zeilen']}) == len(st['zeilen'])
        assert st['tabellen'] == G.tables(st['zeilen'], CFG['comparison'])
        for r in st['zeilen']:
            stops = [s['laenge_m'] for s in r['alle_szenarien']]
            assert r['szenario']['kuerzestes']['laenge_m'] == min(stops)
            assert r['szenario']['laengstes']['laenge_m'] == max(stops)
            if name == 'primaer':
                assert r['jahr'] in EV['primary_years']
            assert pd.Timestamp(r['beginn_utc']) > DEM_UTC
            assert r['lage'] in EV['position_classes_allowed']
    primary = {r['id'] for r in out['sets']['primaer']['zeilen']}
    assert primary <= {r['id'] for r in out['sets']['sekundaer']['zeilen']}
