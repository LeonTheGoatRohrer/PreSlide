"""Pure hangcheck_v01 logic (no IO): model guards, relative classes, review points, plain-language drivers.

Classes and review points reuse preslide.wirkungskette.core (one implementation of each primitive)."""
import numpy as np
import pandas as pd

from ..v04.models import STATIC
from ..wirkungskette.core import review_classes, select_release_points, validate_radius

FEATURE_DE = {
    'elevation': 'Höhe', 'slope': 'Neigung', 'aspect_sin': 'Ausrichtung (Ost/West)', 'aspect_cos': 'Ausrichtung (Nord/Süd)',
    'profile_curvature': 'Wölbung hangabwärts', 'plan_curvature': 'Wölbung quer zum Hang', 'roughness_tri': 'Unebenheit des Geländes',
    'tpi_150m': 'Lage im Kleinrelief (Mulde oder Rücken)', 'tpi_500m': 'Lage im Relief (Mulde oder Rücken)',
    'relative_position_500m': 'Höhenlage im Umfeld', 'log10_catchment_m2': 'Fläche hangaufwärts (Einzugsgebiet)',
    'twi': 'Geländefeuchte-Index (Wasser sammelt sich)'}
LAND_COVER_DE = {'lc_forest': 'Wald', 'lc_grass_shrub': 'Wiese, Weide oder Gebüsch', 'lc_agriculture': 'Acker oder landwirtschaftliche Fläche',
                 'lc_open_bare': 'Fels, Geröll oder offene Fläche', 'lc_artificial_water_other': 'Siedlung, Verkehrsfläche, Wasser oder Sonstiges'}
GEOLOGY_DE = {'geo_carbonate': 'Kalk- oder Karbonatgestein', 'geo_clastic_rock': 'Sandstein oder Siltstein',
              'geo_unconsolidated': 'Lockermaterial (Kies, Schotter)', 'geo_low_grade_metamorphic': 'Phyllit oder Schiefer',
              'geo_crystalline_other': 'Kristallin oder sonstiges Gestein'}
REASON_DE = {'outside_austria': 'außerhalb Österreichs', 'terrain_not_computable': 'Gelände nicht berechenbar',
             'elevation_out_of_range': 'Höhe außerhalb des Modellbereichs', 'slope_below_minimum': 'flacher als 5°',
             'catchment_truncated': 'Einzugsgebiet am Rand abgeschnitten', 'no_land_cover': 'Landbedeckung nicht eindeutig',
             'no_geology': 'Geologie nicht eindeutig'}


def check_model_columns(columns):
    """The bundle must use exactly the registered V0.4 static list in the same order; never reorder or fill."""
    if list(columns) != list(STATIC):
        raise RuntimeError('Model columns differ from preslide.v04.models.STATIC (names or order); hangcheck_v01 stops')


def check_model_sha(actual, expected):
    if actual != expected:
        raise RuntimeError('V0.4 static model changed (SHA-256 mismatch); hangcheck_v01 uses only the frozen model')


def radius(radius_m, cfg):
    """Radius in metres within the configured bounds and step (German message on failure)."""
    return validate_radius(cfg['radius_m']['default'] if radius_m is None else radius_m, cfg)


def classes(score, cfg):
    """Relative class per assessable cell (1 = Prüfstufe 1 ... 3 = unmarked); too few cells is an error, not a result."""
    score = np.asarray(score, float)
    minimum = cfg['area']['minimum_assessable_cells']
    if len(score) < minimum:
        raise ValueError(f'Zu wenige bewertbare Hangzellen im Umkreis ({len(score)} von mindestens {minimum}). '
                         'Einen Ort mit mehr Hängen wählen oder den Umkreis vergrößern.')
    ids = review_classes(score, cfg['classes'])
    # Equal scores share the better class (review_classes alone would split a tie by input order).
    return pd.Series(ids).groupby(score).transform('min').to_numpy()


def rank_percentile(score):
    """0..100, higher = more conspicuous inside the radius (average rank for ties)."""
    return pd.Series(np.asarray(score, float)).rank(method='average', pct=True).to_numpy() * 100


def review_points(x_m, y_m, score, cls, cfg):
    """Indices of up to `count` Prüfstufe-1 cells, best first, >= separation_m apart (EPSG:31287 metres)."""
    rp = cfg['review_points']
    idx = np.flatnonzero(np.asarray(cls) == 1)
    chosen = select_release_points(np.asarray(x_m, float)[idx], np.asarray(y_m, float)[idx], np.asarray(score, float)[idx],
                                   rp['count'], rp['separation_m'])
    return idx[chosen]


def feature_label(column, raw_value):
    if column in LAND_COVER_DE:
        return ('Landbedeckung ' if raw_value >= .5 else 'Landbedeckung nicht ') + LAND_COVER_DE[column]
    if column in GEOLOGY_DE:
        return ('Geologie ' if raw_value >= .5 else 'Geologie nicht ') + GEOLOGY_DE[column]
    return FEATURE_DE[column]


def drivers(z_row, raw_row, coef, columns, k=3):
    """The k largest absolute contributions z * coef of one cell, in plain language with direction."""
    c = np.asarray(z_row, float) * np.asarray(coef, float)
    out = []
    for i in np.argsort(-np.abs(c), kind='stable')[:k]:
        out.append({'merkmal': feature_label(columns[i], float(raw_row[i])),
                    'richtung': 'hebt die Einstufung' if c[i] > 0 else 'senkt die Einstufung'})
    return out


def land_cover_de(cls):
    return LAND_COVER_DE.get(cls, 'unbekannt')


def geology_de(cls):
    return GEOLOGY_DE.get(cls, 'unbekannt')

