"""Check actual arts bodies and open canopy in source, base and near GLBs.

Fixed evidence-derived body heights and three walk-through rays prevent a
successful re-export of the old four/five-storey solid boxes from passing.
"""
import bpy, sys, json, math, hashlib, re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-arts')
assert re.fullmatch('[a-z0-9-]+',PREFIX)
ids=['way/759165563','way/759165562','way/880089961']
bs={b['id']:b for b in json.loads((ROOT/'public/data/buildings.json').read_text())}
heights=dict(zip(ids,[9.9,13.2,3.8]))

def trees(objects):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles()
        result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
            [tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
    return result

def hits(meshes,point,direction,distance):
    return [hit for t in meshes if (hit:=t.ray_cast(Vector(point),Vector(direction),distance))[0] is not None]

def root_name(o):
    while o.parent:o=o.parent
    return o.name

ring=bs[ids[0]]['polygons'][0][0]
main=[sum(ring[k][i] for k in (2,3,10,11))/4 for i in (0,1)]
ring=bs[ids[2]]['polygons'][0][0];a,c=ring[4:6]
length=math.dist(a,c);u=[(c[i]-a[i])/length for i in (0,1)];n=[u[1],-u[0]]
canopy=[(a[i]+c[i])/2+n[i]*2 for i in (0,1)]
probes=dict(zip(ids,[main,bs[ids[1]]['center'],canopy]))

def check(groups,tolerance):
    result=[]
    for id in ids:
        b=bs[id];z=b['elevation'];p=probes[id];mesh=groups[id]
        found=hits(mesh,[*p,z+30],[0,0,-1],40)
        assert found,(id,'missing roof')
        actual=max(h[0].z for h in found);expected=z+heights[id]
        assert abs(actual-expected)<=tolerance,(id,'roof height',actual,expected)
        record={'id':id,'roofProbe':p,'expectedRoofMeters':expected,'actualRoofMeters':actual,'toleranceMeters':tolerance}
        if id==ids[2]:
            record['openPassages']=[]
            for t in (.22,.5,.78):
                front=[a[i]+(c[i]-a[i])*t-n[i]*.2 for i in (0,1)]
                for h in (1.0,2.5):
                    found=hits(mesh,[*front,z+h],[*n,0],5.7)
                    assert not found,('Canopy passage obstructed',t,h,found)
                    record['openPassages'].append({'front':front,'heightAboveDatum':h,'length':5.7})
            # These rays start inside the canopy volume, below roof and above floor.
            for direction,expected_height in [([0,0,1],z+3.35),([0,0,-1],z+.15)]:
                found=hits(mesh,[*p,z+1.8],direction,5)
                assert found,('Missing canopy soffit/floor',direction)
                hit=min(found,key=lambda h:h[3]);assert abs(hit[0].z-expected_height)<=tolerance,(direction,hit[0].z,expected_height)
            record['soffitAndFloorPassed']=True
        result.append(record)
    return result

report={'passed':False,'checkedRoot':str(TARGET),'scope':'Three arts body heights and six canopy passage rays plus soffit/floor, actual source/base/near. Not whole-building or measured-site acceptance.'}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects={o.get('featureId'):o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('featureId')}
    # Published building datums round to centimetres; source uses full terrain
    # interpolation precision (up to 5 mm difference, plus float32 rounding).
    report['source']=check({id:trees([objects[id]]) for id in ids},.006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check({id:trees(o for o in bpy.context.scene.objects if root_name(o)==bs[id]['chunk']) for id in ids},.05)
    near={}
    for chunk in sorted({bs[id]['chunk'] for id in ids}):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{chunk}.glb'));bpy.context.view_layer.update()
        mesh=trees(bpy.context.scene.objects)
        for id in ids:
            if bs[id]['chunk']==chunk:near[id]=mesh
    report['near']=check(near,.02)
    report['fingerprints']={str(p):hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/models/chunk-p0-n1.glb','public/models/chunk-p1-n1.glb']}
    report['passed']=True
except Exception as e:
    report['failure']=str(e);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Arts actual geometry:',report['passed'],flush=True)
