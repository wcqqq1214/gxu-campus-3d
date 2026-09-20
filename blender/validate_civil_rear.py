"""Independent fixed-position checks for estimated civil north roof and low wings.

Do not derive expected heights/positions from the production override. Dimensions
are the adopted photo-constrained estimates, not a survey or whole-building QA.
"""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
TARGET = next((Path(a.split('=', 1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')), ROOT)
PREFIX = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--report-prefix=')), 's2-civil-rear')
ID, CHUNK, Z = 'relation/12875606', 'chunk-n2-n3', 4.06

# Independently specified roof control lines. Northern eaves follow the mapped
# stepped outline; the two short ridges join the east-west ridge at 13.1 m.
EAVE = [(-528.952650393, -806.436055854), (-528.934817691, -791.206900),
        (-514.429118852, -791.218032), (-514.439377478, -795.136496),
        (-488.577378343, -795.169892), (-488.567119715, -787.366360),
        (-476.708146689, -787.377492), (-476.731378534, -806.503250107),
        (-486.146083700, -806.491136000), (-512.100410480, -806.457740000)]
CONTROL = [Vector((x, y, 10.8)) for x, y in EAVE]
CONTROL += [Vector((-521.69, -798.47, 13.1)), Vector((-521.69, -800.82, 13.1)),
            Vector((-482.65, -793.30, 13.1)), Vector((-482.65, -800.82, 13.1))]
# One fixed triangle in each distinct pitch plane, including both roof valleys.
PLANES = [(0,1,10), (1,2,10), (2,3,11), (3,4,13), (4,5,12),
          (5,6,12), (6,7,13), (0,9,11), (9,8,13), (8,7,13)]
JOINTS = [(10,11), (11,13), (12,13), (3,11), (4,13)]


def root_name(obj):
    while obj.parent:
        obj = obj.parent
    return re.sub(r'\.\d+$', '', obj.name)


def check(objects, tolerance):
    trees = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        obj.data.calc_loop_triangles()
        triangles = list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [tuple(t.vertices) for t in triangles], all_triangles=True),
            [obj.data.materials[t.material_index].name.split('.')[0] for t in triangles]))

    def ray(origin, direction, distance):
        hits = []
        for tree, materials in trees:
            loc, normal, index, length = tree.ray_cast(Vector(origin), Vector(direction), distance)
            if loc is not None:
                hits.append((length, loc, normal, materials[index]))
        return min(hits, key=lambda h: h[0]) if hits else None

    samples = []
    def roof(x, y, height, material, kind, normal=None):
        hit = ray((x, y, Z+35), (0, 0, -1), 35)
        assert hit and hit[3] == material, (kind, x, y, 'material', hit)
        assert abs(hit[1].z-Z-height) < tolerance, (kind, x, y, height, hit)
        assert hit[2].z > .75, (kind, 'roof normal', hit)
        if normal is not None:
            assert hit[2].dot(normal) > .995, (kind, 'pitch plane', hit)
        samples.append(dict(kind=kind, position=[x,y], expectedHeight=height,
                            actualHeight=hit[1].z-Z, material=material))

    for i, indices in enumerate(PLANES):
        a, b, c = [CONTROL[k] for k in indices]
        normal = (b-a).cross(c-a).normalized()
        if normal.z < 0:
            normal = -normal
        for weights in [(1/3,1/3,1/3), (.55,.2,.25)]:
            p = a*weights[0]+b*weights[1]+c*weights[2]
            roof(p.x, p.y, p.z, 'red', f'pitch-{i}', normal)
    for i,j in JOINTS:
        for t in (.2,.5,.8):
            p = CONTROL[i].lerp(CONTROL[j], t)
            roof(p.x,p.y,p.z,'red',f'ridge-or-valley-{i}-{j}')
    # Both sides of the long ridge: no elevated flat platform or hole.
    for y,h in [(-800.62,13.01864), (-801.02,13.01849)]:
        roof(-502,y,h,'red','opposite-ridge-slopes')
    for x,y,h in [(-482,-810,10.8),(-482,-816,10.8),(-482,-821,10.8),
                  (-523,-811,13.2),(-523,-817,13.2),(-523,-821,13.2),
                  (-520,-830,26.4),(-500,-830,26.4)]:
        roof(x,y,h,'paleRoof','retained-main-or-low-connector')
    # Check all eave segments just inside the roof. Expected rise comes from
    # the associated fixed pitch plane, not an exported roof mesh.
    for i,j in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,0)]:
        a,b=CONTROL[i],CONTROL[j];p=(a+b)/2
        direction=Vector((-(b-a).y,(b-a).x,0)).normalized()
        # The outline is clockwise, so the interior is on its right.
        p-=direction*.15
        hit=ray((p.x,p.y,Z+15),(0,0,-1),5)
        assert hit and hit[3]=='red' and 10.8-tolerance < hit[1].z-Z < 11.05, ('eave connection',i,j,hit)
        samples.append(dict(kind='eave-connection',edge=[i,j],actualHeight=hit[1].z-Z))
    for x,y in [(-500,-815),(-505,-820),(-490,-810)]:
        assert ray((x,y,Z+35),(0,0,-1),34.8) is None, ('courtyard filled',x,y)
        samples.append(dict(kind='courtyard-void',position=[x,y]))
    # Main upper wall now exposed above each lower connector, facing north.
    for x in (-482,-523):
        hit=ray((x,-822,Z+16.5),(0,-1,0),4)
        assert hit and abs(hit[1].y+824.18)<.12+tolerance and hit[2].y>.98, ('exposed north main wall',x,hit)
        samples.append(dict(kind='upper-main-north-wall',x=x,actualY=hit[1].y))
    return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)


report = dict(passed=False, scope='Adopted estimated north eave 10.8 m/ridge 13.1 m, continuous stepped pitched roof, east 10.8 m and west 13.2 m connectors, cleared former eight-storey mass, exposed main walls, retained south roof and original courtyard. Whole building remains partial.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'))
    bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'))
    bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Civil rear:',report['passed'],flush=True)
