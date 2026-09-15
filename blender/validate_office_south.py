"""Check the documented unequal storeys in the source and both shipped LODs.

Roof height alone cannot detect a generator that still divides 20.4 m equally.
Window-top/bottom probes therefore check the five separate vertical bands.
"""
import bpy,json,sys,math,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-office-south')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759132930')
# These expected heights come from the recorded 2021 source, independently of
# generated form parameters, so an accidentally uniform stack cannot pass.
FLOORS=[4.8,3.9,3.9,3.9,3.9]
CENTERS=[2.688,6.984,10.884,14.784,18.684]

def trees(objects,glass=False):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons if not glass or
               o.data.materials[p.material_index].name.split('.')[0] in ('glass','shadeGlass')]
        if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return result

def ray(ts,point,direction,distance):
    hits=[t.ray_cast(point,direction,distance) for t in ts]
    return min((h for h in hits if h[0] is not None),key=lambda h:h[3],default=None)

def check(objects,tolerance):
    ts=trees(objects);glass=trees(objects,True);z=b['elevation'];roofs=[]
    for x,y in [(-220,-650),(-220,-665),(-205,-675)]:
        hit=ray(ts,Vector((x,y,z+24)),Vector((0,0,-1)),30)
        assert hit and abs(hit[0].z-z-20.4)<=tolerance,('body height',x,y,hit[0].z-z if hit else None)
        assert hit[1].z>.98,('roof normal',x,y)
        roofs.append(dict(x=x,y=y,bodyHeight=hit[0].z-z))
    a,c=b['polygons'][0][0][1:3];length=math.dist(a,c)
    u=Vector(((c[0]-a[0])/length,(c[1]-a[1])/length,0));n=Vector((-u.y,u.x,0));samples=[]
    # East elevation has ten ordinary bays. Move off the near-LOD centre mullion.
    for fraction in (.15,.85):
        center=Vector((a[0]+(c[0]-a[0])*fraction,a[1]+(c[1]-a[1])*fraction,z))+u*.45
        for level,expected in enumerate(CENTERS):
            for offset,present in [(-.87,True),(.87,True),(-1.15,False),(1.15,False)]:
                point=center+n*.8+Vector((0,0,expected+offset))
                hit=ray(glass,point,-n,1.1)
                assert bool(hit)==present,('window band',fraction,level,expected+offset,present,bool(hit))
                samples.append(dict(facadeFraction=fraction,level=level+1,height=expected+offset,glassExpected=present,glassHit=bool(hit)))
    return dict(passed=True,roofToleranceMeters=tolerance,roofs=roofs,windowBandSamples=samples,entranceOverlapProbes=0,
                windowCentersRelativeToDatum=CENTERS,windowDimensionsAreEstimated=True)

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

report=dict(passed=False,buildingId=b['id'],checkedRoot=str(TARGET),sourceFloorHeights=FLOORS,
            scope='Three main-body roof probes and forty east-facade glass-presence/absence probes; no entrance or multipart acceptance.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/buildings.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Office south documented storeys:',report['passed'],flush=True)
