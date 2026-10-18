"""python -m preslide.pruefgebiete – schreibt data/pruefgebiete_v01/web/overview.json aus dem eingefrorenen V0.4-Lauf."""
from ..sources import ROOT
from .overview import write_overview

# Eingefrorener V0.4-Lauf (siehe config/v04.json und reports/v04/FREEZE.json); nur lesend.
DATASET = ROOT / 'data/v04/run_c6d67a854ba7/dataset.parquet'
OUT = ROOT / 'data/pruefgebiete_v01/web/overview.json'

if __name__ == '__main__':
    overview = write_overview(DATASET, OUT)
    print(overview['zaehlung'])
