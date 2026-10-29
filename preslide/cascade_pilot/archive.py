"""Read audited Landslide4Sense ZIP members without re-downloading an active local prefix.

Only data bytes are fetched; ZIP CRC and SHA-256 sidecars are checked. No archive code is executed.
"""
from __future__ import annotations

import io
import struct
import threading
import time
import zipfile
import zlib
from pathlib import Path

import requests

from ..baseline import sha
from ..common import read_json, write_json
from ..sources import ROOT
from .context import DATA, guard

URL = 'https://zenodo.org/records/10463239/files/TrainData.zip?download=1'
PREFIX = ROOT / 'data/satellite_nn_v01/raw/TrainData.zip'
CA = ROOT / 'data/runtime/windows-ca.pem'
_THREAD = threading.local()


def get_range(start: int | None, end: int) -> bytes:
    if not hasattr(_THREAD, 'session'):
        _THREAD.session = requests.Session()
    value = f'bytes={start}-{end}' if start is not None else f'bytes=-{end}'
    for attempt in range(3):
        response = _THREAD.session.get(URL, headers={'Range': value}, verify=str(CA), timeout=40)
        if response.status_code != 429:
            break
        delay = min(60, max(10, int(response.headers.get('Retry-After', '30'))))
        response.close()
        print(f'Source rate limit: respecting {delay}s pause (attempt {attempt + 1}/3)', flush=True)
        time.sleep(delay)
    response.raise_for_status()
    if response.status_code != 206:
        raise RuntimeError('Server did not honour byte range; refusing a full duplicate download')
    if start is not None and len(response.content) != end - start + 1:
        raise RuntimeError('Truncated range response')
    return response.content


def cache_masks() -> None:
    """One contiguous request for all tiny mask entries instead of thousands of requests."""
    z = index()
    start = min(i.header_offset for i in z.infolist() if '/mask/' in i.filename and i.filename.endswith('.h5'))
    end = read_json((DATA / 'raw/l4s_directory.zip').with_suffix('.json'))['original_directory_offset']
    path = guard(DATA / 'raw/l4s_masks_region.bin')
    if not path.exists():
        result = get_range(start, end - 1)
        path.write_bytes(result)
        write_json(path.with_suffix('.json'), {'start': start, 'end': end, 'sha256': sha(path), 'url': URL})
    if sha(path) != read_json(path.with_suffix('.json'))['sha256']:
        raise ValueError('Mask region cache corrupted')


def index() -> zipfile.ZipFile:
    path = guard(DATA / 'raw/l4s_directory.zip')
    if not path.exists():
        tail = get_range(None, 65536)
        offset = tail.rfind(b'PK\x05\x06')
        if offset < 0:
            raise ValueError('ZIP end-of-directory missing')
        end = bytearray(tail[offset:])
        fields = struct.unpack('<4s4H2LH', end[:22])
        size, start = fields[5:7]
        central = get_range(start, start + size - 1)
        struct.pack_into('<L', end, 16, 0)  # local directory-only ZIP; original member offsets stay in entries
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(central + end)
        write_json(path.with_suffix('.json'), {'url': URL, 'sha256': sha(path), 'original_directory_offset': start})
    if sha(path) != read_json(path.with_suffix('.json'))['sha256']:
        raise ValueError('ZIP directory cache corrupted')
    return zipfile.ZipFile(path)


def member(info: zipfile.ZipInfo) -> bytes:
    """Read one member, preferring already downloaded source bytes; verify uncompressed CRC."""
    path = guard(DATA / 'raw/l4s_members' / info.filename)
    if path.exists():
        if sha(path) != read_json(path.with_suffix('.json'))['sha256']:
            raise ValueError(f'Corrupt HDF5 cache: {info.filename}')
        return path.read_bytes()
    start = info.header_offset
    header = None
    mask_region = DATA / 'raw/l4s_masks_region.bin'
    mask_start = None
    if '/mask/' in info.filename and mask_region.exists():
        meta = read_json(mask_region.with_suffix('.json'))
        mask_start = meta['start']
        with mask_region.open('rb') as f:
            f.seek(start - mask_start)
            header = f.read(30)
    # The other local task owns this growing file; we never write, rename or truncate it.
    if header is None and PREFIX.exists() and PREFIX.stat().st_size > start + 30:
        with PREFIX.open('rb') as f:
            f.seek(start)
            header = f.read(30)
    if header is None:
        header = get_range(start, start + 29)
    if header[:4] != b'PK\x03\x04':
        raise ValueError(f'Bad ZIP local header: {info.filename}')
    name_len, extra_len = struct.unpack('<HH', header[26:30])
    payload_start = start + 30 + name_len + extra_len
    payload_end = payload_start + info.compress_size
    if mask_start is not None:
        with mask_region.open('rb') as f:
            f.seek(payload_start - mask_start)
            payload = f.read(info.compress_size)
    elif PREFIX.exists() and PREFIX.stat().st_size >= payload_end:
        with PREFIX.open('rb') as f:
            f.seek(payload_start)
            payload = f.read(info.compress_size)
    else:
        payload = get_range(payload_start, payload_end - 1)
    if info.compress_type == zipfile.ZIP_STORED:
        result = payload
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        result = zlib.decompress(payload, -15)
    else:
        raise ValueError('Unsupported ZIP compression')
    if len(result) != info.file_size or (zlib.crc32(result) & 0xffffffff) != info.CRC:
        raise ValueError(f'ZIP CRC mismatch: {info.filename}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result)
    write_json(path.with_suffix('.json'), {'source_url': URL, 'member': info.filename, 'crc32': info.CRC, 'sha256': sha(path)})
    return result


def arrays(sample_id: int):
    import h5py
    import numpy as np
    z = index()
    names = z.namelist()
    image = next(n for n in names if n.endswith(f'/img/image_{sample_id}.h5'))
    mask = next(n for n in names if n.endswith(f'/mask/mask_{sample_id}.h5'))
    with h5py.File(io.BytesIO(member(z.getinfo(image))), 'r') as f:
        x = f['img'][:]
    with h5py.File(io.BytesIO(member(z.getinfo(mask))), 'r') as f:
        y = f['mask'][:]
    if x.shape != (128, 128, 14) or y.shape != (128, 128):
        raise ValueError(f'Unexpected image/mask shapes: {x.shape}, {y.shape}')
    if not np.isfinite(x).all() or not set(np.unique(y)).issubset({0, 1}):
        raise ValueError('Nonfinite image or invalid mask labels')
    return x, y
