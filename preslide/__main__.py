import argparse
from .audit import run_audit
from .sources import download_layer

def refuse_if_frozen(command):
    """The original pipeline/evaluation write fixed paths of the frozen baseline; their source is hash-protected (V0.2)."""
    from .baseline import BASELINE_VERSION, frozen_paths
    if frozen_paths():
        raise SystemExit(f"'{command}' would overwrite {BASELINE_VERSION} artifacts (data/processed/046074ba6f12556c, "
                         "reports/experiment, models/). Run a larger dataset as a new versioned experiment; "
                         "see reports/baseline/README.md.")

def main():
    parser = argparse.ArgumentParser(description="PreSlide: reproducible real-data audit")
    parser.add_argument("command", choices=["download", "audit", "experiment", "evaluate"])
    parser.add_argument("--limit",type=int,default=5)
    args = parser.parse_args()
    if args.command == "download":
        for name in ("geosphere_mass_movements", "geosphere_inspire_media", "geosphere_natural_hazards"):
            download_layer(name)
    elif args.command == 'audit':
        run_audit()
    elif args.command == 'experiment':
        refuse_if_frozen('experiment')
        from .pipeline import run_pipeline
        run_pipeline(args.limit)
    elif args.command == 'evaluate':
        refuse_if_frozen('evaluate')
        from .evaluation import run_evaluation
        run_evaluation()

if __name__ == "__main__":
    main()
