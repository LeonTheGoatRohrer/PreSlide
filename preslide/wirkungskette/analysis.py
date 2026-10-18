"""Request-time chain on the cached demo window: review classes in a radius -> release points -> D8 route ->
runout scenarios -> corridor -> infrastructure inside each scenario. Cheap; deterministic for (radius, mode)."""
import io
from functools import lru_cache

import numpy as np
from PIL import Image

from ..terrain import PROJECT, INVERSE
from . import build as B
from . import core, store
from .paths import config, config_sha

LAYER_TAGS = {'pruefstufen': 'Befund', 'route': 'Szenario', 'auslauf': 'Szenario', 'infrastruktur': 'Szenario',
              'dokumentierte_ereignisse': 'Befund', 'relief': 'Grundlage'}
END_TEXT = {'gestoppt': 'Szenario endet innerhalb des Rechengebiets',
            'rand': 'Route erreicht den Rand des Rechengebiets; das tatsächliche Ende ist unbekannt (kein Auslaufende)',
            'nodata': 'Route erreicht eine Zelle ohne Höhenwert; nicht beurteilbar',
            'senke': 'Route endet in einer nicht aufgelösten Senke',
            'max_laenge': 'Route länger als die konfigurierte Höchstlänge'}
NOTICE = ('Prüfstufen sind eine relative Rangfolge der Hangzellen innerhalb des gewählten Umkreises aus dem eingefrorenen '
          'V0.4-Geländemodell, keine Eintrittsangabe. Auslaufszenarien sind deterministische Abwärtsrouten mit '
          'Literaturannahmen, nicht an Ereignissen geprüft. Infrastruktur „liegt im Auslaufszenario“ bedeutet nur '
          'räumliche Überlagerung, keine Schadensaussage.')


@lru_cache(maxsize=2)
def _window(radius_max_m):
    cfg = config()
    p = B.paths(radius_max_m)
    for key in ('terrain', 'cells', 'osm', 'relief_meta'):
        if not store.exists(p[key]):
            raise FileNotFoundError('Demogebiet nicht vorbereitet: python -m preslide.wirkungskette build')
    terrain = store.load_npz(p['terrain'], B.terrain_identity(cfg, radius_max_m))
    cells = store.load_parquet(p['cells'], B.cells_identity(cfg, radius_max_m))
    osm = store.load_parquet(p['osm'], B.osm_identity(cfg, radius_max_m))
    features = B.osm_features(osm)
    return {'cfg': cfg, 'terrain': terrain, 'cells': cells, 'osm': osm, 'features': features, 'bundle': B.model_bundle(cfg),
            'exposure': core.Exposure(features), 'radius_max_m': radius_max_m,
            'relief': store.load_json(p['relief_meta'], B.terrain_identity(cfg, radius_max_m))}


def window(radius_max_m=None):
    return _window(float(radius_max_m or config()['radius_m']['max']))


def classes_in_radius(w, radius_m):
    cfg = w['cfg']
    cells = w['cells']
    grid = cells[(cells.kind == 'grid') & (cells.distance_m <= radius_m)].copy()
    ok = grid[grid.reason == ''].copy()
    if len(ok) < 20:
        raise ValueError('Zu wenige bewertbare Hangzellen im Umkreis')
    ok['klasse'] = core.review_classes(ok.score.to_numpy(), cfg['review_points']['classes'])
    return grid, ok


def _lonlat(x, y, digits=6):
    lon, lat = INVERSE.transform(np.asarray(x, float), np.asarray(y, float))
    return [[round(float(a), digits), round(float(b), digits)] for a, b in zip(lon, lat)]


FEATURE_DE = {'elevation': 'Höhe', 'slope': 'Neigung', 'aspect_sin': 'Exposition (Ostanteil)', 'aspect_cos': 'Exposition (Nordanteil)',
              'profile_curvature': 'Profilkrümmung', 'plan_curvature': 'Plankrümmung', 'roughness_tri': 'Rauigkeit',
              'tpi_150m': 'Hangposition 150 m', 'tpi_500m': 'Hangposition 500 m', 'relative_position_500m': 'Höhenlage im 500-m-Umfeld',
              'log10_catchment_m2': 'Einzugsgebiet', 'twi': 'Feuchteindex (TWI)', 'lc_forest': 'Landbedeckung Wald',
              'lc_grass_shrub': 'Landbedeckung Grünland/Gebüsch', 'lc_agriculture': 'Landbedeckung Landwirtschaft',
              'lc_open_bare': 'Landbedeckung offen/vegetationsarm', 'lc_artificial_water_other': 'Landbedeckung Siedlung/Verkehr/sonstige',
              'geo_carbonate': 'Geologie Karbonat', 'geo_clastic_rock': 'Geologie klastisches Gestein',
              'geo_unconsolidated': 'Geologie Lockergestein', 'geo_low_grade_metamorphic': 'Geologie schwach metamorph',
              'geo_crystalline_other': 'Geologie kristallin/sonstige'}
LAND_COVER_DE = {k: v.replace('Landbedeckung ', '') for k, v in FEATURE_DE.items() if k.startswith('lc_')}


def drivers(w, rows, n=3):
    """Largest contributions (standardised value x coefficient) of the frozen linear score, for transparency only."""
    b = w['bundle']
    z = b['preprocessor'].transform(rows[b['columns']], rows.index.to_series())
    out = []
    for vec in z:
        c = vec * b['model'].coef_
        out.append([{'merkmal': FEATURE_DE[b['columns'][i]], 'beitrag': round(float(c[i]), 2),
                     'richtung': 'hebt die Stufe' if c[i] > 0 else 'senkt die Stufe'} for i in np.argsort(-np.abs(c))[:n]])
    return out


def release_candidates(w, ok, radius_m, mode):
    rp = w['cfg']['release_points']
    if mode == 'pruefpunkte':
        idx = core.select_release_points(ok.x, ok.y, ok.score, rp['pruefpunkte_count'], rp['pruefpunkte_separation_m'])
        sel = ok.iloc[idx]
        drv = drivers(w, sel)
        return [{'id': f'P{i + 1}', 'art': 'Prüfpunkt', 'x': float(r.x), 'y': float(r.y), 'klasse': int(r.klasse),
                 'bezeichnung': f'Prüfpunkt {i + 1} (Prüfstufe {int(r.klasse)})', 'treiber': drv[i],
                 'landbedeckung': LAND_COVER_DE[r.land_cover_class], 'neigung_grad': round(float(r.slope), 1)}
                for i, r in enumerate(sel.itertuples())]
    if mode == 'hangmuren':
        ev = w['cells']
        ev = ev[(ev.kind == 'event') & (ev.process_type == 'Hangmure') & (ev.distance_m <= radius_m)].sort_values('event_id')
        return [{'id': r.event_id, 'art': 'Dokumentierte Hangmure', 'x': float(r.x), 'y': float(r.y), 'klasse': None,
                 'bezeichnung': f'Hangmure {r.event_id}', 'treiber': [],
                 'landbedeckung': LAND_COVER_DE.get(r.land_cover_class, 'nicht eindeutig'),
                 'neigung_grad': round(float(r.slope), 1)} for r in ev.itertuples()]
    raise ValueError('Modus muss pruefpunkte oder hangmuren sein')


def scenario_chain(w, release):
    """Route, profile, scenario stops, corridors and infrastructure for one release point."""
    cfg, t = w['cfg'], w['terrain']
    rc = cfg['runout']
    res, left, top = float(t['resolution']), float(t['left']), float(t['top'])
    dem, filled, edge = t['dem'], t['filled'], t['edge']
    r0, c0 = core.xy_to_cell(left, top, res, [release['x']], [release['y']])
    rows, cols, end = core.d8_route(filled, dem, int(r0[0]), int(c0[0]), res, rc['max_route_m'])
    s = core.path_distance_m(rows, cols, res)
    x, y = core.dem_cell_xy(left, top, res, rows, cols)
    z = dem[rows, cols].astype(float)
    sinks = core.sink_cells(filled, dem, rows, cols, cfg['terrain']['sink_flag_depth_m'])
    el = rc['energy_line']
    types = list(cfg['infrastructure']['types'])
    scenarios = []
    for sc in rc['scenarios']:
        if sc['kind'] == 'fixed_reach':
            stop = core.fixed_reach_stop(s, sc['reach_m'], end)
            energy = None
        else:
            stop = core.energy_line_stop(z, s, sc['angle_deg'], el['v_max_m_s'], el['g_m_s2'], end)
            energy = stop.pop('energy_height_m')
        area = core.corridor(x, y, stop['stop_index'], rc['corridor']['width_m'])
        hits = w['exposure'].hits(area)
        scenarios.append({'id': sc['id'], 'bezeichnung': sc['label'], 'art': sc['kind'], 'quelle': sc['source_de'],
                          'stopp_index': stop['stop_index'], 'status': stop['status'], 'status_text': END_TEXT[stop['status']],
                          'laenge_m': round(float(s[stop['stop_index']]), 1), 'stopp_lage': _lonlat([x[stop['stop_index']]], [y[stop['stop_index']]])[0],
                          'hoehendifferenz_m': round(float(z[0] - z[stop['stop_index']]), 1),
                          'energielinie_m': [round(v, 1) for v in energy] if energy is not None else None,
                          'infrastruktur': core.count_by_type(hits, types), '_hits': hits, '_area': area,
                          'korridor': {'type': 'Polygon', 'coordinates': [_lonlat(*area.exterior.xy)]}})
    longest = max(scenarios, key=lambda sc: sc['stopp_index'])
    hit_sets = {sc['id']: {h['index'] for h in sc['_hits']} for sc in scenarios}
    treffer = []
    for h in longest['_hits']:
        f = w['features'][h['index']]
        g = f['geometry']
        pt = g.representative_point() if f['typ'] == 'gebaeude' else g.intersection(longest['_area']).representative_point()
        treffer.append({'typ': f['typ'], 'name': f['name'], 'klasse': f['klasse'], 'osm_id': f['osm_id'],
                        'laenge_im_korridor_m': round(h['length_m'], 1),
                        'szenarien': [sid for sid, ids in hit_sets.items() if h['index'] in ids],
                        'lage': _lonlat([pt.x], [pt.y])[0]})
    for sc in scenarios:
        sc.pop('_hits')
        sc.pop('_area')
    # Display: route and profile up to the longest scenario stop plus a fixed margin (the full route length stays reported).
    shown = int(np.searchsorted(s, s[longest['stopp_index']] + rc['display_beyond_longest_scenario_m'], side='right'))
    step = max(1, shown // 600)
    for sc in scenarios:
        if sc['energielinie_m'] is not None:
            sc['energielinie_m'] = sc['energielinie_m'][:shown:step]
    return {'anriss': {**{k: v for k, v in release.items() if k not in ('x', 'y')}, 'lage': _lonlat([release['x']], [release['y']])[0],
                       'hoehe_m': round(float(z[0]), 1),
                       'einzugsgebiet_unvollstaendig': bool(edge[rows[0], cols[0]])},
            'route': {'koordinaten': _lonlat(x[:shown], y[:shown]), 'angezeigt_bis_m': round(float(s[shown - 1]), 1), 'ende': end, 'ende_text': END_TEXT[end], 'laenge_m': round(float(s[-1]), 1),
                      'senken_zellen': int(sinks.sum()),
                      'senken_distanz_m': [round(float(v), 1) for v in s[:shown][sinks[:shown]]]},
            'profil': {'distanz_m': [round(float(v), 1) for v in s[:shown:step]], 'hoehe_m': [round(float(v), 1) for v in z[:shown:step]],
                       'schritt': step},
            'szenarien': scenarios, 'treffer': treffer}


def exploratory_events(w, ok, radius_m):
    """Seen data, descriptive: documented events of the reference day placed against this window's class cutoffs."""
    cfg = w['cfg']
    cut = core.class_cutoffs(ok.score.to_numpy(), cfg['review_points']['classes'])
    ev = w['cells']
    ev = ev[(ev.kind == 'event') & (ev.distance_m <= radius_m)]
    assessable = ev[ev.reason == '']
    out = {'gesamt': int(len(ev)), 'bewertbar': int(len(assessable)),
           'nicht_bewertbar_nach_grund': ev.reason[ev.reason != ''].value_counts().to_dict(), 'gruppen': {}}
    area = {c['id']: float((ok.klasse == c['id']).mean()) for c in cfg['review_points']['classes']}
    for name, sub in (('alle', assessable), ('hangmuren', assessable[assessable.process_type == 'Hangmure'])):
        cls = core.classify_by_cutoffs(sub.score.to_numpy(), cut) if len(sub) else np.array([], int)
        out['gruppen'][name] = {'anzahl': int(len(sub)),
                                'anteil_je_stufe': {str(c['id']): round(float((cls == c['id']).mean()), 3) if len(sub) else None
                                                    for c in cfg['review_points']['classes']}}
    out['flaechenanteil_je_stufe'] = {str(k): round(v, 3) for k, v in area.items()}
    out['punkte'] = [{'id': r.event_id, 'prozess': r.process_type, 'lage': _lonlat([r.x], [r.y])[0]} for r in ev.itertuples()]
    return out


@lru_cache(maxsize=32)
def _analyse(radius_m, mode):
    w = window()
    cfg = w['cfg']
    radius_m = core.validate_radius(radius_m, cfg)
    grid, ok = classes_in_radius(w, radius_m)
    releases = release_candidates(w, ok, radius_m, mode)
    chains = [scenario_chain(w, r) for r in releases]
    rp = cfg['review_points']
    counts = {str(c['id']): int((ok.klasse == c['id']).sum()) for c in rp['classes']}
    result = {
        'version': cfg['version'], 'hinweis': NOTICE, 'ebenen': LAYER_TAGS,
        'demo': {'name': cfg['demo']['name'], 'stichtag': cfg['demo']['reference_day'],
                 'zentrum': [cfg['demo']['centre_longitude'], cfg['demo']['centre_latitude']],
                 'kennzeichnung': 'Versiegeltes, bereits einmal ausgewertetes V0.4-Testereignis (25.07.2016); hier nur Demonstration, nichts wurde daran angepasst.'},
        'umkreis_m': radius_m, 'umkreis_grenzen_m': [cfg['radius_m']['min'], cfg['radius_m']['max']],
        'umkreis_begruendung': 'Die Kontrollhänge im V0.4-Design lagen 750 m bis 10 km vom Ereignis entfernt; darüber hinaus hat das Modell nie Hänge verglichen.',
        'modus': mode,
        'pruefstufen': {'stufen': [{'id': c['id'], 'bezeichnung': c['label'], 'obere_grenze_anteil': c['top_fraction'],
                                    'zellen': counts[str(c['id'])]} for c in rp['classes']],
                        'zellen_bewertbar': int(len(ok)), 'zellen_gesamt': int(len(grid)),
                        'nicht_bewertbar_nach_grund': grid.reason[grid.reason != ''].value_counts().to_dict(),
                        'zellgroesse_m': rp['cell_m'], 'modell': 'V0.4 Gelände (bedingte logistische Regression, nur Entwicklungsdaten)',
                        'bezug': 'relativ innerhalb dieses Umkreises; dieselbe Farbe bedeutet bei anderem Umkreis etwas anderes',
                        'schwaechen': ['V0.4-Test, Gelände allein: lokale AUC 0,702 (11 unabhängige Testeinheiten).',
                                       'Stanz-Sturm allein, pro Ereignis: Gelände 0,455 gegen gematchte Kontrollen, also keine Trennung.',
                                       'Pilot mudslide_cascade_v01: Für reine Hangmuren trennt eine Geländevorauswahl kaum (lokale AUC 0,539 [0,406; 0,669]).']},
        'anrisspunkte': chains,
        'korridor': cfg['runout']['corridor']['label'] + ' – ' + 'benannte Darstellungsannahme, nicht kalibriert',
        'fehlende_groessen': ['Ausgangsvolumen', 'Material und Korngröße', 'Wassergehalt', 'Materialaufnahme unterwegs',
                              'Schutzbauten und Hindernisse', 'Fließtiefe und Druck'],
        'auslaufpruefung': 'Keine unabhängigen Auslauf- oder Ablagerungsgeometrien im Inventar; für die Stanz-Ereignisse sind alle Schadensfelder leer. Das Auslaufszenario ist eine unvalidierte Illustration.',
        'explorativ_dokumentierte_ereignisse': exploratory_events(w, ok, radius_m),
        'quellen': {'gelaende': 'Mapzen/AWS Skadi 1″ (u. a. österreichisches DGM, EU-DEM), 30 m in EPSG:31287, Objektstand vor dem Stichtag',
                    'landbedeckung': 'Copernicus CORINE Land Cover 2012', 'geologie': 'GeoSphere Austria 1:500 000 (CC BY 4.0)',
                    'infrastruktur': '© OpenStreetMap-Mitwirkende (ODbL), heutiger Stand über Overpass API'},
        'identitaet': {'konfiguration_sha256': config_sha(), 'modell_sha256': rp['model_sha256']},
    }
    return result


def analyse(radius_m, mode='pruefpunkte', anriss=None):
    """API view: all release points as a short list, full chain (route, profile, corridors, hits) for one."""
    full = _analyse(core.validate_radius(radius_m, config()), mode)
    chains = full['anrisspunkte']
    if not chains:
        raise ValueError('Keine Anrisspunkte in diesem Umkreis')
    ids = [c['anriss']['id'] for c in chains]
    if anriss is not None and anriss not in ids:
        raise ValueError('Unbekannter Anrisspunkt')
    selected = chains[ids.index(anriss) if anriss is not None else 0]
    short = [{'anriss': c['anriss'], 'route_ende': c['route']['ende'],
              'szenarien': [{k: s[k] for k in ('id', 'status', 'laenge_m', 'infrastruktur')} for s in c['szenarien']]}
             for c in chains]
    result = {**full, 'anrisspunkte': short, 'auswahl': selected}
    bad = core.banned_words(result)
    if bad:
        raise RuntimeError(f'Unzulässige Formulierung in der Ausgabe: {bad[:3]}')
    return result


CLASS_RGBA = {1: (122, 30, 72, 225), 2: (196, 82, 58, 200), 3: (233, 168, 92, 150), 4: (240, 226, 196, 70)}
NOT_ASSESSABLE_RGBA = (120, 130, 140, 90)


@lru_cache(maxsize=16)
def class_image(radius_m):
    """PNG of the review classes on the 90 m grid inside the radius, plus its four lon/lat corners."""
    w = window()
    cfg = w['cfg']
    radius_m = core.validate_radius(radius_m, cfg)
    grid, ok = classes_in_radius(w, radius_m)
    t = w['terrain']
    res, left, top = float(t['resolution']), float(t['left']), float(t['top'])
    step = int(round(cfg['review_points']['cell_m'] / res))
    r_min, c_min = grid.row.min(), grid.col.min()
    n_r, n_c = (grid.row.max() - r_min) // step + 1, (grid.col.max() - c_min) // step + 1
    rgba = np.zeros((n_r, n_c, 4), np.uint8)
    gi, gj = ((grid.row - r_min) // step).to_numpy(), ((grid.col - c_min) // step).to_numpy()
    rgba[gi, gj] = NOT_ASSESSABLE_RGBA
    oi, oj = ((ok.row - r_min) // step).to_numpy(), ((ok.col - c_min) // step).to_numpy()
    for cid, colour in CLASS_RGBA.items():
        m = ok.klasse.to_numpy() == cid
        rgba[oi[m], oj[m]] = colour
    buf = io.BytesIO()
    Image.fromarray(rgba, 'RGBA').save(buf, format='PNG')
    half = (step * res - res) / 2           # grid cell centred on its anchor DEM cell
    img_left = left + c_min * res - half
    img_top = top - r_min * res + half
    return buf.getvalue(), B.corners_lonlat(img_left, img_top, step * res, (n_r, n_c))


@lru_cache(maxsize=16)
def context_layer(radius_m):
    """Roads, tracks, rail and building points inside the radius as GeoJSON (context, not an analysis result)."""
    w = window()
    cfg = w['cfg']
    radius_m = core.validate_radius(radius_m, cfg)
    cx, cy = PROJECT.transform(cfg['demo']['centre_longitude'], cfg['demo']['centre_latitude'])
    from shapely.geometry import Point
    circle = Point(cx, cy).buffer(radius_m + 500)
    out = []
    for f in w['features']:
        g = f['geometry']
        if f['typ'] == 'weg' or not g.intersects(circle):
            continue
        if f['typ'] == 'gebaeude':
            p = g.representative_point()
            geom = {'type': 'Point', 'coordinates': _lonlat([p.x], [p.y], 5)[0]}
        else:
            g = g.intersection(circle).simplify(3)
            parts = getattr(g, 'geoms', [g])
            geom = {'type': 'MultiLineString', 'coordinates': [_lonlat(*np.asarray(part.coords).T, 5) for part in parts if part.length > 0]}
        out.append({'type': 'Feature', 'properties': {'typ': f['typ'], 'name': f['name']}, 'geometry': geom})
    return {'type': 'FeatureCollection', 'features': out}


def pilot(radius_max_m=None):
    """1 -> 5 release points on the cached window, printed for inspection."""
    w = window(radius_max_m)
    radius = min(w['radius_max_m'], 2000.0)
    grid, ok = classes_in_radius(w, radius)
    rel = release_candidates(w, ok, radius, 'pruefpunkte')
    out = []
    for r in rel:
        ch = scenario_chain(w, r)
        out.append({'anriss': ch['anriss'], 'route_ende': ch['route']['ende'], 'route_m': ch['route']['laenge_m'],
                    'senken': ch['route']['senken_zellen'],
                    'szenarien': [(s['id'], s['status'], s['laenge_m'], s['infrastruktur']) for s in ch['szenarien']]})
    return out
