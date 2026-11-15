# Toy short: deterministic animation, every pose is a function of time t (seconds).
import bpy, math, sys, time
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
OUT=args[0]; F0=int(args[1]); F1=int(args[2]); PCT=int(args[3]); SAMP=int(args[4])
FPS=24
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.render.fps=FPS
sc.render.engine='CYCLES'; sc.cycles.device='CPU'
sc.render.resolution_x, sc.render.resolution_y = 1280, 720; sc.render.resolution_percentage=PCT
sc.cycles.samples=SAMP; sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.03
sc.cycles.use_denoising=True; sc.cycles.denoiser='OPENIMAGEDENOISE'
sc.cycles.max_bounces=6; sc.render.use_persistent_data=True
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'
sc.render.image_settings.file_format='PNG'

def mat(name,col,rough,coat=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*col,1); b.inputs['Roughness'].default_value=rough
    b.inputs['Coat Weight'].default_value=coat; return m
def box(name,loc,size,m,parent=None,bevel=0.0007):
    bpy.ops.mesh.primitive_cube_add(location=(0,0,0)); o=bpy.context.object; o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2); bpy.ops.object.transform_apply(scale=True)
    bv=o.modifiers.new('bv','BEVEL'); bv.width=bevel; bv.segments=3
    o.data.materials.append(m); o.parent=parent; o.location=loc; return o
def empty(name,loc,parent=None):
    o=bpy.data.objects.new(name,None); sc.collection.objects.link(o); o.parent=parent; o.location=loc; return o

orange=mat('orange',(0.80,0.20,0.06),0.45,0.25); eye=mat('eye',(0.01,0.01,0.01),0.08,1.0)
teal=mat('teal',(0.04,0.50,0.52),0.35,0.4); mat_mat=mat('mat',(0.10,0.30,0.20),0.75)
wall=mat('wall',(0.80,0.78,0.72),0.9)

# Toy: feet pivot (squash/stretch) -> body
feet=empty('feet',(0,0,0)); 
body=box('body',(0,0,0.0225),(0.067,0.022,0.035),orange,feet)
box('armL',(-0.0405,0,0.021),(0.014,0.012,0.012),orange,feet); box('armR',(0.0405,0,0.021),(0.014,0.012,0.012),orange,feet)
for x in (-0.024,-0.008,0.008,0.024): box('leg',(x,0,0.0035),(0.010,0.012,0.007),orange,feet)
eyes=empty('eyes',(0,-0.0112,0.026),feet)
box('eyeL',(-0.012,0,0),(0.006,0.0012,0.009),eye,eyes); box('eyeR',(0.012,0,0),(0.006,0.0012,0.009),eye,eyes)
# Ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0125,segments=48,ring_count=24); ball=bpy.context.object
ball.data.materials.append(teal)
for f in ball.data.polygons: f.use_smooth=True
# Cutting mat floor with a centimetre grid (procedural), and a back wall
bpy.ops.mesh.primitive_plane_add(size=8.0); fl=bpy.context.object; fl.data.materials.append(mat_mat)
nt=mat_mat.node_tree; b=nt.nodes['Principled BSDF']
tc=nt.nodes.new('ShaderNodeTexCoord'); br=nt.nodes.new('ShaderNodeTexBrick')
br.inputs['Scale'].default_value=200; br.inputs['Mortar Size'].default_value=0.012; br.offset=0.0; br.squash=1.0
br.inputs['Brick Width'].default_value=1.0; br.inputs['Row Height'].default_value=1.0
br.inputs['Color1'].default_value=(0.10,0.30,0.20,1); br.inputs['Color2'].default_value=(0.10,0.30,0.20,1); br.inputs['Mortar'].default_value=(0.55,0.65,0.58,1)
nt.links.new(tc.outputs['Object'],br.inputs['Vector']); nt.links.new(br.outputs['Color'],b.inputs['Base Color'])
bpy.ops.mesh.primitive_plane_add(size=8.0,location=(0,0.35,0.5),rotation=(math.radians(90),0,0)); bpy.context.object.data.materials.append(wall)
# Light
bpy.ops.object.light_add(type='SUN'); s=bpy.context.object; s.data.energy=2.6; s.data.angle=math.radians(1.2)
s.rotation_euler=(math.radians(55),math.radians(12),math.radians(-35))
bpy.ops.object.light_add(type='AREA',location=(-0.25,-0.15,0.18)); a=bpy.context.object; a.data.energy=1.2; a.data.size=0.2
a.rotation_euler=(math.radians(60),0,math.radians(-60)); a.data.color=(0.75,0.85,1.0)
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']
bg.inputs['Color'].default_value=(0.6,0.68,0.8,1); bg.inputs['Strength'].default_value=0.3
# Camera
cd=bpy.data.cameras.new('c'); cam=bpy.data.objects.new('cam',cd); sc.collection.objects.link(cam); sc.camera=cam
cd.sensor_width=36; cd.dof.use_dof=True; cd.dof.aperture_fstop=4.0

# ---------- timing helpers ----------
def clamp(x): return max(0.0,min(1.0,x))
def ease(x): x=clamp(x); return x*x*(3-2*x)
def lerp(a,b,u): return a+(b-a)*u
def hop(t,t0,dur,h):  # height and squash for one hop starting t0
    u=(t-t0)/dur
    if u<-0.25 or u>1.25: return 0.0,1.0
    if u<0:  return 0.0, 1-0.18*math.sin(math.pi*(u+0.25)/0.25*0.5)   # anticipation squash
    if u>1:  return 0.0, 1-0.15*math.sin(math.pi*(u-1)/0.25)*(1.25-u)/0.25  # landing squash
    return h*4*u*(1-u), 1+0.12*math.sin(math.pi*u)                      # stretch in air
def spring(t,t0,amp,freq=3.0,damp=5.0):
    u=t-t0
    return 0.0 if u<0 else amp*(1-math.exp(-damp*u)*math.cos(2*math.pi*freq*u))

HOPS=[(1.5,0.45,0.030,0.000,0.045),(2.25,0.45,0.030,0.045,0.085),  # (start,dur,height,x0,x1) walk right
      (5.0,0.35,0.020,0.085,0.085),                                     # surprise jump in place
      (6.3,0.5,0.045,0.085,0.21),(7.05,0.5,0.045,0.21,0.34)]            # bounce away together
def pose(t):
    x=0.0; z=0.0; sq=1.0
    for (t0,d,h,x0,x1) in HOPS:
        hz,s=hop(t,t0,d,h); z+=hz; sq*=s
        x = x1 if t>=t0+d else (lerp(x0,x1,ease((t-t0)/d)) if t>=t0 else x)
        if t<t0: break
    # eyes: blink at 0.8 s and 4.2 s, glance right 3.3-4.9 s then back
    bl=1.0
    for tb in (0.8,4.2):
        u=(t-tb)/0.16
        if 0<=u<=1: bl=min(bl,abs(1-2*u)+0.08)
    gx=0.006*ease((t-3.3)/0.25)*(1-ease((t-4.9)/0.25))
    # ball: rolls in 2.8-3.6 s, bounces 4.6-5.1 s, then follows the toy
    bx=lerp(0.25,0.15,ease((t-2.8)/0.8)); bz=0.0125
    u=(t-4.6)/0.5
    if 0<=u<=1: bz+=0.025*4*u*(1-u)
    for (t0,d,h,x0,x1) in HOPS[3:]:
        u=(t-(t0+0.08))/d
        if 0<=u<=1: bz+=h*0.8*4*u*(1-u)
    if t>=6.3: bx=max(bx,x+0.068)
    roll=-(bx-0.25)/0.0125
    # camera: slow push and pan to follow
    cx=lerp(0.02,0.17,ease((t-5.4)/2.6)); cyd=lerp(-0.27,-0.23,ease(t/8.0))
    return x,z,sq,bl,gx,bx,bz,roll,cx,cyd

DUR=8.0; N=int(DUR*FPS)
sc.frame_start=F0; sc.frame_end=F1
t0w=time.time()
for f in range(F0,F1+1):
    t=(f-1)/FPS
    x,z,sq,bl,gx,bx,bz,roll,cx,cyd=pose(t)
    sc.frame_set(f)
    feet.location=(x,0,z); feet.scale=(1/math.sqrt(sq),1/math.sqrt(sq),sq)
    eyes.location=(gx,-0.0112,0.026); eyes.scale=(1,1,bl)
    ball.location=(bx,-0.004,bz); ball.rotation_euler=(0,roll,0)
    cam.location=(cx,cyd,0.03)
    tgt=Vector((x+0.02+0.25*ease((t-2.8)/0.8)*(bx-x-0.02),0,0.024)); d=tgt-cam.location
    cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    cd.lens=50; cd.dof.focus_distance=(Vector((x,-0.0112,0.026+z))-cam.location).length
    sc.render.filepath=f"{OUT}/f{f:04d}.png"; bpy.ops.render.render(write_still=True)
print('done',F0,F1,'seconds',round(time.time()-t0w,1))
