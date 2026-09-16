"""Inspect the adopted fifth-storey recess and retained solid storeys.

Dimensions are fixed photo-constrained acceptance estimates. Map edge anchors
are unchanged inputs; expectations are not read from the new corridor config.
"""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-physics-corridor')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/957404989')
EDGES={0:2,6:3,14:3,15:8,16:12,17:8}
ring=b['polygons'][0][0];sign=1 if sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(ring,ring[1:]))>0 else -1

def root_name(o):
    while o.parent:o=o.parent
    return o.name

def check(objects,tol):
    trees=[BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
           [tuple(p.vertices) for p in o.data.polygons]) for o in objects if o.type=='MESH']
    def ray(p,d,limit=5):
        hits=[t.ray_cast(p,d,limit) for t in trees]
        return min((h for h in hits if h[0] is not None),key=lambda h:h[3],default=None)
    rows=[]
    for edge,bays in EDGES.items():
        a=Vector((*ring[edge],b['elevation']));c=Vector((*ring[edge+1],b['elevation']));u=(c-a).normalized();n=Vector((u.y*sign,-u.x*sign,0));length=(c-a).length
        point=lambda t,h:a+u*t+Vector((0,0,h))
        for bay in range(bays):
            t=2.4+(length-4.8)*(bay+.5)/bays
            p=point(t,16.2)
            h=ray(p+n*.4,-n)
            assert h and abs(h[3]-2.4)<tol and h[1].dot(n)>.98,('fifth-storey rear',edge,bay,h)
            for direction,expected in [(-1,13.2),(1,16.32)]:
                slab=ray(p-n,Vector((0,0,direction)),4)
                assert slab and abs(slab[0].z-b['elevation']-expected)<tol and slab[1].z*direction<-.98,('fifth-storey slab',edge,bay,direction,slab)
            rail=ray(point(t,13.65)+n*.4,-n,.8)
            assert rail and abs(rail[3]-.4)<tol,('rail',edge,bay,rail)
            rows.append({'edge':edge,'kind':'open-bay','bay':bay,'rearDepth':h[3]-.4})
        for i in range(bays+1):
            t=2.4+(length-4.8)*i/bays
            h=ray(point(t,15.2)+n*.4,-n,.8)
            assert h and abs(h[3]-.4)<tol,('column',edge,i,h)
            rows.append({'edge':edge,'kind':'column','index':i})
        for level in (0,3,5,8):
            for fraction in (.23,.67):
                h=ray(point(length*fraction,(level+1)*3.3-.3)+n*.4,-n,.8)
                assert h and abs(h[3]-.4)<tol,('solid storey front',edge,level,h)
            rows.append({'edge':edge,'kind':'retained-solid-storey','levelIndex':level})
        for t in (1.,length-1):
            h=ray(point(t,16.2)+n*.4,-n,.8)
            assert h and abs(h[3]-.4)<tol,('end return',edge,t,h)
        # Probe window centers away from piers. A hidden or wrongly recessed
        # window would hit the wall instead, outside the expected depth band.
        num=int(length/4)
        stations=[length*(i+.5)/num for i in range(num)]
        stations=[t for t in stations if 3.7<t<length-3.7 and min(abs(t-(2.4+(length-4.8)*j/bays)) for j in range(bays+1))>1.4]
        assert stations,('no window station',edge)
        t=stations[len(stations)//2]
        for level in (3,4,5,8):
            depth=2 if level==4 else 0
            # Offset within the pane to avoid the existing central mullion,
            # which projects farther out than the glass in the near model.
            h=ray(point(t+.35,(level+.56)*3.3)+n*.4,-n,3)
            assert h and .4+depth-.3-tol<h[3]<.4+depth-.04+tol/4,('window position',edge,level,h)
            rows.append({'edge':edge,'kind':'window-depth','levelIndex':level,'distance':h[3]})
    for x,y in [(-680,-880),(-680,-840)]:
        assert ray(Vector((x,y,b['elevation']+40)),Vector((0,0,-1)),39) is None,('mapped court filled',x,y)
    return {'passed':True,'toleranceMeters':tol,'checks':rows,'originalCourtsOpen':True}

report={'passed':False,'buildingId':b['id'],'checkedRoot':str(TARGET),'storeyNumber':5,'facadeEdges':list(EDGES),'dimensionStatus':'estimated'}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([bpy.data.objects['物理科学与工程技术学院']],.015)
    for label,file,tol in [('base','base.glb',.06),('near','chunk-n2-n3.glb',.035)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/file));bpy.context.view_layer.update()
        report[label]=check([o for o in bpy.context.scene.objects if o.type=='MESH' and (label!='base' or root_name(o)=='chunk-n2-n3')],tol)
    report['passed']=True
except Exception as error:report['failure']=str(error)
finally:
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/models/chunk-n2-n3.glb']}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)
if not report['passed']:raise AssertionError(report['failure'])
