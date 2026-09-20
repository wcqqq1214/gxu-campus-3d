"""Fixed probes for the civil entrance's front and east return glazing."""
import bpy, sys, json, re, hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-civil-return')
CROWN_ADDED='--crown-added' in sys.argv
SIDE_WALL_ADDED='--side-wall-added' in sys.argv
PORTAL_RETURN_ADDED='--portal-return-added' in sys.argv
ID,CHUNK,Z='relation/12875606','chunk-n2-n3',4.06
CORNER=Vector((-476.769698452549,-838.0503560000666,0))
WEST=Vector((-493.45022625596147,-838.0280919998064,0))
NORTH=Vector((-476.70814668871594,-787.3774919999443,0))
U=(WEST-CORNER).normalized();N=Vector((-U.y,U.x,0))
SIDE=(NORTH-CORNER).normalized();E=Vector((SIDE.y,-SIDE.x,0))


def root_name(obj):
    while obj.parent: obj=obj.parent
    return re.sub(r'\.\d+$','',obj.name)


def check(objects,tolerance):
    trees=[]
    for obj in objects:
        if obj.type!='MESH':continue
        obj.data.calc_loop_triangles();tris=list(obj.data.loop_triangles)
        trees.append((BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                      [tuple(t.vertices) for t in tris],all_triangles=True),
                      [obj.data.materials[t.material_index].name.split('.')[0] for t in tris]))
    samples=[]
    def face(label,u,n,distance,height,material,depth):
        origin=CORNER+u*distance+n*.7+Vector((0,0,Z+height));hits=[]
        for tree,materials in trees:
            loc,normal,index,dist=tree.ray_cast(origin,-n,1)
            if loc is not None:hits.append((dist,loc,normal,materials[index]))
        hit=min(hits,key=lambda x:x[0]) if hits else None
        assert hit and hit[3]==material,('wrong curtain material',label,distance,height,material,hit)
        actual=(hit[1]-CORNER).dot(n)
        assert abs(actual-depth)<tolerance,('wrong curtain depth',label,distance,height,depth,actual)
        assert hit[2].dot(n)>.98,('wrong curtain normal',label,distance,height,hit)
        samples.append(dict(face=label,distance=distance,height=height,material=material,depth=actual))
    for label,u,n,end,columns in [('south',U,N,(WEST-CORNER).length*.91,6),('east',SIDE,E,3.7,2)]:
        start=.1;fw=.07;width=end-start;cell=(width-2*fw)/columns;row=(18.2-2*fw)/12
        for col in range(columns):
            distance=start+fw+(col+.5)*cell
            for j in range(12):face(label,u,n,distance,7.8+fw+(j+.5)*row,'glass',.04)
            for j in range(1,12):face(label,u,n,distance,7.8+fw+j*row,'white',.15)
        for col in range(1,columns):
            for height in (9,15,24):face(label,u,n,start+fw+col*cell,height,'white',.15)
        for distance in (start+fw/2,end-fw/2):
            for height in (9,15,24):face(label,u,n,distance,height,'white',.15)
        # Thin solid corner return and unchanged strip over the glazing.
        face(label,u,n,.035,16.5,'stone',0)
        if not CROWN_ADDED:
            face(label,u,n,(start+end)/2,26.2,'stone',0)
    # Keep the rest of the east facade and both lower storey joints intact.
    for distance,height in [(4.2,16.5),(8,16.5),(1.5,3.3),(1.5,6.6)]:
        if SIDE_WALL_ADDED and distance in (4.2,8):continue
        if PORTAL_RETURN_ADDED and distance==1.5:continue
        face('east-retained',SIDE,E,distance,height,'stone',0)
    return dict(passed=True,rayCount=len(samples),samples=samples,toleranceMeters=tolerance)


report=dict(passed=False,scope='South upper glazing extends to a 0.10 m corner return; 3.60 m estimated east return, two columns/twelve rows, same 7.8–26.0 m heights. Roof crown and side portal remain pending.')
if CROWN_ADDED:
    report['scope']='Retained 7.8–26.0 m south/east glazing; the two former solid roof-strip probes are superseded by the separate crown validator.'
if SIDE_WALL_ADDED:
    report['scope']+=' Two east-wall stone probes at distances 4.2/8 m are superseded by explicit white side-wall checks.'
if PORTAL_RETURN_ADDED:
    report['scope']+=' The two lower east portal probes are superseded by the side portal glazing validator.'
report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in
    ['blender/gxu-campus.blend','public/models/base.glb',f'public/models/{CHUNK}.glb','public/data/buildings.json']}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==ID],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==CHUNK],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{CHUNK}.glb'));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['passed']=True
except Exception as error: report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Civil curtain return:',report['passed'],flush=True)
