"""Compare an actual grounded service road and its retained joins with baseline."""
import argparse,json,math,sys,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from inspect_foundation_clearance import top_tree,layer,covers
from shore_geometry import nearest


def scene(path):
    if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update();objects=list(bpy.context.scene.objects)
    trees=[top_tree([o for o in objects if layer(o)==kind])[0] for kind in ('terrain','roads')]
    vertices=[];faces=[]
    for o in objects:
        if o.type!='MESH' or layer(o)!='roads':continue
        start=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);o.data.calc_loop_triangles()
        for t in o.data.loop_triangles:
            ids=tuple(start+i for i in t.vertices);a,b,c=[vertices[i] for i in ids];n=(b-a).cross(c-a)
            if n.length>1e-8 and abs(n.z)/n.length<.001:faces.append(ids)
    return trees+[BVHTree.FromPolygons(vertices,faces,all_triangles=True)]


def height(tree,xy):
    hit=tree.ray_cast(Vector((*xy,150)),Vector((0,0,-1)),300)[0]
    return None if hit is None else hit.z


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--candidate',type=Path);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    record=json.loads((ROOT/'public/data/foundations.json').read_text())['foundations'][0]['groundedServiceRoad']
    points=[];x0,y0,x1,y1=record['bounds']
    for ix in range(math.floor(x0*2),math.ceil(x1*2)):
        for iy in range(math.floor(y0*2),math.ceil(y1*2)):
            xy=(ix*.5+.13,iy*.5+.17)
            if covers(xy,record['polygons']):
                d=min(nearest(line,*xy)[0] for line in record['contacts'])
                # Keep a 5 cm edge margin for independently quantized exports.
                edge=min(nearest(line,*xy)[0] for line in record['freeEdges'])
                if min(edge,d)>.05:points.append((xy,'core' if covers(xy,record['corePolygons']) else 'transition'))
    # Contact intersections and a dense outside collar must retain old heights.
    retained=[]
    for ix in range(math.floor(x0)-2,math.ceil(x1)+3):
        for iy in range(math.floor(y0)-2,math.ceil(y1)+3):
            xy=(ix+.37,iy+.29)
            if not covers(xy,record['polygons']) and min(nearest(line,*xy)[0] for poly in record['polygons'] for line in poly)>.05:
                retained.append(xy)
    seam=[];inside_seam=[]
    for line in record['contacts']:
        for a,b in zip(line,line[1:]):
            length=math.dist(a,b)
            if length<.01:continue
            for i in range(max(1,math.ceil(length/.25))):
                t=(i+.5)/max(1,math.ceil(length/.25));x,y=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
                nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
                if covers((x+nx*.03,y+ny*.03),record['polygons']):nx,ny=-nx,-ny
                seam.append((x+nx*.03,y+ny*.03));inside_seam.append((x-nx*.03,y-ny*.03))
    _,reference_road,_=scene(args.baseline/'blender/gxu-campus.blend')
    # Compare retained roads with the unchanged source plane. A previous
    # campus-sized quantization grid is not the reference for physical height.
    # Keep a 5 cm interior collar for old road edges in both representations.
    retained=[xy for xy in retained if height(reference_road,xy) is not None and all(height(reference_road,(xy[0]+dx,xy[1]+dy)) is not None for dx,dy in ((.05,0),(-.05,0),(0,.05),(0,-.05)))]
    reference_outside=[height(reference_road,xy) for xy in retained]
    reps=[]
    paths=[('source',Path('blender/gxu-campus.blend')),('base',Path('public/models/base.glb'))]
    if args.candidate:paths=paths[:1]
    for name,relative in paths:
        ground0,road0,_=scene(args.baseline/relative)
        old=[(height(ground0,xy),height(road0,xy)) for xy,_ in points]
        outside=[(height(ground0,xy),height(road0,xy)) for xy in retained]
        joins=[height(reference_road,xy) for xy in seam]
        expected=[]
        for outside_xy,inside_xy in zip(seam,inside_seam):
            hit,normal,_,_=reference_road.ray_cast(Vector((*outside_xy,150)),Vector((0,0,-1)),300)
            expected.append(None if hit is None else hit.z+(normal.x*(hit.x-inside_xy[0])+normal.y*(hit.y-inside_xy[1]))/normal.z)
        path=args.candidate or ROOT/relative;ground,road,sides=scene(path)
        rows=[]
        for (xy,kind),(g0,r0) in zip(points,old):
            g,r=height(ground,xy),height(road,xy)
            rows.append({'xy':xy,'kind':kind,'gap':None if r is None else r-g,'oldGap':None if r0 is None else r0-g0,'groundDelta':abs(g-g0)})
        core=[r['gap'] for r in rows if r['kind']=='core' and r['gap'] is not None]
        transition=[r['gap'] for r in rows if r['kind']=='transition' and r['gap'] is not None]
        ground_delta=[];road_delta=[];previous_road_delta=[];missing_outside=0
        for xy,(g0,previous_road),r0 in zip(retained,outside,reference_outside):
            g,r=height(ground,xy),height(road,xy)
            if g0 is not None and g is not None:ground_delta.append(abs(g-g0))
            if r0 is not None:
                if r is None:missing_outside+=1
                else:
                    road_delta.append(abs(r-r0))
                    if previous_road is not None:previous_road_delta.append(abs(r-previous_road))
        missing_contacts=sum(z is not None and height(road,xy) is None for xy,z in zip(seam,joins))
        missing_repaired_contacts=sum(z is not None and height(road,xy) is None for xy,z in zip(inside_seam,expected))
        inside_join_delta=[abs(height(road,xy)-z) for xy,z in zip(inside_seam,expected) if z is not None and height(road,xy) is not None]
        join_delta=[abs(height(road,xy)-z) for xy,z in zip(seam,joins) if z is not None and height(road,xy) is not None]
        tolerance=.003 if name=='source' else .025
        side_samples=0;missing_sides=[]
        for line in record['freeEdges']:
            for a,b in zip(line,line[1:]):
                length=math.dist(a,b)
                if length<.1:continue
                nx,ny=(b[1]-a[1])/length,-(b[0]-a[0])/length
                count=max(1,math.ceil(length/1.5))
                for i in range(count):
                    t=(i+.5)/count;x,y=a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])
                    g,r=height(ground,(x-nx*.03,y-ny*.03)),height(road,(x-nx*.03,y-ny*.03))
                    side_samples+=1
                    if r is None or g is None:missing_sides.append([x,y]);continue
                    hit=sides.ray_cast(Vector((x+nx*.2,y+ny*.2,(r+g)/2)),Vector((-nx,-ny,0)),.4)[0]
                    if hit is None:missing_sides.append([x,y])
        report={'representation':name,'missingContactExamples':[xy for xy,z in zip(seam,joins) if z is not None and height(road,xy) is None],
            'missingRetainedRoadExamples':[xy for xy,(g,z) in zip(retained,outside) if z is not None and height(road,xy) is None][:5],
            'missingContacts':missing_contacts,'missingRepairedContacts':missing_repaired_contacts,'sideSamples':side_samples,'missingSides':len(missing_sides),'missingSideExamples':missing_sides[:5],'samples':len(rows),'coreSamples':len(core),'transitionSamples':len(transition),
            'worstCore':sorted([r for r in rows if r['kind']=='core' and r['gap'] is not None],key=lambda r:abs(r['gap']-.08),reverse=True)[:5],
            'worstContacts':sorted([{'xy':xy,'old':z,'new':height(road,xy),'delta':abs(height(road,xy)-z)} for xy,z in zip(seam,joins) if z is not None and height(road,xy) is not None],key=lambda r:r['delta'],reverse=True)[:5],
            'coreGapRange':[min(core),max(core)],'transitionGapRange':[min(transition),max(transition)],
            'buriedBefore':sum(r['oldGap'] is not None and r['oldGap']<-.03 for r in rows),
            'buriedAfter':sum(r['gap'] is not None and r['gap']<-.03 for r in rows),
            'missingRoad':sum(r['gap'] is None for r in rows),'retainedSamples':len(retained),'retainedRoadSamples':len(road_delta),
            'missingRetainedRoad':missing_outside,'retainedRoadReference':'baseline source planes; 5 cm interior edge margin','maximumRetainedRoadDelta':max(road_delta,default=0),'maximumPreviousRepresentationRoadDelta':max(previous_road_delta,default=0),
            'maximumGroundDelta':max(ground_delta+[r['groundDelta'] for r in rows]),
            'worstRepairedContacts':sorted([{'xy':xy,'expected':z,'actual':height(road,xy),'delta':abs(height(road,xy)-z)} for xy,z in zip(inside_seam,expected) if z is not None and height(road,xy) is not None],key=lambda r:r['delta'],reverse=True)[:5],
            'repairedContactSamples':len(inside_join_delta),'maximumRepairedContactError':max(inside_join_delta,default=0),
            'contactSamples':len(join_delta),'maximumContactDelta':max(join_delta,default=0),'tolerance':tolerance,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        report['passed']=bool(core and transition and join_delta) and report['missingRoad']==report['buriedAfter']==missing_outside==len(missing_sides)==missing_contacts==missing_repaired_contacts==0 and max(abs(g-record['offset']) for g in core)<tolerance and min(transition)>.04 and report['maximumRetainedRoadDelta']<tolerance and report['maximumContactDelta']<tolerance and report['maximumRepairedContactError']<.05 and report['maximumGroundDelta']<tolerance
        reps.append(report);print('ROAD_AUDIT',report,flush=True)
    result={'surfaceId':record['surfaceId'],'representations':reps,'passed':all(r['passed'] for r in reps)}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:raise AssertionError('Service road validation failed')


if __name__=='__main__':main()
