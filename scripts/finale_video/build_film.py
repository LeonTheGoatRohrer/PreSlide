"""Assemble the finale film from AI clips, rendered motion graphics, app recordings, voice, music and SFX.

Usage: <main checkout>/.venv/Scripts/python scripts/finale_video/build_film.py [--width 960]
Output: deliverables/finale_video/Talwacht_Finale_Prototyp.mp4 (gitignored).
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'deliverables/finale_video'
BUILD = OUT / 'build'
AI, MG, VOICE, SFX = OUT / 'ai', OUT / 'mgclips', OUT / 'voice', OUT / 'sfx'
APP = Path('C:/Users/mario/Documents/HomeProjects/PreSlide/.claude/worktrees/video-pitch-script-497edf/deliverables/pitch')
FPS = 25
SR = 48000
AI_LABEL = 'KI-generierte Illustration'

parser = argparse.ArgumentParser()
parser.add_argument('--width', type=int, default=960)
parser.add_argument('--voice-dir', default='voice', help='folder under deliverables/finale_video with n01.mp3 ... n19.mp3')
parser.add_argument('--audio-only', action='store_true', help='keep the rendered picture, only remix the sound')
parser.add_argument('--out', default='Talwacht_Finale_Prototyp.mp4')
args = parser.parse_args()
VOICE = OUT / args.voice_dir
W, H = args.width, args.width * 9 // 16
S = W / 1920


def duration(path: Path) -> float:
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def run(cmd: list[str]) -> None:
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *cmd], check=True)


def clip(name, start=0.0, dur=3.0, speed=1.0):
    return {'file': AI / f'{name}.mp4', 'start': start, 'dur': dur, 'speed': speed}


# kind: film (AI clips, optional screen-blended plate), mg (full-screen graphics), app (screen recording), black.
# voice: (file, offset seconds into the segment).
SEGMENTS = [
    {'id': 'black0', 'kind': 'black', 'dur': 1.2},
    {'id': 'c1_drop', 'kind': 'film', 'clips': [clip('a01', 0.4, 4.4)], 'bars': True},
    {'id': 'c2_storm', 'kind': 'film', 'clips': [clip('a02', 1.0, 3.6)], 'bars': True},
    {'id': 'c3_crack', 'kind': 'film', 'clips': [clip('a03', 0.5, 3.0)], 'bars': True},
    {'id': 'c4_valley', 'kind': 'film', 'clips': [clip('a04', 1.0, 4.2)], 'bars': True, 'voice': ('n01', 0.0)},
    {'id': 'c5_tear', 'kind': 'film', 'clips': [clip('a05', 0.6, 2.8)], 'bars': True},
    {'id': 'c6_flow', 'kind': 'film', 'clips': [clip('a06c', 0.5, 2.4)], 'bars': True},
    {'id': 'c7_slide', 'kind': 'film', 'clips': [clip('a06b', 2.2, 3.3)], 'bars': True},
    {'id': 'title', 'kind': 'mg', 'scene': 'title', 'dur': 9.0, 'voice': ('n02', 0.2)},
    {'id': 'why1', 'kind': 'film', 'clips': [clip('a08', 0.0, 9.1, 0.55), clip('a09', 0.0, 9.1, 0.66)], 'plate': 'climate',
     'dur': 18.2, 'dim': 0.55, 'voice': ('n03', 0.2)},
    {'id': 'why2', 'kind': 'film', 'clips': [clip('a10', 0.0, 8.4, 0.7)], 'voice': ('n04', 0.3)},
    {'id': 'who', 'kind': 'film', 'clips': [clip('a11', 0.0, 5.6, 1.0)], 'voice': ('n05', 0.2)},
    {'id': 'five', 'kind': 'mg', 'scene': 'five', 'dur': 5.4},
    {'id': 'p1', 'kind': 'mg', 'scene': 'data', 'dur': 19.6, 'voice': ('n06', 0.3)},
    {'id': 'p2a', 'kind': 'film', 'clips': [clip('a12', 0.0, 10.9, 0.55), clip('a14', 0.0, 8.6, 0.58)], 'plate': 'ch2',
     'dur': 19.5, 'voice': ('n07', 0.2)},
    {'id': 'p2b', 'kind': 'mg', 'scene': 'twin', 'dur': 17.6, 'voice': ('n08', 0.5)},
    {'id': 'p3', 'kind': 'mg', 'scene': 'rules', 'dur': 25.0, 'voice': ('n09', 0.4)},
    {'id': 'res', 'kind': 'mg', 'scene': 'result', 'dur': 16.0, 'voice': ('n10', 1.0)},
    {'id': 'p4', 'kind': 'mg', 'scene': 'weather', 'dur': 29.0, 'voice': ('n11', 0.4), 'voice2': ('n12', 12.7)},
    {'id': 'p5', 'kind': 'mg', 'scene': 'bias', 'dur': 27.0, 'voice': ('n13', 0.6)},
    {'id': 'app1', 'kind': 'app', 'file': APP / 'app3/app_01_start.webm', 'start': 2.0, 'dur': 3.7, 'z0': (0, 0, 1920, 1080),
     'z1': (60, 34, 1800, 1012), 'voice': ('n14', 0.2)},
    {'id': 'app2', 'kind': 'app', 'file': APP / 'app3/app_02_hangcheck_gastein.webm', 'start': 5.0, 'dur': 7.2,
     'z0': (0, 0, 1920, 1080), 'z1': (40, 22, 1840, 1035), 'caption': ('HANG-CHECK · GASTEINER TAL',
     'Prüfstufen relativ im Umkreis · Demonstration, noch nicht an neuen Gebieten bestätigt')},
    {'id': 'app2b', 'kind': 'app', 'file': APP / 'app3/app_04_starkregen.webm', 'start': 8.0, 'dur': 5.8,
     'z0': (0, 0, 1920, 1080), 'z1': (240, 135, 1500, 844), 'caption': ('HIER ZUERST HINSCHAUEN',
     'Fünf Prüfpunkte, eine Rangfolge · keine Wahrscheinlichkeit · nicht markiert heißt nicht sicher')},
    {'id': 'app3', 'kind': 'app', 'file': APP / 'app3/app_04_starkregen.webm', 'start': 13.5, 'dur': 10.2,
     'z0': (445, 250, 1475, 830), 'z1': (830, 625, 800, 450), 'voice': ('n15', 0.2),
     'caption': ('MÖGLICHER WEG HANGABWÄRTS', 'Szenario, ungeprüft · Reichweiten aus der Literatur · Straßen und Gebäude: OpenStreetMap')},
    {'id': 'use1', 'kind': 'film', 'clips': [clip('a09', 2.0, 2.3)], 'voice': ('n16', 0.1)},
    {'id': 'use2', 'kind': 'film', 'clips': [clip('a15', 1.0, 2.2)]},
    {'id': 'use3', 'kind': 'film', 'clips': [clip('a14', 1.5, 2.9)]},
    {'id': 'fazit', 'kind': 'film', 'clips': [clip('a13', 0.0, 16.0, 0.44)], 'plate': 'fazit', 'dur': 16.0, 'dim': 0.42,
     'voice': ('n17', 0.5)},
    {'id': 'next', 'kind': 'film', 'clips': [clip('a10', 2.0, 7.6, 0.5)], 'plate': 'next', 'dur': 7.6, 'dim': 0.4,
     'voice': ('n18', 0.3)},
    {'id': 'last', 'kind': 'film', 'clips': [clip('a04', 0.0, 5.6, 0.9)], 'bars': True, 'voice': ('n19', 0.1)},
    {'id': 'end', 'kind': 'mg', 'scene': 'end', 'dur': 7.0},
]


def label_png() -> Path:
    path = BUILD / f'label_{W}.png'
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype('C:/Windows/Fonts/segoeuil.ttf', max(9, int(20 * S)))
    ImageDraw.Draw(im).text((W - 28 * S, H - 26 * S), AI_LABEL, font=font, fill=(255, 255, 255, 120), anchor='rs')
    im.save(path)
    return path


def caption_png(key: str, title: str, sub: str) -> Path:
    path = BUILD / f'cap_{key}_{W}.png'
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top = H - 112 * S
    d.rectangle((0, top, W, H), fill=(5, 8, 13, 235))
    d.text((60 * S, top + 18 * S), title, font=ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf', int(34 * S)), fill=(255, 138, 42, 255))
    d.text((60 * S, top + 62 * S), sub, font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', int(23 * S)), fill=(230, 236, 240, 255))
    im.save(path)
    return path


GRADE = f'scale={W}:{H}:flags=lanczos,eq=contrast=1.06:saturation=0.92,vignette=PI/5,noise=alls=5:allf=t,fps={FPS},format=yuv420p'
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-an']


def render_film(seg: dict, out: Path) -> float:
    inputs, chains = [], []
    total = 0.0
    for i, c in enumerate(seg['clips']):
        source_dur = c['dur'] * c['speed']
        inputs += ['-ss', str(c['start']), '-t', f'{source_dur:.3f}', '-i', str(c['file'])]
        chains.append(f'[{i}:v]setpts=PTS/{c["speed"]},{GRADE}[c{i}]')
        total += c['dur']
    n = len(seg['clips'])
    graph = ';'.join(chains) + ';' + ''.join(f'[c{i}]' for i in range(n)) + f'concat=n={n}:v=1[base]'
    last = 'base'
    if seg.get('dim'):
        graph += f';[{last}]eq=brightness={-(1 - seg["dim"]) * 0.42:.3f}:saturation=0.8[dim]'
        last = 'dim'
    k = n
    if seg.get('plate'):
        inputs += ['-i', str(MG / f'{seg["plate"]}.mp4')]
        # Screen blend must run in RGB; on YUV planes it shifts the chroma and tints everything magenta.
        graph += (f';[{k}:v]scale={W}:{H},fps={FPS},format=gbrp[pl];[{last}]format=gbrp[fb];'
                  f'[fb][pl]blend=all_mode=screen:shortest=1,format=yuv420p[bl]')
        last = 'bl'
        k += 1
    if seg.get('bars'):
        bar = int(H * 0.12)
        graph += f';[{last}]drawbox=x=0:y=0:w={W}:h={bar}:color=black:t=fill,drawbox=x=0:y={H - bar}:w={W}:h={bar}:color=black:t=fill[bb]'
        last = 'bb'
    inputs += ['-i', str(label_png())]
    graph += f';[{last}][{k}:v]overlay=0:0[out]'
    run([*inputs, '-filter_complex', graph, '-map', '[out]', '-t', f'{total:.3f}', *ENC, str(out)])
    return total


def render_app(seg: dict, out: Path) -> float:
    (x0, y0, w0, h0), (x1, y1, w1, h1) = seg['z0'], seg['z1']
    d = seg['dur']
    # Smooth virtual camera move inside the recording (crop window eased with smoothstep).
    p = f'(min(t/{d},1)*min(t/{d},1)*(3-2*min(t/{d},1)))'
    crop = (f"crop=w='{w0}+({w1}-{w0})*{p}':h='{h0}+({h1}-{h0})*{p}':"
            f"x='{x0}+({x1}-{x0})*{p}':y='{y0}+({y1}-{y0})*{p}':exact=1")
    graph = f'[0:v]fps={FPS},setpts=PTS-STARTPTS,{crop},scale={W}:{H}:flags=lanczos,format=yuv420p[v]'
    inputs = ['-ss', str(seg['start']), '-t', str(d), '-i', str(seg['file'])]
    last = 'v'
    if seg.get('caption'):
        inputs += ['-i', str(caption_png(seg['id'], *seg['caption']))]
        graph += f';[v][1:v]overlay=0:0:format=auto[o]'
        last = 'o'
    run([*inputs, '-filter_complex', graph, '-map', f'[{last}]', '-t', str(d), *ENC, str(out)])
    return d


def render_mg(seg: dict, out: Path) -> float:
    run(['-i', str(MG / f'{seg["scene"]}.mp4'), '-vf', f'scale={W}:{H}:flags=lanczos,noise=alls=3:allf=t,format=yuv420p', '-t', str(seg['dur']), *ENC, str(out)])
    return seg['dur']


def render_black(seg: dict, out: Path) -> float:
    run(['-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}:r={FPS}', '-t', str(seg['dur']), *ENC, str(out)])
    return seg['dur']


def load_audio(path: Path, loudnorm: bool = False) -> np.ndarray:
    """Decode to float stereo at SR; shape (n, 2)."""
    af = ['-af', 'loudnorm=I=-16:TP=-2:LRA=7'] if loudnorm else []
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), *af, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def place(buf: np.ndarray, sound: np.ndarray, when_s: float, gain: float = 1.0) -> None:
    i = int(when_s * SR)
    if i >= len(buf):
        return
    n = min(len(sound), len(buf) - i)
    buf[i:i + n] += sound[:n] * gain


def ramp(n: int, points: list[tuple[float, float]]) -> np.ndarray:
    """Piecewise-linear gain curve from (seconds, gain) points."""
    xs, ys = zip(*points)
    return np.interp(np.arange(n) / SR, xs, ys)


def mix_audio(at: dict, total_s: float, out: Path) -> None:
    n = int(total_s * SR)
    voice, sfx, music = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    previous_end, previous_name = 0.0, ''
    for seg in SEGMENTS:
        for key in ('voice', 'voice2'):
            if seg.get(key):
                name, off = seg[key]
                take = load_audio(VOICE / f'{name}.mp3', loudnorm=True)
                when = seg['t'] + off
                if when < previous_end:
                    print(f'WARNUNG: {name} beginnt {previous_end - when:.2f} s vor dem Ende von {previous_name}')
                place(voice, take, when)
                previous_end, previous_name = when + len(take) / SR, name
    title, boom = at['title'], at['title'] + 3.9
    for name, when, gain in [('drop', at['c1_drop'] + 2.6, 1.0), ('thunder', at['c2_storm'], 0.9), ('slide', at['c5_tear'], 1.0),
                             ('scan', title + 0.2, 0.6), ('boom', boom, 1.0), ('scan', at['p1'] + 7.6, 0.4),
                             ('boom', at['res'] + 0.2, 0.5), ('boom', at['end'] + 1.8, 0.75)]:
        place(sfx, load_audio(SFX / f'{name}.mp3'), when, gain)
    # Rain bed through the cold open, fading out under the title.
    rain = load_audio(SFX / 'rain.mp3')
    rain_len = int((title + 2 - at['c1_drop']) * SR)
    bed = np.tile(rain, (rain_len // len(rain) + 1, 1))[:rain_len] * ramp(rain_len, [(0, 0), (3, .55), (title - at['c1_drop'], .55), (title + 2 - at['c1_drop'], 0)])[:, None]
    place(sfx, bed, at['c1_drop'])
    # Music: near silent in the cold open, full at the title impact, cue 2 takes over before the app chapter.
    app_t = at['app1']
    cue1, cue2 = load_audio(SFX / 'music.mp3'), load_audio(SFX / 'music2.mp3')
    cue1 = cue1[:min(len(cue1), n)]
    lead = 12.0
    place(music, cue1 * ramp(len(cue1), [(0, .03), (boom - lead - .1, .12), (boom - lead, .8), (boom - lead + 6, .8), (boom - lead + 9, .42), (app_t - lead - 2, .42), (app_t - lead + 3, 0), (10000, 0)])[:, None], lead)
    start2 = app_t - 2
    fade_out_at = total_s - start2 - 3
    place(music, cue2 * ramp(len(cue2), [(0, 0), (5, .55), (fade_out_at, .55), (fade_out_at + 3, 0), (10000, 0)])[:, None], start2)
    # Duck music under the voice with a smoothed envelope (fast attack, slow release).
    level = np.abs(voice).max(axis=1)
    active = (level > 0.01).astype(float)
    attack, release = np.exp(-1 / (0.03 * SR)), np.exp(-1 / (0.5 * SR))
    env = np.zeros(n)
    e = 0.0
    for i, v in enumerate(active):
        e = attack * e + (1 - attack) * v if v > e else release * e + (1 - release) * v
        env[i] = e
    mix = voice + sfx + music * (1 - 0.72 * env)[:, None]
    mix = mix * min(1.0, 0.89 / np.abs(mix).max())  # headroom for AAC overshoot
    proc = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'aac', '-b:a', '192k', str(out)],
                          input=mix.astype(np.float32).tobytes(), check=True)
    assert proc.returncode == 0


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    label_png()
    t, timeline, listing = 0.0, [], []
    for seg in SEGMENTS:
        out = BUILD / f'{seg["id"]}.mp4'
        renderer = {'film': render_film, 'app': render_app, 'mg': render_mg, 'black': render_black}[seg['kind']]
        if not args.audio_only:
            renderer(seg, out)
        real = duration(out)
        timeline.append({'id': seg['id'], 'start': round(t, 3), 'dur': round(real, 3)})
        listing.append(f"file '{out.as_posix()}'")
        seg['t'] = t
        t += real
    (BUILD / 'concat.txt').write_text('\n'.join(listing), encoding='utf-8')
    (BUILD / 'timeline.json').write_text(json.dumps(timeline, indent=1), encoding='utf-8')
    if not args.audio_only:
        run(['-f', 'concat', '-safe', '0', '-i', str(BUILD / 'concat.txt'), *ENC, str(BUILD / 'picture.mp4')])
    total = duration(BUILD / 'picture.mp4')
    at = {s['id']: s['t'] for s in SEGMENTS}
    audio = BUILD / 'audio.m4a'
    mix_audio(at, total, audio)
    final = OUT / args.out
    run(['-i', str(BUILD / 'picture.mp4'), '-i', str(audio), '-c:v', 'copy', '-c:a', 'copy', '-t', f'{total:.3f}',
         '-movflags', '+faststart', str(final)])
    print('film', final, round(duration(final), 2), 's', round(final.stat().st_size / 1e6, 1), 'MB')

if __name__ == '__main__':
    main()
