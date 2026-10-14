"""Data-availability audit for candidate new PreSlide features (no model training, no labels used for selection).

Five development events of the frozen baseline run 046074ba6f12556c (train/validation only, never test) and their
five controls are enriched from each candidate source. Reported per source: accessibility, real resolution/CRS/nodata,
licence, temporal validity relative to t0 and the label-free variance decomposition (within-group vs between-group).

Usage: python scripts/feature_audit_v04.py [--data-root PATH] [--only SOURCE ...]
`--data-root` points to the checkout holding the git-ignored `data/` directory (defaults to this repository).
Writes: <data-root>/data/feature_audit_v04/ (raw/cache) and reports/feature_audit_v04/ (CSV/JSON summaries).
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
RUN = '046074ba6f12556c'
N_EVENTS = 5
SOURCES = ['terrain30', 'geology', 'soilgrids', 'worldcover', 'tcd', 'gfc', 'osm', 'daily', 'inca_derived']

parser = argparse.ArgumentParser()
parser.add_argument('--data-root', default=str(REPO))
parser.add_argument('--only', nargs='*', default=SOURCES)
args = parser.parse_args()
DATA_ROOT = Path(args.data_root).resolve()

import preslide.sources  # noqa: E402
preslide.sources.ROOT = DATA_ROOT          # read baseline caches/tiles from the data checkout (read only)
from preslide.terrain import PROJECT, INVERSE, derivatives  # noqa: E402
from preslide.v04 import terrain as v04t  # noqa: E402
from preslide.v04 import weather as v04w  # noqa: E402

OUT = DATA_ROOT / 'data/feature_audit_v04'
HTTP = OUT / 'http'
REPORT = REPO / 'reports/feature_audit_v04'
for d in (OUT, HTTP, REPORT):
    d.mkdir(parents=True, exist_ok=True)
CA = DATA_ROOT / 'data/runtime/windows-ca.pem'
if CA.exists():
    os.environ.setdefault('CURL_CA_BUNDLE', str(CA))
os.environ.setdefault('GDAL_HTTP_TIMEOUT', '90')
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
os.environ.setdefault('CPL_VSIL_CURL_ALLOWED_EXTENSIONS', '.tif,.vrt,.ovr')
CURL = shutil.which('curl.exe') or shutil.which('curl')
UA = 'PreSlide-feature-audit/0.4 (non-commercial research)'
_last = [0.0]


# ---------------------------------------------------------------- cache
def fetch(url, params=None, data=None, min_interval=0.5, kind='json'):
    """Immutable response cache: key = sha256(full url [+ POST body]); baseline/V0.4 caches are read first."""
    target = url + ('?' + urlencode(sorted((params or {}).items()), doseq=True) if params else '')
    key = hashlib.sha256((target + ('\n' + data if data else '')).encode()).hexdigest()
    for directory in (DATA_ROOT / 'data/raw/http', DATA_ROOT / 'data/v04/cache/http', HTTP):
        path = directory / f'{key}.json'
        if path.exists():
            meta = json.loads(path.with_suffix('.meta.json').read_text(encoding='utf-8'))
            if meta['sha256'] != hashlib.sha256(path.read_bytes()).hexdigest():
                raise RuntimeError(f'Cache integrity failure {path}')
            return json.loads(path.read_text(encoding='utf-8'))
    wait = _last[0] + min_interval - time.time()
    if wait > 0:
        time.sleep(wait)
    cmd = [CURL, '-sS', '-L', '--max-time', '300', '-A', UA, '-w', '\n%{http_code}']
    if data:
        cmd += ['--data-urlencode', f'data={data}']
    for attempt in range(4):
        _last[0] = time.time()
        r = subprocess.run(cmd + [target], capture_output=True, timeout=400)
        body, _, code = r.stdout.rpartition(b'\n')
        if r.returncode == 0 and code == b'200':
            break
        time.sleep(30 * (attempt + 1))
    else:
        raise RuntimeError(f'HTTP {code!r} for {target[:160]}: {body[:200]!r}')
    parsed = json.loads(body)
    if isinstance(parsed, dict) and 'error' in parsed:
        raise RuntimeError(f"Source error {parsed['error']}")
    path = HTTP / f'{key}.json'
    path.write_bytes(body)
    path.with_suffix('.meta.json').write_text(json.dumps({
        'url': target, 'post_data': data, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'sha256': hashlib.sha256(body).hexdigest()}, indent=2), encoding='utf-8')
    return parsed


def head(url):
    r = subprocess.run([CURL, '-sS', '-I', '-L', '--max-time', '60', url], capture_output=True, text=True, timeout=90)
    h = {}
    for line in r.stdout.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            h[k.strip().lower()] = v.strip()
    return {'content_length': h.get('content-length'), 'last_modified': h.get('last-modified')}


# ---------------------------------------------------------------- samples
def samples():
    d = pd.read_parquet(DATA_ROOT / f'data/processed/{RUN}/evaluation_dataset.parquet')
    dev = d[d.partition.isin(['train', 'validation'])]
    pos = dev[dev.label == 1].copy()
    pos['h'] = pos.event_group_id.map(lambda s: hashlib.sha256(s.encode()).hexdigest())
    chosen, clusters, dates = [], set(), set()
    for r in pos.sort_values('h').itertuples():         # deterministic, label-free, distinct storm and date
        if r.dependence_cluster in clusters or r.event_date in dates:
            continue
        chosen.append(r.event_group_id)
        clusters.add(r.dependence_cluster)
        dates.add(r.event_date)
        if len(chosen) == N_EVENTS:
            break
    s = d[d.event_group_id.isin(chosen)].copy()
    s['t0_utc'] = s.event_date.map(lambda x: pd.Timestamp(x, tz='Europe/Vienna').tz_convert('UTC'))
    assert (s.groupby('event_group_id').size() == 6).all()
    assert s.groupby('event_group_id').event_date.nunique().eq(1).all()
    return s.reset_index(drop=True), dev


# ---------------------------------------------------------------- statistics (label free)
def decompose(frame, features):
    """Within-group std (pooled, ddof=0 over the 6 slopes) vs std of group means; no label is used."""
    rows = []
    for f in features:
        v = frame[['event_group_id', f]].dropna()
        g = v.groupby('event_group_id')[f]
        n_groups = g.ngroups
        within = float(np.sqrt(g.var(ddof=0).mean())) if n_groups else np.nan
        between = float(g.mean().std(ddof=0)) if n_groups > 1 else np.nan
        distinct = g.nunique()
        rows.append({'feature': f, 'n_samples': len(v), 'n_missing': int(frame[f].isna().sum()), 'n_groups': n_groups,
                     'mean': float(v[f].mean()) if len(v) else np.nan,
                     'within_group_std': within, 'between_group_std': between,
                     'within_share': within ** 2 / (within ** 2 + between ** 2) if within + between > 0 else np.nan,
                     'groups_all_identical': int((distinct == 1).sum()),
                     'mean_distinct_values_per_group': float(distinct.mean()) if n_groups else np.nan})
    return pd.DataFrame(rows)


def summarize(source, frame, features, meta):
    stats = decompose(frame, features)
    for k in ('accessible', 'resolution', 'crs', 'nodata', 'licence', 'temporal_rule', 'leakage_notes'):
        stats[k] = meta.get(k)
    stats.insert(0, 'source', source)
    stats.to_csv(REPORT / f'{source}.csv', index=False)
    frame.to_parquet(OUT / f'{source}_values.parquet', index=False)
    (REPORT / f'{source}_meta.json').write_text(json.dumps(meta, indent=2, default=str), encoding='utf-8')
    print(stats[['feature', 'n_missing', 'within_group_std', 'between_group_std', 'groups_all_identical']].to_string())
    return stats


def base(s):
    return s[['event_group_id', 'sample_id', 'event_date']].copy()


# ---------------------------------------------------------------- A: terrain from the existing 30 m composite
def terrain30(s):
    out = []
    cfg = json.loads((REPO / 'config/experiment.json').read_text())
    res, crs = 30, 'EPSG:31287'
    feats_meta = []
    for gid, grp in s.groupby('event_group_id'):
        pos = grp[grp.label == 1].iloc[0]
        event = {'longitude': pos.longitude, 'latitude': pos.latitude, 'event_day': pos.event_date}
        radius = 10000 + 300 + 5010
        dem, left, top, srcs = v04t.dem_window(pos.longitude, pos.latitude, radius, res, crs, pos.event_date)
        slope, _ = derivatives(dem, res)
        profile, plan, tri = v04t.curvatures(dem.astype(float), res)
        tpi150 = dem - v04t.focal_mean(dem.astype(float), v04t.disc(150 / res))
        filled, outlet, it = v04t.fill_depressions(dem.astype(float))
        acc, edge = v04t.flow_accumulation(filled, outlet, res)
        area = acc * res * res
        from scipy import ndimage
        dist = {}
        for thr in (1e5, 1e6):                             # channel initiation at 0.1 km2 and 1 km2 upslope area
            stream = (area >= thr) & ~edge
            dist[thr] = ndimage.distance_transform_edt(~stream) * res
        rows = np.floor((top - grp.y.to_numpy()) / res).astype(int)
        cols = np.floor((grp.x.to_numpy() - left) / res).astype(int)
        beta = np.deg2rad(np.maximum(slope[rows, cols], 0.1))
        tr = edge[rows, cols]
        a = area[rows, cols]
        out.append(pd.DataFrame({
            'sample_id': grp.sample_id.to_numpy(),
            'profile_curvature': profile[rows, cols], 'plan_curvature': plan[rows, cols],
            'roughness_tri': tri[rows, cols], 'tpi_150m': tpi150[rows, cols],
            'log10_catchment_m2': np.where(tr, np.nan, np.log10(a)),
            'twi': np.where(tr, np.nan, np.log(a / res / np.tan(beta))),
            'dist_stream_0p1km2_m': dist[1e5][rows, cols], 'dist_stream_1km2_m': dist[1e6][rows, cols],
            'dem_check_minus_stored_elev': dem[rows, cols] - grp.elevation.to_numpy()}))
        feats_meta.append({'event_group_id': gid, 'tiles_last_modified': sorted({m['object_last_modified'] for m in srcs}),
                           'fill_iterations': int(it), 'truncated': int(tr.sum()), 'nodata_cells': int(np.isnan(dem).sum())})
    f = base(s).merge(pd.concat(out), on='sample_id')
    feats = [c for c in f.columns if c not in ('event_group_id', 'sample_id', 'event_date', 'dem_check_minus_stored_elev')]
    meta = {'accessible': 'yes (cached Skadi tiles, no download)', 'resolution': '1 arcsec composite resampled to 30 m',
            'crs': 'EPSG:31287 (from EPSG:4326 HGT)', 'nodata': -32768, 'licence': 'composite; Austrian DGM CC BY 3.0 AT / EU-DEM / USGS',
            'temporal_rule': 'tile Last-Modified must precede t0 (all 2016)',
            'leakage_notes': 'DEM predates all baseline events; 30 m smooths slope-scale form (10 m DGM not downloaded, see report)',
            'dem_check_max_abs_m': float(np.nanmax(np.abs(f.dem_check_minus_stored_elev))), 'groups': feats_meta}
    return f, feats, meta


# ---------------------------------------------------------------- A: geology 1:200k / 1:500k (GeoSphere, CC BY 4.0)
GEOLOGY = {'stmk_200': 2, 'ober_200': 4, 'szbg_200': 3, 'nied_200': 1, 'vrbg_100': 4}
GEO_BASE = 'https://gis.geosphere.at/maps/rest/services/geologie/'


def geology(s):
    recs = []
    for r in s.itertuples():
        rec = {'sample_id': r.sample_id}
        for svc, layer in list(GEOLOGY.items()) + [('karte_500', 1)]:
            q = fetch(f'{GEO_BASE}{svc}/MapServer/{layer}/query', {
                'geometry': f'{r.longitude:.7f},{r.latitude:.7f}', 'geometryType': 'esriGeometryPoint', 'inSR': 4326,
                'spatialRel': 'esriSpatialRelIntersects', 'outFields': '*', 'returnGeometry': 'false', 'f': 'json'})
            feats = q.get('features', [])
            if feats:
                a = feats[0]['attributes']
                text = a.get('LEGTEXT') or a.get('LEGTEXT_EN') or a.get('legendtext') or json.dumps(a)[:200]
                key = 'geo500' if svc == 'karte_500' else 'geo200'
                if key + '_unit' not in rec:
                    rec[key + '_unit'] = str(text)[:160]
                    rec[key + '_service'] = svc
        recs.append(rec)
    f = base(s).merge(pd.DataFrame(recs), on='sample_id')
    for key in ('geo200', 'geo500'):
        col = f'{key}_unit'
        if col not in f:
            f[col] = None
        f[f'{key}_code'] = f[col].astype('category').cat.codes.replace(-1, np.nan).astype(float)
    meta = {'accessible': 'yes (ArcGIS REST point query, no auth)', 'resolution': 'vector 1:200 000 (Stmk/OÖ/Sbg/NÖ), 1:100 000 (Vbg), 1:500 000 (all Austria)',
            'crs': 'service native, queried with inSR=4326', 'nodata': 'no polygon hit -> missing',
            'licence': 'CC BY 4.0 ©GeoSphere Austria (service iteminfo)',
            'temporal_rule': 'static map; no event-specific content',
            'leakage_notes': 'check legend for mass-movement deposit units (Rutschmasse/Hangschutt) mapped from the event itself; '
                             'no 1:200k for Tirol/Kärnten',
            'units_found': sorted(set(f.geo200_unit.dropna()) | set(f.geo500_unit.dropna()))}
    return f, ['geo200_code', 'geo500_code'], meta


# ---------------------------------------------------------------- raster point sampling over HTTP (windowed reads only)
class RangeFile:
    """Read-only HTTP file using Range requests (Python TLS verification; GDAL's schannel curl fails the local
    certificate chain). Fetches 256 KiB chunks on demand, so only the needed GeoTIFF blocks are transferred."""
    CHUNK = 1 << 18
    bytes_fetched = 0
    shared = {}                                     # (url, chunk) -> bytes, shared by all handles GDAL opens

    def __init__(self, url):
        import urllib.request
        self.url, self.pos, self._ur = url, 0, urllib.request
        self.cache = RangeFile.shared.setdefault(url, {})
        with self._ur.urlopen(self._ur.Request(url, method='HEAD', headers={'User-Agent': UA}), timeout=60) as r:
            self.size = int(r.headers['Content-Length'])

    def _chunk(self, i):
        if i not in self.cache:
            a, b = i * self.CHUNK, min(self.size, (i + 1) * self.CHUNK) - 1
            req = self._ur.Request(self.url, headers={'Range': f'bytes={a}-{b}', 'User-Agent': UA})
            for attempt in range(4):
                try:
                    with self._ur.urlopen(req, timeout=120) as r:
                        self.cache[i] = r.read()
                    break
                except OSError:
                    time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError(f'range read failed {self.url}')
            RangeFile.bytes_fetched += len(self.cache[i])
            if RangeFile.bytes_fetched > 300e6:          # per-source budget: stay far below the 1 GB confirmation limit
                raise RuntimeError('range-read budget exceeded (300 MB)')
        return self.cache[i]

    def read(self, n=-1):
        end = self.size if n is None or n < 0 else min(self.size, self.pos + n)
        out = bytearray()
        while self.pos < end:
            i, off = divmod(self.pos, self.CHUNK)
            c = self._chunk(i)[off:off + end - self.pos]
            out += c
            self.pos += len(c)
        return bytes(out)

    def seek(self, pos, whence=0):
        self.pos = pos if whence == 0 else self.pos + pos if whence == 1 else self.size + pos
        return self.pos

    def tell(self):
        return self.pos

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def http_open(path, mode='rb'):
    """rasterio `opener` callable (rasterio >= 1.4); VRT-relative member paths are re-joined to https://."""
    path = path.replace(chr(92), '/')
    if not path.startswith('https://'):
        path = 'https://' + path.split('https:/', 1)[-1].lstrip('/')
    return RangeFile(path)


class HTTPOpener:
    """rasterio `opener` (rasterio >= 1.4): resolves VRT-relative paths against the remote base URL."""
    def open(self, path, mode='rb'):
        return RangeFile(path.replace('\\', '/').replace('https:/', 'https://', 1) if 'https://' not in path else path)

    def isfile(self, path):
        return True

    def isdir(self, path):
        return False

    def ls(self, path):
        return []

    def mtime(self, path):
        return 0

    def size(self, path):
        return RangeFile(path).size


def sample_raster(url, lons, lats, radius_px=0, valid=None):
    import rasterio
    from rasterio.warp import transform as wtransform
    from rasterio.windows import Window
    with rasterio.open(url, opener=http_open) as src:
        xs, ys = wtransform('EPSG:4326', src.crs, list(lons), list(lats))
        info = {'crs': str(src.crs), 'res': src.res, 'nodata': src.nodata, 'dtype': src.dtypes[0],
                'blocks': src.block_shapes[0], 'size': (src.width, src.height)}
        point, patch = [], []
        for x, y in zip(xs, ys):
            row, col = src.index(x, y)
            w = Window(col - radius_px, row - radius_px, 2 * radius_px + 1, 2 * radius_px + 1)
            a = src.read(1, window=w, boundless=True, fill_value=src.nodata if src.nodata is not None else 0).astype(float)
            if src.nodata is not None:
                a[a == src.nodata] = np.nan
            point.append(a[radius_px, radius_px])
            patch.append(a)
    return np.array(point), patch, info


def tile3(lat, lon):
    la, lo = 3 * math.floor(lat / 3), 3 * math.floor(lon / 3)
    return f'N{la:02d}E{lo:03d}'


def worldcover(s):
    out, info = [], {}
    for ver, year in (('v100', 2020), ('v200', 2021)):
        vals, forest = np.full(len(s), np.nan), np.full(len(s), np.nan)
        for t, idx in s.groupby(s.apply(lambda r: tile3(r.latitude, r.longitude), axis=1)).groups.items():
            url = f'https://esa-worldcover.s3.eu-central-1.amazonaws.com/{ver}/{year}/map/ESA_WorldCover_10m_{year}_{ver}_{t}_Map.tif'
            p, patches, info[f'{year}'] = sample_raster(url, s.loc[idx, 'longitude'], s.loc[idx, 'latitude'], radius_px=2)
            vals[idx] = p
            forest[idx] = [np.nanmean(a == 10) for a in patches]          # tree-cover share in 5x5 (~50 m) patch
        out += [(f'wc{year}_class', vals), (f'wc{year}_tree_share_50m', forest)]
    f = base(s)
    for k, v in out:
        f[k] = v
    meta = {'accessible': 'yes (public COG on AWS, windowed /vsicurl reads)', 'resolution': f"{info['2021']['res']} deg (~10 m)",
            'crs': info['2021']['crs'], 'nodata': info['2021']['nodata'], 'licence': 'CC BY 4.0 © ESA WorldCover project',
            'temporal_rule': 'map year 2020 (v100) / 2021 (v200): admissible only if map year < event year',
            'leakage_notes': 'a post-event map can show the landslide scar as bare/grass -> for events <= 2021 the map is NOT pre-event; '
                             'v100 and v200 use different algorithms, class changes are partly method artefacts',
            'raster_info': info}
    return f, [k for k, _ in out], meta


def tcd(s):
    url = 'https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLandPublic/HRL_TreeCoverDensity_2018/ImageServer/getSamples'
    pts = {'points': [[r.longitude, r.latitude] for r in s.itertuples()], 'spatialReference': {'wkid': 4326}}
    q = fetch(url, {'geometry': json.dumps(pts, separators=(',', ':')), 'geometryType': 'esriGeometryMultipoint',
                    'returnFirstValueOnly': 'true', 'f': 'json'})
    samples_ = sorted(q['samples'], key=lambda x: x['locationId'])
    vals = np.array([float(x['value']) if x.get('value') not in (None, '') else np.nan for x in samples_])
    vals[vals > 100] = np.nan                     # 254/255 = outside area / no data
    f = base(s)
    f['tcd2018_pct'] = vals
    meta = {'accessible': 'yes (EEA ArcGIS ImageServer getSamples, no auth)', 'resolution': '10 m (pixelSizeX 10, Web Mercator)',
            'crs': 'EPSG:3857', 'nodata': '254/255 -> missing', 'licence': 'Copernicus Land Monitoring Service, free and open with attribution',
            'temporal_rule': 'reference year 2018 (imagery 2017-2019): admissible only for t0 >= 2020-01-01; 2012/2015 vintages exist as tiled MapServers',
            'leakage_notes': 'for events 2017-2019 the 2018 product may include the scar', 'n_returned': len(samples_)}
    return f, ['tcd2018_pct'], meta


def gfc(s):
    f = base(s)
    ly, tc = np.full(len(s), np.nan), np.full(len(s), np.nan)
    loss_before, info = np.full(len(s), np.nan), {}
    for t, idx in s.groupby(s.apply(lambda r: f'50N_{10 * math.floor(r.longitude / 10):03d}E', axis=1)).groups.items():
        u = 'https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/Hansen_GFC-2024-v1.12_{}_' + t + '.tif'
        p, patches, info['lossyear'] = sample_raster(u.format('lossyear'), s.loc[idx, 'longitude'], s.loc[idx, 'latitude'], radius_px=2)
        years = s.loc[idx, 'event_date'].str[:4].astype(int).to_numpy() - 2000
        ly[idx] = p
        # share of 5x5 (~150 m) patch with loss in a calendar year strictly before the event year (loss year = event year excluded)
        loss_before[idx] = [np.nanmean((a > 0) & (a < y)) for a, y in zip(patches, years)]
        p2, _, info['treecover2000'] = sample_raster(u.format('treecover2000'), s.loc[idx, 'longitude'], s.loc[idx, 'latitude'])
        tc[idx] = p2
    f['gfc_treecover2000'] = tc
    f['gfc_loss_before_event_year_share150m'] = loss_before
    f['gfc_lossyear_raw'] = ly                      # not a feature: inspected only for same/post-event years
    years = f.event_date.str[:4].astype(int) - 2000
    meta = {'accessible': 'yes (public GeoTIFF on GCS, windowed /vsicurl reads)', 'resolution': f"{info['lossyear']['res']} deg (~30 m)",
            'crs': info['lossyear']['crs'], 'nodata': info['lossyear']['nodata'], 'licence': 'CC BY 4.0 (Hansen/UMD/Google/USGS/NASA)',
            'temporal_rule': 'only loss years strictly < event calendar year; treecover2000 static',
            'leakage_notes': 'loss in the event year or later can be the landslide itself -> excluded',
            'samples_with_loss_in_or_after_event_year': int(((f.gfc_lossyear_raw >= years) & (f.gfc_lossyear_raw > 0)).sum()),
            'raster_info': info}
    return f, ['gfc_treecover2000', 'gfc_loss_before_event_year_share150m'], meta


def soilgrids(s):
    """SoilGrids 2.0 via the ISRIC REST point API (fair use ~5 requests/min); 2017 depth to bedrock by range reads."""
    f = base(s)
    feats, info = [], {}
    props, depths = ('clay', 'sand'), ('0-5cm', '15-30cm', '30-60cm')
    rows = []
    for r in s.itertuples():
        q = fetch('https://rest.isric.org/soilgrids/v2.0/properties/query',
                  {'lon': f'{r.longitude:.6f}', 'lat': f'{r.latitude:.6f}', 'property': list(props), 'depth': list(depths),
                   'value': 'mean'}, min_interval=13)
        rec = {}
        for layer in q['properties']['layers']:
            info[layer['name']] = layer['unit_measure']
            for d in layer['depths']:
                v = d['values']['mean']
                rec[f"sg_{layer['name']}_{d['label']}_pct"] = np.nan if v is None else v / layer['unit_measure']['d_factor']   # mapped g/kg x d_factor -> %
        rows.append(rec)
    vals = pd.DataFrame(rows)
    for c in vals:
        f[c] = vals[c].to_numpy()
        feats.append(c)
    RangeFile.bytes_fetched = 0
    try:
        url = 'https://files.isric.org/soilgrids/former/2017-03-10/data/BDTICM_M_250m_ll.tif'
        p, _, info['BDTICM'] = sample_raster(url, s.longitude, s.latitude)
        f['sg2017_depth_to_bedrock_cm'] = p
        feats.append('sg2017_depth_to_bedrock_cm')
    except Exception as e:  # noqa: BLE001
        info['BDTICM_error'] = repr(e)[:300]
    info['BDTICM_bytes_fetched'] = RangeFile.bytes_fetched
    meta = {'accessible': 'clay/sand yes (ISRIC REST point API); depth-to-bedrock see BDTICM entry',
            'resolution': '250 m (Interrupted Goode Homolosine, ESRI:54052)', 'crs': 'ESRI:54052 (VRT/COG); REST answers in WGS84',
            'nodata': 'null / -32768 -> missing', 'licence': 'CC BY 4.0 ISRIC - World Soil Information',
            'temporal_rule': 'static model output from legacy profiles; no event-specific content',
            'leakage_notes': 'no temporal leakage; 250 m predictions smooth across the 0.75-10 km group', 'source_info': info}
    return f, feats, meta


# ---------------------------------------------------------------- A: OSM roads as of t0 (Overpass attic query)
def osm(s):
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree
    recs, meta_q = [], []
    for gid, grp in s.groupby('event_group_id'):
        t0 = grp.t0_utc.iloc[0]
        pad = 0.012
        bbox = (grp.latitude.min() - pad, grp.longitude.min() - pad, grp.latitude.max() + pad, grp.longitude.max() + pad)
        query = (f'[out:json][timeout:180][date:"{(t0 - pd.Timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}"];'
                 f'way["highway"]({bbox[0]:.5f},{bbox[1]:.5f},{bbox[2]:.5f},{bbox[3]:.5f});out geom;')
        try:
            q = fetch('https://overpass-api.de/api/interpreter', data=query, min_interval=5)
        except RuntimeError:
            q = fetch('https://overpass.kumi.systems/api/interpreter', data=query, min_interval=5)
        if 'remark' in q and 'error' in str(q['remark']).lower():
            raise RuntimeError(f"Overpass remark: {q['remark'][:200]}")
        lines, kinds = [], []
        for el in q.get('elements', []):
            g = el.get('geometry') or []
            if len(g) >= 2:
                xy = [PROJECT.transform(p['lon'], p['lat']) for p in g]
                lines.append(LineString(xy))
                kinds.append(el.get('tags', {}).get('highway'))
        major = [l for l, k in zip(lines, kinds) if k not in ('path', 'footway', 'track', 'steps', 'bridleway', 'cycleway')]
        tree_all, tree_major = STRtree(lines), STRtree(major) if major else None
        for r in grp.itertuples():
            pt = Point(r.x, r.y)
            d_all = pt.distance(lines[tree_all.nearest(pt)]) if lines else np.nan
            d_maj = pt.distance(major[tree_major.nearest(pt)]) if major else np.nan
            buf = pt.buffer(250)
            dens = sum(l.intersection(buf).length for l in (lines[i] for i in tree_all.query(buf))) / (math.pi * 0.25 ** 2) / 1000
            recs.append({'sample_id': r.sample_id, 'osm_dist_any_way_m': d_all, 'osm_dist_road_m': d_maj,
                         'osm_way_density_250m_km_km2': dens})
        meta_q.append({'event_group_id': gid, 'date_filter': query[:80], 'ways': len(lines),
                       'osm_base_timestamp': q.get('osm3s', {}).get('timestamp_osm_base')})
    f = base(s).merge(pd.DataFrame(recs), on='sample_id')
    meta = {'accessible': 'yes (Overpass API attic [date:] query, no auth)', 'resolution': 'vector', 'crs': 'WGS84 -> EPSG:31287',
            'nodata': 'no way in bbox -> NaN', 'licence': 'ODbL 1.0 © OpenStreetMap contributors (share-alike for derived DBs)',
            'temporal_rule': 'OSM database state as of t0 - 1 s (attic data)',
            'leakage_notes': 'state before t0 excludes post-event repair roads; mapping completeness at t0 varies (noise, not leakage)',
            'queries': meta_q}
    return f, ['osm_dist_any_way_m', 'osm_dist_road_m', 'osm_way_density_250m_km_km2'], meta


# ---------------------------------------------------------------- B: daily GeoSphere grids (SPARTACUS / SNOWGRID / WINFORE)
def daily(s):
    v04w.cached_json = lambda url, params, min_interval_s=0, f_param=False: fetch(url, params, min_interval=min_interval_s)
    frames, info = [], {}
    pts = s.copy()
    pts['t0_utc'] = pts.t0_utc.map(lambda t: t.isoformat())
    for resource in v04w.DAILY:
        parts = []
        for day, grp in pts.groupby('event_date'):
            parts.append(v04w.bundle_daily(grp, resource))
        df = pd.concat(parts)
        frames.append(df)
        last = pd.to_datetime(df[f'{resource}_last_day'], utc=True)
        t0 = pd.to_datetime(pts.set_index('sample_id').loc[df.sample_id, 't0_utc'].to_numpy(), utc=True)
        valid_at = last + v04w.DAY_VALID
        info[resource] = {'all_last_days_end_before_t0': bool((valid_at < t0).all()),
                          'max_gap_last_valid_to_t0_h': float(((pd.DatetimeIndex(t0) - pd.DatetimeIndex(valid_at)).total_seconds() / 3600).max()),
                          'min_gap_last_valid_to_t0_h': float(((pd.DatetimeIndex(t0) - pd.DatetimeIndex(valid_at)).total_seconds() / 3600).min()),
                          'max_grid_offset_m': float(df[f'{resource}_offset_m'].max())}
    f = base(s)
    for df in frames:
        f = f.merge(df, on='sample_id', how='left')
    for resource in v04w.DAILY:
        cell = f[f'{resource}_offset_m']
    feats = [c for c in v04w.DAILY_FEATURES if c in f]
    meta = {'accessible': 'yes (GeoSphere Data Hub timeseries API, no auth, 240 req/h)', 'resolution': '1 km daily',
            'crs': 'EPSG:3416 grid (API returns WGS84 cell centres)', 'nodata': 'null -> NaN',
            'licence': 'CC BY 4.0 © GeoSphere Austria',
            'temporal_rule': 'day D (07 CET D -> 07 CET D+1) treated as valid at D+1 06:00 UTC; used only if < t0 (t0 = local midnight)',
            'leakage_notes': 'last used day ends 16-18 h before t0; event-day and the preceding evening are never used',
            'boundary_checks': info}
    return f, feats, meta


# ---------------------------------------------------------------- C: derived from cached INCA hourly (no download)
def inca_index():
    idx = {}
    for meta in (DATA_ROOT / 'data/raw/http').glob('*.meta.json'):
        m = json.loads(meta.read_text(encoding='utf-8'))
        if 'inca-v1-1h-1km' in m['url'] and 'lat_lon' in m['url']:
            idx[meta.name.replace('.meta.json', '')] = m['url']
    return idx


def inca_derived(s, dev):
    from preslide.weather import window_mask
    from urllib.parse import parse_qs, urlsplit
    index = inca_index()
    by_coords = {}
    for key, url in index.items():
        q = parse_qs(urlsplit(url).query)
        by_coords[frozenset(q['lat_lon'])] = key
    recs, missing = [], []
    for gid, grp in dev.groupby('event_group_id'):
        coords = frozenset(f'{r.latitude:.8f},{r.longitude:.8f}' for r in grp.itertuples())
        key = next((k for c, k in by_coords.items() if coords <= c), None)
        if key is None:
            missing.append(gid)
            continue
        resp = json.loads((DATA_ROOT / f'data/raw/http/{key}.json').read_text(encoding='utf-8'))
        times = pd.to_datetime(resp['timestamps'], utc=True)
        event_date = grp.event_date.iloc[0]
        keep = window_mask(times, event_date, 60, 1)         # identical admissibility to the frozen baseline
        cells = {tuple(np.round(PROJECT.transform(*p['geometry']['coordinates']), 1)): p for p in resp['features']}
        cxy = np.array(list(cells))
        for r in grp.itertuples():
            i = int(np.argmin(np.linalg.norm(cxy - [r.x, r.y], axis=1)))
            p = cells[tuple(cxy[i])]['properties']['parameters']
            rain = np.asarray(p['RR']['data'], float)[keep]
            temp = np.asarray(p['T2M']['data'], float)[keep]
            t = times[keep]
            local_day = t.tz_convert('Europe/Vienna').strftime('%Y-%m-%d')
            day = pd.DataFrame({'d': local_day, 'r': rain, 't': temp}).groupby('d').agg(r=('r', 'sum'), tmin=('t', 'min'),
                                                                                       tmax=('t', 'max'), n=('r', 'size'))
            day = day[day.n >= 20]                              # partial boundary days excluded
            k = 0.9
            api = float(sum(v * k ** j for j, v in enumerate(day.r.to_numpy()[::-1])))  # most recent day weight 1
            roll24 = pd.Series(rain).rolling(24).sum().max()
            roll72 = pd.Series(rain).rolling(72).sum().max()
            ft = ((day.tmin < 0) & (day.tmax > 0)).to_numpy()
            recs.append({'event_group_id': gid, 'sample_id': r.sample_id, 'event_date': event_date,
                         'inca_api_k0p9_60d': api, 'inca_max_24h_rain_60d': float(roll24), 'inca_max_72h_rain_60d': float(roll72),
                         'inca_frost_thaw_days_30d': int(ft[-30:].sum()), 'inca_frost_thaw_days_60d': int(ft.sum()),
                         'inca_wet_days_ge1mm_30d': int((day.r.to_numpy()[-30:] >= 1).sum()),
                         'inca_last_hour_used': t.max().isoformat(), 'inca_hours_used': int(keep.sum())})
    f = pd.DataFrame(recs)
    t0 = f.event_date.map(lambda x: pd.Timestamp(x, tz='Europe/Vienna').tz_convert('UTC'))
    assert (pd.to_datetime(f.inca_last_hour_used, utc=True) + pd.Timedelta(hours=1) < t0).all()
    feats = ['inca_api_k0p9_60d', 'inca_max_24h_rain_60d', 'inca_max_72h_rain_60d', 'inca_frost_thaw_days_30d',
             'inca_frost_thaw_days_60d', 'inca_wet_days_ge1mm_30d']
    meta = {'accessible': 'yes (local cached baseline INCA responses, no download)', 'resolution': '1 km hourly',
            'crs': 'EPSG:31287 grid', 'nodata': 'baseline already excluded groups with missing/negative values',
            'licence': 'CC BY 4.0 © GeoSphere Austria',
            'temporal_rule': 'frozen baseline admissibility: T +/- 1 h within [t0-60d, t0)', 'leakage_notes': 'asserted: last hour + 1 h < t0 for all samples',
            'groups': int(f.event_group_id.nunique()), 'groups_without_cache_match': missing,
            'scope': 'all 45 development groups (train+validation), cache only; 5-event subset reported separately'}
    return f, feats, meta


def main():
    s, dev = samples()
    sel = s[s.label == 1][['event_group_id', 'event_date', 'state', 'partition', 'dependence_cluster', 'elevation', 'slope']]
    sel.to_csv(REPORT / 'selected_events.csv', index=False)
    print(sel.to_string())
    funcs = {'terrain30': terrain30, 'geology': geology, 'soilgrids': soilgrids, 'worldcover': worldcover, 'tcd': tcd,
             'gfc': gfc, 'osm': osm, 'daily': daily}
    status = {}
    for name in args.only:
        print(f'\n=== {name}')
        try:
            if name == 'inca_derived':
                f, feats, meta = inca_derived(s, dev)
                summarize('inca_derived_dev45', f, feats, meta)
                summarize('inca_derived', f[f.event_group_id.isin(s.event_group_id)], feats, meta)
            else:
                RangeFile.bytes_fetched = 0
                f, feats, meta = funcs[name](s)
                meta['range_bytes_fetched'] = RangeFile.bytes_fetched
                summarize(name, f, feats, meta)
            status[name] = 'ok'
        except Exception as e:  # noqa: BLE001
            status[name] = f'failed: {e!r}'[:500]
            print(status[name])
    prev = REPORT / 'run_status.json'
    old = json.loads(prev.read_text()) if prev.exists() else {}
    old.update(status)
    prev.write_text(json.dumps(old, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
