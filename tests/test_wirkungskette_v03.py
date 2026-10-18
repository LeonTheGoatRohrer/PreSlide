"""wirkungskette_v03 tests: reference area, inventory exclusion, fixed-seed sampling, metrics, cluster/block resampling,
comparison bookkeeping and the report's internal consistency. Synthetic frames below are unit-test fixtures only; they
never enter data/ or reports/."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from preslide.wirkungskette import nullreferenz as N

CFG = N.config()
X0, Y0 = 560000.0, 390000.0           # EPSG:31287 metres inside Austria


def _cells(points, reason=''):
    return pd.DataFrame([{'kind': 'grid', 'row': i // 100, 'col': i % 100, 'x': x, 'y': y, 'reason': reason} for i, (x, y) in enumerate(points)])


# ---------- registration ----------

def test_amendment_is_recorded_and_used():
    ref = CFG['reference']
    assert ref['area_amended']['buffer_m'] == 2000
    assert set(ref['area_amended']['supersedes']) == {'area_centre', 'area_radius_rule'}
    assert CFG['amendments'][0]['id'] == 1 and 'No reference metric' in CFG['amendments'][0]['seen_before_amendment']
    assert ref['sample_size'] == 500 and ref['exclusion']['min_distance_m'] == 250


# ---------- area and eligibility ----------

def test_area_of_one_buffer_inside_the_window():
    g = N.area_geometry([X0], [Y0], 2000, X0, Y0, 10000)
    assert g['flaeche_km2'] == pytest.approx(math.pi * 4, rel=0.01)
    assert g['anteil_ausserhalb_fenster'] == pytest.approx(0, abs=1e-3)


def test_area_cut_by_window_edge():
    g = N.area_geometry([X0 + 10000], [Y0], 2000, X0, Y0, 10000)
    assert 0.4 < g['anteil_ausserhalb_fenster'] < 0.6


def test_buffer_boundary_is_inclusive():
    cells = _cells([(X0 + 2000.0, Y0), (X0 + 2000.5, Y0), (X0, Y0 + 1999.0)])
    out, counts = N.eligible(cells, [X0], [Y0], 2000, [X0 + 50000], [Y0], 250)
    assert sorted(out.x.round(1)) == [X0, X0 + 2000.0]
    assert counts == {'zellen_im_rahmen': 3, 'im_gebiet': 2, 'zu_nah_am_inventar': 0, 'zulaessig': 2}


def test_inventory_exclusion_boundary_and_any_point():
    cells = _cells([(X0 + 1000, Y0), (X0 + 1000, Y0 + 249.9), (X0 + 1000, Y0 + 250.0), (X0 - 1000, Y0 + 100)])
    inv_x, inv_y = [X0 + 1000, X0 - 1000], [Y0, Y0]      # second inventory point excludes the fourth cell
    out, counts = N.eligible(cells, [X0], [Y0], 2000, inv_x, inv_y, 250)
    assert list(out.y.round(1)) == [Y0 + 250.0]
    assert counts['zu_nah_am_inventar'] == 3
    assert (out.inventar_abstand_m >= 250).all()


def test_eligibility_refuses_degrees_and_empty_inventory():
    cells = _cells([(X0, Y0)])
    with pytest.raises(Exception):
        N.eligible(cells, [X0], [Y0], 2000, [15.5], [47.4], 250)          # lon/lat instead of metres
    with pytest.raises(ValueError):
        N.eligible(cells, [X0], [Y0], 2000, [], [], 250)


@pytest.mark.parametrize('frame,n', [('bewertbar', 2), ('alle_rasterzellen', 3)])
def test_frames(frame, n):
    cells = pd.concat([_cells([(X0, Y0), (X0 + 90, Y0)]), _cells([(X0 + 180, Y0)], 'slope_below_minimum')])
    cells.loc[cells.index[-1], 'row'] = 9
    cells = pd.concat([cells, pd.DataFrame([{'kind': 'event', 'row': 5, 'col': 5, 'x': X0, 'y': Y0, 'reason': ''}])])
    assert len(N.frame_cells(cells, frame)) == n
    with pytest.raises(ValueError):
        N.frame_cells(cells, 'zufall')


# ---------- sampling and blocks ----------

def _grid(n):
    return pd.DataFrame({'row': np.arange(n) // 50, 'col': np.arange(n) % 50, 'x': X0 + np.arange(n) * 90.0, 'y': Y0})


def test_sample_is_deterministic_and_order_invariant():
    g = _grid(400)
    a = N.sample(g, 50, 7)
    b = N.sample(g.sample(frac=1, random_state=3), 50, 7)
    assert a[['row', 'col']].equals(b[['row', 'col']])
    assert not a[['row', 'col']].duplicated().any() and len(a) == 50
    assert not a[['row', 'col']].equals(N.sample(g, 50, 8)[['row', 'col']])


def test_sample_takes_all_when_too_few_and_refuses_duplicates():
    assert len(N.sample(_grid(30), 50, 1)) == 30
    g = _grid(10)
    with pytest.raises(ValueError):
        N.sample(pd.concat([g, g.head(1)]), 5, 1)


def test_block_boundaries_are_one_km():
    ids = N.block_id([560999.9, 561000.0, 560000.0], [390000.0, 390000.0, 390999.9])
    assert ids == ['560_390', '561_390', '560_390']


# ---------- metrics ----------

def _row(road_short=0, road_long=0, bld_short=0, bld_long=0, d_road=100.0, d_bld=100.0, v=1, b=0, unit='A'):
    def inf(r, g):
        return {'strasse': {'anzahl': r}, 'gebaeude': {'anzahl': g}, 'weg': {'anzahl': 0}, 'bahn': {'anzahl': 0}}
    return {'szenario': {'kuerzestes': {'infrastruktur': inf(road_short, bld_short)}, 'laengstes': {'infrastruktur': inf(road_long, bld_long)}},
            'naechstes_objekt_m': {'strasse': d_road, 'gebaeude': d_bld}, 'schaden': {'Verkehrsanlagen': v, 'Bauwerke': b}, 'einheit': unit}


def test_metrics_separate_shortest_longest_and_point():
    m = N.point_metrics(_row(road_long=2, bld_short=1, bld_long=1, d_road=25.0, d_bld=25.1), 25.0)
    assert m == {'strasse_kuerzestes': 0, 'strasse_laengstes': 1, 'strasse_am_punkt': 1,
                 'gebaeude_kuerzestes': 1, 'gebaeude_laengstes': 1, 'gebaeude_am_punkt': 0}


def test_group_mask():
    rows = [_row(v=1, b=0), _row(v=0, b=1), _row(v=1, b=1)]
    assert N.group_mask(rows, 'verkehr_1') == [True, False, True]
    assert N.group_mask(rows, 'bauwerke_1') == [False, True, True]
    assert N.group_mask(rows, 'alle') == [True, True, True]


# ---------- resampling ----------

def test_exact_cluster_bootstrap_pools_hits_per_unit():
    hits = [1] * 10 + [0]
    units = ['A'] * 10 + ['B']
    shares = sorted(N.cluster_bootstrap_exact(hits, units))
    assert len(shares) == 4
    assert shares == pytest.approx([0.0, 10 / 11, 10 / 11, 1.0])
    iv = N.cluster_interval(hits, units)
    assert iv['einheiten'] == 2 and iv['intervall_95'] == [0.0, 1.0] and iv['min_max'] == [0.0, 1.0]


def test_cluster_bootstrap_has_k_to_the_k_resamples_and_collapses_when_all_units_agree():
    units = ['A'] * 14 + ['B'] * 9 + ['C']
    iv = N.cluster_interval([1] * 24, units)
    assert iv['resamples'] == 27 and iv['intervall_95'] == [1.0, 1.0]


def test_cluster_bootstrap_refuses_too_many_units_and_missing_values():
    with pytest.raises(ValueError):
        N.cluster_bootstrap_exact([1] * 8, list('ABCDEFGH'))
    with pytest.raises(ValueError):
        N.cluster_bootstrap_exact([1, np.nan], ['A', 'B'])
    with pytest.raises(ValueError):
        N.cluster_bootstrap_exact([1, 0], ['A'])


def test_weighted_quantile_is_inverted_cdf():
    assert N.weighted_quantile([3, 1, 2], [1, 1, 2], 0.25) == 1
    assert N.weighted_quantile([3, 1, 2], [1, 1, 2], 0.26) == 2
    assert N.weighted_quantile([3, 1, 2], [1, 1, 2], 0.975) == 3


def test_block_draws_respect_blocks_and_seed():
    hits, blocks = [1, 1, 0, 0], ['a', 'a', 'b', 'b']
    d1 = N.block_draws(hits, blocks, 500, np.random.default_rng(1))
    d2 = N.block_draws(hits, blocks, 500, np.random.default_rng(1))
    assert np.array_equal(d1, d2)
    assert set(np.round(d1, 3)) <= {0.0, 0.5, 1.0}      # whole blocks, never single rows
    assert np.allclose(N.block_draws([1, 0, 1, 0], ['a', 'a', 'b', 'b'], 100, np.random.default_rng(2)), 0.5)


@pytest.mark.parametrize('iv,text', [([0.01, 0.3], 'über der Nullreferenz'), ([-0.3, -0.01], 'unter der Nullreferenz'),
                                     ([0.0, 0.3], 'nicht von der Nullreferenz unterscheidbar'), ([-0.1, 0.1], 'nicht von der Nullreferenz unterscheidbar')])
def test_wording_needs_interval_excluding_zero(iv, text):
    assert N.wording(iv) == text


def _synthetic_comparisons():
    events = [{**_row(road_long=1, d_road=10.0, v=1, b=int(i < 2), unit=u, bld_long=int(i < 2)), 'metriken': None}
              for i, u in enumerate('AABBC')]
    events.append({**_row(v=0, b=0, unit='C'), 'metriken': None})
    for e in events:
        e['metriken'] = N.point_metrics(e, 25.0)
    refs = []
    for i in range(40):
        r = _row(road_long=int(i % 2 == 0), d_road=10.0 if i % 4 == 0 else 200.0)
        refs.append({**r, 'metriken': N.point_metrics(r, 25.0), 'block': f'b{i % 5}'})
    return events, {'bewertbar': refs, 'alle_rasterzellen': refs[:30]}


def test_comparisons_are_registered_set_with_correct_groups():
    events, frames = _synthetic_comparisons()
    out = N.comparisons(events, frames, CFG)
    assert len(out) == CFG['comparisons']['comparisons_counted'] == 24
    prim = [c for c in out if c['rang'] == 'primaer']
    assert len(prim) == 6 and all(c['rahmen'] == 'bewertbar' for c in prim)
    assert all((c['gruppe'] == 'verkehr_1') == c['metrik'].startswith('strasse') for c in prim)
    by = {(c['rahmen'], c['gruppe'], c['metrik']): c for c in out}
    c = by[('bewertbar', 'verkehr_1', 'strasse_laengstes')]
    assert (c['ereignisse']['treffer'], c['ereignisse']['n']) == (5, 5)
    assert (c['referenz']['treffer'], c['referenz']['n'], c['referenz']['bloecke']) == (20, 40, 5)
    assert c['differenz'] == pytest.approx(0.5)
    assert by[('bewertbar', 'bauwerke_1', 'gebaeude_laengstes')]['ereignisse']['n'] == 2
    assert by[('alle_rasterzellen', 'alle', 'strasse_laengstes')]['ereignisse']['n'] == 6
    assert by[('alle_rasterzellen', 'alle', 'strasse_laengstes')]['referenz']['n'] == 30
    assert N.comparisons(events, frames, CFG) == out                       # fixed seeds


def test_check_against_v02_detects_drift():
    row = {'id': 'E1', **_row()}
    v02 = {'identitaet': {'konfiguration_v01_sha256': N.config_sha()}, 'sets': {'primaer': {'zeilen': [json.loads(json.dumps(row))]}}}
    N.check_against_v02([row], v02)
    changed = json.loads(json.dumps(row))
    changed['naechstes_objekt_m']['strasse'] = 30.0
    with pytest.raises(ValueError):
        N.check_against_v02([changed], v02)
    with pytest.raises(ValueError):
        N.check_against_v02([{**row, 'id': 'E2'}], v02)
    with pytest.raises(ValueError):
        N.check_against_v02([row], {**v02, 'identitaet': {'konfiguration_v01_sha256': '0' * 64}})


@pytest.mark.parametrize('target', ['outside', 'wrong_name'])
def test_report_dir_guard(monkeypatch, tmp_path, target):
    path = tmp_path / 'reports/wirkungskette_v03' if target == 'outside' else N.ROOT / 'reports/wirkungskette_v02'
    monkeypatch.setattr(N, 'REPORT', path)
    with pytest.raises(RuntimeError):
        N.report_dir()


# ---------- produced report (data-dependent; skipped when the report is absent) ----------

REPORT_JSON = Path('reports/wirkungskette_v03/nullreferenz.json')


@pytest.fixture(scope='module')
def report():
    if not REPORT_JSON.exists():
        pytest.skip('nullreferenz.json fehlt')
    return json.loads(REPORT_JSON.read_text(encoding='utf-8'))


def test_report_counts_match_rows(report):
    ev = report['ereignisse']['zeilen']
    for c in report['vergleiche']:
        refs = report['referenz_zeilen'][c['rahmen']]
        assert c['referenz']['treffer'] == sum(r['metriken'][c['metrik']] for r in refs)
        assert c['referenz']['n'] == len(refs)
        sub = [e for e, m in zip(ev, N.group_mask(ev, c['gruppe'])) if m]
        assert c['ereignisse']['treffer'] == sum(e['metriken'][c['metrik']] for e in sub)
        lo, hi = c['ereignisse']['intervall_95']
        assert c['ereignisse']['min_max'][0] <= lo <= hi <= c['ereignisse']['min_max'][1]


def test_report_reproduces_v02_numbers(report):
    by = {(c['rahmen'], c['gruppe'], c['metrik']): c['ereignisse'] for c in report['vergleiche']}
    assert (by[('bewertbar', 'verkehr_1', 'strasse_laengstes')]['treffer'], by[('bewertbar', 'verkehr_1', 'strasse_laengstes')]['n']) == (22, 22)
    assert by[('bewertbar', 'verkehr_1', 'strasse_am_punkt')]['treffer'] == 20
    assert by[('bewertbar', 'verkehr_1', 'strasse_kuerzestes')]['treffer'] == 21
    assert by[('bewertbar', 'bauwerke_1', 'gebaeude_laengstes')]['treffer'] == 6
    assert report['ereignisse']['n'] == 24 and len(report['ereignisse']['einheiten']) == 3


def test_reference_points_respect_registration(report):
    for fid, rows in report['referenz_zeilen'].items():
        assert len(rows) == CFG['reference']['sample_size']
        assert len({(r['row'], r['col']) for r in rows}) == len(rows)
        assert all(r['inventar_abstand_m'] >= CFG['reference']['exclusion']['min_distance_m'] for r in rows)
        if fid == 'bewertbar':
            assert all(r['grund'] == '' for r in rows)


def test_report_text_has_no_banned_words_and_is_exploratory():
    md = Path('reports/wirkungskette_v03/nullreferenz.md')
    if not md.exists():
        pytest.skip('nullreferenz.md fehlt')
    text = md.read_text(encoding='utf-8')
    assert not N.core.BANNED.findall(text)
    assert 'Explorativ' in text and 'Keine Trefferquote' in text
