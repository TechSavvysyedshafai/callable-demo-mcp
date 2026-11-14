"""Build the flashcards as a PowerPoint deck. Usage: python3 -I build_pptx.py OUT.pptx IMAGEDIR
Cards come from build.py (the CARDS list); a few answer slides carry a frame from the videos."""
import os, re, sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
out, imgdir = sys.argv[1], sys.argv[2]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.py")).read()
ns = {}; exec(src[src.index("CARDS = ["):src.index("CSS =")], ns); CARDS = ns["CARDS"]
BG, TEAL, WHITE, MUTED, ABG = RGBColor(0x0f,0x2a,0x3e), RGBColor(0x5f,0xd0,0xc4), RGBColor(0xf3,0xf7,0xfa), RGBColor(0x9f,0xb8,0xc4), RGBColor(0x0f,0x3f,0x45)
# which answer slide shows which video frame (card number -> file)
PICS = {5: "a17.png", 7: "b17.png", 9: "c11.png"}
QPICS = {7: "b6.png"}
prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
blank = prs.slide_layouts[6]
def base(color):
    s = prs.slides.add_slide(blank); f = s.background.fill; f.solid(); f.fore_color.rgb = color; return s
def box(s, x, y, w, h):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True; return tf
def run(p, text, size, color, bold=False):
    r = p.add_run(); r.text = text; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color; r.font.name = "Calibri"; return r
def tag(s, label, i, pic=False):
    p = box(s, 0.8, 0.4, 5, 0.5).paragraphs[0]; run(p, label.upper(), 14, TEAL, True)
    p = box(s, 6.8 if pic else 10.5, 0.4, 2, 0.5).paragraphs[0]; p.alignment = PP_ALIGN.RIGHT; run(p, f"{i} / {len(CARDS)}", 14, MUTED)
def foot(s, text):
    p = box(s, 0.8, 6.8, 8, 0.4).paragraphs[0]; run(p, text, 12, MUTED)
# title
s = base(BG); tf = box(s, 0.8, 2.3, 11.5, 3)
run(tf.paragraphs[0], "The Pythagorean theorem", 54, WHITE, True)
p = tf.add_paragraph(); run(p, "13 flashcards: question, then answer", 28, TEAL)
p = tf.add_paragraph(); run(p, "From three short videos: squares on the sides, the sliding proof, and real life", 20, MUTED)
s.notes_slide.notes_text_frame.text = "Press next for the question, then next again for its answer."
for i, (q, a, v) in enumerate(CARDS, 1):
    s = base(BG); tag(s, "Question", i, i in QPICS)
    w = 7.2 if i in QPICS else 11.5
    tf = box(s, 0.8, 2.2, w, 3.2); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    run(tf.paragraphs[0], q, 40, WHITE, True)
    if i in QPICS: s.shapes.add_picture(os.path.join(imgdir, QPICS[i]), Inches(9.2), Inches(0.6), height=Inches(6.2))
    foot(s, v)
    s = base(ABG); tag(s, "Answer", i, i in PICS)
    w = 7.2 if i in PICS else 11.5
    tf = box(s, 0.8, 1.8, w, 4.4); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    parts = [x for x in re.split(r"<br>", a)]
    first = True
    for part in parts:
        small = "<small>" in part; bold = "<b>" in part
        text = re.sub(r"</?(small|b)>", "", part).strip()
        if not text: continue
        p = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
        run(p, text, 22 if small else 32, MUTED if small else WHITE, bold)
        p.space_after = Pt(8)
    if i in PICS: s.shapes.add_picture(os.path.join(imgdir, PICS[i]), Inches(9.2), Inches(0.6), height=Inches(6.2))
    foot(s, v)
s = base(BG); tf = box(s, 0.8, 2.4, 11.5, 3)
run(tf.paragraphs[0], "a² + b² = c²", 60, TEAL, True)
p = tf.add_paragraph(); run(p, "Only for right triangles. c is the long side opposite the square corner.", 24, WHITE)
p = tf.add_paragraph(); run(p, "Find a missing side: subtract, then take the square root.", 24, MUTED)
prs.save(out); print("slides", len(prs.slides))
