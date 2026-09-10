"""Inspect the saved sculpture and decoded delivery GLBs, not generator source."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
l=next(l for l in json.loads((ROOT/'public/data/landmarks.json').read_text()) if l['id']=='time-gate')

def check(objects,label):
    verts=[];faces=[]
    for o in objects:
        if o.type!='MESH':continue
        offset=len(verts);verts.extend([tuple(o.matrix_world@v.co) for v in o.data.vertices])
        faces.extend([tuple(offset+i for i in p.vertices) for p in o.data.polygons if o.data.materials[p.material_index].name.split('.')[0]=='timeSilver'])
    assert faces,label
    # GLB import converts back to Blender's east/north/up axes.
    floor=l['islandElevation'];cut=floor+2;adj={}
    for face in faces:
        hits=[]
        for i,j in zip(face,face[1:]+face[:1]):
            a,b=verts[i],verts[j]
            if (a[2]<cut)!=(b[2]<cut):
                t=(cut-a[2])/(b[2]-a[2]);hits.append(tuple(round(a[k]+t*(b[k]-a[k]),2) for k in (0,1)))
        if len(hits)==2 and hits[0]!=hits[1]:
            a,b=hits;adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
    unseen=set(adj);components=[]
    while unseen:
        seed=unseen.pop();todo=[seed];group={seed}
        while todo:
            for q in adj[todo.pop()]:
                if q in unseen:unseen.remove(q);todo.append(q);group.add(q)
        if len(group)>3:components.append(group)
    assert len(components)==3,(label,'foot sections',len(components))
    bvh=BVHTree.FromPolygons(verts,faces)
    a=math.radians(180-l['frontBearing']);x,y=l['center']
    # A person-height ray through the front opening remains clear up to the arch.
    point=Vector((x+3*math.sin(a),y-3*math.cos(a),floor+1))
    hit=bvh.ray_cast(point,Vector((0,0,1)),30)
    assert hit[0] and hit[3]>10,(label,'blocked central arch',hit[3])
    used={i for f in faces for i in f};height=max(verts[i][2] for i in used)-floor
    assert 19<height<22,(label,height)
    return dict(representation=label,metalFaces=len(faces),footSections=len(components),archClearanceFromOneMeter=round(hit[3],3),height=round(height,3))

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
source=[o for o in bpy.context.scene.objects if o.get('landmark')=='time-gate']
assert len(source)==1 and source[0].get('featureId')==l['osmId']
assert len(source[0].vertex_groups)==4
results=[check(source,'editable source')]
for name in ['base','time-gate']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'public/models/{name}.glb'))
    objects=[]
    for o in bpy.context.scene.objects:
        root=o
        while root.parent:root=root.parent
        if o.get('landmark')=='time-gate' or root.get('landmark')=='time-gate':objects.append(o)
    results.append(check(objects,name+'.glb'))
path=ROOT/'docs/model-checks/time-gate-geometry.json';path.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False),flush=True)
