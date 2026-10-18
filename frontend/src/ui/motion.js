// One motion system: scroll reveal (y 16 px → 0, 500 ms, staggered 60 ms) and count-up (1.2 s, once).
export const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

let observer = null
function shared() {
  if (observer || typeof IntersectionObserver === 'undefined') return observer
  observer = new IntersectionObserver(entries => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('in'); observer.unobserve(e.target) }
  }, {rootMargin: '0px 0px -8% 0px', threshold: 0.08})
  return observer
}

/** v-reveal="index" – the value is the stagger position inside its group. */
export const vReveal = {
  mounted(el, binding) {
    el.classList.add('reveal')
    el.style.setProperty('--d', (Number(binding.value) || 0) * 60 + 'ms')
    const o = shared()
    if (!o || reducedMotion()) el.classList.add('in')
    else o.observe(el)
  },
  unmounted(el) { observer?.unobserve(el) },
}

/** Ease-out count from 0 to `to`; calls `step(value)` per frame. Reduced motion jumps to the end state. */
export function countUp(to, step, duration = 1200) {
  if (reducedMotion() || !Number.isFinite(to)) { step(to); return () => {} }
  let raf = 0
  const start = performance.now()
  const frame = now => {
    const t = Math.min(1, (now - start) / duration)
    step(to * (1 - Math.pow(1 - t, 3)))
    if (t < 1) raf = requestAnimationFrame(frame)
  }
  raf = requestAnimationFrame(frame)
  return () => cancelAnimationFrame(raf)
}
