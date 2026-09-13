"""Inspect saved and decoded paving against the preserved pre-repair assets."""
import bpy,json,math,sys,re
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from site_geometry import inside
record=json.loads((ROOT/'public/data/pavings.json').read_text())['pavings'][0]
previous=ROOT/'work/refinement-s4-shore-complete'
ring=record['vertices'];box=record['bounds'];prefix='paving-'+record['id']
baseline=json.loads((ROOT/'docs/model-checks/refinement/s4-paving-before-geometry.json').read_text())
def root(o):
    while o.parent:o=o.parent
    return o
def name(o):return re.sub(r'\.\d{3,}$','',root(o).name)
def geometry(objects):
    vertices=[];faces=[];area=0
    for o in objects:
        o.data.calc_loop_triangles()
        for t in o.data.loop_triangles:
            p=[o.matrix_world@o.data.vertices[i].co for i in t.vertices]
            if max(v.x for v in p)<box[0]-4 or min(v.x for v in p)>box[2]+4 or max(v.y for v in p)<box[1]-4 or min(v.y for v in p)>box[3]+4:continue
            offset=len(vertices);vertices.extend(p);faces.append((offset,offset+1,offset+2))
            area+=abs((p[1]-p[0]).cross(p[2]-p[0]).z)/2
    return (BVHTree.FromPolygons(vertices,faces,all_triangles=True) if faces else None),area
def snapshot(path):
    if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(path))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    result={}
    for key,predicate in [('terrain',lambda o:root(o).get('layer')=='terrain'),('roads',lambda o:root(o).get('layer')=='roads'),('paving',lambda o:name(o)==prefix),('contact',lambda o:name(o).startswith(prefix+'-contact-'))]:
        selected=[o for o in objects if predicate(o)]
        result[key],result[key+'Area']=geometry(selected)
        extents=[]
        for o in selected:
            corners=[o.matrix_world@Vector(p) for p in o.bound_box]
            extents.append(max(max(p[k] for p in corners)-min(p[k] for p in corners) for k in range(3)))
        result[key+'Step']=max(extents,default=0)/(2**15-1)
        if key in ('paving','contact'):assert all(root(o).get('layer')=='roads' for o in selected)
    return result
def height(tree,x,y):
    hit=tree.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)[0]
    return None if hit is None else hit.z
def check(kind,old,new):
    compressed=kind=='base'
    bounds=report['results']['source']['quantizationComparisonBounds'] if compressed else None
    tol=bounds['roads'] if compressed else .001
    terrain_tol=bounds['terrain'] if compressed else .001
    assert new['paving'] and new['contact'],'Missing paving or actual-road contact mesh'
    edge_rows=[];free_closed=0;join_steps=[]
    sign=1 if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))>0 else -1
    for before in baseline['samples'][kind]:
        edge=before['edge'];a,b=ring[edge],ring[(edge+1)%len(ring)];x,y=before['xy']
        length=math.dist(a,b);nx,ny=-(b[1]-a[1])/length*sign,(b[0]-a[0])/length*sign
        z=height(new['paving'],x+nx*.12,y+ny*.12);g=height(new['terrain'],x+nx*.12,y+ny*.12)
        assert z is not None and g is not None,(kind,'missing original boundary',edge)
        outside=height(new['roads'],x-nx*.12,y-ny*.12)
        if edge in record['joinEdges']:
            assert outside is not None,(kind,'missing contact road',edge)
            delta=z-outside;join_steps.append(abs(delta))
            assert abs(delta)<.03,(kind,'join step',edge,before['t'],delta)
        if before['adjacentRoadZ'] is None:
            hit,normal,_,_=new['paving'].ray_cast(Vector((x-nx*.3,y-ny*.3,(z+g)/2)),Vector((nx,ny,0)),.6)
            assert hit is not None and abs(normal.z)<.2,(kind,'unclosed free edge',edge,before['t'])
            assert normal.x*(-nx)+normal.y*(-ny)>.9,(kind,'inward side face',edge)
            free_closed+=1
        edge_rows.append({'edge':edge,'t':before['t'],'xy':[x,y],'beforeJoinStepMeters':before['joinStep'],'afterJoinStepMeters':None if outside is None else z-outside,'aboveGroundMeters':z-g,'previouslyExposedEdgeClosed':before['adjacentRoadZ'] is None})
    # Dense tests cover the seam between the original 25 inspection stations.
    seam=[];contact_errors=[]
    for join in record['joins']:
        a,b=join['a'],join['b'];nx,ny=join['inward']
        for i in range(101):
            t=(i+.5)/101;x=a[0]*(1-t)+b[0]*t;y=a[1]*(1-t)+b[1]*t
            p=height(new['paving'],x+nx*.005,y+ny*.005);c=height(new['contact'],x-nx*.005,y-ny*.005)
            assert p is not None and c is not None,(kind,'seam hole',t)
            seam.append(abs(p-c))
            qx,qy=x-nx*.3,y-ny*.3
            p=height(old['roads'],qx,qy);c=height(new['contact'],qx,qy)
            assert p is not None and c is not None,(kind,'contact hole',t)
            contact_errors.append(abs(p-c))
    assert max(seam)<.025,(kind,'dense seam step',max(seam))
    assert max(contact_errors)<tol,(kind,'original contact road moved',max(contact_errors))
    unchanged=[];ground_errors=[];clearance=[];road_errors=[];interior=0;holes=[];worst_interior=None;slopes={'terrain':0,'roads':0};ground_increases=[]
    for ix in range(math.floor(box[0])-3,math.ceil(box[2])+3):
        for iy in range(math.floor(box[1])-3,math.ceil(box[3])+3):
            x,y=ix+.137,iy+.271;g=height(new['terrain'],x,y);og=height(old['terrain'],x,y)
            assert g is not None and og is not None
            if not compressed:
                for layer in slopes:
                    for state in [old,new]:
                        hit,n,_,_=state[layer].ray_cast(Vector((x,y,200)),Vector((0,0,-1)),400)
                        if hit is not None and abs(n.z)>1e-6:slopes[layer]=max(slopes[layer],(abs(n.x)+abs(n.y))/abs(n.z))
            p=height(new['paving'],x,y)
            if inside((x,y),ring):
                ground_increases.append(g-og)
                assert g-og<terrain_tol,(kind,'ground raised beneath paving',x,y,g-og,terrain_tol)
                if p is None:holes.append([x,y]);continue
                clearance.append(p-g);interior+=1
                outside_strip=all((x-j['a'][0])*j['inward'][0]+(y-j['a'][1])*j['inward'][1]>record['joinFeather']+.01 for j in record['joins'])
                if outside_strip:
                    op=height(old['roads'],x,y);assert op is not None;unchanged.append(abs(p-op))
                    if worst_interior is None or abs(p-op)>worst_interior[0]:worst_interior=[abs(p-op),x,y,op,p]
            else:
                ground_errors.append(abs(g-og))
                assert p is None,(kind,'paving extends outside original footprint',x,y)
                op=height(old['roads'],x,y)
                if op is not None:
                    np=height(new['roads'],x,y);assert np is not None,(kind,'outside road hole',x,y)
                    road_errors.append(abs(np-op))
    assert not holes,(kind,'paving holes',holes[:10])
    assert min(clearance)>.025,(kind,'paving intersects ground',min(clearance))
    # The old drape subdivided only one side of a long triangle edge. Its
    # shared edge had different heights (9.1 mm at the diagnosed station).
    # Joining those planes is an intentional local continuity correction.
    interior_tol=tol+.012 if compressed else .012
    assert max(unchanged)<interior_tol,(kind,'interior continuity correction exceeds bound',worst_interior)
    assert max(ground_errors)<terrain_tol,(kind,'outside terrain changed',max(ground_errors),terrain_tol)
    assert max(road_errors)<tol,(kind,'outside road changed',max(road_errors))
    area_error=abs(new['pavingArea']-record['areaMeters2'])
    assert area_error<(.08 if compressed else .003),(kind,'paving projected area changed',area_error)
    quantization_bounds={layer:max(old[layer+'Step'],new[layer+'Step'])*(1+slopes[layer])+.003 for layer in slopes} if not compressed else bounds
    return {'originalEdgeSamples':edge_rows,'closedOriginalFreeEdgeSamples':free_closed,'maximumOriginalJoinStepMeters':max(join_steps),'denseSeamSamples':len(seam),'maximumDenseSeamStepMeters':max(seam),'maximumContactRoadChangeMeters':max(contact_errors),'pavingGridSamples':interior,'holes':holes,'minimumPavingAboveGroundMeters':min(clearance),'interiorComparisonSamples':len(unchanged),'maximumInteriorChangeMeters':max(unchanged),'interiorToleranceMeters':interior_tol,'interiorToleranceReason':'Original partially subdivided triangle boundary had unequal heights; continuity repair is bounded separately from unchanged road/terrain planes.','unchangedTerrainSamples':len(ground_errors),'maximumTerrainChangeMeters':max(ground_errors),'maximumGroundIncreaseMeters':max(ground_increases),'terrainComparisonToleranceMeters':terrain_tol,'outsideRoadSamples':len(road_errors),'maximumOutsideRoadChangeMeters':max(road_errors),'projectedAreaErrorMeters2':area_error,'comparisonToleranceMeters':tol,'quantizationComparisonBounds':quantization_bounds,'quantizationBoundReason':'Two independently quantized 15-bit surfaces: max node extent / 32767 times (1 + maximum sampled SOURCE L1 slope), plus 3 mm numerical allowance. Source invariance is checked separately.','roadsLayerAssigned':True,'passed':True}
report={'surfaceId':record['surfaceId'],'scope':'Saved source and decoded GLB: original failing edges, dense seam and contact road, exposed side normals, original footprint and interior, surrounding roads and terrain outside the footprint. Intruding ground is lowered beneath paving. Dimensions remain estimates.','results':{}}
for kind,relative in [('source','blender/gxu-campus.blend'),('base','public/models/base.glb')]:
    old=snapshot(previous/relative);new=snapshot(ROOT/relative)
    report['results'][kind]=check(kind,old,new)
report['passed']=True
out=ROOT/'docs/model-checks/refinement/paving-geometry.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
