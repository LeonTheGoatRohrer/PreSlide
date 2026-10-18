<script setup>
// Entry to the unchanged research pages (Projekt, Vorgehen, Ergebnisse im Detail) and the Hangkarte.
const areas = [
  { href: '#/projekt', label: 'Projekt', title: 'Forschungsfrage und Kurzfassung', text: 'Was ein Hang vor dem Ereignis verrät, die Idee des Vergleichs und der Ausblick.' },
  { href: '#/vorgehen', label: 'Vorgehen', title: 'Sechs Schritte vom Inventar zur Auswertung', text: 'Echte Beispielgruppe auf der Karte, 60 Tage Wettergeschichte, Schutzregeln und Datenquellen.' },
  { href: '#/ergebnisse', label: 'Ergebnisse im Detail', title: 'Alle Studien getrennt dargestellt', text: 'Hauptstudie V0.4, Ergänzungsstudie V0.5, alle Modellläufe im Vergleich und die Historie V0 bis V0.3.' },
  { href: '#/hangkarte', label: 'Hangkarte', title: 'Relative Anteile auf einer 3D-Ansicht', text: 'Anwendung des eingefrorenen V0.5-Geländemodells in einem frei gewählten Gebiet. Nur relative Anteile innerhalb einer Vergleichsgruppe, keine Aussage darüber, ob oder wann ein Hang abgeht.' },
]
const direct = [
  ['#/ergebnisse/v04', 'V0.4: alle Modelle und Testdetails'],
  ['#/ergebnisse/v05', 'V0.5: Umgebungshänge und Karten'],
  ['#/ergebnisse/vergleich', 'Benchmarks: alle Untersuchungen im Vergleich'],
  ['#/ergebnisse/historie', 'Historie und Ereignis-Explorer'],
  ['#/vorgehen/beispiel', 'Beispielgruppe mit Wetterverlauf'],
]
</script>
<template>
  <section class="page-intro compact"><p class="eyebrow">Forschungsbereich</p><h1>Die ganze Untersuchung.<br><span>Unverändert, vollständig.</span></h1></section>
  <p class="bf-text fo-intro">Hier liegen die ausführlichen Seiten des Forschungsprototyps mit allen Studien, Karten, Modellvergleichen und früheren Untersuchungen. Inhalte und Kennzahlen sind dieselben wie bisher; frühere Links führen weiterhin hierher.</p>
  <div class="fo-areas">
    <a v-for="a in areas" :key="a.href" :href="a.href"><span>{{ a.label }}</span><strong>{{ a.title }}</strong><p>{{ a.text }}</p></a>
  </div>
  <nav class="bf-more" aria-label="Direkt zu Detailbereichen">
    <p class="eyebrow">Direkt zu</p>
    <a v-for="[href, label] in direct" :key="href" :href="href">{{ label }}</a>
  </nav>
</template>
