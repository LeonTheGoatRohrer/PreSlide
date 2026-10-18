"""Step-0 audit numbers for wirkungskette_v01 (reports/wirkungskette_v01/audit.json); read-only on all inputs."""
import json

import numpy as np
import pandas as pd

from ..common import read_json, write_json
from ..sources import ROOT
from ..terrain import PROJECT
from . import build as B
from . import core, store
from .paths import REPORT, config, guard

DAMAGE = ['SACHSCHADEN', 'Verkehrsanlagen', 'Bauwerke', 'Versorgungsinfrastruktur', 'Bewegliche_Objekte_Tiere', 'Sonstige']


def inventory():
    d = read_json(ROOT / 'data/raw/geosphere_natural_hazards.json')
    return pd.DataFrame([{**f['attributes'], 'lon': f['geometry']['x'], 'lat': f['geometry']['y']} for f in d['features']])


def damage_counts(frame):
    return {'ereignisse': int(len(frame)), 'mit_irgendeinem_schadensfeld': int(frame[DAMAGE].notna().any(axis=1).sum()),
            'verkehrsanlagen_1': int((frame.Verkehrsanlagen == 1).sum()), 'bauwerke_1': int((frame.Bauwerke == 1).sum()),
            'versorgungsinfrastruktur_1': int((frame.Versorgungsinfrastruktur == 1).sum())}


def run():
    cfg = config()
    d = cfg['demo']
    r_max = float(cfg['radius_m']['max'])
    raw = inventory()
    v04 = pd.read_parquet(ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet')
    pos = v04[v04.label == 1]
    matched = raw[raw.nameOfEvent.isin(pos.event_group_id)]
    stanz_ids = pos[pos.event_day == d['reference_day']].event_group_id
    stanz = raw[raw.nameOfEvent.isin(stanz_ids)]
    hm = matched[matched.Prozessuntergruppe.str.contains('Hangmure', na=False)]
    cx, cy = PROJECT.transform(d['centre_longitude'], d['centre_latitude'])
    x, y = PROJECT.transform(raw.lon.to_numpy(), raw.lat.to_numpy())
    near = raw[core.distance_m(x, y, cx, cy) <= r_max]
    wlv = read_json(ROOT / 'data/raw/wlv_slides.json')['features']
    wx, wy = PROJECT.transform(np.array([f['geometry']['coordinates'][0] for f in wlv]), np.array([f['geometry']['coordinates'][1] for f in wlv]))
    wlv_near = [f for f, dist in zip(wlv, core.distance_m(wx, wy, cx, cy)) if dist <= r_max]
    p = B.paths(r_max)
    terrain_meta = json.loads(p['terrain'].with_name('terrain.npz.meta.json').read_text(encoding='utf-8')) if store.exists(p['terrain']) else None
    cells = store.load_parquet(p['cells'], B.cells_identity(cfg, r_max)) if store.exists(p['cells']) else None
    osm_meta = json.loads(p['osm'].with_name('infrastructure.parquet.meta.json').read_text(encoding='utf-8')) if store.exists(p['osm']) else None
    out = {
        'demo': d,
        'gelaende': None if terrain_meta is None else {
            'dem_kacheln': [{k: s[k] for k in ('url', 'object_last_modified', 'sha256', 'vertical_datum', 'resolution')} for s in terrain_meta['dem_sources']],
            'fenster_radius_m': B.window_radius_m(cfg, r_max), 'fenster_zellen': terrain_meta['shape'],
            'nodata_zellen': terrain_meta['nodata_cells'], 'fuellung_iterationen': terrain_meta['fill_iterations']},
        'zellen': None if cells is None else {
            'raster_zellen_bis_10km': int((cells.kind == 'grid').sum()), 'bewertbar': int(((cells.kind == 'grid') & (cells.reason == '')).sum()),
            'nicht_bewertbar_nach_grund': cells[(cells.kind == 'grid') & (cells.reason != '')].reason.value_counts().to_dict(),
            'dokumentierte_ereignisse_im_fenster': int((cells.kind == 'event').sum()),
            'davon_bewertbar': int(((cells.kind == 'event') & (cells.reason == '')).sum())},
        'infrastruktur': osm_meta,
        'auslaufreferenzen': {
            'stanz_v04_ereignisse': damage_counts(stanz),
            'stanz_prozesse': stanz.Prozessuntergruppe.value_counts().to_dict(),
            'stanz_lagequalitaet': stanz.QUAL_LAGE.value_counts().to_dict(),
            'stanz_erhebung': stanz.ERHEBME_TX.value_counts().to_dict(),
            'stanz_projekt': stanz.PROJEKTNAM.value_counts().to_dict(),
            'v04_positive_alle': damage_counts(matched),
            'v04_positive_hangmuren_typ': damage_counts(hm),
            'inventar_im_10km_umkreis': {**damage_counts(near), 'nach_kampagne': near.RegKatE_ID.value_counts().head(8).to_dict()},
            'geometrie': 'nur Punkte; keine Anriss-, Transport- oder Ablagerungsgeometrie, kein Feld zum Ortsbezug des Punkts',
            'wlv_ereignisse_im_10km_umkreis': len(wlv_near),
            'wlv_mit_intensitaet': sum('Intensit' in f['properties'].get('nameofevent', '') for f in wlv_near)},
    }
    write_json(guard(REPORT) / 'audit.json', out)
    return out
