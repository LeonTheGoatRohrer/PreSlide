"""FastAPI routes of the Hangkarte (included by preslide.api). Local research use; heavy computations are serialised."""
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import build
from .paths import config
from .rain import recent_rain

router = APIRouter(prefix='/api/hangkarte')
_lock = threading.Lock()


class AreaRequest(BaseModel):
    longitude: float = Field(ge=9.4, le=17.3)
    latitude: float = Field(ge=46.3, le=49.1)
    radius_m: float | None = None
    points: list[tuple[float, float]] | None = Field(default=None, description='[longitude, latitude] pairs of a custom comparison group')


@router.get('/examples')
def examples():
    return {'examples': config()['examples'], 'area': config()['area'], 'notice': build.NOTICE}


@router.post('')
def area(req: AreaRequest):
    if not _lock.acquire(timeout=120):
        raise HTTPException(503, 'Eine andere Berechnung läuft noch; bitte kurz warten.')
    try:
        return build.compute(req.longitude, req.latitude, req.radius_m, req.points)
    except ValueError as error:
        raise HTTPException(422, str(error))
    finally:
        _lock.release()


@router.get('/rain')
def rain(longitude: float, latitude: float):
    try:
        return recent_rain(longitude, latitude)
    except Exception as error:      # separate optional layer: failure must not affect the shares
        return {'available': False, 'reason': str(error)[:200]}
