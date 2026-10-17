"""HTTP access for susceptibility_v01 through curl (system TLS store; verification stays on), with checksum-verified raw files.

Raw downloads are write-once: an existing file is reused only if its checksum matches the record.
"""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

MAX_TIME_S = 1800


def _curl():
    curl = shutil.which('curl.exe') or shutil.which('curl')
    if not curl:
        raise RuntimeError('curl is required (TLS certificate verification remains enabled)')
    return curl


def url_with(url, params=None):
    return url + ('?' + urlencode(params) if params else '')


def fetch_bytes(url, params=None, method='GET'):
    """Body of a 200 response; raises on any other status."""
    args = [_curl(), '--silent', '--show-error', '--location', '--max-time', str(MAX_TIME_S), '-w', '\n%{http_code}']
    if method == 'HEAD':
        args += ['--head']
    result = subprocess.run(args + [url_with(url, params)], capture_output=True, timeout=MAX_TIME_S + 60)
    body, _, code = result.stdout.rpartition(b'\n')
    if result.returncode != 0 or code != b'200':
        raise RuntimeError(f'HTTP {code.decode() or "?"} for {url}: {result.stderr[:300]!r}')
    return body


def fetch_json(url, params=None):
    return json.loads(fetch_bytes(url, params))


def file_digest(path, algorithm):
    h = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def head(url):
    """Lower-cased response headers of a HEAD request (200 only)."""
    text = fetch_bytes(url, method='HEAD').decode('latin-1')
    block = text.replace('\r\n', '\n').strip().split('\n\n')[-1]
    return {k.strip().lower(): v.strip() for k, _, v in (line.partition(':') for line in block.split('\n')[1:]) if k}


def download_object(url, target, query=''):
    """Object without a published checksum (S3 / Azure blob): size from HEAD must match; a single-part S3 ETag or an
    Azure Content-MD5 is verified as md5. `query` (e.g. a SAS token) is appended for transfer only, never recorded."""
    import base64
    target = Path(target)
    h = head(url + query)
    size = int(h['content-length'])
    etag = h.get('etag', '').strip('"')
    md5 = etag if etag and '-' not in etag and len(etag) == 32 else None
    if not md5 and h.get('content-md5'):
        md5 = base64.b64decode(h['content-md5']).hex()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_suffix(target.suffix + '.part')
        result = subprocess.run([_curl(), '--fail', '--silent', '--show-error', '--location', '--retry', '2',
                                 '--max-time', str(MAX_TIME_S), '--output', str(part), url + query],
                                capture_output=True, timeout=MAX_TIME_S + 60)
        if result.returncode != 0:
            raise RuntimeError(f'download failed for {url}: {result.stderr[:300]!r}')
        part.replace(target)
    if target.stat().st_size != size:
        raise RuntimeError(f'{target}: {target.stat().st_size} B, server reports {size} B')
    if md5 and file_digest(target, 'md5') != md5:
        raise RuntimeError(f'{target}: md5 does not match the server ETag/Content-MD5')
    return {'url': url, 'file': target.name, 'size_bytes': size, 'md5_verified': bool(md5),
            'sha256': file_digest(target, 'sha256'), 'last_modified': h.get('last-modified'),
            'verified_at_utc': datetime.now(timezone.utc).isoformat()}


def download(url, target, checksum, size_bytes):
    """Download `url` to `target` once; `checksum` is 'md5:<hex>' as published by the record. Returns provenance."""
    target = Path(target)
    algorithm, expected = checksum.split(':', 1)
    if not target.exists():
        part = target.with_suffix(target.suffix + '.part')
        result = subprocess.run([_curl(), '--fail', '--silent', '--show-error', '--location', '--retry', '2',
                                 '--max-time', str(MAX_TIME_S), '--output', str(part), url],
                                capture_output=True, timeout=MAX_TIME_S + 60)
        if result.returncode != 0:
            raise RuntimeError(f'download failed for {url}: {result.stderr[:300]!r}')
        part.replace(target)
    got = file_digest(target, algorithm)
    if got != expected or target.stat().st_size != size_bytes:
        raise RuntimeError(f'{target}: {algorithm} {got} / {target.stat().st_size} B does not match record '
                           f'{expected} / {size_bytes} B')
    return {'url': url, 'file': target.name, 'size_bytes': size_bytes, checksum.split(':')[0]: got,
            'sha256': file_digest(target, 'sha256'), 'verified_at_utc': datetime.now(timezone.utc).isoformat()}
