# Shared Blender helpers. Screen pixels (720x1280 layout) map 1:1 onto an orthographic camera.
import bpy, math, sys, json
from mathutils import Vector
def args():
    a=sys.argv[sys.argv.index('--')+1:]; return a[0],a[1],int(a[2]),int(a[3]),int(a[4]),int(a[5])  # state,out,f0,f1,pct,samples
def X(x): return (x-360)/360
def Z(y): return (640-y)/360
def P(px): return px/360
def setup(pct,samples,bg=(0.92,0.88,0.82)):
    bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.render.resolution_x,sc.render.resolution_y=720,1280; sc.render.resolution_percentage=pct
    sc.cycles.samples=samples; sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.1
    sc.cycles.use_denoising=True; sc.cycles.denoiser='OPENIMAGEDENOISE'; sc.cycles.max_bounces=4; sc.render.use_persistent_data=True
    sc.view_settings.view_transform='Standard'; sc.render.image_settings.file_format='PNG'
    cd=bpy.data.cameras.new('c'); cd.type='ORTHO'; cd.ortho_scale=1280/360; cam=bpy.data.objects.new('cam',cd); sc.collection.objects.link(cam); sc.camera=cam
    cam.location=(0,-5,0); cam.rotation_euler=(math.radians(90),0,0)
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; b=w.node_tree.nodes['Background']; b.inputs['Color'].default_value=(1,0.97,0.92,1); b.inputs['Strength'].default_value=0.25
    m=mat('back',bg,0.95); bpy.ops.mesh.primitive_plane_add(size=12,location=(0,0.32,0),rotation=(math.radians(90),0,0)); bpy.context.object.data.materials.append(m)
    bpy.ops.object.light_add(type='AREA',location=(-2.2,-3.0,3.0)); k=bpy.context.object; k.data.energy=260; k.data.size=3.0
    k.rotation_euler=(math.radians(50),0,math.radians(-35))
    bpy.ops.object.light_add(type='AREA',location=(2.5,-3,-0.5)); f=bpy.context.object; f.data.energy=70; f.data.size=3; f.rotation_euler=(math.radians(95),0,math.radians(40))
    return sc
def mat(name,col,rough=0.5,coat=0.0,sss=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*col,1); b.inputs['Roughness'].default_value=rough; b.inputs['Coat Weight'].default_value=coat
    if sss: b.inputs['Subsurface Weight'].default_value=sss; b.inputs['Subsurface Radius'].default_value=(0.05,0.02,0.02)
    return m
def hexc(h):
    h=h.lstrip('#'); c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(((v+0.055)/1.055)**2.4 if v>0.04045 else v/12.92 for v in c)
def box(size,loc=(0,0,0),m=None,bevel=0.01,seg=3,parent=None,name='box'):
    bpy.ops.mesh.primitive_cube_add(location=(0,0,0)); o=bpy.context.object; o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2); bpy.ops.object.transform_apply(scale=True)
    if bevel: bv=o.modifiers.new('bv','BEVEL'); bv.width=bevel; bv.segments=seg
    if m: o.data.materials.append(m)
    o.parent=parent; o.location=loc; return o
def tray(x,y,w,h,depth,m,wall=0.035,r=0.08,name='tray'):
    """Open-fronted rounded box from a screen rect; origin at its centre."""
    o=box((P(w),depth,P(h)),(0,0,0),m,0,name=name)
    inner=box((P(w)-2*wall,depth,P(h)-2*wall),(0,-wall*1.2,0),None,0,name=name+'_cut'); inner.hide_render=True; inner.hide_viewport=True
    bo=o.modifiers.new('cut','BOOLEAN'); bo.operation='DIFFERENCE'; bo.object=inner; bo.solver='EXACT'
    bv=o.modifiers.new('bv','BEVEL'); bv.width=min(r,0.02); bv.segments=3; bv.limit_method='ANGLE'
    bpy.context.view_layer.objects.active=o
    for mod in ('cut','bv'): bpy.ops.object.modifier_apply(modifier=mod)
    bpy.data.objects.remove(inner)
    for f in o.data.polygons: f.use_smooth=True
    o.location=(X(x+w/2),0,Z(y+h/2)); return o
def sphere(r,m,seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r,segments=seg,ring_count=seg//2); o=bpy.context.object; o.data.materials.append(m)
    for f in o.data.polygons: f.use_smooth=True
    return o
def mascot(scale_px=1.0):
    """Orange block toy built in screen pixels (body 120x70 px at scale 1)."""
    root=bpy.data.objects.new('masc',None); bpy.context.scene.collection.objects.link(root)
    o=mat('orange',hexc('#e8803f'),0.45,0.3); d=mat('orange2',hexc('#c9652a'),0.5,0.2); e=mat('eye',(0.01,0.01,0.01),0.1,1.0)
    box((P(120),P(60),P(70)),(0,0,0),o,P(7),parent=root)
    for x in (-68,68): box((P(20),P(40),P(18)),(P(x),0,P(-1)),d,P(3),parent=root)
    for x in (-38,-13,12,37): box((P(16),P(40),P(12)),(P(x),0,P(-41)),d,P(3),parent=root)
    eyes=bpy.data.objects.new('eyes',None); bpy.context.scene.collection.objects.link(eyes); eyes.parent=root; eyes.location=(0,-P(31),P(6))
    for x in (-19,19): box((P(10),P(4),P(20)),(P(x),0,0),e,P(2),parent=eyes)
    root['eyes']=eyes.name; return root,eyes
def place_mascot(root,eyes,st,ydepth=-0.32):
    x,y,s,op,b=st
    root.location=(X(x),ydepth,Z(y)); root.scale=(s,s,s) if op>0.5 else (0,0,0); eyes.scale=(1,1,b)
def render(sc,path): sc.render.filepath=path; bpy.ops.render.render(write_still=True)
