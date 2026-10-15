"""CLI for Pipeline B.  python -m preslide.satellite <stage> [--limit N] [--workers W] [--negatives ...]

Stages: eligibility -> dataset -> contact -> baseline -> discovery -> report (each stage caches; rerunning is cheap).
Added in satellite-0.2: landscape (RANDOM_LANDSCAPE hard negatives), baseline-random (with/without them),
validation (top-candidate persistence + contact sheets), review (apply written review -> statuses + report),
embeddings (Baseline C, optional torch)."""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['eligibility', 'dataset', 'contact', 'baseline', 'baseline-random', 'discovery', 'landscape',
                                      'validation', 'review', 'embeddings', 'cloud-proximity', 'report'])
    ap.add_argument('--limit', type=int, default=0, help='first N eligible positives (0 = all)')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--null-draws', type=int, default=100)
    ap.add_argument('--reverse', action='store_true', help='landscape: process events from the end (second process)')
    ap.add_argument('--negatives', choices=['controls', 'controls_plus_random_landscape'], default='controls',
                    help='discovery: training table (random-landscape variant writes *_random_landscape outputs)')
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
    elif args.stage == 'baseline-random':
        from .baseline import run_random_landscape
        r = run_random_landscape()
        print(json.dumps({k: {m: v[m]['mean'] for m in ('within_group_auc', 'positive_vs_random_auc', 'top1_vs_controls_and_random')}
                          for k, v in r['models'].items()}, indent=1))
    elif args.stage == 'discovery':
        from .discovery import run
        print(json.dumps(run(negatives=args.negatives), indent=1, default=str)[:3000])
    elif args.stage == 'landscape':
        from .landscape import run
        frame, summary = run(args.limit, args.workers, args.reverse)
        print(json.dumps(summary, indent=1, default=str))
    elif args.stage == 'validation':
        from .validation import run
        top, summary = run()
        print(json.dumps(summary, indent=1, default=str))
    elif args.stage == 'review':
        from .validation import apply_review, write_report
        top = apply_review()
        write_report(top)
        print(top['validation_status'].value_counts().to_dict())
    elif args.stage == 'embeddings':
        from .embeddings import run
        r = run()
        print(json.dumps(r['metrics'] if r else r, indent=1))
    elif args.stage == 'cloud-proximity':
        from .validation import cloud_proximity_report
        print(json.dumps(cloud_proximity_report(), indent=1))
    elif args.stage == 'report':
        from .report import write_reports
        write_reports()


if __name__ == '__main__':
    main()
