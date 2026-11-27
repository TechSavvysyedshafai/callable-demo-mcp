# Pyasa Kauwa: bilingual picture book (Hindi + English)

11 pages, 24 x 21 cm, print-ready PDF: `pyasa_kauwa_book.pdf` (about 1.2 MB, fine for WhatsApp).

- `story.json`: the text, page by page (edit here to change words or language).
- `scene.py`: Blender scene. The crow, pot, pebbles, tree and sky are built once and posed per page,
  so every character looks the same on every page. Render: `blender -b -P scene.py -- pages all 100` (about 8 min on CPU).
- `build_book.py`: lays out the pages and exports the PDF (needs Noto fonts and Playwright's Chromium).

Story: folk tale (Aesop's "The Crow and the Pitcher", also told across India); public domain.
Next ideas: personalised edition (child's name in the text), Bhojpuri text, read-aloud sound version.
