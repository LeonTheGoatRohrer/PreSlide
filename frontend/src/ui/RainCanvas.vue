<script setup>
// Fine, slow rain over the hero image: ~120 slanted strokes in --glacier at 6–12 % opacity.
// Paused for reduced motion and while the hero is off screen.
import {ref, onMounted, onBeforeUnmount} from 'vue'
import {reducedMotion} from './motion.js'
const canvas = ref(null)
let raf = 0, io = null, drops = [], w = 0, h = 0, ctx = null, visible = true, last = 0

function resize() {
  const c = canvas.value, dpr = Math.min(2, window.devicePixelRatio || 1)
  w = c.clientWidth; h = c.clientHeight
  c.width = w * dpr; c.height = h * dpr
  ctx = c.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  const n = Math.round(120 * Math.min(1, w / 1200) + 40)
  drops = Array.from({length: n}, () => seed(Math.random() * h))
}
function seed(y = -40) {
  return {x: Math.random() * (w + 200) - 100, y, len: 14 + Math.random() * 26, v: 120 + Math.random() * 140, a: .06 + Math.random() * .06}
}
function draw(now) {
  const dt = Math.min(.05, (now - last) / 1000 || 0); last = now
  ctx.clearRect(0, 0, w, h)
  ctx.lineWidth = 1; ctx.lineCap = 'round'
  for (const d of drops) {
    d.y += d.v * dt; d.x -= d.v * dt * .18
    if (d.y - d.len > h) Object.assign(d, seed())
    ctx.strokeStyle = `rgba(141,182,199,${d.a})`
    ctx.beginPath(); ctx.moveTo(d.x, d.y); ctx.lineTo(d.x + d.len * .18, d.y - d.len); ctx.stroke()
  }
  if (visible) raf = requestAnimationFrame(draw)
}
function start() { cancelAnimationFrame(raf); last = performance.now(); raf = requestAnimationFrame(draw) }
onMounted(() => {
  if (reducedMotion()) return
  resize()
  window.addEventListener('resize', resize)
  io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) start(); else cancelAnimationFrame(raf) })
  io.observe(canvas.value)
})
onBeforeUnmount(() => { cancelAnimationFrame(raf); io?.disconnect(); window.removeEventListener('resize', resize) })
</script>
<template><canvas ref="canvas" class="rain" aria-hidden="true"></canvas></template>
<style>.rain{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1}</style>
