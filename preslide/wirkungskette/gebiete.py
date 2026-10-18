"""wirkungskette_gebietstest_v01 (registered as wirkungskette_v02, renamed by amendment 2): pre-registered test of the review classes on unseen Hangmuren areas.

Design: config/wirkungskette_gebietstest_v01.json, registered in reports/wirkungskette_gebietstest_v01/PREREGISTRATION.json before any
computation. Areas = LAU 2021 municipalities with >= 5 precisely located pure Hangmuren of a 2000-2015 campaign;
terrain = SRTM 1" (February 2000, primary) or Skadi (sensitivity, provenance not pre-event); frozen V0.4 static
model vs slope alone; capture of target events in the top 5 % / 20 % of the assessable area.
"""
import hashlib
import json
import math
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds, Resampling
from rasterio.windows import from_bounds, Window
from scipy import ndimage
from shapely import contains_xy, points as shp_points
from shapely.geometry import shape
from shapely.ops import transform as shp_transform, unary_union

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE, derivatives
from ..v04 import terrain as T4
from ..v04.models import add_one_hot
from . import build as B
from . import sources, store
from .paths import CONFIG_GT, DATA_GT, REPORT_GT, guard, sha

SKADI_DIRS = (ROOT / 'data/raw/terrain', ROOT / 'data/v04/cache/terrain_tiles')


# ---------- configuration ----------

def config():
    """Registered configuration; refuses to run if it changed after registration (amendments need a new hash entry)."""
    reg = read_json(REPORT_GT / 'PREREGISTRATION.json')
    actual = hashlib.sha256(CONFIG_GT.read_bytes()).hexdigest()
    allowed = {reg['config_sha256'], *[a['config_sha256'] for a in reg.get('amendments', [])]}
    if actual not in allowed:
        raise RuntimeError('config/wirkungskette_gebietstest_v01.json changed after registration; write an amendment first')
    return read_json(CONFIG_GT)


# ---------- inventory targets and areas ----------

def targets(cfg):
    """Precisely located pure Hangmuren with campaign and campaign year (EPSG:31287 metres)."""
    inv = cfg['inventory']
    d = read_json(ROOT / 'data/raw/geosphere_natural_hazards.json')
    raw = pd.DataFrame([{**f['attributes'], 'lon': f['geometry']['x'], 'lat': f['geometry']['y']} for f in d['features']])
    raw['year'] = raw[inv['campaign_field']].astype(str).str.extract(r'((?:19|20)\d{2})')[0].astype(float)
    t = raw[(raw.Prozessuntergruppe.fillna('').str.strip() == inv['target_process'].split("'")[1])
            & raw.QUAL_LAGE.isin(inv['precise_location'])].copy()
    if t.nameOfEvent.duplicated().any():
        raise ValueError('Duplicate event id among targets')
    t['x'], t['y'] = PROJECT.transform(t.lon.to_numpy(), t.lat.to_numpy())
    return t[['nameOfEvent', 'RegKatE_ID', 'year', 'lon', 'lat', 'x', 'y', 'GEMEINDE']].rename(
        columns={'nameOfEvent': 'event_id', 'RegKatE_ID': 'campaign'}).reset_index(drop=True)


def selected_campaigns(t, cfg):
    g = t.groupby('campaign').agg(n=('event_id', 'size'), year=('year', 'first')).reset_index()
    return g[(g.year >= 2000) & (g.year <= 2015) & (g.n >= 50)].sort_values('n', ascending=False).reset_index(drop=True)


@lru_cache(maxsize=1)
def lau_austria():
    """Austrian LAU 2021 municipalities projected to EPSG:31287 (cached GISCO file, SHA recorded on first use)."""
    path = DATA_GT / 'cache/gisco/LAU_RG_01M_2021_4326.geojson'
    meta = path.with_name(path.name + '.meta.json')
    if not meta.exists():
        headers = path.with_name('LAU_RG_01M_2021_4326.headers.txt').read_text(encoding='latin-1')
        write_json(meta, {'url': 'https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2021_4326.geojson',
                          'sha256': sha(path), 'headers': headers.splitlines()[:12],
                          'recorded_at': datetime.now(timezone.utc).isoformat()})
    elif read_json(meta)['sha256'] != sha(path):
        raise RuntimeError('GISCO LAU cache checksum mismatch')
    data = json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for f in data['features']:
        p = f['properties']
        if p.get('CNTR_CODE') != 'AT':
            continue
        geom = shp_transform(lambda x, y, z=None: PROJECT.transform(x, y), shape(f['geometry']))
        rows.append({'lau_id': p.get('LAU_ID'), 'name': p.get('LAU_NAME'), 'geometry': geom.buffer(0)})
    if not rows:
        raise RuntimeError('No Austrian LAU units found')
    return rows


def area_of(campaign_targets, lau, min_points):
    """Municipalities containing >= min_points targets; union and connected components (EPSG:31287)."""
    pts = shp_points(campaign_targets.x.to_numpy(), campaign_targets.y.to_numpy())
    chosen = []
    for m in lau:
        n = int(contains_xy(m['geometry'], campaign_targets.x.to_numpy(), campaign_targets.y.to_numpy()).sum())
        if n >= min_points:
            chosen.append({**m, 'n_targets': n})
    if not chosen:
        raise ValueError('No municipality reaches the point threshold')
    union = unary_union([m['geometry'] for m in chosen])
    parts = list(getattr(union, 'geoms', [union]))
    inside = np.array([union.covers(p) for p in pts])
    return {'municipalities': [{'lau_id': m['lau_id'], 'name': m['name'], 'n_targets': m['n_targets'],
                                'area_km2': round(m['geometry'].area / 1e6, 2)} for m in chosen],
            'union': union, 'components': parts, 'inside': inside}


# ---------- terrain tiles ----------

def srtm_tile(lat, lon):
    """SRTMGL1 tile from the ESA STEP mirror (acquisition February 2000), cached with URL/date/SHA manifest."""
    name = f'N{lat:02d}E{lon:03d}'
    d = guard(DATA_GT / 'cache/srtm')
    hgt, manifest = d / f'{name}.hgt', d / f'{name}.json'
    if not manifest.exists():
        url = f'https://step.esa.int/auxdata/dem/SRTMGL1/{name}.SRTMGL1.hgt.zip'
        z, headers = d / f'{name}.zip', d / f'{name}.headers.txt'
        subprocess.run([shutil.which('curl.exe') or 'curl', '-f', '-sS', '-L', '--retry', '2', '--max-time', '300',
                        '-D', str(headers), '-o', str(z), url], check=True, timeout=400)
        with zipfile.ZipFile(z) as archive:
            member = [m for m in archive.namelist() if m.lower().endswith('.hgt')]
            if len(member) != 1:
                raise ValueError(f'Unexpected SRTM archive content: {archive.namelist()}')
            data = archive.read(member[0])
        if len(data) != 3601 * 3601 * 2:
            raise ValueError('Unexpected SRTMGL1 dimensions')
        hgt.write_bytes(data)
        last = [s.split(':', 1)[1].strip() for s in headers.read_text(encoding='latin-1').splitlines() if s.lower().startswith('last-modified:')]
        write_json(manifest, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'object_last_modified': last[-1] if last else None,
                              'sha256': sha(hgt), 'acquisition': 'SRTM, 11-22 February 2000', 'product': 'SRTMGL1 v3 (void-filled)',
                              'vertical_datum': 'EGM96', 'resolution': '1 arc second', 'nodata': -32768})
    if sha(hgt) != read_json(manifest)['sha256']:
        raise RuntimeError('SRTM cache checksum mismatch')
    return hgt


def skadi_tile(lat, lon):
    """Existing Skadi tile (V0.4 caches, read only); used only for the labelled sensitivity analysis."""
    name = f'N{lat:02d}E{lon:03d}'
    for d in SKADI_DIRS:
        if (d / f'{name}.json').exists():
            if sha(d / f'{name}.hgt') != read_json(d / f'{name}.json')['sha256']:
                raise RuntimeError('Skadi cache checksum mismatch')
            return d / f'{name}.hgt'
    return T4.tile(lat, lon, '9999-12-31')[0]   # download into the V0.4 tile cache; date rule handled by the caller


def _open_hgt(path):
    """SRTM/Skadi .hgt as an in-memory GeoTIFF-like dataset (EPSG:4326, nodata -32768)."""
    raw = np.frombuffer(path.read_bytes(), dtype='>i2').reshape(3601, 3601).astype('int16')
    lat0, lon0 = int(path.stem[1:3]), int(path.stem[4:7])
    mem = MemoryFile()
    ds = mem.open(driver='GTiff', width=3601, height=3601, count=1, dtype='int16', crs='EPSG:4326', nodata=-32768,
                  transform=from_origin(lon0 - 0.5 / 3600, lat0 + 1 + 0.5 / 3600, 1 / 3600, 1 / 3600))
    ds.write(raw, 1)
    return mem, ds


def dem_rect(tile_fn, left, top, n_rows, n_cols, res, crs):
    """Bilinear reprojection of 1" tiles into an EPSG:31287 rectangle (same procedure as preslide.v04.terrain.dem_window)."""
    transform = from_origin(left, top, res, res)
    dem = np.full((n_rows, n_cols), np.nan, dtype='float32')
    bounds = transform_bounds(crs, 'EPSG:4326', left, top - n_rows * res, left + n_cols * res, top, densify_pts=21)
    for tlon in range(math.floor(bounds[0]), math.floor(bounds[2]) + 1):
        for tlat in range(math.floor(bounds[1]), math.floor(bounds[3]) + 1):
            path = tile_fn(tlat, tlon)
            mem, src = _open_hgt(path) if path.suffix == '.hgt' else (None, rasterio.open(path))
            with src:
                win = from_bounds(max(bounds[0] - .001, src.bounds.left), max(bounds[1] - .001, src.bounds.bottom),
                                  min(bounds[2] + .001, src.bounds.right), min(bounds[3] + .001, src.bounds.top), src.transform)
                win = win.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
                reproject(src.read(1, window=win), dem, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, src_nodata=-32768, dst_nodata=np.nan,
                          init_dest_nodata=False, resampling=Resampling.bilinear)
            if mem is not None:
                mem.close()
    return dem


def static_features_from_dem(dem, left, top, res, x, y):
    """preslide.v04.terrain.static_features on a given DEM window (identical formulas; V0.4 code is frozen and fetches
    its own Skadi window, so the computation is repeated here). NaN = not computable, never imputed."""
    slope, _ = derivatives(dem, res)
    profile, plan, tri = T4.curvatures(dem.astype(float), res)
    tpi150 = dem - T4.focal_mean(dem.astype(float), T4.disc(150 / res))
    tpi500 = dem - T4.focal_mean(dem.astype(float), T4.disc(500 / res))
    fp = T4.disc(500 / res) > 0
    zmin = ndimage.minimum_filter(np.nan_to_num(dem, nan=np.inf), footprint=fp, mode='constant', cval=np.inf)
    zmax = ndimage.maximum_filter(np.nan_to_num(dem, nan=-np.inf), footprint=fp, mode='constant', cval=-np.inf)
    with np.errstate(invalid='ignore', divide='ignore'):
        relpos = (dem - zmin) / (zmax - zmin)
    relpos[~np.isfinite(tpi500)] = np.nan
    filled, outlet, iterations = T4.fill_depressions(dem.astype(float))
    acc, edge = T4.flow_accumulation(filled, outlet, res)
    cols = np.floor((np.asarray(x) - left) / res).astype(int)
    rows = np.floor((top - np.asarray(y)) / res).astype(int)
    if (rows < 0).any() or (cols < 0).any() or (rows >= dem.shape[0]).any() or (cols >= dem.shape[1]).any():
        raise ValueError('Sample outside terrain window')
    area = acc[rows, cols] * res * res
    truncated = edge[rows, cols]
    beta = np.deg2rad(np.maximum(slope[rows, cols], 0.1))
    out = pd.DataFrame({'profile_curvature': profile[rows, cols], 'plan_curvature': plan[rows, cols],
                        'roughness_tri': tri[rows, cols], 'tpi_150m': tpi150[rows, cols], 'tpi_500m': tpi500[rows, cols],
                        'relative_position_500m': relpos[rows, cols],
                        'log10_catchment_m2': np.where(truncated, np.nan, np.log10(area)),
                        'twi': np.where(truncated, np.nan, np.log(area / res / np.tan(beta))),
                        'catchment_truncated': truncated})
    return out, {'fill_iterations': int(iterations), 'nodata_cells': int(np.isnan(dem).sum())}


# ---------- one connected area component ----------

def land_cover_vintage(year):
    if 2002 <= year <= 2007:
        return 'CLC2000'
    if 2008 <= year <= 2012:
        return 'CLC2006'
    if 2013 <= year <= 2018:
        return 'CLC2012'
    raise ValueError(f'No registered land-cover vintage for {year}')


def component_identity(cfg, campaign, index, dem_name):
    return store.identity({'cfg': hashlib.sha256(CONFIG_GT.read_bytes()).hexdigest(), 'campaign': campaign,
                           'component': index, 'dem': dem_name, 'algorithm': 1})


def compute_component(cfg, campaign, year, index, polygon, events, dem_name, bundle):
    """Grid cells (90 m) inside the component plus target events, with static features, slope and model score."""
    t = cfg['terrain']
    res = float(t['resolution_m'])
    path = guard(DATA_GT / dem_name) / f'{campaign}_c{index}.parquet'
    ident = component_identity(cfg, campaign, index, dem_name)
    if store.exists(path):
        return store.load_parquet(path, ident)
    margin = t['catchment_margin_m'] + t['window_extra_m']
    minx, miny, maxx, maxy = polygon.bounds
    left = math.floor((minx - margin) / res) * res
    top = math.ceil((maxy + margin) / res) * res
    n_cols = int(math.ceil((maxx + margin - left) / res))
    n_rows = int(math.ceil((top - (miny - margin)) / res))
    tile_fn = srtm_tile if dem_name == 'srtm' else skadi_tile
    dem = dem_rect(tile_fn, left, top, n_rows, n_cols, res, t['crs'])
    step = int(round(cfg['cells_m'] / res))
    rr, cc = np.meshgrid(np.arange(0, n_rows, step), np.arange(0, n_cols, step), indexing='ij')
    gx, gy = left + (cc.ravel() + .5) * res, top - (rr.ravel() + .5) * res
    keep = contains_xy(polygon, gx, gy)
    gx, gy = gx[keep], gy[keep]
    frame = pd.DataFrame({'kind': ['grid'] * len(gx) + ['event'] * len(events),
                          'event_id': [''] * len(gx) + events.event_id.tolist(),
                          'x': np.concatenate([gx, events.x.to_numpy()]), 'y': np.concatenate([gy, events.y.to_numpy()])})
    rows = np.floor((top - frame.y.to_numpy()) / res).astype(int)
    cols = np.floor((frame.x.to_numpy() - left) / res).astype(int)
    slope, aspect = derivatives(dem, res)
    frame['elevation'] = dem[rows, cols].astype(float)
    frame['slope'] = slope[rows, cols].astype(float)
    frame['aspect_sin'] = np.sin(np.deg2rad(aspect[rows, cols].astype(float)))
    frame['aspect_cos'] = np.cos(np.deg2rad(aspect[rows, cols].astype(float)))
    feats, meta = static_features_from_dem(dem, left, top, res, frame.x, frame.y)
    frame = pd.concat([frame, feats], axis=1)
    frame['longitude'], frame['latitude'] = INVERSE.transform(frame.x.to_numpy(), frame.y.to_numpy())
    frame['inside_austria'] = True        # LAU AT municipalities are Austrian by definition
    v4 = read_json(ROOT / 'config/v04.json')['features']
    vintage = land_cover_vintage(int(year))
    url, field = cfg['land_cover']['services'][vintage]
    pad = 0.003
    bounds = (frame.longitude.min() - pad, frame.latitude.min() - pad, frame.longitude.max() + pad, frame.latitude.max() + pad)
    tiles = max(1, math.ceil(max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / 0.06))
    geoms, codes = sources.land_cover_polygons(bounds, vintage, tiles, service=(url, field))
    lc = sources.land_cover_at(frame.longitude, frame.latitude, geoms, codes, v4['land_cover']['classes'])
    geo = sources.geology_at(frame.longitude, frame.latitude, v4['geology']['classes'])
    frame = add_one_hot(pd.concat([frame, lc, geo], axis=1))
    frame['reason'] = B.eligibility(frame, {'terrain': t})
    ok = frame.reason == ''
    X = frame.loc[ok, bundle['columns']]
    if X.isna().any().any():
        raise ValueError('NaN in a required static feature of an assessable cell')
    z = bundle['preprocessor'].transform(X, pd.Series(np.arange(len(X)), index=X.index))
    frame['score_model'] = np.nan
    frame.loc[ok, 'score_model'] = bundle['model'].decision_function(z)
    frame['score_slope'] = np.where(ok, frame.slope, np.nan)
    frame['campaign'], frame['component'] = campaign, index
    store.save_parquet(path, ident, frame, {'window': [left, top, n_rows, n_cols], 'land_cover_vintage': vintage,
                                            'land_cover_polygons': len(geoms), **meta, 'dem': dem_name})
    return store.load_parquet(path, ident)


# ---------- capture metric and bootstrap (pure) ----------

def capture_flags(grid_scores, event_scores, top_fraction):
    """Event captured if its score is finite and >= the top-fraction cutoff of the finite grid scores."""
    g = np.asarray(grid_scores, float)
    g = np.sort(g[np.isfinite(g)])[::-1]
    if len(g) == 0:
        raise ValueError('No assessable grid cell in the area')
    k = max(1, int(math.ceil(top_fraction * len(g))))
    cutoff = g[k - 1]
    e = np.asarray(event_scores, float)
    return np.isfinite(e) & (e >= cutoff), float(cutoff)


def block_ids(x_m, y_m, block_m):
    return [f'{int(a)}_{int(b)}' for a, b in zip(np.floor(np.asarray(x_m) / block_m), np.floor(np.asarray(y_m) / block_m))]


def bootstrap(per_area, draws, seed, block_m=2000):
    """Two-stage cluster bootstrap. per_area: {area: DataFrame(event rows with x, y, cap_* columns)}.
    Returns percentile intervals of area-weighted means of each cap_* column and of model - slope differences."""
    rng = np.random.default_rng(seed)
    names = sorted(per_area)
    cols = [c for c in per_area[names[0]].columns if c.startswith('cap_')]
    blocks = {}
    for a in names:
        f = per_area[a]
        ids = np.array(block_ids(f.x, f.y, block_m))
        blocks[a] = [f.loc[ids == b, cols].to_numpy(float) for b in sorted(set(ids))]
    out = {c: [] for c in cols}
    for _ in range(draws):
        sample = rng.choice(len(names), size=len(names), replace=True)
        means = {c: [] for c in cols}
        for i in sample:
            bl = blocks[names[i]]
            pick = rng.choice(len(bl), size=len(bl), replace=True)
            arr = np.vstack([bl[j] for j in pick])
            for k, c in enumerate(cols):
                means[c].append(arr[:, k].mean())
        for c in cols:
            out[c].append(float(np.mean(means[c])))
    res = {c: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for c, v in out.items()}
    for k in ('05', '20'):
        d = np.array(out[f'cap_model_{k}']) - np.array(out[f'cap_slope_{k}'])
        res[f'diff_{k}'] = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    return res


# ---------- area audit (no terrain, no scores) ----------

def area_audit():
    """Area composition per registered campaign; uses only inventory points and municipality polygons."""
    cfg = config()
    t = targets(cfg)
    lau = lau_austria()
    out = []
    for r in selected_campaigns(t, cfg).itertuples():
        a = area_of(t[t.campaign == r.campaign], lau, 5)
        out.append({'campaign': r.campaign, 'year': int(r.year), 'targets': int(r.n), 'targets_in_area': int(a['inside'].sum()),
                    'area_km2': round(a['union'].area / 1e6, 1), 'municipalities': a['municipalities'],
                    'components': [{'area_km2': round(c.area / 1e6, 1), 'bbox_km': [round((c.bounds[2] - c.bounds[0]) / 1000, 1),
                                                                              round((c.bounds[3] - c.bounds[1]) / 1000, 1)]}
                                   for c in a['components']]})
    write_json(guard(REPORT_GT) / 'areas.json', out)
    return out


# ---------- run ----------

def overlap_with_training(union):
    """V0.4 development events (the model's training groups) lying inside the area."""
    bundle = B.model_bundle(B.config())
    data = pd.read_parquet(ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet')
    pos = data[(data.label == 1) & data.event_group_id.isin(bundle['training_groups'])]
    return int(contains_xy(union, pos.x.to_numpy(), pos.y.to_numpy()).sum())


def evaluate_area(cfg, campaign, year, t_campaign, dem_name, bundle, lau):
    area = area_of(t_campaign, lau, 5)
    inside = t_campaign[area['inside']]
    frames = []
    for i, comp in enumerate(area['components']):
        ev = inside[contains_xy(comp, inside.x.to_numpy(), inside.y.to_numpy())]
        frames.append(compute_component(cfg, campaign, year, i, comp, ev, dem_name, bundle))
    f = pd.concat(frames, ignore_index=True)
    grid, ev = f[f.kind == 'grid'], f[f.kind == 'event'].copy()
    summary = {'campaign': campaign, 'year': int(year), 'targets_total': int(len(t_campaign)), 'targets_in_area': int(len(inside)),
               'targets_outside_area': int(len(t_campaign) - len(inside)), 'municipalities': area['municipalities'],
               'area_km2': round(area['union'].area / 1e6, 1), 'components': len(area['components']),
               'grid_cells': int(len(grid)), 'grid_assessable': int((grid.reason == '').sum()),
               'grid_not_assessable_by_reason': grid.reason[grid.reason != ''].value_counts().to_dict(),
               'targets_not_assessable_by_reason': ev.reason[ev.reason != ''].value_counts().to_dict(),
               'v04_training_events_inside': overlap_with_training(area['union'])}
    for method in ('model', 'slope'):
        for k, frac in (('05', .05), ('20', .20)):
            flags, cutoff = capture_flags(grid[f'score_{method}'], ev[f'score_{method}'], frac)
            ev[f'cap_{method}_{k}'] = flags.astype(float)
            summary[f'capture_{method}_{k}'] = round(float(flags.mean()), 4)
            summary[f'cutoff_{method}_{k}'] = round(cutoff, 4)
    summary['targets_not_assessable_share'] = round(float((ev.reason != '').mean()), 4)
    return summary, ev[['event_id', 'x', 'y', 'reason'] + [c for c in ev.columns if c.startswith('cap_')]]


def run(mode='pilot', dem_name='srtm'):
    """mode 'pilot' = smallest area only (technical check); 'full' = all registered areas, written once."""
    cfg = config()
    t = targets(cfg)
    camps = selected_campaigns(t, cfg)
    if mode == 'pilot':
        camps = camps.sort_values('n').head(1)
    out_name = {'full': 'test_results.json', 'pilot': f'pilot_{dem_name}.json'}[mode] if dem_name == 'srtm' else f'sensitivity_{dem_name}.json'
    target_path = guard(REPORT_GT) / out_name
    if mode == 'full' and target_path.exists():
        raise RuntimeError(f'{out_name} exists: the registered test is scored once; it is not rerun')
    bundle = B.model_bundle(B.config())
    lau = lau_austria()
    summaries, per_area = [], {}
    for r in camps.itertuples():
        s, ev = evaluate_area(cfg, r.campaign, r.year, t[t.campaign == r.campaign], dem_name, bundle, lau)
        summaries.append(s)
        per_area[r.campaign] = ev
    u = cfg['uncertainty']
    result = {'version': cfg['version'], 'mode': mode, 'dem': dem_name, 'computed_at_utc': datetime.now(timezone.utc).isoformat(),
              'config_sha256': hashlib.sha256(CONFIG_GT.read_bytes()).hexdigest(), 'areas': summaries,
              'area_weighted': {f'capture_{m}_{k}': round(float(np.mean([s[f'capture_{m}_{k}'] for s in summaries])), 4)
                                for m in ('model', 'slope') for k in ('05', '20')},
              'event_pooled': {f'capture_{m}_{k}': round(float(pd.concat(per_area.values())[f'cap_{m}_{k}'].mean()), 4)
                               for m in ('model', 'slope') for k in ('05', '20')},
              'chance': {'05': 0.05, '20': 0.20}}
    if len(per_area) > 1:
        result['bootstrap_95'] = bootstrap(per_area, u['draws'], u['seed'])
    write_json(target_path, result)
    events_path = guard(DATA_GT / 'results') / out_name.replace('.json', '_events.parquet')
    pd.concat([ev.assign(campaign=a) for a, ev in per_area.items()]).to_parquet(events_path, index=False)
    return result


