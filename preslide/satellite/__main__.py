"""CLI for Pipeline B.  python -m preslide.satellite <stage> [--limit N] [--workers W]

Stages: eligibility -> dataset -> contact -> baseline -> report (each stage caches; rerunning is cheap)."""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['eligibility', 'dataset', 'contact', 'baseline', 'discovery', 'report'])
    ap.add_argument('--limit', type=int, default=0, help='first N eligible positives (0 = all)')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--null-draws', type=int, default=100)
    args = ap.parse_args()
    if args.stage == 'eligibility':
        from .dataset import run_eligibility
        frame = run_eligibility(args.limit, args.workers)
        print(frame['usable'].value_counts().to_dict(), frame['exclusion_reason'].value_counts().to_dict())
    elif args.stage == 'dataset':
        from .dataset import build_dataset
        frame = build_dataset(args.limit, args.workers)
        print(len(frame), 'rows', frame['event_group_id'].nunique(), 'complete groups')
    elif args.stage == 'contact':
        from .contact import sheets_for
        sheets_for(args.limit)
    elif args.stage == 'baseline':
        from .baseline import run
        r = run(null_draws=args.null_draws)
        print(json.dumps({k: v['within_group_auc']['mean'] for k, v in r['models'].items()}, indent=1))
        print('null p_upper', r['permutation_null']['p_upper'])
    elif args.stage == 'discovery':
        from .discovery import run
        print(json.dumps(run(), indent=1, default=str)[:3000])
    elif args.stage == 'report':
        from .report import write_reports
        write_reports()


if __name__ == '__main__':
    main()
