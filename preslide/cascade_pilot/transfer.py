"""Exploratory transfer on inventory-labelled Hangmuren and matched pseudo-negatives.

No Austrian image is used for training. Scores are not calibrated probabilities.
python -m preslide.cascade_pilot.transfer
"""
from __future__ import annotations

from collections import Counter
import numpy as np
import pandas as pd
import rasterio
import torch

from ..baseline import sha
from ..common import read_json, write_json
from ..sources import ROOT
from ..satellite_nn import tiles
from ..satellite_nn.models import UNetResNet18
from ..v04.pipeline import load, save
from ..v05 import metrics as R
from .appearance import CONFIG, DATA, MODELS, REPORTS, frozen_inputs, stretch, MEAN, STD
from .context import guard, selected_candidates


def read_austrian(row, cfg):
    """Load audited reflectance caches only. Coordinates identify the crop, never enter the net."""
    base = ROOT / 'data/satellite/samples' / row.sample_id / 'patches'
    meta = read_json(base / f'{row.after_item}.json')
    rp, sp = base / f'{row.after_item}_refl.tif', base / f'{row.after_item}_scl.tif'
    if sha(rp) != meta['sha256_refl'] or sha(sp) != meta['sha256_scl']:
        raise ValueError('Austrian raster cache hash mismatch')
    if pd.Timestamp(row.after_datetime).date() <= pd.Timestamp(row.event_day).date():
        raise ValueError('Detection image must be after the recorded event day')
    with rasterio.open(rp) as f:
        if f.count != 6 or f.res != (10, 10) or f.crs.to_epsg() not in (32632, 32633):
            raise ValueError('Unexpected cached raster schema/CRS/resolution')
        rgb = f.read([3, 2, 1])
    with rasterio.open(sp) as f:
        scl = f.read(1)
    invalid = tiles.invalid_mask(scl, buffer_m=cfg['transfer']['cloud_buffer_m'], pixel_m=10)
    size = cfg['transfer']['candidate_size_px']
    r, c = (rgb.shape[1] - size) // 2, (rgb.shape[2] - size) // 2
    chip, bad = rgb[:, r:r+size, c:c+size], invalid[r:r+size, c:c+size]
    if not tiles.assessable(bad, cfg['transfer']['minimum_valid_fraction']):
        return None, 'cloud_snow_or_invalid_candidate_window'
    if not np.isfinite(chip).all():
        return None, 'nonfinite_RGB_candidate_window'
    inp = cfg['input']
    return (stretch(chip, inp['per_image_percentile'], inp['minimum_channel_range']), bad, rgb, invalid), None


def variable_ranks(frame, scores):
    f = frame[['event_group_id', 'label']].assign(score=np.asarray(scores))
    if not np.isfinite(f.score).all():
        raise ValueError('Nonfinite transfer scores')
    out = []
    for gid, group in f.groupby('event_group_id'):
        p, n = group[group.label.eq(1)].score, group[group.label.eq(0)].score
        if len(p) != 1 or len(n) < 4:
            raise ValueError('Incomplete Austrian evaluation group')
        out.append({'event_group_id': gid, **R.rank_metrics(p.iloc[0], n.to_numpy())})
    return pd.DataFrame(out)


def run():
    if (REPORTS / 'transfer_results.json').exists():
        raise FileExistsError('Transfer pilot already evaluated; create a new version for changes')
    _, cfg, reg = frozen_inputs()
    torch.set_num_threads(cfg['training']['cpu_threads'])
    model_path = MODELS / 'appearance_unet_resnet18.pt'
    result = read_json(REPORTS / 'appearance_results.json')
    if sha(model_path) != result['model_sha256']:
        raise ValueError('Appearance model changed after training')
    net = UNetResNet18(pretrained=False)
    net.load_state_dict(torch.load(model_path, map_location='cpu', weights_only=True)['state_dict'])
    net.eval()
    frame = pd.read_parquet(ROOT / 'data/satellite/tables/dataset.parquet')
    frame = frame[frame.process_type.isin(cfg['transfer']['accepted_process_types'])].copy()
    reasons, accepted, chips = Counter(), [], []
    for gid, group in frame.groupby('event_group_id', sort=True):
        prepared = []
        for row in group.itertuples(index=False):
            sample, reason = read_austrian(row, cfg)
            if reason:
                reasons[reason] += 1
                break
            prepared.append(sample)
        else:
            if group.after_datetime.nunique() != 1:
                raise ValueError('Controls do not share the event acquisition')
            accepted.append(group)
            chips.extend(prepared)
            continue
        reasons['whole_event_group_excluded'] += 1
    if not accepted:
        raise ValueError('No complete, assessable Austrian Hangmure group')
    data = pd.concat(accepted, ignore_index=True)
    probabilities = []
    batch = cfg['training']['batch_size']
    with torch.inference_mode():
        for start in range(0, len(chips), batch):
            x = np.stack([(chip[0] - MEAN) / STD for chip in chips[start:start+batch]])
            probabilities.extend(net(torch.from_numpy(x)).sigmoid().numpy()[:, 0])
    radius = cfg['transfer']['score_radius_px']
    centre = cfg['input']['size_px'] // 2
    score = np.asarray([p[centre-radius:centre+radius, centre-radius:centre+radius].mean() for p in probabilities])
    context = load(DATA / 'context_oof.parquet').set_index('sample_id')
    context_score = context.loc[data.sample_id, 'score'].to_numpy()
    budget = read_json(ROOT / 'config/mudslide_cascade_v01.json')['context']['candidate_budget_fraction']
    selected = selected_candidates(data, context_score, budget, 42)
    cascade_score = np.where(selected, score, -1.0)
    ranks = {'image_only': variable_ranks(data, score), 'context_then_image': variable_ranks(data, cascade_score)}
    units = data.drop_duplicates('event_group_id').set_index('event_group_id').independence_unit
    summaries = {k: R.summarize(v, units) for k, v in ranks.items()}
    uncertainty = R.bootstrap(ranks, units, 2000, 71017)
    positive_selected = pd.Series(selected, index=data.index)[data.label.eq(1)]
    predictions = data[['sample_id', 'event_group_id', 'independence_unit', 'label']].assign(
        image_score=score, context_score=context_score, context_selected=selected, cascade_score=cascade_score)
    save(predictions, guard(DATA / 'transfer_predictions.parquet'), {'appearance_model_sha256': sha(model_path)})
    np.savez_compressed(guard(DATA / 'transfer_probability_maps.npz'), probability=np.stack(probabilities), sample_id=data.sample_id.to_numpy(dtype=str))
    # Local-only visual inspection: source imagery must not enter public result packages.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    examples = data[data.label.eq(1)].index[:cfg['transfer']['dense_examples']]
    dense = []
    for idx in examples:
        rgb, invalid = chips[idx][2], chips[idx][3]
        if not np.isfinite(rgb).all():
            dense.append({'status': 'UNASSESSABLE', 'reason': 'nonfinite_RGB_outside_valid_candidate_window'})
            continue
        origins = tiles.tile_origins(rgb.shape[1], rgb.shape[2], size_px=128, stride_px=cfg['transfer']['stride_px'])
        tile_probs = []
        with torch.inference_mode():
            for r, c in origins:
                raw = rgb[:, r:r+128, c:c+128]
                if not np.isfinite(raw).all():
                    raise ValueError('Dense pilot contains invalid RGB; choose another registered source')
                inp = cfg['input']
                x = (stretch(raw, inp['per_image_percentile'], inp['minimum_channel_range']) - MEAN) / STD
                tile_probs.append(net(torch.from_numpy(x[None])).sigmoid().numpy()[0, 0])
        mosaic = tiles.mosaic(rgb.shape[1:], origins, tile_probs)
        lab, objects = tiles.objects(mosaic, cfg['training']['pixel_threshold'], cfg['transfer']['minimum_object_px'], invalid)
        kept_mask = np.isin(lab, objects)
        fig, ax = plt.subplots(1, 3, figsize=(12, 4))
        for a in ax:
            a.axis('off')
        # Fixed whole-patch stretch for display only; not an extra model input.
        lo, hi = np.percentile(rgb, [1, 99], axis=(1, 2))
        display = np.clip((rgb - lo[:, None, None]) / np.maximum(hi-lo, 1e-6)[:, None, None], 0, 1).transpose(1, 2, 0)
        ax[0].imshow(display); ax[0].set_title('Einzelaufnahme (RGB)')
        ax[1].imshow(mosaic, vmin=0, vmax=1, cmap='magma'); ax[1].set_title('Unkalibrierter Modellscore')
        ax[2].imshow(display); ax[2].imshow(np.ma.masked_where(~kept_mask, kept_mask), cmap='autumn', alpha=0.55)
        ax[2].set_title(f'{len(objects)} ungeprüfte Vorschläge')
        fig.tight_layout()
        filename = f'dense_example_{len(dense)+1}.png'
        fig.savefig(guard(DATA / filename), dpi=130)
        plt.close(fig)
        dense.append({'image': filename, 'tiles': len(origins), 'unverified_objects': len(objects),
                      'context_selected_positive': bool(selected[idx])})
    out = {'scope': 'Exploratory transfer; inventory points and pseudo-negative controls are weak image labels, not verified scars',
           'target_process': 'Hangmure (source classification)', 'events': int(data.event_group_id.nunique()),
           'independent_units': int(data.independence_unit.nunique()), 'samples': len(data),
           'summaries': summaries, 'uncertainty': uncertainty, 'null_local_auc': 0.5,
           'context_positive_retention_events': float(positive_selected.mean()),
           'excluded_groups_by_reason': dict(reasons), 'dense_examples': dense,
           'limitations': ['No calibrated hit probabilities or confirmed new mudslides',
                          'Image visibility at inventory points not independently annotated',
                          'No image training on Austrian cases; these events were seen in earlier project versions',
                          'Context gate ranks matched point sets, not continuous hazard zones',
                          'All dense proposals remain UNVERIFIED; no automatic training uptake']}
    write_json(guard(REPORTS / 'transfer_results.json'), out)
    print(out, flush=True)
    return out


if __name__ == '__main__':
    run()
