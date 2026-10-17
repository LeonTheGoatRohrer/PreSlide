"""CPU training of model A/B on Landslide4Sense RGB tiles."""
from __future__ import annotations
import time
import numpy as np
import torch
from ..common import read_json, write_json
from . import data, decisions, models, paths, register, tiles


def load_tiles(ids: list[int]) -> tuple[np.ndarray, np.ndarray]:
    x = np.empty((len(ids), 128, 128, 3), 'float32'); y = np.empty((len(ids), 128, 128), 'uint8')
    for k, i in enumerate(ids):
        x[k], y[k] = data.read_pair(i)
    return x, y


def to_tensor(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(((x - mean) / std).transpose(0, 3, 1, 2).copy())


def augment(x: torch.Tensor, y: torch.Tensor, rng: np.random.Generator):
    k = int(rng.integers(4)); x, y = torch.rot90(x, k, (-2, -1)), torch.rot90(y, k, (-2, -1))
    if rng.random() < 0.5:
        x, y = x.flip(-1), y.flip(-1)
    return x * float(1 + 0.1 * (rng.random() - 0.5) * 2), y  # weak brightness variation, mask untouched


@torch.no_grad()
def predict(net, xt: torch.Tensor, bs: int = 32) -> np.ndarray:
    net.eval()
    return np.concatenate([torch.sigmoid(net(xt[i:i + bs])).numpy()[:, 0] for i in range(0, len(xt), bs)])


def object_f1(prob: np.ndarray, y: np.ndarray, thr: float = 0.5, min_px: int = 4, iou_min: float = 0.30) -> dict:
    tp = fp = fn = 0; inter = union = 0
    for p, t in zip(prob, y):
        pm = p >= thr
        inter += int((pm & (t > 0)).sum()); union += int((pm | (t > 0)).sum())
        lp, kp = tiles.objects(p, thr, min_px); lt, kt = tiles.objects(t.astype('float32'), 0.5, min_px)
        m, up, ur = decisions.match_one_to_one([lp == i for i in kp], [lt == i for i in kt], iou_min)
        tp += len(m); fp += len(up); fn += len(ur)
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    return {'precision': prec, 'recall': rec, 'f1': 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            'pixel_iou': inter / union if union else 0.0, 'objects': {'tp': tp, 'fp': fp, 'fn': fn}}


def train_a(pilot: bool = False, overfit: int = 0) -> dict:
    cfg = read_json(paths.CONFIG); ca = cfg['model_a']
    split = register.verify() if not overfit else {'train': list(range(1, overfit + 1)), 'dev': []}
    torch.manual_seed(cfg['seeds']['model_a']); rng = np.random.default_rng(cfg['seeds']['model_a'])
    torch.set_num_threads(max(1, torch.get_num_threads()))
    ids = split['train'][:200] if pilot else split['train']
    x, y = load_tiles(ids); mean = x.mean((0, 1, 2)); std = x.std((0, 1, 2))
    xt = to_tensor(x, mean, std); yt = torch.from_numpy(y.astype('float32'))[:, None]
    dx, dy = (None, None)
    if split['dev']:
        dids = split['dev'][:100] if pilot else split['dev']
        dxn, dy = load_tiles(dids); dx = to_tensor(dxn, mean, std)
    net = models.build('a', pretrained=True)
    enc_names = ('stem', 'l1', 'l2', 'l3', 'l4')
    enc = [p for n, p in net.named_parameters() if n.split('.')[0] in enc_names]
    dec = [p for n, p in net.named_parameters() if n.split('.')[0] not in enc_names]
    last = list(net.l4.parameters())
    opt = torch.optim.AdamW([{'params': dec, 'lr': ca['lr_decoder']}, {'params': last, 'lr': ca['lr_encoder']}], weight_decay=ca['weight_decay'])
    for p in enc:
        p.requires_grad = False
    out_dir = paths.assert_writable(paths.MODELS / ('model_a_overfit' if overfit else 'model_a_pilot' if pilot else 'model_a')); out_dir.mkdir(parents=True, exist_ok=True)
    history, best, stale = [], -1.0, 0
    epochs = 3 if pilot else (150 if overfit else ca['epochs_max'])
    no_ign = torch.zeros(ca['batch_size'], 1, 128, 128, dtype=torch.bool)
    for ep in range(epochs):
        if ep == ca['freeze_encoder_epochs'] and not overfit:
            for p in last:
                p.requires_grad = True
        elif overfit and ep == 0:
            for p in last:
                p.requires_grad = True
        net.train(); order = rng.permutation(len(xt)); t0 = time.time(); losses = []
        for b in range(0, len(order) - ca['batch_size'] + 1, ca['batch_size']):
            idx = order[b:b + ca['batch_size']]
            bx, by = (xt[idx], yt[idx]) if overfit else augment(xt[idx], yt[idx], rng)
            opt.zero_grad(); loss = models.masked_loss(net(bx), by, no_ign); loss.backward(); opt.step(); losses.append(loss.item())
        rec = {'epoch': ep + 1, 'train_loss': float(np.mean(losses)), 'seconds': round(time.time() - t0, 1)}
        if dx is not None:
            rec['dev'] = object_f1(predict(net, dx), dy); score = rec['dev']['f1']
        else:
            score = -rec['train_loss']
        history.append(rec); print(rec, flush=True)
        torch.save({'state': net.state_dict(), 'mean': mean, 'std': std, 'epoch': ep + 1}, out_dir / 'last.pt')
        if score > best:
            best, stale = score, 0; torch.save({'state': net.state_dict(), 'mean': mean, 'std': std, 'epoch': ep + 1}, out_dir / 'best.pt')
        else:
            stale += 1
            if dx is not None and stale >= ca['patience']:
                break
    result = {'history': history, 'best_score': best, 'pilot': pilot, 'overfit': overfit, 'n_train': len(ids)}
    write_json(paths.assert_writable(paths.REPORTS / ('train_a_overfit.json' if overfit else 'train_a_pilot.json' if pilot else 'train_a.json')), result)
    return result
