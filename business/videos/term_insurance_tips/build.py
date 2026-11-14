"""Build the vertical video from slide text. Usage: python3 -I build.py OUTDIR [audio.mp3]
Slides are rendered with Playwright, then joined with ffmpeg. With audio, scene lengths are scaled to the audio."""
import html, os, subprocess, sys, json
out = sys.argv[1]; audio = sys.argv[2] if len(sys.argv) > 2 else None
os.makedirs(out, exist_ok=True)
SCENES = [
  ("", "Buying term insurance?", "Check 3 things first", 5.5),
  ("1", "Cover", "A common rule of thumb: 10 to 15 times your yearly income, minus loans.<br><small>A starting point, not a rule.</small>", 8.5),
  ("2", "Tell the truth on the form", "Smoking, health, other policies.<br><small>A wrong answer can get a claim rejected later.</small>", 8.0),
  ("3", "Check the claim record", "Insurers publish their claim settlement ratio.<br><small>Compare a few years, not one number.</small>", 8.5),
  ("", "General information, not advice", "Ask a licensed adviser before you buy.<br><small>Voice: AI-generated. Script: my own.</small>", 6.0),
]
CSS = """*{box-sizing:border-box;margin:0}body{width:1080px;height:1920px;background:linear-gradient(170deg,#0f1c2e 0%,#12304a 60%,#0e4a4f 100%);font-family:'Noto Sans','DejaVu Sans',Arial,sans-serif;color:#f3f7fa;display:flex;flex-direction:column;justify-content:center;padding:120px 90px}
.n{font-size:200px;font-weight:800;color:#5fd0c4;line-height:1;margin-bottom:30px}h1{font-size:96px;line-height:1.15;font-weight:800;margin-bottom:50px}
p{font-size:56px;line-height:1.35;color:#d4e3ea}small{font-size:44px;color:#9fb8c4}.bar{position:absolute;bottom:90px;left:90px;right:90px;height:10px;background:#1f3b52;border-radius:5px}.bar i{display:block;height:100%;background:#5fd0c4;border-radius:5px}"""
js = "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});const files=JSON.parse(process.argv[1]);for(const f of files){await p.goto('file://'+f);await p.screenshot({path:f.replace('.html','.png')});}await b.close();})();"
files = []
for i, (num, title, body, _) in enumerate(SCENES):
    pct = int((i + 1) / len(SCENES) * 100)
    n = f'<div class="n">{num}</div>' if num else ""
    doc = f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>{n}<h1>{html.escape(title)}</h1><p>{body}</p><div class="bar"><i style="width:{pct}%"></i></div>'
    path = os.path.abspath(os.path.join(out, f"s{i+1}.html")); open(path, "w").write(doc); files.append(path)
root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
subprocess.run(["node", "-e", js, json.dumps(files)], env={**os.environ, "NODE_PATH": root}, check=True)
durs = [s[3] for s in SCENES]
if audio:
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio], capture_output=True, text=True).stdout)
    k = (total + 0.6) / sum(durs); durs = [d * k for d in durs]
lst = os.path.join(out, "list.txt")
with open(lst, "w") as f:
    for p, d in zip(files, durs): f.write(f"file '{p.replace('.html','.png')}'\nduration {d:.3f}\n")
    f.write(f"file '{files[-1].replace('.html','.png')}'\n")
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
if audio: cmd += ["-i", audio]
cmd += ["-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
if audio: cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
target = os.path.join(out, "video.mp4"); cmd += [target]
subprocess.run(cmd, check=True); print(target, round(sum(durs), 1), "seconds")
