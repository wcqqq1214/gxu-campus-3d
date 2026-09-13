"""Verify shipped forecourt, stair clearance, road join and local terrain scope."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import Mesh
from site_geometry import mesh_triangles,inside,ring_distance,polygon_distance

data=json.loads((ROOT/'public/data/sites.json').read_text());site=data['sites'][0]
bs=json.loads((ROOT/'public/data/buildings.json').read_text())
b=next(b for b in bs if b['id']==site['buildingId'])
angle=site['angle'];cs=math.cos(angle);sn=math.sin(angle);ox,oy=site['origin']

def world(x,y):return ox+x*cs-y*sn,oy+x*sn+y*cs

def tree(o):
    o.data.calc_loop_triangles()
    return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
           [tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True)

def owner(o):
    while o.parent:o=o.parent
    return o

def sampler(objects):
    trees=[tree(o) for o in objects]
    def sample(x,y):
        hits=[t.ray_cast(Vector((x,y,150)),Vector((0,0,-1)),300)[0] for t in trees]
        return max((p.z for p in hits if p is not None),default=None)
    return sample

def original_terrain():
    raw=json.loads((ROOT/'public/data/terrain.json').read_text())
    infra=json.loads((ROOT/'public/data/infrastructure.json').read_text())
    courts=json.loads((ROOT/'public/data/basketball.json').read_text())
    cols,rows=raw['cols'],raw['rows'];x0,y0,x1,y1=raw['bounds'];heights=raw['heights']
    cut=set(infra['terrainCells'])|set(courts['terrainCells']);mesh=Mesh();samples=[]
    for j in range(rows-1):
        for i in range(cols-1):
            if j*(cols-1)+i in cut:continue
            points=[(x0+(x1-x0)*ii/(cols-1),y0+(y1-y0)*jj/(rows-1),heights[jj*cols+ii])
                    for ii,jj in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]]
            face=len(mesh.f);mesh.face(points,0)
            samples.append(((points[0][0]+points[2][0])/2,(points[0][1]+points[2][1])/2,face))
    for patch in infra['terrainPatch']+courts['terrainPatch']:
        for i in range(0,len(patch['triangles']),3):mesh.face([patch['vertices'][k] for k in patch['triangles'][i:i+3]],0)
    tri=mesh_triangles(mesh);bvh=BVHTree.FromPolygons(mesh.v,[t for t,_ in tri],all_triangles=True)
    # Draco quantizes a position attribute with one step based on its largest
    # component extent, including Z. This campus-wide terrain needs a larger
    # vertical bound than the independently quantized small forecourt node.
    step=max(max(v[k] for v in mesh.v)-min(v[k] for v in mesh.v) for k in range(3))/(2**15-1)
    slopes={}
    for ids,face in tri:
        a,b,c=[Vector(mesh.v[i]) for i in ids];n=(b-a).cross(c-a)
        slopes[face]=max(slopes.get(face,0),(abs(n.x)+abs(n.y))/abs(n.z)) if abs(n.z)>1e-8 else 0
    bounds=site['gradingBounds'];expected=[]
    shores=json.loads((ROOT/'public/data/shores.json').read_text())['shores']
    shore_areas=[p for s in shores for p in s['gradingPolygons']]
    pavings=json.loads((ROOT/'public/data/pavings.json').read_text())['pavings']
    paving_areas=[[p['vertices']] for p in pavings]
    excluded_shore_samples=0
    excluded_paving_samples=0
    excluded_other_site_samples=0
    for x,y,face in samples:
        if bounds[0]-1<x<bounds[2]+1 and bounds[1]-1<y<bounds[3]+1:continue
        if any(polygon_distance((x,y),p)<1 for p in shore_areas):
            excluded_shore_samples+=1;continue
        if any(polygon_distance((x,y),p)<.15 for p in paving_areas):
            excluded_paving_samples+=1;continue
        if any(polygon_distance((x,y),[s['pavingPolygon']])<.15 for s in data['sites'] if s['id']!=site['id']):
            excluded_other_site_samples+=1;continue
        hit=bvh.ray_cast(Vector((x,y,150)),Vector((0,0,-1)),300)[0]
        if hit is not None:expected.append((x,y,hit.z,step*.5*(1+slopes[face])+.002))
    print("Declared shore samples delegated to shore validator:",excluded_shore_samples,flush=True)
    print("Declared paving samples delegated to paving validator:",excluded_paving_samples,flush=True)
    print("Other declared sites delegated to their geometry validator:",excluded_other_site_samples,flush=True)
    return expected

expected=original_terrain()

def check(label):
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    site_objects=[o for o in objects if owner(o).get('siteId')==site['id']]
    assert site_objects,(label,'forecourt missing')
    assert all(owner(o).get('layer')=='roads' for o in site_objects),'Site must follow road layer visibility'
    paving=sampler(site_objects)
    ground=sampler([o for o in objects if owner(o).get('layer')=='terrain'])
    roads=sampler([o for o in objects if owner(o).get('layer')=='roads' and not owner(o).get('siteId')])
    library=sampler([o for o in objects if owner(o).get('landmark')=='library'])
    ring=site['pavingPolygon'];xmin=min(p[0] for p in ring);xmax=max(p[0] for p in ring)
    ymin=min(p[1] for p in ring);ymax=max(p[1] for p in ring)
    obstacles=[]
    for o in objects:
        if owner(o).get('layer') not in ('buildings','context'):continue
        corners=[o.matrix_world@Vector(p) for p in o.bound_box]
        if max(p.x for p in corners)>=xmin and min(p.x for p in corners)<=xmax and max(p.y for p in corners)>=ymin and min(p.y for p in corners)<=ymax:obstacles.append(o)
    building_surface=sampler(obstacles)
    max_outside=0;max_tolerance=0
    for x,y,z,compressed_bound in expected:
        tolerance=.005 if label=='source' else compressed_bound
        max_tolerance=max(max_tolerance,tolerance)
        actual=ground(x,y)
        assert actual is not None,(label,'outside terrain hole',x,y)
        error=abs(actual-z);max_outside=max(max_outside,error)
        assert error<tolerance,(label,'terrain changed outside site',error,x,y)
    # Test cross-sections between columns as well as their own shared vertices.
    columns=site['columns'];tested=0;minimum_clearance=math.inf;max_join_step=0
    stair_rises=[];edge_gaps=[];start=site['startY']
    for index in range(0,len(columns)-1,3):
        a,c=columns[index:index+2];x=(a[0]+c[0])/2;end=(a[1]+c[1])/2
        for j in range(31):
            y=start+.03+(end-start-.06)*j/30;wx,wy=world(x,y)
            h=paving(wx,wy);g=ground(wx,wy)
            assert h is not None and g is not None,(label,'forecourt hole',x,y)
            margin=h-g;minimum_clearance=min(minimum_clearance,margin)
            assert margin>.025,(label,'terrain enters paving',x,y,margin)
            obstacle=building_surface(wx,wy)
            assert obstacle is None or obstacle<=h+.03,(label,'building obstructs forecourt',x,y,obstacle,h)
            tested+=1
        # Lowest tread remains 15 cm above the paved foot, not under grass.
        px,py=world(x,start+.03);sx,sy=world(x,start-site['entry']['stepRun']/2)
        paved=paving(px,py);tread=library(sx,sy);g=ground(sx,sy)
        assert tread is not None and g is not None,(label,'missing first tread')
        rise=tread-paved;stair_rises.append(rise)
        assert .10<rise<.20 and tread-g>.10,(label,'first stair connection',rise,tread-g)
        last=None
        for j in range(math.ceil((site['roadContactDepth']+.7)/.02)):
            y=end-.3+j*.02;wx,wy=world(x,y);values=[paving(wx,wy),roads(wx,wy)]
            top=max((h for h in values if h is not None),default=None)
            if top is None:
                # Distinct material primitives can separate by one position
                # quantum at their boundary. Bound the actual gap from BOTH
                # sides, instead of accepting a missing point unconditionally.
                sides=[];spacing=.00005 if label=='source' else .0005
                for direction in [-1,1]:
                    found=None
                    for k in range(1,7):
                        xx,yy=world(x,y+direction*k*spacing)
                        hits=[paving(xx,yy),roads(xx,yy)]
                        hit=max((h for h in hits if h is not None),default=None)
                        if hit is not None:found=(k*spacing,hit);break
                    assert found is not None,(label,'road join gap wider than quantization',x,y,direction)
                    sides.append(found)
                edge_gaps.append(sum(s[0] for s in sides));top=max(s[1] for s in sides)
            if last is not None:max_join_step=max(max_join_step,abs(top-last))
            last=top
        assert max_join_step<.075,(label,'road join height jump',max_join_step)
    crowns=None
    if label=='source':
        radii={};crowns=0
        for o in objects:
            if not o.name.startswith('树木示意-'):continue
            key=o.data.name
            if key not in radii:radii[key]=max(math.hypot(v.co.x,v.co.y) for v in o.data.vertices)
            p=(o.location.x,o.location.y);ring=site['pavingPolygon']
            assert not inside(p,ring),(label,'tree in paving',o.name)
            radius=radii[key]*max(o.scale.x,o.scale.y)
            assert ring_distance(p,ring)>radius,(label,'tree crown crosses paving',o.name)
            crowns+=1
    return {'pavingSamples':tested,'minimumTerrainClearance':minimum_clearance,
            'firstStepRiseRange':[min(stair_rises),max(stair_rises)],'maxRoadJoinStepPer2cm':max_join_step,
            'quantizedMaterialEdgeGapBounds':edge_gaps,
            'unchangedTerrainSamples':len(expected),'maxOutsideTerrainError':max_outside,
            'maxOutsideTolerance':max_tolerance,'actualTreeCrownsChecked':crowns,
            'candidateBuildingMeshes':len(obstacles),'roadLayerAssigned':True,'passed':True}

check_root=Path(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--check-root=')),str(ROOT)))
bpy.ops.wm.open_mainfile(filepath=str(check_root/'blender/gxu-campus.blend'))
report={'source':check('source')}
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(check_root/'public/models/base.glb'))
report['base']=check('base')
report['toleranceBasis']='Source float precision and 15-bit base GLB position quantization; not surveyed site accuracy.'
report['passed']=True
(ROOT/'docs/model-checks/refinement/site-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
