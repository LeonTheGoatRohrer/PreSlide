import argparse
import numpy as np
from ..common import write_json
from . import data, paths


def main() -> None:
    p = argparse.ArgumentParser(prog='preslide.satellite_nn')
    p.add_argument('command', choices=['audit'])
    p.add_argument('--limit', type=int, default=1)
    a = p.parse_args()
    ids = list(range(1, a.limit + 1)) if a.limit < 3799 else list(range(1, 3800))
    out = data.audit(ids)
    out['rows'] = out['rows'][:50]
    write_json(paths.assert_writable(paths.REPORTS / f'audit_{a.limit}.json'), out)
    print({k: v for k, v in out.items() if k not in ('rows', 'ids')})


if __name__ == '__main__':
    main()
