"""Check the adopted dome silhouette in source and actual decoded GLBs.

Fixed acceptance dimensions are photo-constrained estimates, not measurements.
--check-root permits the previous bundle as a missing-dome negative control.
"""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-physics')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/957404989')
Z=b['elevation'];CX,CY=-678,-860.7

def check(objects,tol):
    trees=[BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
             [tuple(p.vertices) for p in o.data.polygons]) for o in objects if o.type=='MESH']
    def ray(start,direction,distance):
        hits=[t.ray_cast(Vector(start),Vector(direction),distance) for t in trees]
        return min((h for h in hits if h[0] is not None),key=lambda h:h[3],default=None)
    results=[]
    def down(name,x,y,expected):
        h=ray((x,y,Z+45),(0,0,-1),46)
        assert h and abs(h[0].z-Z-expected)<tol,(name,h[0].z-Z if h else None,expected,tol)
        assert h[1].z>.05,(name,'normal not upward',tuple(h[1]))
        results.append({'kind':name,'x':x,'y':y,'expectedHeight':expected,'actualHeight':h[0].z-Z,'normal':list(h[1])})
    down('dome-apex',CX,CY,37)
    # Three intermediate rings and eight azimuths detect missing quadrants,
    # incorrect radius/rise, reversed faces, and a box replacing the dome.
    for ring in (2,4,6):
        radius=7*math.cos(ring*math.pi/16)
        height=30.5+6.5*math.sin(ring*math.pi/16)
        for i in range(8):
            angle=i*math.pi/4
            down('dome-curve',CX+radius*math.cos(angle),CY+radius*math.sin(angle),height)
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        h=ray((CX+dx*8,CY+dy*8,Z+30.1),(-dx,-dy,0),2)
        assert h and abs(h[3]-1)<tol,('drum side',h)
        assert h[1].dot(Vector((dx,dy,0)))>.98,('drum normal',h)
        results.append({'kind':'drum-side','distance':h[3],'normal':list(h[1])})
    for x,y in [(CX-10,CY),(CX+9,CY),(-680,-899),(-680,-819)]:
        down('retained-flat-roof',x,y,29.7)
    for x,y in [(-680,-880),(-680,-840)]:
        h=ray((x,y,Z+45),(0,0,-1),44)
        assert h is None,('original open court filled',x,y,h)
        results.append({'kind':'original-open-court','x':x,'y':y,'clearAboveOneMeter':True})
    return {'passed':True,'toleranceMeters':tol,'probes':results}

def root_name(o):
    while o.parent:o=o.parent
    return o.name
report={'targetRoot':str(TARGET),'buildingId':b['id'],'passed':False,'adoptedDimensionsStatus':'estimated'}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([bpy.data.objects['物理科学与工程技术学院']],.015)
    for label,file,tol in [('base','base.glb',.06),('near','chunk-n2-n3.glb',.04)]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/file));bpy.context.view_layer.update()
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (label!='base' or root_name(o)=='chunk-n2-n3')]
        report[label]=check(objects,tol)
    report['passed']=True
except Exception as e:report['failure']=str(e)
finally:
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/models/chunk-n2-n3.glb']}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)
if not report['passed']:raise AssertionError(report['failure'])
