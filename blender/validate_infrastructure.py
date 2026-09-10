"""Check actual saved and Draco-decoded geometry, then render inspection angles."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT/'public/data/infrastructure.json').read_text())
out = ROOT/'docs/model-checks'; out.mkdir(exist_ok=True)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mesh_bvh(objects):
    vertices=[]; faces=[]
    for obj in objects:
        if obj.type != 'MESH': continue
        offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(i+offset for i in p.vertices) for p in obj.data.polygons)
    assert vertices, 'Missing infrastructure mesh'
    return BVHTree.FromPolygons(vertices, faces)

def check_rail_intersections(obj):
    """Intersect the actual lower railing faces with the bridge structure."""
    group=next(g for g in obj.vertex_groups if g.name.startswith('坡道'))
    indices={v.index for v in obj.data.vertices if any(g.group==group.index for g in v.groups)}
    def part_bvh(railing):
        faces=[tuple(p.vertices) for p in obj.data.polygons if all((i in indices)==railing for i in p.vertices)]
        return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],faces)
    collisions=part_bvh(True).overlap(part_bvh(False))
    assert not collisions, f'{obj.name}: pedestrian railing intersects bridge structure ({len(collisions)} face pairs)'
    return len(collisions)

def check_walkways(bvh,b,label,tolerance=.06):
    """Probe real surfaces and a standing person's volume across both full walks."""
    walk=b['pedestrian'];path=walk['path'];frames=[]
    for i in range(len(path)):
        a=path[max(0,i-1)];c=path[min(len(path)-1,i+1)]
        axis=Vector((c[0]-a[0],c[1]-a[1],0)).normalized();frames.append(axis)
    samples=0;directions=0;minimum_headroom=math.inf
    for side in [-1,1]:
        for offset in [walk['innerOffset']+.35,walk['innerOffset']+walk['width']/2,
                       walk['innerOffset']+walk['width']-.35]:
            points=[]
            for p,axis in zip(path,frames):
                points.append(Vector((p[0]-axis.y*side*offset,p[1]+axis.x*side*offset,p[2])))
            for a,c in zip(points,points[1:]):
                for t in [.2,.5,.8]:
                    p=a.lerp(c,t)
                    hit=bvh.ray_cast(p+Vector((0,0,.3)),Vector((0,0,-1)),.8)[0]
                    assert hit and abs(hit.z-p.z)<tolerance, f'{label} {b["name"]}: pedestrian floor missing at {tuple(p)}'
                    roof=bvh.ray_cast(p+Vector((0,0,.3)),Vector((0,0,1)),8)[0]
                    headroom=roof.z-hit.z if roof else math.inf
                    minimum_headroom=min(minimum_headroom,headroom)
                    assert headroom >= walk['clearance']-tolerance, f'{label} {b["name"]}: pedestrian headroom {headroom:.3f} at {tuple(p)}'
                    samples+=1
                for start,end in [(a,c),(c,a)]:
                    ray=end-start
                    hit=bvh.ray_cast(start+Vector((0,0,1.7)),ray.normalized(),ray.length)[0]
                    assert hit is None, f'{label} {b["name"]}: pedestrian path blocked at {tuple(hit) if hit else None}'
                    directions+=1
    return {'id':b['id'],'floorAndHeadroomSamples':samples,'clearWalkingSegments':directions,
            'minimumPedestrianHeadroomMeters':round(minimum_headroom,3)}

def check_deck_surface(bvh,b,label):
    a,c=b['upper'];axis=Vector((c[0]-a[0],c[1]-a[1],0));length=axis.length;axis.normalize()
    normal=Vector((-axis.y,axis.x,0));highest=-math.inf;samples=0
    for lane in [-2.5,0,2.5]:
        for i in range(5,math.floor(length/.15)-5):
            point=Vector((*a,b['deckElevation']))+axis*(i*.15)+normal*lane
            hit=bvh.ray_cast(point+Vector((0,0,.65)),Vector((0,0,-1)),1)[0]
            assert hit is not None, f'{label} {b["name"]}: missing public-road deck'
            protrusion=hit.z-point.z;highest=max(highest,protrusion);samples+=1
            assert protrusion<.08, f'{label} {b["name"]}: lower geometry protrudes through road by {protrusion:.3f} m at {tuple(point)}'
    return {'id':b['id'],'samples':samples,'maximumRoadProtrusionMeters':round(highest,3)}

def check_voids(bvh, b, label, tolerance=.05):
    bearing=math.radians(b['frontBearing'])
    direction=Vector((math.sin(bearing),math.cos(bearing),0))
    normal=Vector((direction.y,-direction.x,0))
    center=Vector((*b['center'],b['floorElevation']))
    heads=[]; beam_clearances=[]
    for side in [-1,1]:
        lane=center+normal*(side*2.5)
        floor_hit=bvh.ray_cast(lane+Vector((0,0,.6)),Vector((0,0,-1)),1)[0]
        assert floor_hit and abs(floor_hit.z-center.z)<tolerance, f'{label} {b["name"]}: missing lane floor'
        roof_hit=bvh.ray_cast(lane+Vector((0,0,.6)),Vector((0,0,1)),8)[0]
        assert roof_hit and roof_hit.z-center.z >= b['clearance']-tolerance, f'{label} {b["name"]}: terrain fills opening'
        heads.append(round(roof_hit.z-floor_hit.z,3))
        # Sample densely enough to hit the 24 cm exposed beams, not only the slab.
        for step in range(-50,51):
            point=lane+direction*(step*.1)+Vector((0,0,.6))
            overhead=bvh.ray_cast(point,Vector((0,0,1)),8)[0]
            assert overhead is not None, f'{label} {b["name"]}: missing covered deck'
            beam_clearances.append(overhead.z-center.z)
        # Ray across the complete covered public-road width at pedestrian height.
        reach=math.dist(b['portalCenter'],b['center'])+2
        for sign in [-1,1]:
            origin=lane+direction*(reach*sign)+Vector((0,0,1.7))
            hit=bvh.ray_cast(origin,-direction*sign,reach*2)[0]
            assert hit is None, f'{label} {b["name"]}: lane {side} passage blocked at {tuple(hit) if hit else None}'
    assert abs(min(beam_clearances)-b['clearance'])<tolerance, f'{label} {b["name"]}: beam clearance differs'
    return {'id':b['id'],'openLaneDirections':4,'sampleHeadroomsMeters':heads,
            'beamSamples':len(beam_clearances),'minimumBeamClearanceMeters':round(min(beam_clearances),3)}

reset()
names={b['name'] for b in data['bridges']}
with bpy.data.libraries.load(str(ROOT/'blender/gxu-campus.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n in names or n.startswith(('农院路 ·','infra-approach-')) or n in ('terrain','roads','green','water')]
for obj in dst.objects:bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.update()
source_objects=list(bpy.context.scene.objects)
source_bvh=mesh_bvh(source_objects)
report={'source': [check_voids(source_bvh,b,'source') for b in data['bridges']]}
report['sourcePedestrian']=[check_walkways(source_bvh,b,'source') for b in data['bridges']]
report['sourceDeckSurface']=[check_deck_surface(source_bvh,b,'source') for b in data['bridges']]
report['railingBridgeIntersections']={}
for b in data['bridges']:
    obj=next(o for o in source_objects if o.get('landmark')==b['id'])
    assert obj.get('layer')=='roads' and len(obj.vertex_groups)>=3, f'{b["name"]}: editable groups missing'
    report['railingBridgeIntersections'][b['id']]=check_rail_intersections(obj)
# Both travel directions must have visible, upward-facing paint.
paint_faces=0
for obj in source_objects:
    if not obj.get('infrastructureId','').startswith('infra-road-'):continue
    for p in obj.data.polygons:
        if obj.data.materials[p.material_index].name=='roadWhite':
            assert p.normal.z>.8, f'{obj.name}: inverted road paint'
            paint_faces+=1
assert paint_faces>100
report['sourceRoadPaintFaces']=paint_faces

if '--no-render' not in sys.argv:
    scene=bpy.context.scene; scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1440; scene.render.resolution_y=900; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'
    # Workbench shadow maps streak across this kilometre-scale ground mesh.
    # Studio light and cavity shading show the source geometry without that artifact.
    scene.display.shading.show_shadows=False; scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH'; scene.display.shading.background_type='WORLD'
    scene.world=bpy.data.worlds.new('桥梁检查背景'); scene.world.color=(.68,.73,.72)
    scene.view_settings.view_transform='Standard'; scene.view_settings.exposure=1
    cam=bpy.data.objects.new('路桥检查相机',bpy.data.cameras.new('路桥检查相机'))
    scene.collection.objects.link(cam); scene.camera=cam; cam.data.type='PERSP'; cam.data.lens=42
    for b in data['bridges']:
        angle=math.radians(b['frontBearing']); direction=Vector((math.sin(angle),math.cos(angle),0)); side=Vector((direction.y,-direction.x,0))
        center=Vector((*b['center'],b['floorElevation']))
        positions=[(center+direction*63+side*32+Vector((0,0,34)),center+Vector((0,0,3))),
                   (center+direction*33+side*2.5+Vector((0,0,5.7)),center+Vector((0,0,2.7)))]
        for index,(location,target) in enumerate(positions,1):
            cam.location=location;cam.rotation_euler=(target-location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(out/f'{b["id"]}-{index}.png');bpy.ops.render.render(write_still=True)

# Decode the actual shipping base plus independent detail bridges. Importer restores Z-up.
reset()
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'))
bpy.context.view_layer.update()
base_bvh=mesh_bvh(bpy.context.scene.objects)
report['basePedestrian']=[check_walkways(base_bvh,b,'base Draco',.1) for b in data['bridges']]
def root_name(obj):
    while obj.parent: obj=obj.parent
    return obj.name
bridge_roots={'landmark-'+b['id'] for b in data['bridges']}
for obj in list(bpy.context.scene.objects):
    root=root_name(obj)
    if root in bridge_roots or obj.get('layer') in ('buildings','context','sports'):
        bpy.data.objects.remove(obj,do_unlink=True)
# Remove unrelated buildings, retaining all ground to expose terrain regressions.
for obj in list(bpy.context.scene.objects):
    if obj.type=='MESH' and not root_name(obj).startswith(('terrain','roads','green','water','infra-')):
        bpy.data.objects.remove(obj,do_unlink=True)
for b in data['bridges']:bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models'/f'{b["id"]}.glb'))
bpy.context.view_layer.update()
decoded=mesh_bvh(bpy.context.scene.objects)
report['dracoDecoded']=[check_voids(decoded,b,'Draco',.08) for b in data['bridges']]
report['dracoPedestrian']=[check_walkways(decoded,b,'Draco',.1) for b in data['bridges']]
report['dracoDeckSurface']=[check_deck_surface(decoded,b,'Draco') for b in data['bridges']]
report['result']='passed'
(out/'infrastructure-geometry-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False),flush=True)
