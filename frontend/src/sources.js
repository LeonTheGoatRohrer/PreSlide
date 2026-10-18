// External, checkable sources for statements about the problem (not model results).
// Checked 18.10.2026 against the linked pages; wording stays close to what each source states.
export const problemSources = [
  {
    id: 'haslinger',
    short: 'GeoSphere Austria 2025; Haslinger et al., Nature',
    cite: 'Haslinger, K. et al. (2025): Increasing hourly heavy rainfall in Austria reflected in flood changes. Nature 639, 667–672. 883 Messstationen, 1900–2023. Zusammenfassung: GeoSphere Austria, 12.03.2025.',
    url: 'https://geosphere.at/en/news-and-events/news/heavy-rain-has-increased-significantly',
    urlLabel: 'geosphere.at',
    fact: { figure: '+15 %', text: 'mehr Regen bei extremen Einstunden-Ereignissen in Österreich über die letzten 40 Jahre; bei Tagesextremen +8 %.' },
  },
  {
    id: 'wildbach',
    short: 'BMLUK: Wildbäche und Muren',
    cite: 'Bundesministerium für Land- und Forstwirtschaft, Klima- und Umweltschutz, Regionen und Wasserwirtschaft (BMLUK): Wildbäche und Muren. Abgerufen 18.10.2026.',
    url: 'https://www.bmluk.gv.at/themen/wald/wald-und-naturgefahren/leben-mit-naturgefahren/wildbaeche.html',
    urlLabel: 'bmluk.gv.at',
    fact: { figure: 'rund 12.500', text: 'Wildbacheinzugsgebiete gibt es in Österreich. Ihre Schwemmkegel im Tal sind oft dicht besiedelt.' },
  },
  {
    id: 'erdok2023',
    short: 'BMLUK: Ereignisdokumentation 2023',
    cite: 'BMLUK, Wildbach- und Lawinenverbauung: Ereignisdokumentation 2023 (digitales Ereignisportal des Wildbach- und Lawinenkatasters). Abgerufen 18.10.2026.',
    url: 'https://www.bmluk.gv.at/themen/wald/wald-und-naturgefahren/wildbach--und-lawinenverbauung/aktuelles-bundeslaender/erdok2023.html',
    urlLabel: 'bmluk.gv.at',
    fact: { figure: '432', text: 'Ereignisse wie Muren und Rutschungen erfasste die Wildbach- und Lawinenverbauung 2023 (ohne Lawinen), rund 60 % davon im Juli und August.' },
  },
  {
    id: 'schloegl',
    short: 'Schlögl et al. 2021',
    cite: 'Schlögl, M., Fuchs, S., Scheidl, C., Heiser, M. (2021): Trends in torrential flooding in the Austrian Alps: A combination of climate change, exposure dynamics, and mitigation measures. Climate Risk Management 32, 100294.',
    url: 'https://doi.org/10.1016/j.crm.2021.100294',
    urlLabel: 'doi.org/10.1016/j.crm.2021.100294',
  },
]
