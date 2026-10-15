"""Land cover (CORINE, vintage strictly before t0) and geology (GeoSphere 1:500 000) at sample points."""
import json

import numpy as np
import pandas as pd
from shapely import STRtree, points
from shapely.geometry import shape

from .http import cached_json

CLC = {'CLC2012': ('https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012/MapServer/0/query', 'Code_12'),
       'CLC2018': ('https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_LAEA/MapServer/0/query', 'Code_18')}
GEOLOGY = 'https://gis.geosphere.at/maps/rest/services/inspire/GE_GeologicUnit_500k/MapServer/0/query'
LC_CLASSES = ['lc_forest', 'lc_grass_shrub', 'lc_agriculture', 'lc_open_bare', 'lc_artificial_water_other']
GEO_CLASSES = ['geo_carbonate', 'geo_clastic_rock', 'geo_unconsolidated', 'geo_low_grade_metamorphic', 'geo_crystalline_other']


def clc_vintage(t0_utc):
    """CLC2018 imagery is 2017-2018: only for t0 >= 2019-01-01. CLC2012 imagery 2011-2012 otherwise."""
    return 'CLC2018' if pd.Timestamp(t0_utc) >= pd.Timestamp('2019-01-01', tz='UTC') else 'CLC2012'


def clc_class(code, classes):
    code = int(code)
    for name, codes in classes.items():
        if isinstance(codes, list) and code in codes:
            return name
    return 'lc_artificial_water_other'


def land_cover(samples, classes):
    out = []
    for row in samples.itertuples():
        vintage = clc_vintage(row.t0_utc)
        url, field = CLC[vintage]
        response = cached_json(url, {'geometry': json.dumps({'x': round(row.longitude, 7), 'y': round(row.latitude, 7),
                                                             'spatialReference': {'wkid': 4326}}),
                                     'geometryType': 'esriGeometryPoint', 'inSR': '4326', 'spatialRel': 'esriSpatialRelIntersects',
                                     'outFields': field, 'returnGeometry': 'false'}, min_interval_s=0.2)
        codes = {f['attributes'][field] for f in response.get('features', [])}
        code = codes.pop() if len(codes) == 1 else None      # 0 or >1 polygons (border) -> missing
        out.append({'sample_id': row.sample_id, 'clc_vintage': vintage, 'clc_code': code,
                    'land_cover_class': clc_class(code, classes) if code is not None else None})
    return pd.DataFrame(out)


_GEOLOGY = {}


def geology_layer():
    """Whole layer once (cached); polygons in WGS84 as served."""
    if 'tree' not in _GEOLOGY:
        ids = sorted(cached_json(GEOLOGY, {'where': '1=1', 'returnIdsOnly': 'true'})['objectIds'])
        geoms, lith = [], []
        for i in range(0, len(ids), 200):
            r = cached_json(GEOLOGY, {'objectIds': ','.join(map(str, ids[i:i + 200])), 'outFields': 'OBJECTID,representativeLithology',
                                      'outSR': '4326', 'returnGeometry': 'true'})
            for f in r['features']:
                rings = f['geometry']['rings']
                geoms.append(shape({'type': 'Polygon', 'coordinates': rings}) if len(rings) == 1 else _rings(rings))
                lith.append(f['attributes']['representativeLithology'])
        if len(geoms) != len(ids):
            raise ValueError('Incomplete geology layer')
        _GEOLOGY.update(tree=STRtree(geoms), geoms=geoms, lith=lith)
    return _GEOLOGY


def _rings(rings):
    """Esri rings: clockwise = exterior, counter-clockwise = hole (shoelace sign)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    exteriors, holes = [], []
    for ring in rings:
        x, y = np.array(ring).T
        (exteriors if np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]) < 0 else holes).append(Polygon(ring))
    union = unary_union(exteriors)
    return union.difference(unary_union(holes)) if holes else union


def geology(samples, classes):
    layer = geology_layer()
    pts = points(samples.longitude.to_numpy(), samples.latitude.to_numpy())
    out = []
    for sid, p in zip(samples.sample_id, pts):
        hits = [i for i in layer['tree'].query(p) if layer['geoms'][i].covers(p)]
        names = {layer['lith'][i] for i in hits}
        lith = names.pop() if len(names) == 1 else None
        cls = None
        if lith is not None:
            cls = next((k for k, v in classes.items() if isinstance(v, list) and lith in v), 'geo_crystalline_other')
        out.append({'sample_id': sid, 'lithology': lith, 'geology_class': cls})
    return pd.DataFrame(out)
