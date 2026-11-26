# Assembles chem/index.html: the engine page's drawing-sheet CSS + chem body + three.js + chem.js (inline, single file).
import pathlib
here = pathlib.Path(__file__).parent
eng = (here.parent / 'engine' / 'index.html').read_text()
head = eng[:eng.index('</style>') + len('</style>')]
head = head.replace('<title>How a Car Engine Works</title>', '<title>Le Chatelier Equilibrium</title>')
head += '\n<style>.stroke-name{font-size:26px} body.short .stroke-name{font-size:22px} canvas#qk{width:100%;height:96px} body.short canvas#qk{height:70px} @media (max-width:640px){.viewnote{display:none}}</style>\n'
out = head + '\n' + (here / 'body.html').read_text() + '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script>\n' + (here / 'chem.js').read_text() + '</script>\n'
(here / 'index.html').write_text(out)
print('wrote', len(out), 'bytes')
