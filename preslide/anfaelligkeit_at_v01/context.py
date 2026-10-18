"""Geology (GeoSphere 1:500 000, V0.4 layer code) and CORINE land cover by event-year vintage (config features)."""
import json

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import STRtree, points

from ..v04 import context as v04_context
from .http import cached_json

TO_3035 = Transformer.from_crs('EPSG:4326', 'EPSG:3035', always_xy=True)
TILE_3035_M = 10000

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


def _clc_tile(url, field, tx, ty):
    """All CORINE polygons intersecting one 10 km EPSG:3035 tile (native CRS, exact geometry), paged and cached."""
    env = {'xmin': tx * TILE_3035_M, 'ymin': ty * TILE_3035_M, 'xmax': (tx + 1) * TILE_3035_M, 'ymax': (ty + 1) * TILE_3035_M,
           'spatialReference': {'wkid': 3035}}
    geoms, codes, offset = [], [], 0
    while True:
        r = cached_json(url, {'geometry': json.dumps(env), 'geometryType': 'esriGeometryEnvelope', 'inSR': '3035', 'outSR': '3035',
                              'spatialRel': 'esriSpatialRelIntersects', 'outFields': field, 'returnGeometry': 'true',
                              'resultOffset': str(offset), 'resultRecordCount': '1000', 'orderByFields': 'OBJECTID'}, min_interval_s=0.2)
        for feat in r.get('features', []):
            rings = feat['geometry']['rings']
            geoms.append(v04_context._rings(rings))
            codes.append(feat['attributes'][field])
        if not r.get('exceededTransferLimit'):
            return geoms, codes
        offset += len(r['features'])


def land_cover_tiles(lon, lat, vintages, cfg: dict) -> pd.DataFrame:
    """CORINE class per point: exactly one covering polygon, else missing (V0.4 rule). Polygons are fetched per 10 km
    EPSG:3035 tile (checked against V0.4-style point queries on the 488 pilot samples: 488/488 identical codes)."""
    lc = cfg['features']['land_cover']
    x, y = TO_3035.transform(np.asarray(lon, float), np.asarray(lat, float))
    out = pd.DataFrame({'clc_code': [None] * len(x), 'land_cover_class': [None] * len(x)}, dtype=object)
    vint = pd.Series(vintages, dtype=object)
    keys = pd.DataFrame({'v': vint, 'tx': np.floor(x / TILE_3035_M).astype(int), 'ty': np.floor(y / TILE_3035_M).astype(int)})
    for (v, tx, ty), g in keys[vint.notna()].groupby(['v', 'tx', 'ty']):
        url, field = lc['services'][v]
        geoms, codes = _clc_tile(url, field, tx, ty)
        tree = STRtree(geoms) if geoms else None
        for i in g.index:
            p = points(x[i], y[i])
            hits = {codes[j] for j in tree.query(p) if geoms[j].covers(p)} if tree is not None else set()
            if len(hits) == 1:
                code = hits.pop()
                out.at[i, 'clc_code'] = code
                out.at[i, 'land_cover_class'] = v04_context.clc_class(code, lc['classes'])
    return out
