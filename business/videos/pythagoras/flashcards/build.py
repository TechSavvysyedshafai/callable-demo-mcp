"""Build the Pythagoras flashcards: a PDF (question page, then answer page) and a CSV for Anki/Quizlet.
Usage: python3 -I build.py OUTDIR"""
import csv, html, json, os, subprocess, sys
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
CARDS = [
 ("What is the Pythagorean theorem?", "In a right triangle, a² + b² = c².<br><small>The squares on the two short sides add up to the square on the long side.</small>", "Video 1"),
 ("What is a right triangle?", "A triangle with one square corner (a 90° angle).", "Video 1"),
 ("Which side is c?", "The longest side, opposite the square corner. It is called the hypotenuse.", "Video 1"),
 ("Which sides are a and b?", "The two shorter sides that meet at the square corner. They are called the legs.", "Video 1"),
 ("Check the 3-4-5 triangle.", "3² + 4² = 9 + 16 = 25 = 5².<br><small>The two small squares hold 9 and 16 little squares. The big one holds 25.</small>", "Video 1"),
 ("Check the 5-12-13 triangle.", "5² + 12² = 25 + 144 = 169 = 13².<br><small>It works again.</small>", "Video 1"),
 ("How does the sliding proof work?", "Four identical right triangles sit in a big square and leave a gap shaped like c². Slide the same triangles and the gap becomes a² and b². The gap has the same area both times, so c² = a² + b².", "Video 2"),
 ("Why is the gap the same area both times?", "Because it is the big square minus the same four triangles. The big square and the triangles do not change when you slide them.", "Video 2"),
 ("A 2.5 m ladder has its foot 0.7 m from a wall. How high does it reach?", "0.7² + h² = 2.5²<br>0.49 + h² = 6.25<br>h² = 5.76<br><b>h = 2.4 m</b><br><small>The ladder is the long side (c).</small>", "Video 3"),
 ("How do you find a missing short side?", "Subtract. a² = c² − b². Then take the square root.", "Video 3"),
 ("Common mistake: you get h² = 5.76. Are you done?", "No. Take the square root: h = 2.4. The answer is the side, not its square.", "Video 3"),
 ("How can builders check that a corner is square?", "Mark 3 m along one wall and 4 m along the other. If the marks are 5 m apart, the corner is square.", "Video 3"),
 ("Does the theorem work for every triangle?", "No. Only for right triangles. If a² + b² = c² for the three sides, the triangle is a right triangle.", "Video 3"),
]
CSS = """@page{size:1280px 720px;margin:0}*{box-sizing:border-box;margin:0}
body{font-family:'Noto Sans','DejaVu Sans',Arial,sans-serif;color:#f3f7fa}
.pg{width:1280px;height:720px;page-break-after:always;padding:70px 90px;display:flex;flex-direction:column;justify-content:center;position:relative;background:linear-gradient(170deg,#0f1c2e 0%,#12304a 60%,#0e4a4f 100%)}
.pg.a{background:linear-gradient(170deg,#0e2a2c 0%,#0f4a4f 100%)}
.tag{position:absolute;top:34px;left:90px;font-size:24px;letter-spacing:.12em;text-transform:uppercase;color:#5fd0c4}
.n{position:absolute;top:34px;right:90px;font-size:24px;color:#9fb8c4}
.q{font-size:58px;font-weight:800;line-height:1.2}
.ans{font-size:46px;line-height:1.35;color:#f3f7fa}.ans small{font-size:30px;color:#b9d0da;line-height:1.4}
.src{position:absolute;bottom:34px;left:90px;font-size:22px;color:#9fb8c4}"""
pages = ""
for i, (q, a, v) in enumerate(CARDS, 1):
    pages += f'<div class="pg"><div class="tag">Question</div><div class="n">{i} / {len(CARDS)}</div><div class="q">{html.escape(q)}</div><div class="src">{v}</div></div>'
    pages += f'<div class="pg a"><div class="tag">Answer</div><div class="n">{i} / {len(CARDS)}</div><div class="ans">{a}</div><div class="src">{v}</div></div>'
open(os.path.join(out, "flashcards.html"), "w").write(f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>{pages}')
with open(os.path.join(out, "flashcards.csv"), "w", newline="") as f:
    w = csv.writer(f)
    for q, a, v in CARDS:
        plain = a.replace("<br><small>", " ").replace("<br>", " / ").replace("<small>", "").replace("</small>", "").replace("<b>", "").replace("</b>", "")
        w.writerow([q, plain, v])
js = "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:720}});await p.goto('file://'+process.argv[1]);await p.pdf({path:process.argv[2],width:'1280px',height:'720px',printBackground:true});await p.screenshot({path:process.argv[3]});await b.close();})();"
root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
subprocess.run(["node", "-e", js, os.path.abspath(os.path.join(out, "flashcards.html")), os.path.abspath(os.path.join(out, "flashcards.pdf")), os.path.abspath(os.path.join(out, "preview.png"))], env={**os.environ, "NODE_PATH": root}, check=True)
print(len(CARDS), "cards")
