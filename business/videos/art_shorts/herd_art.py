# Original 15 s Blender piece: three stylised horses draw themselves, then drift. Not a copy of any real artwork.
import bpy, math, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blib import *
a=sys.argv[sys.argv.index('--')+1:]; OUT=a[0]; F0,F1,PCT,SAMP=map(int,a[1:5]); STEP=int(os.environ.get('STEP','2'))
N=360
sc=setup(PCT,SAMP); sc.frame_start=0; sc.frame_end=N-1
m=bpy.data.materials['back']; nt=m.node_tree; b=nt.nodes['Principled BSDF']
n=nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=55; n.inputs['Detail'].default_value=10
r=nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color=(*hexc('#d79a45'),1); r.color_ramp.elements[1].color=(*hexc('#e8bd74'),1)
nt.links.new(n.outputs['Fac'],r.inputs['Fac']); nt.links.new(r.outputs['Color'],b.inputs['Base Color'])
black=mat('ink',hexc('#14110f'),0.55,0.0); red=mat('red',hexc('#b8262b'),0.6,0.0); blue=mat('blue',hexc('#1f3f7a'),0.6,0.0); white=mat('white',hexc('#f3ead7'),0.6,0.0); saffron=mat('saf',hexc('#e07b1a'),0.6,0.0)
CX,CY=420,555   # horse design centre
def draw(cu,f0,f1):
    cu.bevel_factor_end=0.0; cu.keyframe_insert('bevel_factor_end',frame=f0-1); cu.bevel_factor_end=1.0; cu.keyframe_insert('bevel_factor_end',frame=f1)
def hstroke(parent,pts,depth,m,f0,f1):
    cu=bpy.data.curves.new('s','CURVE'); cu.dimensions='3D'; cu.resolution_u=14; cu.bevel_depth=P(depth); cu.bevel_resolution=4; cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for bp,(x,y) in zip(sp.bezier_points,pts): bp.co=((x-CX)/360,0,-(y-CY)/360); bp.handle_left_type=bp.handle_right_type='AUTO'
    o=bpy.data.objects.new('s',cu); sc.collection.objects.link(o); o.data.materials.append(m); o.parent=parent; draw(cu,f0,f1); return o
def pop(o,f0,f1):
    s=tuple(o.scale); o.scale=(0,0,0); o.keyframe_insert('scale',frame=f0-1); o.scale=s; o.keyframe_insert('scale',frame=f1)
def horse(px,py,s,mirror,rot,t0,amp,phase,y=-0.05):
    e=bpy.data.objects.new('h',None); sc.collection.objects.link(e); e.location=(X(px),y,Z(py)); e.scale=((-s if mirror else s),s,s); e.rotation_euler=(0,math.radians(rot),0)
    bz=e.location.z; br=math.radians(rot)
    k=lambda f0: t0+f0
    hstroke(e,[(235,370),(250,430),(275,520),(300,600),(340,650),(420,670),(500,655),(565,615)],11,black,k(8),k(46))
    hstroke(e,[(262,248),(250,282),(205,306),(150,346),(160,368),(205,386),(240,372)],10,black,k(6),k(34))
    hstroke(e,[(250,282),(300,330),(335,420),(385,500),(470,512),(550,505),(602,545),(610,600)],12,black,k(22),k(60))
    hstroke(e,[(322,612),(272,662),(215,650),(186,692)],8,black,k(40),k(62))
    hstroke(e,[(352,640),(330,705),(282,735),(252,780)],8,black,k(46),k(68))
    hstroke(e,[(568,640),(600,720),(592,800),(572,860)],8,black,k(52),k(74))
    hstroke(e,[(520,655),(502,745),(452,792),(430,850)],8,black,k(56),k(78))
    hstroke(e,[(610,555),(668,540),(692,470),(672,405),(640,372)],7,black,k(60),k(84))
    for i,(p,q) in enumerate([((300,330),(332,314)),((318,372),(354,362)),((335,420),(374,418))]): hstroke(e,[p,q],6,black,k(66+i*4),k(76+i*4))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=P(9)); ey=bpy.context.object; ey.data.materials.append(black); ey.parent=e; ey.location=((215-CX)/360,-0.02,-(322-CY)/360); pop(ey,k(46),k(54))
    # idle drift after drawn: gentle bob and sway
    for f in range(t0+90,N,24):
        ph=phase+(f-t0)/24*math.pi
        e.location.z=bz+P(amp)*math.sin(ph); e.keyframe_insert('location',index=2,frame=f)
        e.rotation_euler[1]=br+math.radians(1.6)*math.sin(ph+1.2); e.keyframe_insert('rotation_euler',index=1,frame=f)
    return e
def disc(px,py,rad,m,f0,f1,y=0.05):
    bpy.ops.mesh.primitive_cylinder_add(radius=P(rad),depth=0.02,vertices=96,location=(X(px),y,Z(py)),rotation=(math.radians(90),0,0)); o=bpy.context.object; o.data.materials.append(m); pop(o,f0,f1); return o
def block(px,py,w,h,m,f0,f1,y=0.1):
    bpy.ops.mesh.primitive_cube_add(location=(X(px),y,Z(py))); o=bpy.context.object; o.scale=(P(w)/2,0.01,P(h)/2); o.data.materials.append(m); pop(o,f0,f1); return o
# colour fields behind the horses
block(500,885,190,250,blue,150,190)
block(190,930,150,150,saffron,240,275)
# sun rises from the bottom of the sky
sun=disc(470,230,105,red,0,2); sun.scale=(1,1,1)
sun.location.z=Z(430); sun.keyframe_insert('location',index=2,frame=0); sun.location.z=Z(230); sun.keyframe_insert('location',index=2,frame=70)
disc(555,185,48,white,250,285,y=0.03)
# three horses
horse(340,470,0.80,False,0,24,6,0.0)
horse(480,885,0.55,True,-3,120,5,1.6)
horse(190,930,0.38,False,4,210,4,3.1)
# river and ground
def line(pts,depth,m,f0,f1,y=-0.03):
    cu=bpy.data.curves.new('l','CURVE'); cu.dimensions='3D'; cu.resolution_u=14; cu.bevel_depth=P(depth); cu.bevel_resolution=4; cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for bp,(x,yy) in zip(sp.bezier_points,pts): bp.co=(X(x),y,Z(yy)); bp.handle_left_type=bp.handle_right_type='AUTO'
    o=bpy.data.objects.new('l',cu); sc.collection.objects.link(o); o.data.materials.append(m); draw(cu,f0,f1)
line([(60,1092),(220,1070),(390,1098),(560,1072),(670,1090)],16,blue,270,320)
line([(110,1130),(300,1114),(470,1134),(640,1118)],9,black,295,335)
cam=sc.camera.data; cam.ortho_scale=1280/360; cam.keyframe_insert('ortho_scale',frame=0); cam.ortho_scale=1280/360*0.92; cam.keyframe_insert('ortho_scale',frame=N-1)
t0=time.time(); n_=0
for f in range(F0,F1+1,STEP):
    sc.frame_set(f); render(sc,f'{OUT}/f{f:04d}.png'); n_+=1
print('sec/frame',(time.time()-t0)/max(n_,1))
