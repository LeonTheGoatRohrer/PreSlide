import argparse
import json

parser = argparse.ArgumentParser(prog='python -m preslide.wirkungskette')
parser.add_argument('command', choices=['audit', 'build', 'pilot', 'gegenprobe', 'nullreferenz'])
parser.add_argument('--limit', type=int, default=None, help='nullreferenz pilot: reference points per frame; writes nothing')
parser.add_argument('--radius-m', type=float, default=None)
args = parser.parse_args()
if args.command == 'audit':
    from .audit import run
    print(json.dumps(run(), indent=2, ensure_ascii=False))
elif args.command == 'build':
    from .build import build
    print(json.dumps(build(args.radius_m), indent=2, ensure_ascii=False, default=str))
elif args.command == 'gegenprobe':
    from .gegenprobe import run
    out = run()
    print(json.dumps({k: {kk: v[kk] for kk in ('ausgeschlossen_nach_grund', 'ereignisse', 'tabellen')} for k, v in out['sets'].items()}, indent=2, ensure_ascii=False))
elif args.command == 'nullreferenz':
    from .nullreferenz import run
    out = run(args.limit)
    print(json.dumps({'gebiet': out['gebiet'], 'referenz': out['referenz'],
                      'vergleiche': [{k: c[k] for k in ('rang', 'rahmen', 'gruppe', 'metrik', 'differenz', 'einordnung')} for c in out['vergleiche']]},
                     indent=2, ensure_ascii=False))
else:
    from .analysis import pilot
    print(json.dumps(pilot(args.radius_m), indent=2, ensure_ascii=False, default=str))
