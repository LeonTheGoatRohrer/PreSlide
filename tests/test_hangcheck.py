"""hangcheck_v01 safety tests: frozen model and column order, relative classes, separated review points (metres),
no weather/switch input, determinism, Austria/radius limits, offline municipality search. Synthetic data only in tests."""
import ast
import math

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from preslide.hangcheck import core, gemeinden
from preslide.hangcheck.paths import config, DATA, guard
from preslide.sources import ROOT
from preslide.terrain import PROJECT
from preslide.v04.models import STATIC, LC_CLASSES, GEO_CLASSES
from preslide.wirkungskette.core import banned_words

CFG = config()
HAS_MODEL = (ROOT / CFG['model']['bundle']).exists()
HAS_LAU = (ROOT / CFG['municipalities']['source']).exists() or (DATA / 'gemeinden.json').exists()
HAS_TILES = (ROOT / 'data/raw/terrain/N47E010.hgt').exists()
needs_model = pytest.mark.skipif(not HAS_MODEL, reason='data-dependent: V0.4 model bundle missing (worktree without data junction)')
needs_lau = pytest.mark.skipif(not HAS_LAU, reason='data-dependent: GISCO LAU file missing')
needs_area = pytest.mark.skipif(not (HAS_MODEL and HAS_TILES), reason='data-dependent: model or DEM tile cache missing')
STANZ = CFG['examples'][0]


@pytest.fixture(scope='module')
def client():
    from preslide.api import app
    return TestClient(app)


# ---------- 1/2: frozen model and exact column list ----------

def test_model_hash_mismatch_stops():
    core.check_model_sha('a' * 64, 'a' * 64)
    with pytest.raises(RuntimeError, match='SHA-256'):
        core.check_model_sha('b' * 64, 'a' * 64)


@needs_model
def test_frozen_model_loads_and_wrong_registered_hash_is_refused(monkeypatch):
    from preslide.hangcheck import build
    build.model_bundle.cache_clear()
    assert list(build.model_bundle()['columns']) == list(STATIC)
    bad = {**CFG, 'model': {**CFG['model'], 'bundle_sha256': '0' * 64}}
    monkeypatch.setattr(build, 'config', lambda: bad)
    build.model_bundle.cache_clear()
    with pytest.raises(RuntimeError, match='SHA-256'):
        build.model_bundle()
    monkeypatch.undo()
    build.model_bundle.cache_clear()


def test_columns_must_equal_static_in_order():
    core.check_model_columns(list(STATIC))
    swapped = list(STATIC)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    for bad in (swapped, STATIC[:-1], list(STATIC) + ['rain_sum_3d']):
        with pytest.raises(RuntimeError, match='STATIC'):
            core.check_model_columns(bad)


@needs_model
def test_scoring_refuses_missing_column_and_nan():
    from preslide.hangcheck import build
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(rng.normal(size=(5, len(STATIC))), columns=STATIC)
    score, z = build.score_rows(frame)
    assert score.shape == (5,) and np.isfinite(score).all()
    with pytest.raises(KeyError):
        build.score_rows(frame.drop(columns='twi'))
    frame.loc[2, 'slope'] = np.nan
    with pytest.raises(ValueError, match='NaN'):
        build.score_rows(frame)


def test_plain_language_labels_cover_every_model_column():
    assert set(core.LAND_COVER_DE) == set(LC_CLASSES) and set(core.GEOLOGY_DE) == set(GEO_CLASSES)
    for c in STATIC:
        assert core.feature_label(c, 1.0) and core.feature_label(c, 0.0)
    assert not banned_words([core.FEATURE_DE, core.LAND_COVER_DE, core.GEOLOGY_DE, core.REASON_DE])


# ---------- 3: relative classes ----------

def test_class_shares_are_5_and_15_percent():
    score = np.random.default_rng(1).normal(size=2000)
    cls = core.classes(score, CFG)
    assert (cls == 1).sum() == 100 and (cls == 2).sum() == 300 and (cls == 3).sum() == 1600
    assert score[cls == 1].min() > score[cls == 2].max() > score[cls == 3].max()


def test_equal_scores_keep_equal_class():
    score = np.concatenate([np.full(30, 5.0), np.linspace(-3, 3, 170)])   # 30 tied at the top: more than 5 % of 200
    cls = core.classes(score, CFG)
    assert set(cls[:30]) == {1}
    rng = np.random.default_rng(2)
    score = rng.integers(0, 6, 500).astype(float)                          # heavy ties everywhere
    cls = core.classes(score, CFG)
    assert pd.Series(cls).groupby(score).nunique().max() == 1


def test_too_few_assessable_cells_is_an_error_not_a_result():
    n = CFG['area']['minimum_assessable_cells']
    core.classes(np.arange(n, dtype=float), CFG)
    with pytest.raises(ValueError, match='Zu wenige'):
        core.classes(np.arange(n - 1, dtype=float), CFG)
    with pytest.raises(ValueError, match='NaN'):
        core.classes(np.r_[np.arange(n, dtype=float), np.nan], CFG)


# ---------- 4: review points in projected metres ----------

def test_review_points_are_class_1_and_at_least_300_m_apart():
    rng = np.random.default_rng(4)
    cx, cy = PROJECT.transform(10.5617, 47.1478)
    x, y = cx + rng.uniform(-2000, 2000, 1500), cy + rng.uniform(-2000, 2000, 1500)
    x[:40], y[:40] = cx + rng.uniform(0, 200, 40), cy + rng.uniform(0, 200, 40)  # a dense top cluster
    score = rng.normal(size=1500)
    score[:40] += 10
    cls = core.classes(score, CFG)
    idx = core.review_points(x, y, score, cls, CFG)
    assert 1 <= len(idx) <= CFG['review_points']['count'] and (cls[idx] == 1).all()
    assert idx[0] == int(np.argmax(score))
    sep = CFG['review_points']['separation_m']
    for i in range(len(idx)):
        for j in range(i):
            assert math.hypot(x[idx[i]] - x[idx[j]], y[idx[i]] - y[idx[j]]) >= sep


def test_review_points_come_only_from_class_1():
    # All 75 Prüfstufe-1 cells (5 % of 1500) lie in one 200 m square: only one separated point exists.
    rng = np.random.default_rng(5)
    cx, cy = PROJECT.transform(13.11, 47.11)
    x, y = cx + rng.uniform(-2000, 2000, 1500), cy + rng.uniform(-2000, 2000, 1500)
    x[:75], y[:75] = cx + rng.uniform(0, 200, 75), cy + rng.uniform(0, 200, 75)
    score = rng.normal(size=1500)
    score[:75] += 10
    cls = core.classes(score, CFG)
    assert (cls[:75] == 1).all() and (cls == 1).sum() == 75
    assert len(core.review_points(x, y, score, cls, CFG)) == 1


def test_review_points_refuse_degree_coordinates():
    score = np.linspace(0, 1, 200)
    cls = core.classes(score, CFG)
    with pytest.raises(ValueError, match='Grad'):
        core.review_points(np.linspace(10.5, 10.6, 200), np.linspace(47.1, 47.2, 200), score, cls, CFG)


# ---------- 5: no weather / switch input, determinism ----------

def test_hangcheck_code_has_no_weather_input():
    for path in (ROOT / 'preslide/hangcheck').glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        imported = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imported += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        weather = {'weather', 'rain', 'inca', 'spartacus', 'snowgrid', 'extremwetter'}   # module path parts (not 'terrain')
        assert not [m for m in imported if weather & set(m.split('.'))], path.name


def test_api_refuses_weather_or_switch_parameters(client):
    base = {'longitude': STANZ['longitude'], 'latitude': STANZ['latitude'], 'radius_m': 2000}
    for extra in ({'starkregen': True}, {'regen_mm': 80}, {'weather': {}}):
        r = client.post('/api/hangcheck', json={**base, **extra})
        assert r.status_code == 422, extra
    r = client.post('/api/hangcheck?starkregen=1', json=base)
    assert r.status_code == 422 and 'Wetter' in r.json()['detail']
    fields = client.app.openapi()['components']['schemas']['PlaceRequest']['properties']
    assert set(fields) == {'longitude', 'latitude', 'radius_m'}


@needs_area
def test_same_place_twice_gives_identical_result_and_fresh_compute_matches(client):
    from preslide.hangcheck import build
    body = {'longitude': STANZ['longitude'], 'latitude': STANZ['latitude'], 'radius_m': STANZ['radius_m']}
    a, b = client.post('/api/hangcheck', json=body), client.post('/api/hangcheck', json=body)
    assert a.status_code == 200 and a.json() == b.json()
    fresh = build._compute(body['longitude'], body['latitude'], float(body['radius_m']), config())
    import json
    assert json.loads(json.dumps(fresh)) == a.json()
    r = a.json()
    assert not banned_words(r)
    z = r['zaehlung']
    assert z['bewertet'] + sum(e['anzahl'] for e in z['ausgeschlossen']) == z['zellen']
    assert sum(z['stufen'].values()) == z['bewertet']
    assert len(r['zellen']['features']) == z['stufen']['Prüfstufe 1'] + z['stufen']['Prüfstufe 2']
    pts = r['pruefpunkte']
    assert 1 <= len(pts) <= 5
    xy = np.column_stack(PROJECT.transform([p['longitude'] for p in pts], [p['latitude'] for p in pts]))
    for i in range(len(xy)):
        for j in range(i):
            assert np.hypot(*(xy[i] - xy[j])) >= 300 - 1      # rounding of the returned coordinates
    assert r['modell']['bundle_sha256'] == CFG['model']['bundle_sha256']


# ---------- 6: limits ----------

def test_outside_austria_and_radius_limits_give_422(client):
    for lon, lat in ((11.576, 48.137), (12.5, 45.0), (16.6, 49.3)):   # Munich, Adriatic, Czechia
        r = client.post('/api/hangcheck', json={'longitude': lon, 'latitude': lat, 'radius_m': 2000})
        assert r.status_code == 422, (lon, lat)
    r = client.post('/api/hangcheck', json={'longitude': 11.576, 'latitude': 48.137, 'radius_m': 2000})
    assert 'außerhalb Österreichs' in r.json()['detail']
    for radius in (500, 999, 3500, 1250, -1000):
        r = client.post('/api/hangcheck', json={'longitude': STANZ['longitude'], 'latitude': STANZ['latitude'], 'radius_m': radius})
        assert r.status_code == 422 and 'Radius' in r.json()['detail'], radius


def test_write_guard_stays_in_namespace():
    guard(DATA / 'cache')
    for bad in (ROOT / 'data/v04', ROOT / 'reports/v04', ROOT / 'data/hangmap_v01'):
        with pytest.raises(RuntimeError):
            guard(bad)


# ---------- 7: municipality search ----------

SYNTH = [{'kennziffer': k, 'name': n, 'bundesland': b, 'einwohner_2021': p, 'longitude': 13.0, 'latitude': 47.5}
         for k, n, b, p in (('30001', 'Mühldorf', 'Niederösterreich', 1500), ('20601', 'Mühldorf', 'Kärnten', 900),
                            ('70801', 'Sankt Anton am Arlberg', 'Tirol', 2500), ('50101', 'Großgmain', 'Salzburg', 2600),
                            ('70802', 'Anras', 'Tirol', 1200))]


def test_search_folds_umlauts_case_and_eszett():
    for q in ('mühldorf', 'MÜHLDORF', 'muehldorf', 'Muhldorf', 'mühl'):
        hits = gemeinden.search(q, SYNTH, 10)
        assert [h['bundesland'] for h in hits] == ['Niederösterreich', 'Kärnten'], q   # same name: state + population
        assert hits[0]['anzeige'] == 'Mühldorf (Niederösterreich)'
    assert gemeinden.search('grossgmain', SYNTH, 10)[0]['name'] == 'Großgmain'
    assert [h['name'] for h in gemeinden.search('an', SYNTH, 10)] == ['Anras', 'Sankt Anton am Arlberg']  # prefix before word prefix
    assert gemeinden.search('a', SYNTH, 10) == []
    assert gemeinden.search('xyz', SYNTH, 10) == []


def test_representative_point_lies_inside_a_concave_municipality():
    u_shape = [[[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3], [0, 0]]]
    feature = {'properties': {'CNTR_CODE': 'AT', 'LAU_ID': '70001', 'LAU_NAME': 'U', 'POP_2021': 10.0},
               'geometry': {'type': 'Polygon', 'coordinates': u_shape}}
    other = {'properties': {'CNTR_CODE': 'DE', 'LAU_ID': '1', 'LAU_NAME': 'X'}, 'geometry': {'type': 'Polygon', 'coordinates': u_shape}}
    from shapely.geometry import Point, shape
    entries = gemeinden.entries_from_geojson([feature, other], CFG)
    assert len(entries) == 1 and entries[0]['bundesland'] == 'Tirol'
    poly = shape(feature['geometry'])
    assert not poly.contains(poly.centroid) and poly.contains(Point(entries[0]['longitude'], entries[0]['latitude']))


@needs_lau
def test_real_municipalities_states_duplicates_and_all_in_austria():
    from preslide.hangmap.build import inside_austria
    entries = gemeinden.municipalities()
    assert len(entries) == 2095 and len({e['kennziffer'] for e in entries}) == len(entries)
    assert inside_austria(np.array([e['longitude'] for e in entries]), np.array([e['latitude'] for e in entries])).all()
    capitals = {'Eisenstadt': 'Burgenland', 'Klagenfurt am Wörthersee': 'Kärnten', 'St. Pölten': 'Niederösterreich', 'Linz': 'Oberösterreich',
                'Salzburg': 'Salzburg', 'Graz': 'Steiermark', 'Innsbruck': 'Tirol', 'Bregenz': 'Vorarlberg', 'Wien': 'Wien'}
    for name, state in capitals.items():
        hit = [e for e in entries if e['name'] == name]
        assert len(hit) == 1 and hit[0]['bundesland'] == state, name
    for name in ('Mühldorf', 'Krumbach', 'Warth'):
        hits = [h for h in gemeinden.search(name) if h['name'] == name]
        assert len(hits) == 2 and len({h['anzeige'] for h in hits}) == 2, name
    assert gemeinden.search('LANDECK')[0]['name'] == 'Landeck'
    assert len(gemeinden.search('st')) == CFG['municipalities']['max_results']


@needs_lau
def test_orte_endpoint(client):
    r = client.get('/api/hangcheck/orte', params={'q': 'krumbach'})
    assert r.status_code == 200
    assert {o['bundesland'] for o in r.json()['orte'] if o['name'] == 'Krumbach'} == {'Niederösterreich', 'Vorarlberg'}
    assert client.get('/api/hangcheck/orte', params={'q': ''}).json()['orte'] == []


def test_examples_endpoint_carries_notice_and_no_banned_words(client):
    r = client.get('/api/hangcheck/beispiele').json()
    assert len(r['beispiele']) == 3 and r['hinweise'][0]['titel'] == 'Nicht markiert heißt nicht sicher.'
    assert not banned_words(r)
