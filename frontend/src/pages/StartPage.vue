<script setup>
import {computed, ref, onMounted, defineAsyncComponent} from 'vue'
import {useResource} from '../useResource.js'
import {fmt} from '../metricDefinitions.js'
import {openCheck} from '../session.js'
import {vReveal, reducedMotion} from '../ui/motion.js'
import PlaceSearch from '../ui/PlaceSearch.vue'
import RainCanvas from '../ui/RainCanvas.vue'
import CountUp from '../ui/CountUp.vue'
import IntervalPlot from '../ui/IntervalPlot.vue'
import StatusChip from '../ui/StatusChip.vue'
import InfoTip from '../InfoTip.vue'
const LiveExample = defineAsyncComponent(() => import('../map/LiveExample.vue'))

const {data: v04, error: e04, loading: l04, reload: r04} = useResource('/api/results_v04')
const {data: pg} = useResource('/api/pruefgebiete')
const n = v => Math.round(v).toLocaleString('de-AT')
const signed = v => (v > 0 ? '+' : v < 0 ? '−' : '') + fmt(Math.abs(v))
const range = (iv, f = fmt) => `[${f(iv[0])}; ${f(iv[1])}]`
const primary = computed(() => v04.value?.test.primary)
// Signature: the illustration gives way to the real map. Headline and search leave (250 ms), the image
// zooms and loses focus and colour (500 ms), then the Hang-Check flies in over real terrain.
const leaving = ref(false)
// Optional hero clip (generated from the same illustration): only on wide screens, never with reduced
// motion or data saver; the still image stays underneath and the page is complete without it.
const clip = ref(false), clipPlaying = ref(false)
onMounted(() => {
  clip.value = !reducedMotion() && !navigator.connection?.saveData && window.matchMedia('(min-width: 901px)').matches
})
const webgl = () => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')) } catch { return false } }
function arrive(place) {
  if (reducedMotion() || !webgl()) return openCheck(place)
  leaving.value = true
  setTimeout(() => openCheck(place, {fromHero: true}), 480)
}
const part = computed(() => v04.value?.counts.partition)
const years = computed(() => {
  const list = (pg.value?.jahre || []).map(j => j.jahr)
  return list.length ? `${Math.min(...list)} bis ${Math.max(...list)}` : ''
})
const steps = [
  {title: 'Ort wählen', text: 'Gemeinde eintippen, auf die Karte tippen oder den eigenen Standort nehmen. Dazu den Umkreis von 1 bis 3 km.'},
  {title: '„Starkregen erwartet“ einschalten', text: 'Der Schalter öffnet die Ansicht für den Starkregenfall. Er ruft kein Wetter ab und ändert nichts an der Einstufung.'},
  {title: 'Hänge sehen, die man zuerst ansieht', text: 'Rot sind die auffälligsten Hänge im Umkreis, Orange die nächsten. Fünf Prüfpunkte mit Höhe, Neigung und Landbedeckung im Klartext.'},
]
const uses = [
  {who: 'Gemeinde nach dem Unwetter', text: 'Welche Hänge sieht sich die Begehung zuerst an? Die Prüfliste ordnet den Umkreis vor dem ersten Rundgang und lässt sich ausdrucken.'},
  {who: 'Straßenerhalter auf Kontrollfahrt', text: 'Wo entlang der Strecke lohnt sich der erste Blick hangaufwärts? Die Prüfpunkte geben eine begründete Reihenfolge.'},
  {who: 'Anrainer am Hang', text: 'Wie steht mein Hang im Vergleich zu den Hängen ringsum? Und was sagt die Einstufung ausdrücklich nicht?'},
]
const limits = [
  ['Talwacht warnt nicht.', 'Für aktuelle Unwetterwarnungen gelten GeoSphere Austria und die Landeswarnzentralen. Im Notfall: 112 oder Feuerwehr 122.'],
  ['Nicht markiert heißt nicht sicher.', 'Die Einstufung ist relativ. In jedem Umkreis sind Hänge markiert, und auch nicht markierte Hänge können abgehen.'],
  ['Kein Wetter im Modell.', 'Ein Zusatznutzen von Wetterdaten ist in keiner Studie belegt. Der Schalter wählt nur die Ansicht.'],
  ['Gelernt aus Meldungen.', 'Rutschungen nahe Straßen und Häusern werden eher gemeldet. Ein Teil des Signals kann von der Meldung kommen, nicht vom Hang.'],
]
</script>

<template>
  <section class="hero" :class="{leaving}" aria-labelledby="hero-title">
    <picture class="hero-img">
      <source media="(max-width: 900px)" srcset="/media/tal-1200.webp">
      <img src="/media/tal.webp" width="2400" height="1029" fetchpriority="high" decoding="async"
           alt="KI-generierte Illustration: Alpental zur blauen Stunde vor einem Gewitter, Dorf mit Kirche, Bach und Straße.">
    </picture>
    <video v-if="clip" class="hero-video" :class="{on: clipPlaying}" muted playsinline loop autoplay preload="auto" poster="/media/tal.webp" aria-hidden="true" @playing="clipPlaying = true">
      <source src="/media/tal-clip.webm" type="video/webm"><source src="/media/tal-clip.mp4" type="video/mp4">
    </video>
    <div class="hero-shade" aria-hidden="true"></div>
    <RainCanvas v-if="!clipPlaying"/>
    <div class="hero-copy wrap">
      <p class="eyebrow hero-eyebrow">Hang-Check bei Starkregen · Österreich</p>
      <h1 id="hero-title">Wo zuerst hinschauen, wenn der Starkregen kommt.</h1>
      <p class="hero-sub">Talwacht zeigt für deinen Ort die Hänge, die man bei Starkregen zuerst ansehen sollte, entwickelt und geprüft an {{ v04 ? n(v04.counts.complete_groups) + ' ' : '' }}dokumentierten Rutschungen in Österreich.</p>
      <PlaceSearch class="hero-search" tone="dark" @select="arrive"/>
    </div>
    <span class="ai-credit">KI-generierte Illustration</span>
  </section>

  <section class="section steps" aria-labelledby="steps-title">
    <div class="wrap steps-grid">
      <figure class="steps-img" v-reveal>
        <picture><source media="(max-width: 700px)" srcset="/media/hang-600.webp"><img src="/media/hang.webp" width="1200" height="1500" loading="lazy" decoding="async"
          alt="KI-generierte Illustration: Person im Regen vor einem Bauernhaus, Blick auf den steilen Hang darüber."></picture>
        <span class="ai-credit">KI-generierte Illustration</span>
      </figure>
      <div class="steps-body">
        <p class="eyebrow" v-reveal>So geht der Hang-Check</p>
        <h2 id="steps-title" v-reveal="1">Drei Schritte, eine begründete Reihenfolge.</h2>
        <ol class="steps-list">
          <li v-for="(s, i) in steps" :key="s.title" class="card" v-reveal="i + 2">
            <span class="step-no" aria-hidden="true">{{ i + 1 }}</span>
            <div><h3>{{ s.title }}</h3><p>{{ s.text }}</p></div>
          </li>
        </ol>
        <a class="btn btn-primary" href="#/check" v-reveal="5">Jetzt prüfen <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a>
      </div>
    </div>
  </section>

  <LiveExample/>

  <section class="section basis" aria-labelledby="basis-title">
    <div class="wrap">
      <div class="basis-head">
        <p class="eyebrow" v-reveal>Worauf das beruht</p>
        <h2 id="basis-title" v-reveal="1">Echte Ereignisse, ein fairer Vergleich, ein versiegelter Test.</h2>
      </div>
      <p v-if="l04" class="state" role="status">Kennzahlen werden aus den gespeicherten Ergebnissen geladen …</p>
      <div v-else-if="e04" class="state state-error" role="alert"><p>Kennzahlen nicht verfügbar. {{ e04 }}</p><button type="button" @click="r04">Erneut laden</button></div>
      <div v-else-if="v04" class="basis-grid">
        <article class="card basis-card" v-reveal="0">
          <StatusChip status="Datenbasis V0.4"/>
          <p class="big-num"><CountUp :value="v04.counts.complete_groups" :format="n"/></p>
          <h3>dokumentierte Rutschungen<template v-if="years">, {{ years }}</template></h3>
          <p>Jede mit fünf ähnlichen Nachbarhängen ohne Meldung verglichen, alle zum selben Stichtag.</p>
          <p class="basis-foot mono">{{ n(part.development.events) }} zum Entwickeln · {{ n(part.sealed_test.events) }} nur für den Schlusstest · {{ n(part.sealed_test.units) }} unabhängige Episoden im Test</p>
        </article>
        <article class="card basis-card" v-reveal="1">
          <StatusChip status="versiegelt"/>
          <p class="big-num"><CountUp :value="primary.value" :format="fmt"/></p>
          <h3><InfoTip term="withinGroupAuc" :value="primary.value" label="Trennung im versiegelten Test"/></h3>
          <p>Der gemeldete Hang landet klar öfter vor seinen Nachbarn als bei zufälliger Reihenfolge.</p>
          <IntervalPlot :value="primary.value" :interval="primary.ci95" :reference="primary.chance" label="Gelände und Wetter, lokale AUC im versiegelten Test"/>
          <p class="basis-foot mono">95-%-Intervall {{ range(primary.ci95) }} · {{ n(part.sealed_test.units) }} Einheiten</p>
        </article>
        <article class="card basis-card" v-reveal="2">
          <StatusChip status="versiegelt"/>
          <p class="big-num"><CountUp :value="primary.combined_minus_static.mean" :format="signed"/></p>
          <h3><InfoTip term="weatherDelta" :value="primary.combined_minus_static.mean" label="Wetter bringt keinen belegten Zusatz"/></h3>
          <p>Das Intervall schließt null ein. Deshalb nutzt der Hang-Check nur Gelände, Landbedeckung und Geologie.</p>
          <IntervalPlot :value="primary.combined_minus_static.mean" :interval="primary.combined_minus_static.ci95" :reference="0" reference-label="kein Unterschied" :min="-0.15" :max="0.25" signed tone="grey" label="Zusatz durch Wetter gegenüber Gelände allein"/>
          <p class="basis-foot mono">95-%-Intervall {{ range(primary.combined_minus_static.ci95, signed) }} · gepaart</p>
        </article>
      </div>
      <a class="link basis-more" href="#/belastbar" v-reveal>Alle Ergebnisse, auch die unbequemen <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a>
    </div>
  </section>

  <section class="uses" aria-labelledby="uses-title">
    <figure class="uses-img">
      <picture><source media="(max-width: 900px)" srcset="/media/morgen-960.webp"><img src="/media/morgen.webp" width="1920" height="1086" loading="lazy" decoding="async"
        alt="KI-generierte Illustration: Morgen nach dem Unwetter, frische Rutschung bis auf die Straße, zwei Personen in Warnkleidung."></picture>
      <span class="ai-credit">KI-generierte Illustration</span>
    </figure>
    <div class="wrap uses-body">
      <div class="uses-head">
        <p class="eyebrow">Wofür es gedacht ist</p>
        <h2 id="uses-title">Für den Morgen danach.</h2>
      </div>
      <ul class="uses-list">
        <li v-for="(u, i) in uses" :key="u.who" class="card" v-reveal="i"><h3>{{ u.who }}</h3><p>{{ u.text }}</p></li>
      </ul>
    </div>
  </section>

  <section class="section dark limits" aria-labelledby="limits-title">
    <div class="wrap">
      <p class="eyebrow">Was Talwacht nicht kann</p>
      <h2 id="limits-title" class="limits-title">Ehrlich, bevor du es nutzt.</h2>
      <ul class="limits-list">
        <li v-for="([t, d], i) in limits" :key="t" v-reveal="i"><strong>{{ t }}</strong><span>{{ d }}</span></li>
      </ul>
      <a class="link limits-link" href="#/belastbar">Wie belastbar ist das? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a>
      <div class="closing">
        <p class="closing-line">Weniger Rätselraten nach dem Unwetter.</p>
        <a class="btn btn-primary" href="#/check">Hang prüfen</a>
      </div>
    </div>
  </section>
</template>

<style>
.hero{position:relative;min-height:100svh;display:flex;align-items:flex-start;overflow:hidden;background:var(--slate-900);color:#fff;isolation:isolate}
.hero-img,.hero-img img{position:absolute;inset:0;width:100%;height:100%}
.hero-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 62%;opacity:0;transition:opacity .8s ease,transform .5s var(--ease),filter .5s var(--ease)}
.hero-video.on{opacity:1}
.hero.leaving .hero-video{transform:scale(1.08);filter:blur(8px) saturate(.45)}
.hero-img img{object-fit:cover;object-position:50% 62%;transform-origin:50% 60%}
.hero-shade{position:absolute;inset:0;z-index:1;background:
  linear-gradient(90deg,rgb(14 24 34 / .62) 0%,rgb(14 24 34 / .28) 46%,rgb(14 24 34 / 0) 70%),
  linear-gradient(180deg,rgb(14 24 34 / .5) 0%,rgb(14 24 34 / 0) 30%,rgb(14 24 34 / 0) 62%,rgb(14 24 34 / .55) 100%)}
.hero-copy{position:relative;z-index:3;padding-top:clamp(120px,17vh,180px);padding-bottom:64px}
.hero-eyebrow{color:rgb(255 255 255 / .82)}
.hero h1{max-width:15ch;font-size:clamp(2.6rem,5.3vw,5.4rem);color:#fff;text-shadow:0 2px 30px rgb(14 24 34 / .35)}
.hero-sub{margin-top:24px;max-width:46ch;font-size:clamp(1.08rem,1.5vw,1.3rem);line-height:1.55;color:rgb(255 255 255 / .9)}
.hero-search{margin-top:34px}
.hero-img img,.hero-copy>*,.hero .rain{transition:transform .5s var(--ease),filter .5s var(--ease),opacity .25s ease}
.hero.leaving .hero-img img{transform:scale(1.08);filter:blur(8px) saturate(.45)}
.hero.leaving .hero-copy>*:not(.hero-search){opacity:0}
.hero.leaving .hero-search{transform:translateY(-120px);opacity:0;transition:transform .35s var(--ease),opacity .3s ease}
.hero.leaving .rain{opacity:0}

.steps-grid{display:grid;grid-template-columns:5fr 7fr;gap:clamp(32px,6vw,88px);align-items:center}
.steps-img{position:relative;margin:0;border-radius:var(--r-card);overflow:hidden;aspect-ratio:4/5;box-shadow:var(--shadow-lift)}
.steps-img img{width:100%;height:100%;object-fit:cover}
.steps-body h2{margin-bottom:36px}
.steps-list{list-style:none;margin:0 0 36px;padding:0;display:grid;gap:14px}
.steps-list li{display:grid;grid-template-columns:auto 1fr;gap:20px;padding:22px 24px}
.step-no{font:650 2.4rem/1 var(--f-display);font-stretch:125%;color:var(--moss);min-width:1.1em}
.steps-list h3{margin-bottom:6px}
.steps-list p{color:var(--ink-2)}

.basis{background:var(--paper-2)}
.basis-head{max-width:760px;margin-bottom:48px}
.basis-grid{display:grid;grid-template-columns:1.05fr 1fr 1fr;gap:20px;align-items:stretch}
.basis-card{display:flex;flex-direction:column;gap:12px;padding:26px 26px 22px}
.basis-card .chip{align-self:flex-start;margin-bottom:6px}
.basis-card .big-num{margin:6px 0 2px;color:var(--ink)}
.basis-card h3{font-size:1.2rem}
.basis-card h3 .infotip-text{font:inherit}
.basis-card > p:not(.big-num):not(.basis-foot){color:var(--ink-2)}
.basis-foot{margin-top:auto;padding-top:10px;font-size:.82rem;color:var(--ink-2);border-top:1px solid var(--line)}
.basis-more{margin-top:32px}

.uses{position:relative;padding-bottom:var(--section)}
.uses-img{position:relative;margin:0;height:clamp(380px,62vw,760px)}
.uses-img img{width:100%;height:100%;object-fit:cover}
.uses-img::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgb(14 24 34 / .55),rgb(14 24 34 / 0) 40%,rgb(245 243 238 / 0) 70%,var(--paper) 100%)}
.uses-body{position:relative;margin-top:calc(-1 * clamp(200px,24vw,330px));z-index:2}
.uses-head{color:#fff;position:absolute;top:calc(-1 * clamp(180px,32vw,400px));max-width:560px}
.uses-head .eyebrow{color:rgb(255 255 255 / .85)}
.uses-head h2{color:#fff;text-shadow:0 2px 24px rgb(14 24 34 / .4)}
.uses-list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.uses-list li{padding:26px}
.uses-list li:nth-child(2){transform:translateY(28px)}
.uses-list li:nth-child(2).reveal:not(.in){transform:translateY(44px)}
.uses-list h3{margin-bottom:10px}
.uses-list p{color:var(--ink-2)}

.limits-title{color:#fff;max-width:14ch}
.limits-list{list-style:none;margin:48px 0 0;padding:0;display:grid;grid-template-columns:repeat(2,1fr);gap:0 48px}
.limits-list li{display:flex;flex-direction:column;gap:8px;padding:26px 0;border-top:1px solid rgb(255 255 255 / .14)}
.limits-list strong{font:650 1.5rem/1.15 var(--f-display);font-stretch:115%;letter-spacing:-.01em;color:#fff}
.limits-list span{color:var(--on-dark-2);max-width:48ch}
.limits-link{margin-top:28px;color:var(--glacier)}
.closing{margin-top:clamp(80px,10vw,140px);display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:28px;padding-top:40px;border-top:1px solid rgb(255 255 255 / .14)}
.closing-line{font:650 var(--t-h2)/1.02 var(--f-display);font-stretch:118%;letter-spacing:-.02em;color:#fff;max-width:16ch}

@media (max-width:1000px){
  .basis-grid{grid-template-columns:1fr 1fr}
  .basis-grid .basis-card:first-child{grid-column:1/-1}
}
@media (max-width:860px){
  .steps-grid{grid-template-columns:1fr}
  .steps-img{aspect-ratio:4/3;max-height:440px}
  .uses-list{grid-template-columns:1fr}
  .uses-list li:nth-child(2),.uses-list li:nth-child(2).reveal:not(.in){transform:none}
  .uses-body{margin-top:-120px}
  .uses-head{position:relative;top:auto;margin:0 0 28px;color:var(--ink)}
  .uses-head h2{color:var(--ink);text-shadow:none}
  .uses-head .eyebrow{color:var(--ink-2)}
  .uses-img{height:56vw;min-height:260px}
  .uses-img::after{background:linear-gradient(180deg,rgb(245 243 238 / 0) 50%,var(--paper) 100%)}
  .uses-body{margin-top:0}
  .limits-list{grid-template-columns:1fr}
}
@media (max-width:640px){
  .basis-grid{grid-template-columns:1fr}
  .hero-copy{padding-top:120px}
  .hero-img img{object-position:58% 60%}
  .hero-shade{background:linear-gradient(180deg,rgb(14 24 34 / .66) 0%,rgb(14 24 34 / .38) 55%,rgb(14 24 34 / .7) 100%)}
}
</style>
