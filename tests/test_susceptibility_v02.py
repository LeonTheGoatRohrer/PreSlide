"""susceptibility_v02 Phase 0 safety tests: trigger separation, unseen confirmatory test sets, mapping extents,
sealed v01 blind test, DEM date, multiplicity, registration hash and write/read guards.

Configurations are modified in-memory copies of the registered config; nothing is written to data/ or reports/.
"""
import copy

import pytest

from preslide.common import read_json
from preslide.sources import ROOT
from preslide.susceptibility import v02 as V

CFG = read_json(ROOT / 'config/susceptibility_v02.json')


def cfg():
    return copy.deepcopy(CFG)


def ds(c, key):
    return c['registry']['datasets'][key]


def with_extents(c):
    """The registered config with both pending inventories promoted as Phase 1 would do after obtaining extents."""
    for key in ('iburi_2018', 'rer2023'):
        ds(c, key).update(role='development')
        ds(c, key)['mapping_extent'] = {'status': 'available', 'source': 'test fixture extent'}
    return c


def test_registered_config_is_valid():
    assert V.validate(cfg())
    assert V.validate(with_extents(cfg()))


def test_registered_config_matches_preregistration():
    if not V.REGISTRATION.exists():
        pytest.skip('not registered yet')
    assert V.text_sha(V.CONFIG) == read_json(V.REGISTRATION)['config_sha256']
    assert V.config()['version'] == V.VERSION


@pytest.mark.parametrize('name,mutate,message', [
    ('rain inventory in earthquake arm', lambda c: c['trigger_arms']['earthquake']['inventories'].append('far_western_nepal'), 'is a rain inventory'),
    ('earthquake inventory in rain arm', lambda c: c['trigger_arms']['rain']['inventories'].append('gorkha_2015'), 'is a earthquake inventory'),
    ('sealed dataset in an arm', lambda c: c['trigger_arms']['rain']['inventories'].append('iffi_suedtirol'), "role 'sealed_not_used'"),
    ('excluded dataset in an arm', lambda c: c['trigger_arms']['earthquake']['inventories'].append('wenchuan_fan2019'), "role 'excluded'"),
    ('sealed test dropped', lambda c: ds(c, 'iffi_suedtirol').update(role='excluded'), 'sealed_not_used'),
    ('single inventory per trigger', lambda c: c['trigger_arms']['rain'].update(inventories=['far_western_nepal']), 'at least two'),
    ('confirmatory test seen in v01', lambda c: c['trigger_arms']['earthquake'].update(confirmatory_train='iburi_2018', confirmatory_test='gorkha_2015'), 'seen in v01'),
    ('confirmatory test equals train', lambda c: c['trigger_arms']['rain'].update(confirmatory_test='far_western_nepal'), 'two different'),
    ('development without extent', lambda c: ds(c, 'rer2023').update(role='development'), 'mapping extent'),
    ('extent without documented source', lambda c: ds(c, 'gorkha_2015')['mapping_extent'].update(source=' '), 'mapping extent'),
    ('licence not verified', lambda c: ds(c, 'far_western_nepal').update(license_verified_at_original=False), 'not verified'),
    ('licence missing', lambda c: ds(c, 'iburi_2018').update(license=''), 'licence missing'),
    ('DEM after event', lambda c: c['dem'].update(acquisition_end='2015-06-01'), 'DEM acquired'),
    # Far-Western Nepal has the earliest date (2001-01-01): only the same-day boundary can fire here.
    ('DEM on event day', lambda c: c['dem'].update(acquisition_end='2001-01-01'), 'DEM acquired'),
    ('no ShakeMap for earthquake', lambda c: ds(c, 'iburi_2018').pop('shakemap_event_id'), 'ShakeMap'),
    ('unknown role', lambda c: ds(c, 'rer2023').update(role='train'), 'not allowed'),
    ('confirmatory test added without correction', lambda c: c['hypotheses']['H3_TPI_sign'].update(type='confirmatory'), 'multiplicity'),
    ('ratio changed', lambda c: c['sampling'].update(class_ratio_positive_to_background=[1, 5]), 'ratio'),
])
def test_injected_registry_bug_is_rejected(name, mutate, message):
    c = cfg()
    mutate(c)
    with pytest.raises(ValueError, match=message):
        V.validate(c)


def test_bonferroni_lower_bound():
    assert V.lower_bound_percentile(cfg()) == pytest.approx(0.625)


def test_pending_inventories_cannot_be_trained_or_tested():
    c = cfg()
    for trigger, held in (('earthquake', 'iburi_2018'), ('earthquake', 'gorkha_2015'), ('rain', 'rer2023')):
        with pytest.raises(ValueError, match='pending_extent'):
            V.training_datasets(c, trigger, held)
    with pytest.raises(ValueError, match='pending_extent'):
        V.cross_trigger_reference(c, 'rer2023')


def test_training_never_contains_held_out_or_other_trigger():
    c = with_extents(cfg())
    for trigger in V.TRIGGERS:
        for held in c['trigger_arms'][trigger]['inventories']:
            train = V.training_datasets(c, trigger, held)
            assert held not in train and train
            assert all(ds(c, m)['trigger_class'] == trigger for m in train)
    with pytest.raises(ValueError, match='not an inventory'):
        V.training_datasets(c, 'rain', 'gorkha_2015')
    c['trigger_arms']['rain']['inventories'].append('gorkha_2015')
    with pytest.raises(ValueError, match='not a rain inventory'):
        V.training_datasets(c, 'rain', 'rer2023')


def test_cross_trigger_reference_uses_other_trigger():
    c = with_extents(cfg())
    assert V.cross_trigger_reference(c, 'iburi_2018') == 'far_western_nepal'
    assert V.cross_trigger_reference(c, 'rer2023') == 'gorkha_2015'


def test_changed_config_is_refused(tmp_path):
    path, reg = tmp_path / 'c.json', tmp_path / 'r.json'
    path.write_bytes((V.CONFIG).read_bytes())
    reg.write_text('{"config_sha256": "%s"}' % V.text_sha(path), encoding='utf-8')
    assert V.config(path, reg, tmp_path)['version'] == V.VERSION
    path.write_bytes(path.read_bytes().replace(b'"min_separation_m": 90', b'"min_separation_m": 30'))
    with pytest.raises(RuntimeError, match='changed after pre-registration'):
        V.config(path, reg, tmp_path)


@pytest.mark.parametrize('rel', ['data/susceptibility_v01/x', 'reports/susceptibility_v01', 'reports/v04', 'data', 'config'])
def test_guard_refuses_paths_outside_namespace(rel):
    with pytest.raises(RuntimeError):
        V.guard(ROOT / rel)


def test_sealed_v01_folder_is_unreadable():
    for rel in ('data/susceptibility_v01/sealed', 'data/susceptibility_v01/sealed/iffi/x.gml'):
        with pytest.raises(RuntimeError, match='sealed'):
            V.readable(ROOT / rel)
    assert V.readable(ROOT / 'data/susceptibility_v01/raw/rer2023')
    assert V.readable(ROOT / 'data/susceptibility_v01/sealed_other')
