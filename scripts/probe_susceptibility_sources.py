"""Phase 0 source evidence for susceptibility_v01: metadata only, no dataset download, no geometry of the sealed test.

python scripts/probe_susceptibility_sources.py  ->  reports/susceptibility_v01/phase0_evidence.json
"""
import collections
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preslide.susceptibility.download import fetch_bytes  # noqa: E402

OUT = ROOT / 'reports/susceptibility_v01/phase0_evidence.json'
WFS = 'https://geoservices1.civis.bz.it/geoserver/p_bz-Geology/ows'
IFFI_LAYERS = ['IdroGEO-Landslides-Events-Areas', 'IdroGEO-Landslides-IdentificationPoints',
               'IdroGEO-Landslides-Events-Linear', 'IdroGEO-Landslides-DeepGravitationalSlopeDeformation']


class Response:
    def __init__(self, body):
        self.text = body.decode('utf-8')

    def json(self):
        return json.loads(self.text)


def get(url, **params):
    return Response(fetch_bytes(url, params or None))


def zenodo(record):
    d = get(f'https://zenodo.org/api/records/{record}').json()
    return {'record': d['id'], 'doi': d['metadata'].get('doi'), 'concept_doi': d.get('conceptdoi'),
            'title': d['metadata']['title'], 'license': d['metadata'].get('license'),
            'publication_date': d['metadata'].get('publication_date'),
            'files': [{'key': f['key'], 'size_bytes': f['size'], 'checksum': f['checksum'],
                       'url': f['links']['self']} for f in d['files']]}


def nasadem():
    d = get('https://planetarycomputer.microsoft.com/api/stac/v1/collections/nasadem').json()
    return {'temporal': d['extent']['temporal']['interval'], 'license': d.get('license'),
            'license_link': [l for l in d['links'] if l['rel'] == 'license'],
            'item_assets': list(d.get('item_assets', {})), 'gsd': d.get('summaries', {}).get('gsd'),
            'anonymous_token_ok': 'token' in get('https://planetarycomputer.microsoft.com/api/sas/v1/token/nasadem').json()}


def shakemap(event_id):
    p = get('https://earthquake.usgs.gov/fdsnws/event/1/query', eventid=event_id, format='geojson').json()['properties']
    sm = p['products']['shakemap'][0]
    return {'event': event_id, 'title': p['title'], 'shakemap_version': sm['properties'].get('version'),
            'status': sm['status'],
            'files': {k: v.get('length') for k, v in sm['contents'].items() if k in ('download/grid.xml', 'download/raster.zip')}}


def iffi():
    hits = {}
    for layer in IFFI_LAYERS:
        text = get(WFS, service='WFS', version='2.0.0', request='GetFeature', typeNames=f'p_bz-Geology:{layer}',
                   resultType='hits').text
        hits[layer] = int(text.split('numberMatched="')[1].split('"')[0])
    # Attribute-only query (no geometry) to register the positive subset by movement class.
    attrs = get(WFS, service='WFS', version='2.0.0', request='GetFeature',
                typeNames='p_bz-Geology:IdroGEO-Landslides-Events-Areas', outputFormat='application/json',
                propertyName='MOVEMENT_CODE,MOVEMENT_DE').json()['features']
    if any(f.get('geometry') for f in attrs):
        sys.exit('WFS returned geometry for an attribute-only query; refusing to store it')
    counts = collections.Counter((f['properties']['MOVEMENT_CODE'], f['properties']['MOVEMENT_DE']) for f in attrs)
    schema = get(WFS, service='WFS', version='2.0.0', request='DescribeFeatureType',
                 typeNames='p_bz-Geology:IdroGEO-Landslides-Events-Areas').text
    fields = [s.split('"')[0] for s in schema.split('name="')[1:]]
    ckan = get('https://data.civis.bz.it/api/3/action/package_search', q='IFFI', rows=10).json()['result']['results']
    licences = [{'title': r['title'], 'license_id': r.get('license_id'),
                 'access_constraints': next((e['value'] for e in r.get('extras', []) if e['key'] == 'access_constraints'), None),
                 'lineage': next((e['value'] for e in r.get('extras', []) if e['key'] == 'lineage'), None),
                 'reference_date': next((e['value'] for e in r.get('extras', []) if e['key'] == 'dataset-reference-date'), None)}
                for r in ckan]
    return {'hits': hits, 'movement_counts': [{'code': c, 'label': l, 'n': n} for (c, l), n in sorted(counts.items())],
            'events_areas_fields': fields, 'open_data_portal_records': licences}


def head(url):
    fetch_bytes(url, method='HEAD')
    return {'url': url, 'status': 200}


def main():
    evidence = {
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'zenodo_far_western_nepal': zenodo(4290099),
        'zenodo_rer2023': zenodo(13742643),
        'nasadem_planetary_computer': nasadem(),
        'shakemap_gorkha': shakemap('us20002926'),
        'iffi_suedtirol_metadata_only': iffi(),
        'chirps_daily_head': head('https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/2015/chirps-v2.0.2015.04.25.tif.gz'),
        'open_meteo_archive_reachable': get('https://archive-api.open-meteo.com/v1/archive', latitude=28.2, longitude=84.7,
                                            start_date='2015-04-20', end_date='2015-04-21',
                                            hourly='soil_moisture_0_to_7cm').json().get('hourly_units'),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(json.dumps(evidence, indent=1, ensure_ascii=False).encode('utf-8') + b'\n')
    print(json.dumps(evidence, indent=1, ensure_ascii=False)[:4000])


if __name__ == '__main__':
    main()
