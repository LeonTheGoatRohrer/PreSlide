"""GET /api/extremwetter: aggregate case-crossover results (python -m preslide.extremwetter report)."""
from fastapi import APIRouter, HTTPException

from ..common import read_json
from .paths import WEB

router = APIRouter()


@router.get('/api/extremwetter')
def extremwetter():
    # Aggregates only; the bundle is written by the report step and holds no event-level rows.
    if not WEB.exists():
        raise HTTPException(503, 'Extremwetter-Ergebnisse fehlen: python -m preslide.extremwetter report')
    return read_json(WEB)
