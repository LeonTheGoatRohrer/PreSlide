import argparse
import json

parser = argparse.ArgumentParser(prog='python -m preslide.wirkungskette')
parser.add_argument('command', choices=['audit', 'build', 'pilot'])
parser.add_argument('--radius-m', type=float, default=None)
args = parser.parse_args()
if args.command == 'audit':
    from .audit import run
    print(json.dumps(run(), indent=2, ensure_ascii=False))
elif args.command == 'build':
    from .build import build
    print(json.dumps(build(args.radius_m), indent=2, ensure_ascii=False, default=str))
else:
    from .analysis import pilot
    print(json.dumps(pilot(args.radius_m), indent=2, ensure_ascii=False, default=str))
