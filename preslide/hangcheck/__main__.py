"""Warm the caches (classes, flow paths, OSM) for the examples and a few alpine valley towns, so the demo runs
without waiting: `python -m preslide.hangcheck prewarm`. The town list is a demo convenience, not registered config."""
import sys
import time

from . import build, fliesswege, gemeinden
from .paths import config

TOWNS = ['Landeck', 'Sölden', 'Mayrhofen', 'Schwaz', 'Bad Gastein', 'Zell am See', 'Hallstatt', 'Gasen', 'Schruns',
         'Lienz', 'Murau', 'Gmünd in Kärnten']


def prewarm():
    cfg = config()
    places = [(e['name'], e['longitude'], e['latitude'], e['radius_m']) for e in cfg['examples']]
    for name in TOWNS:
        hits = [h for h in gemeinden.search(name) if h['name'] == name]
        if len(hits) != 1:
            print(f'skip {name}: {len(hits)} exact matches')
            continue
        places.append((hits[0]['anzeige'], hits[0]['longitude'], hits[0]['latitude'], cfg['radius_m']['default']))
    for name, lon, lat, radius_m in places:
        t = time.time()
        try:
            r = build.compute(lon, lat, radius_m)
            f = fliesswege.compute(lon, lat, radius_m)
            print(f"{name}: {r['zaehlung']['bewertet']} cells, {len(r['pruefpunkte'])} review points, "
                  f"{len(f['fliesswege'])} flow paths, {time.time() - t:.1f} s", flush=True)
        except (ValueError, RuntimeError) as error:
            print(f'{name}: not computable ({error})', flush=True)


if __name__ == '__main__':
    if sys.argv[1:] != ['prewarm']:
        raise SystemExit('usage: python -m preslide.hangcheck prewarm')
    prewarm()
