from pathlib import Path
from ..sources import ROOT

VERSION = 'satellite_nn_v01'
DATA = ROOT / 'data' / VERSION
MODELS = ROOT / 'models' / VERSION
REPORTS = ROOT / 'reports' / VERSION
CONFIG = ROOT / 'config' / f'{VERSION}.json'


def assert_writable(path) -> Path:
    """Refuse writes outside this version's namespace (frozen artifacts stay untouched)."""
    path = Path(path).resolve()
    allowed = [p.resolve() for p in (DATA, MODELS, REPORTS)]
    if not any(path == a or a in path.parents for a in allowed):
        raise PermissionError(f'{path} is outside the {VERSION} namespace')
    return path
