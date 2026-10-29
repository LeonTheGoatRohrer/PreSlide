"""Write aggregate German interpretation from the saved pilot artifacts, with no fitting."""
from ..common import read_json, write_json, digest
from ..baseline import sha
from .context import REPORTS, guard


def ci(value):
    return f'[{value[0]:.3f}; {value[1]:.3f}]'


def run():
    c = read_json(REPORTS / 'context_results.json')
    a = read_json(REPORTS / 'appearance_results.json')
    t = read_json(REPORTS / 'transfer_results.json')
    private_path = REPORTS / 'CONTEXT_REGISTRATION.json'
    private = read_json(private_path)
    write_json(guard(REPORTS / 'CONTEXT_REGISTRATION_PUBLIC.json'), {
        'registered_at_utc': private['registered_at_utc'], 'config_sha256': private['config_sha256'],
        'original_private_registration_sha256': sha(private_path), 'sources': private['sources'],
        'dataset_sha256': private['dataset_sha256'], 'cv_plan_digest': digest(private['plan']),
        'events': private['events'], 'independent_units': private['independent_units'],
        'scope': private['scope'], 'note': 'Episode identifiers and detailed assignments remain local; hash-only public summary.'})
    cp, ap = c['primary'], a['best_development']
    lines = [
        '# Pilot: Umgebung vorauswählen, danach Rutschungsspuren im Einzelbild suchen', '',
        'Stand: 17.10.2026. Explorativ, eigener Namespace mudslide_cascade_v01. '
        'Keine bestehenden Experimente überschrieben. Keine kalibrierte Gefahrenkarte, '
        'keine bestätigten neuen Muren und kein automatisches Weiterlernen.', '',
        '## 1. Umgebungsmodell: eindeutig als Hangmure bezeichnete Ereignisse', '',
        f"{cp['events']} Ereignisgruppen mit je fünf gematchten Pseudo-Negativen, {cp['units']} unabhängige Einheiten. "
        'Bedingte logistische Regression auf Gelände, Landbedeckung und Geologie; '
        'keine Wetterwerte, Koordinaten oder Straßen-/Gebäudeabstände als Eingabe. '
        'Fünf vorab eingefrorene Episoden-Folds mit mindestens 1 km Abstand nach Trainingsbereinigung.', '',
        f"Lokale AUC, Einheiten gleich gewichtet: **{cp['local_auc_units']:.3f}**, 95%-Intervall {ci(c['auc_ci95'])}. "
        f"Zufallsreferenz 0,5, oberer empirischer p-Wert {c['random_rank_upper_p']:.3f}.", '',
        f"Bei Suchbudget 50 % bleiben über die Einheiten gewichtet {100*c['positive_retention_units']:.1f} % "
        f"der positiven Hänge erhalten (95%-Intervall {ci(c['positive_retention_ci95'])}; Zufallsbudget 50 %). "
        f"Je Ereignis gerechnet sind es {100*c['positive_retention_events']:.1f} %. "
        'Die unterschiedliche Gewichtung zeigt die Bedeutung großer Episoden.', '',
        'Die Landbedeckung liegt hier als grobe Punktklasse vor. Detaillierte Wald-/Wiesenanteile '
        'in der ganzen Umgebung und gemessene Bodeneigenschaften sind noch keine Eingaben dieses Piloten.', '',
        '**Kein belastbarer Vorteil dieser Vorauswahl belegt.** Sie darf im aktuellen Stand '
        'andere Hänge nicht als sicher ausschließen. Landbedeckung kann weiterhin Erfassungsbias tragen; '
        'Geologie ersetzt keine gemessenen Bodeneigenschaften. Die Vorauswahl gilt hier für lokale '
        'Kandidatenpunkte und ist noch keine flächige Geländeklassifikation.', '',
        '## 2. Bildnetz: echtes beaufsichtigtes RGB-Training', '',
        f"U-Net mit ResNet-18-Encoder (ImageNet-Start), {a['train_images']} Landslide4Sense-Trainingsbilder "
        f"und {a['development_images']} Entwicklungsbilder mit Pixelmasken, acht feste Epochen auf CPU. "
        'Das Netz erhält nur die RGB-Kanäle einer einzelnen Aufnahme, keine Gelände- oder Kontextdaten. '
        'Räumliche Unabhängigkeit der öffentlichen Bildaufteilung ist unbekannt: '
        '**Die folgenden Pixelwerte sind beschreibende Entwicklungswerte, kein unabhängiger geografischer Leistungsnachweis.**', '',
        f"Gespeicherte Epoche {a['best_epoch']} nach vorab festgelegtem Entwicklungs-Dice: "
        f"Pixel-Precision {ap['precision']:.3f}, Pixel-Recall {ap['recall']:.3f}, "
        f"Dice {ap['dice']:.3f}, IoU {ap['iou']:.3f}. Immer-Hintergrund hat auf diesen Masken Recall/Dice 0. "
        'Diese Werte sind keine Quote korrekt entdeckter Muren und keine Sicherheitswahrscheinlichkeiten. '
        'Einheitenintervalle werden mangels rekonstruierbarer räumlicher Einheiten nicht behauptet.', '',
        'Landslide4Sense unterscheidet allgemeine Rutschungsspuren, keine reinen Muren. '
        'Der Nutzer hat dieses allgemeine Vortraining mit gesonderter Hangmurenprüfung ausdrücklich gewählt. '
        'Auch ein RGB-Netz kann sichtbare Straßen oder andere Bildabkürzungen lernen; '
        'der Ausschluss tabellarischer Infrastrukturmerkmale beseitigt das nicht automatisch.', '',
        '## 3. Österreichische Hangmuren: gesonderter Transfercheck', '',
        f"{t['events']} vollständige, bildseitig auswertbare Gruppen, {t['samples']} Proben aus "
        f"{t['independent_units']} unabhängigen Einheiten. Kein österreichisches Bild wurde zum Training "
        'oder zur Epochenwahl dieses Netzes benutzt. Diese Inventarereignisse waren im Projekt allerdings '
        'schon bekannt. Inventarpunkt und Kontrollhang sind schwache Bildlabels: '
        'Eine sichtbare Narbe ist am Positiv noch nicht unabhängig eingezeichnet und '
        'am Kontrollhang nicht unabhängig ausgeschlossen.', '',
        '| Variante | gewichtete lokale AUC | 95%-Einheitenintervall |',
        '|---|---:|---|',
    ]
    for name, label in [('image_only', 'Nur Bildnetz'), ('context_then_image', 'Vorauswahl und Bildnetz')]:
        lines.append(f"| {label} | {t['summaries'][name]['local_auc_units']:.3f} | {ci(t['uncertainty'][name]['ci95'])} |")
    delta = t['uncertainty']['context_then_image_minus_image_only']
    lines += ['', f"Gepaarte Differenz Vorauswahl minus Bildnetz: {delta['mean']:+.3f}, "
              f"95%-Intervall {ci(delta['ci95'])}. Zufallsreferenz der Rangfolge 0,5. "
              'Ein Nutzen der Vorauswahl wird nur bei einem vollständig positiven Differenzintervall behauptet.', '',
              f"Die Vorauswahl behält in dieser Transferteilmenge {100*t['context_positive_retention_events']:.1f} % "
              'der inventarpositiven Hänge. Die AUC der Kette ist eine Rangdiagnose mit gleichem niedrigem '
              'Score für ausgesonderte Kandidaten; sie ist keine End-to-End-Fundquote und darf die '
              'ausgesonderten Positiven nicht verdecken.', '',
              f"Ausschlüsse nach vorab bestimmter Bildprüfung: {t['excluded_groups_by_reason']}. "
              'Die zugehörigen Bildmasken, Vorhersagen und Beispielansichten bleiben lokal unter '
              'data/mudslide_cascade_v01/. Sämtliche zusätzlich markierten Flächen sind UNVERIFIED; '
              'kein Fund wird in die bestätigten Trainingsdaten übernommen.', '',
              '## Konsequenz und nächster sinnvoller Schritt', '',
              'Der kleine Versuch ist ausführbar und liefert eine messbare Antwort. '
              'Vor mehr Training zuerst österreichische sichtbare Spuren und echte Verwechslungen '
              'blind annotieren. Die Bildsuche zunächst ohne ausschließende Umgebungs-Vorauswahl prüfen. '
              'Ein weiterer Versuch braucht eine eigene Version und vorab festgelegte Regeln; '
              'keine Schwellen- oder Seed-Suche auf diesen Ergebnissen.', '',
              '## Quellen und Nachweise', '',
              '- Landslide4Sense: https://zenodo.org/records/10463239 (CC BY 4.0 laut Zenodo-Metadaten; RGB-Bänder und echte Pixelmasken).',
              '- Lokale, unveränderte Inventar-, Gelände- und Geologiedaten: DATA_SOURCES.md.',
              '- CONTEXT_REGISTRATION.json, APPEARANCE_REGISTRATION.json: Registrierung vor dem jeweiligen Training.',
              '- context_results.json, appearance_results.json, transfer_results.json: alle Auswertungen, keine selektierte Ergebnisliste.',
              '- verification.json und appearance_verification.json: gespeicherte Modelle/Vorhersagen nachprüfen.', '']
    path = guard(REPORTS / 'summary.md')
    path.write_text('\n'.join(lines), encoding='utf-8')
    print(path)


if __name__ == '__main__':
    run()
