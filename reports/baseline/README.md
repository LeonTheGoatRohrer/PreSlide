# PreSlide V0.3 Baseline

Frozen 2026-10-14. Covers everything computed on dataset `046074ba6f12556c`:

| Part | Where |
|---|---|
| Original V0 experiment: frozen split, 9 models, Steiermark holdout | `reports/experiment/metrics.json`, `models/046074ba6f12556c/` |
| V0.2 development stability + diagnostics (5 × 4 grouped folds) | `reports/stability_v02/`, `data/analysis/stability_v02/` |
| V0.3 label-permutation null reference | `reports/null_v03/` |
| Event-level error analysis (new, derived from saved predictions only) | `error_analysis.md`, `event_diagnostics.csv`, `sample_scores.csv` |
| Overall verification status | `BASELINE_STATUS.md` |

The version name continues the existing scheme (V0 → V0.2 → V0.3). Nothing was renamed or retrained.

## Identity

- Dataset: 102 candidates → 60 complete groups, 300 controls, 360 samples, 20 dependence clusters, 2017-08-05 … 2026-06-13.
- Features: 4 static + 18 temporal (`BASELINE_MANIFEST.json → features`), configuration `config/experiment.json`.
- `BASELINE_MANIFEST.json` holds SHA-256 hashes of 95 files (configs, candidate snapshot, exclusion inventory, dataset, evaluation dataset, test predictions, models, all V0/V0.2/V0.3 reports, V0.2 predictions/splits), hashes of the event-ID and control-ID lists, model parameters, software versions and source-code hashes.
- `baseline_membership.json` (local only, gitignored) lists every event with its controls, t0, dependence cluster, original partition and V0.2 fold per repetition, plus all exclusions with reasons. Its hash is in the manifest.

Large artifacts are referenced by path and hash, not copied.

## Verify

```powershell
.\.venv\Scripts\python -c "from preslide.baseline import verify_manifest; print(verify_manifest())"
.\.venv\Scripts\python scripts/verify_state.py
.\.venv\Scripts\python -m pytest -q
```

`python -m preslide.baseline` regenerates the diagnostics deterministically and fails if any frozen file changed.

## Protection

- `preslide/baseline.py: assert_not_frozen()` refuses writes to any manifest path.
- `python -m preslide experiment|evaluate` refuse to run while the manifest exists: both write fixed paths of this run (`data/processed/046074ba6f12556c/`, `reports/experiment/`, `models/046074ba6f12556c/`). Their source code is additionally hash-protected by the V0.2 audit (`data/analysis/stability_v02/original_manifest.json`), so it was deliberately not edited.
- Baseline readers (`verify_state.py`, `results_bundle`, `demo`, tests) are pinned via `preslide.baseline.pointer()`, not `data/processed/latest.json`.

## Next experiment version (do not overwrite this one)

A larger dataset must get its own version (e.g. V0.4) with:

1. Its own pre-registered config file and candidate snapshot. Different inputs give a different dataset identity, so `data/processed/<new id>/` and `models/<new id>/` cannot collide with this run.
2. A versioned runner module that reuses the existing functions (`match_event`, `enrich_weather`, `validate_dataset`, `dependent_clusters`, `grouped_split`, `make_model`, `metrics`) but writes reports to `reports/experiments/<new id>/`. The baseline `pipeline.py`/`evaluation.py` stay untouched.
3. Frozen thresholds and models before any new test data is scored. The existing test and Steiermark results are already seen and cannot be used for selection.

Under the frozen V0 quality criteria the source has exactly 102 candidates, and all are in this baseline. More events require a deliberate, documented change of inclusion criteria or a new source. See `BASELINE_STATUS.md`.
