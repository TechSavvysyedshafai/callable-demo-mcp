# Original 10 s Blender piece inspired by the Madhubani (Mithila, Bihar) folk tradition. Not a copy of any artist's work.
import bpy, math, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blib import *
a=sys.argv[sys.argv.index('--')+1:]; OUT=a[0]; F0,F1,PCT,SAMP=map(int,a[1:5]); STEP=int(os.environ.get('STEP','2'))
N=240
sc=setup(PCT,SAMP); sc.frame_start=0; sc.frame_end=N-1
m=bpy.data.materials['back']; nt=m.node_tree; b=nt.nodes['Principled BSDF']
n=nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=60; n.inputs['Detail'].default_value=10
r=nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color=(*hexc('#e6d3a8'),1); r.color_ramp.elements[1].color=(*hexc('#f2e6c6'),1)
nt.links.new(n.outputs['Fac'],r.inputs['Fac']); nt.links.new(r.outputs['Color'],b.inputs['Base Color'])
C=lambda name,h: mat(name,hexc(h),0.6,0.0)
ink=C('ink','#14110f'); red=C('red','#c8281e'); yel=C('yel','#f2b705'); ora=C('ora','#e5701a'); grn=C('grn','#2e8b3d'); blu=C('blu','#1d4e9e'); wht=C('wht','#f6efdc'); mar=C('mar','#7a1f14')
def root(px,py,y=0.0,sx=1.0):
    e=bpy.data.objects.new('r',None); sc.collection.objects.link(e); e.location=(X(px),y,Z(py)); e.scale=(sx,1,1); return e
def child(parent,x=0,z=0,rot=0):
    e=bpy.data.objects.new('c',None); sc.collection.objects.link(e); e.parent=parent; e.location=(x/360,0,z/360); e.rotation_euler=(0,math.radians(rot),0); return e
def draw(cu,f0,f1):
    cu.bevel_factor_end=0.0; cu.keyframe_insert('bevel_factor_end',frame=f0-1); cu.bevel_factor_end=1.0; cu.keyframe_insert('bevel_factor_end',frame=f1)
def outline(par,pts,depth,mt,f0,f1,y=-0.02,cyc=False,sharp=False):
    cu=bpy.data.curves.new('o','CURVE'); cu.dimensions='3D'; cu.resolution_u=10; cu.bevel_depth=P(depth); cu.bevel_resolution=3; cu.use_fill_caps=True
    if cyc: pts=list(pts)+[pts[0]]
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1); sp.use_cyclic_u=False
    for bp,(x,z) in zip(sp.bezier_points,pts): bp.co=(x/360,y,z/360); bp.handle_left_type=bp.handle_right_type=('VECTOR' if sharp else 'AUTO')
    o=bpy.data.objects.new('o',cu); sc.collection.objects.link(o); o.data.materials.append(mt); o.parent=par; draw(cu,f0,f1); return o
def pop(o,f0,f1):
    o.scale=(0,0,0); o.keyframe_insert('scale',frame=f0-1); o.scale=(1,1,1); o.keyframe_insert('scale',frame=f1)
def fill(par,pts,mt,f0,f1,y=0.02):
    cx=sum(p[0] for p in pts)/len(pts); cz=sum(p[1] for p in pts)/len(pts)
    me=bpy.data.meshes.new('f'); me.from_pydata([((x-cx)/360,0,(z-cz)/360) for x,z in pts],[],[tuple(range(len(pts)))]); me.update()
    o=bpy.data.objects.new('f',me); sc.collection.objects.link(o); o.data.materials.append(mt); o.parent=par; o.location=(cx/360,y,cz/360); pop(o,f0,f1); return o
def ell(cx,cz,rx,rz,rot=0,k=28):
    c,s=math.cos(math.radians(rot)),math.sin(math.radians(rot)); out=[]
    for i in range(k):
        t=2*math.pi*i/k; x=rx*math.cos(t); z=rz*math.sin(t); out.append((cx+x*c-z*s, cz+x*s+z*c))
    return out
def shape(par,pts,fm,f0,f1,depth=5,cyc=True,om=None,sharp=False,outl=True,yf=0.02,yo=-0.02):
    fill(par,pts,fm,f0+4,f1+4,y=yf)
    if outl: outline(par,pts,depth,om or ink,f0,f1,y=yo,cyc=cyc,sharp=sharp)
def dot(par,cx,cz,rad,mt,f0,f1,y=-0.03): fill(par,ell(cx,cz,rad,rad,0,14),mt,f0,f1,y)
def sway(e,base,amp,f0,period=48,ph=0.0):
    for f in range(f0,N,period//2):
        e.rotation_euler[1]=math.radians(base+amp*math.sin(ph+(f-f0)/(period/2)*math.pi)); e.keyframe_insert('rotation_euler',index=1,frame=f)
# --- border (double line)
bd=root(360,640); 
outline(bd,[(-332,612),(332,612),(332,-540),(-332,-540)],5,ink,0,34,cyc=True,sharp=True)
outline(bd,[(-314,594),(314,594),(314,-522),(-314,-522)],3,red,12,44,cyc=True,sharp=True)
# --- sun
sun=root(360,190); sunrot=child(sun)
sunrot.rotation_euler[1]=0; sunrot.keyframe_insert('rotation_euler',index=1,frame=0); sunrot.rotation_euler[1]=math.radians(70); sunrot.keyframe_insert('rotation_euler',index=1,frame=N-1)
for k in range(16):
    ph=360/16*k; L=(150 if k%2==0 else 128)
    c,s=math.cos(math.radians(ph)),math.sin(math.radians(ph)); w=0.17
    tri=[(82*math.cos(math.radians(ph-11)),82*math.sin(math.radians(ph-11))),(L*c,L*s),(82*math.cos(math.radians(ph+11)),82*math.sin(math.radians(ph+11)))]
    shape(sunrot,tri,ora if k%2==0 else yel,54+k*2,66+k*2,depth=3,sharp=True)
fill(sunrot,ell(0,0,78,78,0,48),yel,22,42); outline(sunrot,ell(0,0,78,78,0,36),5,ink,20,44,cyc=True)
fill(sunrot,ell(0,0,52,52,0,40),ora,34,50,y=0.0); outline(sunrot,ell(0,0,52,52,0,30),3,ink,34,52,cyc=True)
fill(sunrot,ell(0,0,24,24,0,24),red,44,56,y=-0.01)
# --- peacock
pk=root(360,780); tail=child(pk,0,10); tail.location.y=0.05
angs=[-78,-58,-39,-19.5,0,19.5,39,58,78]
for i,ang in enumerate(angs):
    fe=child(tail,0,0,ang); t0=64+abs(i-4)*6
    shape(fe,ell(0,215,34,100,0,26),grn if i%2==0 else yel,t0,t0+26,depth=5)
    for q,(rad,mt,dt) in enumerate(((21,ora,26),(13,blu,32),(5,ink,38))): dot(fe,0,262,rad,mt,t0+dt,t0+dt+8,y=-0.03-q*0.006)
    sway(fe,ang,2.2,150+i*3,period=72,ph=i*0.7)
shape(pk,ell(0,-40,62,100,0,32),blu,110,136,depth=7)
for row in range(4):
    for col in range(5-row%2):
        x=(col-(4-row%2)/2)*24; dot(pk,x,-95+row*40,4.5,yel if (row+col)%2==0 else wht,134+row*3+col,140+row*3+col)
shape(pk,ell(0,70,22,50,0,18),blu,124,146,outl=False,yf=0.015)
shape(pk,ell(0,135,27,27,0,20),blu,128,150,depth=5,yf=0.0,yo=-0.03)
shape(pk,[(-26,134),(-58,128),(-26,118)],ora,140,156,depth=4,sharp=True,yf=0.0,yo=-0.03)
dot(pk,-6,140,8,wht,150,156,y=-0.04); dot(pk,-8,140,3.5,ink,154,159,y=-0.046)
for dx,dz in ((-20,200),(0,214),(20,200)):
    outline(pk,[(0,160),(dx*0.5,(160+dz)/2),(dx,dz)],4,ink,146,158); dot(pk,dx,dz+8,8,ora,156,162)
outline(pk,[(-22,-130),(-26,-200),(-48,-216)],6,ink,150,170); outline(pk,[(22,-130),(26,-200),(48,-216)],6,ink,153,173)
# --- fish
def fish(px,py,sx,t0,ph):
    fr=root(px,py,0.0,sx); fb=child(fr)
    shape(fb,[(-100,0),(-168,52),(-150,0),(-168,-52)],red,t0,t0+22,depth=4,sharp=True,yf=0.03,yo=-0.01)
    shape(fb,ell(0,0,105,42,0,28),ora,t0+8,t0+34,depth=6)
    shape(fb,[(-20,38),(10,80),(48,38)],yel,t0+16,t0+30,depth=4,sharp=True,yf=0.03,yo=-0.01)
    shape(fb,[(12,-38),(32,-70),(58,-36)],yel,t0+18,t0+32,depth=4,sharp=True,yf=0.03,yo=-0.01)
    for r_ in range(3):
        for c_ in range(5):
            dot(fb,-62+c_*26+(r_%2)*12,-18+r_*18,4.5,mar,t0+30+r_*3+c_,t0+36+r_*3+c_)
    dot(fb,64,10,11,wht,t0+30,t0+36,y=-0.04); dot(fb,66,10,5,ink,t0+34,t0+38,y=-0.046)
    for f in range(t0+40,N,24):
        fb.location.z=P(6)*math.sin(ph+(f-t0)/24*math.pi); fb.keyframe_insert('location',index=2,frame=f)
fish(218,1030,0.9,150,0.0); fish(502,1030,-0.9,166,2.4)
# --- bottom band of triangles
band=root(360,1135)
for i in range(14):
    x=-286+i*44; fill(band,[(x-17,-14),(x+17,-14),(x,18)],red if i%2==0 else grn,192+i*2,200+i*2,y=0.0)
# slow push-in
cam=sc.camera.data; cam.ortho_scale=1280/360; cam.keyframe_insert('ortho_scale',frame=0); cam.ortho_scale=1280/360*0.97; cam.keyframe_insert('ortho_scale',frame=N-1)
cam_obj=sc.camera
t0_=time.time(); n_=0
for f in range(F0,F1+1,STEP):
    sc.frame_set(f); render(sc,f'{OUT}/f{f:04d}.png'); n_+=1
print('sec/frame',(time.time()-t0_)/max(n_,1))
