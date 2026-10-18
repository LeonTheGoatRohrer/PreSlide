"""susceptibility_v02: trigger-specific design rules, registered configuration and write guard.

v01 modules (registry.py, paths.py) are hashed in the v01 pre-registration and stay unchanged; v02 reuses their
amendment and hashing helpers and adds the trigger rules here. Pure functions on the configuration dict plus a
thin IO layer (config, guard).
"""
import os
from datetime import date
from pathlib import Path

from ..baseline import frozen_paths
from ..common import read_json
from ..sources import ROOT
from .paths import amendments, text_sha
from .registry import apply_amendments

VERSION = 'susceptibility_v02'
CONFIG = ROOT / f'config/{VERSION}.json'
REGISTRATION = ROOT / f'reports/{VERSION}/PREREGISTRATION.json'
DATA = ROOT / f'data/{VERSION}'
MODELS = ROOT / f'models/{VERSION}'
REPORT = ROOT / f'reports/{VERSION}'
ROOTS = (DATA, MODELS, REPORT)
V01_SEALED = ROOT / 'data/susceptibility_v01/sealed'

TRIGGERS = ('earthquake', 'rain')
USABLE = 'development'
EXTENT_OK = 'available'


def validate(cfg):
    """Raise ValueError listing every violated v02 rule; return True otherwise."""
    errors = []
    reg = cfg['registry']
    datasets = reg['datasets']
    first_dates = []
    for key, d in datasets.items():
        role = d['role']
        if role not in reg['allowed_roles']:
            errors.append(f'{key}: role {role!r} not allowed')
        if not str(d.get('license') or '').strip():
            errors.append(f'{key}: licence missing')
        if role == USABLE:
            ext = d.get('mapping_extent') or {}
            if ext.get('status') != EXTENT_OK or not str(ext.get('source') or '').strip():
                errors.append(f'{key}: development dataset needs an available, documented mapping extent')
            if not d.get('license_verified_at_original'):
                errors.append(f'{key}: licence not verified at the original record')
        if role in (USABLE, 'pending_extent'):
            if d.get('trigger_class') not in TRIGGERS:
                errors.append(f'{key}: trigger class {d.get("trigger_class")!r} not in {TRIGGERS}')
            if d.get('earliest_event_date'):
                first_dates.append((key, d['earliest_event_date']))
    dem_end = date.fromisoformat(cfg['dem']['acquisition_end'])
    for key, first in first_dates:
        if not dem_end < date.fromisoformat(first):
            errors.append(f'{key}: DEM acquired on or after the earliest event ({first})')

    arms = cfg['trigger_arms']
    for trigger in TRIGGERS:
        arm = arms[trigger]
        members = arm['inventories']
        if len(members) < 2:
            errors.append(f'{trigger}: leave-one-inventory-out needs at least two inventories')
        for m in members:
            d = datasets.get(m)
            if d is None:
                errors.append(f'{trigger}: unknown dataset {m}')
            elif d['role'] not in (USABLE, 'pending_extent'):
                errors.append(f'{trigger}: {m} has role {d["role"]!r}')
            elif d['trigger_class'] != trigger:
                errors.append(f'{trigger}: {m} is a {d["trigger_class"]} inventory')
        train, test = arm['confirmatory_train'], arm['confirmatory_test']
        if train == test or train not in members or test not in members:
            errors.append(f'{trigger}: confirmatory train/test must be two different arm members')
        elif datasets[test].get('seen_in_v01', True):
            errors.append(f'{trigger}: confirmatory test inventory {test} was seen in v01')
        if trigger == 'earthquake':
            for m in members:
                if m in datasets and not datasets[m].get('shakemap_event_id'):
                    errors.append(f'earthquake: {m} has no ShakeMap event id')

    blind = [k for k, d in datasets.items() if d['role'] == 'sealed_not_used']
    if not blind:
        errors.append('the v01 sealed blind test must stay registered as sealed_not_used')
    tests = cfg['hypotheses']
    confirmatory = [k for k, h in tests.items() if isinstance(h, dict) and h.get('type') == 'confirmatory']
    n_tests = len(confirmatory)
    if n_tests != 4 or f'0.025/{n_tests}' not in cfg['evaluation']['multiplicity']:
        errors.append(f'multiplicity correction must cover the {n_tests} confirmatory tests')
    if cfg['sampling']['class_ratio_positive_to_background'] != [1, 1]:
        errors.append('class ratio must stay 1:1 as registered')
    if errors:
        raise ValueError('; '.join(errors))
    return True


def lower_bound_percentile(cfg):
    """Percentile of the paired bootstrap difference used as the confirmatory lower bound (Bonferroni)."""
    n = sum(1 for h in cfg['hypotheses'].values() if isinstance(h, dict) and h.get('type') == 'confirmatory')
    return 100 * 0.025 / n


def training_datasets(cfg, trigger, held_out):
    """Inventories an arm trains on when `held_out` is the test inventory.

    Only development datasets of the same trigger; pending, excluded and sealed datasets are refused."""
    arm = cfg['trigger_arms'][trigger]
    datasets = cfg['registry']['datasets']
    if held_out not in arm['inventories']:
        raise ValueError(f'{held_out} is not an inventory of the {trigger} arm')
    out = [m for m in arm['inventories'] if m != held_out]
    for m in out + [held_out]:
        d = datasets[m]
        if d['role'] != USABLE:
            raise ValueError(f'{m} has role {d["role"]!r}; only development inventories can be used')
        if d['trigger_class'] != trigger:
            raise ValueError(f'{m} is not a {trigger} inventory')
    return out


def cross_trigger_reference(cfg, test):
    """Training inventory of the H2 reference model for `test` (the other trigger's seen inventory)."""
    datasets = cfg['registry']['datasets']
    own = datasets[test]['trigger_class']
    other = next(t for t in TRIGGERS if t != own)
    train = cfg['trigger_arms'][other]['confirmatory_train']
    for m in (train, test):
        if datasets[m]['role'] != USABLE:
            raise ValueError(f'{m} has role {datasets[m]["role"]!r}; only development inventories can be used')
    return train


def guard(path):
    """Create directory `path` only inside the v02 roots, never on a frozen baseline path or the v01 sealed folder."""
    # abspath, not resolve: data/ and models/ may be directory junctions into the main checkout.
    path = Path(os.path.abspath(path))
    roots = [Path(os.path.abspath(r)) for r in ROOTS]
    if not any(path == r or r in path.parents for r in roots):
        raise RuntimeError(f'{VERSION} may only write under {", ".join(str(r) for r in ROOTS)}: {path}')
    rel = path.relative_to(Path(os.path.abspath(ROOT))).as_posix()
    if any(f == rel or f.startswith(rel + '/') for f in frozen_paths()):
        raise RuntimeError(f'{rel} contains frozen baseline files')
    path.mkdir(parents=True, exist_ok=True)
    return path


def readable(path):
    """Refuse any read below the v01 sealed blind-test folder."""
    path = Path(os.path.abspath(path))
    sealed = Path(os.path.abspath(V01_SEALED))
    if path == sealed or sealed in path.parents:
        raise RuntimeError(f'{VERSION} never reads the sealed susceptibility_v01 blind test: {path}')
    return path


def config(path=CONFIG, registration=REGISTRATION, report=REPORT):
    """Registered configuration plus amendments; refuses to run if the config changed after registration."""
    cfg = read_json(path)
    if Path(registration).exists() and text_sha(path) != read_json(registration)['config_sha256']:
        raise RuntimeError(f'{path} changed after pre-registration; write an amendment or a new version')
    apply_amendments(cfg, amendments(report))
    validate(cfg)
    return cfg
