# Paper in 2 minutes (3Blue1Brown-style, Manim)
Vertical 1080x1920, captions carry the narration (no voice yet).
- `attention.py` -> AttentionPaper.mp4 (122 s): Vaswani et al. 2017, arXiv 1706.03762. Numbers (28.4 / 41.8 BLEU, 3.5 days on 8 GPUs) checked against the arXiv abstract on 23 Nov 2026. The attention weights shown are example numbers and are labelled so.
- `crispr.py` -> CrisprPaper.mp4 (110 s): Jinek et al., Science 337:816 (2012), doi:10.1126/science.1225829. crRNA/tracrRNA, HNH and RuvC roles and the single-RNA chimera checked against the PubMed abstract. PAM = NGG and "cut 3 letters before the PAM" are standard facts for S. pyogenes Cas9, from my own knowledge, not re-checked here. Nobel 2020 and Casgevy approval in 2023 are also from my own knowledge.
Render: `pip install manim` (needs libpango1.0-dev, libcairo2-dev; texlive-latex-base/-extra for the equation), then `manim -qh attention.py AttentionPaper`.
