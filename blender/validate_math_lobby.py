"""Inspect the photo-constrained north stair lobby in saved and exported meshes.

The axial relationship is supported by Environment photo 5; absolute placement
and metric dimensions remain estimates. This does not certify its access path.
"""
import hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-mathematics-lobby')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129516')
e=next(e for e in b['form']['entrances'] if e['id']=='north-stair-lobby')
f=next(f for f in b['form']['facades'] if f['edge']==1 and f['part']=='lower-east')
panel=next(p for p in f['rule']['panels'] if p['id']=='north-stair-screen-2')
axis=[f['start'][i]+(panel['from']+panel['to'])/2*(f['end'][i]-f['start'][i]) for i in (0,1)]
assert math.dist(axis,e['center'])<1e-7
angle=math.radians(e['bearing']);n=Vector((math.sin(angle),math.cos(angle),0));t=Vector((n.y,-n.x,0));origin=Vector((*e['center'],b['elevation']))
def owner(o):
    while o.parent:o=o.parent
    return o

def trees(objects,material=None):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons if material is None or o.data.materials[p.material_index].name.split('.')[0]==material]
        if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return result

def ray(mesh,start,direction,distance=1):
    hits=[hit for tree in mesh if (hit:=tree.ray_cast(start,direction,distance))[0] is not None]
    return min(hits,key=lambda h:h[3]) if hits else None

def check(objects,tolerance):
    objects=list(objects);all_mesh=trees(objects);glass=trees(objects,'glass');stone=trees(objects,'stone');samples=[]
    def require(kind,mesh,u,h,projection):
        start=origin+t*u+n*.8+Vector((0,0,h));hit=ray(mesh,start,-n)
        assert hit and abs(hit[3]-(.8-projection))<=tolerance,(kind,u,h,hit)
        first=ray(all_mesh,start,-n)
        assert first and abs(first[3]-hit[3])<=tolerance,('occluded',kind,u,h)
        samples.append({'kind':kind,'u':u,'height':h,'projection':.8-hit[3]})
    for u in (-.4,.4):
        for h in (.5,1.3,2.0):
            require('opaque-door',stone,u,h,.08)
            assert ray(glass,origin+t*u+n*.8+Vector((0,0,h)),-n) is None,('hidden glass behind door',u,h)
    for u,h in [(-2.5,1.2),(2.5,1.2),(-.83,1.2),(.83,1.2),(.4,2.5),(.4,2.95)]:
        require('sidelight-or-transom',glass,u,h,.08)
    for u in (-3.1,-1.1,1.1,3.1):require('doorway-pier',stone,u,1.2,.19)
    for u in (-3.35,0,3.35):
        for depth in (.15,.6,1.05):
            point=origin+t*u+n*depth
            for h,direction,want in [(4,-1,3.45),(2.8,1,3.15)]:
                hit=ray(all_mesh,point+Vector((0,0,h)),Vector((0,0,direction)),2)
                assert hit and abs(hit[0].z-origin.z-want)<=tolerance,('canopy',u,depth,h,hit)
                assert hit[1].z*direction<-.95,('canopy winding',u,depth,h,hit)
                samples.append({'kind':'canopy-top' if direction<0 else 'canopy-soffit','u':u,'depth':depth,'relativeHeight':hit[0].z-origin.z})
    # Neither modeled steps nor floor slabs are inferred from the obscured photo.
    ground=trees([o for o in bpy.context.scene.objects if owner(o).get('layer')=='terrain'])
    clearances=[]
    for u in (-.6,0,.6):
        point=origin+t*u+n*.3
        hit=ray(ground,point+Vector((0,0,3)),Vector((0,0,-1)),10)
        assert hit,'missing local ground'
        clearance=origin.z+.03-hit[0].z
        assert -.02<=clearance<=.15,('local threshold burial or float',u,clearance)
        clearances.append(clearance)
    return dict(passed=True,samples=samples,thresholdAboveTerrain=clearances,accessRouteAccepted=False)

report=dict(passed=False,buildingId=b['id'],wholeBuildingAccepted=False,checkedRoot=str(TARGET),adoptedCenter=e['center'],axisErrorMeters=math.dist(axis,e['center']),scope=__doc__)
report['fingerprints']={str(p):hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/data/models.json','public/data/buildings.json','public/models/base.glb',f'public/models/{b["chunk"]}.glb']}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.011)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if owner(o).name==b['chunk']],.05)
    # Retain the loaded base terrain while replacing its building chunk.
    for o in [o for o in bpy.context.scene.objects if owner(o).get('layer')=='buildings']:
        bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
    report['near']=check([o for o in bpy.context.scene.objects if owner(o).name==b['chunk']],.02)
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Mathematics stair lobby',report['passed'],flush=True)
