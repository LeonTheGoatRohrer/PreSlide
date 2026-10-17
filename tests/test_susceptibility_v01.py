"""susceptibility_v01 Phase 0 safety tests: sealed blind test isolation, registry rules, DEM date, amendments, write guard.

Configurations below are modified in-memory copies of the registered config; nothing is written to data/ or reports/.
"""
import copy
import json

import pytest

from preslide.common import read_json
from preslide.sources import ROOT
from preslide.susceptibility import paths as P
from preslide.susceptibility import registry as G

CFG = read_json(ROOT / 'config/susceptibility_v01.json')
SEALED = CFG['south_tyrol_blind_test']['dataset']


def cfg():
    return copy.deepcopy(CFG)


def broken(mutate):
    c = cfg()
    mutate(c)
    return c


def test_registered_config_is_valid():
    assert G.validate(cfg())


def test_registered_config_matches_preregistration():
    if not P.REGISTRATION.exists():
        pytest.skip('not registered yet')
    assert P.text_sha(P.CONFIG) == read_json(P.REGISTRATION)['config_sha256']
    assert P.config()['version'] == 'susceptibility_v01'


@pytest.mark.parametrize('name,mutate,message', [
    ('sealed in training arm', lambda c: c['arms']['MODEL_Q'].append(SEALED), 'not a development dataset'),
    ('sealed allows training', lambda c: c['registry']['datasets'][SEALED].update(train_allowed=True), 'train_allowed'),
    ('sealed allows thresholds', lambda c: c['registry']['datasets'][SEALED].pop('threshold_selection_allowed'), 'threshold_selection_allowed'),
    ('sealed gets mapped negatives', lambda c: c['registry']['datasets'][SEALED].update(negative_policy='inside_mapping_extent'), 'presence_background'),
    ('sealed relabelled development', lambda c: c['registry']['datasets'][SEALED].update(role='development'), 'role sealed_blind_test'),
    ('unknown role', lambda c: c['registry']['datasets']['rer2023'].update(role='train'), 'not allowed'),
    ('negatives from gaps', lambda c: c['registry']['datasets']['rer2023'].update(negative_policy='presence_background'), 'mapping extent'),
    ('incomplete mapping', lambda c: c['registry']['datasets']['gorkha_2015'].update(mapping_complete=False), 'mapping_complete'),
    ('dem after event', lambda c: c['dem'].update(acquisition_end='2015-06-01'), 'DEM acquired after'),
    ('licence missing', lambda c: c['registry']['datasets']['far_western_nepal'].update(license=' '), 'licence'),
    ('ratio mismatch', lambda c: c['south_tyrol_blind_test']['background'].update(ratio=[1, 10]), 'ratio differs'),
    ('code overlap', lambda c: c['south_tyrol_blind_test']['positive_subset']['exclude_codes'].append(2), 'overlap'),
])
def test_injected_registry_bug_is_rejected(name, mutate, message):
    with pytest.raises(ValueError, match=message):
        G.validate(broken(mutate))


def test_dem_on_event_day_boundary():
    # Acquisition ending on the event day is allowed; one day later is not.
    c = cfg()
    for key in ('gorkha_2015', 'far_western_nepal'):
        c['registry']['datasets'][key]['earliest_event_date'] = None
    c['dem']['acquisition_end'] = c['registry']['datasets']['rer2023']['earliest_event_date']
    G.validate(c)
    c['dem']['acquisition_end'] = '2023-05-02'
    with pytest.raises(ValueError, match='rer2023: DEM acquired after'):
        G.validate(c)


def test_registered_dem_predates_every_development_event():
    first = [d['earliest_event_date'] for d in CFG['registry']['datasets'].values() if d['role'] == 'development']
    assert all(CFG['dem']['acquisition_end'] < f for f in first)


def test_training_datasets_never_include_sealed():
    for arm, members in CFG['arms'].items():
        if isinstance(members, list):
            assert SEALED not in G.training_datasets(CFG, arm)
    with pytest.raises(ValueError):
        G.training_datasets(broken(lambda c: c['arms']['MODEL_D'].append(SEALED)), 'MODEL_D')


def test_amendment_fills_placeholder_only():
    c = G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 120}}])
    assert c['sampling']['background_rule']['exclusion_buffer_m'] == 120
    with pytest.raises(ValueError, match='already registered'):
        G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.cell_m': 10}}])
    with pytest.raises(ValueError, match='unknown path'):
        G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.new_threshold': 1}}])
    with pytest.raises(ValueError, match='already registered'):
        G.apply_amendments(cfg(), [{'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 120}},
                                   {'id': 2, 'set': {'sampling.background_rule.exclusion_buffer_m': 60}}])


def test_changed_config_and_tampered_amendment_are_refused(tmp_path):
    conf, reg, rep = tmp_path / 'c.json', tmp_path / 'r.json', tmp_path / 'rep'
    rep.mkdir()
    conf.write_bytes(json.dumps(CFG).encode())
    reg.write_text(json.dumps({'config_sha256': P.text_sha(conf)}))
    assert P.config(conf, reg, rep)
    am = rep / 'AMENDMENT_1.json'
    am.write_text(json.dumps({'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 120}}))
    am.with_suffix('.sha256').write_text(P.text_sha(am))
    assert P.config(conf, reg, rep)['sampling']['background_rule']['exclusion_buffer_m'] == 120
    am.write_text(json.dumps({'id': 1, 'set': {'sampling.background_rule.exclusion_buffer_m': 60}}))
    with pytest.raises(RuntimeError, match='write-once'):
        P.config(conf, reg, rep)
    am.unlink()
    conf.write_bytes(json.dumps({**CFG, 'seeds': {}}).encode())
    with pytest.raises(RuntimeError, match='changed after pre-registration'):
        P.config(conf, reg, rep)


def test_text_hash_ignores_crlf(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    a.write_bytes(b'{\n "x": 1\n}\n')
    b.write_bytes(b'{\r\n "x": 1\r\n}\r\n')
    assert P.text_sha(a) == P.text_sha(b)


@pytest.mark.parametrize('rel', ['data/v04/x', 'reports/v05/x', 'models/v04', 'reports/baseline', 'data/susceptibility_v02', 'config'])
def test_guard_refuses_paths_outside_namespace(rel, monkeypatch):
    # A broken guard must not create directories in frozen trees while the test runs.
    def no_mkdir(*a, **k):
        raise AssertionError('guard tried to create a directory outside the namespace')
    monkeypatch.setattr(P.Path, 'mkdir', no_mkdir)
    with pytest.raises(RuntimeError):
        P.guard(ROOT / rel)
