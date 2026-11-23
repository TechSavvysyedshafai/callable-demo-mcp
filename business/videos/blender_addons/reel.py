# Blender add-on test reel. Usage: blender-python reel.py -- SEG OUTDIR F0 F1 PCT SAMPLES   (STEP env = render every Nth frame)
# Every scene is original and built in code. Frames are 24 fps; only every STEP-th frame is rendered (held on twos/threes).
import bpy, math, sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blib import *
from gn_lib import *
a=sys.argv[sys.argv.index('--')+1:]; SEG=a[0]; OUT=a[1]; F0,F1,PCT,SAMP=map(int,a[2:6]); STEP=int(os.environ.get('STEP','3'))
FPS=24
_r=render
def render(sc,path):
    if not os.path.exists(path): _r(sc,path)
def hsv(h,s=0.8,v=0.95):
    import colorsys; r,g,b=colorsys.hsv_to_rgb(h%1,s,v); return tuple(((c+0.055)/1.055)**2.4 if c>0.04045 else c/12.92 for c in (r,g,b))
def emit(name,col,strength=2.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; b=nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*col,1); b.inputs['Roughness'].default_value=0.35
    b.inputs['Emission Color'].default_value=(*col,1); b.inputs['Emission Strength'].default_value=strength; return m
def loop(sc,fn,start=0):
    """Call fn(frame) for each frame from start..F1; render the ones in [F0,F1] that fall on STEP."""
    t0=time.time(); n=0
    for f in range(start,F1+1):
        fn(f)
        if f>=F0 and f%STEP==0:
            sc.frame_set(f); render(sc,f'{OUT}/f{f:05d}.png'); n+=1
    print('sec/frame',(time.time()-t0)/max(n,1),flush=True)
def dark(sc,col=(0.03,0.04,0.09)):
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.05
    bpy.data.materials['back'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col,1)

# ---------- S1: Geometry Nodes mandala (the "Grasshopper" of Blender) ----------
def seg_gn():
    sc=setup(PCT,SAMP,bg=(0.02,0.03,0.07)); dark(sc,(0.02,0.03,0.07))
    rings=[]
    for k,(rad,hue) in enumerate([(0.26,0.02),(0.47,0.08),(0.68,0.55),(0.88,0.82)]):
        m=emit(f'p{k}',hsv(hue,0.85,1.0),1.4); ng=ring_group(m)
        bpy.ops.mesh.primitive_plane_add(size=0.01); o=bpy.context.object; o.rotation_euler=(math.radians(90),0,0); o.location=(0,0,0.1)
        md=o.modifiers.new('GN','NODES'); md.node_group=ng; rings.append((md,ids(ng),rad,hue))
    def upd(f):
        t=f/FPS
        for k,(md,i,rad,hue) in enumerate(rings):
            ph=t/15*2*math.pi+k*1.1
            n=int(6+round(18*(0.5-0.5*math.cos(ph))))+k*2; md[i['Count']]=max(n,3)
            md[i['Radius']]=rad*(1+0.12*math.sin(t*0.7+k)); md[i['Size']]=0.07+0.04*k*(0.5+0.5*math.sin(t*0.9+k*2)); md[i['Len']]=0.35+0.9*(0.5+0.5*math.sin(t*0.5+k)); md[i['Twist']]=t*0.25*(1 if k%2==0 else -1)
        for k,(md,i,rad,hue) in enumerate(rings):
            m=md.node_group.nodes['Set Material'].inputs['Material'].default_value; b=m.node_tree.nodes['Principled BSDF']
            c=hsv(hue+t*0.02,0.85,1.0); b.inputs['Base Color'].default_value=(*c,1); b.inputs['Emission Color'].default_value=(*c,1)
    sc.frame_start=0; loop(sc,upd)

# ---------- S2: real protein (HIV capsid C-terminal domain, PDB 1A8O) built with Geometry Nodes ----------
def seg_mol():
    sc=setup(PCT,SAMP,bg=(0.04,0.05,0.10)); dark(sc,(0.04,0.05,0.10))
    atoms=[]; ca=[]
    for ln in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'1A8O.pdb')):
        if ln.startswith('ATOM'):
            el=ln[76:78].strip() or ln[12:14].strip()[:1]; xyz=(float(ln[30:38]),float(ln[38:46]),float(ln[46:54]))
            atoms.append((el,xyz)); 
            if ln[12:16].strip()=='CA': ca.append(xyz)
    n=len(atoms); cx=sum(p[1][0] for p in atoms)/n; cy=sum(p[1][1] for p in atoms)/n; cz=sum(p[1][2] for p in atoms)/n
    S=0.056; pts=[((x-cx)*S,(y-cy)*S,(z-cz)*S) for _,(x,y,z) in atoms]
    code={'C':0,'N':1,'O':2,'S':3}
    me=bpy.data.meshes.new('mol'); me.from_pydata(pts,[],[]); at=me.attributes.new('elem','INT','POINT'); at.data.foreach_set('value',[code.get(e,0) for e,_ in atoms])
    mats=[mat('C',hexc('#9aa5b4'),0.4,0.2),mat('N',hexc('#3b6fe0'),0.35,0.3),mat('O',hexc('#e5483a'),0.35,0.3),mat('S',hexc('#f2c230'),0.3,0.3)]
    ag=atoms_group(mats,[0.062,0.058,0.056,0.085]); ob=bpy.data.objects.new('mol',me); sc.collection.objects.link(ob)
    md=ob.modifiers.new('GN','NODES'); md.node_group=ag; thr=ids(ag)['Threshold']
    # backbone ribbon through the CA atoms, drawn on with bevel_factor_end
    cu=bpy.data.curves.new('bb','CURVE'); cu.dimensions='3D'; cu.bevel_depth=0.018; cu.resolution_u=6; sp=cu.splines.new('POLY'); sp.points.add(len(ca)-1)
    for p,(x,y,z) in zip(sp.points,ca): p.co=((x-cx)*S,(y-cy)*S,(z-cz)*S,1)
    bb=bpy.data.objects.new('bb',cu); sc.collection.objects.link(bb); cu.materials.append(emit('bb',hexc('#ffd24a'),1.0))
    root=bpy.data.objects.new('root',None); sc.collection.objects.link(root); ob.parent=root; bb.parent=root; root.location=(0,0,0.1)
    root.rotation_euler=(math.radians(-70),0,0)  # long axis roughly upright
    def upd(f):
        t=f/FPS
        md[thr]=n*min(1.0,max(0.0,(t-1)/22)); ob.update_tag(); bpy.context.view_layer.update()
        cu.bevel_factor_end=min(1.0,max(0.001,(t-24)/10))
        root.rotation_euler=(math.radians(-70),0,math.radians(t*14))
        z=1.0+0.35*(0.5-0.5*math.cos(t/60*2*math.pi)); root.scale=(z,z,z)
        bb.hide_render = t<24
    sc.frame_start=0; loop(sc,upd)

# ---------- S3: rigid-body physics (3 acts of 20 s) ----------
from mathutils import Matrix, Euler
def rb(o,kind='ACTIVE',mass=1.0,fric=0.6,bounce=0.1,shape=None):
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.rigidbody.object_add(); r=o.rigid_body
    r.type=kind; r.mass=mass; r.friction=fric; r.restitution=bounce
    if shape: r.collision_shape=shape
    o.select_set(False)
def spawn_at(o,frame):
    """Hold the object frozen until `frame`, then let physics take over."""
    o.rigid_body.enabled=False; o.keyframe_insert('rigid_body.enabled',frame=1)
    o.rigid_body.enabled=True; o.keyframe_insert('rigid_body.enabled',frame=frame)
def seg_phys():
    act=int(os.environ.get('ACT','0')); sc=setup(PCT,SAMP,bg=(0.93,0.90,0.84))
    bpy.ops.rigidbody.world_add(); w=sc.rigidbody_world; w.substeps_per_frame=12; w.solver_iterations=25; sc.gravity=(0,0,-5.5); sc.frame_start=1; sc.frame_end=FPS*20+2
    def block(size,loc,m,kind='ACTIVE',mass=1.0,rot=(0,0,0),fric=0.7,vis=True):
        o=box(size,loc,m,bevel=0.01,seg=2); o.rotation_euler=rot; rb(o,kind,mass,fric); o.hide_render=not vis; return o
    wall=mat('wall',hexc('#d9cdb8'),0.9)
    if act==0:   # coloured pyramid knocked down by three rolling balls
        block((3.5,1.2,0.4),(0,0,-1.5),mat('gr',hexc('#bfae92'),0.9),'PASSIVE')
        for s in (-1,1): block((3.5,0.1,3.8),(0,s*0.3,0),wall,'PASSIVE',vis=False)
        block((1.1,0.5,0.1),(-0.8,0,-0.3),mat('ramp',hexc('#6b5b45'),0.7),'PASSIVE',rot=(0,math.radians(-18),0))
        for row in range(7):
            for i in range(7-row):
                m=mat(f'b{row}_{i}',hsv(0.02+0.07*row,0.7,0.95),0.5,0.2)
                block((0.2,0.22,0.14),((i-(6-row)/2)*0.215+0.45,0,-1.3+0.075+row*0.142),m,mass=0.6)
        for k,t0 in enumerate([1,7,13]):
            ball=sphere(0.13,mat(f'ball{k}',hexc('#2b2f3a'),0.25,0.8)); ball.location=(-1.25,0,0.35+0.0); rb(ball,'ACTIVE',5,0.4,0.25,'SPHERE'); spawn_at(ball,int(t0*FPS)+1)
    elif act==1: # domino spiral seen from above-front
        cam=sc.camera; cam.location=(0,-4,2.8); cam.rotation_euler=(math.radians(60),0,0); cam.data.ortho_scale=3.0
        block((6,6,0.2),(0,0,-0.1),mat('fl',hexc('#c9b99c'),0.9),'PASSIVE',fric=0.9)
        pts=[]; th=0.0; T=2*math.pi*2.4
        while th<T:
            r=0.95-0.6*th/T; pts.append((r*math.cos(th),r*math.sin(th),th)); th+=0.125/max(r,0.2)
        for k,(x,y,th) in enumerate(pts):
            m=mat(f'd{k}',hsv(k/len(pts)*0.85,0.75,0.95),0.4,0.2); tilt=math.radians(15) if k==0 else 0.0
            rot=(Matrix.Rotation(th+math.pi/2,3,'Z')@Matrix.Rotation(tilt,3,'Y')).to_euler()
            block((0.05,0.13,0.24),(x,y,0.12+(0.012 if k==0 else 0)),m,mass=0.3,rot=rot,fric=0.6)
    else:        # rain of colourful shapes into a glass tank
        block((1.9,1.0,0.2),(0,0,-1.55),mat('gr2',hexc('#b8a98c'),0.9),'PASSIVE')
        for sx in (-1,1): block((0.1,1.0,1.8),(sx*0.9,0,-0.65),mat('glass',hexc('#9fc6d6'),0.2),'PASSIVE')
        for s in (-1,1): block((2.0,0.1,3.8),(0,s*0.25,0),wall,'PASSIVE',vis=False)
        random.seed(7)
        for k in range(110):
            sz=random.uniform(0.13,0.2); m=mat(f's{k}',hsv(random.random(),0.75,0.97),0.35,0.4); x=random.uniform(-0.6,0.6)
            if k%3==0: o=sphere(sz*0.55,m); o.location=(x,0,2.1); rb(o,'ACTIVE',1,0.5,0.35,'SPHERE')
            else: o=block((sz,sz*0.9,sz),(x,0,2.1),m,mass=1.0,rot=(random.random(),random.random(),random.random()))
            spawn_at(o,int((k*0.16+0.5)*FPS)+1)
    t0=time.time(); n=0
    for f in range(0,F1+1):
        sc.frame_set(f+1)
        if f>=F0 and f%STEP==0: render(sc,f'{OUT}/f{f:05d}.png'); n+=1
    print('sec/frame',(time.time()-t0)/max(n,1),flush=True)

# ---------- S4: Freestyle toon outlines ----------
def seg_toon():
    sc=setup(PCT,SAMP,bg=(0.97,0.93,0.82)); sc.render.use_freestyle=True; sc.render.line_thickness_mode='ABSOLUTE'; sc.render.line_thickness=2.2
    vl=bpy.context.view_layer; vl.use_freestyle=True; fs=vl.freestyle_settings
    ls=fs.linesets.new('ink') if not fs.linesets else fs.linesets[0]; ls.linestyle=bpy.data.linestyles.new('inkstyle') if ls.linestyle is None else ls.linestyle; ls.select_silhouette=True; ls.select_border=True; ls.select_crease=True
    ls.linestyle.color=(0.05,0.04,0.06); ls.linestyle.thickness=2.4
    shapes=[]
    def add(kind,hue,pos):
        if kind=='torus': bpy.ops.mesh.primitive_torus_add(major_radius=0.34,minor_radius=0.13,major_segments=40,minor_segments=20)
        elif kind=='cone': bpy.ops.mesh.primitive_cone_add(radius1=0.3,depth=0.65,vertices=5)
        elif kind=='cube': bpy.ops.mesh.primitive_cube_add(size=0.55)
        elif kind=='ico': bpy.ops.mesh.primitive_ico_sphere_add(radius=0.34,subdivisions=1)
        else: bpy.ops.mesh.primitive_monkey_add(size=0.65)
        o=bpy.context.object; o.data.materials.append(mat(kind,hsv(hue,0.55,1.0),0.9)); o.location=pos
        for p in o.data.polygons: p.use_smooth=False
        shapes.append((o,pos,hue)); return o
    add('torus',0.02,(-0.45,0,1.05)); add('cone',0.12,(0.45,0,0.45)); add('cube',0.35,(-0.4,0,-0.25)); add('ico',0.55,(0.4,0,-0.95)); add('monkey',0.82,(0,0,-1.5))
    def upd(f):
        t=f/FPS
        for k,(o,p,h) in enumerate(shapes):
            o.rotation_euler=(t*(0.5+0.15*k),t*(0.7-0.1*k),t*0.35*(k+1)*0.4)
            s=1+0.12*math.sin(t*1.3+k); o.scale=(s,s,s); o.location=(p[0]+0.12*math.sin(t*0.6+k*1.7),p[1],p[2]+0.08*math.cos(t*0.8+k))
            m=o.data.materials[0].node_tree.nodes['Principled BSDF']; c=hsv(h+t*0.03,0.55,1.0); m.inputs['Base Color'].default_value=(*c,1)
        ls.linestyle.thickness=2.4+2.2*(0.5+0.5*math.sin(t*0.9)); 
        c=0.05+0.4*(0.5+0.5*math.sin(t*0.25)); ls.linestyle.color=(c*0.2,0.04,c)
    sc.frame_start=0; loop(sc,upd)

# ---------- S5: sound drives the animation (synth track -> FFT bands per frame -> bars, ring, pulse) ----------
def make_audio(path,dur=60.0,sr=44100):
    import numpy as np, wave
    n=int(dur*sr); t=np.arange(n)/sr; y=np.zeros(n); bpm=120; beat=60/bpm
    rng=np.random.default_rng(3)
    for k in range(int(dur/beat)+1):                      # kick every beat
        t0=int(k*beat*sr); L=int(0.25*sr); 
        if t0+L>n: break
        tt=np.arange(L)/sr; y[t0:t0+L]+=0.9*np.sin(2*np.pi*(120*np.exp(-tt*18)+40)*tt)*np.exp(-tt*9)
    for k in range(int(dur/beat*2)):                      # off-beat hats (noise)
        t0=int((k*beat/2+beat/4)*sr); L=int(0.06*sr)
        if t0+L>n: break
        y[t0:t0+L]+=0.18*rng.standard_normal(L)*np.exp(-np.arange(L)/sr*70)
    sc_=[0,3,5,7,10,12,15,17]; root=55.0                  # bass + arpeggio (minor pentatonic-ish)
    for k in range(int(dur/(beat/2))):
        t0=int(k*beat/2*sr); L=int(beat/2*sr*0.95)
        if t0+L>n: break
        tt=np.arange(L)/sr; sec=(k//16)%4; base=root*2**(([0,3,-2,5][sec])/12)
        if k%2==0: y[t0:t0+L]+=0.22*np.sin(2*np.pi*base*tt)*np.exp(-tt*5)
        note=sc_[(k*3+sec*2)%len(sc_)]; f=base*4*2**(note/12)
        if t0/sr>8: y[t0:t0+L]+=0.10*np.sin(2*np.pi*f*tt)*np.exp(-tt*9)
    y/=max(1e-9,np.abs(y).max())/0.9
    w=wave.open(path,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((y*32767).astype('<i2').tobytes()); w.close(); return y,sr
def seg_sound():
    import numpy as np
    here=os.path.dirname(os.path.abspath(__file__)); wav=os.path.join(here,'reel_audio.wav')
    y,sr=make_audio(wav) if not os.path.exists(wav) else (None,None)
    if y is None:
        import wave; w=wave.open(wav); sr=w.getframerate(); y=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')/32768.0
    spf=sr//FPS; NB=16; edges=np.geomspace(40,9000,NB+1)
    def bands(f):
        seg=y[f*spf:f*spf+2048]
        if len(seg)<2048: return [0]*NB,0
        sp=np.abs(np.fft.rfft(seg*np.hanning(2048))); fr=np.fft.rfftfreq(2048,1/sr)
        b=[float(sp[(fr>=edges[i])&(fr<edges[i+1])].sum()) for i in range(NB)]; return b,float(np.sqrt((seg**2).mean()))
    allb=[bands(f) for f in range(0,min(F1+1,60*FPS))]; mx=[max(max(b[i] for b,_ in allb) for _ in [0]) for i in range(1)]
    peak=np.max([np.array(b) for b,_ in allb],axis=0)+1e-9; rms_peak=max(r for _,r in allb)+1e-9
    sc=setup(PCT,SAMP,bg=(0.02,0.02,0.06)); dark(sc,(0.02,0.02,0.06))
    bars=[]
    for i in range(NB):
        m=emit(f'bar{i}',hsv(i/NB*0.8,0.85,1.0),1.6); o=box((0.09,0.09,1.0),(0,0,0),m,bevel=0.01,seg=2); o.location=(-0.88+i*0.1175,0,-1.2); bars.append(o)
    core=sphere(0.28,emit('core',hexc('#ff4fa3'),2.0),32); core.location=(0,0,0.55)
    m=emit('rg',hexc('#4fd8ff'),1.6); ng=ring_group(m); bpy.ops.mesh.primitive_plane_add(size=0.01); ro=bpy.context.object; ro.rotation_euler=(math.radians(90),0,0); ro.location=(0,0.05,0.55)
    md=ro.modifiers.new('GN','NODES'); md.node_group=ng; i_=ids(ng)
    def upd(f):
        b,r=allb[min(f,len(allb)-1)]; bn=[min(1.0,(b[i]/peak[i]))**0.8 for i in range(NB)]; lvl=min(1.0,r/rms_peak)
        for i,o in enumerate(bars):
            h=0.08+1.6*bn[i]; o.scale=(1,1,h); o.location.z=-1.55+h/2
            bb=o.data.materials[0].node_tree.nodes['Principled BSDF']; bb.inputs['Emission Strength'].default_value=0.6+3*bn[i]
        s=0.8+0.9*lvl; core.scale=(s,s,s)
        md[i_['Count']]=int(8+14*lvl); md[i_['Radius']]=0.62+0.22*lvl; md[i_['Size']]=0.07+0.05*lvl; md[i_['Len']]=0.5+0.8*lvl; md[i_['Twist']]=f/FPS*0.4
    sc.frame_start=0; loop(sc,upd)

DISPATCH={'gn':seg_gn,'mol':seg_mol,'phys':seg_phys,'toon':seg_toon,'sound':seg_sound}
DISPATCH[SEG]()
