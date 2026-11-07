"""Shape the film's last line: lower and slower voice, more body, a long hall. Writes voice_v4_fast/q5.mp3.

Usage: <main checkout>/.venv/Scripts/python scripts/finale_video/final_line.py
"""
import subprocess
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / 'deliverables/finale_video'
SR = 48000
PITCH = 0.891  # two semitones down; the voice also gets 12 % slower, which is intended here
HALL_S, WET = 2.8, 0.2


def main() -> None:
    effects = f'asetrate={SR}*{PITCH},aresample={SR},bass=g=4:f=110,acompressor=threshold=-20dB:ratio=3:attack=8:release=180'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(OUT / 'voice_v4/q5a.mp3'), '-af', effects, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    dry = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    noise = np.random.default_rng(423).standard_normal((int(HALL_S * SR), 2))
    decay = np.exp(-np.arange(len(noise)) / (0.55 * SR))[:, None]
    predelay = int(0.03 * SR)
    size = len(dry) + len(noise) + predelay
    wet = np.stack([np.fft.irfft(np.fft.rfft(dry, size) * np.fft.rfft(noise[:, c] * decay[:, 0], size), size) for c in (0, 1)], axis=1)
    wet = np.roll(wet, predelay, axis=0)
    wet *= WET * np.abs(dry).max() / np.abs(wet).max()
    mix = wet
    mix[:len(dry)] += dry[:, None]
    mix *= 0.7 / np.abs(mix).max()
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f64le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'libmp3lame', '-q:a', '0', str(OUT / 'voice_v4_fast/q5.mp3')],
                   input=mix.tobytes(), check=True)
    level = np.abs(dry)
    env = np.convolve(level, np.ones(480) / 480, mode='same')
    quiet = np.where(env < env.max() * .03)[0]
    gaps = quiet[(quiet > int(.5 * SR)) & (quiet < int(2.3 * SR))]
    print('Dauer trocken', round(len(dry) / SR, 2), 's, Pause', round(gaps.min() / SR, 2), 'bis', round(gaps.max() / SR, 2), 's')


if __name__ == '__main__':
    main()
