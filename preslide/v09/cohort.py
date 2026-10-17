"""V0.9 cohorts: GeoSphere media events (tier 2, day tier A) and new Land Kärnten events, unseen-block selection.

  python -m preslide.v09.cohort        # writes data/v09/audit/ and reports/v09/cohort_summary.json

Pure functions (date parsing, process tokens, t0, near-duplicate tests, block selection) are unit-tested in
tests/test_v09.py; `run` is the thin IO wrapper. Nothing here looks at weather, terrain or any model output.
"""
import json
import re
from collections import Counter
from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT
from ..v04.units import temporal_episodes, blocks
from .paths import V09_DATA, V09_REPORT, config as load_config, guard, sha

V04_CANDIDATES = ROOT / 'data/v04/audit/candidates.json'
V04_EXCLUSIONS = ROOT / 'data/v04/audit/audit_exclusions.json'
NATURAL_HAZARDS = ROOT / 'data/raw/geosphere_natural_hazards.json'
WLV_SLIDES = ROOT / 'data/raw/wlv_slides.json'
KTN_RAW = V09_DATA / 'raw/kaernten_events.json'
WLV_NON_SLIDE_RAW = V09_DATA / 'raw/wlv_non_slide.json'
VIENNA = 'Europe/Vienna'


# ---------- pure helpers ----------

def parse_ktn_day(text, pivot_yy):
    """'17.11.19 00:00:00,000000' -> date(2019, 11, 17). Two-digit years <= pivot are 20YY, otherwise 19YY."""
    m = re.match(r'(\d{2})\.(\d{2})\.(\d{2}) ', text or '')
    if not m:
        return None
    d, mo, yy = map(int, m.groups())
    try:
        return date(2000 + yy if yy <= pivot_yy else 1900 + yy, mo, d)
    except ValueError:
        return None


def ktn_tokens(value):
    return [t.strip() for t in (value or '').split(';') if t.strip()]


def ktn_process_ok(value, allowed_patterns):
    """Every token must be a registered slide/flow token; mixed records with rockfall, torrent or flood tokens fail."""
    tokens = ktn_tokens(value)
    return bool(tokens) and all(any(re.fullmatch(p, t) for p in allowed_patterns) for t in tokens)


def shifted_t0(reported_day, shift_days):
    """Conservative t0 for a source without verified day precision: local midnight `shift_days` before the reported day.

    Returns (analysis_day, t0_local ISO, t0_utc ISO). A record reported up to `shift_days` days after the true failure day
    still has no post-event hour in [t0 - 60 d, t0)."""
    day = reported_day - timedelta(days=shift_days)
    local = pd.Timestamp(day.isoformat(), tz=VIENNA)
    return day.isoformat(), local.isoformat(), local.tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')


def near_in_time(xy, days, ref_xy, ref_days, radius_m, max_days):
    """Boolean per point: any reference point within radius_m (metric CRS) and |day difference| <= max_days."""
    out = np.zeros(len(xy), bool)
    if len(ref_xy) == 0 or len(xy) == 0:
        return out
    tree = cKDTree(ref_xy)
    for i, js in enumerate(tree.query_ball_point(xy, radius_m)):
        out[i] = any(abs(days[i] - ref_days[j]) <= max_days for j in js)
    return out


def unseen_blocks(seen, new, positive_link_m):
    """V0.4 episode/block rules on seen + new positives. Returns new events with block id and a `seen_block` flag."""
    both = pd.concat([seen.assign(src='seen'), new.assign(src='new')], ignore_index=True)
    both['temporal_episode'] = temporal_episodes([pd.Timestamp(d).date() for d in both.event_day])
    both['block'] = blocks(both, 'temporal_episode', positive_link_m=positive_link_m)
    seen_blocks = set(both.loc[both.src == 'seen', 'block'])
    out = both[both.src == 'new'].drop(columns='src').copy()
    out['seen_block'] = out.block.isin(seen_blocks)
    return out


# ---------- inputs ----------

def local_day_ms(ms):
    return pd.Timestamp(ms, unit='ms', tz='UTC').tz_convert(VIENNA).date()


def geosphere_reference():
    """All Naturgefahren records (any process/quality): metric xy, local start day (or None) and year-month."""
    rows = []
    for f in read_json(NATURAL_HAZARDS)['features']:
        g, a = f.get('geometry'), f['attributes']
        if not g:
            continue
        x, y = PROJECT.transform(g['x'], g['y'])
        rows.append({'x': x, 'y': y, 'day': local_day_ms(a['Date_Anfan']).toordinal() if a.get('Date_Anfan') is not None else None,
                     'ym': (a.get('EREIGNIS_J'), a.get('EREIGNIS_M'))})
    return pd.DataFrame(rows)


def other_source_points(cfg):
    """Independent-source points for the media process screen: slide records and non-slide records (xy, local day)."""
    slide, other = [], []
    for f in read_json(WLV_SLIDES)['features']:
        v = f['properties']['validfrom'] or ''
        try:
            d = pd.Timestamp(v).tz_convert(VIENNA).date() if v[:4].isdigit() else None
        except ValueError:
            d = None
        if d:
            slide.append((*PROJECT.transform(*f['geometry']['coordinates'][:2]), d.toordinal(), 'wlv'))
    for f in read_json(WLV_NON_SLIDE_RAW)['features']:
        v = f['properties']['validfrom'] or ''
        try:
            d = pd.Timestamp(v).tz_convert(VIENNA).date() if v[:4].isdigit() else None
        except ValueError:
            d = None
        if d:
            other.append((*PROJECT.transform(*f['geometry']['coordinates'][:2]), d.toordinal(), 'wlv'))
    k = cfg['cohorts']['kaernten']
    for f in read_json(KTN_RAW)['features']:
        d = parse_ktn_day(f['properties']['validFrom'], k['two_digit_year_pivot'])
        q = (f['properties'].get('magnitudeOrIntensity') or {}).get('qualitativeValue')
        if not d or not f.get('geometry'):
            continue
        p = (*PROJECT.transform(*f['geometry']['coordinates'][:2]), d.toordinal(), 'ktn')
        if ktn_process_ok(q, k['process_tokens']):
            slide.append(p)
        elif any(re.search(t, q or '', re.I) for t in cfg['process_screen']['other_process_patterns']):
            other.append(p)
    as_frame = lambda r: pd.DataFrame(r, columns=['x', 'y', 'day', 'source'])
    return as_frame(slide), as_frame(other)


# ---------- cohorts ----------

def media_candidates(cfg, slide_pts, other_pts):
    m = cfg['cohorts']['media']
    raw = {f['attributes']['nameOfEvent']: f for f in read_json(NATURAL_HAZARDS)['features']}
    rows = [r for r in read_json(V04_EXCLUSIONS) if r['reason'] == m['v04_reason'] and r['date_tier'] == m['date_tier']]
    out = []
    for r in rows:
        f = raw[r['event_id']]
        a, g = f['attributes'], f['geometry']
        x, y = PROJECT.transform(g['x'], g['y'])
        out.append({'event_id': r['event_id'], 'cohort': 'media', 'event_day': r['event_day'], 'reported_day': r['event_day'],
                    't0_local': r['t0_local'], 't0_utc': pd.Timestamp(r['t0_local']).tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'time_quality': r['time_quality'], 'date_text_original': r['date_text_original'],
                    'longitude': g['x'], 'latitude': g['y'], 'x': x, 'y': y, 'state': a.get('Bundesland'),
                    'municipality': a.get('GEMEINDE'), 'process_type_original': a['Prozessuntergruppe'],
                    'process_group_original': a['Prozessgruppe'], 'position_accuracy_original': a['QUAL_LAGE'],
                    'position_accuracy_upper_m': {'Lage sehr genau / sehr sicher (0-5m)': 5, 'Lage genau (5-20m)': 20,
                                                  'Lage relativ genau (20-100m)': 100}.get(a['QUAL_LAGE']),
                    'survey_method': (a.get('ERHEB_MET_agg') or '').strip(), 'survey_note': a.get('ERHEBME_TX'),
                    'source': 'GeoSphere Austria / Naturgefahren (Test), media tier 2'})
    frame = pd.DataFrame(out)
    if frame.position_accuracy_upper_m.isna().any() or (frame.position_accuracy_upper_m > m['max_position_upper_bound_m']).any():
        raise ValueError('Media candidate outside the registered position bound')
    xy, days = frame[['x', 'y']].to_numpy(), np.array([date.fromisoformat(d).toordinal() for d in frame.event_day])
    s = cfg['process_screen']
    frame['process_conflict_other_source'] = near_in_time(xy, days, other_pts[['x', 'y']].to_numpy(), other_pts.day.to_numpy(),
                                                          s['conflict_radius_m'], s['conflict_days'])
    frame['confirmed_by_independent_source'] = near_in_time(xy, days, slide_pts[['x', 'y']].to_numpy(), slide_pts.day.to_numpy(),
                                                            s['confirm_radius_m'], s['confirm_days'])
    return frame


def kaernten_candidates(cfg, geo):
    k = cfg['cohorts']['kaernten']
    rows, excluded = [], Counter()
    for f in read_json(KTN_RAW)['features']:
        p = f['properties']
        q = (p.get('magnitudeOrIntensity') or {}).get('qualitativeValue')
        if not p.get('hazardCategory', '').endswith('/landslide'):
            continue                                     # floods/avalanches: out of scope, not 'excluded events'
        if not ktn_process_ok(q, k['process_tokens']):
            excluded['process_not_registered_slide_token'] += 1
            continue
        day = parse_ktn_day(p.get('validFrom'), k['two_digit_year_pivot'])
        if day is None:
            excluded['no_valid_day'] += 1
            continue
        if not k['period'][0] <= day.isoformat() <= k['period'][1]:
            excluded['outside_period'] += 1
            continue
        if not f.get('geometry') or f['geometry'].get('type') != 'Point':
            excluded['no_point_geometry'] += 1
            continue
        lon, lat = f['geometry']['coordinates'][:2]
        x, y = PROJECT.transform(lon, lat)
        analysis_day, t0_local, t0_utc = shifted_t0(day, k['t0_shift_days'])
        rows.append({'event_id': 'KTN_' + p['inspireID']['localId'], 'cohort': 'kaernten', 'event_day': analysis_day,
                     'reported_day': day.isoformat(), 't0_local': t0_local, 't0_utc': t0_utc, 'time_quality': 'day',
                     'date_text_original': p.get('validFrom'), 'longitude': lon, 'latitude': lat, 'x': x, 'y': y,
                     'state': 'Kaernten', 'municipality': None, 'process_type_original': q, 'process_group_original': None,
                     'position_accuracy_original': 'unbekannt (kein Genauigkeitsfeld)', 'position_accuracy_upper_m': None,
                     'survey_method': None, 'survey_note': None, 'source': 'Land Kärnten, Natur- und Umweltereignisse (INSPIRE)'})
    frame = pd.DataFrame(rows)
    dup = frame.duplicated(['longitude', 'latitude', 'reported_day'])
    excluded['exact_location_day_duplicate'] += int(dup.sum())
    frame = frame[~dup].reset_index(drop=True)
    xy = frame[['x', 'y']].to_numpy()
    rep = np.array([date.fromisoformat(d).toordinal() for d in frame.reported_day])
    dated = geo[geo.day.notna()]
    in_geo = near_in_time(xy, rep, dated[['x', 'y']].to_numpy(), dated.day.to_numpy(int), k['dedup_radius_m'], k['dedup_days'])
    undated = geo[geo.day.isna()]
    ym = [(date.fromordinal(int(d)).year, date.fromordinal(int(d)).month) for d in rep]
    tree = cKDTree(undated[['x', 'y']].to_numpy()) if len(undated) else None
    same_month = np.zeros(len(frame), bool)
    if tree is not None:
        for i, js in enumerate(tree.query_ball_point(xy, k['dedup_radius_m'])):
            same_month[i] = any(undated.ym.iloc[j] == ym[i] for j in js)
    excluded['already_in_geosphere'] = int((in_geo | same_month).sum())
    return frame[~(in_geo | same_month)].reset_index(drop=True), dict(excluded)


def run():
    cfg = load_config()
    slide_pts, other_pts = other_source_points(cfg)
    media = media_candidates(cfg, slide_pts, other_pts)
    counts = {'media_rows': int(len(media))}
    dup = media.duplicated(['longitude', 'latitude', 'event_day'])
    counts['media_exact_location_day_duplicate'] = int(dup.sum())
    counts['media_process_conflict_other_source'] = int(media.process_conflict_other_source[~dup].sum())
    media = media[~dup & ~media.process_conflict_other_source].reset_index(drop=True)
    ktn, ktn_excluded = kaernten_candidates(cfg, geosphere_reference())
    counts['kaernten_excluded'] = ktn_excluded
    new = pd.concat([media, ktn], ignore_index=True)
    if new.event_id.duplicated().any():
        raise ValueError('Duplicate V0.9 event_id')
    seen = pd.DataFrame(read_json(V04_CANDIDATES))[['event_id', 'event_day', 'x', 'y']]
    marked = unseen_blocks(seen, new[['event_id', 'event_day', 'x', 'y']], cfg['partition']['positive_link_m'])
    new = new.merge(marked[['event_id', 'temporal_episode', 'block', 'seen_block']], on='event_id', validate='one_to_one')
    eligible = new[~new.seen_block].sort_values(['event_day', 'event_id']).reset_index(drop=True)
    counts.update({
        f'{c}_{k}': v for c in ('media', 'kaernten')
        for k, v in {'candidates': int((new.cohort == c).sum()), 'in_seen_block': int(((new.cohort == c) & new.seen_block).sum()),
                     'eligible_unseen': int((eligible.cohort == c).sum()),
                     'eligible_blocks': int(eligible[eligible.cohort == c].block.nunique())}.items()})
    counts['eligible_blocks_pooled'] = int(eligible.block.nunique())
    counts['eligible_media_confirmed_by_independent_source'] = int(eligible[eligible.cohort == 'media'].confirmed_by_independent_source.sum())
    out = guard(V09_DATA / 'audit')
    path = out / 'candidates.json'
    eligible.to_json(path, orient='records', force_ascii=False, indent=1)
    new[new.seen_block].to_json(out / 'excluded_seen_block.json', orient='records', force_ascii=False, indent=1)
    summary = {'counts': counts, 'candidates_sha256': sha(path),
               'eligible_by_year': eligible.groupby(['cohort', eligible.event_day.str[:4]]).size().rename('n').reset_index()
               .to_dict('records')}
    write_json(guard(V09_REPORT) / 'cohort_summary.json', summary)
    print(json.dumps(summary['counts'], indent=1, ensure_ascii=False))
    return eligible


if __name__ == '__main__':
    run()
