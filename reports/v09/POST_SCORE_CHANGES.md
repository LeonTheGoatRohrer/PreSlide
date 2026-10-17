# V0.9 changes after scoring

The test was scored once at 2026-10-15T13:51 UTC (`test_results.json`) with the code hashed in `FREEZE.json`.
Afterwards only the following non-functional edits were made, so that the CI lint step (ruff, pyflakes rules) passes:

* `preslide/v09/experiment.py`: removed the unused import `numpy as np`.
* `preslide/v09/pipeline.py`: removed the unused import `parse_ktn_day`.
* `preslide/v09/report.py`: removed the unused import `json`.

No data, model, unit, audit or result file changed. `scripts/verify_v09.py` re-scored all 18 models with the edited code
and reproduced every stored prediction exactly (maximum difference 0.0, `verification.json` PASS). The code hashes in
`FREEZE.json` therefore refer to the files before these three import removals.
