"""Reproduce the saved RGB network's development predictions; never fits or tunes a model."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import torch
from preslide.baseline import sha
from preslide.common import read_json, write_json
from preslide.cascade_pilot.appearance import frozen_inputs, DATA, MODELS, REPORTS, MEAN, STD, binary_counts
from preslide.cascade_pilot.context import guard
from preslide.satellite_nn.models import UNetResNet18


def main():
    source, cfg, reg = frozen_inputs()
    torch.set_num_threads(cfg['training']['cpu_threads'])
    result = read_json(REPORTS / 'appearance_results.json')
    path = MODELS / 'appearance_unet_resnet18.pt'
    net = UNetResNet18(pretrained=False)
    state = torch.load(path, map_location='cpu', weights_only=True)
    net.load_state_dict(state['state_dict'])
    net.eval()
    n, batch = cfg['source']['train_count'], cfg['training']['batch_size']
    x = (source['rgb'][n:] - MEAN) / STD
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(x), batch):
            predictions.append(net(torch.from_numpy(x[start:start+batch])).sigmoid().numpy())
    probability = np.concatenate(predictions)
    saved = np.load(DATA / 'appearance_development_predictions.npz')
    metrics = binary_counts(probability, source['mask'][n:], cfg['training']['pixel_threshold'])
    checks = {'registered_code_and_input_hashes': True, 'model_hash': sha(path) == result['model_sha256'],
              'best_epoch': state['epoch'] == result['best_epoch'],
              'development_targets_unchanged': bool(np.array_equal(saved['target'], source['mask'][n:])),
              'predictions_reproduced': bool(np.allclose(probability, saved['probability'], atol=1e-6, rtol=0)),
              'pixel_metrics_reproduced': all(np.isclose(v, result['best_development'][k], atol=1e-12) for k, v in metrics.items()),
              'no_automatic_self_training': cfg['automatic_self_training'] is False}
    out = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
           'max_probability_difference': float(np.max(np.abs(probability - saved['probability']))),
           'scope': reg['evaluation_scope']}
    write_json(guard(REPORTS / 'appearance_verification.json'), out)
    print(out, flush=True)
    return 0 if out['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
