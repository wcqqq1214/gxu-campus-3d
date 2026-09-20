"""Inspect the actual turned path, both interfaces and outside terrain."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from site_geometry import inside,ring_distance
PREFIX=next((s.split('=',1)[1] for s in sys.argv if s.startswith('--report-prefix=')),'s3-mathematics-path')
BASELINE=next((Path(s.split('=',1)[1]).resolve() for s in sys.argv if s.startswith('--baseline=')),ROOT/'work/refinement-s3-mathematics-path-before')
TARGET=next((Path(s.split('=',1)[1]).resolve() for s in sys.argv if s.startswith('--check-root=')),ROOT)
SITE_ID=next((s.split('=',1)[1] for s in sys.argv if s.startswith('--site-id=')),'mathematics-north-connection')
site=next(s for s in json.loads((ROOT/'public/data/sites.json').read_text())['sites'] if s['id']==SITE_ID)
grounded=next((p for p in json.loads((ROOT/'public/data/pavings.json').read_text())['pavings'] if p['surfaceId']==site.get('surfaceId') and 'groundedService' in p),None)
front=site.get('type') in ('front-connection','terraced-stair-connection')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']==site['buildingId'])
angle=site['angle'];cs,sn=math.cos(angle),math.sin(angle);ox,oy=site['origin']
def world(x,y):return ox+x*cs-y*sn,oy+x*sn+y*cs
def owner(o):
    while o.parent:o=o.parent
    return o
def sampler(objects):
    ts=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();ts.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
    def height(x,y,bottom=-100,top=100):
        hits=[t.ray_cast(Vector((x,y,top)),Vector((0,0,-1)),top-bottom)[0] for t in ts]
        return max((h.z for h in hits if h is not None),default=None)
    return height
bpy.ops.wm.open_mainfile(filepath=str(BASELINE/'blender/gxu-campus.blend'))
old_ground=sampler([o for o in bpy.context.scene.objects if o.get('layer')=='terrain'])
old_roads=sampler([o for o in bpy.context.scene.objects if o.get('layer')=='roads'])

def check(label):
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    selected=[o for o in objects if owner(o).get('siteId')==site['id']]
    assert selected,('side connection missing',label)
    assert all(owner(o).get('layer')=='roads' for o in selected)
    path=sampler(selected);ground=sampler([o for o in objects if owner(o).get('layer')=='terrain'])
    roads=sampler([o for o in objects if owner(o).get('layer')=='roads'])
    building_objects=[o for o in objects if o.get('featureId')==b['id'] or owner(o).name==b['chunk']]
    building=sampler(building_objects)
    flush=site['entry'].get('flushEntrance')
    portal_front=max(flush['pierDepth']-.03,.18) if flush else 0
    tolerance=.004 if label=='source' else .025
    ring=site['localPolygon'];xmin=min(p[0] for p in ring);xmax=max(p[0] for p in ring);ymin=min(p[1] for p in ring);ymax=max(p[1] for p in ring)
    count=0;clearances=[];outside_errors=[]
    for ix in range(math.floor((xmin-4)*2),math.ceil((xmax+4)*2)):
        for iy in range(math.floor((ymin-4)*2),math.ceil((ymax+4)*2)):
            x,y=ix/2+.13,iy/2+.17;wx,wy=world(x,y)
            if inside((x,y),ring) and ring_distance((x,y),ring)>.06:
                h,g=path(wx,wy),ground(wx,wy);assert h is not None and g is not None,('path or ground hole',x,y)
                clearances.append(h-g);assert h-g>.055,('ground intersects connector',x,y,h-g)
                # Check usable approach headroom, allowing a real high canopy.
                # Footprint validation separately excludes solid building bodies.
                obstruction=building(wx,wy,bottom=h+.03,top=h+2.1)
                if not flush or y>portal_front+.025:
                    # The approach must be clear beyond the closed door/frame
                    # envelope. Door leaves and their jambs occupy that envelope
                    # intentionally; this is not an indoor walk-through test.
                    assert obstruction is None,('building blocks approach headroom',x,y,obstruction,h)
                count+=1
            elif ring_distance((x,y),ring)>.2:
                old,new=old_ground(wx,wy),ground(wx,wy);assert old is not None and new is not None
                outside_errors.append(abs(old-new));assert abs(old-new)<tolerance,('terrain changed outside connection',x,y,old,new)
    flush='flushEntrance' in site['entry']
    rises=[];w=site['halfWidth']*2 if 'halfWidth' in site else site['entry']['stairFlight' if front else 'attachedPortico']['width']
    for x in [-w/2+.2,-w/4,0,w/4,w/2-.2]:
        if flush:
            paved=path(*world(x,site['startY']+.025))
            expected=b['elevation']+site['entry']['flushEntrance']['floorHeight']
            assert paved is not None and abs(paved-expected)<.025,('flush door threshold join',x,paved,expected)
            rises.append(expected-paved)
            continue
        paved=path(*world(x,site['startY']+.025));tread=building(*world(x,site['startY']-.15))
        assert paved is not None and tread is not None
        if 'terracedStairs' in site['entry']:
            stairs=site['entry']['terracedStairs']
            expected=(stairs['intermediateHeight']-stairs['baseHeight'])/stairs['lowerRisers']
        else:expected=(site['entry']['landingHeight']-site['stairBaseHeight'])/site['entry']['stairFlight']['riserCount'] if front else .12
        rises.append(tread-paved)
        assert (abs(tread-paved-expected)<.03 if front else .085<tread-paved<.15),('stair join height',x,tread-paved)
    joins=[];max_jump=0;gap_bounds=[];max_jump_at=None
    for a,c in zip(site['columns'],site['columns'][1:]):
        x,y=(a[0]+c[0])/2,(a[1]+c[1])/2
        wx,wy=world(x,y+.05) if front else world(x-.05,y)
        if grounded:
            # These civil contacts lie outside the target road's end blends;
            # the separate road validator checks those blends and both joins.
            assert all(ring_distance((wx,wy),[j['a'],j['b'],j['a']])>grounded['joinFeather'] for j in grounded['joins']), 'Contact lies in road end blend'
            expected=old_ground(wx,wy)+grounded['groundedService']['offset']
        else:expected=old_roads(wx,wy)
        contact=path(wx,wy)
        assert expected is not None and contact is not None
        joins.append(abs(expected-contact));assert abs(expected-contact)<tolerance,('road contact differs from reference plane',x,y)
        previous=None
        for i in range(101):
            xx,yy=(x,y-.3+i*.02) if front else (x+.3-i*.02,y)
            h=roads(*world(xx,yy))
            if h is None:
                # A point exactly on separate float32/material boundaries may
                # miss both triangles. Measure both sides of the gap instead
                # of accepting an unbounded missing point.
                spacing=.00005 if label=='source' else .0005;found=[]
                for direction in [-1,1]:
                    for k in range(1,7):
                        nearby=roads(*world(xx,yy+direction*k*spacing) if front else world(xx+direction*k*spacing,yy))
                        if nearby is not None:
                            found.append((k*spacing,nearby));break
                assert len(found)==2,('gap across footway contact exceeds precision bound',xx,yy)
                gap_bounds.append(sum(d for d,_ in found));h=max(v for _,v in found)
            if previous is not None and abs(h-previous)>max_jump:
                max_jump=abs(h-previous);max_jump_at=(xx,yy,previous,h)
            previous=h
        assert max_jump<.06,('footway join step',max_jump,max_jump_at)
    return {'pavingSamples':count,'minimumGroundClearance':min(clearances),'outsideTerrainSamples':len(outside_errors),
        'approachHeadroomCheckedMeters':2.1,
        'closedPortalEnvelopeDepth':portal_front,'approachObstructionStart':portal_front+.025 if flush else 0,
        'maximumOutsideTerrainError':max(outside_errors),
        ('thresholdOffsetRange' if flush else 'stairRiseRange'):[min(rises),max(rises)],
        'maximumContactRoadPlaneError':max(joins),'maximumRoadJoinStepPer2cm':max_jump,
        'measuredMaterialGapUpperBounds':gap_bounds,'passed':True}

report={'siteId':site['id'],'scope':'Actual source/base path width, stair or flush threshold, mapped road plane/contact, clear ground and unchanged ground outside the connector. Dimensions remain estimates.','passed':False}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'));report['source']=check('source')
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update();report['base']=check('base')
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb','public/data/models.json','public/data/sites.json']};report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/f'docs/model-checks/refinement/{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('Side connection actual geometry',report['passed'],flush=True)
