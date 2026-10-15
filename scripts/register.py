"""Write-once pre-registration of any config: ``python scripts/register.py <config.json> <reports-dir>``.

Records the config SHA-256 and the hashes of the files named under ``inputs`` (keys ending in
``_sha256`` are verified against the file next to them). Refuses to overwrite an existing registration.
"""
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('version', 'registered_on', 'registered_before', 'status', 'question', 'primary_endpoint', 'decision_rule', 'must_not_change')


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register(config_path: Path, out_dir: Path) -> dict:
    out = out_dir / 'PREREGISTRATION.json'
    if out.exists():
        raise SystemExit(f'{out} exists (write-once).')
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise SystemExit(f'config lacks required registration fields: {missing}')
    input_hashes = {}
    for key, expected in cfg.get('inputs', {}).items():
        if key.endswith('_sha256'):
            file_key = key[: -len('_sha256')]
            path = ROOT / cfg['inputs'][file_key]
            actual = sha256_file(path)
            if actual != expected:
                raise SystemExit(f'{path} does not match {key} in the config')
            input_hashes[cfg['inputs'][file_key]] = actual
    record = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'config': (config_path.relative_to(ROOT) if config_path.is_relative_to(ROOT) else config_path).as_posix(),
              'config_sha256': sha256_file(config_path), 'input_sha256': input_hashes}
    out_dir.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1), encoding='utf-8')
    for p in (out, config_path):
        os.chmod(p, stat.S_IREAD)
    return record


def assert_registered(config_path: Path, out_dir: Path) -> None:
    """Abort when the config differs from its registration (call before any run)."""
    reg = json.loads((out_dir / 'PREREGISTRATION.json').read_text(encoding='utf-8'))
    if reg['config_sha256'] != sha256_file(config_path):
        raise SystemExit(f'{config_path} changed after registration')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    print(json.dumps(register(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()), indent=1))
