"""V0.9 media process audit (config/v09.json process_audit): blinded worksheet, validated ingestion, quality gate.

  python -m preslide.v09.audit worksheet           # data/v09/audit/process_audit_worksheet.json (blinded fields only)
  python -m preslide.v09.audit ingest <file.json>  # validates and writes data/v09/audit/process_audit.json (write-once)
  python -m preslide.v09.audit summary             # reports/v09/process_audit_summary.json
"""
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone

from ..common import read_json, write_json
from .paths import V09_DATA, V09_REPORT, config as load_config, guard, sha

AUDIT = V09_DATA / 'audit'
BLINDED = ['event_id', 'municipality', 'state', 'reported_day', 'process_type_original', 'date_text_original']
REQUIRED = ['event_id', 'category', 'urls', 'publisher', 'publication_date', 'retrieved_utc', 'paraphrase']


def wilson_upper(k, n, z=1.959963984540054):
    """Upper bound of the Wilson score interval for a binomial proportion k/n (two-sided 95 % by default)."""
    if n == 0:
        return 1.0
    p = k / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre + half) / (1 + z * z / n)


def gate(categories, cfg):
    """Quality gate of the registered process audit. `categories`: iterable of category strings."""
    c = Counter(categories)
    n, k = c['slide_confirmed'] + c['other_process'], c['other_process']
    upper = wilson_upper(k, n)
    rule = cfg['process_audit']['quality_gate']
    return {'counts': dict(c), 'n_verifiable': n, 'k_other_process': k, 'wilson_upper_95': upper,
            'passes': bool(n >= 20 and upper <= 0.25), 'rule': rule}


def media_events():
    rows = json.loads((AUDIT / 'candidates.json').read_text(encoding='utf-8'))
    return [r for r in rows if r['cohort'] == 'media']


def worksheet():
    load_config()
    rows = [{k: r[k] for k in BLINDED} for r in media_events()]
    path = guard(AUDIT) / 'process_audit_worksheet.json'
    write_json(path, {'protocol': load_config()['process_audit'], 'events': rows})
    print(f'{len(rows)} events -> {path}')


def validate(entries, cfg, events):
    allowed = set(cfg['process_audit']['categories'])
    ids = [e['event_id'] for e in entries]
    expected = {e['event_id'] for e in events}
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate event_id in audit')
    if set(ids) != expected:
        raise ValueError(f'Audit must cover exactly the eligible media events: missing {sorted(expected - set(ids))[:5]}, '
                         f'extra {sorted(set(ids) - expected)[:5]}')
    for e in entries:
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            raise ValueError(f"{e.get('event_id')}: missing fields {missing}")
        if e['category'] not in allowed:
            raise ValueError(f"{e['event_id']}: unknown category {e['category']}")
        if e['category'] != 'not_found' and not e['urls']:
            raise ValueError(f"{e['event_id']}: category {e['category']} needs at least one URL")
    return entries


def ingest(path):
    cfg = load_config()
    target = guard(AUDIT) / 'process_audit.json'
    if target.exists():
        raise SystemExit('process_audit.json exists (write-once)')
    entries = validate(json.loads(open(path, encoding='utf-8').read()), cfg, media_events())
    write_json(target, {'ingested_utc': datetime.now(timezone.utc).isoformat(), 'entries': entries})
    summary()


def decisions(cfg=None):
    """event_id -> (category, in_main_set, in_sensitivity_set)."""
    entries = read_json(AUDIT / 'process_audit.json')['entries']
    out = {}
    for e in entries:
        c = e['category']
        out[e['event_id']] = (c, c in ('slide_confirmed', 'ambiguous', 'not_found'), c == 'slide_confirmed')
    return out


def summary():
    cfg = load_config()
    path = AUDIT / 'process_audit.json'
    entries = read_json(path)['entries']
    result = {'audit_sha256': sha(path), 'events': len(entries), 'gate': gate([e['category'] for e in entries], cfg),
              'excluded': sorted(e['event_id'] for e in entries if e['category'] in ('other_process', 'date_conflict'))}
    write_json(guard(V09_REPORT) / 'process_audit_summary.json', result)
    print(json.dumps(result, indent=1))
    return result


if __name__ == '__main__':
    step = sys.argv[1]
    if step == 'worksheet':
        worksheet()
    elif step == 'ingest':
        ingest(sys.argv[2])
    elif step == 'summary':
        summary()
    else:
        raise SystemExit(__doc__)
