"""Probe the photo-supported south-office portico in source and shipped LODs.

Checks use the recorded design dimensions, including off-axis round-column
rays that would fail if cylindrical supports silently reverted to boxes.
"""
import bpy,json,sys,math,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-office-south-entry')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759132930')
e=b['form']['entrances'][0];p=next(p for p in b['form']['parts'] if p['id']=='west-low-portico');z=b['elevation']
n=Vector((math.sin(math.radians(e['bearing'])),math.cos(math.radians(e['bearing'])),0));u=Vector((n.y,-n.x,0));front=Vector((*e['outerCenter'],z));width=e['porticoWidth']

def trees(objects,glass=False):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons if not glass or o.data.materials[p.material_index].name.split('.')[0] in ('glass','shadeGlass')]
        if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return result

def ray(ts,point,direction,distance):
    hits=[t.ray_cast(point,direction,distance) for t in ts]
    return min((h for h in hits if h[0] is not None),key=lambda h:h[3],default=None)

def check(objects,ground,tolerance):
    ts=trees(objects);glass=trees(objects,True);down=Vector((0,0,-1));up=-down
    roofs=[];bays=[];columns=[]
    for fraction in (.18,.5,.82):
        center=front+u*((fraction-.5)*width)-n*1.2
        hit=ray(ts,center+up*24,down,26)
        assert hit and abs(hit[0].z-z-8.7)<tolerance,('low roof',fraction,hit[0].z-z if hit else None)
        roofs.append(hit[0].z-z)
        hit=ray(ts,center+up*1.5,down,2)
        assert hit and abs(hit[0].z-z-.6)<tolerance,('platform',fraction)
        hit=ray(ts,center+up*1.5,up,4)
        assert hit and abs(hit[0].z-z-4.2)<tolerance,('soffit',fraction)
        start=front+u*((fraction-.5)*width)+n*.2+up*1.7
        # Stop 0.25 m before the rear wall: the closed door's 0.16 m
        # projecting frame is checked separately, not treated as a blocked bay.
        bay_hit=ray(ts,start,-n,e['recess']+.2-.25)
        assert not bay_hit,('blocked bay',fraction,tuple(bay_hit[0]) if bay_hit else None,bay_hit[3] if bay_hit else None)
        bays.append(fraction)
    for c in p['openBelow']['columns']:
        center=Vector((*c['center'],z+1.7))
        axial=ray(ts,center+n*1.1,-n,1.5)
        corner=ray(ts,center+u*.34+n*1.1,-n,1.5)
        assert axial and abs(axial[3]-.7)<tolerance+.01,('missing column',c)
        assert corner and .85-tolerance<corner[3]<.98+tolerance,('round support became square',c,corner[3] if corner else None)
        columns.append(dict(axialDistance=axial[3],offAxisDistance=corner[3]))
    door=Vector((*e['center'],z+.6+1.4))+n*.3
    hit=ray(glass,door,-n,.5)
    assert hit and abs(hit[3]-.21)<tolerance+.015,'rear glass door missing'
    assert not ray(glass,front+up*6.98+n*.5,-n,1),'solid sign fascia contains generic windows'
    # Positive tread clearance alone would miss an entire staircase hovering
    # above the ground. The lowest riser must extend down to the ground datum.
    foot=ray(ts,front+n*1.15+up*.07,-n,.4)
    assert foot and abs(foot[3]-.24)<tolerance+.01,'lowest riser floats above ground'
    steps=[]
    for i,expected in enumerate((.6,.4,.2)):
        start=front+n*((i+.5)*.3)+up*1.4
        hit=ray(ts,start,down,2);g=ray(ground,start,down,10)
        assert hit and abs(hit[0].z-z-expected)<tolerance,('step',i)
        assert g and hit[0].z>g[0].z,('buried step',i)
        steps.append(dict(height=hit[0].z-z,clearanceAboveGround=hit[0].z-g[0].z))
    # The first omitted strip is a solid five-storey end, not a stair extension.
    outside=front+u*(width/2+.4)+n*.45+up*1.2
    assert not ray(ts,outside,down,1.25),'steps escaped low-portico frontage'
    return dict(passed=True,toleranceMeters=tolerance,lowRoofHeights=roofs,openBays=bays,openBayRearWallMargin=.25,roundColumns=columns,recessedGlassDoor=True,solidUpperFascia=True,steps=steps,lowestRiserGrounded=True,stepsClippedToPortico=True)

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

report=dict(passed=False,buildingId=b['id'],checkedRoot=str(TARGET),dimensionsAreEstimated=True)
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    ground=trees([o for o in bpy.context.scene.objects if o.get('layer') in ('terrain','roads')])
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],ground,.008)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    ground=trees([o for o in bpy.context.scene.objects if root_name(o) in ('terrain','roads')])
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],ground,.05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),ground,.02)
    report['fingerprints']={str(p):hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb"]}
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-portico.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)
