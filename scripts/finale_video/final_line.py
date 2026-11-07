"""Shape the film's last line: three separate words with long pauses, lower and slower voice, only a small room.

Writes voice_v4_fast/q5.mp3. Usage: <main checkout>/.venv/Scripts/python scripts/finale_video/final_line.py
"""
import subprocess
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / 'deliverables/finale_video'
SR = 48000
PITCH = 0.891  # two semitones down; the voice also gets 12 % slower, which is intended here
WORDS_S = [(0.0, 0.60), (0.91, 1.41), (1.76, 2.52)]  # Das, Ist, Talwacht in q5s.mp3, cut in the measured silences
PAUSES_S = [0.75, 0.85]
ROOM_S, WET = 0.9, 0.06


def main() -> None:
    effects = f'asetrate={SR}*{PITCH},aresample={SR},bass=g=4:f=110,acompressor=threshold=-20dB:ratio=3:attack=8:release=180'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(OUT / 'voice_v4/q5s.mp3'), '-af', effects, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    source = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    parts, onsets, at = [], [], 0.0
    for i, (start, stop) in enumerate(WORDS_S):
        word = source[int(start / PITCH * SR):int(stop / PITCH * SR)].copy()
        fade = int(0.012 * SR)
        word[:fade] *= np.linspace(0, 1, fade)
        word[-fade:] *= np.linspace(1, 0, fade)
        parts.append(word)
        onsets.append(round(at, 2))
        at += len(word) / SR
        if i < len(PAUSES_S):
            parts.append(np.zeros(int(PAUSES_S[i] * SR)))
            at += PAUSES_S[i]
    dry = np.concatenate(parts)
    noise = np.random.default_rng(423).standard_normal((int(ROOM_S * SR), 2))
    decay = np.exp(-np.arange(len(noise)) / (0.16 * SR))
    size = len(dry) + len(noise)
    wet = np.stack([np.fft.irfft(np.fft.rfft(dry, size) * np.fft.rfft(noise[:, c] * decay, size), size) for c in (0, 1)], axis=1)
    wet *= WET * np.abs(dry).max() / np.abs(wet).max()
    mix = wet
    mix[:len(dry)] += dry[:, None]
    mix *= 0.95 / np.abs(mix).max()
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f64le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'libmp3lame', '-q:a', '0', str(OUT / 'voice_v4_fast/q5.mp3')],
                   input=mix.tobytes(), check=True)
    print('Wortanfaenge', onsets, 's, Ende', round(at, 2), 's')


if __name__ == '__main__':
    main()
