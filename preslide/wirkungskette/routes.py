"""API routes for the Wirkungskette demo (included in preslide.api with one line)."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from . import analysis
from . import build as B
from . import store
from .paths import DEMOS, config

router = APIRouter(prefix='/api/wirkungskette')
GEBIET = Query('stanz', description='Demogebiet: ' + ', '.join(DEMOS))


def _guarded(fn, *args):
    try:
        return fn(*args)
    except FileNotFoundError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def _stored(gebiet, key, loader):
    def load():
        cfg = config(gebiet)
        r = float(cfg['radius_m']['max'])
        p = B.paths(r, cfg)
        if not store.exists(p[key]):
            raise FileNotFoundError(f'Demogebiet nicht vorbereitet: python -m preslide.wirkungskette build --gebiet {gebiet}')
        return loader(p[key], B.terrain_identity(cfg, r))
    return _guarded(load)


@router.get('/gebiete')
def gebiete():
    out = []
    for g in DEMOS:
        cfg = config(g)
        out.append({'id': g, 'name': cfg['demo']['name'], 'stichtag': cfg['demo']['reference_day'],
                    'bereit': store.exists(B.paths(float(cfg['radius_m']['max']), cfg)['cells'])})
    return out


@router.get('')
def wirkungskette(radius_m: float = Query(3000), modus: str = Query('pruefpunkte'), anriss: str | None = Query(None), gebiet: str = GEBIET):
    return _guarded(analysis.analyse, radius_m, modus, anriss, gebiet)


@router.get('/relief')
def relief(gebiet: str = GEBIET):
    return _stored(gebiet, 'relief_meta', store.load_json)


@router.get('/hoehenlinien')
def hoehenlinien(gebiet: str = GEBIET):
    return _stored(gebiet, 'contours', store.load_json)


@router.get('/relief.png')
def relief_png(gebiet: str = GEBIET):
    return Response(_stored(gebiet, 'relief', store.load_bytes), media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})


@router.get('/pruefstufen')
def pruefstufen_meta(radius_m: float = Query(3000), gebiet: str = GEBIET):
    return {'ecken': _guarded(analysis.class_image, radius_m, gebiet)[1]}


@router.get('/pruefstufen.png')
def pruefstufen_png(radius_m: float = Query(3000), gebiet: str = GEBIET):
    return Response(_guarded(analysis.class_image, radius_m, gebiet)[0], media_type='image/png')


@router.get('/kontext')
def kontext(radius_m: float = Query(3000), gebiet: str = GEBIET):
    return _guarded(analysis.context_layer, radius_m, gebiet)
