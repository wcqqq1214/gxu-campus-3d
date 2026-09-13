"""Check actual saved and shipped shore against the accepted pre-shore model."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from site_geometry import polygon_distance
from shore_geometry import core_stations
shore=json.loads((ROOT/'public/data/shores.json').read_text())['shores'][0]
previous=ROOT/'work/refinement-s4-background-complete'

def root(o):
    while o.parent:o=o.parent
    return o

def tree(objects):
    vs=[];faces=[]
    for o in objects:
        o.data.calc_loop_triangles();offset=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices)
        faces.extend(tuple(offset+i for i in t.vertices) for t in o.data.loop_triangles)
    assert faces,'Missing expected mesh'
    return BVHTree.FromPolygons(vs,faces,all_triangles=True)

def snapshot():
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    terrain=tree([o for o in objects if root(o).get('layer')=='terrain'])
    roads=tree([o for o in objects if root(o).get('layer')=='roads'])
    water=tree([o for o in objects if root(o).name.split('.')[0]=='water'])
    wall_objects=[o for o in objects if root(o).name.split('.')[0]=='shore-'+shore['id']]
    if wall_objects:assert all(root(o).get('layer')=='water' for o in wall_objects)
    wall=tree(wall_objects) if wall_objects else None
    return terrain,roads,water,wall

def height(bvh,x,y):
    hit=bvh.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
    return None if hit is None else hit.z

def open_model(path):
    if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path))
    return snapshot()

def check(kind,old,current):
    ground,roads,water,wall=current;old_ground,old_roads,old_water,_=old
    assert wall is not None,(kind,'shore wall missing')
    compressed=kind=='base';tolerance=.12 if compressed else .003
    cap_errors=[];freeboards=[];front_hits=[];land_gaps=[];water_errors=[]
    for a,b in zip(shore['core'],shore['core'][1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);nx,ny=-dy/l*shore['outwardSign'],dx/l*shore['outwardSign']
        for i in range(13):
            t=(i+.1)/13;x=a[0]+dx*t;y=a[1]+dy*t
            origin=Vector((x-nx*.75,y-ny*.75,shore['waterLevel']+.2))
            hit,normal,_,distance=wall.ray_cast(origin,Vector((nx,ny,0)),1.25)
            assert hit is not None and abs(normal.z)<.2,(kind,'open wall at water level',x,y)
            front_hits.append(distance)
            top=height(wall,x+nx*.2,y+ny*.2);assert top is not None,(kind,'cap gap',x,y)
            cap_errors.append(abs(top-(shore['waterLevel']+shore['freeboard'])))
            g=height(ground,x+nx*.8,y+ny*.8);assert g is not None
            freeboards.append(g-shore['waterLevel'])
            rear=height(ground,x+nx*.45,y+ny*.45);land_gaps.append(top-rear)
            w=height(water,x-nx*.2,y-ny*.2);ow=height(old_water,x-nx*.2,y-ny*.2)
            assert w is not None and ow is not None;water_errors.append(abs(w-ow))
    assert max(cap_errors)<(.008 if compressed else .0001),(kind,'cap height',max(cap_errors))
    assert min(freeboards)>.25,(kind,'land remains below water',min(freeboards))
    assert min(land_gaps)>-.01 and max(land_gaps)<.2,(kind,'wall/land join',min(land_gaps),max(land_gaps))
    assert max(water_errors)<.001,(kind,'water moved')
    baseline=json.loads((ROOT/'docs/model-checks/refinement/s4-shore-before-ground.json').read_text())
    baseline_contacts=[];stations=core_stations(shore)
    for sample in baseline['samples']:
        x,y=sample['xy'];_,normal=min(stations,key=lambda s:math.dist(s[0],(x,y)))
        # Sample inside the cap rather than its quantized boundary, including
        # the original two endpoints and the shared mapped corner.
        qx,qy=x+normal[0]*.2,y+normal[1]*.2
        for end,neighbor in [(shore['core'][0],shore['core'][1]),(shore['core'][-1],shore['core'][-2])]:
            if math.dist((x,y),end)<1e-6:
                length=math.dist(end,neighbor);qx+=(neighbor[0]-end[0])*.05/length;qy+=(neighbor[1]-end[1])*.05/length
        top=height(wall,qx,qy)
        assert top is not None and abs(top-shore['waterLevel']-shore['freeboard'])<.008,(kind,'original failing station has no cap',x,y)
        baseline_contacts.append({'xy':[x,y],'capSampleXY':[qx,qy],'previousWaterMinusGroundMeters':sample['waterMinusGround'],
                                  'newCapAboveWaterMeters':top-shore['waterLevel']})
    outside=[];road_errors=[];inside_count=0;raised=[];holes=[]
    x0,y0,x1,y1=shore['gradingBounds']
    for ix in range(math.floor(x0)-3,math.ceil(x1)+4):
        for iy in range(math.floor(y0)-3,math.ceil(y1)+4):
            x,y=ix+.137,iy+.271
            a=height(old_ground,x,y);b=height(ground,x,y)
            if a is not None and b is None:holes.append([x,y])
            if a is None or b is None:continue
            distance=min(polygon_distance((x,y),p) for p in shore['gradingPolygons'])
            if distance>(.15 if compressed else .0001):outside.append(abs(a-b))
            else:inside_count+=1;raised.append(b-a)
            a=height(old_roads,x,y);b=height(roads,x,y)
            if a is not None:
                assert b is not None,(kind,'road missing');road_errors.append(abs(a-b))
    assert not holes,(kind,'terrain holes',holes[:5])
    assert outside and max(outside)<tolerance,(kind,'outside terrain changed',max(outside))
    assert road_errors and max(road_errors)<(.015 if compressed else .001),(kind,'existing road changed',max(road_errors))
    return {'wallWaterlineRays':len(front_hits),'originalFailingStations':baseline_contacts,'maxCapHeightErrorMeters':max(cap_errors),'minimumLandFreeboardMeters':min(freeboards),'wallToLandGapRangeMeters':[min(land_gaps),max(land_gaps)],'unchangedWaterSamples':len(water_errors),'maxWaterChangeMeters':max(water_errors),'outsideTerrainSamples':len(outside),'maxOutsideTerrainChangeMeters':max(outside),'outsideToleranceMeters':tolerance,'insideTerrainSamples':inside_count,'maximumLocalRaiseMeters':max(raised),'existingRoadSamples':len(road_errors),'maxRoadChangeMeters':max(road_errors),'terrainHoles':holes,'waterLayerAssigned':True,'passed':True}

old=open_model(previous/'blender/gxu-campus.blend');current=open_model(ROOT/'blender/gxu-campus.blend');source=check('source',old,current)
old=open_model(previous/'public/models/base.glb');current=open_model(ROOT/'public/models/base.glb');base=check('base',old,current)
report={'shoreId':shore['id'],'source':source,'base':base,'scope':'Actual local terrain, original route and water, cap and waterline closure. Shape/position evidence and estimated dimensions are documented separately.','passed':True}
(ROOT/'docs/model-checks/refinement/shore-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
