"""Read actual source/GLB low foliage, terrain support and nearby scene meshes."""
import hashlib
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'blender')]
from low_planting_contract import load_prepared
from tree_mesh_audit import snapshot
from mesh_volumes import MeshVolumes

args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
prefix = next((s.split('=',1)[1] for s in args if s.startswith('--report-prefix=')), 's4-low-planting')
if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in prefix):
    raise ValueError('Invalid report prefix')
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
items = load_prepared(ROOT)
manifest = json.loads((ROOT/'public/data/models.json').read_text())
rows = json.loads((ROOT/'public/data/vegetation.json').read_text())
fingerprints = {n:sha(ROOT/n) for n in ['blender/gxu-campus.blend', 'public/data/models.json',
                                      'public/data/low-planting.json', 'public/data/vegetation.json']}


def check(objects, foliage, terrain, tolerance):
    tv, tf, _ = snapshot(terrain)
    ground = BVHTree.FromPolygons(tv, tf, all_triangles=True)
    results = []
    for item in items:
        name = 'vegetation-low-'+item['id']
        target = next(o for o in foliage if o.get('plantingId') == item['id'])
        assert target.get('layer') == 'vegetation'
        vs, faces, bounds = snapshot(target)
        assert len(faces) < 400
        volumes = MeshVolumes(vs, faces)
        assert len(volumes.shells) == 1 and volumes.open_components == 0
        tree = BVHTree.FromPolygons(vs, faces, all_triangles=True)
        a,b = item['line']; dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        offsets=[];bottom=[]
        for vertex in vs:
            x,y,z=vertex
            along=((x-a[0])*dx+(y-a[1])*dy)/length
            lateral=(-(x-a[0])*dy+(y-a[1])*dx)/length
            assert -tolerance <= along <= length+tolerance
            assert abs(lateral) <= item['widthMeters']/2+tolerance
            hit=ground.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
            assert hit is not None
            offset=z-hit.z; offsets.append(offset)
            assert -.03-tolerance <= offset <= item['heightMeters']+tolerance, offset
            if offset < .1:bottom.append(offset)
        assert bottom and max(bottom) <= -.03+tolerance
        assert max(offsets) >= item['heightMeters']-.1
        candidates=0;collisions=[]
        for other in objects:
            if other == target or other == terrain or other.type != 'MESH' or other.get('template') is not None:
                continue
            corners=[other.matrix_world@Vector(p) for p in other.bound_box]
            lo=[min(v[i] for v in corners) for i in range(3)]
            hi=[max(v[i] for v in corners) for i in range(3)]
            if not all(bounds[0][i] <= hi[i] and bounds[1][i] >= lo[i] for i in range(3)):continue
            ov,of,_=snapshot(other);candidates+=1
            collision=tree.overlap(BVHTree.FromPolygons(ov,of,all_triangles=True))
            solid=MeshVolumes(ov,of)
            if collision or solid.witness_inside(volumes.representatives) is not None or volumes.witness_inside(solid.representatives_in_bounds(bounds)) is not None:
                collisions.append(other.name)
        assert not collisions,collisions
        results.append(dict(id=item['id'],vertices=len(vs),triangles=len(faces),
                            maximumHeightAboveTerrain=max(offsets),minimumTerrainOffset=min(offsets),
                            bottomSamples=len(bottom),nearbyMeshesChecked=candidates,
                            collisions=collisions,closedComponents=len(volumes.shells),passed=True))
    assert len(foliage) == len(items)
    return results


bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
source_objects=list(bpy.context.scene.objects)
source_foliage=[o for o in source_objects if o.type=='MESH' and o.get('plantingId')]
source=check(source_objects,source_foliage,bpy.data.objects['terrain'],.0001)
assert len([o for o in source_objects if o.name.startswith('树木示意-')]) == len(rows)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

assets=[]
def visit(value):
    if isinstance(value,dict):
        if str(value.get('url','')).endswith('.glb'):assets.append(value)
        for child in value.values():visit(child)
    elif isinstance(value,list):
        for child in value:visit(child)
visit(manifest)
base_objects=[];all_objects=[];asset_hashes={}
for item in assets:
    path=ROOT/'public'/item['url'];asset_hashes[item['url']]=sha(path)
    assert item['bytes']==path.stat().st_size and item['sha256']==asset_hashes[item['url']]
    previous=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported=list(set(bpy.data.objects)-previous)
    if item['url']=='models/base.glb':base_objects=imported
    all_objects.extend(imported)
foliage=[o for o in base_objects if o.type=='MESH' and o.get('plantingId')]
terrain=next(o for o in base_objects if o.type=='MESH' and o.get('layer')=='terrain')
shipping=check(all_objects,foliage,terrain,.025)
# GLB tree templates are local meshes: instantiate the actual runtime rows
# against each low-planting mesh using the existing independent tree audit.
from tree_mesh_audit import check_meshes
templates={}
for lod,filename in [('base','models/trees.glb'),('near','models/trees-near.glb')]:
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public'/filename))
    templates[lod]={int(o.get('template')):snapshot(o) for o in bpy.context.selected_objects
                    if o.type=='MESH' and o.get('template') is not None}
    assert set(templates[lod])=={0,1,2}
tree_check=check_meshes(rows,[(o.name,snapshot(o)) for o in foliage],templates)
assert tree_check['passed']
assert fingerprints == {n:sha(ROOT/n) for n in fingerprints}
report=dict(passed=True,source=source,shipping=shipping,treeClearance=tree_check,
            fingerprints=fingerprints,assetsSha256=asset_hashes,modelsRead=len(assets),
            scope='Actual low foliage has a closed, low mesh, supported by source/decoded terrain; whole footprint checked at preparation, actual nearby scene intersections and closed-component containment checked here. Open meshes are not capped. Runtime tree rows use both decoded tree templates.')
(ROOT/'docs/model-checks/refinement'/f'{prefix}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','source','shipping','modelsRead']}),flush=True)
