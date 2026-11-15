import bpy, math, json, time, sys, os
from mathutils import Vector
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from blib import *
STATE,OUT,F0,F1,PCT,SAMP=args(); S=json.load(open(STATE))['states']
sc=setup(PCT,SAMP)
cyto=mat('cyto',hexc('#fbe3cc'),0.8,0.0); nucm=mat('nuc',hexc('#efc6a2'),0.45,0.35); nlm=mat('nl',hexc('#8e5a3a'),0.35,0.4)
cells=[sphere(1,cyto,96) for _ in range(2)]
nuc=sphere(1,nucm,48); nucl=sphere(P(28),nlm,24); nucl.location=(X(410),-0.17,Z(545))
def curve(pts,r,m,parent=None):
    cu=bpy.data.curves.new('c','CURVE'); cu.dimensions='3D'; cu.bevel_depth=r; cu.bevel_resolution=4; cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for b,(x,y) in zip(sp.bezier_points,pts): b.co=(x,0,y); b.handle_left_type=b.handle_right_type='AUTO'
    o=bpy.data.objects.new('cv',cu); sc.collection.objects.link(o); o.data.materials.append(m); o.parent=parent; return o
def squig(cx,cy,seed,col,scale=1.0):
    root=bpy.data.objects.new('sq',None); sc.collection.objects.link(root); root.location=(X(cx),-0.16,Z(cy))
    pts=[(P(-60+k*10)*scale, -P((math.sin(k*1.7+seed)*14) if k else 0)*scale) for k in range(13)]
    curve(pts,P(3.5)*max(scale,0.7),mat('sq'+col,hexc(col),0.35,0.5),root); return root
CH=[(300,540,1,'#e0663a'),(420,630,2,'#e8a07a'),(320,670,3,'#3b82c4'),(400,560,4,'#86b6e0')]
chromatin=[squig(*c) for c in CH]
dch=[]
for y in (430,770):
    for dx,dy,s,c in [(-40,-25,1,'#e0663a'),(30,-15,2,'#e8a07a'),(-30,25,3,'#3b82c4'),(35,22,4,'#86b6e0')]: dch.append(squig(360+dx,y+dy,s,c,0.55))
dnuc=[sphere(1,nucm,32) for _ in range(2)]
COL=[('#e0663a',96),('#e8a07a',96),('#3b82c4',68),('#86b6e0',68)]
white=mat('white',(0.9,0.9,0.9),0.3); black=mat('black',(0.01,0.01,0.01),0.1,1.0); dark=mat('dark',hexc('#2b2b2b'),0.3,0.5)
chroms=[]
for c,L in COL:
    m=mat('c'+c,hexc(c),0.35,0.5); sis=[]
    for j in range(2):
        root=bpy.data.objects.new('sis',None); sc.collection.objects.link(root)
        box((P(L),P(18),P(18)),(0,0,0),m,P(8.5),6,root)
        for ex in (-8,8):
            w=sphere(P(4.8),white,12); w.parent=root; w.location=(P(ex),-P(9),P(1))
            b=sphere(P(2.4),black,10); b.parent=root; b.location=(P(ex),-P(13.2),P(0))
        sis.append(root)
    cm=sphere(P(7),dark,16); chroms.append((sis,cm))
fibm=mat('fib',hexc('#7d8a99'),0.3,0.3)
fibs=[]
for _ in range(8):
    bpy.ops.mesh.primitive_cylinder_add(radius=P(2),depth=1,vertices=8); o=bpy.context.object; o.data.materials.append(fibm); fibs.append(o)
cm_=mat('cent',hexc('#5b6b7d'),0.3,0.5); cents=[]
for _ in range(2):
    r=bpy.data.objects.new('cent',None); sc.collection.objects.link(r)
    box((P(28),P(12),P(10)),(0,0,0),cm_,P(3),parent=r); box((P(10),P(12),P(28)),(0,0,0),cm_,P(3),parent=r); cents.append(r)
mr,me=mascot()
def sc3(o,k): k=max(0.0,min(1.0,k)); o.scale=(k,k,k)
t0=time.time(); n=0
for f in range(F0,F1+1,int(os.environ.get('STEP','1'))):
    s=S[f]
    for i,(o,(cx,cy,rx,ry)) in enumerate(zip(cells,s['cells'])): o.location=(X(cx),0.012*i,Z(cy)); o.scale=(P(rx),0.10,P(ry))
    nuc.location=(X(360),-0.07,Z(600)); k=s['nuc']; nuc.scale=(P(175)*k,0.06*k+1e-4,P(175)*k); sc3(nucl,s['nuc'])
    for o in chromatin: sc3(o,s['chromatin'])
    for o in dch: sc3(o,s['dn'])
    for o,y in zip(dnuc,(430,770)): o.location=(X(360),-0.07,Z(y)); k=s['dn']; o.scale=(P(95)*k,0.05*k+1e-4,P(95)*k)
    for (sis,cm),st in zip(chroms,s['chroms']):
        for root,tr in zip(sis,st['sis']):
            x,y,r,scl=tr; k=scl*st['op']; root.location=(X(x),-0.19,Z(y)); root.rotation_euler=(0,math.radians(r),0); root.scale=(k,k,k)
        cx,cy,op=st['cm']; cm.location=(X(cx),-0.2,Z(cy)); sc3(cm,op*st['op'])
    for o,(x1,y1,x2,y2,op) in zip(fibs,s['fib']):
        a=Vector((X(x1),-0.18,Z(y1))); b=Vector((X(x2),-0.18,Z(y2))); d=b-a
        o.location=(a+b)/2; o.rotation_mode='QUATERNION'; o.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized() if d.length>1e-6 else Vector((0,0,1)))
        o.scale=(1,1,d.length) if op>0.02 else (0,0,0)
    for o,(x,y,op) in zip(cents,s['cent']): o.location=(X(x),-0.19,Z(y)); sc3(o,op)
    place_mascot(mr,me,s['masc'],ydepth=-0.35)
    render(sc,f'{OUT}/f{f:04d}.png'); n+=1
print('sec/frame',(time.time()-t0)/max(n,1))
