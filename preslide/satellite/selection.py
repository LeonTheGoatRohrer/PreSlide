"""Eligibility and acquisition selection: best usable observations before and after each event, with every exclusion recorded.

Selection is made for the whole event group: an acquisition is accepted as before_primary/after_primary only if it is
locally usable at the positive AND at least `min_controls_usable` of its matched controls (same acquisition for all
members keeps season, snow and illumination identical within a group)."""
from datetime import date, timedelta

from ..common import write_json, read_json
from . import stac
from .imagery import event_grid, quicklook, usable, sample_dir, utm_epsg
from .paths import config

ROLES = ('before_reference', 'before_primary', 'after_primary', 'after_confirm')
GROUP_ROLES = ('before_primary', 'after_primary')


def _d(s):
    return date.fromisoformat(s[:10])


def covering_usable_item(item, sid, lon, lat, grid, el):
    """Same acquisition (same minute, same collection) on a tile covering the point with usable local quality.

    Neighbouring MGRS tiles overlap and partial tiles have nodata swath edges, so the positive's tile may not cover a
    control up to 10 km away. Returns (item or None, reason, metrics)."""
    cands = [item] if stac.covers(item, lon, lat) else []
    for c in stac.search(lon, lat, item['date'], item['date'], [item['collection']]):
        if c['datetime'][:16] == item['datetime'][:16] and c['id'] != item['id'] and stac.covers(c, lon, lat):
            cands.append(c)
    reasons, q = [], None
    for c in cands:
        q = quicklook(sid, c, grid)
        ok, reason = usable(q, el)
        if ok:
            return c, '', q
        reasons.append(reason)
    return None, '/'.join(reasons) if reasons else 'no_tile_covers_point', q


def select_acquisitions(sample_id, lon, lat, event_day, members=(), items=None, el=None):
    """Pick before/after acquisitions for one event group from locally screened candidates.

    members: iterable of (sample_id, lon, lat) of the matched controls (may be empty).
    before_primary: latest acquisition strictly before the event day usable at the positive and >= min controls.
    before_reference: latest acquisition usable at the positive >= reference_min_gap_days before before_primary.
    after_primary: earliest acquisition strictly after the event day usable at the positive and >= min controls.
    after_confirm: earliest acquisition usable at the positive >= confirm_min_gap_days after after_primary.
    Candidates are screened from the event day outwards and screening stops once a role is filled."""
    el = el or config()['eligibility']
    t0 = _d(event_day)
    epsg = utm_epsg(lon)
    grid = event_grid(lon, lat, epsg=epsg)
    members = [(sid, mlon, mlat, event_grid(mlon, mlat, epsg=epsg)) for sid, mlon, mlat in members]
    if items is None:
        items = stac.search(lon, lat, (t0 - timedelta(days=el['before_search_days'])).isoformat(),
                            (t0 + timedelta(days=el['after_search_days'])).isoformat())
    before = sorted([i for i in items if _d(i['date']) < t0], key=lambda i: i['datetime'], reverse=True)
    after = sorted([i for i in items if _d(i['date']) > t0], key=lambda i: i['datetime'])
    same_day = [i['id'] for i in items if _d(i['date']) == t0]
    screened, chosen, control_items = [], {}, {}

    def screen(item, need_controls):
        q = quicklook(sample_id, item, grid)
        ok, reason = usable(q, el)
        rec = {'item_id': item['id'], 'collection': item['collection'], 'date': item['date'],
               'days_from_event': (_d(item['date']) - t0).days, 'usable': ok, 'reason': reason,
               'core_cloud': q['core']['cloud'], 'core_snow': q['core']['snow'], 'core_invalid': q['core']['invalid'],
               'medium_cloud': q['medium']['cloud'], 'medium_snow': q['medium']['snow'], 'medium_invalid': q['medium']['invalid'],
               'patch_cloud': q['patch']['cloud'], 'patch_snow': q['patch']['snow'], 'patch_invalid': q['patch']['invalid'],
               'controls_usable': None, 'control_reasons': {}}
        found = {}
        if ok and need_controls and members:
            for sid, mlon, mlat, mgrid in members:
                c, creason, _ = covering_usable_item(item, sid, mlon, mlat, mgrid, el)
                if c is not None:
                    found[sid] = c
                else:
                    rec['control_reasons'][sid] = creason
            rec['controls_usable'] = len(found)
            if len(found) < min(el['min_controls_usable'], len(members)):
                ok, rec['usable'], rec['reason'] = False, False, f"controls_usable_{len(found)}_of_{len(members)}"
        screened.append(rec)
        return ok, found

    def pick(cands, role, anchor=None, gap=0, reverse=False):
        need_controls = role in GROUP_ROLES
        for item in cands:
            d = _d(item['date'])
            if anchor is not None and ((anchor - d).days < gap if reverse else (d - anchor).days < gap):
                continue
            ok, found = screen(item, need_controls)
            if ok:
                chosen[role] = item
                if need_controls:
                    control_items[role] = found
                return d
        return None

    bp = pick(before, 'before_primary')
    if bp is not None:
        pick(before, 'before_reference', anchor=bp, gap=el['reference_min_gap_days'], reverse=True)
    ap = pick(after, 'after_primary')
    if ap is not None:
        pick(after, 'after_confirm', anchor=ap, gap=el['confirm_min_gap_days'])
    usable_controls = sorted(set(control_items.get('before_primary', {})) & set(control_items.get('after_primary', {}))) \
        if all(r in chosen for r in GROUP_ROLES) else []
    doy_gap = None
    if all(r in chosen for r in GROUP_ROLES):
        a, b = chosen['before_primary']['date'], chosen['after_primary']['date']
        g = abs(_d(a).timetuple().tm_yday - _d(b).timetuple().tm_yday)
        doy_gap = min(g, 365 - g)
    return {'sample_id': sample_id, 'event_day': event_day, 'grid': grid.to_dict(), 'candidates': len(items),
            'members': [m[0] for m in members], 'usable_controls': usable_controls, 'doy_gap_days': doy_gap,
            'same_day_items_excluded': same_day, 'screened': screened,
            'selected': {k: {'item_id': v['id'], 'collection': v['collection'], 'datetime': v['datetime'], 'epsg': v['epsg'],
                             'grid_code': v['grid_code'], 'processing_baseline': v['processing_baseline'],
                             'days_from_event': (_d(v['date']) - t0).days} for k, v in chosen.items()},
            'items': chosen,
            'control_items': {role: {sid: it for sid, it in found.items() if sid in usable_controls} for role, found in control_items.items()}}


def eligibility_row(pos_row, sel, el=None):
    """Machine-readable eligibility record for one event (never silently discards; records the reason)."""
    el = el or config()['eligibility']
    year = int(pos_row['event_day'][:4])
    s = sel['selected'] if sel else {}
    row = {'event_id': pos_row['event_group_id'], 'event_date': pos_row['event_day'], 'latitude': pos_row['latitude'],
           'longitude': pos_row['longitude'], 'position_quality_upper_m': int(pos_row['source_position_upper_m']),
           'time_quality': pos_row['time_quality'], 'process_type': pos_row['process_type'], 'state': pos_row['state'],
           'independence_unit': pos_row['independence_unit'], 'v04_partition': pos_row['partition'],
           'before_date': s.get('before_primary', {}).get('datetime', '')[:10], 'after_date': s.get('after_primary', {}).get('datetime', '')[:10],
           'before_reference_date': s.get('before_reference', {}).get('datetime', '')[:10],
           'after_confirm_date': s.get('after_confirm', {}).get('datetime', '')[:10],
           'days_before': s.get('before_primary', {}).get('days_from_event'), 'days_after': s.get('after_primary', {}).get('days_from_event'),
           'candidates_screened': len(sel['screened']) if sel else 0,
           'controls_usable': len(sel['usable_controls']) if sel else None, 'doy_gap_days': sel.get('doy_gap_days') if sel else None,
           'usable': False, 'exclusion_reason': ''}
    for role in ('before_primary', 'after_primary'):
        m = next((x for x in (sel['screened'] if sel else []) if s.get(role) and x['item_id'] == s[role]['item_id']), None)
        pre = 'before' if role.startswith('before') else 'after'
        row[f'{pre}_cloud_fraction'] = m['patch_cloud'] if m else None
        row[f'{pre}_snow_fraction'] = m['patch_snow'] if m else None
        row[f'{pre}_core_cloud_fraction'] = m['core_cloud'] if m else None
        row[f'{pre}_valid_fraction'] = (1 - m['patch_invalid']) if m else None
    reasons = []
    if year < el['min_event_year']:
        reasons.append(f"year_before_{el['min_event_year']}_no_l2a")
    if int(pos_row['source_position_upper_m']) > el['max_position_upper_m']:
        reasons.append('position_coarse')
    if sel is not None and not reasons:
        if sel['candidates'] == 0:
            reasons.append('no_sentinel2_items')
        if 'before_primary' not in s:
            reasons.append('no_usable_before_pair_for_group')
        if 'after_primary' not in s:
            reasons.append('no_usable_after_pair_for_group')
        if not reasons and len(sel['usable_controls']) < min(el['min_controls_usable'], len(sel.get('members', []))):
            reasons.append('too_few_controls_on_both_acquisitions')
        if not reasons and sel.get('doy_gap_days') is not None and sel['doy_gap_days'] > el['max_doy_gap_days']:
            reasons.append(f"seasonal_gap_gt_{el['max_doy_gap_days']}d")
    row['usable'] = not reasons and sel is not None
    row['exclusion_reason'] = ';'.join(reasons)
    return row


def selection_path(sample_id):
    return sample_dir(sample_id) / 'selection.json'


def run_selection(sample_id, lon, lat, event_day, members=(), force=False):
    path = selection_path(sample_id)
    if path.exists() and not force:
        sel = read_json(path)
        if 'control_items' in sel and 'doy_gap_days' in sel:
            return sel
    sel = select_acquisitions(sample_id, lon, lat, event_day, members)
    write_json(path, sel)
    return sel
