import bpy, math, json, time, sys, os
from mathutils import Vector
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from blib import *
STATE,OUT,F0,F1,PCT,SAMP=args(); S=json.load(open(STATE))['states']
sc=setup(PCT,SAMP); set_dof(sc,-0.06,float(os.environ.get('FSTOP','1.3')))
YC=-0.06
def W(p,yoff=0): return (X(p[0]),YC-P(p[2] if len(p)>2 else 0)+yoff,Z(p[1]))
def glow(name,col,strength=0.0):
    m=mat(name,col,0.5); b=m.node_tree.nodes['Principled BSDF']; b.inputs['Emission Color'].default_value=(*col,1); b.inputs['Emission Strength'].default_value=strength; return m
def emis(m,v): m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=v
cyto=mat('cyto',hexc('#fbe3cc'),0.8,0.0); nucm=glow('nuc',hexc('#efc6a2'),0.0); porem=glow('pore',hexc('#f1c232'),2.5)
oldm=mat('old',hexc('#3b4a5c'),0.45,0.25); rnam=mat('rna',hexc('#2a9d5c'),0.4,0.35)
basem=[mat('b'+c,hexc(c),0.4,0.3) for c in ('#e0663a','#3b82c4','#2e9e6b','#e6b422')]+[glow('stop',hexc('#d62828'),1.5)]
polym=mat('polyE',hexc('#8e5aa8'),0.35,0.5); ribm=mat('ribL',hexc('#9aa7b5'),0.6,0.1); ribm2=mat('ribS',hexc('#8795a4'),0.6,0.1)
capm=mat('cap',hexc('#e6b422'),0.4,0.4); trm=mat('trna',hexc('#5b8c5a'),0.5,0.2); trm2=mat('trna2',hexc('#3f6b3e'),0.5,0.2)
aam=[glow('aa%d'%k,hexc(c),0.0) for k,c in enumerate(['#8e5aa8','#e8803f','#2e9e6b','#3b82c4','#e6b422','#d2547a','#5b8c5a'])]
def curve(name,m,r):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.bevel_depth=r; cu.bevel_resolution=3; cu.resolution_u=4; cu.use_fill_caps=True
    o=bpy.data.objects.new(name,cu); sc.collection.objects.link(o); o.data.materials.append(m); return o
def set_splines(o,lines,yoff=0):
    cu=o.data; cu.splines.clear()
    for pts in lines:
        if len(pts)<2: continue
        sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
        for b,p in zip(sp.bezier_points,pts): b.co=W(p,yoff); b.handle_left_type=b.handle_right_type='AUTO'
cA=curve('pA',oldm,P(5)); cB=curve('pB',oldm,P(5)); cM=curve('mrna',rnam,P(4.5))
def cyl(r,m): bpy.ops.mesh.primitive_cylinder_add(radius=r,depth=1,vertices=10); o=bpy.context.object; o.data.materials.append(m); o.rotation_mode='QUATERNION'; return o
def place_cyl(o,a,b,m,yoff=0):
    va,vb=Vector(W(a,yoff)),Vector(W(b,yoff)); d=vb-va
    o.location=(va+vb)/2; o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized()); o.scale=(1,1,d.length); o.material_slots[0].material=m
def hide(o): o.scale=(0,0,0)
rungs=[[cyl(P(4),basem[0]) for _ in range(40)] for _ in range(2)]; mb=[cyl(P(3.2),basem[0]) for _ in range(24)]
cellO=sphere(1,cyto,64); cellO.location=(X(360),0.22,Z(560)); cellO.scale=(P(300),0.07,P(360))
nucO=sphere(1,nucm,48); nucO.location=(X(360),0.13,Z(420)); nucO.scale=(P(150),0.05,P(150))
bpy.ops.mesh.primitive_torus_add(major_radius=P(26),minor_radius=P(5)); poreO=bpy.context.object; poreO.data.materials.append(porem); poreO.rotation_euler=(math.radians(90),0,0); poreO.location=(X(360),0.0,Z(570))
polyO=sphere(P(36),polym,32); polyO.scale=(1,0.75,0.85)
ribL=sphere(1,ribm,48); ribS=sphere(1,ribm2,48)
capO=sphere(P(11),capm,16); tailO=[sphere(P(6),basem[0],12) for _ in range(3)]
trn=[]
for _ in range(3):
    r=bpy.data.objects.new('trna',None); sc.collection.objects.link(r)
    box((P(14),P(14),P(52)),(0,0,0),trm,P(5),parent=r)
    for dx in (-10,0,10): box((P(6),P(10),P(10)),(P(dx),0,-P(31)),trm2,P(2),parent=r)
    b=sphere(P(11),aam[0],16); b.parent=r; b.location=(0,-P(4),P(36)); trn.append((r,b))
beadO=[sphere(P(12),aam[j],16) for j in range(7)]
mr,me=mascot()
def sc3(o,k,base=1.0): k=max(0.0,min(1.0,k))*base; o.scale=(k,k,k)
t0=time.time(); n=0
for f in range(F0,F1+1,int(os.environ.get('STEP','1'))):
    s=S[f]; z,cx,cy=s['view']; set_view(sc,z,cx,cy)
    emis(nucm,0.7*s['nucGlow']); sc3(poreO,s['pore'])
    set_splines(cA,[s['pA']]); set_splines(cB,[s['pB']])
    i0=0
    for ax,ay,ad,mx,my,bx,by,bd,ca,cb,has in s['rungs']:
        if i0<40: place_cyl(rungs[0][i0],(ax,ay,ad),(mx,my,0),basem[ca]); place_cyl(rungs[1][i0],(mx,my,0),(bx,by,bd),basem[cb]); i0+=1
    for o in rungs[0][i0:]+rungs[1][i0:]: hide(o)
    set_splines(cM,[s['mrna']],-0.03)
    k=0
    for x,y,c in s['bases']:
        place_cyl(mb[k],(x,y-2),(x,y-15),basem[c],-0.03); k+=1
    for o in mb[k:]: hide(o)
    px,py,pop=s['poly']; polyO.location=(X(px),YC-0.07,Z(py)); polyO.scale=(pop,0.75*pop,0.85*pop)
    _,yl,ys,rop=s['ribo']; ribL.location=(X(360),YC+0.06,Z(yl)); ribL.scale=(P(95)*rop,0.09*rop+1e-4,P(55)*rop); ribS.location=(X(360),YC+0.03,Z(ys)); ribS.scale=(P(80)*rop,0.08*rop+1e-4,P(38)*rop)
    x,y,op=s['cap']; capO.location=(X(x),YC-0.05,Z(y)); sc3(capO,op)
    for o,(x,y,op) in zip(tailO,s['tail']): o.location=(X(x),YC-0.04,Z(y)); sc3(o,op)
    for n_,(r,b) in enumerate(trn):
        if n_<len(s['trna']):
            x,y,op,kk=s['trna'][n_]; r.location=(X(x),YC-0.14,Z(y)); sc3(r,op); b.material_slots[0].material=aam[kk]
        else: hide(r)
    for o in beadO: hide(o)
    for x,y,j in s['beads']: beadO[j].location=(X(x),YC-0.12,Z(y)); beadO[j].scale=(1,1,1); emis(aam[j],1.2*s['glow'])
    place_mascot(mr,me,s['masc'],ydepth=-0.12)
    render(sc,f'{OUT}/f{f:04d}.png'); n+=1
print('sec/frame',(time.time()-t0)/max(n,1))
