"""Check actual road meshes against buildings, including generated facade relief.

--generated checks newly generated roads against the saved building meshes before
the full rebuild. Normal execution checks the saved source and shipping GLBs.
"""
import bpy,json,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
D=json.loads((ROOT/'public/data/infrastructure.json').read_text())
B=json.loads((ROOT/'public/data/buildings.json').read_text())
BUILDING_IDS={b['id'] for b in B}
BRIDGE_IDS={b['id'] for b in D['bridges']}

def bounds(obj):
    from mathutils import Vector
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    return ([min(p[k] for p in points) for k in range(3)],
            [max(p[k] for p in points) for k in range(3)])

def overlapping(a,b):
    return all(a[0][k]<=b[1][k] and b[0][k]<=a[1][k] for k in range(3))

def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [tuple(p.vertices) for p in obj.data.polygons])

def check(roads,buildings,label):
    cache={};collisions=[];pairs=0;near_buildings=set()
    rb=[(o,bounds(o)) for o in roads if o.type=='MESH']
    bb=[(o,bounds(o)) for o in buildings if o.type=='MESH']
    for building,box in bb:
        for road,road_box in rb:
            if not overlapping(box,road_box):continue
            pairs+=1;near_buildings.add(building.get('featureId',building.name))
            for obj in [building,road]:
                if obj.name not in cache:cache[obj.name]=tree(obj)
            hits=cache[building.name].overlap(cache[road.name])
            if hits:collisions.append({'building':building.name,'featureId':building.get('featureId'),
                                      'road':road.name,'intersectingFacePairs':len(hits)})
    result={'representation':label,'buildingMeshes':len(bb),'roadMeshes':len(rb),
            'testedMeshPairs':pairs,'nearBuildings':sorted(near_buildings),'collisions':collisions}
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result

def root_name(obj):
    while obj.parent:obj=obj.parent
    return obj.name

def main():
    generated='--generated' in sys.argv;baseline='--baseline' in sys.argv
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
    building_objects=[o for o in bpy.context.scene.objects if o.get('featureId') in BUILDING_IDS]
    assert len({o['featureId'] for o in building_objects})==len(B),'Saved source does not contain all mapped buildings'
    road_objects=[o for o in bpy.context.scene.objects if o.get('infrastructureId','').startswith('infra-road-') or
                  o.get('landmark') in BRIDGE_IDS or o.name.startswith('infra-approach-')]
    if generated:
        from geometry import MATERIALS
        from infrastructure import road_chunk,bridge,approaches
        C={}
        for mat in bpy.data.materials:C[mat.name]=len(MATERIALS);MATERIALS.append(mat)
        collection=bpy.data.collections.new('道路避让预检');bpy.context.scene.collection.children.link(collection)
        from landmarks import landmark
        l=next(l for l in json.loads((ROOT/'public/data/landmarks.json').read_text()) if l['id']=='stadium')
        b=next(b for b in B if b['landmark']=='stadium')
        building_objects=[o for o in building_objects if o.get('landmark')!='stadium']
        building_objects.append(landmark(l,b,b['elevation'],C,True).object('check-stadium',collection,{'featureId':b['id']}))
        road_objects=[]
        for c in D['chunks']:
            if c['kind']=='corridor':road_objects.append(road_chunk(c,C,True).object('check-'+c['id'],collection))
        for b in D['bridges']:
            road_objects.append(bridge(b,C,True).object('check-'+b['id'],collection))
            road_objects.append(approaches(b,C).object('check-approach-'+b['id'],collection))
        for obj in road_objects:
            if not obj.name.startswith('check-infra-road-'):continue
            for p in obj.data.polygons:
                if obj.data.materials[p.material_index].name in ('asphalt','pavingRed','tactile','roadWhite','roadYellow'):
                    assert p.normal.z>.8,f'{obj.name}: folded road / sidewalk face'
    bpy.context.view_layer.update()
    source=check(road_objects,building_objects,'generated' if generated else 'source')
    if baseline:return
    assert not source['collisions'],'Road geometry intersects saved buildings'
    if generated:return
    report={'source':source}
    # Import the complete base, then replace the road and relevant building LODs
    # exactly as the viewer does. Retain all other base buildings as obstacles.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
    def is_road(o):return root_name(o).startswith(('infra-road-','infra-approach-')) or root_name(o) in {'landmark-'+i for i in BRIDGE_IDS}
    def is_building(o):return root_name(o).startswith('chunk-') or root_name(o)=='context' or (root_name(o).startswith('landmark-') and not is_road(o))
    bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if is_road(o)],
                         [o for o in bpy.context.scene.objects if is_building(o)],'base Draco')
    assert not report['base']['collisions'],'Base road/building LOD collision'
    candidates=set(source['nearBuildings'])
    chunks={b['chunk'] for b in B if b['id'] in candidates and b.get('chunk')}
    landmarks={b['landmark'] for b in B if b['id'] in candidates and b.get('landmark')}
    replaced=chunks|{'landmark-'+i for i in landmarks}
    removed=[o for o in bpy.context.scene.objects if root_name(o) in replaced]
    for obj in removed:bpy.data.objects.remove(obj,do_unlink=True)
    for name in sorted(chunks|landmarks):bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models'/f'{name}.glb'))
    bpy.context.view_layer.update()
    report['nearBuildingsBaseRoad']=check([o for o in bpy.context.scene.objects if is_road(o)],
                         [o for o in bpy.context.scene.objects if is_building(o)],'near buildings / base road Draco')
    assert not report['nearBuildingsBaseRoad']['collisions'],'Mixed road/building LOD collision'
    replaced={'landmark-'+i for i in BRIDGE_IDS}|{c['id'] for c in D['chunks'] if c['kind']=='corridor'}
    removed=[o for o in bpy.context.scene.objects if root_name(o) in replaced]
    for obj in removed:bpy.data.objects.remove(obj,do_unlink=True)
    files=BRIDGE_IDS|{c['id'] for c in D['chunks'] if c['kind']=='corridor'}
    for name in sorted(files):bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models'/f'{name}.glb'))
    bpy.context.view_layer.update()
    report['near']=check([o for o in bpy.context.scene.objects if is_road(o)],
                         [o for o in bpy.context.scene.objects if is_building(o)],'near Draco')
    assert not report['near']['collisions'],'Near road/building LOD collision'
    report['result']='passed'
    (ROOT/'docs/model-checks/road-building-clearance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
