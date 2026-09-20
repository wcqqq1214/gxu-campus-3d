"""Fixed map-space probes for the adopted seventh-storey recess and retained top-only separators."""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-seventh')
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
def root_name(obj):
    while obj.parent:obj=obj.parent
    return re.sub(r'\.\d+$','',obj.name)

def check(objects,tolerance):
    trees=[]
    for obj in objects:
        if obj.type!='MESH':continue
        obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(t.vertices) for t in tris],all_triangles=True),[obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
    def ray(origin,direction,limit):
        hits=[]
        for tree,materials in trees:
            loc,normal,index,dist=tree.ray_cast(origin,direction,limit)
            if loc is not None:hits.append((dist,loc,normal,materials[index]))
        return min(hits,key=lambda h:h[0]) if hits else None
    samples=[]
    # Independent map anchors and adopted heights, not read from current config.
    for name,a,b,count,inset,sign in [
        ('south',(-493.43996762938485,-834.8777359997714),(-537.9008578510263,-834.8220759999119),13,None,1),
        ('west',(-548.7011505155482,-834.8085552565082),(-537.9008578510263,-834.8220759999119),3,.4,-1)]:
        A=Vector((*a,0));B=Vector((*b,0));U=(B-A).normalized();N=Vector((-U.y,U.x,0))*sign;L=(B-A).length
        inset=L*.025 if inset is None else inset;bay=(L-2*inset)/count
        def point(u,d,h):return A+U*u+N*d+Vector((0,0,Z+h))
        def front(u,h,material,depth,kind):
            hit=ray(point(u,.6,h),-N,1.8)
            assert hit and hit[3]==material,(name,kind,u,h,material,hit)
            actual=(hit[1]-A).dot(N)
            assert abs(actual-depth)<tolerance,(name,kind,'depth',depth,actual)
            assert hit[2].dot(N)>.98,(name,kind,'normal',hit)
            samples.append(dict(facade=name,kind=kind,along=u,height=h,material=material,expectedDepth=depth,actualDepth=actual))
        def horizontal(u,d,start,direction,expected,kind):
            hit=ray(point(u,d,start),Vector((0,0,direction)),3)
            assert hit and hit[3]=='white' and abs(hit[1].z-Z-expected)<tolerance,(name,kind,expected,hit)
            assert hit[2].z*direction<-.98,(name,kind,'normal',hit)
            samples.append(dict(facade=name,kind=kind,along=u,expectedHeight=expected,actualHeight=hit[1].z-Z))
            return hit[1].z-Z
        for i in range(count):
            center=inset+(i+.5)*bay
            front(center,21.1,'glass',-.81,'recessed-glass')
            front(center,21.775,'white',-.76,'rear-window-crossbar')
            front(center+bay*.32,21.1,'white',-.75,'rear-window-jamb')
            front(center+bay*.4,21.1,'stone',-.95,'rear-solid-wall')
            front(center,22.8,'stone',-.95,'rear-wall-above-window')
            front(center,20.3,'white',0,'lower-solid-spandrel')
            assert ray(point(center,.3,21.1),-N,.6) is None,(name,'old flush window or wall',i)
            samples.append(dict(facade=name,kind='front-clearance',bay=i))
            horizontal(center,-.5,21,-1,19.8,'floor-top')
            horizontal(center,-.5,22.4,1,22.92,'ceiling-underside')
            underside=horizontal(center,-.5,19.55,1,19.71,'first-slab-underside')
            ledge=horizontal(center,.42,19.9,-1,19.698,'retained-sixth-ledge')
            assert underside>ledge,(name,'first slab touches or intersects old ledge',underside,ledge)
            samples.append(dict(facade=name,kind='positive-slab-ledge-separation',gap=underside-ledge))
        for i in range(1,count):
            along=inset+i*bay
            front(along,21.1,'stone',-.95,'continuous-lower-recess-between-bays')
            assert ray(point(along,.3,21.1),-N,.6) is None,(name,'upper separator incorrectly extended down',i)
            samples.append(dict(facade=name,kind='no-lower-separator',separator=i))
            front(along,25.4,'stone',0,'retained-top-separator')
        # Both end returns still terminate the recess at the adopted inset.
        for side,along in [(-1,inset),(1,L-inset)]:
            hit=ray(point(along-side*.3,-.5,21.1),U*side,.5)
            assert hit and hit[3]=='stone' and abs((hit[1]-A).dot(U)-along)<tolerance,(name,'end return',side,hit)
            assert hit[2].dot(-U*side)>.98,(name,'end return normal',side,hit)
            samples.append(dict(facade=name,kind='end-return',side=side))
    return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)

report=dict(passed=False,scope='South seventh-storey recess and western continuation: 13+3 window bays, 0.95 m setback, 0.09 m first slab, retained middle ledge with positive separation, and deep dividers only on the eighth storey. Estimated exterior form, not surveyed dimensions or accessible-corridor evidence.')
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
    print('Civil seventh recess:',report['passed'],flush=True)
