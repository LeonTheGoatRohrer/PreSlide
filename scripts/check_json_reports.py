"""Fail if a tracked JSON file under reports/ or config/ is not valid JSON (CI guard)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bad = []
paths = [p for d in ('reports', 'config') for p in sorted((ROOT / d).rglob('*.json'))]
for p in paths:
    try:
        json.loads(p.read_text(encoding='utf-8'))
    except Exception as exc:  # noqa: BLE001 - report every broken file
        bad.append(f'{p.relative_to(ROOT)}: {exc}')
print(f'{len(paths)} JSON files checked, {len(bad)} invalid')
sys.exit('\n'.join(bad) if bad else 0)
