import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preslide.sources import ROOT, cached_json
event = json.loads((ROOT/'data/interim/quality_candidates_pending_source_clearance.json').read_text(encoding='utf-8'))[0]
print(event['event_id'], event['latitude'], event['longitude'],event['event_date'])
result = cached_json('https://dataset.api.hub.geosphere.at/v1/timeseries/historical/inca-v1-1h-1km', {
    'parameters':'RR,T2M','start':'2022-08-01T00:00','end':'2022-08-02T00:00',
    'lat_lon':f"{event['latitude']},{event['longitude']}", 'output_format':'geojson'})
print(json.dumps(result,ensure_ascii=False)[:6000])
