"""Allowlist-only package: code, docs and aggregate results, never raw records."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def allowed_files():
    result=[]
    result.extend(ROOT.glob('*.md'))
    result.extend([ROOT/'.gitignore',ROOT/'requirements-lock.txt'])
    for folder,pattern in [('preslide','*.py'),('tests','*.py'),('scripts','*.py'),('scripts','*.ps1'),('config','*.json')]:
        result.extend((ROOT/folder).glob(pattern))
    for name in ['package.json','package-lock.json','index.html','vite.config.js']:
        result.append(ROOT/'frontend'/name)
    result.extend((ROOT/'frontend/src').glob('*'))
    for directory in ['reports/experiment','reports/pilot']:
        result.extend((ROOT/directory).glob('*.json'))
        result.extend((ROOT/directory).glob('*.md'))
        result.extend((ROOT/directory).glob('*.png'))
    result.extend([ROOT/'reports/dataset_report/initial_audit.json',ROOT/'reports/dataset_report/initial_audit.md'])
    # V0.2 aggregate-only allowlist. Event-level CSVs and all local checkpoints are excluded.
    stability=ROOT/'reports/stability_v02'
    for pattern in ['*.md','*.png','*.svg']:
        result.extend(stability.glob(pattern))
    for name in ['public_summary.json','verification.json','pipeline_audit.json','weather_summary.json',
                 'stability_metrics.csv','fold_metrics.csv','performance_deltas.csv','delta_summary.csv',
                 'event_consistency.csv','weather_by_feature.csv','weather_by_state.csv','weather_by_year.csv',
                 'weather_by_distance.csv','learning_curve.csv','learning_curve_folds.csv','feature_stability.csv',
                 'feature_importance_folds.csv','feature_importance_repetitions.csv','storm_sensitivity.csv',
                 'storm_deltas.csv','storm_cluster_sizes.csv','event_date_size_distribution.csv',
                 'matching_correlations.csv','position_uncertainty.csv','position_offset_summary.csv',
                 'position_weather_differences.csv','weather_window_ablation.csv','interaction_metrics.csv',
                 'paired_bootstrap.csv','feature_quality.csv']:
        result.append(stability/name)
    return sorted({p for p in result if p.is_file()})

def package():
    output=ROOT/'deliverables/preslide-v0-code-and-aggregate-results.zip'
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in allowed_files():
            relative=path.relative_to(ROOT)
            if relative.parts[0] in {'data','models','.venv','node_modules'}:
                raise RuntimeError('Raw/local artifacts must not enter deliverable')
            archive.write(path,relative.as_posix())
    print(output)
    return output

if __name__=='__main__':package()
