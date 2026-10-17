"""python -m preslide.hangmap [example_id ...]: compute and cache the registered example areas."""
import sys
import time

from . import build
from .paths import config


def main(ids):
    examples = {e['id']: e for e in config()['examples']}
    for eid in ids or examples:
        e = examples[eid]
        t = time.time()
        r = build.compute(e['longitude'], e['latitude'], e['radius_m'])
        print(f"{eid}: {r['counts']} group share sum {r['group_share_sum']} ({time.time() - t:.1f}s)", flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
