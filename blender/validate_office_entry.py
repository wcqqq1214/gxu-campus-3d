"""Check the built portal, upper window band, solid sign wall and removed canopy."""
import bpy,json,sys,math,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-office-entry')
BEFORE=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--baseline=')),None)
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/671978896')
if BEFORE:
    old=next(b for b in json.loads((BEFORE/'public/data/buildings.json').read_text()) if b['id']=='way/671978896')['form']['entrances'][0]
else:
    evidence=json.loads((ROOT/'docs/model-checks/refinement/s2-office-entry-evidence.json').read_text())
    assert evidence['footprintRevision']==b['calibration']['footprintRevision'],'Stale previous entrance evidence'
    old=evidence['previousEntrance']
e=b['form']['entrances'][0];f=next(f for f in b['form']['facades'] if f['edge']==1)

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

def check(objects,tolerance):
    group=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();ts=list(o.data.loop_triangles)
        group.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in ts],all_triangles=True),[o.data.materials[t.material_index].name.split('.')[0] for t in ts]))
    def ray(p,d,limit):
        hits=[]
        for tree,mats in group:
            hit,normal,index,distance=tree.ray_cast(p,d,limit)
            if hit is not None:hits.append((distance,hit,mats[index]))
        return min(hits,key=lambda h:h[0]) if hits else None
    a=Vector((*f['start'],0));edge=Vector((*f['end'],0))-a;n=Vector((*f['normal'],0));center=Vector((*e['center'],0));u=Vector((n.y,-n.x,0));z=b['elevation']
    records=[]
    def face(point,h,material):
        hit=ray(point+n+Vector((0,0,z+h)),-n,1.2)
        assert hit and hit[2]==material,(h,material,hit)
        assert -.02-tolerance<=1-hit[0]<=.3+tolerance,('unexpected facade projection',hit)
        records.append(dict(height=h,material=material,depth=1-hit[0]))
    for offset in (-6.2,-4.6,-.8,.8,4.6,6.2):
        for h in (1.5,4.5):face(center+u*offset,h,'glass')
    for offset in (-7.8,-2.7,2.7,7.8):face(center+u*offset,4.5,'stone')
    for t in (.141667,.285,.428333,.571667,.715,.858333):
        for h in (7.6,8.7):face(a+edge*t,h,'glass')
    for t in (.08,.135,.865,.92):
        for h in (10.8,11.85):face(a+edge*t,h,'glass')
    for t in (.3,.4,.6,.7):face(a+edge*t,11.4,'white')
    # No invented roof/stair solids outside the north glazing or old south door.
    for entry in (e,old):
        angle=math.radians(entry['bearing']);nx,ny=math.sin(angle),math.cos(angle)
        point=Vector((entry['center'][0]+nx*.8,entry['center'][1]+ny*.8,z+3.5))
        assert ray(point,Vector((0,0,-1)),3.7) is None,('remaining generic canopy or steps',entry['id'])
    return dict(passed=True,facadeSamples=records,removedCanopyAndStepSamples=2,toleranceMeters=tolerance)
report=dict(passed=False,scope='Lower two-storey portal, four piers, third-floor band, top end windows and blank sign wall; no false north or obsolete south canopy/steps.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/buildings.json']}
    report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Office entry:',report['passed'],flush=True)
