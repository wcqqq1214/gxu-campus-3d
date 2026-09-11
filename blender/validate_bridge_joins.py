"""Ray-test delivered asphalt continuity at all six ramp mouths and apron boundaries."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];joins=json.loads((R/'public/data/campus-roads.json').read_text())['bridgeJoins']
def bvh(objects):
    v=[];f=[]
    for o in objects:
        if o.type!='MESH':continue
        off=len(v);v.extend(o.matrix_world@p.co for p in o.data.vertices)
        f.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons if o.data.materials[p.material_index].name.split('.')[0]=='asphalt')
    return BVHTree.FromPolygons(v,f)
def probe(mesh,x,y,z):
    p=mesh.ray_cast(Vector((x,y,z+3)),Vector((0,0,-1)),10)[0]
    assert p is not None,('asphalt gap',x,y,z)
    return p.z
def check(objects,label):
    mesh=bvh(objects);records=[]
    for j in joins:
        a=j['start'];ux,uy=j['direction'];jump=0
        for off in [-3.4,-1.7,0,1.7,3.4]:
            heights=[probe(mesh,a[0]-uy*off+ux*d,a[1]+ux*off+uy*d,a[2]) for d in [-.14,.14]]
            jump=max(jump,abs(heights[1]-heights[0]))
        assert jump<.12,(label,j['id'],'entry seam',jump)
        count=0;maxstep=0;previous=None
        for a,c in zip(j['axis'],j['axis'][1:]):
            length=math.dist(a,c);steps=max(1,math.ceil(length/.25));dx=(c[0]-a[0])/length;dy=(c[1]-a[1])/length
            for k in range(steps):
                t=k/steps;heights=[]
                for off in [-2.4,0,2.4]:heights.append(probe(mesh,a[0]*(1-t)+c[0]*t-dy*off,a[1]*(1-t)+c[1]*t+dx*off,j['start'][3]))
                if previous:maxstep=max(maxstep,max(abs(a-b) for a,b in zip(heights,previous)))
                previous=heights;count+=3
        assert maxstep<.25,(label,j['id'],'abrupt rise',maxstep)
        records.append({'id':j['id'],'asphaltSamples':count+10,'entryHeightStep':round(jump,4),'maximumQuarterMeterStep':round(maxstep,4)})
    return {'representation':label,'joins':records}
bpy.ops.wm.open_mainfile(filepath=str(R/'blender/gxu-campus.blend'))
report=[check([o for o in bpy.context.scene.objects if o.name=='roads' or o.name.startswith('infra-approach-')],'editable source')]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'public/models/base.glb'))
objects=[]
for o in bpy.context.scene.objects:
    root=o
    while root.parent:root=root.parent
    if root.name=='roads' or root.name.startswith('infra-approach-'):objects.append(o)
report.append(check(objects,'base GLB'))
(R/'docs/model-checks/bridge-joins-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
