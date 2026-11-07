"""Export real project data for the finale film's motion graphics (read-only on data/).

Usage: <main checkout>/.venv/Scripts/python scripts/finale_video/export_data.py
Writes deliverables/finale_video/mg/data.js (gitignored). Nothing is trained, scored or changed.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WORKTREE = Path(__file__).resolve().parents[2]
MAIN = Path('C:/Users/mario/Documents/HomeProjects/PreSlide')
DATA = MAIN / 'data'
sys.path.insert(0, str(MAIN))
OUT = WORKTREE / 'deliverables/finale_video/mg/data.js'

V04_RUN = DATA / 'v04/run_c6d67a854ba7/dataset.parquet'
TWIN_GROUP = '1310420_001'  # Tamsweg 05.07.2023, same example as the first film


def hgt_tile(lat0: int, lon0: int) -> np.ndarray:
    z = np.fromfile(DATA / f'raw/terrain/N{lat0:02d}E{lon0:03d}.hgt', dtype='>i2').reshape(3601, 3601).astype(float)
    z[z < -1000] = np.nan
    return z


def dem_window(lon_min: float, lon_max: float, lat_min: float, lat_max: float) -> tuple[np.ndarray, float, float]:
    """1 arc-second DEM window; row 0 = north. Returns grid and its north-west corner."""
    lat_tiles = range(math.floor(lat_min), math.floor(lat_max - 1e-9) + 1)
    lon_tiles = range(math.floor(lon_min), math.floor(lon_max - 1e-9) + 1)
    rows = [np.hstack([hgt_tile(la, lo)[:-1, :-1] for lo in lon_tiles]) for la in sorted(lat_tiles, reverse=True)]
    mosaic = np.vstack(rows)
    north, west = max(lat_tiles) + 1, min(lon_tiles)
    r0, r1 = round((north - lat_max) * 3600), round((north - lat_min) * 3600)
    c0, c1 = round((lon_min - west) * 3600), round((lon_max - west) * 3600)
    return mosaic[r0:r1, c0:c1], west + c0 / 3600, north - r0 / 3600


def grid(z: np.ndarray, rows: int, cols: int) -> list[list[int]]:
    """Block-mean downsample to rows x cols, heights rounded to metres."""
    z = np.nan_to_num(z, nan=float(np.nanmean(z)))
    r = np.linspace(0, z.shape[0], rows + 1).astype(int)
    c = np.linspace(0, z.shape[1], cols + 1).astype(int)
    return [[round(float(z[r[i]:r[i + 1], c[j]:c[j + 1]].mean())) for j in range(cols)] for i in range(rows)]


def main() -> None:
    df = pd.read_parquet(V04_RUN)
    positives = df[df.label == 1]

    # Inventory: all georeferenced entries, as in the first film's fact check (25 609 entries).
    raw = json.loads((DATA / 'raw/geosphere_natural_hazards.json').read_text(encoding='utf-8'))
    inv = np.array([(f['geometry']['x'], f['geometry']['y']) for f in raw['features']
                    if f.get('geometry') and 'x' in f['geometry']])
    print('inventory entries', len(raw['features']), 'with geometry', len(inv))
    print('v04 positives', len(positives), 'columns', list(df.columns)[:25])

    from preslide.matching import austria_boundary
    geom = austria_boundary()
    poly = max(geom.geoms, key=lambda g: g.area) if hasattr(geom, 'geoms') else geom
    ring = np.array(poly.exterior.coords)[::max(1, len(poly.exterior.coords) // 900)]

    # Twin group: real positive, its five stored controls and the real candidate pool.
    grp = df[df.event_group_id == TWIN_GROUP]
    p = grp[grp.label == 1].iloc[0]
    lon0, lat0 = float(p.longitude), float(p.latitude)
    half_x_m, half_y_m = 14000.0, 14000.0
    dlon = half_x_m / (111320 * math.cos(math.radians(lat0)))
    dlat = half_y_m / 110574
    z, west, north = dem_window(lon0 - dlon, lon0 + dlon, lat0 - dlat, lat0 + dlat)
    pool = pd.read_parquet(DATA / f'v04/cache/control_pools/{TWIN_GROUP}.parquet')
    print('pool columns', list(pool.columns))

    def xy(lon, lat):
        return ((np.asarray(lon) - lon0) * 111320 * math.cos(math.radians(lat0)), (np.asarray(lat) - lat0) * 110574)

    cx, cy = xy(pool.longitude, pool.latitude)
    keep_cols = {c: pool[c].round(1).tolist() for c in
                 ('slope_difference_deg', 'elevation_difference_m', 'aspect_difference_deg') if c in pool}
    ctl = grp[grp.label == 0]
    tx, ty = xy(ctl.longitude, ctl.latitude)
    twin = {
        'date': str(p.get('event_date', p.get('t0', '')))[:10],
        'half_m': half_x_m,
        'grid': grid(z, 170, 170),
        'pool': {'x': np.round(cx).tolist(), 'y': np.round(cy).tolist(), **keep_cols},
        'controls': {'x': np.round(tx).tolist(), 'y': np.round(ty).tolist()},
    }

    # Stanz demo: real road segments and documented events (wirkungskette_v01 cache, OSM today).
    demo = DATA / 'wirkungskette_v01/demo_r10000'
    infra = pd.read_parquet(demo / 'infrastructure.parquet')
    from shapely import wkb
    from shapely.geometry import box
    # EPSG:31287 metres; window around the demo centre (47.44533 N, 15.49683 E) from the terrain window.
    from pyproj import Transformer
    cx0, cy0 = Transformer.from_crs(4326, 31287, always_xy=True).transform(15.49683, 47.44533)
    half = 7000.0
    win = box(cx0 - half, cy0 - half, cx0 + half, cy0 + half)
    roads = []
    for g in infra[infra.typ == 'strasse'].geometry_wkb:
        geom2 = wkb.loads(g)
        if geom2.intersects(win) and geom2.geom_type == 'LineString':
            roads.append(np.round(np.array(geom2.coords)[:, :2] - [cx0, cy0]).astype(int).ravel().tolist())
    stanz = positives[positives.event_group_id.str.len() > 0]
    sx, sy = stanz.x.to_numpy() - cx0, stanz.y.to_numpy() - cy0
    inside = (np.abs(sx) < half) & (np.abs(sy) < half)
    print('roads', len(roads), 'v04 positives in window', int(inside.sum()))

    # Real daily INCA rain of the Tamsweg positive for the 60 days before t0 (no data after t0 exists in this cache).
    weather = pd.read_parquet(next((V04_RUN.parent / 'weather').glob('history_2023-07-05_*.parquet')))
    rain = weather[weather.sample_id == f'{TWIN_GROUP}_positive'].sort_values('date')
    print('rain days', len(rain), rain.date.iloc[0], rain.date.iloc[-1], 'sum mm', round(rain.rain_mm.sum(), 1))

    payload = {
        'rain': {'dates': [str(d)[:10] for d in rain.date], 'mm': rain.rain_mm.round(1).tolist()},
        'roads': roads,
        'roads_half_m': half,
        'stanz_events': np.round(np.c_[sx[inside], sy[inside]]).ravel().tolist(),
        'austria': np.round(ring, 3).tolist(),
        'inventory': np.round(inv, 3).ravel().tolist(),
        'positives': np.round(positives[['longitude', 'latitude']].to_numpy(), 3).ravel().tolist(),
        'twin': twin,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('window.DATA=' + json.dumps(payload, separators=(',', ':')) + ';', encoding='utf-8')
    print('wrote', OUT, round(OUT.stat().st_size / 1e6, 1), 'MB')


if __name__ == '__main__':
    main()
