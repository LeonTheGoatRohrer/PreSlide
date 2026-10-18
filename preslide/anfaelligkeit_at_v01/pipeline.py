"""Data stages of anfaelligkeit_at_v01 (each stage reads the previous checkpoint, writes a hashed checkpoint).

  python -m preslide.anfaelligkeit_at_v01 positives
  python -m preslide.anfaelligkeit_at_v01 samples  --variant srtm|skadi [--areas N]
  python -m preslide.anfaelligkeit_at_v01 context  --variant srtm|skadi [--areas N]
  python -m preslide.anfaelligkeit_at_v01 infra    --variant srtm|skadi [--areas N]

--areas N is the pilot: only the N smallest evaluation areas (by registered candidate count, ties by name).
"""
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from ..common import write_json
from ..matching import austria_boundary
from . import context, inventory, terrain
from .paths import DATA, config, load, save, sha


def tag(variant, areas):
    return f'{variant}' + (f'_pilot{areas}' if areas else '')


def stage_positives():
    cfg = config()
    records = inventory.load_records()
    cands, counts = inventory.candidates(cfg, records, austria_boundary())
    save(cands, DATA / 'positives_candidates.parquet', {'counts': counts})
    write_json(DATA / 'positives_counts.json', counts)
    print(json.dumps({k: v for k, v in counts.items() if not isinstance(v, dict)}, indent=1))
    return cands


def _blocks(variant, keys, workers=2):
    todo = [k for k in keys if not terrain.block_path(variant, *k).with_suffix('.json').exists()]
    if todo:
        print(f'{variant}: computing {len(todo)} of {len(keys)} terrain blocks', flush=True)
        # DEM tiles are fetched sequentially first, so worker processes never download the same tile twice.
        for k in todo:
            left, top = terrain.block_origin(*k)
            m = terrain.margin_cells()
            bounds = terrain.transform_bounds(terrain.CRS, 'EPSG:4326', left - m * terrain.RES, top - (terrain.BLOCK + m) * terrain.RES,
                                              left + (terrain.BLOCK + m) * terrain.RES, top + m * terrain.RES, densify_pts=21)
            for lon in range(int(np.floor(bounds[0])), int(np.floor(bounds[2])) + 1):
                for lat in range(int(np.floor(bounds[1])), int(np.floor(bounds[3])) + 1):
                    terrain.TILES[variant](lat, lon)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for i, _ in enumerate(pool.map(_compute, [(variant, *k) for k in todo]), 1):
                if i % 10 == 0 or i == len(todo):
                    print(f'  {i}/{len(todo)} blocks', flush=True)


def _compute(args):
    terrain.compute_block(*args)
    return True


def pilot_areas(cands: pd.DataFrame, variant: str, n: int, minimum: int) -> list:
    eligible = cands[inventory.year_eligible(cands.year, variant)]
    sizes = eligible.area_id.value_counts()
    sizes = sizes[sizes >= minimum]
    return sorted(sizes.index, key=lambda a: (sizes[a], a))[:n]


def stage_samples(variant: str, areas: int = 0):
    cfg = config()
    cands = load(DATA / 'positives_candidates.parquet')
    if cands is None:
        raise RuntimeError('run the positives stage first')
    minimum = int(cfg['areas']['evaluation_area'].split('>= ')[1].split(' ')[0])
    counts = {'variant': variant, 'candidates': int(len(cands))}
    elig = inventory.year_eligible(cands.year, variant)
    counts['excluded_dem_provenance_year'] = int((~elig).sum())
    pos = cands[elig].copy()
    if areas:
        chosen = pilot_areas(cands, variant, areas, minimum)
        pos = pos[pos.area_id.isin(chosen)].copy()
        counts['pilot_areas'] = chosen
    bx, by = terrain.block_of(pos.x, pos.y)
    _blocks(variant, sorted(set(zip(bx.tolist(), by.tolist()))))
    t = terrain.sample(variant, pos.x.to_numpy(), pos.y.to_numpy())
    ok = inventory.terrain_ok(t, cfg).to_numpy()
    counts['excluded_terrain'] = {'nan_or_elevation': int((t.elevation.isna() | ~t.elevation.between(*cfg['background']['elevation_range_m'])).sum()),
                                  'slope_below_minimum': int((t.slope < cfg['background']['minimum_slope_deg']).sum())}
    pos = pd.concat([pos.reset_index(drop=True), t], axis=1)[ok].reset_index(drop=True)
    sizes = pos.area_id.value_counts()
    status = {a: ('evaluation' if n >= minimum else 'training_only') for a, n in sizes.items()}
    records = inventory.load_records()
    buffer = inventory.InventoryBuffer(records, cfg['background']['inventory_buffer_m'])
    country = austria_boundary()
    region = {a: inventory.lattice_cells(g.x, g.y) for a, g in pos.groupby('area_id')}
    _blocks(variant, sorted({b for cells in region.values() for b in inventory.cell_blocks(cells)}))
    backgrounds, bg_counts = [], {}
    for a in sorted(region):
        n = int(sizes[a]) * cfg['background']['ratio_per_positive']
        bg, info = inventory.draw_background(a, region[a], n, variant, cfg, buffer, country)
        bg_counts[a] = {**info, 'lattice_cells': len(region[a])}
        if len(bg) < n:
            status[a] = 'excluded_background_shortfall'
        bg['area_id'] = a
        backgrounds.append(bg)
    bg = pd.concat(backgrounds, ignore_index=True)
    keep_cols = ['sample_id', 'area_id', 'x', 'y', 'lon', 'lat'] + terrain.TERRAIN
    p = pos.assign(label=1, sample_type='POSITIVE')[keep_cols + ['label', 'sample_type', 'object_id', 'year', 'project', 'position_class', 'state', 'method']]
    b = bg.assign(label=0, sample_type='PSEUDO_NEGATIVE')[keep_cols + ['label', 'sample_type']]
    samples = pd.concat([p, b], ignore_index=True)
    samples['area_status'] = samples.area_id.map(status)
    samples = samples[samples.area_status != 'excluded_background_shortfall'].reset_index(drop=True)
    years = pos.groupby('area_id').year.agg(lambda s: sorted({int(v) for v in s.dropna()}))
    counts['areas'] = {a: {'positives': int(sizes[a]), 'status': status[a], 'years': years.get(a, []), **bg_counts[a]} for a in sorted(sizes.index)}
    counts['included_positives'] = int(len(p))
    counts['evaluation_areas'] = sum(v == 'evaluation' for v in status.values())
    save(samples, DATA / f'samples_{tag(variant, areas)}.parquet', {'counts': counts})
    write_json(DATA / f'samples_{tag(variant, areas)}_counts.json', counts)
    print(json.dumps({k: v for k, v in counts.items() if k != 'areas'}, indent=1, default=str))
    for a, v in counts['areas'].items():
        print(f"  {a:50s} {v['positives']:5d} {v['status']:16s} bg {v['accepted']}/{v['needed']} examined {v['candidates_examined']} cells {v['lattice_cells']}")
    return samples


def stage_context(variant: str, areas: int = 0):
    cfg = config()
    samples = load(DATA / f'samples_{tag(variant, areas)}.parquet')
    geo = context.geology(samples.lon, samples.lat, cfg)
    # land-cover vintage per area: all included positives known year >= 2002 and one vintage (registered area_rule)
    pos = samples[samples.label == 1]
    vint = {}
    for a, g in pos.groupby('area_id'):
        v = {context.clc_vintage(y) for y in g.year}
        vint[a] = v.pop() if len(v) == 1 and None not in v else None
    vintages = samples.area_id.map(vint).where(samples.area_id.map(vint).notna(), None).tolist()
    lc = context.land_cover(samples.lon, samples.lat, vintages, cfg)
    out = pd.DataFrame({'sample_id': samples.sample_id, 'geology_class': geo.to_numpy(), 'clc_vintage': vintages,
                        'clc_code': lc.clc_code.to_numpy(), 'land_cover_class': lc.land_cover_class.to_numpy()})
    counts = {'geology_missing': int(out.geology_class.isna().sum()), 'lc_areas': {a: v for a, v in vint.items() if v},
              'lc_samples': int(out.clc_vintage.notna().sum()),
              'lc_missing_in_lc_areas': int((out.clc_vintage.notna() & out.land_cover_class.isna()).sum())}
    save(out, DATA / f'context_{tag(variant, areas)}.parquet', {'counts': counts})
    print(json.dumps(counts, indent=1))
    return out


def stage_infra(variant: str, areas: int = 0):
    """OSM distances (reporting-bias control only). variant 'both' streams the extract once for srtm and skadi."""
    from ..v07 import infrastructure as v07
    cfg = config()
    expected = cfg['reporting_bias_control']['source'].split('sha256 ')[1].split(',')[0]
    if sha(v07.PBF) != expected:
        raise RuntimeError('OSM extract differs from the registered file')
    tags = [tag(v, areas) for v in (('srtm', 'skadi') if variant == 'both' else (variant,))]
    tables = {t: load(DATA / f'samples_{t}.parquet') for t in tags}
    xy = np.vstack([s[['x', 'y']].to_numpy(float) for s in tables.values()])
    (road, road_cap), (bld, bld_cap), counts = v07.extract(xy, {'infrastructure': {'distance_cap_m': 5000}})
    start = 0
    for t, samples in tables.items():
        sl = slice(start, start + len(samples))
        start += len(samples)
        out = pd.DataFrame({'sample_id': samples.sample_id, 'dist_road_m': road[sl], 'dist_building_m': bld[sl],
                            'road_capped': road_cap[sl], 'building_capped': bld_cap[sl]})
        out['dist_infrastructure_m'] = out[['dist_road_m', 'dist_building_m']].min(axis=1)
        save(out, DATA / f'infra_{t}.parquet', {'counts': counts})
        print(t, json.dumps(counts), out.describe().round(1).to_string())
