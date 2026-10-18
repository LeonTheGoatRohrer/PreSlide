"""wirkungskette_v01 output locations and write guard; nothing outside these roots is written."""
import hashlib
from pathlib import Path

from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/wirkungskette_v01.json'
DATA = ROOT / 'data/wirkungskette_v01'
REPORT = ROOT / 'reports/wirkungskette_v01'
ROOTS = (DATA, REPORT)
# Earlier response caches, read only (never written here).
READ_ONLY_HTTP = (ROOT / 'data/raw/http', ROOT / 'data/v04/cache/http', ROOT / 'data/hangmap_v01/cache/http')


def guard(path):
    """Create directory `path` only inside the wirkungskette_v01 roots."""
    path = Path(path).resolve()
    if not any(path == r.resolve() or r.resolve() in path.parents for r in ROOTS):
        raise RuntimeError(f'wirkungskette_v01 may only write under data/wirkungskette_v01 or reports/wirkungskette_v01: {path}')
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


def config():
    return read_json(CONFIG)
