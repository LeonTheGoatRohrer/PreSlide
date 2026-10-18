"""Re-run the registered V0.7 analyses unchanged on the exact distances (config/v07b.json).

  python -m preslide.v07b.experiment main

preslide.v07.experiment.main is called as it is; only the module globals through which it reads the distance table and
writes its outputs (V07_DATA, V07_REPORT, guard) are rebound to data/v07b and reports/v07b. The V0.7 analysis plan
(config/v07.json, still checked against its registration), the V0.5 CV plan, hyperparameters, bootstrap and caliper are
therefore identical to V0.7.
"""
import contextlib
import sys

from ..common import read_json, write_json
from ..sources import ROOT
from ..v05.paths import sha
from ..v07 import experiment as E
from .paths import V07B_DATA, V07B_REPORT, config as load_config, guard

REBOUND = ('V07_DATA', 'V07_REPORT', 'guard')


@contextlib.contextmanager
def bound():
    """Point the unchanged V0.7 experiment at the v07b distance table and output folders; restore afterwards."""
    original = {name: getattr(E, name) for name in REBOUND}
    E.V07_DATA, E.V07_REPORT, E.guard = V07B_DATA, V07B_REPORT, guard
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(E, name, value)


def main():
    load_config()
    meta = read_json(V07B_DATA / 'infrastructure.json')
    if meta['limit_ways'] or not read_json(V07B_DATA / 'distance_checks.json').get('v07_reproduced_exactly'):
        raise RuntimeError('exact distance table missing, a pilot, or its checks did not pass')
    with bound():
        E.main()
    path = V07B_REPORT / 'cv_results.json'
    result = read_json(path)
    result['inputs'].update({'v07b_config_sha256': sha(ROOT / 'config/v07b.json'), 'analysis_code': 'preslide.v07.experiment.main (unchanged, rebound)',
                             'distance_table': 'data/v07b/infrastructure.parquet (exact nearest vertex)'})
    write_json(guard(V07B_REPORT) / 'cv_results.json', result)


if __name__ == '__main__':
    {'main': main}[sys.argv[1]]()
