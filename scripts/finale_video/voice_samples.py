"""Generate German narrator samples with Microsoft neural voices (edge-tts).

Usage: PYTHONPATH=<folder containing edge_tts> python scripts/finale_video/voice_samples.py
Writes deliverables/finale_video/stimmen_de/ (gitignored).
"""
import asyncio
import ssl
from pathlib import Path

import edge_tts
import edge_tts.communicate as communicate
import edge_tts.voices as edge_voices

ROOT = Path(__file__).resolve().parents[2]
CA = Path('C:/Users/mario/Documents/HomeProjects/PreSlide/data/runtime/windows-ca.pem')
OUT = ROOT / 'deliverables/finale_video/stimmen_de'
TEXT = ('Starkregen hat in Österreich in vierzig Jahren um rund fünfzehn Prozent zugenommen. '
        'Und mit extremem Regen kommen Hangrutschungen und Muren. Aber warum dieser Hang? Und nicht der daneben?')


async def main() -> None:
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(CA))
    communicate._SSL_CTX = ctx
    edge_voices._SSL_CTX = ctx
    voices = await edge_tts.list_voices()
    male_de = [v['ShortName'] for v in voices if v['Locale'].startswith('de-') and v['Gender'] == 'Male']
    print('verfügbar:', male_de)
    OUT.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(male_de, 1):
        await edge_tts.Communicate(TEXT, name, rate='-6%', pitch='-4Hz').save(str(OUT / f'{i}_{name}.mp3'))
        print('ok', name)


asyncio.run(main())
