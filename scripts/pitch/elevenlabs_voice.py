"""Generate the pitch narration with an ElevenLabs voice (one MP3 per film segment).

The API key is read from the environment variable ELEVENLABS_API_KEY and never written anywhere.
Usage (PowerShell):
    $env:ELEVENLABS_API_KEY = '<dein Schlüssel>'
    .venv\\Scripts\\python scripts\\pitch\\elevenlabs_voice.py
Then rebuild the film: .venv\\Scripts\\python scripts\\pitch\\build_film.py --keep-voice
"""
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_film  # noqa: E402

VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'JiW03c2Gt43XNUQAumRP')
MODEL = os.environ.get('ELEVENLABS_MODEL', 'eleven_multilingual_v2')


def main():
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key:
        raise SystemExit('ELEVENLABS_API_KEY ist nicht gesetzt.')
    ctx = ssl.create_default_context()
    bundle = ROOT / 'data/runtime/windows-ca.pem'
    if bundle.exists():
        ctx.load_verify_locations(cafile=str(bundle))
    build_film.BUILD.mkdir(parents=True, exist_ok=True)
    for seg in build_film.SEGMENTS:
        if not seg['text']:
            continue
        text = seg.get('tts_text', seg['text']).replace('…', '...')
        body = json.dumps({'text': text, 'model_id': MODEL, 'language_code': 'de',
                           'voice_settings': {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.2, 'use_speaker_boost': True}}).encode()
        req = urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_192', data=body,
                                     headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'})
        with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
            (build_film.BUILD / f'voice_{seg["id"]}.mp3').write_bytes(r.read())
        print('ok', seg['id'], flush=True)


if __name__ == '__main__':
    main()
