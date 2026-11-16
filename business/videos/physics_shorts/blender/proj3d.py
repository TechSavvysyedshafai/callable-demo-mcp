import bpy, math, json, time, sys, os
from mathutils import Vector
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from blib import *
STATE,OUT,F0,F1,PCT,SAMP=args(); S=json.load(open(STATE))['states']
sc=setup(PCT,SAMP,bg=(0.93,0.90,0.85)); set_dof(sc,-0.06,float(os.environ.get('FSTOP','1.3')))
YC=-0.06
CB=['#e8803f','#d62828','#3b82c4','#2e9e6b','#8e5aa8','#2b2b2b']
def glow(name,col,strength=0.0):
    m=mat(name,col,0.5); b=m.node_tree.nodes['Principled BSDF']; b.inputs['Emission Color'].default_value=(*col,1); b.inputs['Emission Strength'].default_value=strength; return m
ballm=[mat('ball%d'%k,hexc(c),0.35,0.6) for k,c in enumerate(CB)]
dotm=[glow('dot%d'%k,hexc(c),0.6) for k,c in enumerate(CB)]
grass=mat('grass',hexc('#9ccc83'),0.9); soil=mat('soil',hexc('#c9a27a'),0.95); platm=mat('plat',hexc('#9aa7b5'),0.6,0.1)
basem=mat('base',hexc('#4a5a6a'),0.5,0.2); barm=mat('barrel',hexc('#6b7a8a'),0.4,0.4)
GY=820
box((P(1500),1.6,P(30)),(X(360),0.7,Z(GY+15)),grass,0)
box((P(1500),1.6,P(400)),(X(360),0.7,Z(GY+30+200)),soil,0)
plat=box((P(100),0.26,P(250)),(X(110),0.15,Z(GY-125)),platm,P(6))
hillm=mat('hill',hexc('#b7d6a3'),0.95)
for hx,hy,rx,ry in ((120,GY,420,150),(560,GY,520,120)):
    h=sphere(1,hillm,48); h.location=(X(hx),1.3,Z(hy)); h.scale=(P(rx),0.3,P(ry))
base=box((P(60),P(40),P(22)),(X(100),YC,Z(GY-11)),basem,P(4))
bpy.ops.mesh.primitive_cylinder_add(radius=P(9),depth=P(74),vertices=24); bar=bpy.context.object; bar.data.materials.append(barm)
bv=bar.modifiers.new('bv','BEVEL'); bv.width=P(3); bv.segments=3
balls=[sphere(P(14),ballm[0],32) for _ in range(5)]
dots=[sphere(P(5),dotm[0],12) for _ in range(60)]
mr,me=mascot()
def hide(o): o.scale=(0,0,0)
t0=time.time(); n=0
for f in range(F0,F1+1,int(os.environ.get('STEP','1'))):
    s=S[f]; z,cx,cy=s['view']; set_view(sc,z,cx,cy)
    plat.scale=(1,1,1) if s['plat']>0.5 else (0,0,0)
    bx,by,th,bop=s['bar']; a=math.radians(th)
    bar.location=(X(bx)+P(30)*math.cos(a),YC-0.01,Z(by)+P(30)*math.sin(a)); bar.rotation_euler=(0,math.radians(90-th),0); bar.scale=(bop,bop,bop); base.scale=(bop,bop,bop)
    for o in balls: hide(o)
    for o,(x,y,ci) in zip(balls,s['balls']): o.location=(X(x),YC-0.04,Z(y)); o.scale=(1,1,1); o.material_slots[0].material=ballm[ci]
    for o in dots: hide(o)
    for o,(x,y,ci) in zip(dots,s['dots']): o.location=(X(x),YC,Z(y)); o.scale=(1,1,1); o.material_slots[0].material=dotm[ci]
    place_mascot(mr,me,s['masc'],ydepth=-0.12)
    render(sc,f'{OUT}/f{f:04d}.png'); n+=1
print('sec/frame',(time.time()-t0)/max(n,1))
