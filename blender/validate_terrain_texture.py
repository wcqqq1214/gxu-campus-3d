"""Check the actual ground UV and fine-triangle regression at the paving site."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from site_geometry import split_convex
record=json.loads((ROOT/'public/data/pavings.json').read_text())['pavings'][0]
x0,y0,x1,y1=[math.floor(v) if i<2 else math.ceil(v) for i,v in enumerate(record['bounds'])]
outline=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)];expected_area=(x1-x0)*(y1-y0)
results={}
for kind in ['source','base']:
    if kind=='source':bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
    else:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
    o=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.split('.')[0]=='terrain')
    if kind=='base':
        assert o.get('positionQuantizationBits')==18 and o.get('texcoordQuantizationBits')==18
    m=o.data;m.calc_loop_triangles();vertices=[];faces=[];errors=[];area=0;count=0
    for tri in m.loop_triangles:
        points=[o.matrix_world@m.vertices[i].co for i in tri.vertices]
        if max(p.x for p in points)<x0 or min(p.x for p in points)>x1 or max(p.y for p in points)<y0 or min(p.y for p in points)>y1:continue
        clipped,_=split_convex([tuple(p) for p in points],outline)
        if len(clipped)<3:continue
        area+=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(clipped,clipped[1:]+clipped[:1])))/2
        for p,index in zip(points,tri.loops):
            uv=m.uv_layers.active.data[index].uv;errors.append(math.hypot(uv.x-p.x/4,uv.y-p.y/4))
        at=len(vertices);vertices.extend(points);faces.append((at,at+1,at+2));count+=1
    tree=BVHTree.FromPolygons(vertices,faces,all_triangles=True);holes=[];samples=0
    for ix in range(int((x1-x0)/.1)):
        for iy in range(int((y1-y0)/.1)):
            x=x0+(ix+.37)*.1;y=y0+(iy+.61)*.1;samples+=1
            if tree.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0] is None:holes.append([x,y])
    assert not holes,(kind,'terrain coverage holes',holes[:5])
    assert max(errors)<.00005,(kind,'ground UV no longer follows XY/4',max(errors))
    assert abs(area-expected_area)<(.05 if kind=='base' else .0001),(kind,'collapsed/overlapping fine triangles',area,expected_area)
    results[kind]={'triangles':count,'maximumGroundUVError':max(errors),'coveredRaySamples':samples,'holes':holes,'expectedProjectedAreaMeters2':expected_area,'summedProjectedAreaMeters2':area,'projectedAreaExcessMeters2':area-expected_area,'passed':True}
report={'pavingId':record['id'],'scope':'Actual source and decoded terrain at the previously striped region: XY/4 UV projection, matching export precision, dense coverage and projected triangle area. Browser comparison remains required.','bounds':[x0,y0,x1,y1],'results':results,'passed':True}
(ROOT/'docs/model-checks/refinement/s4-paving-terrain-texture.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
