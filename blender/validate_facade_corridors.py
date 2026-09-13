"""Inspect sourced corridor voids, railings and slabs in source and actual GLBs."""
import bpy,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s3-corridor')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564704')
facades=[f for f in b['form']['facades'] if 'openCorridor' in f['rule']]
assert len(facades)==2 and {f['edge'] for f in facades}=={1,9}

def root_name(o):
    while o.parent:o=o.parent
    return o.name

def trees(objects):
    return [BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
            [tuple(p.vertices) for p in o.data.polygons]) for o in objects if o.type=='MESH']

def ray(ts,point,direction,distance):
    hits=[t.ray_cast(point,direction,distance) for t in ts]
    hits=[h for h in hits if h[0] is not None]
    return min(hits,key=lambda h:h[3]) if hits else None

def check(ts,tolerance):
    records=[];z=b['elevation']
    for f in facades:
        a,c=f['start'],f['end'];rule=f['rule']['openCorridor']
        n=Vector((*f['normal'],0));width=math.dist(a,c);fh=f['height']/f['levels']
        for level in range(rule['firstLevel'],int(f['levels'])):
            floor=z+level*fh
            for fraction in [.23,.5,.77]:
                p=Vector((a[0]+(c[0]-a[0])*fraction,a[1]+(c[1]-a[1])*fraction,floor+1.8))
                # Window frames are allowed on the recessed rear wall only.
                hit=ray(ts,p+n*.3,-n,rule['depth']+.4)
                assert hit and rule['depth']-.4 <= hit[3]-.3 <= rule['depth']+tolerance,('closed/absent recess',f['edge'],level,fraction,hit[3] if hit else None)
                inside=p-n*rule['depth']/2
                slab=ray(ts,inside,Vector((0,0,-1)),2)
                ceiling=ray(ts,inside,Vector((0,0,1)),2)
                assert slab and abs(slab[0].z-floor)<=tolerance,('missing corridor floor',f['edge'],level)
                assert ceiling and abs(ceiling[0].z-(floor+fh-.18))<=tolerance,('missing corridor ceiling',f['edge'],level)
                rail=ray(ts,Vector((p.x,p.y,floor+rule['railHeight']/2))+n*.3,-n,.6)
                assert rail and abs(rail[3]-.3)<=tolerance,('missing railing',f['edge'],level)
                records.append({'edge':f['edge'],'levelIndex':level,'fraction':fraction,'rearSurfaceDepthMeters':hit[3]-.3,'floorErrorMeters':abs(slab[0].z-floor),'ceilingErrorMeters':abs(ceiling[0].z-(floor+fh-.18))})
            # Ground-storey front and each end return must remain closed.
            for fraction,height in [(.5,z+1.6),(.1/width,floor+1.8),(1-.1/width,floor+1.8)]:
                p=Vector((a[0]+(c[0]-a[0])*fraction,a[1]+(c[1]-a[1])*fraction,height))
                assert ray(ts,p+n*.4,-n,.7),('missing wall return/ground floor',f['edge'],level)
    return {'passed':True,'sampledRecesses':len(records),'samples':records}

report={'buildingId':b['id'],'checkedRoot':str(TARGET),'passed':False,
        'scope':'Two sourced facade edges, four upper floors each, three interior stations per floor; actual void, rear surface, railing, floor, ceiling and end/ground walls.',
        'tolerancesMeters':{'source':.011,'baseDraco':.05,'nearDraco':.02}}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']]
    assert len(objects)==1
    report['source']=check(trees(objects),.011)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check(trees([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']]),.05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
    report['near']=check(trees(bpy.context.scene.objects),.02)
    report['modelManifestSha256']=hashlib.sha256((TARGET/'public/data/models.json').read_bytes()).hexdigest()
    report['passed']=True
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Corridor checks',report['passed'],flush=True)
