"""Local web bundle data/anfaelligkeit_at_v01/web/ (aggregates + demo layer). Not served yet; the website session wires it.

  python -m preslide.anfaelligkeit_at_v01 web

bundle.json: per-area results of both variants, primary verdict, reporting-bias and land-cover summaries, demo metadata.
demo_model.png / demo_slope.png: RGBA percentile-rank layers of the demo block (transparent = not assessable),
corners in demo.corners_lonlat_tl_tr_br_bl (MapLibre image source order). Record-level positives stay in this local folder.
"""
import numpy as np
import pandas as pd
from PIL import Image

from ..common import read_json, write_json
from .paths import DATA, REPORT, guard

# sequential light-to-dark ramp (5 classes of 20 percentile points), colour-blind safe (viridis stops)
RAMP = np.array([[253, 231, 37], [94, 201, 98], [33, 145, 140], [59, 82, 139], [68, 1, 84]], dtype=np.uint8)


def clean(v):
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    return v


def to_png(rank: np.ndarray, path) -> None:
    """Top classes dark: 80-100 % darkest. NaN transparent."""
    rgba = np.zeros(rank.shape + (4,), dtype=np.uint8)
    ok = np.isfinite(rank)
    cls = np.clip((np.nan_to_num(rank) // 20).astype(int), 0, 4)
    rgba[..., :3] = RAMP[cls]
    rgba[..., 3] = np.where(ok, 200, 0)
    Image.fromarray(rgba, 'RGBA').save(path)


def run() -> dict:
    out = guard(DATA / 'web')
    bundle = {'version': 'anfaelligkeit_at_v01', 'meaning': 'relative Anfälligkeit (Rangfolge), keine Wahrscheinlichkeit',
              'variants': {}}
    for variant in ('srtm', 'skadi'):
        path = REPORT / f'results_{variant}.json'
        if not path.exists():
            continue
        r = read_json(path)
        table = pd.read_csv(REPORT / f'area_table_{variant}.csv')
        bundle['variants'][variant] = {
            'primary': r['primary'], 'verdict': r['verdict'], 'n_evaluation_areas': r['n_evaluation_areas'],
            'summary': r['summary'], 'pooled_auc': r['pooled_auc'],
            'reporting_bias': r['reporting_bias'],
            'land_cover': {k: v for k, v in r['land_cover'].items() if k != 'per_area'},
            'importance': r['permutation_importance_mean'],
            'areas': table.to_dict('records')}
    demo_meta = DATA / 'demo/demo_meta.json'
    if demo_meta.exists():
        meta = read_json(demo_meta)
        layers = np.load(DATA / 'demo/demo_layers.npz')
        to_png(layers['rank'], out / 'demo_model.png')
        to_png(layers['rank_slope'], out / 'demo_slope.png')
        pos = pd.read_parquet(DATA / 'demo/demo_positives.parquet')
        bundle['demo'] = {**meta, 'layers': {'model': 'demo_model.png', 'slope': 'demo_slope.png'},
                          'legend': ['0-20 %', '20-40 %', '40-60 %', '60-80 %', '80-100 % (höchste relative Anfälligkeit)'],
                          'documented_hangmuren': pos.round(6).to_dict('records')}
    write_json(out / 'bundle.json', clean(bundle))
    print(f'wrote {out / "bundle.json"}')
    return bundle
