"""V0.4 terrain: V0 matching on unchanged inputs, plus local and hydrological terrain features.

All rasters are the Skadi 1 arc-second composite reprojected to a 30 m EPSG:31287 grid. Baseline
caches are read only (checksum-verified); everything new is written below data/v04/cache/.
"""
import gzip
import hashlib
import math
import shutil
import subprocess
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds, Resampling
from rasterio.windows import from_bounds, Window
from scipy import ndimage
from scipy.signal import fftconvolve
from shapely import contains_xy

from ..common import read_json, write_json, digest
from ..matching import angular_distance
from ..sources import ROOT
from ..terrain import PROJECT, INVERSE, derivatives, sample
from .paths import V04_DATA, guard

BASE_TILES = ROOT / 'data/raw/terrain'
BASE_TERRAIN = ROOT / 'data/interim/terrain'
CACHE = V04_DATA / 'cache'
_VERIFIED = set()


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def tile(lat, lon, event_day):
    """Skadi tile; baseline copy read only, otherwise downloaded into data/v04/cache/terrain_tiles."""
    name = f'N{lat:02d}E{lon:03d}'
    directory = BASE_TILES if (BASE_TILES / f'{name}.json').exists() else guard(CACHE / 'terrain_tiles')
    hgt, manifest = directory / f'{name}.hgt', directory / f'{name}.json'
    if not manifest.exists():
        url = f'https://elevation-tiles-prod.s3.amazonaws.com/skadi/N{lat:02d}/{name}.hgt.gz'
        compressed, headers = directory / f'{name}.hgt.gz', directory / f'{name}.headers.txt'
        subprocess.run([shutil.which('curl.exe') or 'curl', '-f', '-sS', '-L', '--retry', '2', '--max-time', '180',
                        '-D', str(headers), '-o', str(compressed), url], check=True, timeout=550)
        last = [s.split(':', 1)[1].strip() for s in headers.read_text().splitlines() if s.lower().startswith('last-modified:')]
        if not last:
            raise ValueError('Terrain object lacks dated provenance')
        modified = parsedate_to_datetime(last[-1])
        with gzip.open(compressed, 'rb') as src, hgt.with_suffix('.tmp').open('wb') as dst:
            shutil.copyfileobj(src, dst)
        hgt.with_suffix('.tmp').replace(hgt)
        if hgt.stat().st_size != 3601 * 3601 * 2:
            raise ValueError('Unexpected Skadi dimensions')
        write_json(manifest, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                              'object_last_modified': modified.isoformat(), 'sha256': sha(hgt),
                              'source': 'Mapzen Skadi composite; attribution includes Austrian DGM, EU-DEM and USGS',
                              'vertical_datum': 'EGM96', 'resolution': '1 arc second', 'nodata': -32768})
    meta = read_json(manifest)
    if str(hgt) not in _VERIFIED:
        if sha(hgt) != meta['sha256']:
            raise ValueError('Terrain source cache checksum mismatch')
        _VERIFIED.add(str(hgt))
    if meta['object_last_modified'][:10] >= event_day:
        raise ValueError('terrain_source_not_demonstrably_pre_event')
    return hgt, meta


def dem_window(lon, lat, radius, res, crs, event_day):
    px, py = PROJECT.transform(lon, lat)
    n = math.ceil(2 * radius / res)
    left, top = px - radius, py + radius
    transform = from_origin(left, top, res, res)
    dem = np.full((n, n), np.nan, dtype='float32')
    bounds = transform_bounds(crs, 'EPSG:4326', left, top - n * res, left + n * res, top, densify_pts=21)
    sources = []
    for tlon in range(math.floor(bounds[0]), math.floor(bounds[2]) + 1):
        for tlat in range(math.floor(bounds[1]), math.floor(bounds[3]) + 1):
            path, meta = tile(tlat, tlon, event_day)
            with rasterio.open(path) as src:
                if src.crs.to_epsg() != 4326 or src.nodata != -32768:
                    raise ValueError('Unexpected DEM CRS/nodata')
                win = from_bounds(max(bounds[0] - .001, src.bounds.left), max(bounds[1] - .001, src.bounds.bottom),
                                  min(bounds[2] + .001, src.bounds.right), min(bounds[3] + .001, src.bounds.top), src.transform)
                win = win.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
                reproject(src.read(1, window=win), dem, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, src_nodata=-32768, dst_nodata=np.nan,
                          init_dest_nodata=False, resampling=Resampling.bilinear)
            sources.append(meta)
    return dem, left, top, sources


def matching_terrain(event, cfg):
    """Identical algorithm and cache identity as the V0 matching window (preslide.terrain.local_terrain)."""
    identity = digest({'lon': event['longitude'], 'lat': event['latitude'], 't0': event['event_day'],
                       'radius': cfg['control_max_distance_m'], 'resolution': cfg['terrain_resolution_m'], 'algorithm': 1})
    for directory in (BASE_TERRAIN, CACHE / 'terrain'):
        path = directory / f'{identity}.npz'
        if path.exists():
            meta = read_json(path.with_suffix('.json'))
            if sha(path) != meta['sha256']:
                raise ValueError('Terrain feature cache checksum mismatch')
            if any(s['object_last_modified'][:10] >= event['event_day'] for s in meta['sources']):
                raise ValueError('terrain_source_not_demonstrably_pre_event')
            z = np.load(path)
            return {k: z[k] for k in z.files}
    dem, left, top, sources = dem_window(event['longitude'], event['latitude'], cfg['control_max_distance_m'] + 300,
                                         cfg['terrain_resolution_m'], cfg['terrain_crs'], event['event_day'])
    slope, aspect = derivatives(dem, cfg['terrain_resolution_m'])
    result = {'elevation': dem, 'slope': slope, 'aspect': aspect, 'left': np.array(left), 'top': np.array(top),
              'resolution': np.array(cfg['terrain_resolution_m'])}
    path = guard(CACHE / 'terrain') / f'{identity}.npz'
    np.savez_compressed(path, **result)
    write_json(path.with_suffix('.json'), {'sources': sources, 'event_id': event['event_id'], 'crs': cfg['terrain_crs'],
                                           'sha256': sha(path)})
    return result


def match_event(event, cfg, exclusions, country):
    """V0 preslide.matching.match_event, unchanged logic; candidate pool written to data/v04."""
    terrain = matching_terrain(event, cfg)
    px, py = PROJECT.transform(event['longitude'], event['latitude'])
    positive = {k: float(v[0]) for k, v in sample(terrain, [px], [py]).items()}
    if not all(np.isfinite(v) for v in positive.values()) or not 0 <= positive['elevation'] <= 4500:
        raise ValueError('invalid_positive_terrain')
    if positive['slope'] < cfg['minimum_slope_deg']:
        raise ValueError('positive_dem_slope_below_minimum')
    rng = np.random.default_rng(int(digest([event['event_id'], cfg['random_seed']])[:8], 16))
    n = cfg['candidate_pool_size']
    distance = np.sqrt(rng.uniform(cfg['control_min_distance_m'] ** 2, cfg['control_max_distance_m'] ** 2, n))
    angle = rng.uniform(0, 2 * np.pi, n)
    xy = np.column_stack([px + distance * np.cos(angle), py + distance * np.sin(angle)])
    lon, lat = INVERSE.transform(xy[:, 0], xy[:, 1])
    frame = pd.DataFrame({'x': xy[:, 0], 'y': xy[:, 1], 'longitude': lon, 'latitude': lat,
                          'distance_to_positive_m': distance, **sample(terrain, xy[:, 0], xy[:, 1])})
    frame['slope_difference_deg'] = np.abs(frame.slope - positive['slope'])
    frame['elevation_difference_m'] = np.abs(frame.elevation - positive['elevation'])
    frame['aspect_difference_deg'] = angular_distance(frame.aspect, positive['aspect'])
    frame['inventory_clear'] = exclusions.allowed(xy)
    frame['inside_austria'] = contains_xy(country, lon, lat)
    keep = (frame.inventory_clear & frame.inside_austria & (frame.slope >= cfg['minimum_slope_deg']) &
            (frame.slope_difference_deg <= cfg['slope_caliper_deg']) &
            (frame.elevation_difference_m <= cfg['elevation_caliper_m']) &
            (frame.aspect_difference_deg <= cfg['aspect_caliper_deg']))
    frame['matching_score'] = ((frame.slope_difference_deg / cfg['slope_caliper_deg']) ** 2 +
                               (frame.elevation_difference_m / cfg['elevation_caliper_m']) ** 2 +
                               (frame.aspect_difference_deg / cfg['aspect_caliper_deg']) ** 2 +
                               0.15 * (distance / cfg['control_max_distance_m']) ** 2)
    frame['passes_calipers'] = keep
    selected = []
    for i, row in frame[keep].sort_values('matching_score').iterrows():
        if all(np.linalg.norm(xy[i] - xy[j]) >= cfg['control_separation_m'] for j in selected):
            selected.append(i)
        if len(selected) == cfg['controls_per_event']:
            break
    frame.to_parquet(guard(CACHE / 'control_pools') / f"{event['event_id']}.parquet", index=False)
    if len(selected) < cfg['controls_per_event']:
        raise ValueError(f'insufficient_controls:{len(selected)}_from_{int(keep.sum())}_eligible')
    common = {'event_group_id': event['event_id'], 'event_day': event['event_day'], 't0_utc': event['t0_utc'],
              'time_quality': event['time_quality'], 'state': event['state'],
              'source_position_upper_m': event['position_accuracy_upper_m'], 'process_type': event['process_type_original']}
    rows = [{**common, 'sample_id': event['event_id'] + '_positive', 'label': 1, 'sample_type': 'POSITIVE',
             'longitude': event['longitude'], 'latitude': event['latitude'], 'x': px, 'y': py, **positive,
             'distance_to_positive_m': 0., 'matching_score': 0., 'slope_difference_deg': 0.,
             'elevation_difference_m': 0., 'aspect_difference_deg': 0., 'inventory_clear': True, 'inside_austria': True}]
    for number, i in enumerate(selected, 1):
        rows.append({**common, **frame.loc[i].drop('passes_calipers').to_dict(),
                     'sample_id': f"{event['event_id']}_control_{number:02d}", 'label': 0, 'sample_type': 'PSEUDO_NEGATIVE'})
    data = pd.DataFrame(rows)
    data['aspect_sin'] = np.sin(np.deg2rad(data.aspect))
    data['aspect_cos'] = np.cos(np.deg2rad(data.aspect))
    return data, {'candidate_pool': n, 'eligible_pool': int(keep.sum()), 'selected': len(selected)}


# ---------- local terrain features ----------

def curvatures(z, res):
    """Zevenbergen & Thorne (1987) profile/plan curvature in 1/(100 m); ArcGIS sign convention."""
    p = np.pad(z, 1, mode='edge')
    z1, z2, z3 = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    z4, z5, z6 = p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:]
    z7, z8, z9 = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    D = ((z4 + z6) / 2 - z5) / res ** 2
    E = ((z2 + z8) / 2 - z5) / res ** 2
    F = (-z1 + z3 + z7 - z9) / (4 * res ** 2)
    G = (-z4 + z6) / (2 * res)
    H = (z2 - z8) / (2 * res)
    g2 = G ** 2 + H ** 2
    with np.errstate(invalid='ignore', divide='ignore'):
        profile = np.where(g2 > 1e-12, -2 * (D * G ** 2 + E * H ** 2 + F * G * H) / g2, 0.0) * 100
        plan = np.where(g2 > 1e-12, 2 * (D * H ** 2 + E * G ** 2 - F * G * H) / g2, 0.0) * 100
    tri = np.mean([np.abs(n - z5) for n in (z1, z2, z3, z4, z6, z7, z8, z9)], axis=0)
    return profile, plan, tri


def disc(radius_cells):
    r = int(np.ceil(radius_cells))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return (xx ** 2 + yy ** 2 <= radius_cells ** 2).astype(float)


def focal_mean(z, kernel):
    valid = np.isfinite(z).astype(float)
    total = fftconvolve(np.where(valid > 0, z, 0.0), kernel, mode='same')
    count = fftconvolve(valid, kernel, mode='same')
    with np.errstate(invalid='ignore', divide='ignore'):
        out = total / count
    out[count < 0.99 * kernel.sum()] = np.nan      # incomplete neighbourhood (window edge / nodata)
    return out


def fill_depressions(z, eps=1e-3, max_iter=20000):
    """Planchon & Darboux (2001): smallest surface >= z draining to the window edge with gradient eps."""
    big = 1e9
    outlet = np.zeros(z.shape, bool)
    outlet[0, :] = outlet[-1, :] = outlet[:, 0] = outlet[:, -1] = True
    finite = np.isfinite(z)
    outlet |= ~finite | ~ndimage.binary_erosion(finite, np.ones((3, 3)), border_value=1)
    zz = np.where(finite, z, -big).astype(float)
    w = np.where(outlet, zz, big)
    footprint = np.ones((3, 3), bool)
    footprint[1, 1] = False
    for iteration in range(max_iter):
        lowest = ndimage.minimum_filter(w, footprint=footprint, mode='constant', cval=big)
        new = np.where(outlet, w, np.maximum(zz, np.minimum(w, lowest + eps)))
        if np.array_equal(new, w):
            return w, outlet, iteration
        w = new
    raise RuntimeError('Depression filling did not converge')


OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def flow_accumulation(w, outlet, res):
    """D8 on the filled surface; returns contributing cells and an 'edge-influenced' flag per cell."""
    rows, cols = w.shape
    best = np.zeros(w.shape)
    receiver = np.full(w.shape, -1, dtype=np.int64)
    flat = np.arange(w.size).reshape(w.shape)
    pad_w = np.pad(w, 1, mode='constant', constant_values=np.inf)
    pad_i = np.pad(flat, 1, mode='constant', constant_values=-1)
    for dr, dc in OFFSETS:
        neighbour = pad_w[1 + dr:1 + dr + rows, 1 + dc:1 + dc + cols]
        drop = (w - neighbour) / (res * np.hypot(dr, dc))
        better = drop > best
        best = np.where(better, drop, best)
        receiver = np.where(better, pad_i[1 + dr:1 + dr + rows, 1 + dc:1 + dc + cols], receiver)
    # Border cells keep their downslope receiver: water entering from outside the window flows through them,
    # so everything downstream of a border cell is flagged as possibly truncated. Nodata cells are sinks.
    receiver[w < -1e8] = -1
    acc = np.ones(w.size)
    edge = outlet.ravel().copy()
    order = np.argsort(-w.ravel(), kind='stable')
    rec = receiver.ravel()
    acc_l, edge_l, rec_l = acc.tolist(), edge.tolist(), rec.tolist()
    for i in order.tolist():
        r = rec_l[i]
        if r >= 0:
            acc_l[r] += acc_l[i]
            if edge_l[i]:
                edge_l[r] = True
    return np.array(acc_l).reshape(w.shape), np.array(edge_l).reshape(w.shape)


def static_features(event, samples, cfg, margin_m=5010):
    """Local and hydrological terrain features at the six sample points (NaN = not computable, never imputed)."""
    res = cfg['terrain_resolution_m']
    radius = cfg['control_max_distance_m'] + 300 + margin_m
    dem, left, top, _ = dem_window(event['longitude'], event['latitude'], radius, res, cfg['terrain_crs'], event['event_day'])
    slope, _ = derivatives(dem, res)
    profile, plan, tri = curvatures(dem.astype(float), res)
    tpi150 = dem - focal_mean(dem.astype(float), disc(150 / res))
    tpi500 = dem - focal_mean(dem.astype(float), disc(500 / res))
    fp = disc(500 / res) > 0
    zmin = ndimage.minimum_filter(np.nan_to_num(dem, nan=np.inf), footprint=fp, mode='constant', cval=np.inf)
    zmax = ndimage.maximum_filter(np.nan_to_num(dem, nan=-np.inf), footprint=fp, mode='constant', cval=-np.inf)
    with np.errstate(invalid='ignore', divide='ignore'):
        relpos = (dem - zmin) / (zmax - zmin)
    relpos[~np.isfinite(tpi500)] = np.nan
    filled, outlet, iterations = fill_depressions(dem.astype(float))
    acc, edge = flow_accumulation(filled, outlet, res)
    cols = np.floor((samples.x.to_numpy() - left) / res).astype(int)
    rows = np.floor((top - samples.y.to_numpy()) / res).astype(int)
    if (rows < 0).any() or (cols < 0).any() or (rows >= dem.shape[0]).any() or (cols >= dem.shape[1]).any():
        raise ValueError('Sample outside static terrain window')
    area = acc[rows, cols] * res * res
    truncated = edge[rows, cols]
    beta = np.deg2rad(np.maximum(slope[rows, cols], 0.1))
    out = pd.DataFrame({'sample_id': samples.sample_id.to_numpy(),
                        'profile_curvature': profile[rows, cols], 'plan_curvature': plan[rows, cols],
                        'roughness_tri': tri[rows, cols], 'tpi_150m': tpi150[rows, cols], 'tpi_500m': tpi500[rows, cols],
                        'relative_position_500m': relpos[rows, cols],
                        'log10_catchment_m2': np.where(truncated, np.nan, np.log10(area)),
                        'twi': np.where(truncated, np.nan, np.log(area / res / np.tan(beta))),
                        'catchment_truncated': truncated,
                        'static_dem_elevation_check': dem[rows, cols]})
    meta = {'window_radius_m': radius, 'cells': int(dem.size), 'fill_iterations': int(iterations),
            'nodata_cells': int(np.isnan(dem).sum()), 'truncated_samples': int(truncated.sum())}
    return out, meta
