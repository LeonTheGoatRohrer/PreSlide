"""susceptibility_v02 Phase 2 safety tests: terrain parameters as registered, verified NASADEM tiles, CRS orientation
of the DEM window in EPSG:32654, block coverage of the extent, DEM date rule and meridian convergence.

Synthetic tiles are written to pytest's tmp_path only; nothing goes to data/ or reports/.
"""
import copy

import numpy as np
import pytest
import rasterio
import shapely
from pyproj import Transformer
from rasterio.transform import from_origin

from preslide.common import read_json, write_json
from preslide.sources import ROOT
from preslide.susceptibility import v02_terrain as T
from preslide.susceptibility.download import file_digest
from preslide.susceptibility.terrain import CacheCorruption, check_dem_date

CFG = read_json(ROOT / 'config/susceptibility_v02.json')


def field(lon, lat):
    """Asymmetric linear elevation field: east and north gradients differ, so swapped axes are visible."""
    return 1000.0 * (lon - 141.0) + 50.0 * (lat - 42.0)


def write_tile(folder, lat, lon, step=0.005):
    name = f'NASADEM_HGT_n{lat:02d}e{lon:03d}'
    d = folder / name
    d.mkdir(parents=True)
    n = round(1 / step) + 1
    lons = lon + np.arange(n) * step
    lats = lat + 1 - np.arange(n) * step
    g = field(lons[None, :], lats[:, None]).astype('float32')
    path = d / f'{name}.tif'
    with rasterio.open(path, 'w', driver='GTiff', height=n, width=n, count=1, dtype='float32', crs='EPSG:4326',
                       transform=from_origin(lon - step / 2, lat + 1 + step / 2, step, step), nodata=-32768) as dst:
        dst.write(g, 1)
    write_json(d / 'provenance.json', {'files': [{'sha256': file_digest(path, 'sha256')}]})
    return path


def test_terrain_parameters_match_registration():
    t = T.terrain_parameters(copy.deepcopy(CFG))
    assert {k: t[k] for k in T.REGISTERED_TERRAIN} == T.REGISTERED_TERRAIN
    bad = copy.deepcopy(CFG)
    bad['terrain_parameters']['rule'] = bad['terrain_parameters']['rule'].replace('tpi_radius_m 300', 'tpi_radius_m 500')
    with pytest.raises(RuntimeError, match='tpi_radius_m'):
        T.terrain_parameters(bad)


def test_dem_window_orientation_in_utm54(tmp_path):
    write_tile(tmp_path, 42, 141)
    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:32654', always_xy=True)
    x0, y0 = fwd.transform(141.5, 42.5)
    left, top = round(x0 / 30) * 30, round(y0 / 30) * 30
    dem = T.dem_window('EPSG:32654', left, top - 3000, left + 6000, top, 30, dem_dir=tmp_path)
    assert dem.shape == (100, 200)
    inv = Transformer.from_crs('EPSG:32654', 'EPSG:4326', always_xy=True)
    for r, c in [(0, 0), (10, 150), (99, 199), (50, 7)]:
        lon, lat = inv.transform(left + 30 * c + 15, top - 30 * r - 15)
        assert dem[r, c] == pytest.approx(field(lon, lat), abs=0.05)
    assert dem[50, 199] > dem[50, 0]  # east is higher
    assert dem[0, 100] > dem[99, 100]  # north is higher


def test_dem_window_across_tile_seam(tmp_path):
    write_tile(tmp_path, 42, 141)
    write_tile(tmp_path, 42, 142)
    fwd, inv = (Transformer.from_crs(a, b, always_xy=True) for a, b in (('EPSG:4326', 'EPSG:32654'), ('EPSG:32654', 'EPSG:4326')))
    x0, y0 = fwd.transform(141.97, 42.5)
    left, top = round(x0 / 30) * 30, round(y0 / 30) * 30
    dem = T.dem_window('EPSG:32654', left, top - 1500, left + 6000, top, 30, dem_dir=tmp_path)
    for r, c in [(25, 0), (25, 100), (25, 199)]:
        lon, lat = inv.transform(left + 30 * c + 15, top - 30 * r - 15)
        assert dem[r, c] == pytest.approx(field(lon, lat), abs=0.05)


def test_changed_or_missing_tile_is_refused(tmp_path):
    path = write_tile(tmp_path, 42, 141)
    assert T.tile_file(42, 141, tmp_path) == path
    with rasterio.open(path, 'r+') as dst:
        dst.write(np.zeros((1, dst.height, dst.width), 'float32'))
    with pytest.raises(CacheCorruption):
        T.tile_file(42, 141, tmp_path)
    with pytest.raises(FileNotFoundError):
        T.tile_file(43, 141, tmp_path)


def test_blocks_cover_extent_and_skip_disjoint():
    # L-shaped extent: the grid over its bounding box has an empty corner block that must be skipped.
    poly = shapely.Polygon([(560000, 4710000), (600000, 4710000), (600000, 4722000), (572000, 4722000),
                            (572000, 4755000), (560000, 4755000)])
    t = T.REGISTERED_TERRAIN
    blocks = T.blocks_for(poly, t, 30)
    union = shapely.union_all([shapely.box(*b[2:]) for b in blocks])
    assert union.contains(poly)
    assert all(shapely.box(*b[2:]).intersects(poly) for b in blocks)
    assert all(b[2] % 30 == 0 and b[5] % 30 == 0 for b in blocks)
    assert len(blocks) < len(T.block_grid(poly.bounds, t['block_core_m'], 30))


def test_dem_must_predate_iburi_event():
    c = copy.deepcopy(CFG)
    c['registry']['datasets']['iburi_2018']['earliest_event_date'] = '2018-09-06'
    check_dem_date(c, 'iburi_2018')
    c['dem']['acquisition_end'] = '2018-09-06'
    with pytest.raises(ValueError, match='not before'):
        check_dem_date(c, 'iburi_2018')


def test_only_new_inventory_and_registered_crs(monkeypatch):
    monkeypatch.setattr(T, 'fetch_nasadem', lambda *a: pytest.fail('download attempted'))
    with pytest.raises(ValueError, match='no v02 terrain'):
        T.extent_utm('rer2023', 32632)
    c = copy.deepcopy(CFG)
    assert T.working_crs(c, 'gorkha_2015') == 'EPSG:32645' and T.working_crs(c, 'far_western_nepal') == 'EPSG:32644'
    with pytest.raises(RuntimeError, match='working CRS'):
        T.working_crs(c, 'rer2023')
    with pytest.raises(ValueError, match='nothing to download'):
        T.terrain_fetch('gorkha_2015')


def test_snap_to_lattice_expands_to_whole_pixels():
    res, x0, y0 = 1 / 3600, 141 - 0.5 / 3600, 43 + 0.5 / 3600
    b = (141.2345678, 42.3456789, 141.5432109, 42.6543219)
    s = T.snap_to_lattice(b, x0, y0, res)
    assert s[0] <= b[0] and s[1] <= b[1] and s[2] >= b[2] and s[3] >= b[3]
    for v, o in ((s[0], x0), (s[2], x0), (s[1], y0), (s[3], y0)):
        assert abs((v - o) / res - round((v - o) / res)) < 1e-6
    assert all(abs(a - c) <= res for a, c in zip(s, b))


def test_meridian_convergence_zero_on_central_meridian():
    fwd = Transformer.from_crs('EPSG:4326', 'EPSG:32654', always_xy=True)
    on_cm = shapely.Polygon([fwd.transform(141.0, la) for la in (42.0, 42.5, 43.0)] + [fwd.transform(141.0, 42.0)])
    assert T.meridian_convergence_max(on_cm.buffer(1), 32654) < 0.01
    east = shapely.Polygon([fwd.transform(lo, la) for lo, la in ((142, 42.5), (142.01, 42.5), (142.01, 42.51), (142, 42.5))])
    assert T.meridian_convergence_max(east, 32654) == pytest.approx(np.degrees(np.arctan(np.tan(np.radians(1.0)) * np.sin(np.radians(42.5)))), abs=0.02)
