# Assembles gpu/index.html: the engine page's drawing-sheet CSS + gpu body + three.js + gpu.js (inline, single file).
import pathlib, re
here = pathlib.Path(__file__).parent
eng = (here.parent / 'engine' / 'index.html').read_text()
head = eng[:eng.index('</style>') + len('</style>')]
head = head.replace('<title>How a Car Engine Works</title>', '<title>How a GPU Works</title>')
head = head.replace('<style>\n/* Layout: an engineering drawing sheet.', '<style>\n/* GPU explainer reuses the engine sheet. Layout: an engineering drawing sheet.')
head += '\n<style>body.short .stroke-name{font-size:22px} .stroke-name{font-size:26px} @media (max-width:640px){.viewnote{display:none}}</style>\n'
body = (here / 'body.html').read_text()
js = (here / 'gpu.js').read_text()
out = head + '\n' + body + '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script>\n' + js + '</script>\n'
(here / 'index.html').write_text(out)
print('wrote', len(out), 'bytes')
