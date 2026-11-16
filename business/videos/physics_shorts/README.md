# Physics in 50 Seconds (Class 11)

Same pipeline as `../bio_shorts/` (see its README): a deterministic `seek(t)` SVG scene
exports a state JSON, Blender renders the 3D layer, ffmpeg composites the text overlay.
Shared helpers (`lib.js`, `render.js`, `page.html`, `blender/blib.py`, `make.sh`) live in `../bio_shorts/`.

| Topic | Scene | Blender | Video |
|---|---|---|---|
| Projectile motion | `proj.js` | `blender/proj3d.py` | `phys3d_projectile.mp4` |

Physics in `proj.js` is computed from the real equations (u = 10 m/s, g = 9.8 m/s², 50 px per metre),
played at half speed. Render: copy the three files next to the bio_shorts tooling and run `./make.sh proj proj3d.py`.
