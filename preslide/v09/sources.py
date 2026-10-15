"""V0.9 source snapshots (before registration): Land Kärnten event cadastre and WLV non-slide records.

  python -m preslide.v09.sources

Each snapshot is paged through the cached HTTP layer, checked for completeness and duplicate IDs and written once to
data/v09/raw/<name>.json with a SHA-256 manifest. The Kärnten field `nameOfEvent` frequently contains personal names;
it is dropped from the snapshot and from every derived table (the raw API pages remain only in the local, git-ignored
HTTP cache that proves what was retrieved).
"""
import json
from datetime import datetime, timezone

from ..common import write_json
from .http import cached_json
from .paths import V09_DATA, guard, sha

KTN = ('https://gis.ktn.gv.at/api/features/inspire/v1/collections/'
       'AT.0019.598479ac-f70f-4287-aeb4-8c8550855329/items')
WLV = 'https://gis.lfrz.gv.at/api/geodata/i000901/ogc/features/v1/collections/i000901:wlv_ereignisse/items'
WLV_NON_SLIDE = "nameofevent LIKE 'Wasser: Murgang%' OR nameofevent LIKE 'Wasser: Murartig%' OR nameofevent LIKE 'Steinschlag%'"
KTN_KEEP = ('inspireID', 'hazardCategory', 'validFrom', 'magnitudeOrIntensity')


def raw_path(name):
    return guard(V09_DATA / 'raw') / f'{name}.json'


def _write_once(name, payload):
    path = raw_path(name)
    if path.exists():
        return path
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    write_json(path.with_suffix('.manifest.json'), {'sha256': sha(path), 'records': len(payload['features']),
                                                    'written_at': datetime.now(timezone.utc).isoformat(), 'source': payload['source']})
    return path


def kaernten():
    # The service pages with `start` (its NEXT link); an `offset` parameter is silently ignored.
    feats, count = [], None
    while count is None or len(feats) < count:
        page = cached_json(KTN, {'f': 'json', 'limit': 1000, 'start': len(feats)}, min_interval_s=1.0, f_param=False)
        if count is not None and page['numberMatched'] != count:
            raise ValueError('Kärnten source changed during download')
        count = page['numberMatched']
        if not page['features']:
            raise ValueError('Empty Kärnten page before all records were read')
        feats += page['features']
    ids = [f['properties']['inspireID']['localId'] for f in feats]
    if len(ids) != count or len(set(ids)) != len(ids):
        raise ValueError('Incomplete or duplicated Kärnten records')
    clean = [{'type': 'Feature', 'geometry': f['geometry'], 'properties': {k: f['properties'].get(k) for k in KTN_KEEP}}
             for f in feats]
    return _write_once('kaernten_events', {'source': KTN, 'retrieval': 'f=json, limit=1000, start paging',
                                           'dropped_fields': ['nameOfEvent (personal names)'], 'features': clean})


def wlv_non_slide():
    params = {'f': 'application/geo+json', 'limit': 1000, 'filter': WLV_NON_SLIDE, 'filter-lang': 'cql-text'}
    first = cached_json(WLV, {**params, 'limit': 5}, f_param=False)
    count, feats = first['numberMatched'], []
    while len(feats) < count:
        page = cached_json(WLV, {**params, 'startIndex': len(feats)}, min_interval_s=1.0, f_param=False)
        if not page['features'] or page['numberMatched'] != count:
            raise ValueError('Empty WLV page or source changed during download')
        feats += page['features']
    if len(feats) != count or len({f['id'] for f in feats}) != count:
        raise ValueError('Incomplete or duplicated WLV results')
    if not all(f['properties']['nameofevent'].startswith(('Wasser: Murgang', 'Wasser: Murartig', 'Steinschlag')) for f in feats):
        raise ValueError('WLV endpoint did not apply the filter')
    return _write_once('wlv_non_slide', {'source': WLV, 'filter': WLV_NON_SLIDE, 'features': feats})


if __name__ == '__main__':
    for fn in (kaernten, wlv_non_slide):
        p = fn()
        print(p, sha(p))
