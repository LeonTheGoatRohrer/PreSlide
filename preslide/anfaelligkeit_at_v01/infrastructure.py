"""Exact nearest OSM building-vertex / public-road-vertex distance per sample (reporting-bias control only).

Same OSM definitions as V0.7 (preslide.v07.infrastructure: ROAD_CLASSES, buildings with any 'building' tag except 'no',
roads densified to <= 25 m, cap 5000 m). The V0.7 accumulator assigns each OSM vertex only to its single nearest
sample; a sample whose nearest vertex is even nearer to another sample is then never updated and its distance is
overestimated (up to the cap). Here every buffered chunk of vertices gets its own KD-tree and every sample queries it,
so the running minimum is the exact nearest-vertex distance regardless of how close samples lie to each other.
"""
import numpy as np
from scipy.spatial import cKDTree

from ..v07.infrastructure import PBF, ROAD_CLASSES, TO_31287, densify


class NearestVertex:
    """Exact minimum distance from every sample to all vertices added so far, capped at cap_m."""

    def __init__(self, sample_xy: np.ndarray, cap_m: float, chunk: int = 400_000):
        self.samples, self.cap, self.chunk = np.asarray(sample_xy, float), float(cap_m), chunk
        self.best = np.full(len(self.samples), np.inf)
        self.buffer: list[np.ndarray] = []
        self.size = 0

    def add(self, xy: np.ndarray) -> None:
        self.buffer.append(xy)
        self.size += len(xy)
        if self.size > self.chunk:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return
        tree = cKDTree(np.vstack(self.buffer))
        self.buffer, self.size = [], 0
        d, _ = tree.query(self.samples, k=1, distance_upper_bound=self.cap)
        self.best = np.minimum(self.best, d)

    def result(self) -> tuple[np.ndarray, np.ndarray]:
        self.flush()
        capped = ~np.isfinite(self.best)
        return np.where(capped, self.cap, self.best), capped


def extract(sample_xy: np.ndarray, cap_m: float):
    import osmium
    roads, buildings = NearestVertex(sample_xy, cap_m), NearestVertex(sample_xy, cap_m)
    counts = {'road_ways': 0, 'building_ways': 0, 'ways_without_location': 0}
    fp = osmium.FileProcessor(str(PBF), osmium.osm.NODE | osmium.osm.WAY).with_locations().with_filter(osmium.filter.KeyFilter('highway', 'building'))
    for way in fp:
        if not way.is_way():
            continue
        highway, building = way.tags.get('highway'), way.tags.get('building')
        is_road = highway in ROAD_CLASSES
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
