import bpy, math, json, time, sys, os
from mathutils import Vector
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from blib import *
STATE,OUT,F0,F1,PCT,SAMP=args(); S=json.load(open(STATE))['states']
sc=setup(PCT,SAMP)
YC=-0.06                                   # depth of the DNA axis (world y); negative = toward the camera
def W(p): return (X(p[0]),YC-P(p[2]) if len(p)>2 else YC,Z(p[1]))
oldm=mat('old',hexc('#3b4a5c'),0.45,0.25); newm=mat('new',hexc('#e8803f'),0.4,0.35)
basem=[mat('b'+c,hexc(c),0.4,0.3) for c in ('#e0663a','#3b82c4','#2e9e6b','#e6b422')]
helim=mat('heli',hexc('#3b82c4'),0.35,0.5); polym=mat('poly',hexc('#2e9e6b'),0.35,0.5)
def glow(name,col,strength):
    m=mat(name,col,0.5); b=m.node_tree.nodes['Principled BSDF']; b.inputs['Emission Color'].default_value=(*col,1); b.inputs['Emission Strength'].default_value=strength; return m
ligm=glow('lig',hexc('#b07ad0'),2.0); orim=glow('ori',hexc('#f1c232'),2.5)
def curve(name,m,r):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.bevel_depth=r; cu.bevel_resolution=3; cu.resolution_u=4; cu.use_fill_caps=True
    o=bpy.data.objects.new(name,cu); sc.collection.objects.link(o); o.data.materials.append(m); return o
def set_splines(o,lines):
    cu=o.data; cu.splines.clear()
    for pts in lines:
        if len(pts)<2: continue
        sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
        for b,p in zip(sp.bezier_points,pts): b.co=W(p); b.handle_left_type=b.handle_right_type='AUTO'
RB=P(5.5)
cA=curve('pA',oldm,RB); cB=curve('pB',oldm,RB); cO=[curve('oL',oldm,RB),curve('oR',oldm,RB)]; cN=[curve('nL',newm,RB),curve('nR',newm,RB)]
# rung pools: cylinders from a backbone point to the axis, coloured by base
def cyl(): bpy.ops.mesh.primitive_cylinder_add(radius=P(4.6),depth=1,vertices=10); o=bpy.context.object; o.data.materials.append(basem[0]); o.rotation_mode='QUATERNION'; return o
POOL=90; halves=[[cyl() for _ in range(POOL)] for _ in range(2)]
def place_cyl(o,a,b,m):
    va,vb=Vector(W(a)),Vector(W(b)); d=vb-va
    o.location=(va+vb)/2; o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized()); o.scale=(1,1,d.length); o.material_slots[0].material=m
def hide(o): o.scale=(0,0,0)
heli=sphere(P(31),helim,32); heli.scale=(1,0.55,1)
polys=[sphere(P(20),polym,24) for _ in range(2)]
ligs=[sphere(P(10),ligm,16) for _ in range(6)]
ori=sphere(P(15),orim,20)
mr,me=mascot()
def sc3(o,k,base=1.0): k=max(0.0,min(1.0,k))*base; o.scale=(k,k,k)
t0=time.time(); n=0
for f in range(F0,F1+1,int(os.environ.get('STEP','1'))):
    s=S[f]
    set_splines(cA,[s['pA']]); set_splines(cB,[s['pB']])
    for k in range(2): set_splines(cO[k],[s['arms'][k]['old']]); set_splines(cN[k],s['arms'][k]['nw'])
    r=s['rungs']; i0=i1=0
    for ax,ay,ad,mx,my,bx,by,bd,ca,cb,has in r:
        if i0<POOL: place_cyl(halves[0][i0],(ax,ay,ad),(mx,my,0),basem[ca]); i0+=1
        if has and i1<POOL: place_cyl(halves[1][i1],(mx,my,0),(bx,by,bd),basem[cb]); i1+=1
    for o in halves[0][i0:]: hide(o)
    for o in halves[1][i1:]: hide(o)
    hx,hy,hop=s['heli']; heli.location=(X(hx),YC-0.02,Z(hy)); k=max(0,min(1,hop)); heli.scale=(k,0.55*k,k)
    for o,(x,y,op) in zip(polys,s['poly']): o.location=(X(x),YC-0.07,Z(y)); sc3(o,op)
    for o,(x,y,op) in zip(ligs,s['lig']): o.location=(X(x),YC-0.08,Z(y)); sc3(o,op)
    ox,oy,oop=s['origin']; ori.location=(X(ox),YC-0.05,Z(oy)); sc3(ori,oop)
    place_mascot(mr,me,s['masc'],ydepth=-0.30)
    render(sc,f'{OUT}/f{f:04d}.png'); n+=1
print('sec/frame',(time.time()-t0)/max(n,1))
