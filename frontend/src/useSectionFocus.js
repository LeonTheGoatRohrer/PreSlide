import { nextTick, onMounted, watch } from 'vue'
export function useSectionFocus(section, prefix) {
  async function focusSection() {
    if(!section())return
    await nextTick()
    const target=document.getElementById(prefix+section())?.querySelector('summary')
    if(target){target.focus({preventScroll:true});target.scrollIntoView({block:'start',behavior:'instant'})}
  }
  onMounted(focusSection)
  watch(section,focusSection,{flush:'post'})
}
