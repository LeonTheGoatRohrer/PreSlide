"""Assemble the Talwacht pitch film from the rendered clips, app recordings and a synthetic narration.

Narration: Microsoft neural TTS via edge-tts (voice configurable); replace build/voice_*.mp3 with your own
recordings of the same text to use your own voice (keep the file names, rerun with --keep-voice).
Music: a quiet synthetic drone generated with ffmpeg (no third-party audio).
Output: deliverables/pitch/Talwacht_Pitch.mp4 and Talwacht_Pitch.srt.

Usage: .venv/Scripts/python scripts/pitch/build_film.py [--voice de-AT-JonasNeural] [--keep-voice]
(edge-tts must be importable, e.g. PYTHONPATH pointing to a folder where it is installed.)
"""
import argparse
import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PITCH = ROOT / 'deliverables/pitch'
BUILD = PITCH / 'build'
FPS = 25
VOICE_DELAY_S = 0.6
TAIL_S = 0.7

# (clip, start_s, duration_s or None = to end); app clips come from deliverables/pitch/app
SEGMENTS = [
    dict(id='01_hook', clips=[('app3/app_00_hero.webm|crop=1920:1062:0:10', 0.8, 7.5), ('clips/a1_terminal.mp4', 0, 4.2), ('app3/app_02_hangcheck_gastein.webm|crop=1440:810:480:100', 'mark:app_02_hangcheck_gastein:-2.0', 6.0, 'clips/a1_ort.mp4')],
         text='Achtzehnter November 2019. Gasteiner Tal. Ein Eintrag im Naturgefahren-Inventar: Hangmure. Rundherum: Hänge. Genauso steil. Genauso hoch. Von ihnen: keine Meldung. Was unterscheidet diesen einen Hang von seinen Zwillingen – bevor etwas passiert?'),
    dict(id='02_titel', clips=[('clips/a1_titel.mp4', 1.0, 5.0)], text=''),
    dict(id='03_idee', clips=[('app3/app_01_start.webm', 3.0, None)],
         text='Rutschungen und Muren treffen in Österreich jedes Jahr Straßen, Bahnlinien und Häuser. Wir wollten wissen: Lässt sich der betroffene Hang von seinen Zwillingen unterscheiden – nur mit dem, was vorher bekannt war?'),
    dict(id='04_daten', clips=[('clips/a3_01_ebenen.mp4', 3.5, None)],
         text='Talwacht baut jeden Hang aus echten Daten neu auf: Gelände auf dreißig Meter genau, Landbedeckung, Geologie – und Niederschlag, Stunde für Stunde, sechzig Tage zurück.'),
    dict(id='05_filter', clips=[('clips/a3_02_filter_oesterreich.mp4', 0, None)],
         text='Aus über fünfundzwanzigtausend Einträgen bleibt nur, was gesichert ist: Datum, Prozess, Lage. 423 Ereignisse.'),
    dict(id='05b_gastein', delay=2.2, clips=[('clips/a3_02_gastein_ausschluss.mp4|setpts=PTS/1.5', 0, None)],
         text='Und die Hangmure aus dem Gasteiner Tal? Aussortiert – ob es wirklich eine war, ist nicht bestätigt.'),
    dict(id='06_zwillinge', clips=[('clips/a3_03_zwillinge.mp4', 0, None)],
         text='Jedes Ereignis bekommt fünf Zwillinge: in der Nähe, gleich steil, gleich hoch, gleich ausgerichtet – mit demselben Stichtag.'),
    dict(id='07_regeln', clips=[('clips/a3_04_zeitwand.mp4', 0, None), ('clips/a3_04_gruppen.mp4', 0, None), ('clips/a3_04_siegel.mp4', 0, None)],
         text='Keine Information ab dem Ereignis. Ein Hang und seine Zwillinge bleiben immer zusammen. Der Plan wurde vorab festgeschrieben, der Test versiegelt.'),
    dict(id='08_modell', clips=[('clips/a3_05_modell.mp4', 0, None)],
         text='Im Kern: eine selbst gebaute bedingte logistische Regression – gegengeprüft mit Random Forest, Gradient Boosting und Zufallsvergleichen.'),
    dict(id='09_ergebnis', clips=[('clips/a4_ergebnis.mp4', 0, None), ('clips/a4_balken.mp4', 0, None),
                                  ('clips/a4_ungesehen.mp4', 0, None), ('clips/a4_extremwetter.mp4', 0, None)],
         text='Das Ergebnis: In rund drei von vier Vergleichen liegt der betroffene Hang vor seinen Zwillingen. Null Komma fünfundsiebzig – Zufall wäre null Komma fünf. Den Großteil leistet das Gelände. Ein Zusatznutzen des Wetters ist nicht belegt – auch nicht auf neuen Ereignissen. Und doch: Die drei Tage vor einem Ereignis waren in einem Viertel der Fälle extrem nass. Erwartet wäre jeder zwanzigste.'),
    dict(id='10_spiegel', clips=[('clips/a5_meldebias.mp4', 0, None), ('clips/a5_grenzen.mp4', 0, None), ('clips/a5_kein_warnsystem.mp4', 0, None)],
         text='Allein der Abstand zu Straßen und Häusern trennt fast perfekt – gemeldet wird, was Menschen sehen. Elf unabhängige Episoden, eine dominiert. Nicht gemeldet heißt nicht sicher. Talwacht warnt nicht – es gibt eine begründete Reihenfolge.'),
    dict(id='11_produkt', clips=[('app3/app_02_hangcheck_gastein.webm', 'mark:app_02_hangcheck_gastein:-1.0', 9.0), ('app3/app_04_starkregen.webm', 'mark:app_04_ready:+2.5', 12.0)],
         text='Daraus wurde der Hang-Check: Ort wählen – zum Beispiel das Gasteiner Tal. Sofort zeigt Talwacht die auffälligsten Hänge und fünf Prüfpunkte: hier zuerst hinschauen. Bei Starkregen: mögliche Fließwege – und welche Straßen und Häuser im Szenario liegen.'),
    dict(id='12_finale', clips=[('app3/app_05_belastbar.webm', 2.0, 5.0), ('clips/a7_endtafel.mp4', 0, 7.0)],
         text='Als Nächstes: ein vorab registrierter Test mit Ereignissen, die erst noch kommen. Talwacht. Wo zuerst hinschauen, wenn der Starkregen kommt.'),
]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'command failed: {" ".join(map(str, cmd))[:300]}\n{r.stderr[-2000:]}')
    return r.stdout


def duration(path):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]).strip())


async def tts(text, out, voice, rate):
    import ssl

    import edge_tts
    import edge_tts.communicate as communicate
    # edge-tts pins certifi; use the system store plus the project CA bundle (TLS inspection on this machine)
    ctx = ssl.create_default_context()
    bundle = ROOT / 'data/runtime/windows-ca.pem'
    if bundle.exists():
        ctx.load_verify_locations(cafile=str(bundle))
    communicate._SSL_CTX = ctx
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def voice_files(voice, rate, keep):
    for seg in SEGMENTS:
        out = BUILD / f'voice_{seg["id"]}.mp3'
        seg['voice'] = out if seg['text'] else None
        if not seg['text'] or (keep and out.exists()):
            continue
        asyncio.run(tts(seg['text'], out, voice, rate))


def resolve_marks():
    marks_file = PITCH / 'app3/marks.json'
    marks = json.loads(marks_file.read_text(encoding='utf-8')) if marks_file.exists() else {}
    for seg in SEGMENTS:
        fixed = []
        for path, start, *rest in seg['clips']:
            if isinstance(start, str) and start.startswith('mark:'):
                _, name, off = start.split(':')
                start = max(marks[name] + float(off), 0.0)
            fixed.append((path, start, *rest))
        seg['clips'] = fixed


def speed(path):
    m = re.search(r'setpts=PTS/([0-9.]+)', path)
    return float(m.group(1)) if m else 1.0


def clip_len(path, start, dur):
    total = duration(PITCH / path.split('|')[0])
    raw = min(dur, total - start) if dur else total - start
    return raw / speed(path)


def build_segment(seg, idx):
    lens = [clip_len(c[0], c[1], c[2]) for c in seg['clips']]
    vis = sum(lens)
    speech = duration(seg['voice']) if seg['voice'] else 0.0
    delay_s = seg.get('delay', VOICE_DELAY_S)
    length = (speech + delay_s + TAIL_S) if speech else vis
    k = min(1.0, length / vis)
    seg['length'] = length
    seg['speech'] = speech
    inputs, filters, labels = [], [], []
    n = 0
    for k, (c, (path, start, _dur, *overlay)) in enumerate(zip(lens, seg['clips'])):
        path, _, pre = path.partition('|')
        pre = pre + ',' if pre else ''
        inputs += ['-ss', str(start), '-t', f'{c * speed(pre):.3f}', '-i', str(PITCH / path)]
        base = n
        n += 1
        chain = f'[{base}:v]{pre}fps={FPS},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0E1822,setsar=1,format=gbrp'
        if overlay:
            inputs += ['-t', f'{c:.3f}', '-i', str(PITCH / overlay[0])]
            filters.append(f'[{n}:v]fps={FPS},scale=1920:1080,setsar=1,format=gbrp,tpad=stop_mode=clone:stop_duration=30,trim=duration={c:.3f}[ov{k}]')
            filters.append(f'{chain}[b{k}]')
            chain = f'[b{k}][ov{k}]blend=all_mode=screen'
            n += 1
        extra = length - vis if k == len(lens) - 1 else 0.0
        if extra > 0.01:
            chain += f',tpad=stop_mode=clone:stop_duration={extra:.3f}'
        d = c + max(extra, 0.0)
        chain += f',format=yuv420p,fade=t=in:st=0:d=0.35,fade=t=out:st={max(d - 0.35, 0):.3f}:d=0.35[v{k}]'
        filters.append(chain)
        labels.append(f'[v{k}]')
    filters.append(''.join(labels) + f'concat=n={len(labels)}:v=1:a=0[vcat]')
    filters.append(f'[vcat]setpts=PTS*{k:.5f}[vout]' if k < 0.999 else '[vcat]null[vout]')
    if seg['voice']:
        inputs += ['-i', str(seg['voice'])]
        delay = int(delay_s * 1000)
        filters.append(f'[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={delay}|{delay},apad,atrim=0:{length:.3f}[aout]')
    else:
        inputs += ['-f', 'lavfi', '-t', f'{length:.3f}', '-i', 'anullsrc=r=48000:cl=stereo']
        filters.append(f'[{n}:a]anull[aout]')
    out = BUILD / f'seg_{idx:02d}.mp4'
    run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(filters), '-map', '[vout]', '-map', '[aout]',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-r', str(FPS), '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{length:.3f}', str(out)])
    return out


def music(total):
    out = BUILD / 'music.wav'
    # low A-minor drone with slow swell; quiet, no third-party material
    expr = ('0.16*sin(2*PI*55*t)+0.10*sin(2*PI*82.41*t)+0.08*sin(2*PI*110*t)+0.05*sin(2*PI*130.81*t)+0.03*sin(2*PI*164.81*t)')
    swell = '(0.75+0.25*sin(2*PI*t/23))'
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'aevalsrc=({expr})*{swell}:s=48000:d={total:.2f}',
         '-af', f'lowpass=f=600,aecho=0.8:0.7:600|1100:0.25|0.2,afade=t=in:d=4,afade=t=out:st={total - 5:.2f}:d=5,pan=stereo|c0=c0|c1=c0',
         str(out)])
    return out


def srt(segments):
    lines, t, k = [], 0.0, 1
    for seg in segments:
        if seg['text']:
            sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', seg['text'].replace('…', '').strip()) if s.strip()]
            total_chars = sum(len(s) for s in sentences)
            cur = t + seg.get('delay', VOICE_DELAY_S)
            for s in sentences:
                d = seg['speech'] * len(s) / total_chars
                lines.append(f'{k}\n{ts(cur)} --> {ts(cur + d)}\n{s}\n')
                cur += d
                k += 1
        t += seg['length']
    (PITCH / 'Talwacht_Pitch.srt').write_text('\n'.join(lines), encoding='utf-8')


def ts(s):
    h, m = int(s // 3600), int(s % 3600 // 60)
    return f'{h:02d}:{m:02d}:{s % 60:06.3f}'.replace('.', ',')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--voice', default='de-AT-JonasNeural')
    ap.add_argument('--rate', default='+8%')
    ap.add_argument('--keep-voice', action='store_true')
    args = ap.parse_args()
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg not found')
    BUILD.mkdir(parents=True, exist_ok=True)
    resolve_marks()
    voice_files(args.voice, args.rate, args.keep_voice)
    parts = [build_segment(seg, i) for i, seg in enumerate(SEGMENTS)]
    total = sum(s['length'] for s in SEGMENTS)
    (BUILD / 'concat.txt').write_text(''.join(f"file '{p.as_posix()}'\n" for p in parts), encoding='utf-8')
    joined = BUILD / 'joined.mp4'
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(BUILD / 'concat.txt'), '-c', 'copy', str(joined)])
    bed = music(total)
    final = PITCH / 'Talwacht_Pitch.mp4'
    run(['ffmpeg', '-y', '-v', 'error', '-i', str(joined), '-i', str(bed), '-filter_complex',
         '[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[vo];[1:a]volume=0.22[mu];[vo][mu]amix=inputs=2:duration=first:normalize=0[a]',
         '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(final)])
    srt(SEGMENTS)
    report = [{'id': s['id'], 'length_s': round(s['length'], 2), 'speech_s': round(s['speech'], 2)} for s in SEGMENTS]
    (BUILD / 'timeline.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(json.dumps(report))
    print('total_s', round(total, 1), final)


if __name__ == '__main__':
    main()
