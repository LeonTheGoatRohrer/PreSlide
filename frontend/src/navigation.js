export const pages = [{id:'projekt',label:'Projekt'},{id:'vorgehen',label:'Vorgehen'},{id:'ergebnisse',label:'Ergebnisse'},{id:'pruefgebiete',label:'Prüfgebiete'}]
// Hash routes work in the existing FastAPI static deployment, without a new server route.
const legacy = {experiment:['vorgehen','beispiel'],wetter:['vorgehen','beispiel'],warum:['vorgehen',''],methodik:['vorgehen','quellen'],v04:['ergebnisse','v04'],v05:['ergebnisse','v05'],benchmarks:['ergebnisse','vergleich'],einzelfaelle:['ergebnisse','historie'],ergebnisse:['ergebnisse','historie']}
export function resolveRoute(hash) {
  const value = hash.replace(/^#\/?/,'')
  const old = !hash.startsWith('#/') && legacy[value]
  if (old) return {page:old[0],section:old[1]}
  const [page,section=''] = value.split('/')
  return {page:pages.some(p=>p.id===page)?page:'projekt',section}
}
