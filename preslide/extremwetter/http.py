"""Immutable JSON response cache for extremwetter_v01 (data/extremwetter_v01/cache/http)."""
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone

from ..v04.http import _read, full_url
from .paths import DATA, guard

_last_call = [0.0]
STATS = {'hits': 0, 'downloads': 0}


def cached_json(url, params, min_interval_s=15.5):
    target = full_url(url, params)
    key = hashlib.sha256(target.encode()).hexdigest()
    path = DATA / 'cache/http' / f'{key}.json'
    if path.exists():
        STATS['hits'] += 1
        return _read(path, target)
    guard(path.parent)
    wait = _last_call[0] + min_interval_s - time.time()
    if wait > 0:
        time.sleep(wait)
    curl = shutil.which('curl.exe') or shutil.which('curl')
    for attempt in range(5):
        _last_call[0] = time.time()
        result = subprocess.run([curl, '--silent', '--show-error', '--location', '--max-time', '300',
                                 '-w', '\n%{http_code}', target], capture_output=True, timeout=360)
        body, _, code = result.stdout.rpartition(b'\n')
        if result.returncode == 0 and code == b'200':
            break
        if code == b'429' or code.startswith(b'5') or result.returncode != 0:
            time.sleep(20 * (attempt + 1) if code != b'429' else 90)
            continue
        raise RuntimeError(f'HTTP {code.decode()} for {target[:200]}: {body[:300]!r}')
    else:
        raise RuntimeError(f'Request failed after retries: {target[:200]}')
    data = json.loads(body)
    if isinstance(data, dict) and 'error' in data:
        raise RuntimeError(f"Source error: {data['error']}")
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(body)
    tmp.replace(path)
    path.with_suffix('.meta.json').write_text(json.dumps({'url': target, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                                                          'sha256': hashlib.sha256(body).hexdigest()}, indent=1), encoding='utf-8')
    STATS['downloads'] += 1
    return data
