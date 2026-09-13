"""Inspect the saved and shipped forestry portico, including openings and ground."""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from validate_generic import root_name

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
prefix=next((x.split('=',1)[1] for x in args if x.startswith('--report-prefix=')),'s2-forestry')
if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in prefix):
    raise ValueError('Invalid report prefix')
b=next(x for x in json.loads((ROOT/'public/data/buildings.json').read_text()) if x['id']=='relation/11564703')
e=b['form']['entrances'][0];p=e['attachedPortico'];z=b['elevation']
n=Vector((math.sin(math.radians(e['bearing'])),math.cos(math.radians(e['bearing'])),0))
t=Vector((n.y,-n.x,0));origin=Vector((*e['center'],z))

def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [tuple(f.vertices) for f in obj.data.polygons])

def inspect(building_trees,terrain,tolerance):
    results=[]
    def cast(point,direction,distance=10):
        hits=[tr.ray_cast(point,direction,distance) for tr in building_trees]
        return min((hit[3] for hit in hits if hit[0] is not None),default=None)
    def expected(label,point,direction,distance,length):
        actual=cast(point,direction,length)
        assert actual is not None and abs(actual-distance)<=tolerance,(label,actual,distance)
        results.append({'kind':label,'distanceErrorMeters':abs(actual-distance)})
    # Every resolved support must exist at walking height; the wall behind
    # is farther away than the finite ray and cannot make this check pass.
    for i,(x,y) in enumerate(p['columns']):
        start=Vector((x,y,z+p['platformHeight']+1))+n*p['columnWidth']
        expected('column-'+str(i),start,-n,p['columnWidth']/2,p['columnWidth']*1.5)
    midpoint=origin+n*(p['depth']/2)+Vector((0,0,p['platformHeight']+.3))
    expected('open-doorway-under-canopy',midpoint,Vector((0,0,1)),
             p['clearHeight']-p['platformHeight']-.3,p['clearHeight'])
    ground=[]
    for i in range(p['steps']):
        height=p['stepBaseHeight']+(p['platformHeight']-p['stepBaseHeight'])*(p['steps']-i)/p['steps']
        center=origin+n*(p['depth']+(i+.5)*p['tread'])
        expected('step-'+str(i),center+Vector((0,0,height+.4)),Vector((0,0,-1)),.4,1)
        for u in (-p['width']/2+.2,0,p['width']/2-.2):
            point=center+t*u
            hit=terrain.ray_cast(point+Vector((0,0,3)),Vector((0,0,-1)),20)
            assert hit[0] is not None,('missing actual ground',i,u)
            clearance=z+height-hit[0].z
            assert -.03<=clearance<=.65,('buried or floating step',i,u,clearance)
            expected('step-width-surface',point+Vector((0,0,height+.4)),Vector((0,0,-1)),.4,1)
            assert hit[0].z>=z-.15-tolerance,('step bottom floats over actual ground',i,u)
            ground.append({'step':i,'localWidthOffset':u,'topAboveActualGroundMeters':clearance})
    bays=max(2,math.ceil(p['width']/2.2))
    u=-p['width']/2+.10+(p['width']-.20)/(2*bays)
    roof=p['clearHeight']+p['slabThickness']
    for fraction in (.25,.75):
        point=origin+t*u+n*(p['depth']+.4)+Vector((0,0,roof+p['parapetHeight']*fraction))
        assert cast(point,-n,.8) is None,('parapet opening blocked',fraction)
        results.append({'kind':'open-parapet-row','fraction':fraction})
    return {'checks':results,'ground':ground,'passed':True}

sha=lambda name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
inputs=['public/data/buildings.json','data/building-overrides.json','blender/gxu-campus.blend',
        'public/data/models.json','public/models/base.glb',f"public/models/{b['chunk']}.glb"]
fingerprints={name:sha(name) for name in inputs}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('featureId')==b['id'])
ground_obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('layer')=='terrain')
source=inspect([tree(obj)],tree(ground_obj),.011)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'));bpy.context.view_layer.update()
terrain=tree(next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('layer')=='terrain'))
base=inspect([tree(o) for o in bpy.context.scene.objects if o.type=='MESH' and root_name(o)==b['chunk']],terrain,.05)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/f"public/models/{b['chunk']}.glb"));bpy.context.view_layer.update()
near=inspect([tree(o) for o in bpy.context.scene.objects if o.type=='MESH'],terrain,.02)
assert fingerprints=={name:sha(name) for name in inputs}
report={'buildingId':b['id'],'source':source,'base':base,'near':near,'fingerprints':fingerprints,
        'scope':'Four portico supports, three step surfaces, canopy soffit, two open parapet rows, actual terrain below steps. Dimensions are estimates; this does not validate the whole building or a road-to-door route.', 'passed':True}
(ROOT/f'docs/model-checks/refinement/{prefix}-entry-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print('Forestry source/base/near entrance and ground checks passed',flush=True)
