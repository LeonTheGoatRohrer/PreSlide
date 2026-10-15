"""Run the unchanged V0.4 data code for V0.9 with every write redirected to data/v09.

`bind()` rebinds the module globals through which V0.4 writes or downloads:
  * every V0.4 module's `guard` -> the V0.9 guard (which refuses any path outside data/v09, models/v09, reports/v09),
  * preslide.v04.terrain.CACHE -> data/v09/cache (matching windows, control pools, new DEM tiles),
  * preslide.v04.terrain.tile -> read the baseline and V0.4 tile caches (checksum + pre-event provenance) first,
  * cached_json in preslide.v04.{http, weather, context} -> the V0.9 cache (baseline/V0.4/V0.5 caches read only).
Feature, matching and weather algorithms are not copied or changed. tests/test_v09.py checks that a bound V0.4
write to data/v04 raises.
"""
import numpy as np
from scipy.spatial import cKDTree

from ..common import read_json
from ..matching import Exclusions
from ..sources import ROOT
from ..terrain import PROJECT
from .http import cached_json
from .paths import V09_DATA, guard

V04_TILES = ROOT / 'data/v04/cache/terrain_tiles'
_BOUND = {}


def _tile_factory(original, terrain):
    def tile(lat, lon, event_day):
        name = f'N{lat:02d}E{lon:03d}'
        if not (terrain.BASE_TILES / f'{name}.json').exists() and (V04_TILES / f'{name}.json').exists():
            hgt, meta = V04_TILES / f'{name}.hgt', read_json(V04_TILES / f'{name}.json')
            if str(hgt) not in terrain._VERIFIED:
                if terrain.sha(hgt) != meta['sha256']:
                    raise ValueError('Terrain source cache checksum mismatch')
                terrain._VERIFIED.add(str(hgt))
            if meta['object_last_modified'][:10] >= event_day:
                raise ValueError('terrain_source_not_demonstrably_pre_event')
            return hgt, meta
        return original(lat, lon, event_day)
    return tile


def bind():
    if _BOUND:
        return _BOUND
    from ..v04 import context, http, paths, pipeline, terrain, weather
    for module in (paths, terrain, pipeline):
        _BOUND[(module.__name__, 'guard')] = module.guard
        module.guard = guard
    _BOUND[('terrain', 'CACHE')] = terrain.CACHE
    terrain.CACHE = V09_DATA / 'cache'
    _BOUND[('terrain', 'tile')] = terrain.tile
    terrain.tile = _tile_factory(terrain.tile, terrain)
    for module in (http, weather, context):
        _BOUND[(module.__name__, 'cached_json')] = module.cached_json
        module.cached_json = cached_json
    return _BOUND


class V09Exclusions(Exclusions):
    """V0.4 GeoSphere exclusion set plus WLV Rutschung and Kärnten slide-token records (radius = extent buffer only)."""

    def __init__(self, cfg, extra_lonlat):
        super().__init__(cfg)
        if len(extra_lonlat):
            xy = np.array([PROJECT.transform(lon, lat) for lon, lat in extra_lonlat])
            self.xy = np.vstack([self.xy, xy])
            self.radii = np.concatenate([self.radii, np.full(len(xy), float(cfg['exclusion_extent_buffer_m']))])
            self.tree = cKDTree(self.xy)
        self.extra_points = int(len(extra_lonlat))
