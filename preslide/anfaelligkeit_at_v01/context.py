"""Geology (GeoSphere 1:500 000, V0.4 layer code) and CORINE land cover by event-year vintage (config features)."""
import json

import numpy as np
import pandas as pd
from shapely import points

from ..v04 import context as v04_context
from .http import cached_json

GEO = ['geo_carbonate', 'geo_clastic_rock', 'geo_unconsolidated', 'geo_low_grade_metamorphic', 'geo_crystalline_other']
LC = ['lc_forest', 'lc_grass_shrub', 'lc_agriculture', 'lc_open_bare', 'lc_artificial_water_other']


def clc_vintage(year) -> str | None:
    """Latest CORINE vintage whose imagery ended before the event year (registered rule)."""
    if year is None or pd.isna(year) or year < 2002:
        return None
    if year <= 2007:
        return 'CLC2000'
    if year <= 2012:
        return 'CLC2006'
    if year <= 2018:
        return 'CLC2012'
    return 'CLC2018'


def one_hot(classes: pd.Series, names: list) -> pd.DataFrame:
    """Indicator columns; a missing class gives NaN in every column (never a silent zero)."""
    out = pd.DataFrame({n: (classes == n).astype(float) for n in names}, index=classes.index)
    out[classes.isna()] = np.nan
    return out


def geology(lon, lat, cfg: dict) -> pd.Series:
    v04_context.cached_json = cached_json          # the V0.4 layer code reads/writes only through this cache
    layer = v04_context.geology_layer()
    classes = cfg['features']['geology']['classes']
    out = []
    for p in points(np.asarray(lon, float), np.asarray(lat, float)):
        hits = [i for i in layer['tree'].query(p) if layer['geoms'][i].covers(p)]
        names = {layer['lith'][i] for i in hits}
        lith = names.pop() if len(names) == 1 else None
        out.append(None if lith is None else
                   next((k for k, v in classes.items() if isinstance(v, list) and lith in v), 'geo_crystalline_other'))
    return pd.Series(out, dtype=object)


def land_cover(lon, lat, vintages, cfg: dict) -> pd.DataFrame:
    lc = cfg['features']['land_cover']
    rows = []
    for x, y, vintage in zip(lon, lat, vintages):
        if vintage is None:
            rows.append({'clc_code': None, 'land_cover_class': None})
            continue
        url, field = lc['services'][vintage]
        r = cached_json(url, {'geometry': json.dumps({'x': round(float(x), 7), 'y': round(float(y), 7), 'spatialReference': {'wkid': 4326}}),
                              'geometryType': 'esriGeometryPoint', 'inSR': '4326', 'spatialRel': 'esriSpatialRelIntersects',
                              'outFields': field, 'returnGeometry': 'false'}, min_interval_s=0.2)
        codes = {f['attributes'][field] for f in r.get('features', [])}
        code = codes.pop() if len(codes) == 1 else None
        rows.append({'clc_code': code, 'land_cover_class': v04_context.clc_class(code, lc['classes']) if code is not None else None})
    return pd.DataFrame(rows)
