import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preslide.common import candidates,experiment_config
from preslide.matching import Exclusions,match_event,austria_boundary
c=experiment_config()
e=candidates()[0]
print('FIRST EVENT',e['event_id'],e['event_date'],flush=True)
d,s=match_event(e,c,Exclusions(c),austria_boundary())
print(d[['sample_id','elevation','slope','aspect','distance_to_positive_m']].to_string(index=False),flush=True)
print(s,flush=True)
