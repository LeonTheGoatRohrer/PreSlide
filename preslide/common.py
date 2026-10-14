import hashlib
import json
from pathlib import Path
from .sources import ROOT

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=str), encoding='utf-8')
    tmp.replace(path)

BASELINE_CANDIDATES = 'data/interim/quality_candidates_pending_source_clearance.json'

def experiment_config(path='config/experiment.json'):
    return read_json(ROOT/path)

def candidates(path=BASELINE_CANDIDATES):
    rows = read_json(ROOT/path)
    if path == BASELINE_CANDIDATES and len(rows) != 102:
        raise ValueError('Expected accepted 102-event audit snapshot; inspect any changed snapshot explicitly')
    if len({r['event_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate event_id in candidate snapshot')
    return rows
