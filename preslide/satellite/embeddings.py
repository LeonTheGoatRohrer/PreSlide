"""Baseline C: frozen pretrained-encoder embeddings (torchvision ResNet-18, ImageNet weights, CPU) of the before and
after RGB chips, difference embedding, logistic regression with the same unit-held-out folds as the other baselines.

Single configuration declared in config/satellite.json before the first run; not tuned. torch is an optional
dependency (requirements-satellite-optional.txt); without it the stage records why it did not run."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..common import read_json, write_json
from .baseline import within_group_metrics, unit_weighted
from .imagery import Grid, fetch_patch, sample_dir
from .paths import SAT_DATA, SAT_REPORT, guard, config
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import GroupKFold

EMBED_C = 0.05
RGB_CLIP = 0.3
WINDOW_M = 960
UPSAMPLE = 2
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def available():
    try:
        import torch, torchvision  # noqa: F401
        return True, f'torch {torch.__version__}, torchvision {torchvision.__version__}'
    except ImportError as error:
        return False, f'torch/torchvision not installed ({error}); install requirements-satellite-optional.txt'


def rgb_chip(refl, grid, window_m=WINDOW_M):
    """(3, w, w) RGB chip of the central window: reflectance clipped to [0, RGB_CLIP], scaled to [0, 1],
    NaN -> 0, ImageNet-normalised."""
    r, c = grid.centre_pixel()
    h = int(round(window_m / grid.res / 2))
    rgb = refl[[2, 1, 0], r - h:r + h, c - h:c + h]
    rgb = np.nan_to_num(np.clip(rgb, 0, RGB_CLIP) / RGB_CLIP, nan=0.0).astype(np.float32)
    return (rgb - IMAGENET_MEAN[:, None, None]) / IMAGENET_STD[:, None, None]


def _encoder():
    import torch
    from torchvision.models import resnet18, ResNet18_Weights
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    model.fc = torch.nn.Identity()
    model.eval()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    return model


def embed_chips(model, chips):
    import torch
    x = torch.from_numpy(np.stack(chips))
    if UPSAMPLE > 1:
        x = torch.nn.functional.interpolate(x, scale_factor=UPSAMPLE, mode='bilinear', align_corners=False)
    with torch.no_grad():
        return model(x).numpy()


def _items_for(row):
    sid, eid = row['sample_id'], row['event_group_id']
    sel = read_json(sample_dir(f'{eid}_positive') / 'selection.json')
    if row['label'] == 1:
        return sel['items']['before_primary'], sel['items']['after_primary'], Grid(**sel['grid'])
    sdir = sample_dir(sid)
    # Controls' patches are cached under their own grid; the item is the group acquisition on a covering tile.
    before = sel['control_items']['before_primary'][sid]
    after = sel['control_items']['after_primary'][sid]
    meta = read_json(sdir / 'patches' / f"{before['id']}.json")
    return before, after, Grid(**meta['grid'])


def sample_embedding(model, row):
    """Cached (before, after) embeddings for one sample."""
    path = sample_dir(row['sample_id']) / 'embedding_resnet18.npz'
    if path.exists():
        z = np.load(path)
        if z['before_item'] == row['before_item'] and z['after_item'] == row['after_item']:
            return z['before'], z['after']
    before, after, grid = _items_for(row)
    rb, _, _ = fetch_patch(row['sample_id'], before, grid)
    ra, _, _ = fetch_patch(row['sample_id'], after, grid)
    e = embed_chips(model, [rgb_chip(rb, grid), rgb_chip(ra, grid)])
    np.savez(path, before=e[0], after=e[1], before_item=row['before_item'], after_item=row['after_item'])
    return e[0], e[1]


def embedding_features(frame, model):
    X = np.zeros((len(frame), 1024), dtype=np.float32)
    for i, (_, row) in enumerate(frame.iterrows()):
        eb, ea = sample_embedding(model, row)
        X[i, :512] = ea - eb
        X[i, 512:] = np.abs(ea - eb)
        if i % 100 == 0:
            print(f'embedded {i}/{len(frame)}', flush=True)
    return X


def make_embedding_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=EMBED_C, class_weight='balanced', max_iter=5000))


def cv_scores(X, frame, cfg, seed):
    groups = frame['independence_unit'].to_numpy()
    k = min(cfg['models']['cv_folds'], len(np.unique(groups)))
    rng = np.random.default_rng(seed)
    unit_ids = {u: i for i, u in enumerate(rng.permutation(np.unique(groups)))}
    g = np.array([unit_ids[u] for u in groups])
    y = frame['label'].to_numpy()
    scores = np.full(len(frame), np.nan)
    for tr, te in GroupKFold(n_splits=k).split(X, y, g):
        assert not set(groups[tr]) & set(groups[te]), 'independence unit leaked across folds'
        scores[te] = make_embedding_model().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return scores


def run(seeds=(0, 1, 2)):
    cfg = config()
    ok, note = available()
    guard(SAT_REPORT)
    out = SAT_REPORT / 'baseline_results_embedding.json'
    if not ok:
        write_json(out, {'ran': False, 'reason': note, 'config': cfg['embedding_baseline']})
        print('Baseline C skipped:', note)
        return None
    frame = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    model = _encoder()
    X = embedding_features(frame, model)
    y = frame['label'].to_numpy()
    reps = []
    for seed in seeds:
        s = cv_scores(X, frame, cfg, seed)
        wg = within_group_metrics(frame, s)
        reps.append({'roc_auc': float(roc_auc_score(y, s)), 'average_precision': float(average_precision_score(y, s)),
                     'within_group_auc': wg['within_group_auc'], 'within_group_auc_unit_weighted': unit_weighted(frame, wg['per_group_auc']),
                     'top1_rate': wg['top1_rate'], 'mean_rank': wg['mean_rank']})
    results = {'ran': True, 'environment': note, 'config': cfg['embedding_baseline'], 'C': EMBED_C, 'rgb_clip': RGB_CLIP,
               'window_m': WINDOW_M, 'upsample': UPSAMPLE, 'rows': len(frame), 'features': int(X.shape[1]),
               'metrics': {m: {'mean': float(np.mean([r[m] for r in reps])), 'per_seed': [r[m] for r in reps]} for m in reps[0]}}
    write_json(out, results)
    return results
