import { ref, onMounted } from 'vue'
// Only successful read-only responses are cached; a failed request is always retryable.
// `status` keeps the HTTP status of a failed response (0 = no response) so pages can tell
// "result not produced yet" (503) apart from other failures.
const cache = new Map()
export function useResource(url) {
  const data=ref(cache.get(url)||null), error=ref(''), loading=ref(!data.value), status=ref(data.value?200:null)
  let active=false
  async function reload() {
    if(active)return
    active=true; loading.value=true; error.value=''; status.value=null
    try {
      const response=await fetch(url)
      status.value=response.status
      if(!response.ok)throw new Error(`Die gespeicherten Daten sind gerade nicht verfügbar (HTTP ${response.status}).`)
      data.value=await response.json(); cache.set(url,data.value)
    } catch(e) { error.value=e.message; data.value=null; if(status.value===null)status.value=0 }
    finally {loading.value=false;active=false}
  }
  onMounted(()=>{if(!data.value)reload()})
  return {data,error,loading,status,reload}
}
