"""Ray-check the sourced low portico in source, base and shipping near chunk.

Optional --check-root=... checks an older model against the current intended
building data. It must fail on the previous five-storey extrusion.
"""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s3-agriculture')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759185166')
if 'elevation' not in b or 'chunk' not in b:
    assert TARGET != ROOT, 'Build models before validating the current asset set'
    previous=next(x for x in json.loads((TARGET/'public/data/buildings.json').read_text()) if x['id']==b['id'])
    assert previous['polygons']==b['polygons'], 'Historical sampling requires the same mapped outline'
    b.update(elevation=previous['elevation'],chunk=previous['chunk'])
e=b['form']['entrances'][0];p=next(p for p in b['form']['parts'] if p['id']=='south-portico')
n=Vector((math.sin(math.radians(e['bearing'])),math.cos(math.radians(e['bearing'])),0));u=Vector((n.y,-n.x,0))
z=b['elevation'];front=Vector((*e['outerCenter'],z));depth=e['recess'];width=e['porticoWidth']

def trees(objects,windows=False):
    result=[]
    for o in objects:
        if o.type!='MESH': continue
        faces=[tuple(p.vertices) for p in o.data.polygons if not windows or
               o.data.materials[p.material_index].name.split('.')[0] in ('glass','shadeGlass')]
        if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return result

def ray(ts,point,direction,distance=100):
    hits=[t.ray_cast(point,direction,distance) for t in ts]
    return sorted([h for h in hits if h[0] is not None],key=lambda h:h[3])

def check(ts,tolerance,label,ground,windows):
    center=front-n*depth/2
    roof=ray(ts,Vector((center.x,center.y,z+25)),Vector((0,0,-1)))
    assert roof and abs(roof[0][0].z-z-p['height'])<=tolerance,(label,'portico is not a low canopy',roof[0][0].z if roof else None)
    floor=ray(ts,Vector((center.x,center.y,z+1.3)),Vector((0,0,-1)))
    assert floor and abs(floor[0][0].z-z-e['platformHeight'])<=tolerance,(label,'missing raised floor')
    # Three open bays below the canopy, ending before the actual back wall.
    for fraction in [.14,.5,.86]:
        point=front+u*((fraction-.5)*width)+n*.2;point.z=z+1.6
        hits=ray(ts,point,-n,depth+.05)
        assert not hits,(label,'blocked portico bay',fraction,hits[0][3] if hits else None)
    for c in p['openBelow']['columns']:
        point=Vector((*c['center'],z+1.6))+n*1.1
        hit=ray(ts,point,-n,1.5)
        assert hit and abs(hit[0][3]-(1.1-c['depth']/2))<tolerance+.03,(label,'missing or displaced column')
    door=Vector((*e['center'],z+e['platformHeight']+1.4))+n*.3
    hit=ray(ts,door,-n,.5)
    assert hit and abs(hit[0][3]-.21)<tolerance+.04,(label,'door is not on the rear wall')
    facade=next(f for f in b['form']['facades'] if 'minimumHeight' in f)
    count=max(1,int(math.dist(facade['start'],facade['end'])/4));fraction=.5/count
    window=Vector((*[facade['start'][i]+(facade['end'][i]-facade['start'][i])*fraction for i in (0,1)],z+1.56*facade['height']/facade['levels']))
    assert ray(windows,window+n*.8,-n,1),(label,'exposed second-floor window above portico is missing')
    stair_heights=[];ground_clearances=[]
    for i in range(3):
        point=front+n*((i+.5)*.3);point.z=z+1.4
        hit=ray(ts,point,Vector((0,0,-1)),2)
        expected=e['platformHeight']*(3-i)/3
        assert hit and abs(hit[0][0].z-z-expected)<=tolerance,(label,'missing stair',i)
        stair_heights.append(hit[0][0].z-z)
        ground_hit=ray(ground,point,Vector((0,0,-1)),10)
        assert ground_hit,(label,'ground sample missing')
        clearance=hit[0][0].z-ground_hit[0][0].z
        ground_clearances.append(clearance)
        assert clearance>0,(label,'stair buried by terrain or paving',i,clearance)
    return {'canopyHeight':roof[0][0].z-z,'floorHeight':floor[0][0].z-z,'openBays':3,'columns':4,'rearDoor':True,'exposedWindowAbovePortico':True,'stairHeights':stair_heights,'stairClearanceAboveGroundOrPaving':ground_clearances,'passed':True}

def root_name(o):
    while o.parent:o=o.parent
    return o.name

report={'buildingId':b['id'],'checkedRoot':str(TARGET),'toleranceBasis':'Source float and Draco position errors; these are model checks, not site measurements.','passed':False}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']]
    assert len(objects)==1
    ground=trees([o for o in bpy.context.scene.objects if o.get('layer') in ('terrain','roads')])
    report['source']=check(trees(objects),.011,'source',ground,trees(objects,windows=True))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    ground=trees([o for o in bpy.context.scene.objects if root_name(o).split('.')[0] in ('terrain','roads')])
    objects=[o for o in bpy.context.scene.objects if root_name(o)==b['chunk']]
    report['base']=check(trees(objects),.05,'base',ground,trees(objects,windows=True))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
    report['near']=check(trees(bpy.context.scene.objects),.02,'near',ground,trees(bpy.context.scene.objects,windows=True));report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-portico.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)
