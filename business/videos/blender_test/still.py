import bpy, math, time, sys
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.device='CPU'
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.cycles.samples=48; sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.03
sc.cycles.use_denoising=True; sc.cycles.denoiser='OPENIMAGEDENOISE'
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'
sc.render.image_settings.file_format='PNG'
def mat(name,col,rough,coat=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*col,1); b.inputs['Roughness'].default_value=rough
    try: b.inputs['Coat Weight'].default_value=coat
    except Exception: pass
    return m
def box(name,loc,size,m,bevel=0.0006):
    bpy.ops.mesh.primitive_cube_add(location=loc); o=bpy.context.object; o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2); bpy.ops.object.transform_apply(scale=True)
    bv=o.modifiers.new('bv','BEVEL'); bv.width=bevel; bv.segments=3
    o.data.materials.append(m); return o
orange=mat('orange',(0.80,0.20,0.06),0.45,0.25); eye=mat('eye',(0.01,0.01,0.01),0.08,1.0)
teal=mat('teal',(0.05,0.55,0.55),0.4,0.3); wood=mat('wood',(0.45,0.28,0.14),0.6)
# real-size toy, metres: 67 x 35 x 22 mm
box('body',(0,0,0.0225),(0.067,0.022,0.035),orange)
box('armL',(-0.0405,0,0.021),(0.014,0.012,0.012),orange); box('armR',(0.0405,0,0.021),(0.014,0.012,0.012),orange)
for x in (-0.024,-0.008,0.008,0.024): box('leg',(x,0,0.0035),(0.010,0.012,0.007),orange)
box('eyeL',(-0.012,-0.0112,0.026),(0.006,0.001,0.009),eye); box('eyeR',(0.012,-0.0112,0.026),(0.006,0.001,0.009),eye)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0125,location=(0.075,-0.01,0.0125)); p=bpy.context.object; p.data.materials.append(teal)
for f in p.data.polygons: f.use_smooth=True
bpy.ops.mesh.primitive_plane_add(size=1.0,location=(0,0,0)); fl=bpy.context.object; fl.data.materials.append(wood)
# wood stripes procedurally
nt=wood.node_tree; b=nt.nodes['Principled BSDF']
tc=nt.nodes.new('ShaderNodeTexCoord'); mp=nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value=(60,3,1)
wv=nt.nodes.new('ShaderNodeTexWave'); wv.wave_type='BANDS'; wv.inputs['Scale'].default_value=1; wv.inputs['Distortion'].default_value=4
cr=nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color=(0.30,0.17,0.08,1); cr.color_ramp.elements[1].color=(0.55,0.35,0.18,1)
nt.links.new(tc.outputs['Object'],mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'],wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'],cr.inputs['Fac']); nt.links.new(cr.outputs['Color'],b.inputs['Base Color'])
# light: one key through a window-ish area + sky fill
bpy.ops.object.light_add(type='SUN',location=(0,0,1)); s=bpy.context.object; s.data.energy=3.0; s.data.angle=math.radians(1.2)
s.rotation_euler=(math.radians(55),math.radians(10),math.radians(-35))
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(0.55,0.65,0.8,1); bg.inputs['Strength'].default_value=0.35
# camera low, DOF on the eyes
cd=bpy.data.cameras.new('c'); cam=bpy.data.objects.new('cam',cd); sc.collection.objects.link(cam); sc.camera=cam
cd.sensor_width=36; cd.lens=50; cd.dof.use_dof=True; cd.dof.aperture_fstop=2.8
cam.location=(0.07,-0.20,0.035); tgt=Vector((0.0,0,0.026)); d=tgt-cam.location
cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); cd.dof.focus_distance=d.length
t=time.time(); sc.render.filepath=sys.argv[-1]; bpy.ops.render.render(write_still=True); print('render seconds',round(time.time()-t,1))
