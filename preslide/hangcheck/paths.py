"""hangcheck_v01 locations and write guard: this namespace writes only below data/hangcheck_v01 (never frozen artefacts)."""
import os
from pathlib import Path

from ..common import read_json
from ..sources import ROOT

CONFIG = ROOT / 'config/hangcheck_v01.json'
DATA = ROOT / 'data/hangcheck_v01'


def config():
    return read_json(CONFIG)


def guard(path):
    """Create the directory `path` only inside data/hangcheck_v01 (abspath: data/ may be a junction)."""
    path, root = Path(os.path.abspath(path)), Path(os.path.abspath(DATA))
    if path != root and root not in path.parents:
        raise RuntimeError(f'hangcheck_v01 may only write under data/hangcheck_v01: {path}')
    path.mkdir(parents=True, exist_ok=True)
    return path
