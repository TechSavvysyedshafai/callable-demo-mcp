"""Ten automatic checks on a finished explainer. All must pass (10/10) before it goes out.
Also writes work/qa/contact.jpg (one frame every few seconds) for a human or a fresh agent to judge.
Usage: python3 qa.py path/to/project     (the folder holding script.md, work/ and renders/)
"""
import glob, json, os, re, subprocess, sys, wave
import numpy as np


def sh(*c):
    r = subprocess.run(c, capture_output=True, text=True); return r.stdout + r.stderr


def main(proj):
    tl = json.load(open(os.path.join(proj, 'work', 'timeline.json')))
    vid = sorted(glob.glob(os.path.join(proj, 'renders', '*.mp4')), key=os.path.getmtime)[-1]
    p = json.loads(sh('ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,pix_fmt,width,height,avg_frame_rate', '-show_entries', 'format=duration', '-of', 'json', vid))
    v = next(s for s in p['streams'] if s['codec_type'] == 'video'); a = [s for s in p['streams'] if s['codec_type'] == 'audio']
    dur = float(p['format']['duration']); fps = eval(v['avg_frame_rate']); caps = tl['captions']
    res = []
    def check(name, ok, detail): res.append((name, bool(ok), detail))

    check('1 format', v['codec_name'] == 'h264' and v['pix_fmt'] == 'yuv420p', f"{v['codec_name']} {v['pix_fmt']}")
    W, H = v['width'], v['height']
    check('2 size', (W, H) in [(1920, 1080), (1080, 1920), (1080, 1080)], f'{W}x{H}')
    check('3 frame rate', round(fps) in (24, 25, 30, 60), f'{fps:.2f} fps')
    check('4 length', 10 <= dur <= min(120, tl['max_duration'] + 0.5), f'{dur:.1f}s (cap {min(120, tl["max_duration"]):.0f}s)')
    check('5 audio track', len(a) == 1 and a[0]['codec_name'] == 'aac', f'{len(a)} audio stream(s)')
    eb = sh('ffmpeg', '-hide_banner', '-nostats', '-i', vid, '-af', 'ebur128=peak=true', '-f', 'null', '-')
    I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', eb)[-1]); tp = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', eb)[-1])
    check('6 loudness', -15.5 <= I <= -12.5 and tp <= -1.0, f'{I:.1f} LUFS, true peak {tp:.1f} dBTP (want -14 +-1.5, peak <= -1)')
    bd = sh('ffmpeg', '-hide_banner', '-i', vid, '-vf', 'blackdetect=d=0.5:pix_th=0.08', '-an', '-f', 'null', '-')
    check('7 no black gaps', 'black_start' not in bd, f"{bd.count('black_start')} black stretch(es) >= 0.5s")
    fd = sh('ffmpeg', '-hide_banner', '-i', vid, '-vf', 'freezedetect=n=0.002:d=3', '-an', '-f', 'null', '-')
    nfz = fd.count('freeze_start')
    check('8 no frozen picture', nfz == 0, f'{nfz} still stretch(es) >= 3s (a still picture reads as a slide)')
    bad = [c for c in caps if c['end'] > dur or c['end'] - c['start'] < 0.6 or len(c['text']) / max(0.1, c['end'] - c['start']) > 22]
    over = [i for i in range(1, len(caps)) if caps[i]['start'] < caps[i - 1]['end'] - 0.01]
    band = H - tl['margin_px'] - tl['font_px'] * 1.3
    safe = band > H * (0.78 if W > H else 0.55) or W <= H and band < 1400
    check('9 captions readable', not bad and not over and safe, f'{len(caps)} captions, {len(bad)} too fast/short, {len(over)} overlaps, caption top y={band:.0f}px')
    # 10. sync: the voice energy should sit inside the caption windows
    w = wave.open(os.path.join(proj, 'work', 'narration.wav')); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float); sr = w.getframerate()
    inside = np.zeros(len(x), bool)
    for c in caps: inside[int(c['start'] * sr):int(c['end'] * sr)] = True
    e = x ** 2; share = e[inside].sum() / max(1, e.sum())
    check('10 captions match voice', share >= 0.95 or tl['voice'] == 'none', f'{share:.1%} of voice energy falls inside caption windows')

    qa = os.path.join(proj, 'work', 'qa'); os.makedirs(qa, exist_ok=True)
    step = max(1, dur / 12)
    sh('ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-vf', f'fps=1/{step:.2f},scale=480:-1,tile=4x3', '-frames:v', '1', os.path.join(qa, 'contact.jpg'))
    sh('ffmpeg', '-y', '-loglevel', 'error', '-i', vid, '-t', '15', '-vf', 'fps=1/2.5,scale=480:-1,tile=3x2', '-frames:v', '1', os.path.join(qa, 'opening.jpg'))
    passed = sum(r[1] for r in res)
    for name, ok, d in res: print(f"{'PASS' if ok else 'FAIL'}  {name:24s} {d}")
    print(f'{passed}/10 passed  ->  {vid}\ncontact sheets: {qa}/contact.jpg, {qa}/opening.jpg')
    json.dump([{'check': n, 'pass': o, 'detail': d} for n, o, d in res], open(os.path.join(qa, 'report.json'), 'w'), indent=1)
    return passed


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) == 10 else 1)
