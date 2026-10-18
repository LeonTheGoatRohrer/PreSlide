// Jury-facing entry pages first; the earlier three pages stay intact as the research area.
export const mainNav = [
  {id:'start',label:'Start'},
  {id:'hangcheck',label:'Hang-Check'},
  {id:'pruefgebiete',label:'Demo'},
  {id:'befunde',label:'Ergebnisse'},
  {id:'methodik',label:'Methodik & Grenzen',short:'Methodik'},
  {id:'forschung',label:'Forschung'},
]
// Old route ids are kept as the canonical addresses of the research pages, so every earlier link still works.
export const researchPages = [
  {id:'projekt',label:'Projekt'},
  {id:'vorgehen',label:'Vorgehen'},
  {id:'ergebnisse',label:'Ergebnisse im Detail'},
  {id:'hangkarte',label:'Hangkarte'},
]
export const pages = [...mainNav, ...researchPages]
export const pageTitles = {pruefgebiete:'Demo: Prüfgebiete',hangcheck:'Hang-Check bei Starkregen',forschung:'Forschungsbereich'}
// Hash routes work in the existing FastAPI static deployment, without a new server route.
const legacy = {experiment:['vorgehen','beispiel'],wetter:['vorgehen','beispiel'],warum:['vorgehen',''],methodik:['vorgehen','quellen'],v04:['ergebnisse','v04'],v05:['ergebnisse','v05'],benchmarks:['ergebnisse','vergleich'],einzelfaelle:['ergebnisse','historie'],ergebnisse:['ergebnisse','historie']}
export function resolveRoute(hash) {
  const value = hash.replace(/^#\/?/,'')
  const old = !hash.startsWith('#/') && legacy[value]
  if (old) return {page:old[0],section:old[1]}
  const [page,section=''] = value.split('/')
  if (page==='forschung' && researchPages.some(p=>p.id===section)) return {page:section,section:''}
  return {page:pages.some(p=>p.id===page)?page:'start',section}
}
// Which main navigation entry is highlighted for a page: research pages belong to "Forschung".
export function activeNav(page) {
  return researchPages.some(p=>p.id===page) ? 'forschung' : page
}
export function isResearch(page) {
  return page==='forschung' || researchPages.some(p=>p.id===page)
}
export function pageTitle(page) {
  return pageTitles[page] || pages.find(p=>p.id===page)?.label || 'Start'
}
