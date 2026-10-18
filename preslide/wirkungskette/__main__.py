import argparse
import json

parser = argparse.ArgumentParser(prog='python -m preslide.wirkungskette')
parser.add_argument("command", choices=["audit", "build", "pilot", "v02-areas", "v02-pilot", "v02-full", "v02-skadi"])
parser.add_argument('--radius-m', type=float, default=None)
args = parser.parse_args()
if args.command == 'audit':
    from .audit import run
    print(json.dumps(run(), indent=2, ensure_ascii=False))
elif args.command == 'build':
    from .build import build
    print(json.dumps(build(args.radius_m), indent=2, ensure_ascii=False, default=str))
elif args.command == 'pilot':
    from .analysis import pilot
    print(json.dumps(pilot(args.radius_m), indent=2, ensure_ascii=False, default=str))
elif args.command == 'v02-areas':
    from .gebiete import area_audit
    print(json.dumps(area_audit(), indent=2, ensure_ascii=False, default=str))
else:
    from .gebiete import run
    mode, dem = {'v02-pilot': ('pilot', 'srtm'), 'v02-full': ('full', 'srtm'), 'v02-skadi': ('full', 'skadi')}[args.command]
    print(json.dumps(run(mode, dem), indent=2, ensure_ascii=False, default=str))
