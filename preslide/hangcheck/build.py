"""hangcheck_v01 computation: hangmap feature code -> frozen V0.4 static model -> relative classes and review points.

No weather enters anywhere; the heavy-rain switch of the page only selects the view."""
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from ..hangmap.build import build_features, inside_austria
from ..sources import ROOT
from ..terrain import INVERSE
from ..v05.paths import sha
from ..wirkungskette import store
from . import core
from .paths import CONFIG, DATA, config, guard

HINWEISE = [
    {'titel': 'Nicht markiert heißt nicht sicher.',
     'text': 'Die Einstufung ist relativ: In jedem Gebiet sind Hänge markiert, auch wenn dort nichts passiert. '
             'Auch nicht markierte Hänge können abgehen.'},
    {'titel': 'Talwacht ist keine Warnung.',
     'text': 'Aktuelle Unwetterwarnungen geben GeoSphere Austria und die Landeswarnzentralen. '
             'Im Notfall: Euronotruf 112, Feuerwehr 122.'},
    {'titel': 'Grundlage ist nur das Gelände.',
     'text': 'Berücksichtigt sind {terrain}, {land_cover} und {geology}. Nicht berücksichtigt sind Wetter, '
             'der Untergrund im Detail und Schutzbauten. Mehr unter „Methodik & Grenzen“.'},
    {'titel': 'Gelernt aus gemeldeten Ereignissen.',
     'text': 'Ein Teil der Unterschiede kann daher von der Meldung kommen (zum Beispiel die Nähe zu Straßen), '
             'nicht vom Hang selbst.'},
]


def hinweise(cfg):
    v = cfg['data_vintages']
    return [{'titel': h['titel'], 'text': h['text'].format(**v)} for h in HINWEISE]


@lru_cache(maxsize=1)
def model_bundle():
    m = config()['model']
    path = ROOT / m['bundle']
    core.check_model_sha(sha(path), m['bundle_sha256'])
    bundle = joblib.load(path)
    core.check_model_columns(bundle['columns'])
    return bundle


def score_rows(frame):
    """Linear V0.4 static score of assessable rows (all 22 features finite; never imputed)."""
    b = model_bundle()
    X = frame[list(b['columns'])]
    core.check_model_columns(X.columns)
    if X.isna().any().any():
        raise ValueError('NaN in a required static feature of an assessable cell')
    z = b['preprocessor'].transform(X, pd.Series(np.arange(len(X)), index=X.index))  # every cell its own group
    return b['model'].decision_function(z), z


def identity(lon, lat, radius_m):
    return store.identity({'lon': round(float(lon), 5), 'lat': round(float(lat), 5), 'radius_m': float(radius_m),
                           'config_sha256': sha(CONFIG), 'algorithm': 1})


def compute(lon, lat, radius_m=None):
    """Deterministic result for one place; cached with an identity- and SHA-256-checked sidecar."""
    cfg = config()
    lon, lat = float(lon), float(lat)
    radius_m = core.radius(radius_m, cfg)
    if not (np.isfinite(lon) and np.isfinite(lat)) or not inside_austria(lon, lat)[0]:
        raise ValueError('Der gewählte Ort liegt außerhalb Österreichs. Hang-Check rechnet nur für Orte in Österreich.')
    ident = identity(lon, lat, radius_m)
    path = guard(DATA / 'cache/results') / f'{ident}.json'
    if store.exists(path):
        return store.load_json(path, ident)
    try:
        result = _compute(lon, lat, radius_m, cfg)
    except ValueError as error:
        if str(error).startswith(('terrain_tile_not_cached', 'terrain_source_not_demonstrably_pre_event')):
            raise ValueError('Für diesen Ort liegen keine passenden Geländedaten im lokalen Speicher vor.') from error
        raise
    store.save_json(path, ident, result)
    return store.load_json(path, ident)


def _compute(lon, lat, radius_m, cfg):
    frame, meta = build_features(lon, lat, radius_m, None, cfg)
    reasons = frame.reason[frame.reason != ''].value_counts()
    ok = frame[frame.reason == ''].reset_index(drop=True)
    score, z = score_rows(ok)
    cls = core.classes(score, cfg)
    pct = core.rank_percentile(score)
    bundle = model_bundle()
    cols, coef = list(bundle['columns']), bundle['model'].coef_
    raw = ok[cols].to_numpy(float)
    half = cfg['area']['cell_m'] / 2
    labels = {c['id']: c['label'] for c in cfg['classes']}

    cells = []
    for i in np.flatnonzero(cls <= 2):
        x, y = float(ok.x[i]), float(ok.y[i])
        ring = [INVERSE.transform(x + dx, y + dy) for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half), (-half, -half))]
        cells.append({'type': 'Feature',
                      'properties': {'stufe': int(cls[i]), 'perzentil': round(float(pct[i]), 1),
                                     'treiber': [d['merkmal'] for d in core.drivers(z[i], raw[i], coef, cols, k=2)]},
                      'geometry': {'type': 'Polygon', 'coordinates': [[[round(a, 6), round(b, 6)] for a, b in ring]]}})

    points = []
    for rank, i in enumerate(core.review_points(ok.x, ok.y, score, cls, cfg), start=1):
        points.append({'nr': rank, 'longitude': round(float(ok.longitude[i]), 6), 'latitude': round(float(ok.latitude[i]), 6),
                       'hoehe_m': int(round(float(ok.elevation[i]))), 'neigung_grad': round(float(ok.slope[i]), 1),
                       'landbedeckung': core.land_cover_de(ok.land_cover_class[i]), 'geologie': core.geology_de(ok.geology_class[i]),
                       'perzentil': round(float(pct[i]), 1), 'treiber': core.drivers(z[i], raw[i], coef, cols)})

    counts = {'zellen': int(len(frame)), 'bewertet': int(len(ok)),
              'stufen': {labels[c['id']]: int((cls == c['id']).sum()) for c in cfg['classes']},
              'ausgeschlossen': [{'grund': core.REASON_DE[k], 'anzahl': int(v)} for k, v in reasons.items()]}
    return {'version': cfg['version'], 'status': cfg['status'], 'centre': {'longitude': lon, 'latitude': lat}, 'radius_m': radius_m,
            'zellen': {'type': 'FeatureCollection', 'features': cells}, 'pruefpunkte': points,
            'pruefpunkte_abstand_m': cfg['review_points']['separation_m'], 'zaehlung': counts,
            'stufen': [{'id': c['id'], 'label': c['label'], 'top_fraction': c['top_fraction']} for c in cfg['classes']],
            'zellgroesse_m': cfg['area']['cell_m'],
            'modell': {'bundle_sha256': cfg['model']['bundle_sha256'], 'variante': 'V0.4 Gelände (conditional logit, statisch)'},
            'datenstand': cfg['data_vintages'], 'gelaende_meta': meta, 'hinweise': hinweise(cfg)}
