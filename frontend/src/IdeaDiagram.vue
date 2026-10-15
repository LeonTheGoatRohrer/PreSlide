<template>
  <figure class="idea-diagram">
    <svg viewBox="0 0 720 320" role="img" aria-labelledby="idea-t idea-d">
      <title id="idea-t">Die Idee im Überblick</title>
      <desc id="idea-d">Ein Hang mit dokumentierter Rutschung wird mit fünf ähnlichen Hängen in der Umgebung verglichen. Alle werden zum selben Zeitpunkt t0 betrachtet; nur Information davor wird verwendet.</desc>
      <g class="id-contours" fill="none" stroke-width="1">
        <path d="M0 210c80-60 140-110 230-120s150 40 240 20 150-80 250-60"/>
        <path d="M0 240c90-55 150-90 235-100s150 40 235 20 150-70 250-50"/>
        <path d="M0 270c95-50 160-70 240-80s150 40 235 20 150-60 245-40"/>
      </g>
      <g class="id-controls">
        <circle cx="90" cy="168" r="9"/><circle cx="215" cy="108" r="9"/><circle cx="440" cy="118" r="9"/><circle cx="565" cy="84" r="9"/><circle cx="655" cy="104" r="9"/>
      </g>
      <g class="id-event"><circle cx="330" cy="100" r="15"/><text x="330" y="105" text-anchor="middle">E</text></g>
      <text class="id-note" x="330" y="64" text-anchor="middle">Ereignishang</text>
      <text class="id-note" x="372" y="196" text-anchor="middle">5 ähnliche Kontrollhänge</text>
      <g class="id-time">
        <line x1="40" y1="262" x2="560" y2="262"/><line x1="560" y1="252" x2="560" y2="272" class="id-t0"/><line x1="560" y1="262" x2="690" y2="262" class="id-after"/>
        <text x="40" y="302">60 Tage Vorgeschichte</text><text x="560" y="240" text-anchor="middle" class="id-t0-label">t₀</text><text x="625" y="302" text-anchor="middle" class="id-after-label">ausgeschlossen</text>
      </g>
    </svg>
    <figcaption>Alle Hänge einer Gruppe teilen denselben Zeitpunkt t₀. Verwendet wird nur Information davor.</figcaption>
  </figure>
</template>
