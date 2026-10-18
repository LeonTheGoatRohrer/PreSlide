"""wirkungskette_v01 output locations and write guard; nothing outside these roots is written."""
import hashlib
from pathlib import Path

from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/wirkungskette_v01.json'
DATA = ROOT / 'data/wirkungskette_v01'
REPORT = ROOT / 'reports/wirkungskette_v01'
CONFIG_GT = ROOT / 'config/wirkungskette_gebietstest_v01.json'
DATA_GT = ROOT / 'data/wirkungskette_gebietstest_v01'
REPORT_GT = ROOT / 'reports/wirkungskette_gebietstest_v01'
ROOTS = (DATA, REPORT, DATA_GT, REPORT_GT)
# Earlier response caches, read only (never written here).
READ_ONLY_HTTP = (ROOT / 'data/raw/http', ROOT / 'data/v04/cache/http', ROOT / 'data/hangmap_v01/cache/http')


def guard(path):
    """Create directory `path` only inside the wirkungskette_v01 roots."""
    path = Path(path).resolve()
    if not any(path == r.resolve() or r.resolve() in path.parents for r in ROOTS):
        raise RuntimeError(f'wirkungskette may only write under data/ or reports/wirkungskette_v01|v02: {path}')
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def config_sha():
    return sha(CONFIG)


DEMOS = {'stanz': None, 'mittelberg': ROOT / 'config/wirkungskette_gebietstest_v01_demo.json'}
DEFAULT_DEMO = 'stanz'


def _merge(base, override):
    out = dict(base)
    for k, v in override.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def config(gebiet=DEFAULT_DEMO):
    """v01 configuration; other demo areas override only their own blocks (demo, terrain source, land cover)."""
    if gebiet not in DEMOS:
        raise ValueError('Unbekanntes Demogebiet')
    base = read_json(CONFIG)
    if DEMOS[gebiet] is None:
        return base
    override = read_json(DEMOS[gebiet])
    return _merge(base, {k: override[k] for k in ('demo', 'terrain', 'review_points')})
