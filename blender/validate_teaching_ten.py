"""Inspect the actual source and delivery geometry of the newly curated 十教."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
l=next(l for l in json.loads((ROOT/'public/data/landmarks.json').read_text()) if l['id']=='teaching-ten')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']==l['osmId']);e=b['architecture']

def check(objects,label):
    verts=[];faces=[]
    for o in objects:
        if o.type!='MESH':continue
        offset=len(verts);verts.extend([tuple(o.matrix_world@v.co) for v in o.data.vertices]);faces.extend([tuple(offset+i for i in p.vertices) for p in o.data.polygons])
    assert faces,label
    bv=BVHTree.FromPolygons(verts,faces);ca,sa=math.cos(e['angle']),math.sin(e['angle']);ox,oy=e['origin']
    def roof(x,y):
        hit=bv.ray_cast(Vector((ox+x*ca-y*sa,oy+x*sa+y*ca,l['elevation']+45)),Vector((0,0,-1)),55)
        return None if hit[0] is None else hit[0].z-l['elevation']
    samples=[(0,0,13.2),(-18,-16,9.9),(1,20,6.6),(10,40,26.4)]
    heights=[]
    for x,y,h in samples:
        measured=roof(x,y);assert measured is not None and abs(measured-h)<.08,(label,x,y,measured,h);heights.append(round(measured,3))
    # Empty notches between the curved low block and north classroom wing stay open.
    for x,y in [(-10,28),(12,28),(-28,0),(28,0)]:assert roof(x,y) is None,(label,'filled recess',x,y)
    assert roof(0,-21) is not None,(label,'missing entrance stairs')
    # Entry glass and name plate must sit ahead of the curved wall, not inside it.
    entryDistances=[]
    for x,h in [(2,1.8),(0,4.6)]:
        origin=Vector((ox+x*ca+25*sa,oy+x*sa-25*ca,l['elevation']+h))
        hit=bv.ray_cast(origin,Vector((-sa,ca,0)),10)
        assert hit[0] is not None and hit[3]<5.8,(label,'entry hidden by curved wall',hit[3])
        entryDistances.append(round(hit[3],3))
    return dict(representation=label,faces=len(faces),sampleRoofHeights=heights,openRecesses=4,entranceStairs=True,entryRayDistances=entryDistances)

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
objects=[o for o in bpy.context.scene.objects if o.get('featureId')==l['osmId']]
assert len(objects)==1 and objects[0].get('landmark')==l['id']
assert len(objects[0].vertex_groups)>=7
results=[check(objects,'editable source')]
for name in ['base','teaching-ten']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'public/models/{name}.glb'))
    objects=[]
    for o in bpy.context.scene.objects:
        root=o
        while root.parent:root=root.parent
        if o.get('landmark')==l['id'] or root.get('landmark')==l['id']:objects.append(o)
    results.append(check(objects,name+'.glb'))
p=ROOT/'docs/model-checks/teaching-ten-geometry.json';p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results),flush=True)
