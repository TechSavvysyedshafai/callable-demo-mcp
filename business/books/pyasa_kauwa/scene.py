# Pyasa Kauwa picture book: one Blender scene, one camera set-up per page.
# Characters and props are built once and posed per page, so they look the same on every page.
# Usage: blender -b -P scene.py -- <out_dir> <shot|all> <resolution_percentage>
import bpy, math, sys, os, random
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, WHICH, PCT = argv[0], argv[1], int(argv[2])
os.makedirs(OUT, exist_ok=True)
rad = math.radians
rng = random.Random(4)

def hexc(h, a=1.0):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4)) + (a,)

def lin(c):  # sRGB -> linear for material colours
    return tuple(((x/12.92) if x <= 0.04045 else ((x+0.055)/1.055)**2.4) if i < 3 else x for i, x in enumerate(c))

MATS = {}
def mat(name, h, rough=0.75, emit=0.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexc(h)); b.inputs['Roughness'].default_value = rough
    for key in ('Specular IOR Level', 'Specular'):
        if key in b.inputs: b.inputs[key].default_value = 0.15
    if emit:
        b.inputs['Emission Color'].default_value = lin(hexc(h)); b.inputs['Emission Strength'].default_value = emit
    MATS[name] = m; return m

def add(obj, m, smooth=True, parent=None):
    obj.data.materials.append(m)
    if smooth and hasattr(obj.data, 'polygons'):
        for p in obj.data.polygons: p.use_smooth = True
    if parent: obj.parent = parent
    return obj

def sphere(loc, scale, m, seg=40, parent=None, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg//2, location=loc); o = bpy.context.object
    o.scale = scale; return add(o, m, smooth, parent)

def ico(loc, r, m, sub=2, parent=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc); o = bpy.context.object
    return add(o, m, False, parent)

def cyl(loc, r, depth, m, rot=(0, 0, 0), verts=40, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot); o = bpy.context.object
    return add(o, m, True, parent)

def cone(loc, r1, r2, depth, m, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot); o = bpy.context.object
    return add(o, m, True, parent)

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o); o.location = loc
    if parent: o.parent = parent
    return o

def cut_front(objs):
    """Cut-away: remove the half of each object that faces the camera (y < 0)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -1.5, 1.2)); c = bpy.context.object; c.scale = (4, 3, 4); c.hide_render = True; c.hide_viewport = True
    for o in objs:
        mod = o.modifiers.new('cut', 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.object = c; mod.solver = 'EXACT'

# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 40
try:
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    sc.cycles.use_denoising = False
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600, 1000, PCT
sc.view_settings.view_transform = 'Standard'
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'
vl = sc.view_layers[0]; vl.use_freestyle = True; fs = vl.freestyle_settings
lset = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('ink')
if lset.linestyle is None: lset.linestyle = bpy.data.linestyles.new('ink')
lset.select_by_visibility = True; lset.select_by_edge_types = True
lset.select_silhouette = True; lset.select_border = True; lset.select_crease = True
ls = lset.linestyle
ls.color = lin(hexc('#2a1d14'))[:3]; ls.thickness = 2.6 * PCT / 100 * 1.6

# ---------- world sky (gradient by screen height) ----------
w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes['Background']; bg.inputs['Strength'].default_value = 1.0
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
nt.links.new(tc.outputs['Window'], sep.inputs[0]); nt.links.new(sep.outputs['Y'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
def sky(top, horizon):
    ramp.color_ramp.elements[0].position = 0.25; ramp.color_ramp.elements[0].color = lin(hexc(horizon))
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = lin(hexc(top))

# ---------- light ----------
bpy.ops.object.light_add(type='SUN', rotation=(rad(50), rad(-10), rad(-35))); sunl = bpy.context.object
sunl.data.energy = 3.2; sunl.data.angle = rad(8); sunl.data.color = (1.0, 0.95, 0.85)

# ---------- land ----------
SAND, HILL = mat('sand', '#d79a5a'), mat('hill', '#c98448')
bpy.ops.mesh.primitive_plane_add(size=120); ground = add(bpy.context.object, SAND, False)
for x, y, sx, sz in [(-14, 22, 12, 3.2), (6, 26, 14, 4.0), (24, 20, 10, 2.6), (-30, 28, 12, 3.0)]:
    sphere((x, y, -0.4), (sx, 4, sz), HILL)
CRACK = mat('crack', '#9c6332')
for i in range(14):
    x, y = rng.uniform(-7, 7), rng.uniform(-3.5, 6)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0.004), rotation=(0, 0, rng.uniform(0, 3.14))); c = bpy.context.object
    c.scale = (rng.uniform(0.4, 1.1), 0.025, 0.005); add(c, CRACK, False)
# dry pond for the search page
bpy.ops.mesh.primitive_circle_add(vertices=48, radius=1.6, fill_type='NGON', location=(3.5, 5, 0.006)); pond = add(bpy.context.object, mat('pond', '#a87445'), False); pond.scale = (1.6, 1, 1)

# ---------- tree ----------
TRUNK, LEAF, LEAF2 = mat('trunk', '#7a4f2b'), mat('leaf', '#5d8f3a'), mat('leaf2', '#3f6b25')
tree = empty('tree', (-3.4, 2.4, 0))
cyl((0, 0, 1.4), 0.24, 2.8, TRUNK, parent=tree)
for (x, y, z, r, m) in [(-0.6, 0, 3.0, 1.15, LEAF), (0.7, 0.2, 3.2, 1.0, LEAF2), (0, -0.2, 3.9, 1.05, LEAF), (0.1, 0.5, 3.4, 0.9, LEAF2)]:
    ico((x, y, z), r, m, parent=tree)

# ---------- sun ----------
SUN = mat('sunm', '#ffcf3f', emit=4.0)
sun = empty('sun', (6, 40, 15))
sphere((0, 0, 0), (2.4, 2.4, 2.4), SUN, parent=sun)
for i in range(12):
    a = i * math.tau / 12
    bpy.ops.mesh.primitive_cube_add(size=1, location=(3.6*math.cos(a), 0, 3.6*math.sin(a)), rotation=(0, -a, 0)); r = bpy.context.object
    r.scale = (1.1, 0.2, 0.28); add(r, SUN, False, parent=sun)

# ---------- pot (ghada) ----------
CLAY, CLAYD, BAND, INNER, WATER, PEB = mat('clay', '#b5532e'), mat('clayd', '#8a3a1e'), mat('band', '#f2c14e'), mat('inner', '#4a2212'), mat('water', '#4aa3d8', 0.15), mat('peb', '#9a9a8c')
pot = empty('pot')
body = sphere((0, 0, 0.8), (0.82, 0.82, 0.78), CLAY, parent=pot)
inner = sphere((0, 0, 0.8), (0.75, 0.75, 0.71), INNER, parent=pot)
neck = cyl((0, 0, 1.66), 0.36, 0.42, CLAY, parent=pot)
bpy.ops.mesh.primitive_torus_add(major_radius=0.40, minor_radius=0.075, location=(0, 0, 1.88)); rim = add(bpy.context.object, CLAYD, True, parent=pot)
bpy.ops.mesh.primitive_torus_add(major_radius=0.80, minor_radius=0.03, location=(0, 0, 0.95)); band = add(bpy.context.object, BAND, True, parent=pot)
import bmesh
def halve(o):
    """Copy of o with the camera-side half removed: an open shell, so the inside shows (no filled cap)."""
    c = o.copy(); c.data = o.data.copy(); bpy.context.collection.objects.link(c); c.parent = o.parent
    bm = bmesh.new(); bm.from_mesh(c.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y < 0], context='FACES')
    bm.to_mesh(c.data); bm.free()
    for p in c.data.polygons: p.use_smooth = True
    return c
FULL = [body, neck, rim, band]
CUT = [halve(o) for o in (body, inner, neck, rim, band)]
inner.hide_render = True
# water: the pot's inside shape, kept only below the water line and behind the cut (its flat face is the visible section)
WATER = mat('water', '#4aa3d8', 0.15)
wb = WATER.node_tree.nodes['Principled BSDF']; wb.inputs['Alpha'].default_value = 0.5
water = sphere((0, 0, 0.8), (0.735, 0.735, 0.695), WATER, parent=pot)
bpy.ops.mesh.primitive_cube_add(size=1); wbox = bpy.context.object; wbox.hide_render = True; wbox.hide_viewport = True
wm = water.modifiers.new('keep', 'BOOLEAN'); wm.operation = 'INTERSECT'; wm.object = wbox; wm.solver = 'EXACT'
neckw = cyl((0, 0, 1.68), 0.31, 0.5, WATER, parent=pot)   # water rising into the neck
nm = neckw.modifiers.new('keep', 'BOOLEAN'); nm.operation = 'INTERSECT'; nm.object = wbox; nm.solver = 'EXACT'
inside_pebbles = [sphere(((-0.36 + 0.24*(i % 4)) + rng.uniform(-0.04, 0.04), rng.uniform(0.03, 0.1), 0.2 + 0.2*(i // 4)), (0.13, 0.12, 0.11), mat('pebin', '#c9c7b8'), seg=20, parent=pot) for i in range(10)]
pile = [sphere((1.35 + 0.28*(i % 3) + rng.uniform(-0.05, 0.05), -0.8 + 0.25*(i // 3), 0.1), (0.13, 0.12, 0.1), PEB, seg=20) for i in range(9)]
for p in inside_pebbles + pile: p.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
def set_cut(on, potvis=True):
    for o in FULL: o.hide_render = not potvis or on
    for o in CUT: o.hide_render = not potvis or not on
    water.hide_render = not (potvis and on); neckw.hide_render = water.hide_render
def set_water(top):
    wbox.location = (0, 0.6, (0.06 + top) / 2); wbox.scale = (2, 1.2, max(0.02, top - 0.06))

# ---------- crow ----------
BLK, WINGM, BEAK, WHITE = mat('crow', '#22222e', 0.6), mat('wing', '#33334a', 0.6), mat('beak', '#e8a33c', 0.5), mat('white', '#ffffff', 0.4)
crow = empty('crow')
sphere((0, 0, 0), (0.46, 0.28, 0.3), BLK, parent=crow)
headp = empty('head', (0.36, 0, 0.2), crow)
sphere((0.08, 0, 0.06), (0.21, 0.2, 0.2), BLK, parent=headp)
cone((0.36, 0, 0.03), 0.075, 0.0, 0.28, BEAK, rot=(0, rad(90), 0), parent=headp)
for s in (1, -1):
    sphere((0.17, 0.14*s, 0.12), (0.06, 0.03, 0.06), WHITE, seg=16, parent=headp)
    sphere((0.2, 0.165*s, 0.12), (0.03, 0.015, 0.03), BLK, seg=12, parent=headp)
beak_pebble = sphere((0.5, 0, 0.0), (0.09, 0.08, 0.07), PEB, seg=16, parent=headp)
wings = []
for s in (1, -1):
    pv = empty('wing', (0.02, 0.2*s, 0.12), crow)
    wm = sphere((-0.08, 0.14*s, 0), (0.4, 0.17, 0.05), WINGM, parent=pv); wings.append((pv, s))
cone((-0.55, 0, 0.06), 0.16, 0.02, 0.4, BLK, rot=(0, rad(-80), 0), parent=crow).scale = (1, 0.45, 1)
legs = []
for s in (1, -1):
    l = cyl((0.03, 0.09*s, -0.36), 0.022, 0.26, BEAK, parent=crow); legs.append(l)
    f = sphere((0.08, 0.09*s, -0.49), (0.09, 0.03, 0.02), BEAK, seg=12, parent=crow); legs.append(f)
# a thought light bulb for the idea page
bulb = empty('bulb')
sphere((0, 0, 0), (0.2, 0.2, 0.2), mat('bulbm', '#ffe25a', emit=2.5), parent=bulb)
cyl((0, 0, -0.24), 0.09, 0.12, mat('bulbbase', '#9a9a9a'), parent=bulb)

def pose_crow(loc, yaw=0, wing=0, head=0, standing=True, pebble=False, scale=1.0):
    crow.location = loc; crow.rotation_euler = (0, 0, rad(yaw)); crow.scale = (scale,)*3
    for pv, s in wings: pv.rotation_euler = (rad(-wing) * s, 0, 0)
    headp.rotation_euler = (0, rad(head), 0)
    for l in legs: l.hide_render = not standing
    beak_pebble.hide_render = not pebble

def show(obj, on):
    obj.hide_render = not on
    for c in obj.children_recursive: c.hide_render = not on
    if obj is crow:   # keep the pose's leg and pebble visibility
        pass

# ---------- camera ----------
cam_data = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_data); sc.collection.objects.link(cam); sc.camera = cam
def look(loc, target, lens):
    cam.location = loc; cam_data.lens = lens
    d = Vector(target) - Vector(loc); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

RIM = 2.40   # crow body height when standing on the rim

SHOTS = {
  'cover':  dict(sky=('#7ec4ea', '#fde7c0'), cam=((2.4, -6.6, 2.0), (0.3, 0, 1.5), 38), pot=True, cut=False, water=0.5,
                 crow=dict(loc=(0.12, 0, RIM), yaw=180, head=10), pile=True, sunloc=(-7, 40, 16)),
  'hot':    dict(sky=('#ff8c4a', '#ffd690'), cam=((0, -12, 1.8), (0, 4, 3.2), 28), pot=False, crow=None, pile=False, sunloc=(3, 40, 13)),
  'fly':    dict(sky=('#ff9d5c', '#ffd08a'), cam=((0, -7.5, 3.8), (0, 0, 4.4), 35), pot=False, crow=dict(loc=(-0.4, 0, 4.4), yaw=0, wing=55, standing=False), pile=False, sunloc=(9, 40, 15)),
  'search': dict(sky=('#ff9d5c', '#ffd08a'), cam=((0, -13, 6.5), (1.5, 5, 1.0), 30), pot=False, crow=dict(loc=(2.2, 1.0, 5.2), yaw=-20, wing=25, head=25, standing=False), pile=False, sunloc=(-12, 40, 18)),
  'pot':    dict(sky=('#f7b267', '#ffe2b0'), cam=((1.6, -7.0, 1.7), (0.3, 0, 1.3), 35), pot=True, cut=False, water=0.5, crow=dict(loc=(1.9, -0.2, 2.9), yaw=180, wing=45, standing=False), pile=True, sunloc=(-8, 40, 15)),
  'low':    dict(sky=('#f7b267', '#ffe2b0'), cam=((0.25, -5.6, 1.9), (0.05, 0, 1.4), 34), pot=True, cut=True, water=0.35, peb=0, crow=dict(loc=(0.3, 0.12, RIM), yaw=180, head=45), pile=True, sunloc=(-8, 40, 15)),
  'idea':   dict(sky=('#f7b267', '#ffe2b0'), cam=((0.9, -5.4, 1.1), (1.0, 0, 0.9), 40), pot=True, cut=False, water=0.35, crow=dict(loc=(0.75, -0.75, 0.5), yaw=0, head=20), pile=True, bulb=(1.2, -0.75, 1.35), sunloc=(-8, 40, 15)),
  'drop':   dict(sky=('#f7b267', '#ffe2b0'), cam=((0.25, -5.6, 1.9), (0.05, 0, 1.4), 34), pot=True, cut=True, water=0.95, peb=5, crow=dict(loc=(0.3, 0.12, RIM), yaw=180, head=35, pebble=True), pile=True, sunloc=(-8, 40, 15)),
  'drink':  dict(sky=('#f7b267', '#ffe2b0'), cam=((0.25, -5.6, 1.9), (0.05, 0, 1.4), 34), pot=True, cut=True, water=1.86, peb=10, crow=dict(loc=(0.46, 0.12, RIM), yaw=180, head=62), pile=False, sunloc=(-8, 40, 15)),
  'lesson': dict(sky=('#7d6bb8', '#ffb38a'), cam=((0, -9, 2.4), (0.8, 0, 2.6), 32), pot=True, cut=False, water=1.62, crow=dict(loc=(2.2, 0.5, 4.2), yaw=-25, wing=60, standing=False), pile=False, sunloc=(-10, 40, 6)),
}

def render(name):
    s = SHOTS[name]
    sky(*s['sky']); look(*s['cam'])
    sun.location = s['sunloc']
    set_cut(s.get('cut', False), s['pot']); set_water(s.get('water', 0.5))
    for i, p in enumerate(inside_pebbles): p.hide_render = not (s['pot'] and i < s.get('peb', 0))
    for p in pile: p.hide_render = not s['pile']
    show(bulb, 'bulb' in s)
    if 'bulb' in s: bulb.location = s['bulb']
    if s['crow']:
        show(crow, True); c = s['crow']
        pose_crow(c['loc'], c.get('yaw', 0), c.get('wing', 0), c.get('head', 0), c.get('standing', True), c.get('pebble', False))
    else:
        show(crow, False)
    sc.render.filepath = os.path.join(OUT, f'{name}.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', name, flush=True)

for n in (SHOTS if WHICH == 'all' else WHICH.split(',')):
    render(n)
