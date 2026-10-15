<script setup>
import { ref, watch } from 'vue'
const props = defineProps({title:String,subtitle:String,open:Boolean})
const expanded = ref(props.open)
watch(()=>props.open,v=>expanded.value=v)
</script>
<template>
  <details class="disclosure" :open="expanded" @toggle="expanded=$event.target.open">
    <summary><span>{{title}}<small v-if="subtitle">{{subtitle}}</small></span><svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="M5 12h14M12 5v14" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></summary>
    <div v-if="expanded" class="disclosure-body"><slot/></div>
  </details>
</template>
