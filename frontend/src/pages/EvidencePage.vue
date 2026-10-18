<script setup>
// "Wie belastbar": every claim as a card with its stored figures, interval, units and study status.
// All figures come from GET /api/studien (stored report values); studies not in this checkout say so.
import {computed} from 'vue'
import {useResource} from '../useResource.js'
import {formatValue, plotScale} from '../studien.js'
import {vReveal} from '../ui/motion.js'
import StatusChip from '../ui/StatusChip.vue'
import IntervalPlot from '../ui/IntervalPlot.vue'
import InfoTip from '../InfoTip.vue'

const {data, error, loading, reload} = useResource('/api/studien')
const byId = computed(() => Object.fromEntries((data.value?.studien ?? []).map(s => [s.id, s])))
// Which stored figures (by position in the registry) support which sentence.
const claims = [
  {id: 'gelaende', titel: 'Das Gelände trennt über Zufall.', text: 'Im versiegelten Test landet der gemeldete Hang deutlich öfter vor seinen fünf ähnlichen Nachbarn als bei zufälliger Reihenfolge. Auf ungesehenen Episoden aus Medienberichten hält das.', term: 'withinGroupAuc',
    belege: [['v04', 1], ['v04', 0], ['v09', 0]]},
  {id: 'wetter', titel: 'Wetter bringt keinen belegten Zusatz.', text: 'In keiner Variante schließt das Intervall des Wetterzusatzes die Null aus. Deshalb nutzt der Hang-Check kein Wetter. Das heißt nicht, dass Regen keine Rolle spielt: Das Wetterraster ist 1 km grob.', term: 'weatherDelta',
    belege: [['v04', 2], ['v05', 2], ['v06', 0], ['v09', 1]]},
  {id: 'meldebias', titel: 'Ein Teil des Signals kommt von der Meldung.', text: 'Rutschungen nahe Straßen und Häusern werden eher entdeckt. Der Abstand zur Infrastruktur trennt allein sehr stark. Bei gleicher Erreichbarkeit trennt das Gelände weiterhin, aber schwächer.',
    belege: [['v07', 0], ['v07', 1]], extra: 'v07b'},
  {id: 'extrem', titel: 'Vor Ereignissen regnet es am selben Ort öfter extrem.', text: 'Derselbe Ort zu gewöhnlichen Zeiten als Vergleich: Vor gemeldeten Ereignissen liegt der Regen viel öfter über dem örtlichen 95. Perzentil. Ein Zusammenhang mit dem Zeitpunkt, keine Aussage über einen einzelnen Hang.',
    belege: [['extremwetter', 0], ['extremwetter', 1], ['v08', 0]]},
  {id: 'gebiet', titel: 'Gebietstest an ungesehenen Gebieten.', text: 'Vorab registrierter Test der Prüfstufen an Hangmuren-Gebieten, die kein Modell gesehen hat.', belege: [], nurWennDa: 'gebietstest'},
  {id: 'hangmuren', titel: 'Bei reinen Hangmuren trennt das Gelände kaum.', text: 'Werden nur eindeutig als Hangmure gemeldete Ereignisse betrachtet, unterscheidet das Gelände den betroffenen Hang kaum von seinen Nachbarn. Eine Geländerangfolge darf dort keinen Hang aussortieren.',
    belege: [['hangmuren_pilot', 0]]},
  {id: 'satellit', titel: 'Satellitenbilder erkennen frische Rutschungen, finden aber keine neuen.', text: 'Nach dem Ereignis sind Rutschung und Kontrollhang auf Sentinel-2-Bildern gut zu unterscheiden. Die Suche nach unbekannten Rutschungen findet bekannte nur mäßig wieder; neue Kandidaten sind nicht bestätigt.',
    belege: [['satellite', 0], ['satellite', 1], ['satellite', 2]]},
  {id: 'international', titel: 'Im Ausland überträgt Gelände nicht besser als die Neigung.', text: 'In Nepal und Japan, vorab registriert und einmal bewertet: Das Geländemodell ist nicht besser als die Neigung allein.',
    belege: [['susceptibility_v01', 0], ['susceptibility_v02', 0]]},
]
const limits = [
  ['Rückblick statt Warnung', 'Alle Ergebnisse stammen aus vergangenen Ereignissen. Talwacht ist kein Warnsystem und keine Gefahrenkarte.'],
  ['Kontrollen sind Pseudo-Negative', 'Ein Vergleichshang ohne Meldung kann trotzdem gerutscht sein. Fehlende Meldung ist kein Nachweis von Stabilität.'],
  ['Wenige unabhängige Einheiten', 'Ein Sturm liefert viele Ereignisse. Für die Unsicherheit zählen Wetterepisoden, nicht Hänge; im versiegelten Test sind es nur wenige.'],
  ['Meldeverzerrung', 'Landbedeckung und Siedlungsnähe beeinflussen, wo Ereignisse entdeckt und gemeldet werden.'],
  ['Rangfolge statt Häufigkeit', 'Die Werte ordnen Hänge innerhalb einer Vergleichsgruppe. Sie sagen nicht, wie oft ein Hang rutscht.'],
  ['Grobe Eingangsdaten', 'Wetter auf 1 km, Landbedeckung und Geologie in grobem Maßstab, Gelände Stand 2000. Kleinräumiges geht verloren.'],
]
function rows(claim) {
  return claim.belege.map(([id, i]) => ({study: byId.value[id], fig: byId.value[id]?.kennzahlen?.[i], id}))
    .filter(r => r.study)
}
const visibleClaims = computed(() => claims.filter(c => !c.nurWennDa || byId.value[c.nurWennDa]?.verfuegbar))
const iv = f => `${formatValue(f.art, f.intervall[0])} bis ${formatValue(f.art, f.intervall[1])}`
</script>

<template>
  <section class="page-head wrap ev-head">
    <p class="eyebrow">Wie belastbar</p>
    <h1>Wir zeigen dir nicht nur, was funktioniert, sondern auch, was nicht.</h1>
    <p class="lead">Jede Aussage mit ihrer Zahl, dem Unsicherheitsintervall, der Zahl unabhängiger Einheiten und dem Status der Studie. Nur ein Test des Projekts war versiegelt; alles andere ist als explorativ gekennzeichnet.</p>
    <ul class="ev-legend" aria-label="Status">
      <li><StatusChip status="versiegelt"/><span>vorab registriert, genau einmal ausgewertet</span></li>
      <li><StatusChip status="explorativ"/><span>Hinweis auf bereits gesehenen Daten</span></li>
      <li><StatusChip status="demonstration"/><span>Ablauf an einem Beispiel</span></li>
    </ul>
  </section>

  <p v-if="loading" class="wrap state" role="status">Ergebnisse werden aus den gespeicherten Berichten geladen …</p>
  <div v-else-if="error" class="wrap state state-error" role="alert"><p>Ergebnisse nicht verfügbar. {{ error }}</p><button type="button" @click="reload">Erneut laden</button></div>
  <div v-else-if="data" class="wrap ev-list">
    <article v-for="c in visibleClaims" :id="c.id" :key="c.id" class="card ev-card" v-reveal>
      <header class="ev-card-head">
        <h2>{{ c.titel }}</h2>
        <p>{{ c.text }}<template v-if="c.term"> <InfoTip :term="c.term" label=""/></template></p>
      </header>
      <div v-if="rows(c).length" class="ev-rows">
        <div v-for="r in rows(c)" :key="r.id + r.fig?.label" class="ev-row">
          <div class="ev-row-meta"><StatusChip :status="r.study.status"/><a class="ev-study" :href="'#/studien#' + r.study.id">{{ r.study.kurztitel ?? r.study.titel }}</a></div>
          <template v-if="r.fig?.verfuegbar">
            <div class="ev-row-fig"><strong>{{ formatValue(r.fig.art, r.fig.wert) }}</strong><span>{{ r.fig.label }}</span></div>
            <div class="ev-row-plot">
              <IntervalPlot v-if="plotScale(r.fig)" :value="r.fig.wert" :interval="r.fig.intervall" :reference="plotScale(r.fig).reference ?? 0" :reference-label="r.fig.bezug_label ?? (r.fig.art === 'delta' ? 'kein Unterschied' : 'Zufall')" :min="plotScale(r.fig).min" :max="plotScale(r.fig).max" :signed="r.fig.art === 'delta'" :tone="r.fig.art === 'delta' ? 'grey' : 'moss'" :label="r.fig.label"/>
              <p class="mono ev-row-iv"><template v-if="r.fig.intervall">{{ r.fig.intervall_art ?? '95-%-Intervall' }} {{ iv(r.fig) }}</template><template v-else>Kein Intervall gespeichert</template><template v-if="r.fig.einheiten != null"> · {{ r.fig.einheiten.toLocaleString('de-AT') }} {{ r.fig.einheiten_label ?? 'unabhängige Einheiten' }}</template></p>
            </div>
          </template>
          <p v-else class="ev-row-na">{{ r.study.status === 'lokal' ? 'Bericht liegt nur lokal und ist in diesem Stand nicht enthalten.' : 'In diesem Stand noch nicht verfügbar.' }}</p>
        </div>
      </div>
      <p v-if="c.extra && byId[c.extra]?.verfuegbar" class="ev-extra">Korrektur verfügbar: <a :href="'#/studien#' + c.extra">{{ byId[c.extra].titel }}</a></p>
      <p v-if="c.nurWennDa" class="ev-extra"><a :href="'#/studien#' + c.nurWennDa">Details im Studienatlas</a></p>
    </article>
  </div>

  <section class="section dark ev-limits" aria-labelledby="ev-lim">
    <div class="wrap">
      <p class="eyebrow">Grenzen</p>
      <h2 id="ev-lim">Was diese Zahlen nicht sagen.</h2>
      <dl class="ev-limit-list">
        <div v-for="([t, d], i) in limits" :key="t" v-reveal="i % 2"><dt>{{ t }}</dt><dd>{{ d }}</dd></div>
      </dl>
      <a class="link ev-atlas" href="#/studien">Alle Studien im Studienatlas</a>
    </div>
  </section>
</template>

<style>
.ev-head h1{max-width:22ch;font-size:clamp(2.4rem,5vw,4.4rem)}
.ev-legend{list-style:none;margin:28px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:10px 24px}
.ev-legend li{display:flex;align-items:center;gap:10px;font-size:.92rem;color:var(--ink-2)}
.ev-list{display:grid;grid-template-columns:minmax(0,1fr);gap:22px;padding-bottom:var(--section)}
.ev-card-head>*,.ev-row>*{min-width:0}
.ev-card{padding:clamp(22px,3vw,36px)}
.ev-card-head{display:grid;grid-template-columns:5fr 7fr;gap:16px 48px;align-items:start;padding-bottom:20px}
.ev-card-head h2{font-size:clamp(1.6rem,2.6vw,2.3rem)}
.ev-card-head p{color:var(--ink-2)}
.ev-rows{display:grid;border-top:1px solid var(--line-2)}
.ev-row{display:grid;grid-template-columns:220px 1.1fr 1.4fr;gap:12px 28px;align-items:center;padding:18px 0;border-bottom:1px solid var(--line)}
.ev-row-meta{display:flex;flex-direction:column;align-items:flex-start;gap:8px}
.ev-study{font-weight:600;font-size:.95rem}
.ev-row-fig{display:flex;flex-direction:column;gap:4px}
.ev-row-fig strong{font:650 2.2rem/1 var(--f-display);font-stretch:122%;font-variant-numeric:tabular-nums}
.ev-row-fig span{font-size:.9rem;color:var(--ink-2)}
.ev-row-iv{font-size:12px;color:var(--ink-2);margin-top:4px}
.ev-row-na{grid-column:2/-1;color:var(--ink-2);font-style:italic}
.ev-extra{margin-top:14px;font-size:.95rem}
.ev-limits h2{color:#fff;margin-bottom:36px}
.ev-limit-list{margin:0;display:grid;grid-template-columns:1fr 1fr;gap:0 48px}
.ev-limit-list div{padding:22px 0;border-top:1px solid rgb(255 255 255 / .14)}
.ev-limit-list dt{font:650 1.3rem/1.2 var(--f-display);font-stretch:112%;color:#fff;margin-bottom:6px}
.ev-limit-list dd{margin:0;color:var(--on-dark-2)}
.ev-atlas{margin-top:28px;color:var(--glacier)}
@media (max-width:900px){.ev-card-head{grid-template-columns:minmax(0,1fr)}.ev-row{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.ev-row-meta{grid-column:1/-1;flex-direction:row;align-items:center}.ev-row-plot{grid-column:1/-1}.ev-limit-list{grid-template-columns:1fr}}
@media (max-width:560px){.ev-row{grid-template-columns:minmax(0,1fr)}}
</style>
