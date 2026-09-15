"""Check visible rear glass and frames in both generated and shipping LODs."""
import bpy,json,sys,re,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-office-south-glazing')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759132930')
e=b['form']['entrances'][0];a=math.radians(e['bearing']);n=Vector((math.sin(a),math.cos(a),0));u=Vector((n.y,-n.x,0))
origin=Vector((*e['center'],b['elevation']+.6))

def trees(objects):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons]
        materials=[o.data.materials[p.material_index].name.split('.')[0] for p in o.data.polygons]
        if faces:result.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces),materials))
    return result

def ray(ts,point):
    hits=[]
    for tree,materials in ts:
        hit=tree.ray_cast(point,-n,.65)
        if hit[0] is not None:hits.append((*hit,materials[hit[2]]))
    return min(hits,key=lambda hit:hit[3],default=None)

def check(objects,tolerance):
    ts=trees(objects);samples=[]
    def sample(offset,height,material):
        hit=ray(ts,origin+u*offset+n*.4+Vector((0,0,height)))
        assert hit and hit[4]==material,('visible material',offset,height,material,hit[4] if hit else None)
        expected=.32 if material=='glass' else .24
        assert abs(hit[3]-expected)<tolerance,('wrong rear-wall depth',offset,height,hit[3])
        assert hit[1].dot(n)>.98,('inward-facing panel',offset,height)
        samples.append(dict(offset=offset,heightAbovePlatform=height,material=material,distance=hit[3],outwardNormalDot=hit[1].dot(n)))
    # Intended photo-matched dimensions are explicit here, not read from the
    # generator's derived bank widths, so a misplaced bank cannot self-verify.
    for offset in (-10.4,-8.55,-6.7,-4.85,4.85,6.7,8.55,10.4):
        for height in (1.4,2.97):sample(offset,height,'glass')
    for offset in (-2.5,-.8,.8,2.5):sample(offset,1.4,'glass')
    for height in (2.48,2.83,3.0):sample(.8,height,'glass')
    for offset in (-11.3625,-9.475,-7.625,-5.775,-3.8875,3.8875,5.775,7.625,9.475,11.3625):
        sample(offset,1.4,'white')
    for offset in (-8,.8,8):sample(offset,2.65,'white')
    for offset in (-1.6,0,1.6):sample(offset,1.4,'white')
    sample(.8,2.35,'white')
    for offset,height in [(-11.6,1.4),(11.6,1.4),(0,3.4)]:
        hit=ray(ts,origin+u*offset+n*.4+Vector((0,0,height)))
        assert hit and hit[4]!='glass',('glazing outside configured banks',offset,height)
    return dict(passed=True,toleranceMeters=tolerance,glassSamples=23,frameSamples=17,outsideGlazingSamples=3,samples=samples)

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

report=dict(passed=False,buildingId=b['id'],dimensionsAreEstimated=True,checkedRoot=str(TARGET))
try:
    if '--generated-only' in sys.argv:
        sys.path.insert(0,str(ROOT/'blender'))
        from generic_buildings import ordinary_building
        from geometry import MATERIALS
        bpy.ops.wm.read_factory_settings(use_empty=True)
        colors=['pink','stone','white','paleRoof','red','path','shadeGlass','glass']
        MATERIALS[:]=[bpy.data.materials.new(name) for name in colors];C={name:i for i,name in enumerate(colors)}
        for detail in (False,True):
            obj=ordinary_building(b,b['elevation'],C,detail).object('test',bpy.context.scene.collection)
            report['generatedNear' if detail else 'generatedBase']=check([obj],.008)
            bpy.data.objects.remove(obj,do_unlink=True)
    else:
        report['sourceSha256']=hashlib.sha256((TARGET/'blender/gxu-campus.blend').read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
        report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.008)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
        report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
        report['near']=check(list(bpy.context.scene.objects),.02)
        report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/buildings.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-glazing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Office south rear glazing:',report['passed'],flush=True)
