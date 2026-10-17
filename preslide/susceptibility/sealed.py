"""Sealed Suedtirol blind-test snapshot: download the registered subset once, hash it, never open it before Phase 15.

  python -m preslide.susceptibility.sealed seal     -> data/susceptibility_v01/sealed/ + reports/.../SEALED_SUEDTIROL.json

Only the hit count (a server-side number) is compared with the registration; the file content is not parsed here.
"""
import json
import sys
from datetime import datetime, timezone

from ..common import write_json
from .download import fetch_bytes, file_digest, url_with
from .paths import REPORT, SEALED, config, guard

WFS = 'https://geoservices1.civis.bz.it/geoserver/p_bz-Geology/ows'
MANIFEST = REPORT / 'SEALED_SUEDTIROL.json'


def subset_filter(cfg):
    sub = cfg['south_tyrol_blind_test']['positive_subset']
    return f"{sub['field']} IN ({','.join(str(c) for c in sub['include_codes'])})"


def request(cfg, **extra):
    return {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature',
            'typeNames': cfg['south_tyrol_blind_test']['layer'], 'CQL_FILTER': subset_filter(cfg), **extra}


def seal():
    if MANIFEST.exists():
        sys.exit(f'{MANIFEST} exists (write-once)')
    cfg = config()
    hits_text = fetch_bytes(WFS, request(cfg, resultType='hits')).decode('utf-8')
    hits = int(hits_text.split('numberMatched="')[1].split('"')[0])
    expected = cfg['south_tyrol_blind_test']['expected_counts_at_registration']['include_codes_total']
    params = request(cfg, outputFormat='SHAPE-ZIP')
    body = fetch_bytes(WFS, params)
    target = guard(SEALED) / 'iffi_suedtirol_subset.zip'
    if target.exists():
        sys.exit(f'{target} exists (write-once)')
    target.write_bytes(body)
    record = {'sealed_at_utc': datetime.now(timezone.utc).isoformat(), 'url': url_with(WFS, params),
              'filter': subset_filter(cfg), 'server_hits': hits, 'hits_at_registration': expected,
              'hits_match_registration': hits == expected, 'file': target.name, 'size_bytes': target.stat().st_size,
              'sha256': file_digest(target, 'sha256'),
              'rule': 'not opened, parsed or plotted before the Phase 15 approval; no model, feature or threshold uses it'}
    write_json(MANIFEST, record)
    return record


if __name__ == '__main__':
    if sys.argv[1:] != ['seal']:
        sys.exit('usage: python -m preslide.susceptibility.sealed seal')
    print(json.dumps(seal(), indent=1))
