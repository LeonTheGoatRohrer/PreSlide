"""Entry point for susceptibility_v02 stages; safe under `python -I` (isolated mode, no cwd on sys.path).

python -I scripts/run_susceptibility_v02.py gsi_fetch|gsi_inspect|shakemap <dataset>|pga <dataset> [--limit N]
python -I scripts/run_susceptibility_v02.py sensitivity
python -I scripts/run_susceptibility_v02.py terrain_fetch|terrain|terrain_check|terrain_compare <dataset> [--limit N]
python -I scripts/run_susceptibility_v02.py sample|sample_verify <dataset> [--limit N]
python -I scripts/run_susceptibility_v02.py phase4 [--pilot]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    if sys.argv[1:2] == ['sensitivity']:
        from preslide.susceptibility.v02_sensitivity import main
        sys.argv.pop(1)
    elif sys.argv[1:2] == ['phase4']:
        from preslide.susceptibility.v02_evaluate import main
        sys.argv.pop(1)
    elif sys.argv[1:2] and sys.argv[1].startswith('sample'):
        from preslide.susceptibility.v02_sampling import main
    elif sys.argv[1:2] and sys.argv[1].startswith('terrain'):
        from preslide.susceptibility.v02_terrain import main
    else:
        from preslide.susceptibility.v02_phase1 import main
    main()
