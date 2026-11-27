"""Lay out the picture book: story.json + pages/*.png -> book.html -> book.pdf (24 x 21 cm pages)."""
import json, html, pathlib, subprocess
here = pathlib.Path(__file__).parent
d = json.loads((here / 'story.json').read_text())
E = html.escape
css = """
@page { size: 240mm 210mm; margin: 0 }
* { box-sizing: border-box }
body { margin: 0; background: #fff8ec; color: #2a1d14; font-family: 'Noto Sans Devanagari', sans-serif }
.page { width: 240mm; height: 210mm; position: relative; overflow: hidden; page-break-after: always; background: #fff8ec }
.art { width: 240mm; height: 150mm; display: block; object-fit: cover; border-bottom: 1.2mm solid #2a1d14 }
.text { height: 60mm; padding: 7mm 14mm 0; display: flex; flex-direction: column; gap: 3mm }
.hi { font-size: 25pt; font-weight: 700; line-height: 1.35 }
.en { font-family: 'Noto Serif', 'DejaVu Serif', serif; font-style: italic; font-size: 15.5pt; color: #5b4636 }
.num { position: absolute; right: 9mm; bottom: 6mm; font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; color: #a08a74 }
.cover .art { height: 210mm; border: 0 }
.titlebox { position: absolute; right: 8mm; top: 8mm; text-align: right; background: rgba(255,248,236,0.93); border: 1.2mm solid #2a1d14; border-radius: 6mm; padding: 6mm 9mm 5mm }
.titlebox .sub { font-size: 15pt; color: #8a3a1e; font-weight: 700 }
.titlebox .t { font-size: 36pt; font-weight: 700; line-height: 1.1 }
.titlebox .ten { font-family: 'Noto Serif', 'DejaVu Serif', serif; font-style: italic; font-size: 20pt; color: #5b4636 }
.back { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 6mm; padding: 20mm }
.back .t { font-size: 30pt; font-weight: 700 }
.back p { font-family: 'Noto Serif', 'DejaVu Serif', serif; font-size: 12pt; color: #5b4636; max-width: 150mm; margin: 0 }
"""
parts = [f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>']
for i, p in enumerate(d['pages']):
    img = f'pages_jpg/{p["shot"]}.jpg'
    if p['shot'] == 'cover':
        parts.append(f'<section class="page cover"><img class="art" src="{img}"><div class="titlebox"><div class="sub">{E(d["subtitle_hi"])} · {E(d["subtitle_en"])}</div><div class="t">{E(d["title_hi"])}</div><div class="ten">{E(d["title_en"])}</div></div></section>')
    else:
        parts.append(f'<section class="page"><img class="art" src="{img}"><div class="text"><div class="hi">{E(p["hi"])}</div><div class="en">{E(p["en"])}</div></div><div class="num">{i}</div></section>')
parts.append(f'<section class="page back"><div class="t">{E(d["subtitle_hi"])}</div><p>{E(d["credit"])}</p><p>Illustrations: 3D models built and rendered in Blender, so every character looks the same on every page.</p></section>')
parts.append('</body></html>')
(here / 'book.html').write_text('\n'.join(parts))
js = """const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();
await p.goto('file://'+process.argv[2]);await p.evaluate(()=>document.fonts.ready);
await p.pdf({path:process.argv[3],width:'240mm',height:'210mm',printBackground:true});await b.close();})();"""
(here / 'pdf.js').write_text(js)
subprocess.run(['node', str(here / 'pdf.js'), str(here / 'book.html'), str(here / 'pyasa_kauwa_book.pdf')], check=True)
print('wrote', here / 'pyasa_kauwa_book.pdf')
