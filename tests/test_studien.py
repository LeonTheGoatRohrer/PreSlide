"""Study atlas registry and API: stored values only, missing files never replaced, every report folder covered."""
import json
import re

import pytest
from fastapi import HTTPException

from preslide import studien
from preslide.common import read_json
from preslide.sources import ROOT

REGISTRY = read_json(ROOT / 'config/studien_atlas.json')
BANNED = re.compile(r'wahrscheinlich|risik|vorhersag|prognos|gefährdet', re.IGNORECASE)


def test_every_report_folder_with_a_summary_is_registered_or_excluded():
    registered = {e['bericht'] for e in REGISTRY['studien'] if e.get('bericht')}
    excluded = set(REGISTRY.get('ausgenommen', {}))
    for summary in sorted((ROOT / 'reports').glob('*/summary.md')):
        relative = summary.relative_to(ROOT).as_posix()
        assert relative in registered or summary.parent.relative_to(ROOT).as_posix() in excluded, relative


def test_registry_ids_unique_and_groups_and_status_known():
    ids = [e['id'] for e in REGISTRY['studien']]
    assert len(ids) == len(set(ids))
    groups = {g['id'] for g in REGISTRY['gruppen']}
    for e in REGISTRY['studien']:
        assert set(e['gruppen']) <= groups, e['id']
        assert e['status'] in REGISTRY['status_bedeutung'], e['id']


def test_registry_texts_avoid_probability_and_risk_wording():
    hit = BANNED.search(json.dumps(REGISTRY, ensure_ascii=False))
    assert hit is None, hit and hit.group(0)


def test_registered_paths_resolve_in_this_checkout():
    # A wrong JSON path must not silently hide a figure: only a missing file may make a figure unavailable.
    for s in studien.atlas()['studien']:
        for f in s['kennzahlen']:
            if f['verfuegbar']:
                assert isinstance(f['wert'], (int, float)), (s['id'], f['label'])
                if 'intervall' in f:
                    assert f['intervall'][0] <= f['intervall'][1], (s['id'], f['label'])
            else:
                assert 'nicht vor' in f['grund'], (s['id'], f)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_missing_file_gives_unavailable_with_reason_and_no_value(tmp_path):
    _write(tmp_path / 'reports/a/results.json', {'test': {'results': {'m/combined': {'auc': 0.7, 'ci95': [0.6, 0.8]}}, 'n': {'units': 11}}})
    (tmp_path / 'reports/a/summary.md').write_text('# A', encoding='utf-8')
    fig = {'label': 'x', 'art': 'auc', 'datei': 'reports/a/results.json', 'pfad': 'test.results.m/combined.auc',
           'intervall': {'pfad': 'test.results.m/combined.ci95'}, 'einheiten': {'pfad': 'test.n.units'}}
    entry = {'id': 'a', 'titel': 'A', 'bericht': 'reports/a/summary.md', 'kennzahlen': [fig]}
    ok = studien.study(entry, tmp_path)
    assert ok['verfuegbar'] and ok['kennzahlen'][0] == {'label': 'x', 'art': 'auc', 'wert': 0.7, 'intervall': [0.6, 0.8], 'einheiten': 11, 'verfuegbar': True}
    gone = studien.study({**entry, 'kennzahlen': [{**fig, 'datei': 'reports/a/fehlt.json'}]}, tmp_path)
    assert gone['verfuegbar'] is False and gone['grund']
    assert 'wert' not in gone['kennzahlen'][0] and 'intervall' not in gone['kennzahlen'][0]
    no_report = studien.study({**entry, 'bericht': 'reports/b/summary.md'}, tmp_path)
    assert no_report['verfuegbar'] is False and no_report['bericht'] is False
    wrong_path = studien.study({**entry, 'kennzahlen': [{**fig, 'pfad': 'test.results.m/combined.nope'}]}, tmp_path)
    assert wrong_path['verfuegbar'] is False and 'wert' not in wrong_path['kennzahlen'][0]


def test_interval_must_be_two_sided_numbers(tmp_path):
    _write(tmp_path / 'r.json', {'v': 0.5, 'ci': [0.4], 'flag': True})
    bad = studien.resolve_figure({'label': 'x', 'datei': 'r.json', 'pfad': 'v', 'intervall': {'pfad': 'ci'}}, tmp_path)
    assert bad['verfuegbar'] is False and 'intervall' not in bad
    boolean = studien.resolve_figure({'label': 'x', 'datei': 'r.json', 'pfad': 'flag'}, tmp_path)
    assert boolean['verfuegbar'] is False


def test_json_path_handles_slashes_and_indices():
    data = {'a': {'b/c': [{'d': 1}, {'d': 2}]}}
    assert studien.json_path(data, 'a.b/c[1].d') == 2
    with pytest.raises(KeyError):
        studien.json_path(data, 'a.b/c[5].d')
    with pytest.raises(KeyError):
        studien.json_path(data, 'a.x')


def test_report_endpoint_serves_only_registered_paths():
    with pytest.raises(HTTPException) as unknown:
        studien.bericht('../../AGENTS')
    assert unknown.value.status_code == 404
    with pytest.raises(ValueError):
        studien.inside_root('../outside.md')
    first = next(e for e in REGISTRY['studien'] if e.get('bericht') and (ROOT / e['bericht']).exists())
    assert studien.bericht(first['id']).body.decode('utf-8').strip()
