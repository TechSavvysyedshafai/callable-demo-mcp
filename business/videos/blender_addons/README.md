# Blender add-on test reel (5 min 10 s)
Original scenes, all built in code (Blender 5.0.1, Cycles CPU). Run: `STEP=3 python reel.py -- SEG OUTDIR F0 F1 PCT SAMPLES` (SEG: gn, mol, phys [ACT=0..2], toon, sound), then `assemble.sh`.
1. Geometry Nodes mandala (the Grasshopper equivalent), 2. real protein 1A8O from a PDB file, built as Geometry Nodes, 3. rigid-body physics (3 acts), 4. Freestyle toon outlines, 5. sound-driven animation (my own FFT analysis of a synthesised track).
Not done: Molecular Nodes (needs Python 3.13 / Blender 5.2; extension store blocked here), Grease Pencil, Sverchok, Animation Nodes.
Protein file 1A8O from the Protein Data Bank (via a Biopython test-data copy).
