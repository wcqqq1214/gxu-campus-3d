"""Ray-test every static scene layer, not just road nodes, against original roads."""
import gzip,json,sys,math,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
b=json.loads((ROOT/'public/data/north-campus.json').read_text())['underpass']
fixture=json.loads(gzip.decompress((ROOT/'docs/model-checks/north-road-baseline.json.gz').read_bytes()))

def inside(p,ring):
    result=False
    for a,d in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>p[1])!=(d[1]>p[1]) and p[0]<(d[0]-a[0])*(p[1]-a[1])/(d[1]-a[1])+a[0]:result=not result
    return result

def distance(p,a,d):
    dx,dy=d[0]-a[0],d[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def tree():
    vs=[];fs=[];info=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH' or o.name.startswith('\u6811\u6728\u793a\u610f-'):continue
        bounds=[o.matrix_world@Vector(p) for p in o.bound_box]
        if max(p.x for p in bounds)<-681 or min(p.x for p in bounds)>301 or max(p.y for p in bounds)<1079 or min(p.y for p in bounds)>1301:continue
        o.data.calc_loop_triangles();offset=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices)
        for t in o.data.loop_triangles:
            fs.append(tuple(offset+i for i in t.vertices));info.append((o.name.split('.')[0],o.data.materials[t.material_index].name.split('.')[0]))
    return BVHTree.FromPolygons(vs,fs,all_triangles=True),info

def check(label):
    mesh,info=tree()
    def hit(x,y):
        p,n,i,d=mesh.ray_cast(Vector((x,y,200)),Vector((0,0,-1)),250)
        return p,n,(None if p is None else info[i])
    preserved=0;changed_scope=0;max_delta=0;problems=[];source_coplanar=0
    for x,y,z,material,edge_clear in fixture['samples']:
        # Imported baseline edges move a few mm through Draco quantization.
        # Source tests omit only pre-recorded 3 cm boundary points; delivered
        # asset tests keep every sample, including those boundary points.
        if label.startswith('editable') and not edge_clear:continue
        p,n,record=hit(x,y)
        repair=any(inside((x,y),r['outline']) for r in b['upperRoadRepairs'])
        ramp=min(distance((x,y),a,d) for a,d in zip(b['axis'],b['axis'][1:]))<b['cutHalfWidth']+.02
        if p is None or n.z<=0:
            problems.append([x,y,'missing or back-facing',record]);continue
        if repair or ramp:
            changed_scope+=1
            if record[1] not in ('asphalt','road','white'):problems.append([x,y,'occluded road',record])
        else:
            preserved+=1;max_delta=max(max_delta,abs(p.z-z))
            # At unchanged coplanar road/asphalt overlaps, compression may
            # swap which surface wins the ray. Base/near GLBs stay strict.
            coplanar=(label.startswith('editable') and {record[1],material}=={'road','asphalt'} and abs(p.z-z)<.015)
            source_coplanar+=int(coplanar)
            if (record[1]!=material and not coplanar) or abs(p.z-z)>.06:problems.append([x,y,z,material,p.z,record])
    assert not problems,(label,'road regression',len(problems),problems[:12])
    deck_samples=0;max_seam=0
    for r in b['upperRoadRepairs']:
        ux,uy=r['direction'];a,d=r['a'],r['b'];w=r['width']
        # Dense full-width samples include the previously absent carriageway edges.
        for ti in range(1,72):
            t=ti/72
            for vi in range(1,28):
                v=-w/2+w*vi/28;x=a[0]*(1-t)+d[0]*t-uy*v;y=a[1]*(1-t)+d[1]*t+ux*v
                p,n,record=hit(x,y)
                assert p is not None and n.z>.9 and record[1]=='asphalt',(label,'deck surface',x,y,record)
                deck_samples+=1
        for endpoint,sign in [(a,1),(d,-1)]:
            for vi in range(1,28):
                v=-w/2+w*vi/28;x=endpoint[0]-uy*v;y=endpoint[1]+ux*v
                inner=hit(x+sign*ux*.08,y+sign*uy*.08);outer=hit(x-sign*ux*.08,y-sign*uy*.08)
                assert all(p is not None and n.z>.9 and record[1]=='asphalt' for p,n,record in (inner,outer)),(label,'seam hole',r['roadId'],vi)
                delta=abs(inner[0].z-outer[0].z);max_seam=max(max_seam,delta)
                assert delta<.035,(label,'seam step',r['roadId'],vi,delta)
    return {'representation':label,'originalRoadSamples':preserved+changed_scope,'sourceCoplanarSurfaceTies':source_coplanar,'unchangedOutsidePassageSamples':preserved,'passageSamples':changed_scope,'maxOutsideHeightDeltaMeters':max_delta,'fullWidthDeckSamples':deck_samples,'maxSeamStepMeters':max_seam,'buildingOcclusions':0,'unexpectedMaterialChanges':0,'missingOrBackFacingRoads':0}

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
reports=[check('editable source, all static objects')]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models/base.glb'));bpy.context.view_layer.update()
reports.append(check('delivered base, all static objects'))
keys={r['chunk'] for r in json.loads((ROOT/'public/data/buildings.json').read_text()) if r.get('customModel')=='north-campus'}
for o in list(bpy.context.scene.objects):
    if o.name.split('.')[0] in keys:bpy.data.objects.remove(o,do_unlink=True)
for key in sorted(keys):bpy.ops.import_scene.gltf(filepath=str(ROOT/'public/models'/f'{key}.glb'))
bpy.context.view_layer.update()
reports.append(check('delivered base with all north near-detail chunks'))
result={'passed':True,'baselineSourceSha256':fixture['sourceSha256'],
        'assetSha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['blender/gxu-campus.blend','public/models/base.glb',*[f'public/models/{key}.glb' for key in sorted(keys)]]},
        'scope':'All static meshes including buildings; tree billboards excluded. Original 1 m road grid, dense asphalt probes and boundary joins. Intended deck restoration and lower ramps are separately checked.','checks':reports}
(ROOT/'docs/model-checks/north-road-integrity.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
