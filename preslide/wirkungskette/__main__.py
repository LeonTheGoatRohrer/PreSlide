import argparse
import json

parser = argparse.ArgumentParser(prog='python -m preslide.wirkungskette')
parser.add_argument("command", choices=["audit", "build", "pilot", "gt-areas", "gt-pilot", "gt-full", "gt-skadi"])
parser.add_argument('--radius-m', type=float, default=None)
parser.add_argument('--gebiet', default='stanz')
args = parser.parse_args()
if args.command == 'audit':
    from .audit import run
    print(json.dumps(run(), indent=2, ensure_ascii=False))
elif args.command == 'build':
    from .build import build
    print(json.dumps(build(args.radius_m, args.gebiet), indent=2, ensure_ascii=False, default=str))
elif args.command == 'pilot':
    from .analysis import pilot
    print(json.dumps(pilot(args.radius_m), indent=2, ensure_ascii=False, default=str))
elif args.command == 'gt-areas':
    from .gebiete import area_audit
    print(json.dumps(area_audit(), indent=2, ensure_ascii=False, default=str))
else:
    from .gebiete import run
    mode, dem = {'gt-pilot': ('pilot', 'srtm'), 'gt-full': ('full', 'srtm'), 'gt-skadi': ('full', 'skadi')}[args.command]
    print(json.dumps(run(mode, dem), indent=2, ensure_ascii=False, default=str))
