import argparse

if __name__ == '__main__':
    ap = argparse.ArgumentParser(prog='python -m preslide.anfaelligkeit_at_v01')
    ap.add_argument('stage', choices=['positives', 'samples', 'context', 'infra', 'experiment', 'demo', 'report', 'web'])
    ap.add_argument('--variant', choices=['srtm', 'skadi', 'both'], default='srtm')
    ap.add_argument('--areas', type=int, default=0, help='pilot: only the N smallest evaluation areas')
    a = ap.parse_args()
    from . import pipeline
    if a.stage == 'positives':
        pipeline.stage_positives()
    elif a.stage in ('samples', 'context', 'infra'):
        getattr(pipeline, f'stage_{a.stage}')(a.variant, a.areas)
    elif a.stage == 'experiment':
        from . import experiment
        experiment.run(a.variant, a.areas)
    elif a.stage == 'demo':
        from . import demo
        demo.run()
    elif a.stage == 'report':
        from . import report
        report.run()
    elif a.stage == 'web':
        from . import web
        web.run()
