"""Pure wirkungskette_v01 logic (no IO): radius rule, metric grid, relative review classes, D8 route,
runout scenarios (fixed reach, energy line), corridor exposure, wording guard, relief image.

All coordinates handed to these functions are EPSG:31287 metres; degree input is refused.
"""
import math
import re

import numpy as np
from shapely import STRtree
from shapely.geometry import LineString, Point

# ---------- radius and metric guard ----------


def validate_radius(radius_m, cfg):
    r = cfg['radius_m']
    try:
        radius_m = float(radius_m)
    except (TypeError, ValueError) as error:
        raise ValueError('Radius muss eine Zahl in Metern sein') from error
    if not math.isfinite(radius_m) or not r['min'] <= radius_m <= r['max']:
        raise ValueError(f"Radius muss zwischen {r['min'] / 1000:g} und {r['max'] / 1000:g} km liegen")
    if abs(radius_m / r['step'] - round(radius_m / r['step'])) > 1e-9:
        raise ValueError(f"Radius in Schritten von {r['step']:g} m")
    return radius_m


def assert_projected(x_m, y_m):
    """EPSG:31287 coordinates in Austria are ~1e5..1e6 m; values that look like degrees are refused."""
    x, y = np.asarray(x_m, float), np.asarray(y_m, float)
    if x.size and (np.nanmax(np.abs(x)) < 1000 or np.nanmax(np.abs(y)) < 1000):
        raise ValueError('Koordinaten sehen nach Grad aus; erwartet sind EPSG:31287-Meter')


def distance_m(x_m, y_m, cx_m, cy_m):
    """Planar distance in the metric EPSG:31287 grid (Lambert conformal; scale error < 0.1 % in Austria)."""
    assert_projected(x_m, y_m)
    assert_projected([cx_m], [cy_m])
    return np.hypot(np.asarray(x_m, float) - cx_m, np.asarray(y_m, float) - cy_m)


# ---------- grid (ported from hangmap_v01 core, branch claude/clever-satoshi-e4ace7) ----------


def dem_cell_xy(left, top, res_m, rows, cols):
    """Centres (EPSG:31287 metres) of DEM cells; inverse of the floor lookup used by the feature code."""
    return left + (np.asarray(cols) + .5) * res_m, top - (np.asarray(rows) + .5) * res_m


def xy_to_cell(left, top, res_m, x_m, y_m):
    assert_projected(x_m, y_m)
    return (np.floor((top - np.asarray(y_m, float)) / res_m).astype(int),
            np.floor((np.asarray(x_m, float) - left) / res_m).astype(int))


def grid_cells(cx, cy, radius_m, left, top, res_m, cell_m, shape):
    """DEM cells on a cell_m grid anchored at the centre cell, inside the circle (projected metres)."""
    assert_projected([cx], [cy])
    step = int(round(cell_m / res_m))
    if step < 1 or abs(step * res_m - cell_m) > 1e-9:
        raise ValueError('cell_m must be a multiple of the DEM resolution')
    r0, c0 = int(math.floor((top - cy) / res_m)), int(math.floor((cx - left) / res_m))
    span = int(radius_m // res_m) + 1
    rows, cols = np.meshgrid(np.arange(r0 - span // step * step, r0 + span + 1, step),
                             np.arange(c0 - span // step * step, c0 + span + 1, step), indexing='ij')
    rows, cols = rows.ravel(), cols.ravel()
    ok = (rows >= 0) & (cols >= 0) & (rows < shape[0]) & (cols < shape[1])
    rows, cols = rows[ok], cols[ok]
    x, y = dem_cell_xy(left, top, res_m, rows, cols)
    inside = np.hypot(x - cx, y - cy) <= radius_m
    return rows[inside], cols[inside], x[inside], y[inside]


# ---------- relative review classes ----------


def review_classes(score, classes):
    """Class id per cell from the descending rank inside the window: position/n <= top_fraction.

    Ties are broken by the stable input order (scores are continuous, ties practically absent)."""
    score = np.asarray(score, float)
    if not np.isfinite(score).all():
        raise ValueError('NaN score: only assessable cells may be classed')
    n = len(score)
    out = np.zeros(n, int)
    if n == 0:
        return out
    order = np.argsort(-score, kind='stable')
    frac = np.empty(n)
    frac[order] = (np.arange(n) + 1) / n
    bounds = sorted(classes, key=lambda c: c['top_fraction'])
    if abs(bounds[-1]['top_fraction'] - 1) > 1e-12:
        raise ValueError('last class must cover the remaining cells (top_fraction 1.0)')
    for c in reversed(bounds):
        out[frac <= c['top_fraction'] + 1e-12] = c['id']
    return out


def class_cutoffs(score, classes):
    """Lowest score still inside each class (for placing extra points relative to the same window)."""
    score = np.asarray(score, float)
    ids = review_classes(score, classes)
    return {c['id']: float(score[ids == c['id']].min()) for c in classes if (ids == c['id']).any()}


def classify_by_cutoffs(score, cutoffs):
    """Class of new scores against cutoffs of a reference window (best class whose minimum is reached)."""
    out = np.full(len(score), max(cutoffs), int)
    for cid in sorted(cutoffs, reverse=True):
        out[np.asarray(score) >= cutoffs[cid]] = cid
    return out


def select_release_points(x_m, y_m, score, k, separation_m):
    """Highest scores first; a point is taken only if >= separation_m from every taken point."""
    assert_projected(x_m, y_m)
    x, y, s = np.asarray(x_m, float), np.asarray(y_m, float), np.asarray(score, float)
    chosen = []
    for i in np.argsort(-s, kind='stable'):
        if all(math.hypot(x[i] - x[j], y[i] - y[j]) >= separation_m for j in chosen):
            chosen.append(int(i))
            if len(chosen) == k:
                break
    return chosen


# ---------- D8 route ----------

OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def d8_route(surface, dem, start_row, start_col, res_m, max_route_m):
    """Steepest descent (D8) on `surface` from a start cell.

    Ends with 'rand' when the route stands on the window border (the true end is unknown), 'nodata' when the
    steepest neighbour has no DEM value, 'senke' when no neighbour is lower (unresolved pit) and 'max_laenge'
    after max_route_m. Returns rows, cols and the end reason. The start cell must hold a DEM value."""
    rows, cols = surface.shape
    r, c = int(start_row), int(start_col)
    if not (0 <= r < rows and 0 <= c < cols) or not np.isfinite(dem[r, c]):
        raise ValueError('Anrisspunkt außerhalb des Geländefensters oder ohne Höhenwert')
    path_r, path_c, length = [r], [c], 0.0
    while True:
        if r == 0 or c == 0 or r == rows - 1 or c == cols - 1:
            return np.array(path_r), np.array(path_c), 'rand'
        best, nxt = 0.0, None
        for dr, dc in OFFSETS:
            dist = res_m * math.hypot(dr, dc)
            nz = dem[r + dr, c + dc]
            ns = surface[r + dr, c + dc] if np.isfinite(nz) else -np.inf
            drop = (surface[r, c] - ns) / dist
            if drop > best:
                best, nxt = drop, (r + dr, c + dc, dist)
        if nxt is None:
            return np.array(path_r), np.array(path_c), 'senke'
        if not np.isfinite(dem[nxt[0], nxt[1]]):
            return np.array(path_r), np.array(path_c), 'nodata'
        if length + nxt[2] > max_route_m:
            return np.array(path_r), np.array(path_c), 'max_laenge'
        r, c, length = nxt[0], nxt[1], length + nxt[2]
        path_r.append(r)
        path_c.append(c)


def path_distance_m(rows, cols, res_m):
    """Cumulative horizontal path length along the route (0 at the start cell)."""
    steps = np.hypot(np.diff(rows), np.diff(cols)) * res_m
    return np.concatenate([[0.0], np.cumsum(steps)])


def sink_cells(surface, dem, rows, cols, depth_m):
    """Route cells lying in a computationally filled depression deeper than depth_m."""
    return (surface[rows, cols] - dem[rows, cols]) > depth_m


# ---------- runout scenarios ----------


def _unfinished(route_end):
    # A scenario that has not stopped when the route ends: the route end decides what is known.
    return route_end


def fixed_reach_stop(s_m, reach_m, route_end):
    """Last route index within the horizontal reach; status 'gestoppt' or the route end reason if the route is shorter."""
    s = np.asarray(s_m, float)
    if s[-1] >= reach_m:
        return {'stop_index': int(np.searchsorted(s, reach_m, side='right') - 1), 'status': 'gestoppt'}
    return {'stop_index': len(s) - 1, 'status': _unfinished(route_end)}


def energy_line_stop(z_m, s_m, angle_deg, v_max_m_s, g_m_s2, route_end):
    """Fahrböschung energy line with velocity cap (Flow-R style), along the route.

    h_0 = 0, h_i = min(h_{i-1} + (z_{i-1} - z_i) - dx_i * tan(alpha), v_max^2 / (2 g)); the scenario stops at the
    last index with h >= 0. Returns stop index, status and the energy-line height z + h up to the stop."""
    z, s = np.asarray(z_m, float), np.asarray(s_m, float)
    if not np.isfinite(z).all():
        raise ValueError('Höhenprofil enthält Lücken')
    cap = v_max_m_s ** 2 / (2 * g_m_s2)
    tan_a = math.tan(math.radians(angle_deg))
    h = np.zeros(len(z))
    for i in range(1, len(z)):
        h[i] = min(h[i - 1] + (z[i - 1] - z[i]) - (s[i] - s[i - 1]) * tan_a, cap)
        if h[i] < 0:
            return {'stop_index': i - 1, 'status': 'gestoppt', 'energy_height_m': (z[:i] + h[:i]).tolist()}
    return {'stop_index': len(z) - 1, 'status': _unfinished(route_end), 'energy_height_m': (z + h).tolist()}


# ---------- corridor and exposure ----------


def corridor(x_m, y_m, stop_index, width_m):
    """Route up to stop_index, buffered by width/2 (EPSG:31287 metres)."""
    assert_projected(x_m, y_m)
    xs, ys = np.asarray(x_m, float)[:stop_index + 1], np.asarray(y_m, float)[:stop_index + 1]
    geom = Point(xs[0], ys[0]) if len(xs) == 1 else LineString(np.column_stack([xs, ys]))
    return geom.buffer(width_m / 2)


class Exposure:
    """Spatial index over infrastructure features (shapely geometries in EPSG:31287)."""

    def __init__(self, features):
        self.features = features
        self.tree = STRtree([f['geometry'] for f in features]) if features else None

    def hits(self, area):
        if self.tree is None:
            return []
        out = []
        for i in self.tree.query(area, predicate='intersects'):
            f = self.features[int(i)]
            inside = f['geometry'].intersection(area)
            out.append({'index': int(i), 'typ': f['typ'], 'length_m': float(inside.length) if f['geometry'].geom_type != 'Polygon' else 0.0})
        return sorted(out, key=lambda h: h['index'])


def count_by_type(hits, types):
    out = {t: {'anzahl': 0, 'laenge_m': 0.0} for t in types}
    for h in hits:
        out[h['typ']]['anzahl'] += 1
        out[h['typ']]['laenge_m'] += h['length_m']
    return {t: {'anzahl': v['anzahl'], 'laenge_m': round(v['laenge_m'], 1)} for t, v in out.items()}


# ---------- wording guard ----------

BANNED = re.compile(r'wahrscheinlich|risiko|risk|probab|gefährd|gefaehrd', re.IGNORECASE)


def banned_words(value, where='$'):
    """Paths of every string (key or value) in a JSON-like object that uses a probability/risk word."""
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            if BANNED.search(str(k)):
                found.append(f'{where}.{k} (Schlüssel)')
            found += banned_words(v, f'{where}.{k}')
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            found += banned_words(v, f'{where}[{i}]')
    elif isinstance(value, str) and BANNED.search(value):
        found.append(where)
    return found


# ---------- relief ----------


def hillshade(dem, res_m, azimuth_deg=315.0, altitude_deg=45.0):
    """Lambertian hillshade 0..255 (row = south, col = east); NaN where the DEM or a neighbour is missing."""
    z = dem.astype(float)
    dzdy, dzdx = np.gradient(z, res_m, res_m)          # dzdy along rows (southward)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdx, dzdy)                    # downslope azimuth, clockwise from north
    az, alt = math.radians(azimuth_deg), math.radians(altitude_deg)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1) * 255
