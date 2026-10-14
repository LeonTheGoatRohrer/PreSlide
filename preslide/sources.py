"""Read-only ArcGIS retrieval with immutable response caches and provenance."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://gis.geosphere.at/maps/rest/services"
LAYERS = {
    "geosphere_natural_hazards": f"{BASE}/naturgefahren/Naturgefahren/MapServer/0",
    "geosphere_mass_movements": f"{BASE}/naturgefahren/Gravitative_Massenbewegungen/MapServer/0",
    "geosphere_inspire_media": f"{BASE}/inspire/NZ_ObservedEvent_Media/MapServer/0",
}


def cached_json(url, params=None):
    params = {"f": "json", **(params or {})}
    full_url = url + "?" + urlencode(sorted(params.items()), doseq=True)
    key = hashlib.sha256(full_url.encode()).hexdigest()
    directory = ROOT / "data/raw/http"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{key}.json"
    if path.exists():
        manifest = json.loads(path.with_suffix(".meta.json").read_text(encoding="utf-8"))
        if manifest["url"] != full_url or manifest["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise RuntimeError(f"Cache integrity failure: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise RuntimeError("curl is required (TLS certificate verification remains enabled)")
    result = subprocess.run(
        [curl, "--fail", "--silent", "--show-error", "--location", "--retry", "2",
         "--max-time", "60", full_url], capture_output=True, check=True, timeout=200,
    )
    data = json.loads(result.stdout)
    if "error" in data:
        raise RuntimeError(f"Source error: {data['error']}")
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(result.stdout)
    temporary.replace(path)
    path.with_suffix(".meta.json").write_text(json.dumps({
        "url": full_url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(result.stdout).hexdigest(),
    }, indent=2), encoding="utf-8")
    return data


def download_layer(name, batch_size=1000):
    url = LAYERS[name]
    metadata = cached_json(url)
    ids = cached_json(url + "/query", {"where": "1=1", "returnIdsOnly": "true"})
    all_ids = sorted(ids["objectIds"])
    id_field = ids["objectIdFieldName"]
    features = []
    # Small verified request before batching; all raw responses remain cached.
    batches = [all_ids[:1], all_ids[1:6]]
    batches += [all_ids[i:i+batch_size] for i in range(6, len(all_ids), batch_size)]
    for batch in batches:
        if not batch:
            continue
        response = cached_json(url + "/query", {
            "objectIds": ",".join(map(str, batch)), "outFields": "*",
            "outSR": "4326", "returnGeometry": "true",
        })
        if response.get("exceededTransferLimit"):
            raise RuntimeError("Truncated source response; reduce batch size")
        received = response["features"]
        if {x["attributes"][id_field] for x in received} != set(batch):
            raise RuntimeError("Source IDs do not match requested IDs")
        if response.get("spatialReference", {}).get("wkid") != 4326:
            raise RuntimeError("Source did not return WGS84 coordinates")
        features.extend(received)
        print(f"[{name}] {len(features)}/{len(all_ids)}", flush=True)
    if len(features) != len(all_ids):
        raise RuntimeError("Incomplete inventory")
    output = ROOT / "data/raw" / f"{name}.json"
    output.write_text(json.dumps({"source": url, "metadata": metadata,
        "spatialReference": {"wkid": 4326}, "features": features}, ensure_ascii=False), encoding="utf-8")
    return features
