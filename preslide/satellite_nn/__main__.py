import argparse
import numpy as np
from ..common import write_json
from . import data, paths


def main() -> None:
    p = argparse.ArgumentParser(prog='preslide.satellite_nn')
    p.add_argument('command', choices=['audit', 'register', 'train'])
    p.add_argument('--limit', type=int, default=1)
    p.add_argument('--model', default='a')
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--overfit', type=int, default=0)
    a = p.parse_args()
    if a.command == 'register':
        from . import register
        print(register.register()); return
    if a.command == 'train':
        from . import train
        if a.model != 'a':
            raise SystemExit('model B is a separate registered run')
        r = train.train_a(a.pilot, a.overfit); print('best', r['best_score']); return
    ids = list(range(1, a.limit + 1)) if a.limit < 3799 else list(range(1, 3800))
    out = data.audit(ids)
    out['rows'] = out['rows'][:50]
    write_json(paths.assert_writable(paths.REPORTS / f'audit_{a.limit}.json'), out)
    print({k: v for k, v in out.items() if k not in ('rows', 'ids')})


if __name__ == '__main__':
    main()
