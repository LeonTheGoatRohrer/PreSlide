"""Shape the film's last line: three separate words with long pauses, lower and slower voice, only a small room.

Writes voice_v4_fast/q5.mp3, with --v5 voice_v5/q5.mp3 (new take, cut before the T plosive, short fade-in, presence lift).
Usage: <main checkout>/.venv/Scripts/python scripts/finale_video/final_line.py [--v5]
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[2] / 'deliverables/finale_video'
SR = 48000
PITCH = 0.891  # two semitones down; the voice also gets 12 % slower, which is intended here
WORDS_S = [(0.0, 0.60), (0.91, 1.41), (1.76, 2.52)]  # Das, Ist, Talwacht in q5s.mp3, cut in the measured silences
PAUSES_S = [0.75, 0.85]
ROOM_S, WET = 0.9, 0.06
SOURCE, TARGET, FADE_IN_S, PRESENCE = 'voice_v4/q5s.mp3', 'voice_v4_fast/q5.mp3', 0.012, ''
TALWACHT_T_S = None  # T plosive inside the source take, measured in the waveform
STRETCH = PITCH  # V4 mapping of source seconds to the processed stream (kept so V4 stays bit-identical)
parser = argparse.ArgumentParser()
parser.add_argument('--v5', action='store_true')
if parser.parse_args().v5:
    # Higgsfield elevenlabs_v4, Alistair, text "Das. ... Ist. ... Talwacht." (job c0fb6366), take0 of four.
    # Measured (10 ms RMS, 3-8 kHz band): Das 0.03-0.78, Ist 0.99-1.56, T burst of Talwacht at 1.865, word end 2.67.
    # The Talwacht cut sits 35 ms before the plosive, so the T is never inside the fade.
    SOURCE, TARGET, FADE_IN_S = 'voice_v5/takes/take0.mp3', 'voice_v5/q5.mp3', 0.003
    WORDS_S = [(0.02, 0.72), (0.98, 1.56), (1.83, 2.68)]
    TALWACHT_T_S = 1.865
    PRESENCE = ',equalizer=f=4000:t=q:w=1:g=4'  # only on Talwacht, so the T cuts through the song
    # The takes are 44.1 kHz, so asetrate=48000*PITCH really stretches by 44100/(48000*PITCH), not 1/PITCH.
    # With 1/PITCH every V4 cut landed ~8 % too late; the Talwacht cut fell behind the T, which is why it was missing.
    STRETCH = PITCH * SR / 44100


def decode(extra: str) -> np.ndarray:
    effects = f'asetrate={SR}*{PITCH},aresample={SR},bass=g=4:f=110,acompressor=threshold=-20dB:ratio=3:attack=8:release=180{extra}'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(OUT / SOURCE), '-af', effects, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def main() -> None:
    source = decode('')
    talwacht = decode(PRESENCE) if PRESENCE else source
    parts, onsets, at = [], [], 0.0
    for i, (start, stop) in enumerate(WORDS_S):
        word = (talwacht if i == 2 else source)[int(start / STRETCH * SR):int(stop / STRETCH * SR)].copy()
        fade_in, fade = int(FADE_IN_S * SR), int(0.012 * SR)
        word[:fade_in] *= np.linspace(0, 1, fade_in)
        word[-fade:] *= np.linspace(1, 0, fade)
        parts.append(word)
        onsets.append(round(at, 4))
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
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f64le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'libmp3lame', '-q:a', '0', str(OUT / TARGET)],
                   input=mix.tobytes(), check=True)
    print('Wortanfaenge', onsets, 's, Ende', round(at, 2), 's')
    if TALWACHT_T_S is not None:
        print('T-Plosiv von Talwacht bei', round(onsets[2] + (TALWACHT_T_S - WORDS_S[2][0]) / STRETCH, 4), 's in', TARGET)


if __name__ == '__main__':
    main()
