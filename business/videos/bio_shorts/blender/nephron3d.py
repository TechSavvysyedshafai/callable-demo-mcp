import bpy, math, json, time, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from blib import *
STATE,OUT,F0,F1,PCT,SAMP=args(); S=json.load(open(STATE))['states']; G=S[0]['geo']
sc=setup(PCT,SAMP)
def tube(pts,r,m,ydepth=0.0):
    cu=bpy.data.curves.new('c','CURVE'); cu.dimensions='3D'; cu.bevel_depth=r; cu.bevel_resolution=6; cu.use_fill_caps=True
    sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p,(x,y) in zip(sp.points,pts): p.co=(X(x),ydepth,Z(y),1)
    o=bpy.data.objects.new('t',cu); sc.collection.objects.link(o); o.data.materials.append(m); return o
cream=mat('cream',hexc('#f3d98f'),0.35,0.3,0.15); red=mat('red',hexc('#c0392b'),0.3,0.5); cap=mat('cap',hexc('#b8935a'),0.4,0.3)
tube(G['tube'],P(15),cream); tube(G['aff'],P(9),red); tube(G['eff'],P(7),red); tube(G['cap'],P(7),cap)
glo=mat('glo',hexc('#e06b5e'),0.3,0.6,0.1)
for x,y in [(185,312),(205,334),(180,348),(200,312),(214,318),(188,330)]:
    o=sphere(P(16),glo); o.location=(X(x),-0.02,Z(y))
water=mat('water',hexc('#4a90d9'),0.08,1.0)
drop=sphere(1,water,32); filt=[sphere(P(6),water,12) for _ in range(8)]
mr,me=mascot()
t0=time.time(); n=0
for f in range(F0,F1+1,int(os.environ.get('STEP','1'))):
    s=S[f]; x,y,r=s['drop']; rr=P(r)
    drop.location=(X(x),-0.06-rr*0.5,Z(y)); drop.scale=(rr,rr,rr*1.08)
    for o,(fx,fy,op) in zip(filt,s['filt']): o.location=(X(fx),-0.06,Z(fy)); k=max(0,min(1,op)); o.scale=(k,k,k)
    place_mascot(mr,me,s['masc'],ydepth=-0.12)
    render(sc,f'{OUT}/f{f:04d}.png'); n+=1
print('sec/frame',(time.time()-t0)/max(n,1))
