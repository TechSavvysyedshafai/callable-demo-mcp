import bpy, math
def _new(N,*names):
    err=None
    for nm in names:
        try: return N.new(nm)
        except Exception as e: err=e
    raise err
def sock(ng,name,typ,io='INPUT'): return ng.interface.new_socket(name,in_out=io,socket_type=typ)
def ids(ng): return {s.name:s.identifier for s in ng.interface.items_tree if s.in_out=='INPUT'}
def kf(mod,ident,frame,value):
    mod[ident]=value; mod.keyframe_insert(f'["{ident}"]',frame=frame)
def ring_group(mat):
    """Petals on a circle. Inputs: Count, Radius, Size, Twist, Len."""
    ng=bpy.data.node_groups.new('Ring','GeometryNodeTree')
    sock(ng,'Geometry','NodeSocketGeometry'); sock(ng,'Count','NodeSocketInt'); sock(ng,'Radius','NodeSocketFloat'); sock(ng,'Size','NodeSocketFloat'); sock(ng,'Twist','NodeSocketFloat'); sock(ng,'Len','NodeSocketFloat')
    sock(ng,'Geometry','NodeSocketGeometry','OUTPUT')
    N=ng.nodes; L=ng.links; gi=N.new('NodeGroupInput'); go=N.new('NodeGroupOutput')
    circ=N.new('GeometryNodeMeshCircle'); ico=N.new('GeometryNodeMeshIcoSphere'); tf=N.new('GeometryNodeTransform'); inst=N.new('GeometryNodeInstanceOnPoints'); sm=N.new('GeometryNodeSetMaterial')
    idx=N.new('GeometryNodeInputIndex'); div=_new(N,'ShaderNodeMath'); mul=_new(N,'ShaderNodeMath'); add=_new(N,'ShaderNodeMath')
    cz=_new(N,'ShaderNodeCombineXYZ','FunctionNodeCombineXYZ'); cs=_new(N,'ShaderNodeCombineXYZ','FunctionNodeCombineXYZ'); cl=_new(N,'ShaderNodeCombineXYZ','FunctionNodeCombineXYZ')
    div.operation='DIVIDE'; mul.operation='MULTIPLY'; mul.inputs[1].default_value=2*math.pi; add.operation='ADD'
    ico.inputs['Radius'].default_value=1.0; ico.inputs['Subdivisions'].default_value=2
    cl.inputs['Y'].default_value=0.42; cl.inputs['Z'].default_value=0.14
    sm.inputs['Material'].default_value=mat
    lk=lambda a,b: L.new(a,b)
    lk(gi.outputs['Count'],circ.inputs['Vertices']); lk(gi.outputs['Radius'],circ.inputs['Radius'])
    lk(idx.outputs[0],div.inputs[0]); lk(gi.outputs['Count'],div.inputs[1]); lk(div.outputs[0],mul.inputs[0]); lk(mul.outputs[0],add.inputs[0]); lk(gi.outputs['Twist'],add.inputs[1]); lk(add.outputs[0],cz.inputs['Z'])
    lk(gi.outputs['Len'],cl.inputs['X']); lk(ico.outputs['Mesh'],tf.inputs['Geometry']); lk(cl.outputs[0],tf.inputs['Scale'])
    for a in ('X','Y','Z'): lk(gi.outputs['Size'],cs.inputs[a])
    lk(circ.outputs['Mesh'],inst.inputs['Points']); lk(tf.outputs['Geometry'],inst.inputs['Instance']); lk(cz.outputs[0],inst.inputs['Rotation']); lk(cs.outputs[0],inst.inputs['Scale'])
    lk(inst.outputs['Instances'],sm.inputs['Geometry']); lk(sm.outputs['Geometry'],go.inputs[0])
    return ng
def atoms_group(mats,radii):
    """Instances spheres on mesh points, split by int attribute 'elem' (0..3), revealed up to Threshold index."""
    ng=bpy.data.node_groups.new('Atoms','GeometryNodeTree')
    sock(ng,'Geometry','NodeSocketGeometry'); sock(ng,'Threshold','NodeSocketFloat'); sock(ng,'Geometry','NodeSocketGeometry','OUTPUT')
    N=ng.nodes; L=ng.links; gi=N.new('NodeGroupInput'); go=N.new('NodeGroupOutput'); jn=N.new('GeometryNodeJoinGeometry')
    idx=N.new('GeometryNodeInputIndex'); lt=_new(N,'ShaderNodeMath'); lt.operation='LESS_THAN'
    L.new(idx.outputs[0],lt.inputs[0]); L.new(gi.outputs['Threshold'],lt.inputs[1])
    na=N.new('GeometryNodeInputNamedAttribute'); na.data_type='INT'; na.inputs['Name'].default_value='elem'
    for k,(m,r) in enumerate(zip(mats,radii)):
        eq=_new(N,'ShaderNodeMath'); eq.operation='COMPARE'; eq.inputs[1].default_value=float(k); eq.inputs[2].default_value=0.1
        mu=_new(N,'ShaderNodeMath'); mu.operation='MULTIPLY'
        ico=N.new('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value=1.0; ico.inputs['Subdivisions'].default_value=2
        inst=N.new('GeometryNodeInstanceOnPoints'); sm=N.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value=m
        L.new(na.outputs[0],eq.inputs[0]); L.new(eq.outputs[0],mu.inputs[0]); L.new(lt.outputs[0],mu.inputs[1])
        L.new(gi.outputs['Geometry'],inst.inputs['Points']); L.new(mu.outputs[0],inst.inputs['Selection']); L.new(ico.outputs['Mesh'],inst.inputs['Instance']); inst.inputs['Scale'].default_value=(r,r,r)
        L.new(inst.outputs['Instances'],sm.inputs['Geometry']); L.new(sm.outputs['Geometry'],jn.inputs[0])
    L.new(jn.outputs['Geometry'],go.inputs[0])
    return ng
