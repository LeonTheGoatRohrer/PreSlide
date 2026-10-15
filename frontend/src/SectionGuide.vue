<script setup>
defineProps({
  kind:{type:String,default:''},
  what:{type:String,default:''},
  see:{type:String,default:''},
  why:{type:String,default:''},
  take:{type:String,default:''}
})
</script>

<template>
  <details class="guide"><summary>Lesehilfe zu dieser Darstellung</summary>
    <p v-if="kind" class="guide-kind"><span>{{kind}}</span></p>
    <div class="guide-grid">
      <div v-if="what"><h4>Worum geht es?</h4><p>{{what}}</p></div>
      <div v-if="see"><h4>Was siehst du hier?</h4><p>{{see}}</p></div>
      <div v-if="why"><h4>Warum ist das interessant?</h4><p>{{why}}</p></div>
      <div v-if="take" class="guide-take"><h4>Kernaussage</h4><p>{{take}}</p></div>
    </div>
  </details>
</template>

<style scoped>
.guide summary{padding:16px 20px;cursor:pointer;font-size:14px;color:var(--blue);min-height:48px}
.guide{margin:26px 0 30px;border:1px solid var(--line);background:#fafafc}
.guide-kind{margin:0;padding:10px 20px 0}
.guide-kind span{display:inline-block;font-size:10px;letter-spacing:1px;text-transform:uppercase;font-weight:600;color:var(--blue);border:1px solid var(--blue);padding:2px 8px}
.guide-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:0}
.guide-grid>div{padding:14px 20px 18px;border-right:1px solid var(--line)}
.guide-grid>div:last-child{border-right:0}
.guide h4{margin:0 0 6px;font-size:11px;letter-spacing:.8px;text-transform:uppercase;color:var(--muted);font-weight:600}
.guide p{margin:0;font-size:13.5px;line-height:1.6}
.guide-take{background:#eef2fc}
.guide-take h4{color:var(--blue)}
.guide-take p{font-weight:500}
@media(max-width:720px){.guide-grid>div{border-right:0;border-bottom:1px solid var(--line)}.guide-grid>div:last-child{border-bottom:0}}
</style>
