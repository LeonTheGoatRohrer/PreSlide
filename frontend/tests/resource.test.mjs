import test from 'node:test'
import assert from 'node:assert/strict'
import {createRenderer,h,nextTick} from 'vue'
import {useResource} from '../src/useResource.js'

// Mount the real composable without a browser or additional test dependency.
function mount(url) {
  const renderer=createRenderer({createElement:()=>({}),insert(){},remove(){},patchProp(){},setElementText(){},createText:()=>({}),createComment:()=>({}),setText(){},setComment(){},parentNode:()=>null,nextSibling:()=>null})
  let state
  const app=renderer.createApp({setup(){state=useResource(url);return ()=>h('div')}})
  app.mount({})
  return {state,unmount:()=>app.unmount()}
}
const flush=async()=>{await new Promise(resolve=>setImmediate(resolve));await nextTick()}

test('loading, unavailable data, retry, and successful-response caching',async(t)=>{
  const old=globalThis.fetch
  t.after(()=>{globalThis.fetch=old})
  let complete,calls=0
  globalThis.fetch=()=>{calls++;return new Promise(resolve=>complete=resolve)}
  const first=mount('/test/display-resource')
  assert.equal(first.state.loading.value,true)
  assert.equal(first.state.data.value,null)
  complete({ok:false,status:503});await flush()
  assert.match(first.state.error.value,/503/)
  assert.equal(first.state.status.value,503)
  assert.equal(first.state.loading.value,false)
  assert.equal(first.state.data.value,null)
  const retry=first.state.reload()
  assert.equal(first.state.loading.value,true)
  assert.equal(first.state.error.value,'')
  complete({ok:true,json:async()=>({label:'real response received'})});await retry
  assert.deepEqual(first.state.data.value,{label:'real response received'})
  first.unmount()
  const second=mount('/test/display-resource')
  assert.equal(calls,2)
  assert.equal(second.state.loading.value,false)
  assert.deepEqual(second.state.data.value,first.state.data.value)
  second.unmount()
})

test('network and malformed JSON failures remain errors, never fabricated values',async(t)=>{
  const old=globalThis.fetch;t.after(()=>{globalThis.fetch=old})
  globalThis.fetch=async()=>{throw Error('Verbindung unterbrochen')}
  const {state,unmount}=mount('/test/unavailable-resource')
  await flush();assert.equal(state.data.value,null);assert.match(state.error.value,/Verbindung/);assert.equal(state.status.value,0)
  globalThis.fetch=async()=>({ok:true,json:async()=>{throw Error('Ungültiges JSON')}})
  await state.reload();assert.equal(state.data.value,null);assert.match(state.error.value,/JSON/)
  unmount()
})
