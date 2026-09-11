"""Verify shipped basketball geometry, markings, basket height and open net centers."""
import bpy,json,math,struct
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];data=json.loads((R/'public/data/basketball.json').read_text())
def bvh(objects):
    v=[];f=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();offset=len(v);v.extend([tuple(o.matrix_world@p.co) for p in o.data.vertices]);f.extend([tuple(offset+i for i in t.vertices) for t in o.data.loop_triangles])
    return BVHTree.FromPolygons(v,f,all_triangles=True)
def verify(groups,terrain,label):
    ground=bvh(terrain);results=[]
    for court in data['courts']:
        mesh=groups[court['id']] if court['id'] in groups else groups[court['bank']]
        geom=bvh(mesh);z=court['elevation']+.025;c,s=math.cos(court['rotation']),math.sin(court['rotation']);cx,cy=court['center']
        def point(x,y,h):return Vector((cx+x*c-y*s,cy+x*s+y*c,h))
        def hit(x,y,h=10,length=20):return geom.ray_cast(point(x,y,z+h),Vector((0,0,-1)),length)[0]
        floor=hit(4,3);assert floor is not None and abs(floor.z-z)<.012,(label,'floor',court['id'],floor)
        g=ground.ray_cast(point(4,3,z+1),Vector((0,0,-1)),4)[0]
        # The campus-wide 15-bit terrain allows up to one ~0.10 m quantization step.
        assert g is not None and .12<floor.z-g.z<.37,(label,'terrain',court['id'],None if g is None else floor.z-g.z)
        offsets=[]
        for x,y in [(.08,1.77),(6.575,-13),(.13,-5.704),(.08,-6.454),(2.425,-11),(7.525,2)]:
            p=hit(x,y);assert p is not None,(label,'missing paint',court['id'],x,y)
            delta=p.z-z;assert .024<delta<.054,(label,'paint collapsed',court['id'],x,y,delta);offsets.append(delta)
        rimerrors=[]
        for sign in [-1,1]:
            p=hit(.23,sign*12.425+.01);assert p is not None
            err=abs(p.z-z-3.05);assert err<.015,(label,'rim height',court['id'],err);rimerrors.append(err)
            assert hit(0,sign*12.425,3.3,.8) is None,(label,'blocked basket opening',court['id'])
            board=geom.ray_cast(point(.7,sign*12,z+3.65),Vector((-s*sign,c*sign,0)),1)[0]
            assert board is not None,(label,'missing board',court['id'])
        results.append({'id':court['id'],'paintSamples':len(offsets),'minimumPaintAboveFloor':round(min(offsets),4),'maximumRimHeightError':round(max(rimerrors),4),'basketOpenings':2,'floorAboveTerrain':round(floor.z-g.z,4)})
    return {'representation':label,'courts':len(results),'results':results}
bpy.ops.wm.open_mainfile(filepath=str(R/'blender/gxu-campus.blend'))
report=[verify({c['id']:[bpy.data.objects[c['id']]] for c in data['courts']},[bpy.data.objects['terrain']],'editable source')]
# Keep the shipped binary buffer byte-for-byte; import only relevant scene roots.
# This skips unrelated buildings without re-exporting or recompressing geometry.
raw=(R/'public/models/base.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length])
for scene in doc['scenes']:scene['nodes']=[i for i in scene['nodes'] if doc['nodes'][i].get('name','').startswith('basketball-bank-') or doc['nodes'][i].get('name')=='terrain']
js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);tail=raw[20+length:]
path=R/'work/basketball-validation.glb';path.parent.mkdir(exist_ok=True);path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(js)+len(tail))+struct.pack('<I4s',len(js),b'JSON')+js+tail)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
groups={};terrain=[]
for o in bpy.context.scene.objects:
    root=o
    while root.parent:root=root.parent
    if root.name.startswith('basketball-bank-'):groups.setdefault(root.name,[]).append(o)
    elif root.name=='terrain':terrain.append(o)
report.append(verify(groups,terrain,'base GLB'))
(R/'docs/model-checks/basketball-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"Passed: {len(data['courts'])} courts × source/GLB; court paint, 3.05 m rims, open nets and terrain",flush=True)
