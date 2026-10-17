"""hazard_v01 feasibility audit: reference counts only, no model, no scoring.

Reads the frozen V0.4 dataset/partition and the raw GeoSphere inventory read-only.
Usage: python scripts/hazard_v01_audit.py --data-root <checkout with data/> --out reports/hazard_v01/feasibility.json
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

NEIGHBOUR_RADIUS_M = 5000.0
UTM33N = 32633  # Austria spans UTM 32/33; used only for a ~5 km neighbour count (error << radius)


def neighbour_table(data_root: Path) -> pd.DataFrame:
    df = pd.read_parquet(data_root / "data/v04/run_c6d67a854ba7/dataset.parquet")
    pos = df[df.label == 1].drop_duplicates("event_group_id")
    part = pd.DataFrame(json.loads((data_root / "data/v04/partition/partition.json").read_text(encoding="utf-8")))
    m = pos[["event_group_id", "longitude", "latitude", "process_type", "source_position_upper_m"]].merge(
        part[["event_group_id", "temporal_episode", "independence_unit", "partition"]], on="event_group_id")
    m["x"], m["y"] = Transformer.from_crs(4326, UTM33N, always_xy=True).transform(m.longitude.values, m.latitude.values)
    n = np.zeros(len(m), dtype=int)
    for _, g in m.groupby("temporal_episode"):
        xy = g[["x", "y"]].to_numpy()
        d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
        np.fill_diagonal(d, np.inf)
        n[m.index.get_indexer(g.index)] = (d <= NEIGHBOUR_RADIUS_M).sum(axis=1)
    m["n_other_events_5km_same_episode"] = n
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m = neighbour_table(a.data_root)
    q = m[m.n_other_events_5km_same_episode > 0]
    big = q.groupby("independence_unit").size().sort_values(ascending=False)
    inv = json.loads((a.data_root / "data/raw/geosphere_natural_hazards.json").read_text(encoding="utf-8"))["features"]
    out = {
        "scope": "reference audit only; no model fitted, nothing scored",
        "positives": len(m),
        "process_type": m.process_type.value_counts().to_dict(),
        "position_upper_m": {str(k): int(v) for k, v in m.source_position_upper_m.value_counts().items()},
        "independence_units": int(m.independence_unit.nunique()),
        "temporal_episodes": int(m.temporal_episode.nunique()),
        "queries_with_neighbour_5km": int(len(q)),
        "queries_without_neighbour_5km": int(len(m) - len(q)),
        "units_with_neighbour_queries": int(big.size),
        "largest_unit_share_of_neighbour_queries": round(float(big.iloc[0] / len(q)), 3),
        "by_partition": {
            p: {"queries": int(len(g)), "with_neighbour": int((g.n_other_events_5km_same_episode > 0).sum()),
                "units": int(g.independence_unit.nunique()),
                "units_with_neighbour": int(g[g.n_other_events_5km_same_episode > 0].independence_unit.nunique())}
            for p, g in m.groupby("partition")},
        "inventory_geometry_types": dict(Counter(tuple(sorted(f.get("geometry", {}).keys())) .__repr__() for f in inv)),
        "inventory_has_initiation_or_deposit_field": any(
            any(s in k.lower() for s in ("anriss", "ablager", "runout", "flaech", "area", "volum")) for k in inv[0]["attributes"]),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
