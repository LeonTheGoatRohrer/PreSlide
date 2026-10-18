"""Study atlas (GET /api/studien): every study of the project with its stored figures, read through the registry
config/studien_atlas.json. Only stored values are delivered; a missing file makes the study unavailable with a
reason, never a substitute value. Reports are served only from paths named in the registry."""
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from .common import read_json
from .sources import ROOT

REGISTRY = ROOT / 'config/studien_atlas.json'
router = APIRouter(prefix='/api/studien')
_TOKEN = re.compile(r'([^.\[\]]+)|\[(\d+)\]')


def json_path(data, path):
    """Value at a dot path with list indices ('test.results.conditional_logit/combined.ci95[0]'); KeyError if absent."""
    value = data
    for key, index in _TOKEN.findall(path):
        if index:
            if not isinstance(value, list) or int(index) >= len(value):
                raise KeyError(path)
            value = value[int(index)]
        else:
            if not isinstance(value, dict) or key not in value:
                raise KeyError(path)
            value = value[key]
    return value


def inside_root(relative, root=ROOT):
    """Absolute path of a registry entry; refuses anything outside the repository."""
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'path outside the repository: {relative}')
    return path


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def resolve_figure(fig, root=ROOT, cache=None):
    """One registered figure with its stored value, interval and units. Problems are returned, never filled."""
    cache = {} if cache is None else cache
    out = {k: fig[k] for k in ('label', 'art', 'bezug', 'bezug_label', 'intervall_art', 'einheiten_label', 'satz') if k in fig}

    def read(ref):
        file = ref.get('datei', fig['datei'])
        if file not in cache:
            path = inside_root(file, root)
            cache[file] = read_json(path) if path.exists() else None
        if cache[file] is None:
            raise FileNotFoundError(file)
        return json_path(cache[file], ref['pfad'])

    try:
        value = read(fig)
        if not _number(value):
            raise TypeError(f"{fig['pfad']} is not a number")
        out['wert'] = value
        if fig.get('intervall'):
            iv = read(fig['intervall'])
            if not (isinstance(iv, list) and len(iv) == 2 and all(_number(v) for v in iv)):
                raise TypeError(f"{fig['intervall']['pfad']} is not a two-sided interval")
            out['intervall'] = iv
        if fig.get('einheiten'):
            units = read(fig['einheiten'])
            if not _number(units):
                raise TypeError(f"{fig['einheiten']['pfad']} is not a number")
            out['einheiten'] = units
        out['verfuegbar'] = True
    except FileNotFoundError as missing:
        out.update(verfuegbar=False, grund=f'Datei liegt in diesem Checkout nicht vor: {missing}')
        for key in ('wert', 'intervall', 'einheiten'):
            out.pop(key, None)
    except (KeyError, TypeError) as error:
        out.update(verfuegbar=False, grund=f'Gespeicherter Wert nicht lesbar: {error}')
        for key in ('wert', 'intervall', 'einheiten'):
            out.pop(key, None)
    return out


def verification_status(relative, root=ROOT):
    if not relative:
        return None
    path = inside_root(relative, root)
    if not path.exists():
        return {'datei': relative, 'status': None}
    status = read_json(path).get('status')
    return {'datei': relative, 'status': status if isinstance(status, str) else None}


def study(entry, root=ROOT):
    """Registry entry with resolved figures; unavailable as a whole when its report or a figure is missing."""
    out = {k: v for k, v in entry.items() if k not in ('kennzahlen', 'bericht', 'verifikation')}
    reasons = []
    report = entry.get('bericht')
    out['bericht'] = bool(report) and inside_root(report, root).exists()
    if report and not out['bericht']:
        reasons.append(f'Bericht liegt in diesem Checkout nicht vor: {report}')
    cache = {}
    figures = [resolve_figure(f, root, cache) for f in entry.get('kennzahlen', [])]
    reasons += [f['grund'] for f in figures if not f['verfuegbar']]
    out['kennzahlen'] = figures
    out['verifikation'] = verification_status(entry.get('verifikation'), root)
    out['verfuegbar'] = not reasons
    if reasons:
        out['grund'] = reasons
    return out


def atlas(root=ROOT, registry=None):
    reg = registry if registry is not None else read_json(root / 'config/studien_atlas.json')
    return {'version': reg['version'], 'gruppen': reg['gruppen'], 'status_bedeutung': reg['status_bedeutung'],
            'studien': [study(e, root) for e in reg['studien']]}


@router.get('')
def studien():
    return atlas()


@router.get('/{study_id}/bericht', response_class=PlainTextResponse)
def bericht(study_id: str):
    entry = next((e for e in read_json(REGISTRY)['studien'] if e['id'] == study_id), None)
    if entry is None or not entry.get('bericht'):
        raise HTTPException(404, 'Für diese Studie ist kein Bericht registriert.')
    path = inside_root(entry['bericht'])
    if not path.exists():
        raise HTTPException(404, 'Der Bericht liegt in diesem Checkout nicht vor.')
    return PlainTextResponse(path.read_text(encoding='utf-8'), media_type='text/markdown; charset=utf-8')
