"""Reproduce RGB-only Austrian scores, context gate and paired metrics from cached real images."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import torch
from preslide.common import read_json, write_json
from preslide.cascade_pilot.appearance import frozen_inputs, DATA, MODELS, REPORTS, MEAN, STD
from preslide.cascade_pilot.context import guard, selected_candidates
from preslide.cascade_pilot.transfer import read_austrian, variable_ranks
from preslide.satellite_nn.models import UNetResNet18
from preslide.sources import ROOT
from preslide.v04.pipeline import load
from preslide.v05 import metrics as R


def main():
    _, cfg, _ = frozen_inputs()
    torch.set_num_threads(cfg['training']['cpu_threads'])
    result = read_json(REPORTS / 'transfer_results.json')
    predictions = load(DATA / 'transfer_predictions.parquet')
    source = pd.read_parquet(ROOT / 'data/satellite/tables/dataset.parquet').set_index('sample_id')
    frame = source.loc[predictions.sample_id].reset_index()
    net = UNetResNet18(pretrained=False)
    net.load_state_dict(torch.load(MODELS / 'appearance_unet_resnet18.pt', map_location='cpu', weights_only=True)['state_dict'])
    net.eval()
    chips = []
    for row in frame.itertuples(index=False):
        sample, reason = read_austrian(row, cfg)
        if reason:
            raise ValueError(f'Previously valid image now failed quality: {reason}')
        chips.append((sample[0] - MEAN) / STD)
    maps = []
    batch = cfg['training']['batch_size']
    with torch.inference_mode():
        for start in range(0, len(chips), batch):
            maps.extend(net(torch.from_numpy(np.stack(chips[start:start+batch]))).sigmoid().numpy()[:, 0])
    maps = np.stack(maps)
    saved = np.load(DATA / 'transfer_probability_maps.npz')
    radius, centre = cfg['transfer']['score_radius_px'], cfg['input']['size_px'] // 2
    scores = maps[:, centre-radius:centre+radius, centre-radius:centre+radius].mean(axis=(1, 2))
    context = load(DATA / 'context_oof.parquet').set_index('sample_id').loc[predictions.sample_id, 'score'].to_numpy()
    fraction = read_json(ROOT / 'config/mudslide_cascade_v01.json')['context']['candidate_budget_fraction']
    gate = selected_candidates(frame, context, fraction, 42)
    units = frame.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
    ranks = {'image_only': variable_ranks(frame, scores),
             'context_then_image': variable_ranks(frame, np.where(gate, scores, -1.0))}
    intervals = R.bootstrap(ranks, units, 2000, 71017)
    checks = {'real_source_process_is_Hangmure': frame.process_type.eq('Hangmure').all(),
              'map_ids_unchanged': bool(np.array_equal(saved['sample_id'], predictions.sample_id.to_numpy())),
              'all_image_maps_reproduced': bool(np.allclose(maps, saved['probability'], atol=1e-6, rtol=0)),
              'all_image_scores_reproduced': bool(np.allclose(scores, predictions.image_score, atol=1e-6, rtol=0)),
              'context_gate_reproduced': bool(np.array_equal(gate, predictions.context_selected)),
              'unit_count': frame.independence_unit.nunique() == result['independent_units'],
              'all_metrics_reproduced': all(np.isclose(R.summarize(r, units)[k], v, atol=1e-12)
                  for name, r in ranks.items() for k, v in result['summaries'][name].items()),
              'paired_intervals_reproduced': all(np.allclose(intervals[k]['ci95'], v['ci95'], atol=1e-12)
                  for k, v in result['uncertainty'].items())}
    checks = {k: bool(v) for k, v in checks.items()}
    out = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
           'max_probability_difference': float(np.max(np.abs(maps - saved['probability']))),
           'scope': result['scope']}
    write_json(guard(REPORTS / 'transfer_verification.json'), out)
    print(out, flush=True)
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
