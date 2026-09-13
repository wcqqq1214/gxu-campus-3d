"""Located north/south silhouette in source and actual compressed GLBs."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
check_root=Path(next((a.split('=',1)[1] for a in sys.argv if a.startswith('--check-root=')),str(ROOT)))
b=next(x for x in json.loads((check_root/'public/data/buildings.json').read_text()) if x['landmark']=='library')
e=b['architecture'];angle=e['angle'];ox,oy=e['origin'];z=b['elevation']

def world(x,y,h):
    return Vector((ox+x*math.cos(angle)-y*math.sin(angle),oy+x*math.sin(angle)+y*math.cos(angle),z+h))

def check(objects,label):
    trees=[]
    for o in objects:
        o.data.calc_loop_triangles()
        trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
                     [tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
    def roof(x,y):
        hits=[t.ray_cast(world(x,y,100),Vector((0,0,-1)))[0] for t in trees]
        return max((p.z-z for p in hits if p is not None),default=None)
    # Positions avoid rooftop pergola beams; parapet may add < 1 m.
    samples={'south':roof(0,-32),'northCenter':roof(0,10),
             'northWest':roof(-25,10),'northEast':roof(25,10)}
    assert all(h is not None for h in samples.values()),(label,samples)
    assert 35.9<samples['south']<37.1,(label,'south high extension',samples)
    assert 26.9<samples['northCenter']<28.1,(label,'north central body',samples)
    for name in ('northWest','northEast'):
        assert 23.4<samples[name]<24.6,(label,name,samples)
    for x,y in [(0,-4),(5,-4),(0,-9),(8,-9)]:
        assert roof(x,y) is None,(label,'court filled',x,y)
    motif_hits=[]
    for x in [-.55-6.25,-.55+6.25]:
        hits=[t.ray_cast(world(x,30,17.5),Vector((math.sin(angle),-math.cos(angle),0)),4)[0] for t in trees]
        hits=[p for p in hits if p is not None]
        assert hits,(label,'north motif missing',x)
        north=max(-(p.x-ox)*math.sin(angle)+(p.y-oy)*math.cos(angle) for p in hits)
        assert 27.37<north<27.56,(label,'north motif projection',x,north)
        motif_hits.append(north)
    return {'roofSamplesMeters':samples,'northMotifFrontY':motif_hits,'courtyardOpen':True,'passed':True}

def owner(o):
    while o.parent:o=o.parent
    return o

bpy.ops.wm.open_mainfile(filepath=str(check_root/'blender/gxu-campus.blend'))
report={'source':check([o for o in bpy.context.scene.objects if o.get('landmark')=='library'],'source')}
for label,file in [('base','base.glb'),('near','library.glb')]:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(check_root/'public/models'/file))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and owner(o).get('landmark')=='library']
    assert objects,(label,'missing library meshes')
    report[label]=check(objects,label)
report['toleranceBasis']='0.1 m vertical bounds allow compressed mesh quantization; not survey accuracy.'
report['passed']=True
(ROOT/'docs/model-checks/refinement/s3-library-envelope.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
