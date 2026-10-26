"""Check the saved source and decoded published LODs against independent probes."""
import json
import re
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_line_line_2d

ROOT=Path(__file__).resolve().parents[1]
l=next(x for x in json.loads((ROOT/'public/data/landmarks.json').read_text()) if x['id']=='new-east-gate')
cx,cy=l['center'];base=l['elevation']+.24


def check(objects,label):
    trees=[]
    for obj in objects:
        if obj.type!='MESH':continue
        obj.data.calc_loop_triangles();triangles=list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                      [tuple(t.vertices) for t in triangles],all_triangles=True),
                      [re.sub(r'\.\d+$','',obj.data.materials[t.material_index].name) for t in triangles]))
    def ray(x,y,z,direction,length):
        found=[]
        for tree,mats in trees:
            p,n,i,d=tree.ray_cast(Vector((cx+x,cy+y,base+z)),Vector(direction),length)
            if p is not None:found.append((d,p,mats[i]))
        return min(found,key=lambda item:item[0]) if found else None
    for x in [-3,-2,-1,1,2,3]:
        for z in [1,2.5,4.8]:
            # The deliberate lowered arms sit between these probes at z=1.24.
            assert ray(x,-4,z,(0,1,0),8) is None,(label,'unexpected geometry above/below barrier',x,z)
    for x,finish in [(-.70,'newEastBarrierWhite'),(-1,'newEastBarrierRed'),
                     (-2,'newEastBarrierWhite'),(-2.9,'newEastBarrierRed'),
                     (.70,'newEastBarrierWhite'),(1,'newEastBarrierRed'),
                     (2,'newEastBarrierWhite'),(3.6,'newEastBarrierRed')]:
        arm=ray(x,-2,1.24,(0,1,0),4)
        assert arm and arm[2]==finish and abs(arm[1].y-cy-1.05)<.01,(label,'missing/misplaced lowered arm',x,arm)
    for x in [-3.115,3.80]:
        assert ray(x,-2,1.24,(0,1,0),4) is None,(label,'arm touches tower or pier',x)
    for x in [6.1,7]:
        for z in [.6,1.5,2.35]:
            assert ray(x,-4,z,(0,1,0),8) is None,(label,'blocked pedestrian corridor',x,z)
    assert ray(4.5,-3,2,(0,1,0),6),(label,'missing ringed pier')
    assert ray(-4.9,-3,5,(0,1,0),6),(label,'missing tall west tower')
    assert ray(-4.9,-3,7.7,(0,1,0),6) is None,(label,'tower opening blocked')
    for x in [-6.35,-3.45]:
        assert ray(x,-3,7.7,(0,1,0),6),(label,'missing clad opening post',x)
    glass=ray(-4.9,-3,1.6,(0,1,0),6)
    assert glass and glass[2]=='newEastGlass',(label,'guardroom window',glass)
    # Diagonal probes catch the formerly open joins between front and side panes.
    for x in [-6.28,-3.52]:
        corner=ray(x,-3,1.6,(0,1,0),2.8)
        assert corner and corner[2]=='newEastGlass',(label,'open window corner',x,corner)
    rail=ray(-4.9,-3,1.48,(0,1,0),3)
    assert rail and rail[2]=='newEastWindowFrame',(label,'missing horizontal window rail',rail)
    # Both neighbouring panes remain visible rather than being filled by trim.
    for z in [1.1,2.1]:
        pane=ray(-4.9,-3,z,(0,1,0),3)
        assert pane and pane[2]=='newEastGlass',(label,'window rail covers pane',z,pane)
    low_finishes=set();upper_finishes=set()
    for i in range(31):
        for z,finishes in [(.6,low_finishes),(3.3,upper_finishes)]:
            hit=ray(-5.8+i*.06,-2,z,(0,1,0),1.5)
            if hit:finishes.add(hit[2])
    assert {'newEastBaseSilver','newEastAgedSilver'}<=low_finishes,(label,'missing booth base variation',low_finishes)
    assert not upper_finishes & {'newEastBaseSilver','newEastAgedSilver'},(label,'base finish extends above window')
    # The rear door is closed and must remain visible in front of the low
    # cladding. Its threshold meets the existing guardroom paving.
    for z in [.5,1.3,2.0]:
        door=ray(-4.25,3,z,(0,-1,0),2)
        assert door and door[2]=='newEastGlass' and abs(door[1].y-cy-1.8875)<.01,\
            (label,'missing/occluded rear door',z,door)
    for x in [-4.675,-3.825]:
        jamb=ray(x,3,1.5,(0,-1,0),2)
        assert jamb and jamb[2]=='newEastFrame',(label,'missing rear door jamb',x,jamb)
    threshold=ray(-4.25,1.98,.7,(0,0,-1),1)
    assert threshold and threshold[2]=='newEastBaseSilver' and abs(threshold[1].z-base-.21)<.01,\
        (label,'missing/misplaced rear door threshold',threshold)
    assert ray(-3,3.4,1.3,(0,-1,0),2) is None,(label,'rear doorway projects into lane')
    for x in [5.65,6.55,7.45]:
        for y,direction in [(-2,(0,1,0)),(2,(0,-1,0))]:
            reader=ray(x,y,1.56,direction,2)
            assert reader and reader[2]=='newEastGlass',(label,'reader facing away from approach',x,y,reader)
            for z in [1.70,1.81]:
                face=ray(x,y,z,direction,2)
                assert face and face[2]=='newEastGlass',(label,'portrait reader/lens missing',x,y,z,face)
            cover=ray(x,y,.69,direction,2)
            assert cover and cover[2]=='newEastBlue',(label,'blue reader end cover missing',x,y,cover)
    for x,y,direction in [(6.1,.23,(-1,0,0)),(6.1,-.23,(1,0,0)),
                          (7,.23,(-1,0,0)),(7,-.23,(1,0,0))]:
        leaf=ray(x,y,.89,direction,.4)
        assert leaf and leaf[2]=='newEastBlue',(label,'missing open swing leaf',x,y,leaf)
    assert ray(2.5,-3,6,(0,1,0),6),(label,'missing lintel')
    soffit=ray(2.485,0,4.85,(0,0,1),.6)
    assert soffit and soffit[2]=='newEastSilver',(label,'missing wrapped soffit rib',soffit)
    for x,y in [(5.4694,-.5),(5.3489,-.1),(5.875,.39),(6.725,.39),(7.575,.39)]:
        rib=ray(x,y,5,(0,0,1),.4)
        assert rib and rib[2]=='newEastSilver' and abs(rib[1].z-base-5.17)<.015,\
            (label,'curved/end-panel soffit rib missing or misplaced',x,y,rib)
    joint=ray(6.81,.39,5,(0,0,1),.4)
    assert joint and joint[2]=='newEastRecess' and abs(joint[1].z-base-5.24)<.015,\
        (label,'end-panel rib spacing lost',joint)
    for z,material in [(.514,'newEastAgedSilver'),(.656,'newEastSilver')]:
        ring=ray(4.5,-1,z,(0,1,0),2)
        assert ring and ring[2]==material,(label,'lower pier finish',z,ring)
    notice=ray(0,-3,1.5,(0,1,0),6)
    assert notice and notice[2]=='newEastBlue',(label,'missing central blue notice panel',notice)
    assert ray(0,-3,2.7,(0,1,0),6),(label,'missing upper checkpoint sign')
    for x in [-.49,.49]:
        equipment=ray(x,-3,.8,(0,1,0),6)
        assert equipment and equipment[2]=='newEastYellow',(label,'missing yellow checkpoint equipment',equipment)
    cap=ray(6.7,-3,6.1,(0,1,0),6)
    assert cap and cap[2]=='newEastStone',(label,'missing front-facing end panel',cap)
    assert abs(cap[1].y-cy+.4)<.02,(label,'end panel must return behind front fins',cap)
    # The photographed single seam must be recessed and survive both LODs.
    seam=ray(6.7,-3,6.245,(0,1,0),6)
    assert seam and seam[2]=='newEastRecess' and abs(seam[1].y-cy+.389)<.003, (label,'end panel seam',seam)
    for height in [5.93,6.225,6.265,6.55]:
        face=ray(6.7,-3,height,(0,1,0),6)
        assert face and face[2]=='newEastStone', (label,'extra seam or missing panel',height,face)
    texture_faces=0
    for obj in objects:
        if obj.type!='MESH':continue
        for face in obj.data.polygons:
            material=obj.data.materials[face.material_index]
            if re.sub(r'\.\d+$','',material.name)!='newEastStone':continue
            images=[n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
            assert any(tuple(img.size)==(128,128) for img in images),(label,'missing fine grain texture')
            uv=obj.data.uv_layers.active
            assert uv,(label,'end panel lost UVs during export')
            a,b=list(face.loop_indices)[:2]
            va=obj.matrix_world@obj.data.vertices[obj.data.loops[a].vertex_index].co
            vb=obj.matrix_world@obj.data.vertices[obj.data.loops[b].vertex_index].co
            assert abs((uv.data[a].uv-uv.data[b].uv).length/(va-vb).length-2)<.03,(label,'incorrect grain scale')
            texture_faces+=1
    assert texture_faces>=6,(label,'missing textured end panel faces')
    gold=[];latin_spans=[];latin_vertices=[]
    for obj in objects:
        if obj.type!='MESH':continue
        for face in obj.data.polygons:
            material=obj.data.materials[face.material_index]
            if re.sub(r'\.\d+$','',material.name)=='newEastGold':
                points=[obj.matrix_world@obj.data.vertices[i].co for i in face.vertices]
                gold.extend(points)
                if all(5.61<p.z-base<5.95 for p in points):
                    latin_vertices.extend(points)
                    latin_spans.append((min(p.x-cx for p in points),max(p.x-cx for p in points)))
    assert gold and max(v.y-cy for v in gold)<-1.4,(label,'lettering intersects front fins')
    # Count separate capitals, then inspect the seventh letter (I). A serif
    # should extend sideways at its foot while leaving that space open at mid-height.
    letters=[]
    for a,b in sorted(latin_spans):
        if letters and a<=letters[-1][1]+.0005:letters[-1][1]=max(b,letters[-1][1])
        else:letters.append([a,b])
    assert len(letters)==17,(label,'missing/merged English capitals',letters)
    low=min(v.z for v in latin_vertices)-base;high=max(v.z for v in latin_vertices)-base
    assert abs(high-low-.32)<.005 and abs(letters[-1][1]-letters[0][0]-5.8)<.01,(label,'English lettering scale')
    a,b=letters[6];x=a+(b-a)*.15
    serif=ray(x,-1.7,low+(high-low)*.04,(0,1,0),.3)
    assert serif and serif[2]=='newEastGold',(label,'missing serif on English I',serif)
    assert ray(x,-1.7,(low+high)/2,(0,1,0),.3) is None,(label,'English I lacks narrow central stem')
    canopy=ray(6.55,0,2.2,(0,0,1),2)
    assert canopy and canopy[2]=='newEastCanopyBlue',(label,'missing blue canopy',canopy)
    assert abs(canopy[1].z-base-3.225)<.025,(label,'canopy height',canopy)
    levels=[]
    for x,y,z in [(6.1,0,.16),(7,2,.16),(6.55,-3.8,-.2988),(6.55,3.8,-.2988)]:
        hit=ray(x,y,2,(0,0,-1),3)
        assert hit and abs(hit[1].z-base-z)<.015,(label,'pavement gap/step',x,y,hit)
        levels.append(round(hit[1].z,4))
    verts=[o.matrix_world@v.co for o in objects if o.type=='MESH' for v in o.data.vertices]
    site=[offset+(cx if i%2==0 else cy) for i,offset in enumerate(l['siteBoundsOffset'])]
    assert min(v.x for v in verts)>=site[0]-.02
    assert max(v.x for v in verts)<=site[2]+.02
    assert min(v.y for v in verts)>=site[1]-.02
    assert max(v.y for v in verts)<=site[3]+.02
    assert max(v.z for v in verts)<=l['elevation']+l['height']+.02
    buildings=json.loads((ROOT/'public/data/buildings.json').read_text())
    west=next(b for b in buildings if b['id']=='way/1501460937')
    # This concave footprint leaves a real gap beside the tower. An AABB-only
    # exclusion would reject the new wall even when it is outside the building.
    # Check containment, edge crossings and a 5 cm clearance against the actual
    # polygon, for the source AND both decoded LODs.
    west_clearance=float('inf')
    for poly in west['polygons']:
        ring=[Vector(p) for p in poly[0]]
        edges=list(zip(ring,ring[1:]))
        candidates=[v for v in verts if v.x<=west['bounds'][2]+.05]
        for v in candidates:
            q=Vector((v.x,v.y));inside=False
            for a,b in edges:
                ab=b-a;t=max(0,min(1,(q-a).dot(ab)/ab.length_squared))
                west_clearance=min(west_clearance,(q-a-ab*t).length)
                if (a.y>q.y)!=(b.y>q.y) and q.x<(b.x-a.x)*(q.y-a.y)/(b.y-a.y)+a.x:
                    inside=not inside
            assert not inside,(label,'gate vertex inside west building',tuple(q))
        for obj in objects:
            if obj.type!='MESH':continue
            for face in obj.data.polygons:
                points=[obj.matrix_world@obj.data.vertices[i].co for i in face.vertices]
                if min(p.x for p in points)>west['bounds'][2]+.05:continue
                for p,q in zip(points,points[1:]+points[:1]):
                    if (p.xy-q.xy).length<1e-6:continue
                    assert not any(intersect_line_line_2d(p.xy,q.xy,a,b) is not None for a,b in edges),\
                        (label,'gate face crosses west building footprint')
    assert west_clearance>.05,(label,'insufficient west building clearance',west_clearance)
    for x in [-9.6,-8.8,-7.8,-6.9]:
        cap_hit=ray(x,.2,4,(0,0,-1),2)
        assert cap_hit and cap_hit[2]=='newEastSilver' and abs(cap_hit[1].z-base-3.24)<.015,\
            (label,'missing west wall coping',x,cap_hit)
        for z in [.5,1.8,2.9]:
            assert ray(x,-1,z,(0,1,0),1.7),(label,'gap in west wall',x,z)
    east=next(b for b in buildings if b['id']=='way/1501460952')
    assert max(v.x for v in verts)<east['bounds'][0]-.05,(label,'garden overlaps East 25')
    # The low wall follows the ramp and remains outside its usable width.
    wall_levels=[]
    for y,expected in [(-1,.35),(2,.35),(3,.1359),(5,-.17),(7.7,-.17)]:
        hit=ray(8.2,y,1,(0,0,-1),2)
        assert hit and hit[2]=='newEastWallCap' and abs(hit[1].z-base-expected)<.015,(label,'wall coping/grade',y,hit)
        wall_levels.append(round(hit[1].z,4))
    for (x,y),ground in site_ground.items():
        bottom=ray(x,y,-1,(0,0,1),2)
        top=ray(x,y,4,(0,0,-1),5)
        assert bottom and top and bottom[1].z<ground-.005<top[1].z,(label,'floating or buried wall',x,y,ground,bottom,top)
    for y in [1.45,2.3,4,6.1,8.2]:
        grade=.16-min(1,max(0,(y-2.3)/1.7))*.52
        hit=ray(7.7,y,grade+1.7,(1,0,0),.6)
        assert hit and hit[2]=='newEastSilver',(label,'missing enclosure post',y,hit)
    # Extended approach stays clear even beyond the former four-metre crop.
    for x in [6.1,7,7.7]:
        assert ray(x,3.9,.7,(0,1,0),4.8) is None,(label,'fence blocks north approach',x)
    for x in [8.6,9.5,10.3]:
        assert ray(x,3,1.65,(0,1,0),.8) is None,(label,'planting exceeds low hedge envelope',x)
    notice=ray(7.7,0,1.8,(1,0,0),.4)
    assert notice and notice[2]=='newEastBlue',(label,'missing side notice backing',notice)
    assert ray(7.7,-2,1.8,(0,1,0),4) is None,(label,'notice blocks pedestrian approach')
    frame_area=0;leaf_points=[];leaf_faces=0
    for obj in objects:
        if obj.type!='MESH':continue
        for face in obj.data.polygons:
            material=re.sub(r'\.\d+$','',obj.data.materials[face.material_index].name)
            if material not in ('newEastSilver','newEastLeafTips'):continue
            points=[obj.matrix_world@obj.data.vertices[i].co for i in face.vertices]
            if material=='newEastLeafTips':
                leaf_points.extend(points);leaf_faces+=1
            elif all(abs(p.x-cx-7.965)<.002 and abs(p.y-cy)<1.226 and 1.014<p.z-base<2.666 for p in points):
                frame_area+=sum((points[i]-points[0]).cross(points[i+1]-points[0]).length/2 for i in range(1,len(points)-1))
    # The opening and border determine 0.40 m² of visible frame. Overlapping
    # rectangular rails add 0.01 m², despite passing single-hit ray probes.
    assert abs(frame_area-.40)<.002,(label,'overlapping/incomplete notice frame',frame_area)
    for y in [-1.20,1.20]:
        for z in [1.04,2.64]:
            corner=ray(8.05,y,z,(-1,0,0),.15)
            assert corner and corner[2]=='newEastSilver',(label,'open mitred frame corner',y,z,corner)
    assert leaf_faces>100,(label,'missing leafy shrub detail',leaf_faces)
    for point in leaf_points:
        x,y,z=point.x-cx,point.y-cy,point.z-base
        grade=.16-min(1,max(0,(y-2.3)/1.7))*.52
        assert 8.28<x<10.67 and -1.8<y<8.02 and grade+.06<z<grade+1.12,\
            (label,'leaf detail extends beyond low planting strip',point)
    ribs=ray(6.55,.5,2.5,(0,0,1),1)
    assert ribs and ribs[2]=='newEastSilver',(label,'missing canopy underside support',ribs)
    # Ray along each straight rail: an uncapped tube would let the ray run
    # through its centre. The cap projects past the arch face to avoid overlap.
    for x,z in [(5.2,2.91),(6.55,3.27),(7.9,2.91)]:
        end=ray(x,-2,z,(0,1,0),.4)
        assert end and end[2]=='newEastSilver' and abs(end[1].y-cy+1.895)<.004,(label,'open/overlapping canopy rail end',x,end)
    for x in [5.55,6.15,6.95,7.55]:
        rib=ray(x,.5,2.5,(0,0,1),1)
        assert rib and rib[2]=='newEastSilver',(label,'gap in continuous canopy arch',x,rib)
    for x in [8.94,9.96]:
        for y in [-1,.7,2.8,4.8,6.6,7.5]:
            hit=ray(x,y,1.5,(0,0,-1),2)
            assert hit and hit[2] in ('newEastLeaf','newEastLeafLight'),(label,'gap in continuous planting',x,y,hit)
    for x,ground in road_ground.items():
        bottom=ray(x,.35,-.5,(0,0,1),1.5)
        top=ray(x,.35,.6,(0,0,-1),1)
        assert top and bottom and top[2] in ('newEastRubber','newEastYellow'),(label,'missing speed strip',x)
        assert ground-.025<bottom[1].z<ground<top[1].z and .035<top[1].z-ground<.06,\
            (label,'floating/buried speed strip',x,ground,bottom,top)
    return dict(passed=True,vehicleApertureProbes=18,loweredBarrierProbes=8,
                cappedCanopyRails=3,continuousCanopyRibProbes=4,pedestrianProbes=6,pavingElevations=levels,
                enclosureCopingElevations=wall_levels,enclosurePosts=5,extendedPedestrianProbes=3,
                groundedWallSamples=len(site_ground),
                westWallCoverageSamples=12,westBuildingClearance=round(west_clearance,3),
                continuousPlantingSamples=12,sideNoticeClearance=True,canopyUndersideSupport=True,
                texturedEndPanelFaces=texture_faces,recessedEndPanelSeam=True,windowMeetingRail=True,soffitReturnProbes=5,
                speedStripGroundSamples=len(road_ground),openSwingLeaves=4,portraitReaderFaces=6,
                englishCapitals=len(letters),englishSerif=True,boothBaseVariation=True,
                rearDoorProbes=3,rearDoorThreshold=True,
                noticeFrameArea=round(frame_area,4),leafDetailFaces=leaf_faces,
                eastBuildingClearance=round(east['bounds'][0]-max(v.x for v in verts),3),
                endPanelY=round(cap[1].y-cy,3),letteringFrontClearance=True,
                vertices=len(verts),height=round(max(v.z for v in verts)-l['elevation'],3))


report={}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
terrain=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('layer')=='terrain']
assert terrain,'missing source terrain for wall grounding checks'
ground_trees=[(o,BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())) for o in terrain]
site_ground={}
for x,y in ([(x,y) for x in [8.15,10.8] for y in [-1,2,3,5,7.7]]+
            [(x,.2) for x in [-9.6,-8.8,-7.8,-6.9]]):
    hits=[]
    for obj,tree in ground_trees:
        origin=obj.matrix_world.inverted()@Vector((cx+x,cy+y,100))
        direction=obj.matrix_world.inverted().to_3x3()@Vector((0,0,-1))
        hit=tree.ray_cast(origin,direction,200)[0]
        if hit is not None:hits.append((obj.matrix_world@hit).z)
    assert hits,('missing ground under wall',x,y)
    site_ground[x,y]=max(hits)
roads=bpy.data.objects['roads']
road_tree=BVHTree.FromObject(roads,bpy.context.evaluated_depsgraph_get())
road_ground={}
for x in [-3,-2,-1,1,2,3]:
    point=road_tree.ray_cast(roads.matrix_world.inverted()@Vector((cx+x,cy+.35,100)),Vector((0,0,-1)),200)[0]
    assert point is not None,('missing road under speed strip',x)
    road_ground[x]=(roads.matrix_world@point).z
objects=[o for o in bpy.context.scene.objects if o.get('landmark')=='new-east-gate']
assert len(objects)==1 and len(objects[0].vertex_groups)==13
report['source']=check(objects,'source')
for name in ['base','new-east-gate']:
    raw=(ROOT/f'public/models/{name}.glb').read_bytes()
    doc=json.loads(raw[20:20+int.from_bytes(raw[12:16],'little')])
    stone=next(mat for mat in doc['materials'] if mat['name']=='newEastStone')
    texture=stone['pbrMetallicRoughness']['baseColorTexture']['index']
    embedded=doc['images'][doc['textures'][texture]['source']]
    assert 'bufferView' in embedded and 'uri' not in embedded,(name,'stone grain is not embedded')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'public/models/{name}.glb'))
    bpy.context.view_layer.update()
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('landmark')=='new-east-gate']
    assert objects,(name,'missing exported landmark')
    report[name]=check(objects,name)
for row in report.values():
    assert max(abs(a-b) for a,b in zip(row['pavingElevations'],report['source']['pavingElevations']))<.01
    assert max(abs(a-b) for a,b in zip(row['enclosureCopingElevations'],report['source']['enclosureCopingElevations']))<.01
(ROOT/'work/new-east-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False),flush=True)
