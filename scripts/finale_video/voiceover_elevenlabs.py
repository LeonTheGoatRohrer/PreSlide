"""Generate the film narration with one ElevenLabs voice, one MP3 per film segment.

The API key is read from ELEVENLABS_API_KEY (process or Windows user environment) and is never printed or stored here.
Usage: python scripts/finale_video/voiceover_elevenlabs.py [--only n01,n02]
Writes deliverables/finale_video/voice_elevenlabs/ (gitignored).
"""
import argparse
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CA = Path('C:/Users/mario/Documents/HomeProjects/PreSlide/data/runtime/windows-ca.pem')
OUT = ROOT / 'deliverables/finale_video/voice_elevenlabs'
VOICE_ID = '5KvpaGteYkNayiswuX2h'
MODEL = 'eleven_multilingual_v2'

TEXTS = {
    'n01': 'Regen. Stundenlang. Irgendwann hält der Hang nicht mehr.',
    'n02': 'Aber warum dieser Hang? Und nicht der daneben?',
    'n03': 'Starkregen hat in Österreich in vierzig Jahren um rund fünfzehn Prozent zugenommen. Wärmere Luft trägt mehr Wasser. Und mit extremem Regen kommen Hangrutschungen und Muren: Forscher erwarten, dass Regen, der Muren auslösen kann, wahrscheinlicher wird und größere Flächen trifft.',
    'n04': 'Aber niemand kann jeden Hang im Land beobachten. Wenn das Unwetter kommt, bleibt eine Frage: Wo zuerst hinschauen?',
    'n05': 'Dafür habe ich Talwacht gebaut. Ein Machine-Learning-System auf echten Daten aus Österreich. Der Weg dorthin bestand aus fünf Problemen.',
    'n06': 'Problem eins: die Daten. Das Inventar von GeoSphere Austria enthält über fünfundzwanzigtausend Einträge zu Naturgefahren. Aber nicht jeder ist eine Rutschung, und nicht bei jedem sind Datum, Prozess und Lage gesichert. Nach strenger Prüfung bleiben vierhundertdreiundzwanzig Ereignisse.',
    'n07': 'Problem zwei ist das Herzstück. Ein Modell braucht Gegenbeispiele: Hänge, an denen nichts passiert ist. Genau die gibt es nicht. Niemand dokumentiert einen Hang, der einfach stehen bleibt. Und zufällige Punkte wären wertlos. Dann lernt das Modell nur: Berg ist nicht Flachland.',
    'n08': 'Also sucht Talwacht jedem Ereignis fünf Zwillinge. In der Nähe, gleich steil, gleich hoch, gleich ausgerichtet, mit demselben Stichtag. Sie sind nicht garantiert stabil, nur ohne Meldung. Aber jetzt ist die Frage fair: Hang gegen Zwilling.',
    'n09': 'Problem drei: sich nicht selbst täuschen. Ein Modell, das die Zukunft sieht, sieht immer gut aus. Deshalb gilt: keine Information ab dem Ereignis, automatisch getestet. Ein Hang und seine Zwillinge bleiben immer zusammen. Der Plan wurde vorab festgeschrieben. Und der Test blieb versiegelt, bis zum Schluss. Genau ein Versuch.',
    'n10': 'Das Ergebnis: null Komma sieben fünf. Zufall wäre null Komma fünf. In rund drei von vier Vergleichen liegt der betroffene Hang vor seinen Zwillingen. Bei elf unabhängigen Unwetterepisoden, von denen eine dominiert.',
    'n11': 'Problem vier hat mich überrascht. Ich war sicher: Mit dem Wetter wird das Modell besser. Ein Zusatznutzen ließ sich aber nicht belegen. Denn am selben Tag haben Nachbarhänge fast dasselbe Wetter.',
    'n12': 'Also habe ich die Frage gedreht. Derselbe Ort, verschiedene Zeiten. Und da zeigt sich: In einem Viertel der Episoden waren die drei Tage davor extrem nass. Erwartet wäre jede zwanzigste. Ein Hinweis, noch keine Bestätigung.',
    'n13': 'Problem fünf: Dann habe ich gegen mein eigenes Projekt gesucht. Allein der Abstand zu Straßen und Häusern trennt gemeldete von anderen Hängen mit null Komma neun drei. Gemeldet wird, was Menschen sehen. Also habe ich nur Hänge verglichen, die ähnlich nah an Straßen und Gebäuden liegen. Das Gelände trennt dort immer noch mit null Komma sieben acht. Ein Teil des Signals bleibt Meldeverhalten. Das sage ich offen.',
    'n14': 'Daraus ist ein Werkzeug geworden: der Hang-Check. Ich wähle einen Ort, zum Beispiel das Gasteiner Tal. Aus diesem Tal kennt das Modell kein einziges Ereignis. Talwacht ordnet die Hänge im Umkreis und zeigt fünf Prüfpunkte: hier zuerst hinschauen.',
    'n15': 'Und wenn der Starkregen kommt: Für jeden Prüfpunkt zeigt die Karte den möglichen Weg hangabwärts, und welche Straßen und Gebäude in diesem Szenario liegen.',
    'n16': 'Für die Gemeinde nach dem Unwetter. Für den Straßendienst auf Kontrollfahrt. Für die Menschen am Hang.',
    'n17': 'Was kann Talwacht? Es ordnet Hänge und zeigt, wo man zuerst hinschauen kann. Was kann es nicht? Es warnt nicht, und es nennt keine Wahrscheinlichkeit. Nicht markiert heißt nicht sicher, und reine Hangmuren trennt es bisher kaum.',
    'n18': 'Als Nächstes kommt der härteste Test: vorab festgelegt, mit Ereignissen, die noch gar nicht passiert sind.',
    'n19': 'Denn der nächste Starkregen kommt. Und dann sollte man wissen, wo man zuerst hinschaut.',
}


def api_key() -> str:
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key and os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as reg:
                key = winreg.QueryValueEx(reg, 'ELEVENLABS_API_KEY')[0]
        except OSError:
            key = None
    if not key:
        raise SystemExit('ELEVENLABS_API_KEY ist nicht gesetzt.')
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    names = args.only.split(',') if args.only else list(TEXTS)
    key = api_key()
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(CA))
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0.0
    for name in names:
        body = json.dumps({'text': TEXTS[name], 'model_id': MODEL, 'language_code': 'de',
                           'voice_settings': {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.15, 'use_speaker_boost': True}}).encode()
        req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128', data=body,
                                     headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=180) as resp:
                (OUT / f'{name}.mp3').write_bytes(resp.read())
        except urllib.error.HTTPError as err:
            raise SystemExit(f'{name}: ElevenLabs HTTP {err.code}: {err.read().decode(errors="replace")[:400]}') from err
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(OUT / f'{name}.mp3')],
                                   capture_output=True, text=True, check=True).stdout)
        total += dur
        print(name, round(dur, 2), flush=True)
    print('Summe', round(total, 1), 's')


if __name__ == '__main__':
    main()
