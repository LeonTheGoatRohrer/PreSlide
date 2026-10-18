// User-first structure: one main action (Hang-Check) and four questions a visitor asks.
// Hash routes keep working in the existing FastAPI static deployment without a server route.
export const primaryAction = {id: 'check', label: 'Hang prüfen'}
export const mainNav = [
  {id: 'so-funktionierts', label: "So funktioniert's"},
  {id: 'belastbar', label: 'Wie belastbar'},
  {id: 'studien', label: 'Studienatlas'},
  {id: 'ueber', label: 'Über'},
]
export const pages = ['start', primaryAction.id, ...mainNav.map(p => p.id)]
export const pageTitles = {start: 'Hang-Check bei Starkregen', check: 'Hang-Check', 'so-funktionierts': "So funktioniert's",
  belastbar: 'Wie belastbar', studien: 'Studienatlas', ueber: 'Über Talwacht'}

// Every earlier address leads to the place where its content lives now.
export const redirects = {
  start: '', hangcheck: 'check', hangkarte: 'check',
  pruefgebiete: 'so-funktionierts#wirkungskette', befunde: 'belastbar', methodik: 'so-funktionierts',
  forschung: 'studien', projekt: 'studien#kernfrage', vorgehen: 'studien#baseline',
  'vorgehen/beispiel': 'studien#baseline', 'vorgehen/quellen': 'studien#v04',
  ergebnisse: 'studien', 'ergebnisse/v04': 'studien#v04', 'ergebnisse/v05': 'studien#v05',
  'ergebnisse/vergleich': 'studien#vergleich', 'ergebnisse/historie': 'studien#baseline',
  'forschung/projekt': 'studien#kernfrage', 'forschung/vorgehen': 'studien#baseline',
  'forschung/ergebnisse': 'studien', 'forschung/hangkarte': 'check',
}
// Bookmarks of the very first single-page version (without "/").
export const legacyAnchors = {
  experiment: 'vorgehen/beispiel', wetter: 'vorgehen/beispiel', warum: 'vorgehen', methodik: 'vorgehen/quellen',
  v04: 'ergebnisse/v04', v05: 'ergebnisse/v05', benchmarks: 'ergebnisse/vergleich',
  einzelfaelle: 'ergebnisse/historie', ergebnisse: 'ergebnisse/historie',
}

function split(text, sep) {
  const i = text.indexOf(sep)
  return i < 0 ? [text, ''] : [text.slice(0, i), text.slice(i + 1)]
}

// "#/check?lon=…&lat=…" or "#/studien#v04" → path, query parameters and in-page anchor.
export function parseHash(hash = '') {
  const raw = hash.replace(/^#\/?/, '')
  const [pathQuery, anchor] = split(raw, '#')
  const [path, query] = split(pathQuery, '?')
  return {path: path.replace(/\/+$/, ''), anchor, params: Object.fromEntries(new URLSearchParams(query))}
}

function target(path) {
  const [page, anchor] = split(path, '#')
  return {page: page || 'start', anchor}
}

/** Resolve a location hash. `redirect` is the canonical hash when the address is an old or unknown one. */
export function resolveRoute(hash = '') {
  if (hash.length > 1 && !hash.startsWith('#/') && legacyAnchors[hash.slice(1)]) hash = '#/' + legacyAnchors[hash.slice(1)]
  const {path, anchor, params} = parseHash(hash)
  const forward = redirects[path] ?? redirects[path.split('/')[0]]
  if (forward !== undefined) {
    const t = target(forward)
    const query = new URLSearchParams(params).toString()
    return {page: t.page, anchor: t.anchor || anchor, params,
      redirect: '#/' + (t.page === 'start' ? '' : t.page) + (query ? '?' + query : '') + (t.anchor || anchor ? '#' + (t.anchor || anchor) : '')}
  }
  const page = path.split('/')[0] || 'start'
  if (!pages.includes(page)) return {page: 'start', anchor: '', params: {}, redirect: '#/'}
  return {page, anchor, params, redirect: null}
}

export function pageTitle(page) {
  return pageTitles[page] || pageTitles.start
}
export function href(page, anchor = '') {
  return '#/' + (page === 'start' ? '' : page) + (anchor ? '#' + anchor : '')
}
