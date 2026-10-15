import { ref, onMounted } from 'vue'
// Only successful read-only responses are cached; a failed request is always retryable.
const cache = new Map()
export function useResource(url) {
  const data=ref(cache.get(url)||null), error=ref(''), loading=ref(!data.value)
  let active=false
  async function reload() {
    if(active)return
    active=true; loading.value=true; error.value=''
    try {
      const response=await fetch(url)
      if(!response.ok)throw new Error(`Die gespeicherten Daten sind gerade nicht verfügbar (HTTP ${response.status}).`)
      data.value=await response.json(); cache.set(url,data.value)
    } catch(e) { error.value=e.message; data.value=null }
    finally {loading.value=false;active=false}
  }
  onMounted(()=>{if(!data.value)reload()})
  return {data,error,loading,reload}
}
