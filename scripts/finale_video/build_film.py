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
AI, MG, SFX = OUT / 'ai', OUT / 'mgclips', OUT / 'sfx'
APP = Path('C:/Users/mario/Documents/HomeProjects/PreSlide/.claude/worktrees/video-pitch-script-497edf/deliverables/pitch')
FPS = 25
SR = 48000
AI_LABEL = 'KI-generierte Illustration'

parser = argparse.ArgumentParser()
parser.add_argument('--width', type=int, default=1920)
parser.add_argument('--audio-only', action='store_true', help='keep the rendered picture, only remix the sound')
parser.add_argument('--out', default='Talwacht_Finale_v4.mp4')
args = parser.parse_args()
VOICES = [OUT / 'voice_v4_fast']  # voice Alistair via Higgsfield/ElevenLabs v4; narration at 1.15x, the closing quote untouched
FINALE_HIT_S = 76.0  # position in sfx/finale.mp3 that lands on the title; its loudest stretch (measured) runs to 83 s
W, H = args.width, args.width * 9 // 16
S = W / 1920


def duration(path: Path) -> float:
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def run(cmd: list[str]) -> None:
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *cmd], check=True)


def clip(name, start=0.0, dur=3.0, speed=1.0, crop=None):
    return {'file': AI / f'{name}.mp4', 'start': start, 'dur': dur, 'speed': speed, 'crop': crop}


def take(name: str) -> Path:
    return next(d / f'{name}.mp3' for d in VOICES if (d / f'{name}.mp3').exists())


# kind: film (AI clips, optional screen-blended plate), mg (full-screen graphics), app (screen recording), black.
# voice: (file, offset seconds into the segment).
SEGMENTS = [
    {'id': 'black0', 'kind': 'black', 'dur': 0.5},
    {'id': 'c1_drop', 'kind': 'film', 'clips': [clip('a01', 0.8, 2.6)], 'bars': True},
    {'id': 'c2_storm', 'kind': 'film', 'clips': [clip('a02', 1.0, 2.4)], 'bars': True},
    {'id': 'c3_crack', 'kind': 'film', 'clips': [clip('a03', 0.5, 1.4)], 'bars': True},
    {'id': 'c4_valley', 'kind': 'film', 'clips': [clip('a04', 1.0, 4.6)], 'bars': True, 'voices': [('n01', 0.05)]},
    {'id': 'c5_tear', 'kind': 'film', 'clips': [clip('m1', 0.8, 2.8)], 'bars': True},
    {'id': 'c7_slide', 'kind': 'film', 'clips': [clip('m0', 0.0, 3.6)], 'bars': True},
    {'id': 'title', 'kind': 'mg', 'scene': 'title', 'dur': 6.0, 'voices': [('n02', 0.2)]},
    {'id': 'why1', 'kind': 'film', 'clips': [clip('p2', 0.0, 7.4, 1.0), clip('a09', 0.0, 7.3, 0.66)], 'plate': 'climate',
     'dur': 14.7, 'dim': 0.8, 'voices': [('n03', 0.2)]},
    {'id': 'why2', 'kind': 'film', 'clips': [clip('a10', 0.0, 7.4, 0.7)], 'voices': [('n04', 0.3)]},
    {'id': 'who', 'kind': 'film', 'clips': [clip('a11', 0.0, 4.4, 1.0)], 'voices': [('n05', 0.15)]},
    {'id': 'five', 'kind': 'mg', 'scene': 'five', 'dur': 3.7},
    {'id': 'p1', 'kind': 'mg', 'scene': 'data', 'dur': 14.2, 'voices': [('n06', 0.2)]},
    {'id': 'p2a', 'kind': 'film', 'clips': [clip('k3', 0.0, 5.6, 0.8), clip('a14', 0.0, 4.6, 1.0), clip('k4', 0.0, 3.2, 1.0), clip('k3', 3.0, 2.4, 1.0)], 'plate': 'ch2',
     'dur': 15.8, 'voices': [('n07', 0.15)]},
    {'id': 'p2b', 'kind': 'mg', 'scene': 'twin', 'dur': 16.2, 'voices': [('n08', 0.3)]},
    {'id': 'p3', 'kind': 'mg', 'scene': 'rules', 'dur': 23.1, 'voices': [('n09a', 0.3), ('n09b', 12.6), ('n09c', 16.2)]},
    {'id': 'res', 'kind': 'mg', 'scene': 'result', 'dur': 28.1, 'voices': [('n10a', 0.3), ('n10b', 4.25), ('n10c', 14.6), ('n10d', 23.0)]},
    {'id': 'p4', 'kind': 'mg', 'scene': 'weather', 'dur': 34.3, 'voices': [('n11a', 0.3), ('n11b', 11.6), ('n12', 15.2)]},
    {'id': 'p5', 'kind': 'mg', 'scene': 'bias', 'dur': 28.8, 'voices': [('n13a', 0.4), ('n13b', 18.0)]},
    {'id': 'app1', 'kind': 'app', 'file': APP / 'app3/app_01_start.webm', 'start': 2.0, 'dur': 3.7, 'z0': (0, 0, 1920, 1080),
     'z1': (60, 34, 1800, 1012), 'voices': [('n14', 0.2)]},
    {'id': 'app2', 'kind': 'app', 'file': APP / 'app3/app_02_hangcheck_gastein.webm', 'start': 5.0, 'dur': 6.0,
     'z0': (0, 0, 1920, 1080), 'z1': (40, 22, 1840, 1035), 'caption': ('HANG-CHECK · GASTEINER TAL',
     'Prüfstufen relativ im Umkreis · Demonstration, noch nicht an neuen Gebieten bestätigt')},
    {'id': 'app2b', 'kind': 'app', 'file': APP / 'app3/app_04_starkregen.webm', 'start': 8.0, 'dur': 5.2,
     'z0': (0, 0, 1920, 1080), 'z1': (240, 135, 1500, 844), 'caption': ('HIER ZUERST HINSCHAUEN',
     'Fünf Prüfpunkte, eine Rangfolge · keine Wahrscheinlichkeit · nicht markiert heißt nicht sicher')},
    {'id': 'app3', 'kind': 'app', 'file': APP / 'app3/app_04_starkregen.webm', 'start': 13.5, 'dur': 9.5,
     'z0': (445, 250, 1475, 830), 'z1': (830, 625, 800, 450), 'voices': [('n15', 0.2)],
     'caption': ('MÖGLICHER WEG HANGABWÄRTS', 'Szenario, ungeprüft · Reichweiten aus der Literatur · Straßen und Gebäude: OpenStreetMap')},
    {'id': 'use1', 'kind': 'film', 'clips': [clip('a09', 2.0, 2.2)], 'voices': [('n16', 0.1)]},
    {'id': 'use2', 'kind': 'film', 'clips': [clip('a15', 1.0, 2.0)]},
    {'id': 'use3', 'kind': 'film', 'clips': [clip('a14', 1.5, 2.2)]},
    {'id': 'fazit', 'kind': 'film', 'clips': [clip('a13', 0.0, 13.4, 0.52)], 'plate': 'fazit', 'dur': 13.4, 'dim': 0.42,
     'voices': [('n17', 0.3)]},
    {'id': 'next', 'kind': 'film', 'clips': [clip('a10', 2.0, 6.7, 0.5)], 'plate': 'next', 'dur': 6.7, 'dim': 0.4,
     'voices': [('n18', 0.2)]},
    {'id': 'last', 'kind': 'film', 'clips': [clip('a02', 0.3, 5.5, 1.0)], 'voices': [('n19', 0.1)]},
    {'id': 'q1', 'kind': 'film', 'clips': [clip('m3', 0.0, 8.0, 1.0)], 'plate': 'q1', 'dur': 8.0, 'voices': [('q1', 3.2), ('q2', 5.5)]},
    {'id': 'q3', 'kind': 'film', 'clips': [clip('m4', 0.0, 2.8, 1.0)], 'plate': 'q2', 'dur': 2.8, 'voices': [('q3a', 0.25)]},
    {'id': 'spuren', 'kind': 'mg', 'scene': 'spuren', 'dur': 8.98, 'voices': [('q3b', 0.1), ('q4', 3.4), ('q5', 6.15)]},
    {'id': 'end', 'kind': 'mg', 'scene': 'end', 'dur': 7.7},
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
ENC = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-an']


def render_film(seg: dict, out: Path) -> float:
    inputs, chains = [], []
    total = 0.0
    for i, c in enumerate(seg['clips']):
        source_dur = c['dur'] * c['speed']
        inputs += ['-ss', str(c['start']), '-t', f'{source_dur:.3f}', '-i', str(c['file'])]
        smooth = f'minterpolate=fps={FPS}:mi_mode=blend,' if c['speed'] < 0.8 else ''
        crop = f'crop={c["crop"]},' if c['crop'] else ''
        chains.append(f'[{i}:v]{crop}setpts=PTS/{c["speed"]},{smooth}{GRADE}[c{i}]')
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
    run(['-i', str(MG / f'{seg["scene"]}.mp4'), '-vf', f'scale={W}:{H}:flags=lanczos,format=yuv420p', '-t', str(seg['dur']), *ENC, str(out)])
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


def mix_audio(seg_at: dict, total_s: float, out: Path) -> None:
    at = seg_at
    n = int(total_s * SR)
    voice, sfx, music = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    previous_end, previous_name = 0.0, ''
    voice_at = {}
    for seg in SEGMENTS:
        for name, off in seg.get('voices', []):
            sample = load_audio(take(name), loudnorm=name != 'q5')  # q5 keeps its own level and hall (final_line.py)
            when = seg['t'] + off
            if when < previous_end:
                print(f'WARNUNG: {name} beginnt {previous_end - when:.2f} s vor dem Ende von {previous_name}')
            if when + len(sample) / SR > seg['t'] + seg['dur_real'] and seg['id'] not in ('who', 'app1', 'use1'):
                print(f'WARNUNG: {name} endet {when + len(sample) / SR - seg["t"] - seg["dur_real"]:.2f} s nach {seg["id"]}')
            place(voice, sample, when, 1.2 if name.startswith('q') and name != 'q5' else 1.0)
            voice_at[name] = (when, when + len(sample) / SR)
            previous_end, previous_name = when + len(sample) / SR, name
    title, boom = at['title'], at['title'] + 3.9
    hit = at['end']
    for name, when, gain in [('drop', at['c1_drop'] + 2.0, 1.0), ('thunder', at['c2_storm'], 0.9), 
                             ('scan', title + 0.2, 0.6), ('boom', boom, 1.0), ('scan', at['p1'] + 5.6, 0.4),
                             ('boom', at['res'] + 0.5, 0.5), ('boom', hit, 0.8)]:
        place(sfx, load_audio(SFX / f'{name}.mp3'), when, gain)
    # Debris flow: normalised takes; the rumble dies away before the title line.
    place(sfx, load_audio(SFX / 'tear.mp3', loudnorm=True), at['c5_tear'], 0.9)
    rumble = load_audio(SFX / 'debris.mp3', loudnorm=True)
    place(sfx, rumble * ramp(len(rumble), [(0, 0), (.3, 1.2), (4.3, 1.2), (6.0, 0), (100, 0)])[:, None], at['c7_slide'] - .4)
    # Rain bed through the cold open, fading out under the title.
    rain = load_audio(SFX / 'rain.mp3')
    rain_len = int((title + 2 - at['c1_drop']) * SR)
    bed = np.tile(rain, (rain_len // len(rain) + 1, 1))[:rain_len] * ramp(rain_len, [(0, 0), (3, .55), (title - at['c1_drop'], .55), (title + 2 - at['c1_drop'], 0)])[:, None]
    place(sfx, bed, at['c1_drop'])
    # Cue 1: as before up to the app chapter, near silent in the cold open, full at the title impact.
    app_t = at['app1']
    cue1 = load_audio(SFX / 'music.mp3')
    cue1 = cue1[:min(len(cue1), n)]
    lead = 12.0
    place(music, cue1 * ramp(len(cue1), [(0, .03), (boom - lead - .1, .12), (boom - lead, .8), (boom - lead + 6, .8), (boom - lead + 9, .42), (app_t - lead + 8, .42), (app_t - lead + 14, 0), (10000, 0)])[:, None], lead)
    # Finale cue: one continuous crescendo (measured -46 dB to -10 dB). Its loudest stretch starts exactly on the title.
    cue = load_audio(SFX / 'finale.mp3')
    cue_start = hit - FINALE_HIT_S
    listen0, listen1 = voice_at['q4']
    line0 = voice_at['q5'][0]
    word_end = hit + 0.75  # "Talwacht" starts exactly on the cut to the title
    last_t, q1_t = at['last'] - cue_start, at['q1'] - cue_start
    curve = [(0, 0), (6, 1.0), (last_t - 20, 1.0), (last_t, 1.5),
             # After "wo man zuerst hinschaut": seconds without a voice, the music really goes up.
             (q1_t + 2.6, 2.4), (q1_t + 3.2, 1.9),
             # No dip from here on: the music keeps climbing under the last words and opens fully after "Talwacht".
             (listen0 - cue_start - .5, 1.8), (line0 - cue_start, 1.8), (hit - cue_start, 1.9), (1000, 1.9)]
    gain = ramp(len(cue), curve)
    place(music, cue * gain[:, None], cue_start)
    # Duck under the voice with a smoothed envelope (fast attack, slow release); gentler toward the end so the build stays audible.
    level = np.abs(voice).max(axis=1)
    active = (level > 0.01).astype(float)
    active[int(word_end * SR):] = 0  # the hall of the last word must not hold the orchestra down
    attack, release = np.exp(-1 / (0.03 * SR)), np.exp(-1 / (0.5 * SR))
    env = np.zeros(n)
    e = 0.0
    for i, v in enumerate(active):
        e = attack * e + (1 - attack) * v if v > e else release * e + (1 - release) * v
        env[i] = e
    depth = ramp(n, [(0, .72), (at['fazit'], .72), (at['last'], .65), (at['q1'] + 3.0, .75), (line0 - .05, .75), (line0 + .1, .6), (total_s, .6)])
    mix = voice + sfx + music * (1 - depth * env)[:, None]
    mix *= ramp(n, [(0, 1), (total_s - 1.6, 1), (total_s, 0)])[:, None]
    wav = BUILD / 'mix.f32'
    wav.write_bytes(mix.astype(np.float32).tobytes())
    raw = ['-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', str(wav)]
    # Linear mastering: measure once, apply one gain, limit the peaks. Dynamic loudnorm would flatten the build.
    report = subprocess.run(['ffmpeg', '-hide_banner', *raw, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=20:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    measured = json.loads(report[report.rindex('{'):report.rindex('}') + 1])
    gain_db = -14.0 - float(measured['input_i'])
    print('Lautheit gemessen', measured['input_i'], 'LUFS, Spitze', measured['input_tp'], 'dBTP, Verstaerkung', round(gain_db, 2), 'dB')
    run([*raw, '-af', f'volume={gain_db:.2f}dB,alimiter=limit=0.82:level=false:attack=3:release=120', '-c:a', 'aac', '-b:a', '256k', str(out)])
    print('Audioabschnitte (dB RMS):', {k: round(float(20 * np.log10(np.sqrt((mix[int(at[k] * SR):int(at[k] * SR) + 3 * SR] ** 2).mean()) + 1e-9)), 1) for k in ('c7_slide', 'res', 'app3', 'fazit', 'last', 'q1', 'end')})


FADES = {'why1': (.5, 0), 'who': (.35, 0), 'five': (.3, 0), 'app1': (.5, 0), 'use1': (.3, 0), 'fazit': (.6, .4), 'next': (.4, .3),
         'last': (.4, .5), 'q1': (.8, .4), 'q3': (.4, 0), 'end': (0, .8), 'p5': (0, .4), 'why2': (.3, .3)}


def add_fades(path: Path, seg_id: str) -> None:
    if seg_id not in FADES:
        return
    fin, fout = FADES[seg_id]
    dur = duration(path)
    filters = []
    if fin:
        filters.append(f'fade=t=in:st=0:d={fin}')
    if fout:
        filters.append(f'fade=t=out:st={dur - fout:.3f}:d={fout}')
    tmp = path.with_name(path.stem + '_f.mp4')
    run(['-i', str(path), '-vf', ','.join(filters), *ENC, str(tmp)])
    tmp.replace(path)


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    label_png()
    t, timeline, listing = 0.0, [], []
    for seg in SEGMENTS:
        out = BUILD / f'{seg["id"]}.mp4'
        renderer = {'film': render_film, 'app': render_app, 'mg': render_mg, 'black': render_black}[seg['kind']]
        if not args.audio_only:
            renderer(seg, out)
            add_fades(out, seg['id'])
        real = duration(out)
        timeline.append({'id': seg['id'], 'start': round(t, 3), 'dur': round(real, 3)})
        listing.append(f"file '{out.as_posix()}'")
        seg['t'] = t
        seg['dur_real'] = real
        t += real
    (BUILD / 'concat.txt').write_text('\n'.join(listing), encoding='utf-8')
    (BUILD / 'timeline.json').write_text(json.dumps(timeline, indent=1), encoding='utf-8')
    if not args.audio_only:
        # Fixed rate for the final picture: the entry form allows 500 MB at most.
        final_enc = ['-c:v', 'libx264', '-preset', 'medium', '-b:v', '11M', '-maxrate', '18M', '-bufsize', '24M', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-an']
        run(['-f', 'concat', '-safe', '0', '-i', str(BUILD / 'concat.txt'), *final_enc, str(BUILD / 'picture.mp4')])
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
