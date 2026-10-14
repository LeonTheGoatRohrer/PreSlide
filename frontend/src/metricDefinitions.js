// Central, static explanations for every technical number in the UI.
// Values are never stored here: components pass the real value from the results bundle,
// and interpret() turns it into a cautious, value-dependent sentence.

export const fmt = (v, d = 3) => Number(v).toLocaleString('de-AT', { minimumFractionDigits: d, maximumFractionDigits: d })
const pct = (v, d = 0) => fmt(v * 100, d) + ' %'
const SMALL = 'Bei nur wenigen unabhängigen Ereignisgruppen schwanken solche Werte stark.'

// Shared reading for every AUC-type number (0.5 = random order, 1 = perfect).
function aucReading(v) {
  if (v < 0.45) return 'Der Wert liegt unter dem Zufallsniveau von 0,5: Die Rangfolge ist hier eher umgekehrt. Bei kleinen Stichproben ist das meist Zufallsschwankung, kein umgekehrtes Signal.'
  if (v < 0.55) return 'Der Wert liegt nahe am Zufallsniveau von 0,5. Eine Trennung ist damit nicht erkennbar.'
  if (v < 0.65) return 'Der Wert liegt etwas über dem Zufallsniveau. ' + SMALL + ' Ein so kleiner Abstand ist oft nicht sicher von Zufall zu unterscheiden.'
  if (v < 0.8) return 'Das Modell ordnet in dieser Auswertung deutlich besser als eine zufällige Rangfolge, ist aber weit von einer perfekten Trennung entfernt. ' + SMALL
  return 'Hohe Trennung in genau dieser Stichprobe. ' + SMALL + ' Ohne unabhängige Bestätigung ist das kein Nachweis.'
}

function relativeToChance(v, chance) {
  const r = v / chance
  if (r < 0.9) return `Der Wert liegt unter der Zufallsreferenz von ${fmt(chance)}.`
  if (r < 1.15) return `Der Wert liegt nahe an der Zufallsreferenz von ${fmt(chance)}. Eine bessere Rangfolge als Zufall ist damit nicht erkennbar.`
  if (r < 1.6) return `Der Wert liegt etwas über der Zufallsreferenz von ${fmt(chance)}. ` + SMALL
  return `Der Wert liegt deutlich über der Zufallsreferenz von ${fmt(chance)}, ist aber weit vom Maximum 1 entfernt. ` + SMALL
}

export const metricDefinitions = {
  rocAuc: {
    label: 'ROC AUC',
    what: 'Wie gut das Modell Ereignishänge allgemein vor Kontrollhänge reiht – über alle Gruppen hinweg gemischt.',
    reference: '0,5 = zufällige Reihenfolge · 1,0 = perfekte Trennung',
    direction: 'higher',
    warning: 'Kein Wahrscheinlichkeitswert: 0,64 bedeutet nicht „64 % Rutschungsrisiko“.',
    format: v => fmt(v),
    interpret: aucReading,
  },
  withinGroupAuc: {
    label: 'AUC innerhalb der Gruppe',
    what: 'Wie oft der echte Rutschungshang einen höheren Modellwert erhält als einer seiner fünf Vergleichshänge aus derselben Gruppe. Gleichstände zählen halb.',
    reference: '0,5 = Zufall · 1,0 = Rutschungshang immer vor allen fünf Kontrollen',
    direction: 'higher',
    warning: 'Das ist die direkteste Kennzahl für die Forschungsfrage, weil nur Hänge desselben Ortes und Zeitpunkts verglichen werden.',
    format: v => fmt(v),
    interpret: aucReading,
  },
  averagePrecision: {
    label: 'Average Precision',
    what: 'Bewertet, ob die echten Rutschungshänge in der Gesamtrangliste weit oben stehen. Geeignet, wenn – wie hier – nur jeder sechste Hang ein Ereignishang ist.',
    reference: 'Zufall ≈ Anteil der Ereignishänge = 1 von 6 ≈ 0,167 · Maximum 1,0',
    direction: 'higher',
    format: v => fmt(v),
    interpret: (v, ctx = {}) => relativeToChance(v, ctx.chance ?? 1 / 6),
  },
  precision: {
    label: 'Präzision',
    what: 'Von allen Hängen, die das Modell bei der festen Schwelle 0,5 als „Ereignishang“ markiert, der Anteil echter Ereignishänge.',
    reference: 'Zufall ≈ 0,167 (Anteil der Ereignishänge)',
    direction: 'higher',
    warning: 'Hängt von der willkürlichen Schwelle 0,5 ab; die Modelle sind dafür nicht kalibriert.',
    format: v => fmt(v),
    interpret: (v, ctx = {}) => relativeToChance(v, ctx.chance ?? 1 / 6),
  },
  recall: {
    label: 'Trefferquote (Recall)',
    what: 'Anteil der echten Ereignishänge, die das Modell bei der Schwelle 0,5 als „Ereignishang“ markiert.',
    reference: 'Keine feste Zufallsreferenz; hängt davon ab, wie viele Hänge markiert werden.',
    direction: 'higher',
    warning: 'Ein Wert von 0 bedeutet nur, dass kein Wert die Schwelle 0,5 überschritt – über die Rangfolge sagt das nichts.',
    format: v => fmt(v),
    interpret: v => v === 0 ? 'Bei der Schwelle 0,5 wurde kein Ereignishang markiert. Schwellenkennzahlen tragen hier keine Information.' : `Bei der Schwelle 0,5 wurden ${pct(v)} der Ereignishänge markiert.`,
  },
  f1: {
    label: 'F1',
    what: 'Kombiniert Präzision und Trefferquote bei der festen Schwelle 0,5 zu einer Zahl.',
    reference: '0 = kein Ereignishang korrekt markiert · 1 = perfekt',
    direction: 'higher',
    warning: 'Hängt stark von der Schwelle ab und ist hier weniger aussagekräftig als die Rangfolge-Kennzahlen.',
    format: v => fmt(v),
    interpret: v => v === 0 ? 'Bei der Schwelle 0,5 wurde kein Ereignishang korrekt markiert. Die Rangfolge-Kennzahlen sind hier aussagekräftiger.' : 'Niedrige F1-Werte sind bei der festen Schwelle und dem Verhältnis 1:5 zu erwarten.',
  },
  balancedAccuracy: {
    label: 'Ausgewogene Genauigkeit',
    what: 'Mittel aus dem Anteil richtig erkannter Ereignishänge und richtig erkannter Kontrollhänge bei der Schwelle 0,5.',
    reference: '0,5 = Zufall · 1,0 = perfekt',
    direction: 'higher',
    format: v => fmt(v),
    interpret: aucReading,
  },
  controlsBeaten: {
    label: 'Kontrollen geschlagen',
    what: 'Gegen wie viele seiner fünf ähnlichen Vergleichshänge der echte Rutschungshang einen höheren Modellwert erhielt.',
    reference: 'Zufall: im Mittel 2,5 von 5 · perfekte lokale Rangfolge: 5 von 5',
    direction: 'higher',
    format: v => Number.isInteger(v) ? `${v} / 5` : `${fmt(v, 2)} / 5`,
    interpret: v => Number.isInteger(v)
      ? `Der echte Rutschungshang erhielt einen höheren Modellwert als ${v} seiner 5 ähnlichen Vergleichshänge.` + (v === 5 ? ' Das ist die bestmögliche Platzierung.' : ' Bei einer perfekten lokalen Rangfolge wären es 5 von 5.')
      : `Im Mittel übertraf der Rutschungshang ${fmt(v, 2)} seiner 5 Vergleichshänge. ` + (Math.abs(v - 2.5) < 0.3 ? 'Das liegt nahe am Zufallswert 2,5.' : v > 2.5 ? 'Das liegt über dem Zufallswert 2,5.' : 'Das liegt unter dem Zufallswert 2,5.'),
  },
  positiveRank: {
    label: 'Rang',
    what: 'Platz des dokumentierten Rutschungshangs unter den sechs verglichenen Hängen, geordnet nach Modellwert. Gleichstände erhalten halbe Ränge.',
    reference: 'Rang 1 = beste Platzierung · Zufall: im Mittel Rang 3,5',
    direction: 'lower',
    format: v => `${fmt(v, Number.isInteger(v) ? 0 : 1)} von 6`,
    interpret: v => {
      const words = ['erster', 'zweiter', 'dritter', 'vierter', 'fünfter', 'sechster']
      const where = Number.isInteger(v) ? `an ${words[v - 1]} Stelle` : `auf Rang ${fmt(v, 1)} (Gleichstand)`
      return `Der dokumentierte Rutschungshang wurde unter den sechs verglichenen Hängen ${where} eingeordnet. Rang 1 wäre die beste mögliche Platzierung.`
    },
  },
  firstPlaceRate: {
    label: 'Ereignishang auf Platz 1',
    what: 'Anteil der Ereignisse, bei denen der echte Rutschungshang den höchsten Modellwert seiner Sechsergruppe erhielt.',
    reference: 'Zufall: 1 von 6 ≈ 16,7 %',
    direction: 'higher',
    format: v => pct(v),
    interpret: v => Math.abs(v - 1 / 6) < 0.05 ? 'Das liegt nahe am Zufallswert von etwa 16,7 %.' : v > 1 / 6 ? 'Das liegt über dem Zufallswert von etwa 16,7 %. ' + SMALL : 'Das liegt unter dem Zufallswert von etwa 16,7 %.',
  },
  weatherDelta: {
    label: 'Zugewinn durch Wetter',
    what: 'Kennzahl mit Gelände + Wetter minus dieselbe Kennzahl mit Gelände allein, im selben Modell und auf denselben Daten.',
    reference: '0 = kein Unterschied',
    direction: 'higher',
    warning: 'Ein positiver Wert zeigt nur einen Unterschied zur Geländevariante – nicht, dass das Ergebnis besser als Zufall ist.',
    format: v => (v > 0 ? '+' : '') + fmt(v),
    interpret: v => Math.abs(v) < 0.01 ? 'Praktisch kein Unterschied zwischen beiden Varianten.' : v > 0 ? 'Mit Wetter war die Kennzahl in diesem Median höher. Entscheidend ist, ob das über die Wiederholungen stabil ist.' : 'Mit Wetter war die Kennzahl in diesem Median niedriger.',
  },
  rankChange: {
    label: 'Rangänderung durch Wetter',
    what: 'Rang mit Gelände allein minus Rang mit Gelände + Wetter, für dieses eine Ereignis.',
    reference: '0 = unverändert · positiv = Wetter hat den Rutschungshang nach vorne gebracht',
    direction: 'higher',
    format: v => (v > 0 ? '+' : '') + fmt(v, Number.isInteger(v) ? 0 : 1),
    interpret: v => v > 0 ? `Mit Wetter rückte der Rutschungshang um ${fmt(v, Number.isInteger(v) ? 0 : 1)} Rang nach vorne.` : v < 0 ? `Mit Wetter fiel der Rutschungshang um ${fmt(-v, Number.isInteger(v) ? 0 : 1)} Rang zurück.` : 'Wetter hat den Rang nicht verändert.',
  },
  modelScore: {
    label: 'Modellscore',
    what: 'Relativer Vergleichswert des Modells für einen Hang. Er dient dazu, die sechs Hänge einer Gruppe untereinander zu ordnen.',
    reference: 'Nur innerhalb einer Gruppe vergleichen; höher = vom Modell eher als Ereignishang eingestuft',
    direction: 'higher',
    warning: 'Keine Rutschungswahrscheinlichkeit: Die Modelle wurden mit künstlich ausgeglichenen Klassen trainiert und nicht kalibriert. 0,72 heißt nicht „72 %“.',
    format: v => fmt(v),
  },
  nullBand: {
    label: 'Zufallsreferenz (Nullreferenz)',
    what: 'In jeder Gruppe wird zufällig einer der sechs Hänge zum „Ereignis“ erklärt; danach läuft exakt dieselbe Auswertung. Das wurde 100-mal wiederholt.',
    reference: 'Grauer Bereich: mittlere 90 % dieser Zufallsergebnisse',
    direction: 'higher',
    warning: 'Liegt der beobachtete Wert im grauen Bereich, ist er von Zufall nicht unterscheidbar. Das beweist nicht, dass Wetter keine Rolle spielt.',
  },
  eventCount: {
    label: 'Ereignisse',
    what: 'Dokumentierte Rutschungen, für die alle Daten vollständig vorliegen: Gelände, fünf passende Kontrollen und 60 Tage Wetter.',
    reference: 'Jedes Ereignis bildet mit seinen fünf Kontrollen eine Sechsergruppe.',
    format: v => fmt(v, 0),
  },
  candidateCount: {
    label: 'Geprüfte Kandidaten',
    what: 'Ereignisse aus der Quelle, die Datum, Prozess und Lage-Prüfung bestanden haben. Nur ein Teil davon ist am Ende vollständig.',
    reference: 'Ausschlussgründe stehen im Abschnitt „Qualität vor Umfang“.',
    format: v => fmt(v, 0),
  },
  controlCount: {
    label: 'Kontrollhänge',
    what: 'Fünf topographisch ähnliche Hänge je Ereignis aus der näheren Umgebung, für die im Inventar kein Ereignis dokumentiert ist.',
    reference: 'Pseudo-Negative: nicht nachweislich stabil, nur ohne dokumentiertes Ereignis.',
    format: v => fmt(v, 0),
  },
  sampleCount: {
    label: 'Proben',
    what: 'Alle bewerteten Hänge zusammen: Ereignishänge plus Kontrollhänge.',
    reference: 'Proben derselben Gruppe sind nicht unabhängig voneinander.',
    format: v => fmt(v, 0),
  },
  dependencyGroups: {
    label: 'Abhängigkeitsgruppen',
    what: 'Ereignisse, die zeitlich (≤ 3 Tage) oder räumlich (< 2 km) eng zusammenhängen, etwa durch dasselbe Unwetter, werden zusammengefasst und nie zwischen Training und Prüfung getrennt.',
    reference: 'Die Zahl der Abhängigkeitsgruppen ist die eigentliche Zahl weitgehend unabhängiger Fälle – sie ist deutlich kleiner als die Zahl der Ereignisse.',
    format: v => fmt(v, 0),
  },
  retainedHours: {
    label: 'Geprüfte Stunden',
    what: 'Stündliche Wetterwerte im 60-Tage-Fenster je Hang. Randstunden nahe dem Stichtag werden vorsorglich ausgelassen, damit keine Messung vom Ereignistag eingeht.',
    reference: '60 Tage × 24 h = 1.440 h, abzüglich je einer Randstunde am Anfang und am Ende des Fensters',
    format: v => fmt(v, 0),
  },
  repetitionRange: {
    label: 'Spanne über Wiederholungen',
    what: 'Dieselben Daten wurden fünfmal unterschiedlich in gruppierte Teile zerlegt. Angezeigt sind Median und kleinster bis größter Wert.',
    reference: 'Eine breite Spanne bedeutet: Das Ergebnis hängt stark von der zufälligen Aufteilung ab.',
    warning: 'Fünf Wiederholungen derselben Daten sind keine fünf unabhängigen Bestätigungen.',
  },
  permutationImportance: {
    label: 'Merkmalswichtigkeit',
    what: 'Wie stark die Average Precision sinkt, wenn die Werte eines Merkmals zufällig durchmischt werden.',
    reference: '0 = Merkmal ohne erkennbaren Beitrag · negativ = Durchmischen schadet nicht',
    direction: 'higher',
    warning: 'Zeigt, worauf sich das Modell gestützt hat – nicht, was Rutschungen verursacht.',
    format: v => (v > 0 ? '+' : '') + fmt(v),
  },
  matchingScore: {
    label: 'Matching-Abstand',
    what: 'Wie stark die Kontrollen im Mittel vom Ereignishang abweichen (Neigung, Höhe, Exposition, Entfernung), normiert auf die erlaubten Grenzen.',
    reference: '0 = identisch · ≈ 1 = ein Merkmal an seiner erlaubten Grenze',
    direction: 'lower',
    format: v => fmt(v, 2),
    interpret: v => v < 0.2 ? 'Die Kontrollen sind dem Ereignishang topographisch sehr ähnlich.' : v < 0.5 ? 'Die Kontrollen sind dem Ereignishang gut ähnlich.' : 'Die Kontrollen weichen vergleichsweise stärker ab, liegen aber innerhalb der Grenzen.',
  },
  weatherDifference: {
    label: 'Wetterunterschied',
    what: 'Wie verschieden die Wetterwerte des Ereignishangs vom Mittel seiner Kontrollen sind, gemessen in Standardabweichungen über alle Hänge (Median über 18 Wettermerkmale).',
    reference: '0 = praktisch identisches Wetter · unter 0,05 gilt hier als „nahezu gleich“',
    direction: 'neutral',
    warning: 'Wetter ist ein 1-km-Produkt: Ob das hangspezifische Unterschiede abbildet, ist nicht gezeigt.',
    format: v => fmt(v, 2),
    interpret: v => v < 0.05 ? 'Das Wetter des Ereignishangs und seiner Kontrollen ist nahezu gleich. Wetter kann hier kaum unterscheiden.' : v < 0.15 ? 'Geringe Wetterunterschiede zwischen Ereignishang und Kontrollen.' : 'Spürbare Wetterunterschiede zwischen Ereignishang und Kontrollen.',
  },
  positionCategory: {
    label: 'Positionskategorie',
    what: 'Von der Quelle angegebene Lagekategorie des Ereignispunkts (obere Grenze in Metern).',
    reference: 'Kleiner = genauer · nicht unabhängig als Vermessungsgenauigkeit bestätigt',
    direction: 'lower',
    format: v => `bis ${fmt(v, 0)} m`,
  },
  positionSensitivity: {
    label: 'Neigungsänderung bei Verschiebung',
    what: 'Größte Änderung der Hangneigung, wenn der Ereignispunkt innerhalb seiner Positionskategorie verschoben wird.',
    reference: 'Über 5° überschreitet die Unsicherheit die Matching-Grenze für die Neigung.',
    direction: 'lower',
    format: v => fmt(v, 1) + '°',
    interpret: v => v > 5 ? 'Die Lageunsicherheit kann die Neigung stärker verändern, als Kontrollen abweichen dürfen.' : 'Die Lageunsicherheit verändert die Neigung nur innerhalb der Matching-Grenze.',
  },
  slopeDifference: {
    label: 'Neigungsdifferenz',
    what: 'Absoluter Unterschied der Hangneigung zwischen Kontrolle und Ereignishang.',
    reference: 'Erlaubt: höchstens 5°',
    direction: 'lower',
  },
  learningFraction: {
    label: 'Anteil Trainingsgruppen',
    what: 'Wie viele der verfügbaren Trainingsgruppen für das Modell verwendet wurden; die Prüfgruppen bleiben gleich.',
    reference: 'Steigt die Kennzahl mit mehr Gruppen, helfen mehr Daten derselben Art vermutlich.',
  },
}

export const directionText = { higher: 'Höher ist besser.', lower: 'Niedriger ist besser.', neutral: 'Weder höher noch niedriger ist an sich besser.' }

export function explain(term, value, ctx) {
  const d = metricDefinitions[term]
  if (!d) throw new Error('Unknown metric definition: ' + term)
  const has = value !== undefined && value !== null && Number.isFinite(Number(value))
  return {
    label: d.label, what: d.what, reference: d.reference, warning: d.warning,
    direction: d.direction ? directionText[d.direction] : null,
    value: has && d.format ? d.format(Number(value)) : null,
    reading: has && d.interpret ? d.interpret(Number(value), ctx) : null,
  }
}
