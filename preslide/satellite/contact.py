"""Contact sheets for mandatory visual inspection: RGB before, RGB after and NDVI change for each event, centre marked."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from ..common import read_json
from .features import indices, valid_mask
from .imagery import fetch_patch, sample_dir
from .paths import SAT_DATA, SAT_REPORT, guard, config


def stretch_rgb(refl, lo=None, hi=None):
    rgb = np.stack([refl[2], refl[1], refl[0]], axis=-1)
    if lo is None:
        lo, hi = np.nanpercentile(rgb, 2), np.nanpercentile(rgb, 98)
    out = np.clip((rgb - lo) / max(hi - lo, 1e-6), 0, 1)
    return np.nan_to_num(out) ** 0.8, lo, hi


def _crop(a, grid, extent_m):
    r, c = grid.centre_pixel()
    h = int(round(extent_m / grid.res / 2))
    return a[..., r - h:r + h, c - h:c + h]


def event_panels(event_id, label, extent_m=960):
    """Return the figure rows for one positive: (rgb_before, rgb_after, delta_ndvi, meta)."""
    sid = f'{event_id}_positive'
    sel = read_json(sample_dir(sid) / 'selection.json')
    g = sel['grid']
    from .imagery import Grid
    grid = Grid(**g)
    (rb, sb, mb) = fetch_patch(sid, sel['items']['before_primary'], grid)
    (ra, sa, ma) = fetch_patch(sid, sel['items']['after_primary'], grid)
    rgb_b, lo, hi = stretch_rgb(_crop(rb, grid, extent_m))
    rgb_a, _, _ = stretch_rgb(_crop(ra, grid, extent_m), lo, hi)
    valid = valid_mask(rb, sb) & valid_mask(ra, sa)
    dndvi = np.where(valid, indices(ra)['ndvi'] - indices(rb)['ndvi'], np.nan)
    return rgb_b, rgb_a, _crop(dndvi, grid, extent_m), {'before': mb, 'after': ma, 'sel': sel, 'label': label, 'grid': grid, 'extent_m': extent_m}


def contact_sheet(event_ids, labels, out_path, extent_m=960, title=None):
    core_m = config()['patch']['core_m']
    n = len(event_ids)
    fig, axes = plt.subplots(n, 3, figsize=(10.5, 3.6 * n), squeeze=False)
    for i, (eid, lab) in enumerate(zip(event_ids, labels)):
        rgb_b, rgb_a, dn, meta = event_panels(eid, lab, extent_m)
        px = rgb_b.shape[0]
        half_core = core_m / 10 / 2
        for ax, img, kind in zip(axes[i], (rgb_b, rgb_a, dn), ('before', 'after', 'delta')):
            if kind == 'delta':
                ax.imshow(img, cmap='RdBu', vmin=-0.5, vmax=0.5)
            else:
                ax.imshow(img)
            ax.add_patch(Rectangle((px / 2 - half_core, px / 2 - half_core), 2 * half_core, 2 * half_core, fill=False, ec='yellow', lw=1.2))
            ax.plot(px / 2, px / 2, marker='+', color='yellow', ms=10, mew=1.2)
            ax.set_xticks([]); ax.set_yticks([])
        sb, sa = meta['sel']['selected']['before_primary'], meta['sel']['selected']['after_primary']
        qb, qa = meta['before']['quality'], meta['after']['quality']
        axes[i][0].set_title(f"{lab} · vorher {sb['datetime'][:10]} ({sb['days_from_event']} d)\nWolken {qb['patch']['cloud']:.0%} · Schnee {qb['patch']['snow']:.0%}", fontsize=8, loc='left')
        axes[i][1].set_title(f"nachher {sa['datetime'][:10]} (+{sa['days_from_event']} d)\nWolken {qa['patch']['cloud']:.0%} · Schnee {qa['patch']['snow']:.0%}", fontsize=8, loc='left')
        axes[i][2].set_title(f'ΔNDVI (nachher − vorher) · Ausschnitt {extent_m} m · Kasten {core_m} m', fontsize=8, loc='left')
    fig.suptitle(title or 'PreSlide Pipeline B – Sentinel-2 vorher/nachher, bekannte Ereignisse (Kreuz = gemeldete Position)', fontsize=10)
    fig.tight_layout()
    guard(out_path.parent)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path


def anonymous_labels(event_ids, states, years):
    """Stable local labels SAT-01.. that avoid exposing source identifiers in committed images."""
    return [f'SAT-{i + 1:02d} · {s} {y}' for i, (s, y) in enumerate(zip(states, years))]


def sheets_for(limit=0, per_sheet=6):
    """Contact sheets for all positives with a built feature record (eligible, pair available)."""
    data = pd.read_parquet(SAT_DATA / 'tables/dataset.parquet')
    pos = data[data['label'] == 1].sort_values('event_day').reset_index(drop=True)
    if limit:
        pos = pos.head(limit)
    labels = anonymous_labels(pos['event_group_id'], pos['state'], pos['event_day'].str[:4])
    mapping = pd.DataFrame({'label': labels, 'event_id': pos['event_group_id'], 'event_day': pos['event_day']})
    out_dir = guard(SAT_REPORT / 'contact_sheets')
    mapping.to_csv(SAT_DATA / 'tables/contact_sheet_labels.csv', index=False)   # local only: links labels to source ids
    paths = []
    for k in range(0, len(pos), per_sheet):
        chunk = pos.iloc[k:k + per_sheet]
        p = contact_sheet(list(chunk['event_group_id']), labels[k:k + per_sheet], out_dir / f'contact_sheet_{k // per_sheet + 1:02d}.png')
        paths.append(p)
        print('wrote', p, flush=True)
    return paths
