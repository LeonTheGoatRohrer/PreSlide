"""FastAPI routes of the Hang-Check (included by preslide.api). No weather or switch parameter exists anywhere."""
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from . import build, fliesswege, gemeinden
from .paths import config

router = APIRouter(prefix='/api/hangcheck')
_lock = threading.Lock()


class PlaceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')   # e.g. a rain amount or the page switch is refused with 422
    longitude: float
    latitude: float
    radius_m: float | None = None


@router.get('/orte')
def orte(q: str = ''):
    return {'orte': gemeinden.search(q), 'quelle': 'GISCO LAU 2021 (Gemeindegrenzen), offline durchsucht'}


@router.get('/beispiele')
def beispiele():
    cfg = config()
    return {'beispiele': cfg['examples'], 'radius_m': cfg['radius_m'], 'stufen': cfg['classes'],
            'datenstand': cfg['data_vintages'], 'hinweise': build.hinweise(cfg), 'status': cfg['status']}


@router.post('')
def hangcheck(req: PlaceRequest, request: Request):
    if request.query_params:
        raise HTTPException(422, 'Hang-Check nimmt keine Zusatzparameter an (auch keine Wetterangaben).')
    if not _lock.acquire(timeout=5):
        raise HTTPException(503, 'Eine andere Berechnung läuft noch; bitte kurz warten.')
    try:
        return build.compute(req.longitude, req.latitude, req.radius_m)
    except ValueError as error:
        raise HTTPException(422, str(error))
    finally:
        _lock.release()


@router.get('/fliesswege')
def fliesswege_route(longitude: float, latitude: float, request: Request, radius_m: float | None = None):
    """Possible flow paths of the review points (scenario, unvalidated) and OSM features inside the corridor."""
    if set(request.query_params) - {'longitude', 'latitude', 'radius_m'}:
        raise HTTPException(422, 'Hang-Check nimmt keine Zusatzparameter an (auch keine Wetterangaben).')
    if not _lock.acquire(timeout=5):
        raise HTTPException(503, 'Eine andere Berechnung läuft noch; bitte kurz warten.')
    try:
        return fliesswege.compute(longitude, latitude, radius_m)
    except ValueError as error:
        raise HTTPException(422, str(error))
    except RuntimeError as error:
        raise HTTPException(503, f'Fließwege gerade nicht berechenbar: {error}'[:300])
    finally:
        _lock.release()
