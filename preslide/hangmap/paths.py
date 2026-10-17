"""hangmap_v01 locations and write guard: this namespace writes only below data/hangmap_v01 (never frozen artefacts)."""
import os
from pathlib import Path

from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/hangmap_v01.json'
DATA = ROOT / 'data/hangmap_v01'
READ_ONLY_HTTP = (ROOT / 'data/raw/http', ROOT / 'data/v04/cache/http', ROOT / 'data/v05/cache/http')


def config():
    return read_json(CONFIG)


def guard(path):
    """Create the directory `path` only inside data/hangmap_v01 (abspath: data/ may be a junction)."""
    path, root = Path(os.path.abspath(path)), Path(os.path.abspath(DATA))
    if path != root and root not in path.parents:
        raise RuntimeError(f'hangmap_v01 may only write under data/hangmap_v01: {path}')
    path.mkdir(parents=True, exist_ok=True)
    return path
