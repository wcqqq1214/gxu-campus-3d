"""Probe the actual east lattice, openings and supports in all shipped forms."""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-materials-frame')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564999')
# Fixed acceptance coordinates from the mapped eastern courtyard and the
# reviewed frame layout; do not derive expectations from the tested GLB.
A=Vector((-519.4148116637112,-907.1800759999411,0))
B=Vector((-510.18038464069923,-907.1800759999411,0))
C=Vector((-510.2436132668971,-891.8067839998389,0))
D=Vector((-519.4763634260866,-891.8067839998389,0))
def pt(u,v,h):return (1-u)*(1-v)*A+u*(1-v)*B+u*v*C+(1-u)*v*D+Vector((0,0,b['elevation']+h))
def trees(objects):
    return [BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]) for o in objects if o.type=='MESH']
def ray(ts,start,direction,distance):
    hits=[t.ray_cast(start,direction,distance) for t in ts]
    return min((h for h in hits if h[0] is not None),key=lambda h:h[3],default=None)
def check(objects,tol):
    ts=trees(objects);down=Vector((0,0,-1));results=[]
    def down_to(name,p,expected,distance=60):
        h=ray(ts,p,down,distance)
        assert h and abs(h[0].z-b['elevation']-expected)<tol,(name,h[0].z-b['elevation'] if h else None,expected)
        assert h[1].z>.98,(name,'upward normal',tuple(h[1]))
        results.append({'kind':name,'actualHeight':h[0].z-b['elevation'],'expectedHeight':expected})
    # 7 slats and 8 independent gaps: a full low slab fails the gap probes;
    # the old high extrusion fails both height and opening checks.
    length=min((D-A).length,(C-B).length);edge=.8;slat=.3;gap=(length-2*edge-7*slat)/8
    for i in range(7):
        v=(edge+(i+1)*gap+(i+.5)*slat)/length
        down_to('slat-top',pt(.5,v,55),21.86)
    for i in range(8):
        v=(edge+(i+.5)*gap+i*slat)/length
        down_to('sky-gap-to-platform',pt(.5,v,55),.6)
    for u,v in [(.04,.5),(.96,.5),(.5,.02),(.5,.98)]:
        down_to('edge-beam',pt(u,v,55),21.86)
    for u in (.05,.95):
        for v in (.03,.97):
            center=pt(u,v,10);direction=Vector((1 if u>.5 else -1,0,0))
            start=center-direction*1.2
            hit=ray(ts,start,direction,1.4)
            assert hit and abs(hit[3]-.85)<tol,('column axial',u,v,hit[3] if hit else None)
            miss=ray(ts,start+Vector((0,.43 if v<.5 else -.43,0)),direction,1.4)
            assert miss is None,('column round clearance',u,v)
            results.append({'kind':'round-column','u':u,'v':v,'axialDistance':hit[3],'offAxisClear':True})
    for x,y in [(-514,-915),(-514,-884),(-596,-900)]:
        down_to('unchanged-high-roof',Vector((x,y,b['elevation']+55)),48.1)
    for x,y in [(-576,-900),(-543,-900),(-523,-900)]:
        hit=ray(ts,Vector((x,y,b['elevation']+55)),down,54)
        assert hit is None,('original courtyard filled',x,y,hit[0] if hit else None)
        results.append({'kind':'original-courtyard','x':x,'y':y,'clearAboveOneMeter':True})
    return {'passed':True,'toleranceMeters':tol,'probes':results}
def root_name(o):
    while o.parent:o=o.parent
    return o.name
report={'targetRoot':str(TARGET),'buildingId':b['id'],'passed':False}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([bpy.data.objects['资源环境与材料学院']],.015)
    for label,file,tol in [('base','base.glb',.05),('near','chunk-n2-n3.glb',.025)]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/file));bpy.context.view_layer.update()
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (label!='base' or root_name(o)=='chunk-n2-n3')]
        report[label]=check(objects,tol)
    report['passed']=True
except Exception as e:
    report['failure']=str(e)
finally:
    files=['blender/gxu-campus.blend','public/models/base.glb','public/models/chunk-n2-n3.glb']
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in files}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)
if not report['passed']:raise AssertionError(report['failure'])
