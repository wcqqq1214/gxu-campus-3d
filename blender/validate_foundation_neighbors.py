"""Compare actual before/after ground, retained roads, and neighboring floors."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from inspect_foundation_clearance import top_tree,layer,covers
from site_geometry import ring_distance


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--source',type=Path,default=ROOT/'blender/gxu-campus.blend')
    parser.add_argument('--source-only',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    record=json.loads((ROOT/'public/data/foundations.json').read_text())['foundations'][0]
    x0,y0,x1,y1=record['bounds'];points=set()
    for ix in range(math.floor((x0-10)*2),math.ceil((x1+10)*2)):
        for iy in range(math.floor((y0-10)*2),math.ceil((y1+10)*2)):
            points.add((ix/2+.17,iy/2+.19))
    for poly in record['gradingPolygons']:
        for ring in poly:
            for a,b in zip(ring,ring[1:]):
                n=max(1,math.ceil(math.dist(a,b)))
                for i in range(n+1):points.add(tuple(a[k]+(b[k]-a[k])*i/n for k in range(2)))
    neighbor=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/957404989')
    neighbor_points=[]
    for poly in neighbor['polygons']:
        for ring in poly:
            for a,b in zip(ring,ring[1:]):
                n=max(1,math.ceil(math.dist(a,b)/.5))
                neighbor_points.extend(tuple(a[k]+(b[k]-a[k])*i/n for k in range(2)) for i in range(n+1))
    neighbor_points=set(neighbor_points)
    points.update(neighbor_points);points=sorted(points)
    def read(path):
        if path.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
        bpy.context.view_layer.update()
        objects=list(bpy.context.scene.objects)
        ground,_=top_tree([o for o in objects if layer(o)=='terrain'])
        road,_=top_tree([o for o in objects if layer(o)=='roads'])
        def hit(tree,p):
            result=tree.ray_cast(Vector((*p,150)),Vector((0,0,-1)),300)[0]
            return None if result is None else result.z
        return {p:(hit(ground,p),hit(road,p)) for p in points}
    source_baseline=read(args.baseline/'blender/gxu-campus.blend')
    reports=[]
    paths=[('source',args.source)]
    if not args.source_only:paths.append(('base',ROOT/'public/models/base.glb'))
    for label,path in paths:
        old=source_baseline if label=='source' else read(args.baseline/'public/models/base.glb')
        current=read(path);tol=.002 if label=='source' else .025
        errors=[];outside_points=[];outside=[];support=[];retained=[];road_points=[];old_export_deltas=[];neighbors=[]
        for p,(g,r) in current.items():
            bg,old_export_road=old[p]
            source_ground,br=source_baseline[p]
            if g is None:errors.append(['missing ground',p]);continue
            distance=min(ring_distance(p,ring) for poly in record['gradingPolygons'] for ring in poly)
            if not covers(p,record['gradingPolygons']) or distance<1e-6:
                outside.append(abs(g-bg));outside_points.append((abs(g-bg),p,g,bg))
            trimmed=any(covers(p,[[m+[m[0]]]]) for m in record['roadTrimMasks'])
            trim_edge=min(ring_distance(p,m+[m[0]]) for m in record['roadTrimMasks'])
            # Boundary rounding can change road hit/no-hit; evaluate interior.
            if not trimmed and trim_edge>.05 and br is not None and r is None:
                adjacent=[(p[0]+dx,p[1]+dy) for dx,dy in ((-.5,0),(.5,0),(0,-.5),(0,.5))]
                if all(source_baseline.get(q,(None,None))[1] is not None for q in adjacent):
                    errors.append(['missing retained road interior',p])
            if not trimmed and trim_edge>.05 and br is not None and r is not None:
                retained.append(abs(r-br));support.append(abs((r-g)-(br-source_ground)));road_points.append((abs(r-br),p,r,br,g,source_ground))
                if old_export_road is not None:old_export_deltas.append(abs(r-old_export_road))
            if p in neighbor_points:neighbors.append(abs(g-bg))
        for name,values in [('outside',outside),('road',retained),('roadSupport',support),('neighbor',neighbors)]:
            if not values or max(values)>tol:errors.append([name,max(values,default=None),tol])
        report={'representation':label,'samples':len(points),'outsideSamples':len(outside),
                'maximumOutsideGroundChange':max(outside),'worstOutsideSamples':sorted(outside_points,reverse=True)[:5],'retainedRoadSamples':len(retained),
                'maximumRetainedRoadErrorToSource':max(retained),'maximumRoadChangeFromPreviousExport':max(old_export_deltas,default=0),'worstRoadSamples':sorted(road_points,reverse=True)[:5],'maximumRoadSupportChange':max(support),
                'neighborId':neighbor['id'],'neighborPerimeterSamples':len(neighbors),
                'maximumNeighborGroundChange':max(neighbors),'errors':errors,'passed':not errors}
        reports.append(report)
    result={'passed':all(r['passed'] for r in reports),'representations':reports,
            'scope':'0.5m grid, grading boundary at 1m, physics perimeter at 0.5m; representation-matched ground baselines; retained road height/support checked against unchanged source planes, not old quantized road levels'}
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
    print('FOUNDATION_NEIGHBORS',json.dumps(result),flush=True)
    assert result['passed'],result

if __name__=='__main__':main()
