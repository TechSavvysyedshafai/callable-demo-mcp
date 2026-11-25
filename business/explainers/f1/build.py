# Assembles f1/index.html: the engine page's drawing-sheet CSS + gpu body + three.js + gpu.js (inline, single file).
import pathlib, re
here = pathlib.Path(__file__).parent
eng = (here.parent / 'engine' / 'index.html').read_text()
head = eng[:eng.index('</style>') + len('</style>')]
head = head.replace('<title>How a Car Engine Works</title>', '<title>Race Car Airflow</title>')
head = head.replace('<style>\n/* Layout: an engineering drawing sheet.', '<style>\n/* F1 airflow explainer reuses the engine sheet. Layout: an engineering drawing sheet.')
head += '\n<style>body.short .stroke-name{font-size:22px} .stroke-name{font-size:26px} @media (max-width:640px){.viewnote{display:none}} .mono-note{font-family:var(--mono);font-size:12px;color:var(--ink2);min-height:0} .cbar{position:absolute;left:50%;top:8px;transform:translateX(-50%);display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:10px;color:var(--ink2);background:rgba(251,250,246,.85);padding:2px 6px;pointer-events:none} .cbar i{display:block;width:110px;height:8px;border:1px solid var(--ink);background:linear-gradient(90deg,#1d3f8f,#ffffff,#c8371f)} body.short .cbar{display:none} body.short .mono-note{display:none}</style>\n'
body = (here / 'body.html').read_text()
js = (here / 'f1.js').read_text()
out = head + '\n' + body + '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script>\n' + js + '</script>\n'
(here / 'index.html').write_text(out)
print('wrote', len(out), 'bytes')
