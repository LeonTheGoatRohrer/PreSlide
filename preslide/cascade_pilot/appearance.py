"""Real RGB/mask training pilot. Development patches are NOT independent geographic test units.

python -m preslide.cascade_pilot.appearance prepare|register|train
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from ..baseline import sha
from ..common import read_json, write_json
from ..sources import ROOT
from ..satellite_nn.models import UNetResNet18, masked_loss
from .archive import arrays, cache_masks
from .context import DATA, MODELS, REPORTS, guard

CONFIG = ROOT / 'config/mudslide_appearance_pilot_v01.json'
REGISTRATION = REPORTS / 'APPEARANCE_REGISTRATION.json'
MEAN = np.array([0.485, 0.456, 0.406], np.float32)[:, None, None]
STD = np.array([0.229, 0.224, 0.225], np.float32)[:, None, None]


def stretch(rgb: np.ndarray, percentiles: list[float], minimum_range: float) -> np.ndarray:
    """Same predeclared input transform in both domains; no test-label/statistics fitting."""
    rgb = np.asarray(rgb, dtype=np.float32)
    if rgb.shape != (3, 128, 128) or not np.isfinite(rgb).all():
        raise ValueError('RGB must be finite with shape 3 x 128 x 128')
    lo, hi = np.percentile(rgb, percentiles, axis=(1, 2))
    if np.any(hi - lo < minimum_range):
        raise ValueError('Flat/invalid image channel; do not silently normalise')
    return np.clip((rgb - lo[:, None, None]) / (hi - lo)[:, None, None], 0, 1).astype(np.float32)


def binary_counts(prob: np.ndarray, target: np.ndarray, threshold: float) -> dict:
    if prob.shape != target.shape or not np.isfinite(prob).all():
        raise ValueError('Invalid prediction or mask shape')
    pred, truth = prob >= threshold, target.astype(bool)
    tp, fp, fn = int((pred & truth).sum()), int((pred & ~truth).sum()), int((~pred & truth).sum())
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': tp / max(tp + fp, 1),
            'recall': tp / max(tp + fn, 1), 'dice': 2 * tp / max(2 * tp + fp + fn, 1),
            'iou': tp / max(tp + fp + fn, 1)}


def source_rgb(image: np.ndarray, cfg: dict) -> np.ndarray:
    """Select exactly the source RGB bands; terrain/other bands never enter the network."""
    if image.shape != (128, 128, 14):
        raise ValueError('Unexpected source channel schema')
    inp = cfg['input']
    return stretch(image[:, :, cfg['source']['rgb_indices']].transpose(2, 0, 1),
                   inp['per_image_percentile'], inp['minimum_channel_range'])


def prepare() -> dict:
    cfg = read_json(CONFIG)
    s, inp = cfg['source'], cfg['input']
    ids = np.random.default_rng(cfg['split']['seed']).permutation(np.arange(1, s['image_count'] + 1))[
        :s['train_count'] + s['development_count']].tolist()
    cache_masks()

    def get(i):
        x, y = arrays(i)
        rgb = source_rgb(x, cfg)
        return rgb, y.astype(np.float32)

    # Fail-fast stages reuse the CRC-verified raw member caches.
    for limit in (1, 5, 20):
        for sample_id in ids[:limit]:
            get(sample_id)
        print(f'RGB/mask admission {limit}: PASS', flush=True)
    xs, ys = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k, (x, y) in enumerate(pool.map(get, ids), 1):
            xs.append(x)
            ys.append(y)
            if k % 20 == 0:
                print(f'Prepared {k}/{len(ids)} real image/mask pairs', flush=True)
    x, y = np.stack(xs), np.stack(ys)[:, None]
    # Exact duplicate images cannot cross the split; spatial overlap remains unknown.
    import hashlib
    hashes = [hashlib.sha256(a.tobytes()).hexdigest() for a in x]
    if set(hashes[:s['train_count']]) & set(hashes[s['train_count']:]):
        raise ValueError('Duplicate RGB image crosses training/development split')
    path = guard(DATA / 'appearance_rgb_masks.npz')
    np.savez_compressed(path, rgb=x, mask=y, sample_ids=np.asarray(ids))
    meta = {'sha256': sha(path), 'config_sha256': sha(CONFIG), 'train_count': s['train_count'],
            'development_count': s['development_count'], 'positive_pixels': int(y.sum()),
            'spatial_independence_known': False, 'rgb_image_hashes': hashes}
    write_json(path.with_suffix('.json'), meta)
    # Visual QA uses only training examples.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 4, figsize=(10, 8))
    for j, row in enumerate(axes):
        for col, kind in enumerate(('image', 'mask', 'image', 'mask')):
            i = j * 2 + col // 2
            row[col].imshow(x[i].transpose(1, 2, 0) if kind == 'image' else y[i, 0],
                            cmap=None if kind == 'image' else 'gray', vmin=0, vmax=1)
            row[col].set_title(f'{ids[i]} {kind}')
            row[col].axis('off')
    fig.tight_layout()
    fig.savefig(guard(DATA / 'appearance_training_contact_sheet.png'), dpi=120)
    plt.close(fig)
    print(meta | {'rgb_image_hashes': 'stored locally'}, flush=True)
    return meta


def register() -> dict:
    if REGISTRATION.exists():
        raise FileExistsError('Appearance design already registered')
    data = DATA / 'appearance_rgb_masks.npz'
    meta = read_json(data.with_suffix('.json'))
    if sha(data) != meta['sha256'] or sha(CONFIG) != meta['config_sha256']:
        raise ValueError('Prepared RGB dataset/config changed')
    weights = ROOT.home() / '.cache/torch/hub/checkpoints/resnet18-f37072fd.pth'
    if not weights.exists():
        raise FileNotFoundError('Audited cached ImageNet encoder weights missing')
    code = [ROOT / 'preslide/satellite_nn/models.py', ROOT / 'preslide/cascade_pilot/appearance.py']
    out = {'registered_at_utc': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha(CONFIG),
           'dataset_sha256': sha(data), 'code': {p.relative_to(ROOT).as_posix(): sha(p) for p in code},
           'imagenet_encoder_sha256': sha(weights), 'dataset': {k: v for k, v in meta.items() if k != 'rgb_image_hashes'},
           'target': 'Visible general-landslide mask, no subtype claim',
           'evaluation_scope': 'Technical development validation; source spatial units unknown. Austrian Hangmure transfer is separate.'}
    write_json(guard(REGISTRATION), out)
    return out


def frozen_inputs():
    reg, cfg = read_json(REGISTRATION), read_json(CONFIG)
    path = DATA / 'appearance_rgb_masks.npz'
    if sha(CONFIG) != reg['config_sha256'] or sha(path) != reg['dataset_sha256']:
        raise ValueError('Registered appearance input/config changed')
    if any(sha(ROOT / p) != h for p, h in reg['code'].items()):
        raise ValueError('Registered training implementation changed')
    return np.load(path), cfg, reg


def train() -> dict:
    if (REPORTS / 'appearance_results.json').exists():
        raise FileExistsError('Training pilot complete; do not tune it silently')
    data, cfg, reg = frozen_inputs()
    c, s = cfg['training'], cfg['source']
    torch.set_num_threads(c['cpu_threads'])
    torch.manual_seed(c['seed'])
    torch.use_deterministic_algorithms(True)
    x = (data['rgb'] - MEAN) / STD
    y = data['mask']
    n = s['train_count']
    tr = TensorDataset(torch.from_numpy(x[:n]), torch.from_numpy(y[:n]))
    va = DataLoader(TensorDataset(torch.from_numpy(x[n:]), torch.from_numpy(y[n:])), batch_size=c['batch_size'])
    generator = torch.Generator().manual_seed(c['seed'])
    loader = DataLoader(tr, batch_size=c['batch_size'], shuffle=True, generator=generator, num_workers=0)
    net = UNetResNet18(pretrained=True)
    encoder = [net.stem, net.l1, net.l2, net.l3, net.l4]
    for module in encoder:
        for param in module.parameters():
            param.requires_grad = False
    decoder = list(net.u1.parameters()) + list(net.u2.parameters()) + list(net.u3.parameters()) + list(net.u4.parameters()) + list(net.head.parameters())
    optimizer = torch.optim.AdamW(decoder, lr=c['lr_decoder'], weight_decay=c['weight_decay'])
    history, best, started = [], -1.0, time.perf_counter()
    out_path = guard(MODELS / 'appearance_unet_resnet18.pt')
    MODELS.mkdir(parents=True, exist_ok=True)
    for epoch in range(c['max_epochs']):
        if epoch == c['freeze_encoder_epochs']:
            for param in net.l4.parameters():
                param.requires_grad = True
            optimizer.add_param_group({'params': net.l4.parameters(), 'lr': c['lr_encoder']})
        net.train()
        # Frozen BatchNorm statistics must not adapt to validation or drift while the encoder is frozen.
        for module in encoder[:-1]:
            module.eval()
        if epoch < c['freeze_encoder_epochs']:
            net.l4.eval()
        loss_sum = 0.0
        for xb, yb in loader:
            if c['augment_rot90_flips']:
                k = int(torch.randint(4, (1,)))
                xb, yb = torch.rot90(xb, k, (-2, -1)), torch.rot90(yb, k, (-2, -1))
                if bool(torch.randint(2, (1,))):
                    xb, yb = xb.flip(-1), yb.flip(-1)
            optimizer.zero_grad()
            logits = net(xb)
            loss = masked_loss(logits, yb, torch.zeros_like(yb, dtype=torch.bool))
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite supervised loss')
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach()) * len(xb)
        net.eval()
        probs = []
        with torch.inference_mode():
            for xb, _ in va:
                probs.append(net(xb).sigmoid().numpy())
        p = np.concatenate(probs)
        metrics = binary_counts(p, y[n:], c['pixel_threshold'])
        record = {'epoch': epoch + 1, 'train_loss': loss_sum / n, 'development': metrics,
                  'elapsed_seconds': time.perf_counter() - started}
        history.append(record)
        print(record, flush=True)
        if metrics['dice'] > best:
            best = metrics['dice']
            torch.save({'state_dict': net.state_dict(), 'epoch': epoch + 1, 'config_sha256': sha(CONFIG),
                        'registration_sha256': sha(REGISTRATION)}, out_path)
            np.savez_compressed(guard(DATA / 'appearance_development_predictions.npz'), probability=p, target=y[n:])
    result = {'version': cfg['version'], 'target': reg['target'], 'scope': reg['evaluation_scope'],
              'history': history, 'best_epoch': max(history, key=lambda r: r['development']['dice'])['epoch'],
              'best_development': max(history, key=lambda r: r['development']['dice'])['development'],
              'independent_source_units': None, 'train_images': n, 'development_images': len(y) - n,
              'confidence_intervals': 'Not claimed: independent source units unavailable; descriptive development metrics only',
              'null_reference': 'Always-background has zero recall/Dice on these positive masks',
              'model_sha256': sha(out_path), 'trained_seconds': time.perf_counter() - started,
              'limitations': ['General landslides, not exclusively mudslides', 'RGB may still encode roads and reporting bias',
                              'Fixed per-image contrast stretch discards absolute radiometry',
                              'No calibrated event probabilities or proof of new Austrian discoveries',
                              'No pseudo-labels or automatic self-training used']}
    write_json(guard(REPORTS / 'appearance_results.json'), result)
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage', choices=['prepare', 'register', 'train'])
    stage = parser.parse_args().stage
    result = {'prepare': prepare, 'register': register, 'train': train}[stage]()
    print({k: v for k, v in result.items() if k in ('best_epoch', 'best_development', 'train_images', 'development_images')}, flush=True)


if __name__ == '__main__':
    main()
