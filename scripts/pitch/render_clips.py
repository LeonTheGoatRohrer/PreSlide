"""Render the data animations for the Talwacht pitch film (1920x1080, 25 fps, H.264).

Every point, polygon and number comes from stored project artefacts; the sources are listed in
reports/weiterentwicklung_2026-10-18/VIDEO_PITCH_SKRIPT.md (Faktencheck). Nothing here trains, scores or
changes a frozen artefact. Output goes to deliverables/pitch/clips/ (gitignored).

Usage (main checkout or a worktree with junctions to data/):
    .venv/Scripts/python scripts/pitch/render_clips.py                 # all clips
    .venv/Scripts/python scripts/pitch/render_clips.py --only a4_ergebnis
    .venv/Scripts/python scripts/pitch/render_clips.py --still 3.5     # one PNG per clip at t = 3.5 s
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LightSource, to_rgba  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'deliverables/pitch/clips'
W, H, FPS = 1920, 1080, 25

# ---------- look ----------
BG = '#0E1822'
INK = '#E9EEF1'
DIM = '#AEBBC5'
FAINT = '#22313F'
ORANGE = '#E9973A'
CYAN = '#8DB6C7'
TITLE_FONT = 'Bahnschrift'
TEXT_FONT = 'Segoe UI'
LIGHT_FONT = 'Segoe UI Light'
MONO_FONT = 'Cascadia Mono'

# ---------- facts (from reports, see Faktencheck) ----------
V04_COMBINED, V04_CI = 0.751, (0.633, 0.866)
V04_STATIC, V04_TEMPORAL, V04_NULL95 = 0.702, 0.604, 0.629
V04_INCREMENT = (0.049, -0.003, 0.108)
V09_STATIC, V09_COMBINED, V09_INCREMENT = 0.770, 0.752, (-0.019, -0.121, 0.082)
EXTREM_SHARE, EXTREM_CI = 24.6, (11.8, 38.2)
V07_DISTANCE = 0.928
GASTEIN_EVENT = '1310133_001'
TWIN_GROUP = '1310420_001'
V04_RUN = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'


def de(x, digits=2):
    return f'{x:.{digits}f}'.replace('.', ',')


def de_int(n):
    return f'{n:,}'.replace(',', ' ')


# ---------- timing helpers ----------
def clamp(x):
    return max(0.0, min(1.0, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def seg(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def fade(t, a, b, c=None, d=None):
    v = seg(t, a, b)
    if c is not None:
        v *= 1 - seg(t, c, d)
    return v


# ---------- drawing helpers ----------
def canvas(fig):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')
    ax.patch.set_alpha(0)
    return ax


def txt(ax, x, y, s, size=28, color=INK, alpha=1.0, font=TEXT_FONT, ha='left', va='baseline', weight='normal', **kw):
    if alpha <= 0.002:
        return None
    return ax.text(x, y, s, fontsize=size, color=color, alpha=clamp(alpha), family=font, ha=ha, va=va, weight=weight, **kw)


def spaced(ax, x, y, s, size, spacing, color=INK, alpha=1.0, font=TITLE_FONT, ha='center'):
    """Letter-spaced title; spacing in em."""
    if alpha <= 0.002:
        return
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    fp = FontProperties(family=font)
    px = size * 100 / 72
    widths = []
    for ch in s:
        w = TextPath((0, 0), ch, size=px, prop=fp).get_extents().width if ch != ' ' else px * 0.3
        widths.append(w + px * 0.06)
    total = sum(widths) + spacing * px * (len(s) - 1)
    cx = x - total / 2 if ha == 'center' else x
    for ch, w in zip(s, widths):
        ax.text(cx, y, ch, fontsize=size, color=color, alpha=clamp(alpha), family=font, ha='left', va='baseline')
        cx += w + spacing * px


def chapter(ax, label, t, t_out=None):
    a = fade(t, 0.2, 0.9) * (1 - seg(t, t_out, t_out + 0.6) if t_out else 1)
    txt(ax, 90, 985, label, size=17, color=CYAN, alpha=a, font=MONO_FONT)
    ax.plot([90, 90 + 260 * a], [968, 968], color=CYAN, lw=1, alpha=a * 0.6)


def footnote(ax, s, alpha=1.0, y=52):
    txt(ax, 90, y, s, size=13, color=DIM, alpha=alpha, font=TEXT_FONT)


def vignette(ax, strength=0.55):
    yy, xx = np.mgrid[-1:1:108j, -1:1:192j]
    r = np.clip(np.hypot(xx * 0.9, yy) - 0.55, 0, None)
    a = np.clip(r * strength * 1.6, 0, strength)
    img = np.zeros((108, 192, 4))
    img[..., 3] = a
    ax.imshow(img, extent=(0, W, 0, H), origin='lower', zorder=50, interpolation='bilinear')


# ---------- data ----------
@lru_cache(maxsize=None)
def hgt_tile(lat0, lon0):
    path = ROOT / f'data/raw/terrain/N{lat0:02d}E{lon0:03d}.hgt'
    z = np.fromfile(path, dtype='>i2').reshape(3601, 3601).astype(float)
    z[z < -1000] = np.nan
    return z


def dem_window(lon_min, lon_max, lat_min, lat_max, stride=1):
    """DEM (1 arc-second Skadi/SRTM tiles from the read-only cache) for a lon/lat window; row 0 = north."""
    lat_tiles = range(math.floor(lat_min), math.floor(lat_max - 1e-9) + 1)
    lon_tiles = range(math.floor(lon_min), math.floor(lon_max - 1e-9) + 1)
    rows = []
    for la in sorted(lat_tiles, reverse=True):
        rows.append(np.hstack([hgt_tile(la, lo)[:-1, :-1] for lo in lon_tiles]))
    mosaic = np.vstack(rows)
    north = max(lat_tiles) + 1
    west = min(lon_tiles)
    r0 = int(round((north - lat_max) * 3600))
    r1 = int(round((north - lat_min) * 3600))
    c0 = int(round((lon_min - west) * 3600))
    c1 = int(round((lon_max - west) * 3600))
    z = mosaic[r0:r1:stride, c0:c1:stride]
    lats = north - (np.arange(r0, r1, stride) / 3600)
    lons = west + (np.arange(c0, c1, stride) / 3600)
    return z, lons, lats


def metres(lon, lat, lon0, lat0):
    """Local equirectangular metres around (lon0, lat0); adequate for display over a few km."""
    return (np.asarray(lon) - lon0) * 111320 * math.cos(math.radians(lat0)), (np.asarray(lat) - lat0) * 110574


def hillshade(z, lat0, stride=1, exag=1.6):
    cell = 30.87 * stride
    return LightSource(azdeg=315, altdeg=38).hillshade(np.nan_to_num(z, nan=np.nanmean(z)), vert_exag=exag,
                                                        dx=cell * math.cos(math.radians(lat0)), dy=cell)


@lru_cache(maxsize=1)
def inventory():
    d = json.loads((ROOT / 'data/raw/geosphere_natural_hazards.json').read_text(encoding='utf-8'))
    rows = [(f['attributes'].get('nameOfEvent'), f['geometry']['x'], f['geometry']['y'], f['attributes'].get('Prozessgruppe'))
            for f in d['features'] if f.get('geometry') and 'x' in f['geometry']]
    return pd.DataFrame(rows, columns=['event_id', 'lon', 'lat', 'process_group'])


@lru_cache(maxsize=1)
def v04():
    return pd.read_parquet(V04_RUN)


# ---------- renderer ----------
def ffmpeg():
    exe = shutil.which('ffmpeg')
    if not exe:
        raise RuntimeError('ffmpeg not found on PATH')
    return exe


def render(name, duration, factory, still=None):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    frame = factory(fig)
    OUT.mkdir(parents=True, exist_ok=True)
    if still is not None:
        frame(min(still, duration - 1 / FPS))
        fig.savefig(OUT / f'{name}.png', dpi=100, facecolor=BG)
        plt.close(fig)
        return
    cmd = [ffmpeg(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
           str(OUT / f'{name}.mp4')]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(round(duration * FPS))):
        frame(i / FPS)
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
        if buf.shape != (H, W, 4):
            raise RuntimeError(f'unexpected frame size {buf.shape}')
        proc.stdin.write(buf.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f'ffmpeg failed for {name}')
    plt.close(fig)


def flat(draw):
    """Factory for 2D clips that redraw everything on every frame."""
    def factory(fig):
        def frame(t):
            fig.clf()
            fig.patch.set_facecolor(BG)
            draw(canvas(fig), t)
        return frame
    return factory


# =====================================================================
# AKT I
# =====================================================================
def a1_titel(ax, t):
    a = fade(t, 1.0, 2.6, 6.2, 7.0)
    spacing = 0.9 - 0.45 * seg(t, 1.0, 6.5)
    spaced(ax, W / 2, 545, 'TALWACHT', 92, spacing, color=INK, alpha=a)
    txt(ax, W / 2, 455, 'Was die Vorgeschichte eines Hangs verrät. Und was nicht.', size=26, color=DIM,
        alpha=fade(t, 3.2, 4.4, 6.2, 7.0), font=LIGHT_FONT, ha='center')
    ax.plot([W / 2 - 160 * a, W / 2 + 160 * a], [510, 510], color=ORANGE, lw=1.4, alpha=a * 0.9)


def a1_terminal(ax, t):
    line1 = '18.11.2019  ·  Bad Hofgastein  ·  Hangmure'
    n = int(len(line1) * clamp((t - 0.4) / 2.2))
    cursor = '█' if (t * 2.2) % 1 < 0.55 else ' '
    a = 1 - seg(t, 4.4, 5.0)
    txt(ax, 160, 600, line1[:n] + cursor, size=40, color=INK, alpha=a, font=MONO_FONT)
    txt(ax, 160, 548, f'GeoSphere Austria · Naturgefahren-Inventar · ID {GASTEIN_EVENT}', size=17, color=DIM,
        alpha=fade(t, 2.8, 3.4) * a, font=MONO_FONT)


def a1_ort(ax, t):
    a = fade(t, 0.3, 1.2, 4.0, 4.8)
    ax.plot([120, 120], [150, 210], color=ORANGE, lw=2, alpha=a)
    spaced(ax, 145, 185, 'GASTEINERTAL · SALZBURG', 24, 0.35, color=INK, alpha=a, font=TITLE_FONT, ha='left')
    txt(ax, 145, 155, '47,1° N · 13,1° O', size=15, color=DIM, alpha=a, font=MONO_FONT)


# =====================================================================
# AKT III – 01 DATEN: layers over the real Gastein terrain (3D)
# =====================================================================
GASTEIN_CENTRE = (13.11, 47.11)
LC_COLORS = {'lc_forest': '#2f6b4f', 'lc_grass_shrub': '#9fb86a', 'lc_agriculture': '#d8c27a',
             'lc_open_bare': '#b8b1a6', 'lc_artificial_water_other': '#d0603f'}
LC_NAMES = {'lc_forest': 'Wald', 'lc_grass_shrub': 'Grünland/Gebüsch', 'lc_agriculture': 'Landwirtschaft',
            'lc_open_bare': 'Fels/offen', 'lc_artificial_water_other': 'Siedlung/Wasser/Sonstiges'}
GEO_COLORS = {'geo_carbonate': '#86aed6', 'geo_clastic_rock': '#c9a26b', 'geo_unconsolidated': '#e3d6a0',
              'geo_low_grade_metamorphic': '#9c7fc0', 'geo_crystalline_other': '#c98585'}
GEO_NAMES = {'geo_carbonate': 'Karbonat', 'geo_clastic_rock': 'klastisches Gestein', 'geo_unconsolidated': 'Lockergestein',
             'geo_low_grade_metamorphic': 'schwach metamorph', 'geo_crystalline_other': 'Kristallin/Sonstiges'}


def gastein_layers():
    from preslide.hangmap import build
    lon0, lat0 = GASTEIN_CENTRE
    half_m = 3000
    dlon = half_m / (111320 * math.cos(math.radians(lat0)))
    dlat = half_m / 110574
    z, lons, lats = dem_window(lon0 - dlon, lon0 + dlon, lat0 - dlat, lat0 + dlat, stride=2)
    LON, LAT = np.meshgrid(lons, lats)
    X, Y = metres(LON, LAT, lon0, lat0)
    hs = hillshade(z, lat0, stride=2, exag=1.3)
    gy, gx = np.gradient(z, 61.74, 61.74 * math.cos(math.radians(lat0)))
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    inside = np.hypot(X, Y) <= 2000
    cfg = json.loads((ROOT / 'config/v04.json').read_text(encoding='utf-8'))['features']
    lc = np.full(z.shape, None, dtype=object)
    geo = np.full(z.shape, None, dtype=object)
    pts = pd.DataFrame({'lon': LON[inside], 'lat': LAT[inside]})
    lc[inside] = build.land_cover_cells(pts.lon, pts.lat, cfg['land_cover']['classes'], 'CLC2018')['land_cover_class'].to_numpy()
    geo[inside] = build.geology_cells(pts.lon, pts.lat, cfg['geology']['classes'])['geology_class'].to_numpy()
    return dict(X=X, Y=Y, Z=z, hs=hs, slope=slope, inside=inside, lc=lc, geo=geo)


def a3_ebenen_factory(fig):
    d = gastein_layers()
    hs = d['hs'][..., None]
    base = np.concatenate([0.10 + 0.80 * hs * np.array([0.78, 0.84, 0.90]), np.ones_like(hs)], axis=-1)
    dark = np.concatenate([0.05 + 0.35 * hs * np.array([0.78, 0.84, 0.90]), np.ones_like(hs)], axis=-1)
    sl = np.clip(d['slope'] / 45, 0, 1)[..., None]
    slope_rgb = (1 - sl) * np.array(to_rgba('#13283a')[:3]) + sl * np.array(to_rgba(CYAN)[:3])
    slope_col = np.concatenate([slope_rgb * (0.55 + 0.45 * hs), np.ones_like(hs)], axis=-1)

    def classes(arr, colors):
        out = dark.copy()
        for k, c in colors.items():
            m = arr == k
            out[m, :3] = np.array(to_rgba(c)[:3]) * (0.55 + 0.45 * d['hs'][m])[:, None]
        return out

    lc_col = classes(d['lc'], LC_COLORS)
    geo_col = classes(d['geo'], GEO_COLORS)
    layers = [base, slope_col, lc_col, geo_col, dark]
    starts = [0.0, 4.5, 9.0, 13.5, 18.0]
    names = ['GELÄNDE · 30 m', 'NEIGUNG', 'LANDBEDECKUNG · CORINE 2018', 'GEOLOGIE · 1 : 500 000', 'NIEDERSCHLAG · 1 km · STÜNDLICH']

    ax3 = fig.add_axes([-0.08, -0.12, 1.16, 1.3], projection='3d')
    ax3.set_axis_off()
    ax3.set_facecolor(BG)
    Z = d['Z']
    zmin, zmax = np.nanmin(Z), np.nanmax(Z)
    ax3.set_box_aspect((1, 1, (zmax - zmin) * 1.25 / 6000), zoom=1.15)
    surf = ax3.plot_surface(d['X'], d['Y'], Z, facecolors=base, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    # 1 km precipitation grid draped on the terrain (structure of the INCA raster, no values shown)
    grid_lines = []
    for k in range(-3, 4):
        for axis in (0, 1):
            if axis == 0:
                j = np.argmin(np.abs(d['X'][0] - k * 1000))
                xs, ys, zs = d['X'][:, j], d['Y'][:, j], Z[:, j]
            else:
                i = np.argmin(np.abs(d['Y'][:, 0] - k * 1000))
                xs, ys, zs = d['X'][i], d['Y'][i], Z[i]
            (ln,) = ax3.plot(xs, ys, zs + 25, color=CYAN, lw=1.1, alpha=0.0)
            grid_lines.append(ln)
    ov = fig.add_axes([0, 0, 1, 1])
    used_lc = [k for k in LC_COLORS if (d['lc'] == k).any()]
    used_geo = [k for k in GEO_COLORS if (d['geo'] == k).any()]

    def frame(t):
        k = max(i for i, s in enumerate(starts) if t >= s)
        if k > 0:
            a = seg(t, starts[k], starts[k] + 1.2)
            col = (1 - a) * layers[k - 1] + a * layers[k]
        else:
            col = layers[0]
        surf.set_facecolor(col[:-1, :-1].reshape(-1, 4))
        for ln in grid_lines:
            ln.set_alpha(0.85 * seg(t, 18.4, 19.8))
        ax3.view_init(elev=38 - 6 * ease(t / 24), azim=-110 + 55 * (t / 24))
        ov.cla()
        ov.set_xlim(0, W)
        ov.set_ylim(0, H)
        ov.axis('off')
        ov.patch.set_alpha(0)
        chapter(ov, '01  DATEN', t)
        for i, nm in enumerate(names):
            on = seg(t, starts[i], starts[i] + 0.8)
            y = 820 - i * 46
            ov.add_patch(Rectangle((1420, y - 6), 26, 26, facecolor=CYAN if i == k else FAINT, alpha=0.25 + 0.75 * on, lw=0))
            txt(ov, 1462, y, nm, size=16, color=INK if i == k else DIM, alpha=0.25 + 0.75 * on, font=MONO_FONT)
        sub = {2: ', '.join(LC_NAMES[c] for c in used_lc), 3: ', '.join(GEO_NAMES[c] for c in used_geo),
               4: 'Merkmale nur aus  [t₀ − 60 Tage, t₀)'}.get(k, '')
        la = fade(t, starts[k] + 0.4, starts[k] + 1.2)
        txt(ov, 90, 150, names[k], size=34, color=INK, alpha=la, font=TITLE_FONT)
        txt(ov, 90, 108, sub, size=17, color=DIM, alpha=la, font=TEXT_FONT)
        if k in (2, 3):
            txt(ov, 90, 78, 'im 2-km-Gebiet der Hangkarte', size=13, color=DIM, alpha=la * 0.8)
        if k == 4:
            days = int(round(60 * (1 - seg(t, 19.5, 23.0))))
            txt(ov, 1420, 470, f't₀ − {days:2d} Tage', size=30, color=CYAN, alpha=fade(t, 19.0, 19.6), font=MONO_FONT)
        footnote(ov, 'Gasteinertal · Gelände: Skadi/SRTM 1″ · CORINE CLC2018 (Copernicus) · Geologie GeoSphere Austria · Raster: INCA (GeoSphere)', alpha=0.9)
        vignette(ov, 0.5)
    return frame


# =====================================================================
# AKT III – 02 FILTER: Austria, 25 609 entries → 423 events
# =====================================================================
def a3_filter_factory(fig):
    from preslide.matching import austria_boundary
    inv = inventory()
    pos = v04()[lambda x: x.label == 1]
    k = math.cos(math.radians(47.6))
    geom = austria_boundary()
    polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
    x0, x1, y0, y1 = 9.45 * k, 17.25 * k, 46.3, 49.1
    sx = 1700 / (x1 - x0)
    ox, oy = 110, 140

    def P(lon, lat):
        return ox + (np.asarray(lon) * k - x0) * sx, oy + (np.asarray(lat) - y0) * sx

    rng = np.random.default_rng(7)
    ix, iy = P(inv.lon, inv.lat)
    appear = 0.6 + 3.8 * rng.random(len(inv))
    px, py = P(pos.longitude, pos.latitude)
    n_total, n_pos = len(inv), len(pos)
    outlines = [P(*np.asarray(p.exterior.coords).T) for p in polys]
    scan_a, scan_b = 6.0, 10.5
    xmin, xmax = ix.min() - 10, ix.max() + 10

    def frame(t):
        fig.clf()
        fig.patch.set_facecolor(BG)
        ax = canvas(fig)
        chapter(ax, '02  FILTER', t)
        for ox_, oy_ in outlines:
            ax.plot(ox_, oy_, color=DIM, lw=1.0, alpha=0.5 * fade(t, 0, 0.8))
        scan = xmin + (xmax - xmin) * seg(t, scan_a, scan_b)
        shown = appear <= t
        if t < scan_a:
            ax.scatter(ix[shown], iy[shown], s=2.2, c=INK, alpha=0.55, lw=0)
            count = int(shown.sum())
        else:
            left = ix < scan
            ax.scatter(ix[~left], iy[~left], s=2.2, c=INK, alpha=0.55, lw=0)
            ax.scatter(ix[left], iy[left], s=2.0, c=DIM, alpha=0.08, lw=0)
            pl = px < scan
            ax.scatter(px[pl], py[pl], s=60, c=ORANGE, alpha=0.18, lw=0)
            ax.scatter(px[pl], py[pl], s=9, c=ORANGE, alpha=0.95, lw=0)
            ax.plot([scan, scan], [oy - 30, oy + (y1 - y0) * sx + 10], color=CYAN, lw=1.5, alpha=0.9 * (1 - seg(t, scan_b, scan_b + 0.5)))
            count = int((~left).sum() + pl.sum())
        if t >= scan_b:
            count = n_pos
        txt(ax, W - 110, 960, de_int(count), size=60, color=ORANGE if t >= scan_b else INK, font=MONO_FONT, ha='right',
            alpha=fade(t, 0.4, 1.0))
        lab = 'Einträge im Naturgefahren-Inventar' if t < scan_a else ('Prüfung: Datum · Prozess · Lage' if t < scan_b else 'vollständige Ereignisse mit je 5 Zwillingen')
        txt(ax, W - 110, 915, lab, size=18, color=DIM, ha='right', alpha=fade(t, 0.6, 1.2))
        footnote(ax, 'GeoSphere Austria, Naturgefahren-Inventar (Abruf 14.10.2026) · Grenze: EuroGeographics/GISCO · 423 Ereignisgruppen der Studie V0.4')
        vignette(ax, 0.4)
    return frame


# =====================================================================
# AKT III – 02 FILTER: Gastein entries go dark
# =====================================================================
def a3_gastein_factory(fig):
    lon_min, lon_max, lat_min, lat_max = 13.00, 13.26, 47.02, 47.25
    z, lons, lats = dem_window(lon_min, lon_max, lat_min, lat_max, stride=1)
    lat0 = (lat_min + lat_max) / 2
    hs = hillshade(z, lat0, exag=1.4)
    inv = inventory()
    win = inv[(inv.lon.between(lon_min, lon_max)) & (inv.lat.between(lat_min, lat_max))].reset_index(drop=True)
    in_dataset = set(v04().event_group_id.str[:11]) | set(pd.read_parquet(ROOT / 'data/v05/run_5b86b6475ecb/dataset.parquet').event_group_id.str[:11])
    passed = win.event_id.isin(in_dataset)
    if passed.any():
        raise RuntimeError('A Gastein entry is in the dataset; the film text would be wrong')
    if GASTEIN_EVENT not in set(win.event_id):
        raise RuntimeError('Gastein example event missing from the window')
    ext_w = (lon_max - lon_min) * 111320 * math.cos(math.radians(lat0))
    ext_h = (lat_max - lat_min) * 110574
    mh = 900
    mw = mh * ext_w / ext_h
    mx, my = 140, 90

    def P(lon, lat):
        return mx + (np.asarray(lon) - lon_min) / (lon_max - lon_min) * mw, my + (np.asarray(lat) - lat_min) / (lat_max - lat_min) * mh

    wx, wy = P(win.lon, win.lat)
    rng = np.random.default_rng(3)
    hero = int(np.flatnonzero(win.event_id == GASTEIN_EVENT)[0])
    order = rng.permutation([i for i in range(len(win)) if i != hero])
    off = np.empty(len(win))
    off[order] = np.linspace(3.2, 7.6, len(order))
    off[hero] = 8.4
    towns = [('Bad Hofgastein', 13.1006, 47.1708), ('Bad Gastein', 13.1336, 47.1153), ('Dorfgastein', 13.1342, 47.2417)]
    img = np.dstack([0.06 + 0.6 * hs * c for c in (0.78, 0.84, 0.90)])

    def frame(t):
        fig.clf()
        fig.patch.set_facecolor(BG)
        ax = canvas(fig)
        ax.imshow(img, extent=(mx, mx + mw, my, my + mh), origin='upper', alpha=fade(t, 0, 1.0), interpolation='bilinear')
        chapter(ax, '02  FILTER', t)
        for name, lo, la in towns:
            tx, ty = P(lo, la)
            ax.scatter([tx], [ty], s=10, c=INK, alpha=0.6 * fade(t, 0.5, 1.2), marker='s', lw=0)
            txt(ax, tx + 12, ty - 6, name, size=13, color=INK, alpha=0.75 * fade(t, 0.5, 1.2))
        lit = clamp((t - 1.0) / 1.2)
        for i in range(len(win)):
            gone = seg(t, off[i], off[i] + 0.35)
            col = ORANGE if i == hero else INK
            a = lit * (1 - 0.82 * gone)
            ax.scatter([wx[i]], [wy[i]], s=26 if i == hero else 16, c=DIM if gone > 0.5 else col, alpha=a, lw=0)
            if gone > 0.5 and i != hero:
                ax.scatter([wx[i]], [wy[i]], s=26, c=DIM, marker='x', alpha=0.5 * gone, lw=0.8)
        hx, hy = wx[hero], wy[hero]
        ha = fade(t, 2.0, 2.6)
        ax.add_patch(Circle((hx, hy), 18 + 4 * math.sin(t * 3), fill=False, ec=ORANGE, lw=1.2, alpha=0.8 * ha * (1 - seg(t, 8.4, 8.8))))
        bx, by = mx + mw + 70, 640
        box_a = fade(t, 2.2, 2.9)
        ax.plot([hx + 20, bx - 10], [hy, by + 40], color=ORANGE, lw=0.8, alpha=0.6 * box_a)
        lines = [('18.11.2019 · Hangmure · Bad Hofgastein', INK), ('Massenbewegung:  keine Information', DIM),
                 ('Prozess:         keine Information', DIM), ('Quelle:          Webmeldung', DIM)]
        for j, (s, c) in enumerate(lines):
            txt(ax, bx, by + 60 - j * 38, s, size=19, color=c, alpha=box_a * fade(t, 2.4 + 0.25 * j, 3.0 + 0.25 * j), font=MONO_FONT)
        txt(ax, bx, by - 110, 'AUSGESCHLOSSEN', size=30, color=ORANGE, alpha=fade(t, 8.5, 8.9), font=MONO_FONT)
        n = len(win)
        txt(ax, bx, 330, f'{n} Einträge zu Massenbewegungen im Bildausschnitt', size=19, color=INK, alpha=fade(t, 9.2, 9.8))
        txt(ax, bx, 286, 'davon in unserem Datensatz:  0', size=19, color=ORANGE, alpha=fade(t, 9.8, 10.4), font=MONO_FONT)
        footnote(ax, 'GeoSphere Austria, Naturgefahren-Inventar (Abruf 14.10.2026) · Ausschlussgrund laut Prüfprotokoll V0.4 · Gelände Skadi/SRTM 1″')
        vignette(ax, 0.45)
    return frame


# =====================================================================
# AKT III – 03 ZWILLINGE: real control search for one real event (Tamsweg, 05.07.2023)
# =====================================================================
def a3_zwillinge_factory(fig):
    df = v04()
    grp = df[df.event_group_id == TWIN_GROUP]
    p = grp[grp.label == 1].iloc[0]
    ctl = grp[grp.label == 0]
    pool = pd.read_parquet(ROOT / f'data/v04/cache/control_pools/{TWIN_GROUP}.parquet')
    lon0, lat0 = float(p.longitude), float(p.latitude)
    half_x, half_y = 20500, 11550
    dlon = half_x / (111320 * math.cos(math.radians(lat0)))
    dlat = half_y / 110574
    z, lons, lats = dem_window(lon0 - dlon, lon0 + dlon, lat0 - dlat, lat0 + dlat, stride=2)
    hs = hillshade(z, lat0, stride=2, exag=1.5)
    img = np.dstack([0.05 + 0.42 * hs * c for c in (0.78, 0.84, 0.90)])
    scale = H / (2 * half_y)

    def P(lon, lat):
        x, y = metres(lon, lat, lon0, lat0)
        return W / 2 + x * scale, H / 2 + y * scale

    cx, cy = P(pool.longitude, pool.latitude)
    tx, ty = P(ctl.longitude, ctl.latitude)
    steps = [('Neigung  ± 5°', pool.slope_difference_deg <= 5),
             ('Höhe     ± 150 m', pool.elevation_difference_m <= 150),
             ('Ausrichtung ± 45° (zirkulär)', pool.aspect_difference_deg <= 45),
             ('keine bekannte Rutschung nahe', pool.inventory_clear & pool.inside_austria)]
    masks = [np.ones(len(pool), bool)]
    for _, m in steps:
        masks.append(masks[-1] & m.to_numpy())
    if masks[-1].sum() != int(pool.passes_calipers.sum()):
        raise RuntimeError('Animated filter steps do not reproduce passes_calipers')
    t_steps = [6.0, 8.0, 10.0, 12.0]
    rng = np.random.default_rng(11)
    pop = 3.6 + 2.0 * rng.random(len(pool))
    day = pd.Timestamp(p.event_day).strftime('%d.%m.%Y')

    def frame(t):
        fig.clf()
        fig.patch.set_facecolor(BG)
        ax = canvas(fig)
        ax.imshow(img, extent=(0, W, 0, H), origin='upper', alpha=fade(t, 0, 1.0), interpolation='bilinear')
        chapter(ax, '03  ZWILLINGE', t)
        X0, Y0 = W / 2, H / 2
        ra = seg(t, 1.6, 3.2)
        ax.add_patch(Circle((X0, Y0), 10000 * scale * ra, fill=False, ec=CYAN, lw=1.0, alpha=0.7 * ra, ls=(0, (4, 4))))
        ax.add_patch(Circle((X0, Y0), 750 * scale * ra, fill=False, ec=CYAN, lw=1.0, alpha=0.7 * ra))
        txt(ax, X0 + 10000 * scale * 0.71 + 8, Y0 + 10000 * scale * 0.71, '10 km', size=14, color=CYAN, alpha=fade(t, 3.0, 3.5), font=MONO_FONT)
        stage = sum(t >= s for s in t_steps)
        cur = masks[stage]
        prev = masks[stage - 1] if stage > 0 else cur
        fadeout = seg(t, t_steps[stage - 1], t_steps[stage - 1] + 0.8) if stage > 0 else 1.0
        vis = pop <= t
        keep = vis & cur
        drop = vis & prev & ~cur
        sel_a = seg(t, 14.0, 15.0)
        ax.scatter(cx[keep], cy[keep], s=7, c=INK, alpha=0.55 * (1 - 0.6 * sel_a), lw=0)
        ax.scatter(cx[drop], cy[drop], s=7, c=INK, alpha=0.55 * (1 - fadeout), lw=0)
        for i in range(len(tx)):
            a = seg(t, 14.0 + 0.2 * i, 14.8 + 0.2 * i)
            ax.plot([X0, tx[i]], [Y0, ty[i]], color=INK, lw=0.8, alpha=0.5 * a)
            ax.add_patch(Circle((tx[i], ty[i]), 400 * scale, fill=False, ec=INK, lw=0.8, alpha=0.6 * a))
            ax.scatter([tx[i]], [ty[i]], s=55, c=INK, alpha=a, lw=0)
            txt(ax, tx[i] + 14, ty[i] + 10, f't₀ = {day}', size=12, color=INK, alpha=fade(t, 16.0 + 0.25 * i, 16.6 + 0.25 * i), font=MONO_FONT)
        ax.scatter([X0], [Y0], s=200 + 60 * math.sin(t * 3), c=ORANGE, alpha=0.25 * fade(t, 0.3, 1.0), lw=0)
        ax.scatter([X0], [Y0], s=60, c=ORANGE, alpha=fade(t, 0.3, 1.0), lw=0)
        txt(ax, X0 + 18, Y0 - 30, f't₀ = {day}', size=14, color=ORANGE, alpha=fade(t, 0.8, 1.4), font=MONO_FONT)
        # side panel
        px0 = 1490
        n_now = int(keep.sum()) if t < 14.0 else 5
        if t < 3.6:
            n_now = 0
        txt(ax, px0, 960, de_int(n_now), size=48, color=ORANGE if t >= 14 else INK, font=MONO_FONT, alpha=fade(t, 3.6, 4.0))
        txt(ax, px0, 925, 'Zwillinge' if t >= 14 else 'Kandidatenhänge', size=16, color=DIM, alpha=fade(t, 3.6, 4.0))
        for i, (lab, _) in enumerate(steps):
            on = fade(t, t_steps[i] - 0.3, t_steps[i] + 0.2)
            y = 860 - i * 40
            txt(ax, px0, y, ('✓ ' if on > 0.5 else '• ') + lab, size=15, color=INK if on > 0.5 else DIM, alpha=0.3 + 0.7 * on, font=MONO_FONT)
        txt(ax, px0, 860 - 4 * 40, ('✓ ' if t >= 14 else '• ') + 'beste 5, je ≥ 400 m Abstand', size=15,
            color=INK if t >= 14 else DIM, alpha=0.3 + 0.7 * fade(t, 13.7, 14.2), font=MONO_FONT)
        txt(ax, 90, 150, 'Beispiel aus dem Datensatz', size=15, color=DIM, alpha=fade(t, 0.5, 1.2))
        txt(ax, 90, 112, f'Rutschung bei Tamsweg (Salzburg) · {day} · Lage genau (5–20 m)', size=22, color=INK, alpha=fade(t, 0.6, 1.3))
        txt(ax, 90, 80, 'Zwillinge: Hänge ohne Meldung, nicht zwingend stabil', size=14, color=DIM, alpha=fade(t, 16.5, 17.2))
        footnote(ax, 'Kandidaten und Auswahl aus dem gespeicherten Kontrollpool der Studie V0.4 · Gelände Skadi/SRTM 1″')
        vignette(ax, 0.45)
    return frame


# =====================================================================
# AKT III – 04 REGELN
# =====================================================================
def a3_zeitwand(ax, t):
    chapter(ax, '04  REGELN', t)
    x0, x1, y = 260, 1460, 560
    wall = x1
    a = fade(t, 0.2, 0.9)
    ax.plot([x0, wall], [y, y], color=DIM, lw=1.2, alpha=a)
    for days, lab in [(60, '60 d'), (30, '30 d'), (14, '14 d'), (7, '7 d'), (3, '3 d'), (1, '1 d')]:
        xx = wall - (wall - x0) * days / 60
        ax.plot([xx, xx], [y - 10, y + 10], color=DIM, lw=1, alpha=a)
        txt(ax, xx, y - 42, lab, size=14, color=DIM, alpha=a, font=MONO_FONT, ha='center')
    rng = np.random.default_rng(5)
    n = 70
    seed_x = rng.random(n)
    seed_y = rng.normal(0, 55, n)
    speed = 0.12 + 0.12 * rng.random(n)
    for i in range(n):
        xx = x0 + ((seed_x[i] + speed[i] * t) % 1.15) * (wall - x0 + 60)
        if xx > wall:
            continue
        ax.scatter([xx], [y + 120 + seed_y[i] * 0.6], s=10, c=CYAN, alpha=0.75 * fade(t, 0.5, 1.2), lw=0)
    wa = fade(t, 1.0, 1.6)
    ax.add_patch(Rectangle((wall, 330), 8, 470, facecolor=CYAN, alpha=0.65 * wa, lw=0))
    ax.add_patch(Rectangle((wall + 8, 330), 360, 470, facecolor='#ff3b3b', alpha=0.06 * wa, lw=0, hatch='///', edgecolor='#ff3b3b'))
    txt(ax, wall, 830, 't₀', size=30, color=CYAN, alpha=wa, font=MONO_FONT, ha='center')
    txt(ax, wall + 190, 560, 'gesperrt', size=20, color='#ff6b6b', alpha=wa * 0.9, font=MONO_FONT, ha='center')
    txt(ax, W / 2, 230, 'Keine Information ab dem Ereignis', size=34, color=INK, alpha=fade(t, 2.0, 2.8), font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 180, 'Merkmalsfenster  [t₀ − 60 Tage, t₀)  ·  automatische Tests prüfen jede Grenze', size=18,
        color=DIM, alpha=fade(t, 2.6, 3.4), font=MONO_FONT, ha='center')


def a3_gruppen(ax, t):
    chapter(ax, '04  REGELN', t)
    rng = np.random.default_rng(2)
    groups = 4
    gx = [420, 760, 1100, 1440]
    merge = seg(t, 3.6, 5.0)
    for g in range(groups):
        cx = gx[g] * (1 - merge) + (W / 2 + (g - 1.5) * 150) * merge
        cy = 560
        box_a = fade(t, 1.2 + 0.2 * g, 1.8 + 0.2 * g)
        for j in range(6):
            sx = cx - 75 + (j % 3) * 75
            sy = cy + 40 - (j // 3) * 75
            start_x = sx + rng.normal(0, 140) * (1 - seg(t, 0.2, 1.4))
            start_y = sy + rng.normal(0, 120) * (1 - seg(t, 0.2, 1.4))
            ax.add_patch(Rectangle((start_x - 22, start_y - 22), 44, 44, facecolor=ORANGE if j == 0 else '#c9d2da',
                                   alpha=fade(t, 0.1, 0.6), lw=0))
        ax.add_patch(FancyBboxPatch((cx - 120, cy - 80), 240, 190, boxstyle='round,pad=6', fill=False, ec=INK,
                                    lw=1.1, alpha=box_a * (1 - 0.6 * merge)))
    ea = seg(t, 4.8, 5.6)
    ax.add_patch(FancyBboxPatch((W / 2 - 380, 460), 760, 210, boxstyle='round,pad=10', fill=False, ec=CYAN, lw=1.6, alpha=ea))
    txt(ax, W / 2, 760, 'Ein Unwetter = eine unabhängige Einheit', size=30, color=CYAN, alpha=ea, font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 230, 'Ein Hang und seine Zwillinge bleiben immer zusammen', size=34, color=INK, alpha=fade(t, 1.6, 2.4),
        font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 180, 'nie zwischen Training und Test getrennt  ·  gezählt werden Episoden, nicht Zeilen', size=18, color=DIM,
        alpha=fade(t, 2.2, 3.0), font=MONO_FONT, ha='center')


def a3_siegel(ax, t):
    chapter(ax, '04  REGELN', t)
    slide = seg(t, 0.3, 1.8)
    dx = W / 2 - 260 + (1 - slide) * -600
    ax.add_patch(FancyBboxPatch((dx, 420), 520, 300, boxstyle='round,pad=8', facecolor='#11161c', ec=INK, lw=1.2, alpha=fade(t, 0.1, 0.6)))
    txt(ax, dx + 40, 650, 'TESTDATEN', size=24, color=INK, alpha=fade(t, 0.3, 0.9), font=MONO_FONT)
    txt(ax, dx + 40, 605, '300 Ereignisse', size=18, color=DIM, alpha=fade(t, 0.4, 1.0), font=MONO_FONT)
    txt(ax, dx + 40, 570, '11 unabhängige Episoden', size=18, color=DIM, alpha=fade(t, 0.5, 1.1), font=MONO_FONT)
    s = seg(t, 2.2, 2.6)
    scale = 1.6 - 0.6 * s
    if t >= 2.2:
        ax.add_patch(Circle((W / 2 + 190, 470), 70 * scale, facecolor=ORANGE, alpha=0.9 * s, lw=0))
        ax.add_patch(Circle((W / 2 + 190, 470), 56 * scale, fill=False, ec=BG, lw=1.5, alpha=0.8 * s))
        txt(ax, W / 2 + 190, 462, 'SIEGEL', size=13 * scale, color=BG, alpha=s, font=MONO_FONT, ha='center')
    txt(ax, W / 2, 260, 'Vorab registriert. Versiegelt. Genau einmal geöffnet.', size=34, color=INK, alpha=fade(t, 2.8, 3.6),
        font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 210, 'Präregistrierung und Freeze vor der Auswertung · Ergebnis danach nie nachjustiert', size=18,
        color=DIM, alpha=fade(t, 3.4, 4.2), font=MONO_FONT, ha='center')


# =====================================================================
# AKT III – 05 MODELL
# =====================================================================
def a3_modell(ax, t):
    chapter(ax, '05  MODELL', t)
    a = fade(t, 0.3, 1.2)
    tilt = math.radians(9) * math.exp(-0.9 * max(t - 1.0, 0)) * math.cos(3.2 * max(t - 1.0, 0)) + math.radians(2.5) * seg(t, 1.0, 4.0)
    cx, cy, L = W / 2, 620, 420
    lx, ly = cx - L * math.cos(tilt), cy - L * math.sin(tilt)
    rx, ry = cx + L * math.cos(tilt), cy + L * math.sin(tilt)
    ax.plot([lx, rx], [ly, ry], color=INK, lw=2.0, alpha=a)
    ax.add_patch(Polygon([[cx - 26, cy - 60], [cx + 26, cy - 60], [cx, cy - 4]], closed=True, facecolor=DIM, alpha=a, lw=0))
    for (px, py), items in [((lx, ly), [ORANGE]), ((rx, ry), ['#c9d2da'] * 5)]:
        ax.plot([px - 90, px + 90], [py - 70, py - 70], color=INK, lw=1.4, alpha=a)
        ax.plot([px, px - 90], [py, py - 70], color=DIM, lw=0.8, alpha=a)
        ax.plot([px, px + 90], [py, py - 70], color=DIM, lw=0.8, alpha=a)
        n = len(items)
        for j, c in enumerate(items):
            ax.scatter([px + (j - (n - 1) / 2) * 34], [py - 52], s=380, c=c, alpha=a, lw=0)
    txt(ax, lx, ly - 140, 'gemeldeter Hang', size=16, color=ORANGE, alpha=a, ha='center')
    txt(ax, rx, ry - 140, '5 Zwillinge', size=16, color=INK, alpha=a, ha='center')
    txt(ax, W / 2, 880, r'$P(i\,|\,\mathrm{Gruppe}) = \frac{\exp(\beta^{T} x_i)}{\sum_{j=1}^{6}\exp(\beta^{T} x_j)}$', size=34,
        color=INK, alpha=fade(t, 1.8, 2.8), ha='center')
    txt(ax, W / 2, 300, 'Bedingte logistische Regression · eigene Implementierung', size=30, color=INK, alpha=fade(t, 3.0, 3.8),
        font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 245, 'vergleicht immer einen Hang mit seinen fünf Zwillingen', size=20, color=DIM, alpha=fade(t, 3.4, 4.2), ha='center')
    txt(ax, W / 2, 170, 'Gegenprüfung:  Logistische Regression  ·  Random Forest  ·  Gradient Boosting  ·  Permutationstest', size=17,
        color=CYAN, alpha=fade(t, 5.0, 5.8), font=MONO_FONT, ha='center')


# =====================================================================
# AKT IV – RESULTS
# =====================================================================
def a4_ergebnis(ax, t):
    flash = math.exp(-((t - 0.6) / 0.25) ** 2)
    if flash > 0.01:
        ax.add_patch(Rectangle((0, 0), W, H, facecolor='#fff6e8', alpha=0.85 * flash, lw=0))
    v = 0.5 + (V04_COMBINED - 0.5) * seg(t, 1.0, 3.2)
    txt(ax, W / 2, 560, de(v, 2), size=170, color=INK, alpha=fade(t, 0.9, 1.4), font=MONO_FONT, ha='center')
    txt(ax, W / 2, 455, 'lokale AUC · Gelände + Wetter · versiegelter Test', size=20, color=DIM, alpha=fade(t, 1.6, 2.2), ha='center')
    x0, x1, y = 460, 1460, 360

    def X(val):
        return x0 + (val - 0.4) / 0.6 * (x1 - x0)
    sa = fade(t, 3.2, 3.9)
    ax.plot([x0, x1], [y, y], color=DIM, lw=1, alpha=sa)
    for val in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        ax.plot([X(val), X(val)], [y - 6, y + 6], color=DIM, lw=1, alpha=sa)
        txt(ax, X(val), y - 34, de(val, 1), size=13, color=DIM, alpha=sa, font=MONO_FONT, ha='center')
    ax.add_patch(Rectangle((X(0.5), y - 14), X(V04_NULL95) - X(0.5), 28, facecolor=DIM, alpha=0.25 * sa, lw=0))
    txt(ax, X(0.5), y + 24, 'Zufall', size=13, color=DIM, alpha=sa, ha='left', font=MONO_FONT)
    ia = fade(t, 4.0, 4.8)
    ax.plot([X(V04_CI[0]), X(V04_CI[1])], [y, y], color=ORANGE, lw=5, alpha=ia, solid_capstyle='butt')
    ax.scatter([X(V04_COMBINED)], [y], s=140, c=ORANGE, alpha=ia, lw=0, zorder=5)
    txt(ax, X(V04_COMBINED), y + 30, f'[{de(V04_CI[0], 3)} – {de(V04_CI[1], 3)}]', size=16, color=ORANGE, alpha=ia, font=MONO_FONT, ha='center')
    txt(ax, W / 2, 190, 'In rund drei von vier Vergleichen liegt der betroffene Hang vor seinen Zwillingen.', size=24, color=INK,
        alpha=fade(t, 5.0, 5.8), ha='center')
    footnote(ax, '300 Ereignisse · 11 unabhängige Episoden · 95 %-Intervall (Einheiten-Bootstrap) · grau: 95 % der Zufallsläufe bis 0,629',
             alpha=fade(t, 5.4, 6.0))


def a4_balken(ax, t):
    rows = [('Wetter allein', V04_TEMPORAL, None, CYAN), ('Gelände allein', V04_STATIC, None, '#c9d2da'),
            ('Gelände + Wetter', V04_COMBINED, V04_CI, ORANGE)]
    x0, x1 = 520, 1640

    def X(val):
        return x0 + (val - 0.4) / 0.6 * (x1 - x0)
    a = fade(t, 0.2, 0.8)
    for val in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        ax.plot([X(val), X(val)], [300, 800], color=FAINT, lw=1, alpha=a)
        txt(ax, X(val), 262, de(val, 1), size=13, color=DIM, alpha=a, font=MONO_FONT, ha='center')
    ax.add_patch(Rectangle((X(0.5), 300), X(V04_NULL95) - X(0.5), 500, facecolor=DIM, alpha=0.12 * a, lw=0))
    ax.plot([X(0.5), X(0.5)], [300, 800], color=DIM, lw=1.2, ls=(0, (5, 5)), alpha=a)
    txt(ax, X(0.5), 820, 'Zufall', size=14, color=DIM, alpha=a, ha='center', font=MONO_FONT)
    for i, (lab, val, ci, col) in enumerate(rows):
        y = 680 - i * 150
        g = seg(t, 1.0 + 0.9 * i, 2.4 + 0.9 * i)
        ax.add_patch(Rectangle((X(0.4), y - 30), (X(val) - X(0.4)) * g, 60, facecolor=col, alpha=0.9, lw=0))
        txt(ax, X(0.4) - 30, y - 9, lab, size=22, color=INK, alpha=fade(t, 0.8 + 0.9 * i, 1.4 + 0.9 * i), ha='right')
        txt(ax, X(val) + 18, y - 10, de(val, 3), size=22, color=col, alpha=fade(t, 2.2 + 0.9 * i, 2.8 + 0.9 * i), font=MONO_FONT)
        if ci:
            ca = fade(t, 4.6, 5.2)
            ax.plot([X(ci[0]), X(ci[1])], [y - 48, y - 48], color=col, lw=2, alpha=ca)
            for c in ci:
                ax.plot([X(c), X(c)], [y - 56, y - 40], color=col, lw=2, alpha=ca)
    inc, lo, hi = V04_INCREMENT
    txt(ax, W / 2, 160, f'Zusatz durch Wetter:  +{de(inc, 3)}  [{de(lo, 3)}; +{de(hi, 3)}]   →   nicht belegt', size=24,
        color=INK, alpha=fade(t, 6.0, 6.8), font=MONO_FONT, ha='center')
    footnote(ax, 'Versiegelter Test V0.4 · bedingte logistische Regression · lokale AUC, Einheiten gleich gewichtet · Intervall nur für den Primärendpunkt berichtet',
             alpha=fade(t, 6.4, 7.0))


def a4_ungesehen(ax, t):
    txt(ax, W / 2, 800, 'Neue, ungesehene Ereignisse', size=30, color=INK, alpha=fade(t, 0.2, 0.9), font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 520, de(V09_STATIC, 2), size=150, color=INK, alpha=fade(t, 0.8, 1.6), font=MONO_FONT, ha='center')
    txt(ax, W / 2, 455, 'Gelände allein', size=22, color=DIM, alpha=fade(t, 1.2, 1.8), ha='center')
    inc, lo, hi = V09_INCREMENT
    txt(ax, W / 2, 330, f'Gelände + Wetter {de(V09_COMBINED, 3)}  ·  Zusatz {de(inc, 3)}  [{de(lo, 3)}; +{de(hi, 3)}]', size=20,
        color=CYAN, alpha=fade(t, 2.4, 3.2), font=MONO_FONT, ha='center')
    footnote(ax, 'explorativ · V0.9, Medienmeldungen · 14 Episoden · einmal bewertet', alpha=fade(t, 2.8, 3.4))


def a4_extremwetter(ax, t):
    txt(ax, W / 2, 860, 'Derselbe Ort, verschiedene Zeiten', size=30, color=INK, alpha=fade(t, 0.2, 0.9), font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 815, 'Anteil der Episoden mit extrem nassen 3 Tagen davor (über dem örtlichen 95. Perzentil)', size=18,
        color=DIM, alpha=fade(t, 0.6, 1.2), ha='center')
    base, top = 260, 680

    def Y(pct):
        return base + pct / 40 * (top - base)
    for i, (lab, val, col, ci) in enumerate([('erwartet', 5.0, '#c9d2da', None), ('beobachtet', EXTREM_SHARE, CYAN, EXTREM_CI)]):
        x = W / 2 - 220 + i * 440
        g = seg(t, 1.2 + 1.2 * i, 2.6 + 1.2 * i)
        ax.add_patch(Rectangle((x - 90, base), 180, (Y(val) - base) * g, facecolor=col, alpha=0.9, lw=0))
        txt(ax, x, Y(val) * 1 + 24 if ci is None else Y(ci[1]) + 24, f'{de(val, 1)} %', size=34, color=col,
            alpha=fade(t, 2.4 + 1.2 * i, 3.0 + 1.2 * i), font=MONO_FONT, ha='center')
        txt(ax, x, base - 44, lab, size=20, color=INK, alpha=fade(t, 1.0 + 1.2 * i, 1.6 + 1.2 * i), ha='center')
        if ci:
            ca = fade(t, 4.4, 5.0)
            ax.plot([x, x], [Y(ci[0]), Y(ci[1])], color=INK, lw=1.6, alpha=ca)
            for c in ci:
                ax.plot([x - 14, x + 14], [Y(c), Y(c)], color=INK, lw=1.6, alpha=ca)
    ax.plot([W / 2 - 420, W / 2 + 420], [base, base], color=DIM, lw=1, alpha=fade(t, 0.8, 1.2))
    footnote(ax, 'explorativ · 35 Episoden · SPARTACUS (GeoSphere), Referenz ±15 Kalendertage 1991–2025 · Zusammenhang, keine Ursache · vorab festgelegter Haupttest knapp nicht erfüllt',
             alpha=fade(t, 5.2, 5.8))


# =====================================================================
# AKT V – REFLECTION
# =====================================================================
def a5_meldebias(ax, t):
    rng = np.random.default_rng(9)
    a = fade(t, 0.2, 1.0)
    for _ in range(9):
        xs = np.linspace(-50, W + 50, 40)
        y0 = rng.uniform(150, 950)
        ys = y0 + np.cumsum(rng.normal(0, 9, 40))
        ax.plot(xs, ys, color=CYAN, lw=1.2, alpha=0.18 * a)
    txt(ax, W / 2, 560, de(V07_DISTANCE, 2), size=160, color=INK, alpha=fade(t, 0.8, 1.6), font=MONO_FONT, ha='center')
    txt(ax, W / 2, 485, 'nur der Abstand zu Straßen und Gebäuden', size=26, color=DIM, alpha=fade(t, 1.4, 2.0), ha='center')
    txt(ax, W / 2, 330, 'Gemeldet wird, was Menschen sehen.', size=36, color=ORANGE, alpha=fade(t, 2.8, 3.6), font=TITLE_FONT, ha='center')
    footnote(ax, 'explorativ · V0.7 · Vergleich gemeldeter Hang gegen ungematchte Umgebungspunkte (V0.5-Design) · OpenStreetMap-Mitwirkende',
             alpha=fade(t, 3.4, 4.0))


def a5_grenzen(ax, t):
    lines = ['11 unabhängige Episoden im Test', 'eine Episode (Stanz 2016) = 243 von 300 Ereignissen', 'nicht gemeldet heißt nicht sicher']
    for i, s in enumerate(lines):
        y = 640 - i * 120
        a = fade(t, 0.5 + 1.6 * i, 1.2 + 1.6 * i)
        ax.plot([560, 560], [y - 12, y + 40], color=ORANGE, lw=2, alpha=a)
        txt(ax, 590, y, s, size=34, color=INK, alpha=a, font=TITLE_FONT)


def a5_kein_warnsystem(ax, t):
    txt(ax, W / 2, 560, 'Kein Warnsystem.', size=54, color=INK, alpha=fade(t, 0.4, 1.2), font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 470, 'Keine Wahrscheinlichkeit.', size=54, color=INK, alpha=fade(t, 1.4, 2.2), font=TITLE_FONT, ha='center')
    txt(ax, W / 2, 360, 'Eine begründete Reihenfolge: wo man zuerst hinschaut.', size=24, color=DIM, alpha=fade(t, 2.6, 3.4), font=LIGHT_FONT, ha='center')


# =====================================================================
# AKT VII – END CARD
# =====================================================================
def a7_endtafel(ax, t):
    a = fade(t, 0.4, 1.8)
    spaced(ax, W / 2, 610, 'TALWACHT', 84, 0.22, alpha=a)
    ax.plot([W / 2 - 150 * a, W / 2 + 150 * a], [565, 565], color=ORANGE, lw=1.4, alpha=a)
    txt(ax, W / 2, 500, 'Wo zuerst hinschauen, wenn der Starkregen kommt.', size=26, color=INK, alpha=fade(t, 1.6, 2.6), font=LIGHT_FONT, ha='center')
    credits = ('Daten: GeoSphere Austria (Naturgefahren-Inventar, INCA, SPARTACUS, Geologie 1:500 000) · Copernicus CORINE Land Cover · '
               'Skadi/SRTM-Gelände · OpenStreetMap-Mitwirkende · EuroGeographics/GISCO')
    txt(ax, W / 2, 120, credits, size=13, color=DIM, alpha=fade(t, 2.6, 3.4), ha='center')


CLIPS = {
    'a1_titel': (7.0, flat(a1_titel)),
    'a1_terminal': (5.0, flat(a1_terminal)),
    'a1_ort': (5.0, flat(a1_ort)),
    'a3_01_ebenen': (24.0, a3_ebenen_factory),
    'a3_02_filter_oesterreich': (15.0, a3_filter_factory),
    'a3_02_gastein_ausschluss': (13.0, a3_gastein_factory),
    'a3_03_zwillinge': (19.0, a3_zwillinge_factory),
    'a3_04_zeitwand': (7.0, flat(a3_zeitwand)),
    'a3_04_gruppen': (7.5, flat(a3_gruppen)),
    'a3_04_siegel': (6.0, flat(a3_siegel)),
    'a3_05_modell': (9.0, flat(a3_modell)),
    'a4_ergebnis': (10.0, flat(a4_ergebnis)),
    'a4_balken': (11.0, flat(a4_balken)),
    'a4_ungesehen': (7.0, flat(a4_ungesehen)),
    'a4_extremwetter': (9.0, flat(a4_extremwetter)),
    'a5_meldebias': (8.0, flat(a5_meldebias)),
    'a5_grenzen': (8.0, flat(a5_grenzen)),
    'a5_kein_warnsystem': (5.0, flat(a5_kein_warnsystem)),
    'a7_endtafel': (9.0, flat(a7_endtafel)),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--still', type=float)
    args = ap.parse_args()
    for name, (duration, factory) in CLIPS.items():
        if args.only and name not in args.only:
            continue
        render(name, duration, factory, still=args.still)
        print(name, 'still' if args.still is not None else 'mp4', flush=True)


if __name__ == '__main__':
    main()
