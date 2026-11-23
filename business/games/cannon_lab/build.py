# Inline levels.js into page.html -> index.html (the published single file).
import pathlib
d=pathlib.Path(__file__).parent
lv=(d/'levels.js').read_text().replace("if (typeof module !== 'undefined') module.exports = { PLANETS, LEVELS, stepShot, newShot };\n","")
(d/'index.html').write_text((d/'page.html').read_text().replace('/*LEVELS_JS*/',lv))
