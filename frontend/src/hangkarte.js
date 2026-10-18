// Pure helpers of the Hangkarte (unit-tested without a browser).
export const MAX_POINTS = 12, MIN_POINTS = 2

const FEATURES = {
  elevation: 'Höhe', slope: 'Neigung', aspect_sin: 'Exposition (Ost–West)', aspect_cos: 'Exposition (Nord–Süd)',
  profile_curvature: 'Profilkrümmung', plan_curvature: 'Grundrisskrümmung', roughness_tri: 'Rauigkeit',
  tpi_150m: 'Geländeposition (150 m)', tpi_500m: 'Geländeposition (500 m)', relative_position_500m: 'relative Hangposition',
  log10_catchment_m2: 'Einzugsgebiet', twi: 'Nässeindex (TWI)',
  lc_forest: 'Landbedeckung: Wald', lc_grass_shrub: 'Landbedeckung: Grünland/Gebüsch', lc_agriculture: 'Landbedeckung: Acker/Dauerkultur',
  lc_open_bare: 'Landbedeckung: offener Boden/Fels', lc_artificial_water_other: 'Landbedeckung: Siedlung, Verkehr, Wasser, sonstige',
  geo_carbonate: 'Geologie: Karbonat', geo_clastic_rock: 'Geologie: klastisches Gestein', geo_unconsolidated: 'Geologie: Lockermaterial',
  geo_low_grade_metamorphic: 'Geologie: schwach metamorph', geo_crystalline_other: 'Geologie: Kristallin/sonstige'
}
const LAND_COVER = {
  lc_forest: 'Wald', lc_grass_shrub: 'Grünland/Gebüsch', lc_agriculture: 'Acker/Dauerkultur', lc_open_bare: 'offen/Fels',
  lc_artificial_water_other: 'Siedlung/Verkehr/sonstige'
}

export const driverLabel = f => FEATURES[f] || f
export const landCoverLabel = c => LAND_COVER[c] || '–'

/** Share (0..1) as German percentage with one decimal; never shows a hard 0 for a positive share. */
export function formatShare(share) {
  if (!Number.isFinite(share) || share < 0 || share > 1) return '–'
  const pct = share * 100
  if (pct > 0 && pct < 0.1) return '< 0,1 %'
  return pct.toLocaleString('de-AT', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + ' %'
}

/** Great-circle distance in metres (haversine, WGS84 mean radius); no Euclidean degrees. */
export function distanceM(a, b) {
  const R = 6371008.8, rad = d => d * Math.PI / 180
  const dLat = rad(b.latitude - a.latitude), dLon = rad(b.longitude - a.longitude)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

/** Why a clicked point cannot join the custom comparison group ('' = it can). */
export function pointProblem(point, centre, radiusM, points) {
  if (!centre) return 'Zuerst ein Gebiet wählen.'
  if (points.length >= MAX_POINTS) return `Höchstens ${MAX_POINTS} Punkte.`
  if (distanceM(centre, point) > radiusM) return 'Der Punkt liegt außerhalb des gewählten Gebiets.'
  if (points.some(p => distanceM(p, point) < 30)) return 'Dieser Hang ist schon gewählt.'
  return ''
}

/** Colour of a share inside its group: dark = low, bright = high (sequential, not a warning scale). */
export function shareColor(share) {
  const stops = [[0, [68, 1, 84]], [.25, [59, 82, 139]], [.5, [33, 144, 141]], [.75, [93, 200, 99]], [1, [253, 231, 37]]]
  const t = Math.sqrt(Math.min(1, Math.max(0, Number.isFinite(share) ? share : 0)))   // sqrt: small shares stay distinguishable
  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i][0]) {
      const [t0, c0] = stops[i - 1], [t1, c1] = stops[i], u = (t - t0) / (t1 - t0)
      return 'rgb(' + c0.map((v, k) => Math.round(v + u * (c1[k] - v))).join(',') + ')'
    }
  }
  return 'rgb(253,231,37)'
}

export const CAVEATS = [
  'Relative Anteile zwischen den gezeigten Hängen – keine Eintrittswahrscheinlichkeit und keine Warnung.',
  'Das Modell (V0.5, explorativ) kennt nur Geländeinformation vor einem Ereignis. Es sagt nicht, ob oder wann ein Hang rutscht.',
  'Ein Teil der Trennung kann Meldebias sein: Rutschungen werden eher an Straßen, in Siedlungsnähe und auf Grünland gemeldet. Gegen gematchte Kontrollen sinkt die lokale AUC von 0,85 auf 0,70.',
  'Wichtigkeit eines Merkmals bedeutet nicht, dass es die Rutschung verursacht.'
]
