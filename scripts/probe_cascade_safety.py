"""Run an intentionally broken safety check; success means pytest detects that injected bug.

This mutates function bytecode in this process only. No scientific file or source is modified.
python scripts/probe_cascade_safety.py table|split|guard|gate
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from preslide.cascade_pilot import context
from preslide.cascade_pilot import appearance


def main():
    mutations = {
        'table': (context.validate_table, lambda frame, columns: None,
                  'test_whole_table_preconditions'),
        'split': (context.validate_split, lambda train, held: None,
                  'test_split_rejects_one_leaking_unit_even_when_ids_differ'),
        'guard': (context.guard, lambda path: path,
                  'test_write_guard_protects_frozen_artifacts'),
        'gate': (context.selected_candidates, lambda frame, scores, fraction, seed: frame.label.eq(1).to_numpy(),
                 'test_gate_does_not_read_labels_and_has_fixed_budget'),
        'rgb': (appearance.source_rgb, lambda image, cfg: image[:, :, 4:7].transpose(2, 0, 1).astype('float32'),
                'test_appearance_uses_no_terrain_or_other_non_rgb_channels'),
    }
    name = sys.argv[1]
    function, broken, test = mutations[name]
    original = function.__code__
    try:
        function.__code__ = broken.__code__
        result = pytest.main(['-q', f'tests/test_cascade_pilot.py::{test}', '--tb=short'])
    finally:
        function.__code__ = original
    if result != 1:
        raise RuntimeError(f'Mutation {name} was not detected (pytest exit {result})')
    print(f'EXPECTED_FAILURE_CONFIRMED: {name}', flush=True)


if __name__ == '__main__':
    main()
