"""Offline municipality search (GISCO LAU 2021, Austria only); no external geocoder, place names never leave the machine."""
import json
import shutil
import subprocess
import unicodedata
from functools import lru_cache

from shapely.geometry import shape

from ..sources import ROOT
from ..v05.paths import sha
from ..wirkungskette import store
from .paths import DATA, config, guard

UMLAUT_E = str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'})


def folds(text):
    """Spellings a query or name is compared in: 'Mühldorf' -> {'muehldorf', 'muhldorf'} (case- and accent-insensitive)."""
    s = ' '.join(str(text).casefold().replace('-', ' ').split())
    plain = ''.join(ch for ch in unicodedata.normalize('NFKD', s.replace('ß', 'ss')) if not unicodedata.combining(ch))
    digraph = ''.join(ch for ch in unicodedata.normalize('NFKD', s.translate(UMLAUT_E)) if not unicodedata.combining(ch))
    return {plain, digraph}


def state_of(lau_id, states):
    """Bundesland from the first digit of the Gemeindekennziffer (1 = Burgenland ... 9 = Wien)."""
    return states[str(lau_id)[0]]


def entries_from_geojson(features, cfg):
    m = cfg['municipalities']
    out = []
    for f in features:
        p = f['properties']
        if p.get('CNTR_CODE') != 'AT':
            continue
        point = shape(f['geometry']).representative_point()
        out.append({'kennziffer': str(p['LAU_ID']), 'name': p['LAU_NAME'], 'bundesland': state_of(p['LAU_ID'], m['states']),
                    'einwohner_2021': int(p['POP_2021']) if p.get('POP_2021') is not None else None,
                    'longitude': round(point.x, 6), 'latitude': round(point.y, 6)})
    return sorted(out, key=lambda e: e['kennziffer'])


def _source(cfg):
    m = cfg['municipalities']
    path = ROOT / m['source']
    if not path.exists():
        path = guard(DATA / 'cache/gisco') / path.name
        if not path.exists():
            curl = shutil.which('curl.exe') or shutil.which('curl')
            subprocess.run([curl, '-f', '-sS', '-L', '--max-time', '600', '-o', str(path), m['source_url']], check=True, timeout=650)
    if sha(path) != m['source_sha256']:
        raise RuntimeError(f'GISCO LAU file differs from the registered SHA-256: {path}')
    return path


@lru_cache(maxsize=1)
def municipalities():
    cfg = config()
    ident = store.identity({'source_sha256': cfg['municipalities']['source_sha256'], 'filter': cfg['municipalities']['filter'],
                            'states': cfg['municipalities']['states'], 'algorithm': 1})
    path = guard(DATA) / 'gemeinden.json'
    if not store.exists(path):
        with open(_source(cfg), encoding='utf-8') as f:
            features = json.load(f)['features']
        store.save_json(path, ident, entries_from_geojson(features, cfg), {'source': cfg['municipalities']['source_url']})
    entries = store.load_json(path, ident)
    return [{**e, '_folds': folds(e['name'])} for e in entries]


def search(query, entries=None, limit=None):
    """Up to `limit` matches: exact, then prefix, then word prefix, then substring; ties by population, then name."""
    if entries is None:
        entries = municipalities()
    limit = limit or config()['municipalities']['max_results']
    q = folds(query)
    if not any(len(v) >= 2 for v in q):
        return []
    scored = []
    for e in entries:
        names = e['_folds'] if '_folds' in e else folds(e['name'])
        best = None
        for a in q:
            for n in names:
                if n == a:
                    rank = 0
                elif n.startswith(a):
                    rank = 1
                elif any(w.startswith(a) for w in n.split()):
                    rank = 2
                elif a in n:
                    rank = 3
                else:
                    continue
                best = rank if best is None else min(best, rank)
        if best is not None:
            scored.append((best, -(e['einwohner_2021'] or 0), e['name'], e['kennziffer'], e))
    scored.sort(key=lambda t: t[:4])
    return [{k: v for k, v in t[4].items() if k != '_folds'} | {'anzeige': f"{t[4]['name']} ({t[4]['bundesland']})"}
            for t in scored[:limit]]
