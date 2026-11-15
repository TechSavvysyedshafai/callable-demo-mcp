import bpy, math, json, time, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from blib import *
STATE,OUT,F0,F1,PCT,SAMP=args(); S=json.load(open(STATE))['states']
sc=setup(PCT,SAMP)
RB=mat('rb',hexc('#9db6ee'),0.55,0.15,0.1); LB=mat('lb',hexc('#f0a19a'),0.55,0.15,0.1)
RS=mat('rs',hexc('#3f63b8'),0.25,0.6); LS=mat('ls',hexc('#c0392b'),0.25,0.6)
D=0.30
ch={'RA':tray(150,300,190,170,D,RB),'LA':tray(380,300,190,170,D,LB),'RV':tray(150,500,190,270,D,RB),'LV':tray(380,500,190,270,D,LB)}
tray(100,250,40,360,D*0.8,RB); tray(580,250,40,360,D*0.8,LB)
box((P(30),D*0.8,P(50)),(X(150),0,Z(585)),RB,0.01); box((P(30),D*0.8,P(50)),(X(570),0,Z(585)),LB,0.01)
def flap(m,length,thick=9):
    piv=bpy.data.objects.new('piv',None); sc.collection.objects.link(piv)
    box((P(length),D*0.9,P(thick)),(P(length/2),0,0),m,P(3),parent=piv); return piv
av=[(178,1,RS),(312,-1,RS),(408,1,LS),(542,-1,LS)]; av=[(x,d,flap(m,62)) for x,d,m in av]
sl=[(100,1,RS),(140,-1,RS),(580,1,LS),(620,-1,LS)]; sl=[(x,d,flap(m,22,7)) for x,d,m in sl]
for x,d,p in av: p.location=(X(x),-0.02,Z(485)); p.scale=(d,1,1)
for x,d,p in sl: p.location=(X(x),-0.02,Z(540)); p.scale=(d,1,1)
blood=[mat('bR',hexc('#2f4fa8'),0.15,1.0),mat('bL',hexc('#b3261e'),0.15,1.0)]
dots=[sphere(P(9),blood[k%2==1 and 1 or 0],16) for k in range(48)]
for k,o in enumerate(dots): o.data.materials[0]=blood[1 if k%6 in (1,3,5) else 0]
mr,me=mascot()
t0=time.time()
for f in range(F0,F1+1,int(os.environ.get("STEP","1"))):
    s=S[f]
    for k,n in enumerate(('RA','LA','RV','LV')):
        q=s['sq'][k]; ch[n].scale=(1-0.12*q,1,1-0.10*q)
    for x,d,p in av: p.rotation_euler=(0,d*s['avO']*1.25,0)
    for x,d,p in sl: p.rotation_euler=(0,-d*s['slO']*1.3,0)
    for o,(x,y,c,op) in zip(dots,s['dots']):
        o.location=(X(x),-0.17,Z(y)); r=max(0,min(1,op)); o.scale=(r,r,r)
    place_mascot(mr,me,s['masc'])
    render(sc,f'{OUT}/f{f:04d}.png')
print('sec/frame',(time.time()-t0)/(F1-F0+1))
