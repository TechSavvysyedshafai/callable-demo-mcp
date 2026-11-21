# Original Blender piece "in the spirit of" Indian modernist horse paintings. Not a copy of any real work.
import bpy, math, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blib import *
a=sys.argv[sys.argv.index('--')+1:]; OUT=a[0]; F0,F1,PCT,SAMP=map(int,a[1:5]); STEP=int(os.environ.get('STEP','2'))
sc=setup(PCT,SAMP); sc.frame_start=0; sc.frame_end=143
# warm paper background with grain
m=bpy.data.materials['back']; nt=m.node_tree; b=nt.nodes['Principled BSDF']
n=nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=55; n.inputs['Detail'].default_value=10
r=nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color=(*hexc('#d79a45'),1); r.color_ramp.elements[1].color=(*hexc('#e8bd74'),1)
nt.links.new(n.outputs['Fac'],r.inputs['Fac']); nt.links.new(r.outputs['Color'],b.inputs['Base Color'])
black=mat('ink',hexc('#14110f'),0.55,0.0); red=mat('red',hexc('#b8262b'),0.6,0.0); blue=mat('blue',hexc('#1f3f7a'),0.6,0.0); white=mat('white',hexc('#f3ead7'),0.6,0.0)
def stroke(pts,depth,m,f0,f1,y=-0.05):
    cu=bpy.data.curves.new('s','CURVE'); cu.dimensions='3D'; cu.resolution_u=14; cu.bevel_depth=P(depth); cu.bevel_resolution=4; cu.use_fill_caps=True
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
    for bp,(x,yy) in zip(sp.bezier_points,pts): bp.co=(X(x),y,Z(yy)); bp.handle_left_type=bp.handle_right_type='AUTO'
    o=bpy.data.objects.new('s',cu); sc.collection.objects.link(o); o.data.materials.append(m)
    cu.bevel_factor_end=0.0; cu.keyframe_insert('bevel_factor_end',frame=f0-1)
    cu.bevel_factor_end=1.0; cu.keyframe_insert('bevel_factor_end',frame=f1)
    return o
def pop(o,f0,f1):
    o.scale=(0,0,0); o.keyframe_insert('scale',frame=f0-1); o.scale=(1,1,1); o.keyframe_insert('scale',frame=f1)
# sun
bpy.ops.mesh.primitive_cylinder_add(radius=P(105),depth=0.02,vertices=96,location=(X(470),0.05,Z(250)),rotation=(math.radians(90),0,0)); sun=bpy.context.object; sun.data.materials.append(red); pop(sun,64,92)
bpy.ops.mesh.primitive_cylinder_add(radius=P(52),depth=0.02,vertices=64,location=(X(525),0.04,Z(222)),rotation=(math.radians(90),0,0)); sun2=bpy.context.object; sun2.data.materials.append(white); pop(sun2,76,100)
# horse
stroke([(235,370),(250,430),(275,520),(300,600),(340,650),(420,670),(500,655),(565,615)],11,black,8,46)
stroke([(262,248),(250,282),(205,306),(150,346),(160,368),(205,386),(240,372)],10,black,6,34)
stroke([(250,282),(300,330),(335,420),(385,500),(470,512),(550,505),(602,545),(610,600)],12,black,22,60)
stroke([(322,612),(272,662),(215,650),(186,692)],8,black,40,62)
stroke([(352,640),(330,705),(282,735),(252,780)],8,black,46,68)
stroke([(568,640),(600,720),(592,800),(572,860)],8,black,52,74)
stroke([(520,655),(502,745),(452,792),(430,850)],8,black,56,78)
stroke([(610,555),(668,540),(692,470),(672,405),(640,372)],7,black,60,84)
for k,(p,q) in enumerate([((300,330),(332,314)),((318,372),(354,362)),((335,420),(374,418))]): stroke([p,q],6,black,66+k*4,76+k*4)
bpy.ops.mesh.primitive_uv_sphere_add(radius=P(9),location=(X(215),-0.07,Z(322))); eye=bpy.context.object; eye.data.materials.append(black); pop(eye,46,54)
# ground / water
stroke([(80,905),(240,884),(400,910),(560,888),(660,904)],17,blue,84,116,y=-0.03)
stroke([(120,945),(300,930),(470,950),(620,934)],10,black,100,128,y=-0.03)
# slow push-in
cam=sc.camera.data; cam.ortho_scale=1280/360; cam.keyframe_insert('ortho_scale',frame=0); cam.ortho_scale=1280/360*0.9; cam.keyframe_insert('ortho_scale',frame=143)
t0=time.time(); n_=0
for f in range(F0,F1+1,STEP):
    sc.frame_set(f); render(sc,f'{OUT}/f{f:04d}.png'); n_+=1
print('sec/frame',(time.time()-t0)/max(n_,1))
