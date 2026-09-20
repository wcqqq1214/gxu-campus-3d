"""Fixed map-space probes for the adopted top-storey recessed window bays."""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-recess')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
A=Vector((-493.43996762938485,-834.8777359997714,0))
B=Vector((-537.9008578510263,-834.8220759999119,0))
U=(B-A).normalized();N=Vector((-U.y,U.x,0));L=(B-A).length
INSET=L*.025;BAY=L*.95/13

def root_name(obj):
    while obj.parent:obj=obj.parent
    return re.sub(r'\.\d+$','',obj.name)

def check(objects,tolerance):
    trees=[]
    for obj in objects:
        if obj.type!='MESH':continue
        obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
    def point(u,depth,h):return A+U*u+N*depth+Vector((0,0,Z+h))
    def ray(origin,direction,limit):
        hits=[]
        for tree,materials in trees:
            loc,normal,index,dist=tree.ray_cast(origin,direction,limit)
            if loc is not None:hits.append((dist,loc,normal,materials[index]))
        return min(hits,key=lambda h:h[0]) if hits else None
    samples=[]
    def front(u,h,material,depth):
        hit=ray(point(u,.6,h),-N,1.8)
        assert hit and hit[3]==material,('front material',u,h,material,hit)
        actual=(hit[1]-A).dot(N)
        assert abs(actual-depth)<tolerance,('wrong recess depth',u,h,depth,actual)
        assert hit[2].dot(N)>.98,('reversed front face',u,h,hit)
        samples.append(dict(kind='front',u=u,height=h,material=material,expectedDepth=depth,actualDepth=actual))
    for bay in range(13):
        center=INSET+(bay+.5)*BAY
        front(center,25.4,'glass',-.81)
        front(center,25.075,'white',-.76)
        front(center+BAY*.4,25.4,'stone',-.95)
        front(center,23.55,'white',0)
        assert ray(point(center,.3,25.4),-N,.6) is None,('old flush window/wall blocks recess',bay)
        samples.append(dict(kind='openRecess',bay=bay))
        for start,direction,expected,material in [(24.3,-1,23.1,'white'),(25.5,1,26.22,'white'),(28,-1,26.4,'paleRoof')]:
            hit=ray(point(center,-.5,start),Vector((0,0,direction)),3)
            assert hit and hit[3]==material and abs(hit[1].z-Z-expected)<tolerance,('floor/ceiling/roof',bay,expected,hit)
            assert hit[2].z*direction<-.98,('floor/ceiling/roof normal',bay,expected,hit)
            samples.append(dict(kind='horizontal',bay=bay,expectedHeight=expected,actualHeight=hit[1].z-Z))
    for i in range(14):
        u=INSET+i*BAY;front(u,25.4,'stone',0)
        # Probe both sides, including end piers, inside the window groove.
        for side in (-1,1):
            hit=ray(point(u+side*.6,-.5,25.4),-U*side,.8)
            actual=(hit[1]-A).dot(U) if hit else None
            assert hit and hit[3]=='stone' and abs(actual-(u+side*.21))<tolerance,('pier width/side',i,side,hit)
            assert hit[2].dot(U*side)>.98,('pier side normal',i,side,hit)
            samples.append(dict(kind='pierSide',pier=i,side=side,actualU=actual))
    return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='Only original south edge 1 top storey: 13 estimated 0.95 m recessed bays, 14 piers, lower solid spandrel, rear windows, floor, soffit, original roof. Does not establish an accessible corridor or surveyed dimensions.')
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['passed']=True
except Exception as error:report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Civil top recess:',report['passed'],flush=True)
