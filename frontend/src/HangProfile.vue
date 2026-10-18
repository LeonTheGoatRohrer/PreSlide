<script setup>
// Schematic longitudinal section: rain on a slope → check point → possible runout → road and houses.
// Purely illustrative (not to scale, no data); the three numbered marks match the chain on the start page.
</script>
<template>
  <figure class="hang-profile">
    <svg viewBox="0 0 640 430" role="img" aria-labelledby="hp-title hp-desc">
      <title id="hp-title">Schematischer Längsschnitt eines Hanges</title>
      <desc id="hp-desc">Regen fällt auf einen steilen Hang. Ein markierter Prüfpunkt liegt im oberen Hangdrittel. Eine Linie zeigt einen möglichen Auslauf hangabwärts bis zu einem Ablagerungsfächer im Tal. Dort liegen eine Straße und zwei Gebäude.</desc>
      <g class="hp-rain" aria-hidden="true">
        <line v-for="i in 26" :key="i" :x1="(i * 23) % 330 + 20" :y1="12 + (i * 37) % 70" :x2="(i * 23) % 330 + 10" :y2="40 + (i * 37) % 70"/>
      </g>
      <path class="hp-ground" d="M0 104 C70 96 112 120 150 150 C210 196 262 240 318 276 C366 306 410 330 470 342 L640 344 L640 430 L0 430 Z"/>
      <path class="hp-bedrock" d="M0 170 C90 176 170 214 240 262 C300 302 380 352 470 372 L640 376"/>
      <path class="hp-fan" d="M392 330 C420 326 470 330 512 344 L392 344 Z"/>
      <path class="hp-runout" d="M184 176 C232 214 270 244 318 274 C356 298 392 322 446 336"/>
      <path class="hp-arrow" d="M434 327 L450 337 L433 343"/>
      <g class="hp-road">
        <rect x="492" y="338" width="148" height="9"/>
        <line x1="498" y1="342.5" x2="640" y2="342.5"/>
      </g>
      <g class="hp-house">
        <path d="M548 338 V312 L562 300 L576 312 V338 Z"/>
        <path d="M590 338 V318 L601 308 L612 318 V338 Z"/>
      </g>
      <g class="hp-check">
        <circle class="hp-ring" cx="178" cy="170" r="17"/>
        <circle cx="178" cy="170" r="5"/>
      </g>
      <g class="hp-marks">
        <g transform="translate(150 118)"><circle r="14"/><text y="5">1</text></g>
        <g transform="translate(336 248)"><circle r="14"/><text y="5">2</text></g>
        <g transform="translate(580 276)"><circle r="14"/><text y="5">3</text></g>
      </g>
      <g class="hp-labels" aria-hidden="true">
        <text x="172" y="112">Prüfpunkt</text>
        <text x="358" y="243">möglicher Auslauf</text>
        <text x="510" y="400">Straße, Gebäude</text>
        <text x="16" y="400" class="hp-small">Schema, nicht maßstäblich</text>
      </g>
    </svg>
  </figure>
</template>
