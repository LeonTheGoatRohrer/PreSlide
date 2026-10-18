"""API routes for the Wirkungskette demo (included in preslide.api with one line)."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from . import analysis
from . import build as B
from . import store
from .paths import config

router = APIRouter(prefix='/api/wirkungskette')


def _guarded(fn, *args):
    try:
        return fn(*args)
    except FileNotFoundError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get('')
def wirkungskette(radius_m: float = Query(3000), modus: str = Query('pruefpunkte'), anriss: str | None = Query(None)):
    return _guarded(analysis.analyse, radius_m, modus, anriss)


@router.get('/relief')
def relief():
    def load():
        cfg = config()
        r = float(cfg['radius_m']['max'])
        p = B.paths(r)
        if not store.exists(p['relief_meta']):
            raise FileNotFoundError('Demogebiet nicht vorbereitet: python -m preslide.wirkungskette build')
        ident = B.terrain_identity(cfg, r)
        return store.load_json(p['relief_meta'], ident)
    return _guarded(load)


@router.get('/hoehenlinien')
def hoehenlinien():
    def load():
        cfg = config()
        r = float(cfg['radius_m']['max'])
        p = B.paths(r)
        if not store.exists(p['contours']):
            raise FileNotFoundError('Demogebiet nicht vorbereitet: python -m preslide.wirkungskette build')
        return store.load_json(p['contours'], B.terrain_identity(cfg, r))
    return _guarded(load)


@router.get('/relief.png')
def relief_png():
    def load():
        cfg = config()
        r = float(cfg['radius_m']['max'])
        p = B.paths(r)
        if not store.exists(p['relief']):
            raise FileNotFoundError('Demogebiet nicht vorbereitet: python -m preslide.wirkungskette build')
        return store.load_bytes(p['relief'], B.terrain_identity(cfg, r))
    return Response(_guarded(load), media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})


@router.get('/pruefstufen')
def pruefstufen_meta(radius_m: float = Query(3000)):
    return {'ecken': _guarded(analysis.class_image, radius_m)[1]}


@router.get('/pruefstufen.png')
def pruefstufen_png(radius_m: float = Query(3000)):
    return Response(_guarded(analysis.class_image, radius_m)[0], media_type='image/png')


@router.get('/kontext')
def kontext(radius_m: float = Query(3000)):
    return _guarded(analysis.context_layer, radius_m)
