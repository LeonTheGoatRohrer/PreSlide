"""Inspect WLV's public endpoint without assuming its positions are precise."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preslide.sources import ROOT, cached_json

WLV = "https://gis.lfrz.gv.at/api/geodata/i000901/ogc/features/v1/collections/i000901:wlv_ereignisse/items"

if __name__ == "__main__":
    params = {"f": "application/geo+json", "limit": 5,
              "filter": "nameofevent LIKE 'Rutschung%'", "filter-lang": "cql-text"}
    try:
        response = cached_json(WLV, params)
        print("WLV matching records:", response.get("numberMatched"), flush=True)
        selected = response.get("features", [])
        if not all(f["properties"]["nameofevent"].startswith("Rutschung") for f in selected):
            raise ValueError("The endpoint did not apply the requested filter")
        count = response["numberMatched"]
        while len(selected) < count:
            page = cached_json(WLV, {**params, "limit": 1000, "startIndex": len(selected)})
            if not page["features"] or page["numberMatched"] != count:
                raise ValueError("Empty page or source changed during download")
            selected.extend(page["features"])
            print(f"[WLV] {len(selected)}/{count}", flush=True)
        if len(selected) != count or len({f['id'] for f in selected}) != count:
            raise ValueError("Incomplete or duplicated WLV results")
        (ROOT / "data/raw/wlv_slides.json").write_text(json.dumps({
            "source": WLV, "filter": params["filter"], "features": selected,
        }, ensure_ascii=False), encoding="utf-8")
        print("WLV landslides:", len(selected))
    except Exception as exc:
        print(type(exc).__name__, str(exc))
        raise
