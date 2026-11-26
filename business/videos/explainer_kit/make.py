"""Turn a recorded explainer video plus a script.md into a finished video: voiceover, word-synced captions,
music bed (ducked under the voice), sound effects, loudness set to -14 LUFS.

Ideas taken from petergyang/video-explainer (MIT licence): per-line narration, word-synced captions,
synthesized music and keyword-anchored sound effects, a safe caption band, automatic QA afterwards.
The code here is our own.

Usage: python3 make.py path/to/script.md            -> <project>/renders/<slug>.mp4 and <project>/work/*
script.md format: see README.md.
"""
import json, os, re, subprocess, sys, wave
import numpy as np
from audio import SR, music_bed, sfx

WORDS_PER_SEC = 2.5
PRE = 'acompressor=threshold=-20dB:ratio=3:attack=5:release=120,alimiter=limit=0.7:level=false,'   # tame peaks so loudness can reach -14 LUFS          # used for Voice: none (silent timing) and the length check


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def parse(path):
    head, lines, mode = {}, [], None
    for raw in open(path, encoding='utf-8'):
        s = raw.rstrip('\n')
        if s.startswith('## '):
            mode = s[3:].strip().lower(); continue
        if mode is None and ':' in s and not s.startswith('#'):
            k, v = s.split(':', 1); head[k.strip().lower()] = v.strip(); continue
        if mode == 'lines' and s.startswith('- '):
            m = re.match(r'- (?:@([\d.]+)\s+)?(.*)', s)
            at, text = (float(m.group(1)) if m.group(1) else None), m.group(2).strip()
            text, _, tr = text.partition(' | ')   # optional translation shown above the caption
            cues = []  # {sfx} placed before a word -> cue at that word
            words = []
            for tok in text.split():
                c = re.fullmatch(r'\{(\w+)\}', tok)
                if c: cues.append((len(words), c.group(1)))
                else: words.append(tok)
            lines.append({'at': at, 'words': words, 'cues': cues, 'tr': tr.strip()})
    return head, lines


def read_wav(p):
    w = wave.open(p); sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    x = np.frombuffer(w.readframes(n), '<i2').astype(np.float32) / 32768; w.close()
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x).astype(np.float32)
    return x


def write_wav(p, x):
    x = np.clip(x, -1, 1)
    w = wave.open(p, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype('<i2').tobytes()); w.close()


def trim(x, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    return x[max(0, idx[0] - 480): idx[-1] + 2400] if len(idx) else x


def voice_line(i, text, voice, proj, work):
    """Return the audio for one line. espeak:<voice> = free robot draft voice; own:<folder> = your recordings
    (line01.wav, line02.wav ...); none = silence timed at 2.5 words per second."""
    kind, _, arg = voice.partition(':')
    if kind == 'none':
        return np.zeros(int(len(text.split()) / WORDS_PER_SEC * SR), np.float32)
    if kind == 'own':
        p = os.path.join(proj, arg, f'line{i + 1:02d}.wav')
        if os.path.exists(p): return trim(read_wav(p))
        print(f'  (no recording {p}; using the draft voice for this line)')
        kind, arg = 'espeak', 'en-gb'
    if kind == 'espeak':
        out = os.path.join(work, f'line{i + 1:02d}.wav')
        run('espeak-ng', '-v', arg or 'en-gb', '-s', '155', '-w', out, text)
        return trim(read_wav(out))
    raise SystemExit(f'unknown Voice {voice!r}')


def chunks(words, max_chars=34):
    """Split a line into caption chunks of even length (no one-word orphans); prefer breaks after punctuation."""
    total = sum(len(w) + 1 for w in words)
    k = max(1, -(-total // max_chars)); target = total / k
    out, cur, size = [], [], 0
    for i, w in enumerate(words):
        cur.append(w); size += len(w) + 1
        left = len(words) - i - 1
        if len(out) < k - 1 and left >= 2 and (size >= target or (size >= 0.7 * target and w[-1] in ',.:;?!')):
            out.append(cur); cur, size = [], 0
    if cur: out.append(cur)
    return out


def ass_time(t):
    t = max(0, t); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def main(script, plan=False):
    proj = os.path.dirname(os.path.abspath(script))
    head, lines = parse(script)
    video = os.path.normpath(os.path.join(proj, head['video']))
    slug = head.get('slug') or os.path.basename(proj)
    work = os.path.join(proj, 'work'); os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.join(proj, 'renders'), exist_ok=True)
    voice = head.get('voice', 'espeak:en-gb')
    if plan:   # time the voice only (no video yet): animation code then reads work/timeline.json
        W, H = map(int, head.get('size', '1080x1920').split('x')); dur = float(head['max duration']); has_audio = False
    else:
        info = json.loads(run('ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height', '-show_entries', 'format=duration', '-of', 'json', video))
        W = next(s['width'] for s in info['streams'] if s['codec_type'] == 'video'); H = next(s['height'] for s in info['streams'] if s['codec_type'] == 'video')
        dur = float(info['format']['duration']); has_audio = any(s['codec_type'] == 'audio' for s in info['streams'])

    # 1. narration, one audio piece per line; each line starts at its @time or after the previous line
    n = int(dur * SR); narr = np.zeros(n, np.float32); t = 0.3; timeline = []
    for i, ln in enumerate(lines):
        a = voice_line(i, ' '.join(ln['words']), voice, proj, work)
        start = max(ln['at'] if ln['at'] is not None else 0, t)
        if start + len(a) / SR > dur - 0.2:
            print(f'WARNING line {i + 1} runs past the video end; shorten it'); a = a[:max(0, int((dur - 0.2 - start) * SR))]
        s0 = int(start * SR); narr[s0:s0 + len(a)] += a[:n - s0]
        end = start + len(a) / SR; t = end + 0.25
        # word times: spread across the line by word length (an estimate; exact for chunk edges)
        wts = np.array([len(w) + 2 for w in ln['words']], float); edges = start + np.concatenate([[0], np.cumsum(wts)]) / wts.sum() * (end - start)
        timeline.append({'line': i + 1, 'tr': ln['tr'], 'start': round(start, 3), 'end': round(end, 3), 'words': [{'w': w, 's': round(edges[k], 3), 'e': round(edges[k + 1], 3)} for k, w in enumerate(ln['words'])], 'cues': [{'sfx': c, 'at': round(edges[min(k, len(ln['words']) - 1)], 3)} for k, c in ln['cues']]})
    words_total = sum(len(l['words']) for l in lines)
    write_wav(os.path.join(work, 'narration.wav'), narr)
    if plan:
        json.dump({'width': W, 'height': H, 'duration': dur, 'lines': timeline}, open(os.path.join(work, 'timeline.json'), 'w'), indent=1)
        print(f'planned {len(timeline)} lines; voice ends at {timeline[-1]["end"]:.1f}s of {dur:.0f}s -> {work}/timeline.json'); return

    # 2. music bed ducked under the voice, sound effects, original video sound
    mus = music_bed(dur, head.get('music', 'synth:warm').split(':')[-1])[:n]
    env = np.convolve(np.abs(narr), np.ones(4800) / 4800, mode='same'); duck = 1 - 0.7 * np.clip(env / 0.02, 0, 1)
    duck = np.convolve(duck, np.ones(9600) / 9600, mode='same')
    fx = np.zeros(n, np.float32)
    for ln in timeline:
        for c in ln['cues']:
            s = sfx(c['sfx']); a = int(c['at'] * SR); fx[a:a + len(s)] += s[:n - a]
    orig = np.zeros(n, np.float32)
    if has_audio:
        run('ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-ac', '1', '-ar', str(SR), os.path.join(work, 'orig.wav'))
        o = read_wav(os.path.join(work, 'orig.wav'))[:n]; orig[:len(o)] = o
    bed_gain = float(head.get('video sound', '0.35'))
    mix = narr * 1.0 + mus * duck * 0.8 + fx * 0.6 + orig * bed_gain * (1 - 0.5 * (1 - duck))
    mix /= max(1e-6, np.max(np.abs(mix))) / 0.9
    write_wav(os.path.join(work, 'mix_raw.wav'), mix)
    # two-pass loudness to -14 LUFS (YouTube / Shorts level), peaks at most -1.5 dBTP
    meas = \
        subprocess.run(['ffmpeg', '-hide_banner', '-i', os.path.join(work, 'mix_raw.wav'), '-af', PRE + 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
    ln_f = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    run('ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(work, 'mix_raw.wav'), '-af', PRE + ln_f, '-ar', str(SR), os.path.join(work, 'mix.wav'))

    # 3. captions (.ass), karaoke highlight per word, inside the safe band above the bottom edge
    caps = head.get('captions', 'on') != 'off'
    font = head.get('font', 'DejaVu Sans')
    fs = int(H * (0.05 if W > H else 0.034)); margin = int(H * (0.07 if W > H else 0.25))
    top = head.get('caption position', 'bottom') == 'top'   # top = over a static title band
    if top: margin = int(H * 0.075)
    align = 8 if top else 2
    ass = ['[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {W}', f'PlayResY: {H}', 'WrapStyle: 0', '',
           '[V4+ Styles]', 'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           f'Style: Cap,{font},{fs},&H0000D7FF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{max(3, fs // 12)},2,{align},{W // 10},{W // 10},{margin},1',
           f'Style: Tr,DejaVu Sans,{int(fs * 0.62)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,1,0,0,100,100,0,0,1,{max(2, fs // 16)},1,{align},{W // 10},{W // 10},{margin + int(fs * 2.9)},1', '',
           '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    capjson = []
    for ln in timeline:
        if ln['tr']: ass.append(f"Dialogue: 0,{ass_time(ln['start'])},{ass_time(ln['end'])},Tr,,0,0,0,,{ln['tr']}")
        k = 0
        for ch in chunks([w['w'] for w in ln['words']]):
            ws = ln['words'][k:k + len(ch)]; k += len(ch)
            s, e = ws[0]['s'], ws[-1]['e']
            txt = ''.join('{\\kf%d}%s ' % (round((w['e'] - w['s']) * 100), w['w']) for w in ws).strip()
            ass.append(f'Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{txt}')
            capjson.append({'start': s, 'end': e, 'text': ' '.join(ch)})
    open(os.path.join(work, 'captions.ass'), 'w').write('\n'.join(ass) + '\n')
    json.dump({'video': video, 'width': W, 'height': H, 'duration': dur, 'words': words_total, 'voice': voice, 'captions_on': caps, 'font_px': fs, 'margin_px': margin, 'cap_pos': 'top' if top else 'bottom',
               'max_duration': float(head.get('max duration', dur)), 'lines': timeline, 'captions': capjson}, open(os.path.join(work, 'timeline.json'), 'w'), indent=1)

    out = os.path.join(proj, 'renders', f'{slug}.mp4')
    vf = ['-vf', 'ass=captions.ass'] if caps else []
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-i', 'mix.wav', *vf, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], check=True, cwd=work)
    print(f'wrote {out}  ({dur:.1f}s, {words_total} spoken words, {len(capjson)} captions, voice {voice})')
    return out


if __name__ == '__main__':
    main(sys.argv[1], plan='--plan' in sys.argv)
