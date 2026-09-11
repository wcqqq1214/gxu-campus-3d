"""Ray-test source and shipped LODs: courtyard, north colonnade, canopy and stairs."""
import bpy,json,math,struct
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1]
b=next(b for b in json.loads((R/'public/data/buildings.json').read_text()) if b.get('customModel')=='huicui')
e=b['architecture'];ox,oy=e['origin'];ca,sa=math.cos(e['angle']),math.sin(e['angle']);yn=e['bounds'][3];back=yn-e['arcadeDepth']
t=json.loads((R/'public/data/terrain.json').read_text());x0,y0,x1,y1=t['bounds'];cols,rows=t['cols'],t['rows']
def elevation(x,y):
    u=(x-x0)/(x1-x0)*(cols-1);v=(y-y0)/(y1-y0)*(rows-1);i,j=int(u),int(v);a,q=u-i,v-j;h=t['heights']
    return (h[j*cols+i]*(1-a)+h[j*cols+i+1]*a)*(1-q)+(h[(j+1)*cols+i]*(1-a)+h[(j+1)*cols+i+1]*a)*q
z=elevation(*b['center'])
def point(x,y,h):return Vector((ox+x*ca-y*sa,oy+x*sa+y*ca,z+h))
def bvh(objects):
    v=[];f=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();offset=len(v);v.extend(tuple(o.matrix_world@p.co) for p in o.data.vertices)
        f.extend(tuple(offset+i for i in t.vertices) for t in o.data.loop_triangles)
    return BVHTree.FromPolygons(v,f,all_triangles=True)
def check(objects,terrain,label):
    geom=bvh(objects);ground=bvh(terrain) if terrain else None;open_rays=0
    for x in [-34,-26,-18,0,18,26,34]:
        for h in [1.8,3.8]:
            a=point(x,yn+6,h);c=point(x,back+.5,h);direction=c-a
            assert geom.ray_cast(a,direction.normalized(),direction.length)[0] is None,(label,'blocked arcade',x,h)
            open_rays+=1
    for x,y in [(0,0),(8,6),(10,-6)]:
        assert geom.ray_cast(point(x,y,40),Vector((0,0,-1)),38)[0] is None,(label,'sealed courtyard')
    canopy=geom.ray_cast(point(0,yn+2,2),Vector((0,0,1)),5)[0]
    assert canopy is not None and 4.48<canopy.z-z<4.60,(label,'missing canopy ceiling')
    floor=[];margins=[]
    for x in [-5,0,5]:
        for y in [yn+.4,yn+3.8,yn+5.5,yn+6.7]:
            p=point(x,y,2);hit=geom.ray_cast(p,Vector((0,0,-1)),3)[0]
            assert hit is not None and -.46<hit.z-z<.63,(label,'stairs',x,y,hit)
            floor.append(round(hit.z-z,4))
            if ground:
                g=ground.ray_cast(p,Vector((0,0,-1)),5)[0]
                assert g is not None and hit.z-g.z>.045,(label,'buried stair',x,y,None if g is None else hit.z-g.z)
                margins.append(round(hit.z-g.z,4))
                if y>yn+6.5:assert hit.z-g.z<.45,(label,'excessive bottom step',x,hit.z-g.z)
    return {'representation':label,'openArcadeRays':open_rays,'openCourtyardRays':3,'canopyUnderside':round(canopy.z-z,4),'stairHeights':floor,'minimumTreadAboveTerrain':min(margins) if margins else None}
bpy.ops.wm.open_mainfile(filepath=str(R/'blender/gxu-campus.blend'))
objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']];assert len(objects)==1
assert len(objects[0].vertex_groups)>=8
report=[check(objects,[bpy.data.objects['terrain']],'editable source')]
for name in ['base',b['chunk']]:
    raw=(R/f'public/models/{name}.glb').read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size])
    for scene in doc['scenes']:scene['nodes']=[i for i in scene['nodes'] if doc['nodes'][i].get('name') in (b['chunk'],'terrain')]
    js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);tail=raw[20+size:]
    path=R/'work/huicui-validation.glb';path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(js)+len(tail))+struct.pack('<I4s',len(js),b'JSON')+js+tail)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));bpy.context.view_layer.update()
    buildings=[];terrain=[]
    for o in bpy.context.scene.objects:
        root=o
        while root.parent:root=root.parent
        if root.name==b['chunk']:buildings.append(o)
        elif root.name=='terrain':terrain.append(o)
    report.append(check(buildings,terrain,name+'.glb'))
(R/'docs/model-checks/huicui-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('PASS: source/base/near courtyard, arcade, entrance canopy and stairs',flush=True)
