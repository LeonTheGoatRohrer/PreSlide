"""Distance of every sample to the nearest OSM building outline vertex and public-road vertex (config/v07.json).

  python -m preslide.v07.infrastructure distances [--limit N]

The PBF is streamed once; for each way the projected vertices (roads densified to <= step_m) update a running minimum
distance per sample, so nothing nationwide is kept in memory.
"""
import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

from ..common import write_json
from ..sources import ROOT
from ..v05.paths import sha
from .paths import V05_DATASET, V07_DATA, config as load_config, guard

PBF = V07_DATA / 'source/austria-261014.osm.pbf'
TO_31287 = Transformer.from_crs('EPSG:4326', 'EPSG:31287', always_xy=True)
STEP_M = 25.0
BASE_ROADS = ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'living_street', 'service')
ROAD_CLASSES = frozenset(BASE_ROADS) | {c + '_link' for c in BASE_ROADS}      # registered list in config/v07.json


def densify(xy: np.ndarray, step_m: float = STEP_M) -> np.ndarray:
    """Insert vertices so that consecutive vertices are at most step_m apart (xy: n x 2, metres)."""
    if len(xy) < 2:
        return xy
    out = [xy[:1]]
    for a, b in zip(xy[:-1], xy[1:]):
        n = int(np.ceil(np.hypot(*(b - a)) / step_m))
        if n > 1:
            t = np.arange(1, n + 1)[:, None] / n
            out.append(a + (b - a) * t)
        else:
            out.append(b[None, :])
    return np.vstack(out)


class RunningMinimum:
    """Minimum distance from each sample to all vertices seen so far, capped at cap_m."""

    def __init__(self, sample_xy: np.ndarray, cap_m: float):
        self.tree, self.cap = cKDTree(sample_xy), cap_m
        self.best = np.full(len(sample_xy), np.inf)
        self.buffer: list[np.ndarray] = []
        self.size = 0

    def add(self, xy: np.ndarray) -> None:
        self.buffer.append(xy)
        self.size += len(xy)
        if self.size > 400_000:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        pts = np.vstack(self.buffer)
        self.buffer, self.size = [], 0
        d, i = self.tree.query(pts, distance_upper_bound=self.cap)
        ok = np.isfinite(d)
        np.minimum.at(self.best, i[ok], d[ok])

    def result(self) -> tuple[np.ndarray, np.ndarray]:
        self.flush()
        capped = ~np.isfinite(self.best)
        return np.where(capped, self.cap, self.best), capped


def extract(sample_xy: np.ndarray, cfg: dict, limit_ways: int = 0):
    import osmium
    road_classes = ROAD_CLASSES
    cap = cfg['infrastructure']['distance_cap_m']
    roads, buildings = RunningMinimum(sample_xy, cap), RunningMinimum(sample_xy, cap)
    counts = {'road_ways': 0, 'building_ways': 0, 'ways_without_location': 0}
    fp = osmium.FileProcessor(str(PBF), osmium.osm.NODE | osmium.osm.WAY).with_locations().with_filter(osmium.filter.KeyFilter('highway', 'building'))
    n = 0
    for way in fp:
        if not way.is_way():
            continue
        n += 1
        if limit_ways and n > limit_ways:
            break
        tags = way.tags
        highway, building = tags.get('highway'), tags.get('building')
        is_road = highway in road_classes
        is_building = building is not None and building != 'no'
        if not (is_road or is_building):
            continue
        try:
            lonlat = np.array([(nd.lon, nd.lat) for nd in way.nodes])
        except osmium.InvalidLocationError:
            counts['ways_without_location'] += 1
            continue
        x, y = TO_31287.transform(lonlat[:, 0], lonlat[:, 1])
        xy = np.column_stack([x, y])
        if is_road:
            counts['road_ways'] += 1
            roads.add(densify(xy))
        else:
            counts['building_ways'] += 1
            buildings.add(xy)
    return roads.result(), buildings.result(), counts


def stage_distances(limit: int = 0) -> pd.DataFrame:
    cfg = load_config()
    data = pd.read_parquet(V05_DATASET)
    if sha(V05_DATASET) != cfg['inputs']['dataset_sha256']:
        raise RuntimeError('V0.5 dataset changed')
    source_meta = guard(V07_DATA) / 'source.json'
    if not source_meta.exists():
        write_json(source_meta, {'file': PBF.name, 'bytes': PBF.stat().st_size, 'sha256': sha(PBF), 'url': cfg['source']['url'],
                                 'retrieved_by_registered_url_at_utc': datetime.fromtimestamp(PBF.stat().st_mtime, timezone.utc).isoformat()})
    if PBF.stat().st_size != cfg['source']['size_bytes']:
        raise RuntimeError('PBF size differs from the registered file size')
    sample_xy = data[['x', 'y']].to_numpy(float)
    (road, road_cap), (bld, bld_cap), counts = extract(sample_xy, cfg, limit_ways=limit)
    out = pd.DataFrame({'sample_id': data.sample_id, 'dist_road_m': road, 'dist_building_m': bld,
                        'road_capped': road_cap, 'building_capped': bld_cap})
    out['dist_infrastructure_m'] = out[['dist_road_m', 'dist_building_m']].min(axis=1)
    name = 'infrastructure.parquet' if not limit else f'infrastructure_pilot_{limit}.parquet'
    path = V07_DATA / name
    out.to_parquet(path, index=False)
    write_json(path.with_suffix('.json'), {'sha256': sha(path), 'rows': len(out), 'config_sha256': sha(ROOT / 'config/v07.json'),
                                           'dataset_sha256': cfg['inputs']['dataset_sha256'], **counts})
    print(json.dumps(counts), out.describe().round(1).to_string(), flush=True)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['distances'])
    ap.add_argument('--limit', type=int, default=0, help='stop after N ways (code check only)')
    a = ap.parse_args()
    stage_distances(a.limit)
