"""Stage 6 (satellite-0.4): guided region / time-window scan with a blinded manual review sheet.

The user names a bbox, a window before and a window after the suspected event. Each overlapping 2.56 km tile gets the
cleanest before and after acquisition (whole-tile screening), the satellite-0.3 detector scores it (buffered cloud
mask), peaks near documented V0.4 positives are counted separately (plausibility check, not candidates) and the rest
become review candidates. A self-contained HTML sheet is shuffled and hides rank and score; the verdicts come back as
labels.json and are evaluated as precision (Wilson interval). Recall is not measurable. Candidates stay UNVERIFIED
until a label says otherwise.
"""
import base64
import io
import json
import math
from datetime import date, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Geod, Transformer

from ..common import read_json, write_json
from . import events, stac
from .baseline import make_model, feature_columns
from .contact import stretch_rgb
from .discovery import score_map, peaks, buffered_maps, suppress_near_known, training_frame
from .features import model_feature_names, features_at, indices
from .imagery import Grid, event_grid, fetch_patch, quicklook
from .paths import SAT_DATA, SAT_REPORT, guard, config
from .validation import persistence_rule

GEOD = Geod(ellps='WGS84')
VERDICTS = ('slide', 'not_slide', 'unsure')


# ---------- pure helpers (unit-tested without data) ----------

def tile_centres(bbox, step_m):
    """Centres (lon, lat) of a regular tile lattice, in the UTM zone of the bbox centre, covering `bbox`
    (lon_min, lat_min, lon_max, lat_max). Tiles overlap because step_m is smaller than the tile edge."""
    lon0, lat0, lon1, lat1 = bbox
    if not (lon0 < lon1 and lat0 < lat1):
        raise ValueError(f'empty bbox {bbox}')
    epsg = event_grid((lon0 + lon1) / 2, (lat0 + lat1) / 2).epsg
    fwd = Transformer.from_crs('EPSG:4326', f'EPSG:{epsg}', always_xy=True)
    back = Transformer.from_crs(f'EPSG:{epsg}', 'EPSG:4326', always_xy=True)
    xs, ys = zip(*(fwd.transform(lo, la) for lo in (lon0, lon1) for la in (lat0, lat1)))
    nx, ny = math.ceil((max(xs) - min(xs)) / step_m), math.ceil((max(ys) - min(ys)) / step_m)
    out = []
    for i in range(max(nx, 1)):
        for j in range(max(ny, 1)):
            out.append(back.transform(min(xs) + (i + 0.5) * step_m, min(ys) + (j + 0.5) * step_m))
    return out


def pick_acquisition(options, role, max_bad, not_before=None, min_gap_days=0):
    """Choose one acquisition. `options`: dicts with 'date' (ISO) and 'bad_frac'. before: latest date with
    bad_frac <= max_bad; after: earliest such date; confirm: earliest such date at least `min_gap_days` after
    `not_before`. Returns the option or None (never relaxes the threshold)."""
    ok = [o for o in options if o['bad_frac'] <= max_bad]
    if role == 'confirm':
        floor = (date.fromisoformat(not_before) + timedelta(days=min_gap_days)).isoformat()
        ok = [o for o in ok if o['date'] >= floor]
    if not ok:
        return None
    return max(ok, key=lambda o: o['date']) if role == 'before' else min(ok, key=lambda o: o['date'])


def dedup_candidates(cands, min_sep_m):
    """Keep the highest-scoring candidate of every group closer than `min_sep_m` (geodesic distance)."""
    kept = []
    for c in sorted(cands, key=lambda c: -c['score']):
        if all(GEOD.inv(c['longitude'], c['latitude'], k['longitude'], k['latitude'])[2] > min_sep_m for k in kept):
            kept.append(c)
    return kept


def known_in_grid(grid, known, margin_px):
    """(event_group_id, row, col) of known positives inside the scored interior of the grid."""
    to_grid = Transformer.from_crs('EPSG:4326', grid.crs, always_xy=True)
    out = []
    for eid, lon, lat in zip(known['event_group_id'], known['longitude'], known['latitude']):
        x, y = to_grid.transform(lon, lat)
        r, c = int((grid.y1 - y) // grid.res), int((x - grid.x0) // grid.res)
        if margin_px <= r < grid.n - margin_px and margin_px <= c < grid.n - margin_px:
            out.append((eid, r, c))
    return out


def select_review(cands, top_n, random_n, seed):
    """Top-N by score (stratum 'top') plus random_n of the remaining ones (stratum 'random'), shuffled with a fixed
    seed. Returns a new list; ids are opaque ('c01'...) and carry no rank information."""
    ranked = sorted(cands, key=lambda c: -c['score'])
    top = [dict(c, stratum='top', rank=i + 1) for i, c in enumerate(ranked[:top_n])]
    rest = ranked[top_n:]
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(rest), size=min(random_n, len(rest)), replace=False) if rest else []
    rand = [dict(rest[i], stratum='random', rank=top_n + int(i) + 1) for i in sorted(pick)]
    both = top + rand
    order = rng.permutation(len(both))
    return [dict(both[i], candidate_id=f'c{k + 1:02d}') for k, i in enumerate(order)]


def wilson(k, n, z=1.96):
    """Wilson score interval for k successes in n trials; (nan, nan) for n = 0."""
    if n == 0:
        return float('nan'), float('nan')
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def evaluate_labels(cands, labels, z=1.96):
    """Precision per stratum from reviewed candidates. `labels`: candidate_id -> {'verdict', 'note'}.
    precision_excl_unsure = slide / (slide + not_slide); precision_lower = slide / all reviewed (unsure counted as no)."""
    for cid, lab in labels.items():
        if lab.get('verdict') not in VERDICTS:
            raise ValueError(f'unknown verdict for {cid}: {lab.get("verdict")}')
    out = {}
    for stratum in ('top', 'random'):
        rows = [c for c in cands if c['stratum'] == stratum]
        got = [labels[c['candidate_id']]['verdict'] for c in rows if c['candidate_id'] in labels]
        k, ns, nu = got.count('slide'), got.count('not_slide'), got.count('unsure')
        lo, hi = wilson(k, k + ns, z)
        out[stratum] = {'candidates': len(rows), 'reviewed': len(got), 'slide': k, 'not_slide': ns, 'unsure': nu,
                        'precision_excl_unsure': k / (k + ns) if k + ns else None, 'wilson_95': [lo, hi],
                        'precision_lower': k / len(got) if got else None}
    return out


# ---------- scan ----------

def scan_dir(name):
    return guard(SAT_DATA / 'scan' / name)


def _options(sid, grid, lon, lat, start, end):
    opts = []
    for it in stac.search(lon, lat, start, end):
        q = quicklook(sid, it, grid)
        p = q['patch']
        opts.append({'date': it['date'], 'item': it, 'bad_frac': p['cloud'] + p['snow'] + p['invalid']})
    return opts


def _train_detector(bbox, cfg):
    frame = training_frame('controls')
    known = events.known_positive_positions()
    pad = 0.02
    inside = known[(known['longitude'].between(bbox[0] - pad, bbox[2] + pad)) & (known['latitude'].between(bbox[1] - pad, bbox[3] + pad))]
    units = set(frame[frame['event_group_id'].isin(inside['event_group_id'])]['independence_unit'])
    train = frame[~frame['independence_unit'].isin(units)]
    cols = model_feature_names(feature_columns(frame))
    model = make_model('logistic_regression', cfg).fit(train[cols].to_numpy(dtype=float), train['label'].to_numpy())
    return model, cols, known, sorted(units), int(train['independence_unit'].nunique())


def scan_tile(sid, lon, lat, win, model, cols, known, cfg):
    """Returns (record, candidates). Never raises for a missing acquisition: the reason is recorded."""
    sc, d = cfg['scan'], cfg['discovery']
    grid = event_grid(lon, lat, sc['tile_extent_m'])
    rec = {'tile': sid, 'longitude': lon, 'latitude': lat, 'grid': grid.to_dict(), 'status': 'scanned', 'reason': ''}
    before = pick_acquisition(_options(sid, grid, lon, lat, win['before_start'], win['before_end']), 'before', sc['max_patch_bad_frac'])
    after_opts = _options(sid, grid, lon, lat, win['after_start'], win['after_end'])
    after = pick_acquisition(after_opts, 'after', sc['max_patch_bad_frac'])
    if before is None or after is None:
        rec.update(status='skipped', reason='no_clean_before' if before is None else 'no_clean_after')
        return rec, []
    wide_end = (date.fromisoformat(win['after_end']) + timedelta(days=sc['confirm_extra_days'])).isoformat()
    confirm = pick_acquisition(_options(sid, grid, lon, lat, win['after_start'], wide_end), 'confirm', sc['max_patch_bad_frac'],
                               after['date'], sc['confirm_min_gap_days'])
    rec.update(before_date=before['date'], after_date=after['date'], confirm_date=confirm['date'] if confirm else None,
               before_item=before['item']['id'], after_item=after['item']['id'], confirm_item=confirm['item']['id'] if confirm else None)
    rb, sb, _ = fetch_patch(sid, before['item'], grid)
    ra, sa, _ = fetch_patch(sid, after['item'], grid)
    maps, scorable, diag = buffered_maps(rb, ra, sb, sa, grid.res, cfg)
    margin = int(round(cfg['patch']['medium_m'] / grid.res / 2))
    s = score_map(model, maps, cols, margin, scorable)
    rec['buffer_masked_frac'] = diag['buffer_masked_frac']
    rec['scored_frac'] = float(np.isfinite(s[margin:-margin, margin:-margin]).mean())
    pk_all = peaks(s, int(round(d['min_peak_distance_m'] / grid.res / 2)))
    kin = known_in_grid(grid, known, margin)
    hit_px = d['hit_radius_m'] / grid.res
    rec['known_events'] = sorted({e for e, _, _ in kin})
    rec['known_rediscovered'] = sorted({e for e, r, c in kin if any(np.hypot(r - p[1], c - p[2]) <= hit_px for p in pk_all)})
    kept, suppressed = suppress_near_known(pk_all, [(r, c) for _, r, c in kin], d['suppress_known_positives_m'] / grid.res)
    rec['peaks'], rec['peaks_suppressed_known'] = len(kept), len(suppressed)
    maps_c = s_c = scor_c = None
    if confirm:
        rc, scc, _ = fetch_patch(sid, confirm['item'], grid)
        maps_c, scor_c, _ = buffered_maps(rb, rc, sb, scc, grid.res, cfg)
        s_c = score_map(model, maps_c, cols, margin, scor_c)
    to_wgs = Transformer.from_crs(grid.crs, 'EPSG:4326', always_xy=True)
    cands = []
    for sc_, r, c in kept:
        lon_c, lat_c = to_wgs.transform(grid.x0 + (c + 0.5) * grid.res, grid.y1 - (r + 0.5) * grid.res)
        cand = {'tile': sid, 'row': r, 'col': c, 'longitude': float(lon_c), 'latitude': float(lat_c), 'score': float(sc_),
                'before_date': before['date'], 'after_date': after['date'], 'confirm_date': confirm['date'] if confirm else None,
                'persistence_assessable': False, 'persists': False, 'score_confirm': None}
        if maps_c is not None:
            assessable, persists, _, _ = persistence_rule(features_at(maps, r, c), features_at(maps_c, r, c), float(s_c[r, c]), cfg['validation'])
            cand.update(persistence_assessable=assessable, persists=persists,
                        score_confirm=float(s_c[r, c]) if np.isfinite(s_c[r, c]) else None)
        cands.append(cand)
    return rec, cands


def _png_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def render_chip(cand, tile, cfg):
    """Four panels: RGB before, RGB after, RGB confirm (or 'keine Aufnahme'), dNDVI after - before (buffered mask)."""
    from .features import pair_valid_mask
    grid = Grid(**tile['grid'])
    sid = tile['tile']
    items = {k: _item_by_id(tile, k) for k in ('before', 'after', 'confirm') if tile.get(f'{k}_item')}
    arr = {k: fetch_patch(sid, it, grid) for k, it in items.items()}
    half = int(round(cfg['scan']['review_chip_m'] / grid.res / 2))
    r, c = cand['row'], cand['col']

    def crop(a):
        return a[..., r - half:r + half, c - half:c + half]
    rgb_b, lo, hi = stretch_rgb(crop(arr['before'][0]))
    fig, axes = plt.subplots(1, 4, figsize=(11, 2.9))
    panels = [(rgb_b, f"vorher {tile['before_date']}"), (stretch_rgb(crop(arr['after'][0]), lo, hi)[0], f"nachher {tile['after_date']}")]
    panels.append((stretch_rgb(crop(arr['confirm'][0]), lo, hi)[0], f"später {tile['confirm_date']}") if 'confirm' in arr else (None, 'keine spätere Aufnahme'))
    valid = pair_valid_mask(arr['before'][0], arr['after'][0], arr['before'][1], arr['after'][1], cfg['discovery']['cloud_buffer_m'], grid.res, cfg['discovery'])[0]
    dn = np.where(valid, indices(arr['after'][0])['ndvi'] - indices(arr['before'][0])['ndvi'], np.nan)
    for ax, (img, title) in zip(axes[:3], panels):
        if img is not None:
            ax.imshow(img)
        ax.set_title(title, fontsize=8)
    axes[3].imshow(crop(dn), cmap='RdBu', vmin=-0.5, vmax=0.5)
    axes[3].set_title('ΔNDVI (weiß = maskiert)', fontsize=8)
    for ax in axes:
        ax.plot(half, half, '+', color='yellow', ms=10)
        ax.set_xticks([]); ax.set_yticks([])
    return _png_b64(fig)


def _item_by_id(tile, kind):
    lon, lat = tile['longitude'], tile['latitude']
    day = tile[f'{kind}_date']
    for it in stac.search(lon, lat, day, day):
        if it['id'] == tile[f'{kind}_item']:
            return it
    raise RuntimeError(f"item {tile[f'{kind}_item']} not found on {day}")


REVIEW_JS = """
const KEY='preslide-scan-'+document.body.dataset.scan;
let st={};try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}
 document.getElementById('n').textContent=Object.values(st).filter(x=>x.verdict).length}
document.querySelectorAll('.cand').forEach(el=>{const id=el.dataset.id;
 const cur=st[id]||{};
 el.querySelectorAll('input[type=radio]').forEach(r=>{r.checked=(cur.verdict===r.value);
  r.onchange=()=>{st[id]=Object.assign(st[id]||{},{verdict:r.value});save()}});
 const t=el.querySelector('textarea');t.value=cur.note||'';t.oninput=()=>{st[id]=Object.assign(st[id]||{},{note:t.value});save()}});
document.getElementById('dl').onclick=()=>{const out={scan:document.body.dataset.scan,labels:st};
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,1)],{type:'application/json'}));
 a.download='labels.json';a.click()};save();
"""


def build_review_html(name, review, chips, meta):
    body = []
    for i, cand in enumerate(review, 1):
        cid = cand['candidate_id']
        body.append(
            f'<div class="cand" data-id="{cid}"><div class="h">Kandidat {i} von {len(review)} · {cid}</div>'
            f'<img src="data:image/png;base64,{chips[cid]}" alt="Vorher/Nachher-Ausschnitt {cid}">'
            f'<div class="v"><label><input type="radio" name="{cid}" value="slide"> Rutschung</label>'
            f'<label><input type="radio" name="{cid}" value="not_slide"> keine Rutschung</label>'
            f'<label><input type="radio" name="{cid}" value="unsure"> unsicher</label></div>'
            f'<textarea placeholder="Notiz (z. B. Ursache, Quelle: Orthofoto)" rows="1"></textarea></div>')
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prüfbogen {name}</title><style>
body{{font:15px system-ui,sans-serif;margin:0 auto;max-width:900px;padding:16px;background:#fff;color:#222}}
.cand{{border:1px solid #ccc;border-radius:8px;padding:10px;margin:14px 0}}.cand img{{max-width:100%}}
.h{{font-weight:600;margin-bottom:6px}}.v label{{margin-right:16px}}textarea{{width:100%;box-sizing:border-box;margin-top:6px}}
#bar{{position:sticky;top:0;background:#fff;padding:8px 0;border-bottom:1px solid #ddd}}
@media(prefers-color-scheme:dark){{body,#bar{{background:#161616;color:#eee}}.cand{{border-color:#444}}}}</style></head>
<body data-scan="{name}"><div id="bar"><b>Prüfbogen {name}</b> · geprüft: <span id="n">0</span> / {len(review)}
 · <button id="dl">Labels herunterladen (labels.json)</button></div>
<p>{meta}</p><p>Reihenfolge gemischt; Rang und Score sind verborgen. Gelbes Kreuz = Kandidat (Sentinel-2, 10 m). Im Zweifel „unsicher“ und ein Orthofoto heranziehen.</p>
{''.join(body)}<script>{REVIEW_JS}</script></body></html>"""


def run_scan(name, bbox, win, limit_tiles=0):
    cfg = config()
    sc = cfg['scan']
    root = scan_dir(name)
    model, cols, known, held_out_units, n_train_units = _train_detector(bbox, cfg)
    centres = tile_centres(bbox, sc['tile_step_m'])
    if limit_tiles:
        centres = centres[:limit_tiles]
    tiles, cands = [], []
    for i, (lon, lat) in enumerate(centres):
        rec, tc = scan_tile(f'scan_{name}_{i:03d}', lon, lat, win, model, cols, known, cfg)
        tiles.append(rec)
        cands += tc
        print(rec['tile'], rec['status'], rec['reason'], len(tc), flush=True)
    uniq = dedup_candidates(cands, sc['dedup_m'])
    review = select_review(uniq, sc['review_top_n'], sc['review_random_n'], sc['review_seed'])
    by_tile = {t['tile']: t for t in tiles}
    chips = {c['candidate_id']: render_chip(c, by_tile[c['tile']], cfg) for c in review}
    scanned = [t for t in tiles if t['status'] == 'scanned']
    known_all = sorted({e for t in scanned for e in t['known_events']})
    known_hit = sorted({e for t in scanned for e in t['known_rediscovered']})
    summary = {'scan': name, 'version': cfg['version'], 'bbox': list(bbox), 'windows': win, 'tiles_total': len(tiles),
               'tiles_scanned': len(scanned), 'skipped_reasons': pd.Series([t['reason'] for t in tiles if t['status'] != 'scanned']).value_counts().to_dict(),
               'scanned_km2_interior': len(scanned) * ((sc['tile_extent_m'] - 960) / 1000) ** 2,
               'detections': len(cands), 'physical_candidates': len(uniq), 'reviewed_sample': len(review),
               'known_events_in_scanned_tiles': len(known_all), 'known_events_rediscovered': len(known_hit),
               'units_held_out_from_training': held_out_units, 'training_units': n_train_units,
               'candidates_with_persistence': int(sum(c['persistence_assessable'] for c in uniq))}
    meta = f"Region {name}: {len(scanned)} Kacheln, Fenster vorher {win['before_start']}…{win['before_end']}, nachher {win['after_start']}…{win['after_end']}."
    (root / 'review.html').write_text(build_review_html(name, review, chips, meta), encoding='utf-8')
    pd.DataFrame(review).to_csv(root / 'candidates_with_ids.csv', index=False)      # local only: holds rank/score/coordinates
    pd.DataFrame(uniq).to_parquet(root / 'all_candidates.parquet', index=False)
    write_json(root / 'tiles.json', tiles)
    write_json(root / 'summary.json', summary)
    return summary


def evaluate_scan(name, labels_path):
    cfg = config()
    root = scan_dir(name)
    review = pd.read_csv(root / 'candidates_with_ids.csv').to_dict('records')
    labels = json.loads(open(labels_path, encoding='utf-8').read())['labels']
    labels = {k: v for k, v in labels.items() if v.get('verdict')}
    res = evaluate_labels(review, labels, cfg['scan']['wilson_z'])
    summary = read_json(root / 'summary.json')
    persist = {}
    for flag in (True, False):
        rows = [c for c in review if c['stratum'] == 'top' and bool(c['persists']) == flag and c['candidate_id'] in labels]
        k = sum(labels[c['candidate_id']]['verdict'] == 'slide' for c in rows)
        persist['persists' if flag else 'does_not_persist'] = {'reviewed': len(rows), 'slide': k}
    out = {'scan': name, 'version': cfg['version'], 'strata': res, 'top_by_persistence': persist, 'scan_summary': summary,
           'caveats': ['precision only; recall not measurable', 'candidates of one storm are not independent',
                       'verdicts from Sentinel-2 10 m and optional orthophoto; unsure counted as not confirmed in precision_lower']}
    guard(SAT_REPORT)
    write_json(SAT_REPORT / f'scan_{name}_results.json', out)
    write_json(root / 'labels_used.json', labels)
    return out
