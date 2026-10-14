"""Initial schema/distribution inspection, before selecting scientific thresholds."""
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preslide.sources import download_layer

if __name__ == "__main__":
    features = download_layer("geosphere_mass_movements")
    for field in ["processGroupWeb_DE", "positionalAccuracy", "resolutionScale", "Bundesland"]:
        print(field, json.dumps(Counter(f["attributes"].get(field) for f in features), ensure_ascii=False))
    recent = [f["attributes"] for f in features if (f["attributes"].get("Ereignisdatum_validFrom") or "") >= "2015"]
    print("2015+ dated:",len(recent))
    print("Recent position:",Counter(f.get("positionalAccuracy") for f in recent))
    print("Recent process:",Counter(f.get("processGroupWeb_DE") for f in recent))
    print("Date examples:", json.dumps(recent[:8],ensure_ascii=False))
