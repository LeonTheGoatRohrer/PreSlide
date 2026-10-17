"""Phase 1: fetch, extract and audit the open development inventories (no terrain, no model).

  python -m preslide.susceptibility.inventory fetch far_western_nepal|rer2023
  python -m preslide.susceptibility.inventory audit far_western_nepal|rer2023 --limit 1|5|20|0(all)

Download URL, size and checksum come from the registered Phase 0 evidence; the sealed Suedtirol data are not handled here.
"""
import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import shapefile
from pyproj import CRS, Transformer
import shapely
from shapely import make_valid
from shapely.geometry import shape

from ..common import read_json, write_json
from .download import download, fetch_json, file_digest
from .paths import DATA, REPORT, config, guard

RAW = DATA / 'raw'
EVIDENCE_KEYS = {'far_western_nepal': 'zenodo_far_western_nepal', 'rer2023': 'zenodo_rer2023'}
AUDITABLE = sorted(EVIDENCE_KEYS) + ['gorkha_2015']
AREA_QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)


def _bsdtar():
    # Windows bsdtar (libarchive) reads zip and rar; GNU tar from Git Bash does not.
    for candidate in (Path(r'C:\Windows\System32\tar.exe'), shutil.which('bsdtar')):
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise RuntimeError('bsdtar (libarchive) is required to extract zip/rar archives')


def safe_members(names):
    """Refuse archive members that would escape the extraction directory."""
    bad = [n for n in names if n.startswith(('/', '\\')) or ':' in n or '..' in Path(n).parts]
    if bad:
        raise RuntimeError(f'unsafe archive members: {bad[:5]}')
    return names


def fetch(dataset):
    if dataset not in config()['registry']['datasets'] or config()['registry']['datasets'][dataset]['role'] != 'development':
        raise ValueError(f'{dataset} is not a registered development inventory')
    ev = read_json(REPORT / 'phase0_evidence.json')[EVIDENCE_KEYS[dataset]]
    if len(ev['files']) != 1:
        raise RuntimeError(f'{dataset}: expected one file in the record, found {len(ev["files"])}')
    f = ev['files'][0]
    folder = guard(RAW / dataset)
    prov = download(f['url'], folder / f['key'], f['checksum'], f['size_bytes'])
    out = folder / 'extracted'
    names = subprocess.run([_bsdtar(), '-tf', str(folder / f['key'])], capture_output=True, text=True, check=True).stdout.split('\n')
    names = safe_members([n for n in names if n.strip()])
    if not out.exists():
        tmp = guard(folder / 'extracting')
        subprocess.run([_bsdtar(), '-xf', str(folder / f['key']), '-C', str(tmp)], check=True)
        tmp.replace(out)
    prov.update({'dataset': dataset, 'record': ev['record'], 'doi': ev['doi'], 'concept_doi': ev['concept_doi'],
                 'licence_from_record': ev['license']['id'], 'title': ev['title'],
                 'members': sorted(names)})
    write_json(folder / 'provenance.json', prov)
    return prov


def fetch_candidate(name, record):
    """Unregistered candidate inventory (registry only, never training without an amendment): all record files,
    md5-verified, archives extracted with member checks."""
    d = fetch_json(f'https://zenodo.org/api/records/{record}')
    folder = guard(RAW / 'candidates' / name)
    files = []
    for f in d['files']:
        prov = download(f['links']['self'], folder / f['key'], f['checksum'], f['size'])
        if f['key'].lower().endswith(('.zip', '.rar')):
            target = folder / 'extracted' / Path(f['key']).stem
            names = subprocess.run([_bsdtar(), '-tf', str(folder / f['key'])], capture_output=True, text=True,
                                   check=True).stdout.split('\n')
            prov['members'] = safe_members(sorted(n for n in names if n.strip()))
            if not target.exists():
                tmp = guard(folder / 'extracting')
                subprocess.run([_bsdtar(), '-xf', str(folder / f['key']), '-C', str(tmp)], check=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp.replace(target)
        files.append(prov)
    out = {'candidate': name, 'status': 'not registered; registry only', 'record': d['id'], 'doi': d['metadata'].get('doi'),
           'concept_doi': d.get('conceptdoi'), 'title': d['metadata']['title'], 'licence_from_record': d['metadata']['license']['id'],
           'files': files}
    write_json(folder / 'provenance.json', out)
    return out


def register_manual(dataset, archive, listed_size_mib, source_url, note):
    """Archive downloaded by the user in a browser (no published checksum): size check against the listing,
    hashes recorded, members checked, then extracted like a scripted download."""
    folder = guard(RAW / dataset)
    path = folder / archive
    if not path.exists():
        raise RuntimeError(f'{path} missing')
    size_mib = path.stat().st_size / 2**20
    if round(size_mib, 2) != listed_size_mib:
        raise RuntimeError(f'{archive}: {size_mib:.2f} MiB does not match the listed {listed_size_mib} MB')
    names = subprocess.run([_bsdtar(), '-tf', str(path)], capture_output=True, text=True, check=True).stdout.split('\n')
    names = safe_members([n for n in names if n.strip()])
    out = folder / 'extracted'
    if not out.exists():
        tmp = guard(folder / 'extracting')
        subprocess.run([_bsdtar(), '-xf', str(path), '-C', str(tmp)], check=True)
        tmp.replace(out)
    prov = {'dataset': dataset, 'file': archive, 'size_bytes': path.stat().st_size, 'listed_size': f'{listed_size_mib} MB',
            'md5': file_digest(path, 'md5'), 'sha256': file_digest(path, 'sha256'), 'source': source_url,
            'retrieval': note, 'members': sorted(names)}
    write_json(folder / 'provenance.json', prov)
    return prov


def layer_crs(shp):
    prj = Path(shp).with_suffix('.prj')
    if not prj.exists():
        raise RuntimeError(f'{shp}: no .prj; CRS unknown, refusing to guess')
    return CRS.from_wkt(prj.read_text(encoding='utf-8', errors='replace'))


def metric_transformer(crs, lon, lat):
    """Identity for a metre-based projected CRS, else transform to the local UTM zone of (lon, lat)."""
    if crs.is_projected and crs.axis_info[0].unit_name == 'metre':
        return None, crs
    zone = int((lon + 180) // 6) + 1
    utm = CRS.from_epsg((32600 if lat >= 0 else 32700) + zone)
    return Transformer.from_crs(crs, utm, always_xy=True).transform, utm


def read_layer(shp, limit=0):
    """Fields, CRS and shapely geometries of a shapefile layer (first `limit` records, 0 = all)."""
    with shapefile.Reader(str(shp), encodingErrors='replace') as r:
        n = len(r)
        idx = range(n if not limit else min(limit, n))
        fields = [f[0] for f in r.fields[1:]]
        geoms, records = [], []
        for i in idx:
            try:
                s = r.shape(i)
                geoms.append(shape(s.__geo_interface__) if s.shapeType != shapefile.NULL else None)
            except shapefile.ShapefileException:
                geoms.append(None)  # empty polygon record; counted as a null geometry by the caller
            records.append(dict(zip(fields, r.record(i))))
        return {'path': shp, 'n_total': n, 'shape_type': r.shapeTypeName, 'fields': fields, 'bbox': list(r.bbox),
                'geoms': geoms, 'records': records}


def reproject(geom, fn):
    """Apply a pyproj always_xy transform function to all coordinates of a geometry."""
    return shapely.transform(geom, lambda xy: np.column_stack(fn(xy[:, 0], xy[:, 1])))


def polygon_areas_m2(geoms, crs):
    valid = [g for g in geoms if g is not None]
    if not valid:
        return np.array([]), crs, 0, 0
    c = valid[0].centroid
    to_m, metric_crs = metric_transformer(crs, c.x, c.y)
    invalid = sum(not g.is_valid for g in valid)
    fixed = [make_valid(g) if not g.is_valid else g for g in valid]
    if to_m:
        fixed = [reproject(g, to_m) for g in fixed]
    return np.array([g.area for g in fixed]), metric_crs, invalid, len(geoms) - len(valid)


def summarize(layer, crs):
    out = {'file': Path(layer['path']).name, 'n_total': layer['n_total'], 'n_read': len(layer['geoms']),
           'shape_type': layer['shape_type'], 'fields': layer['fields'], 'bbox_native': layer['bbox'],
           'crs_native': crs.name, 'crs_epsg': crs.to_epsg()}
    if layer['shape_type'].startswith('POLYGON'):
        areas, metric_crs, invalid, null = polygon_areas_m2(layer['geoms'], crs)
        out.update({'area_crs': metric_crs.name, 'invalid_geometries': int(invalid), 'null_geometries': int(null)})
        if len(areas):
            radius = np.sqrt(areas / math.pi)
            out['area_m2_quantiles'] = {str(q): float(np.quantile(areas, q)) for q in AREA_QUANTILES}
            out['area_m2_min_max_sum'] = [float(areas.min()), float(areas.max()), float(areas.sum())]
            out['equivalent_radius_m_p90'] = float(np.quantile(radius, 0.9))
            out['below_min_area'] = int((areas < config()['sampling']['positive_rule']['min_polygon_area_m2']).sum())
    categorical = {}
    for field in layer['fields']:
        values = [r[field] for r in layer['records']]
        distinct = set(map(str, values))
        if len(distinct) <= 30:
            categorical[field] = {v: sum(str(x) == v for x in values) for v in sorted(distinct)}
    out['categorical_fields'] = categorical
    return out


def audit(dataset, limit):
    folder = RAW / dataset / 'extracted'
    if not folder.exists():
        raise RuntimeError(f'{dataset}: not fetched')
    layers = []
    for shp in sorted(folder.rglob('*.shp')):
        layer = read_layer(shp, limit)
        layers.append(summarize(layer, layer_crs(shp)))
    result = {'dataset': dataset, 'limit': limit, 'layers': layers,
              'other_files': sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*')
                                    if p.is_file() and p.suffix.lower() not in ('.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.xml'))}
    if not limit:
        write_json(guard(REPORT) / f'phase1_audit_{dataset}.json', result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['fetch', 'audit'])
    ap.add_argument('dataset', choices=AUDITABLE)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    result = fetch(a.dataset) if a.stage == 'fetch' else audit(a.dataset, a.limit)
    print(json.dumps(result, indent=1, ensure_ascii=False, default=str)[:6000])


if __name__ == '__main__':
    main()
