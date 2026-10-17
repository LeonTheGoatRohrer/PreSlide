import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import register  # noqa: E402


def _config(tmp_path, data_hash=None):
    data = tmp_path / 'data.txt'
    data.write_text('x', encoding='utf-8')
    cfg = {k: 'x' for k in register.REQUIRED}
    cfg['inputs'] = {'dataset': str(data), 'dataset_sha256': data_hash or hashlib.sha256(b'x').hexdigest()}
    path = tmp_path / 'cfg.json'
    path.write_text(json.dumps(cfg), encoding='utf-8')
    return path


def test_registration_is_write_once_and_detects_config_change(tmp_path):
    cfg, out = _config(tmp_path), tmp_path / 'reports'
    register.register(cfg, out)
    with pytest.raises(SystemExit):
        register.register(cfg, out)
    register.assert_registered(cfg, out)
    os.chmod(cfg, stat.S_IWRITE)
    cfg.write_text(cfg.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    with pytest.raises(SystemExit):
        register.assert_registered(cfg, out)


def test_registration_rejects_wrong_input_hash_and_missing_fields(tmp_path):
    with pytest.raises(SystemExit):
        register.register(_config(tmp_path, data_hash='0' * 64), tmp_path / 'r1')
    bad = tmp_path / 'bad.json'
    bad.write_text('{"version": "v"}', encoding='utf-8')
    with pytest.raises(SystemExit):
        register.register(bad, tmp_path / 'r2')
