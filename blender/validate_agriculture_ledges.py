"""Probe actual triangulated source and shipping ledges, plus empty space and windows."""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s3-agriculture-ledges')
b=next(x for x in json.loads((ROOT/'public/data/buildings.json').read_text()) if x['id']=='way/759185166')
def root_name(o):
    while o.parent:o=o.parent
    return o.name

def check(objects,tolerance,detail):
    trees=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles()
        triangles=o.data.loop_triangles
        trees.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
                      [tuple(t.vertices) for t in triangles],all_triangles=True),
                      [o.data.materials[t.material_index].name.split('.')[0] for t in triangles]))
    samples=[]
    def probe(kind,point,direction,distance,expected=None,material=None):
        hits=[]
        for tree,mats in trees:
            h=tree.ray_cast(point,direction,distance)
            if h[0] is not None:hits.append((h[3],mats[h[2]]))
        actual=min(hits,default=None)
        if expected is None:
            assert actual is None,(kind,'unexpected obstruction',actual)
        else:
            assert actual and abs(actual[0]-expected)<=tolerance and (material is None or actual[1]==material),(kind,actual,expected,material)
        samples.append(dict(kind=kind,hit=actual))
    for edge in [7,11]:
        f=next(f for f in b['form']['facades'] if f['edge']==edge)
        a=Vector((*f['start'],b['elevation']));delta=Vector((*f['end'],b['elevation']))-a;n=Vector((*f['normal'],0))
        # Fixed acceptance estimates, independent of the new configuration list.
        for top in [3.3,6.6,9.9,13.2,16.5]:
            for t in [.08,.3,.5,.7,.92]:
                p=a+delta*t
                probe(f'edge-{edge}-ledge-top',p+n*.42+Vector((0,0,top+.3)),Vector((0,0,-1)),.6,.3,'white')
                probe(f'edge-{edge}-ledge-soffit',p+n*.42+Vector((0,0,top-.46)),Vector((0,0,1)),.6,.3,'white')
                probe(f'edge-{edge}-ledge-front',p+n*.95+Vector((0,0,top-.08)),-n,.5,.3,'white')
                probe(f'edge-{edge}-outside-depth',p+n*.85+Vector((0,0,top+.3)),Vector((0,0,-1)),.6)
        # A side edge must not silently become a balcony or a solid horizontal band.
        count=max(1,int(delta.length/4))
        for level in range(5):
            t=.5/count;z=(level+.56)*3.3
            p=a+delta*(t+.4/delta.length)+Vector((0,0,z))
            probe(f'edge-{edge}-window-retained',p+n*.8,-n,1,.55 if detail else .73)
            probe(f'edge-{edge}-clear-space-below',a+delta*.5+n*.42+Vector((0,0,level*3.3+2.3)),Vector((0,0,1)),.6)
    return dict(passed=True,ledgeCount=10,sampleCount=len(samples),toleranceMeters=tolerance,samples=samples)
report=dict(passed=False,buildingId=b['id'],checkedRoot=str(TARGET),method='BVH over actual mesh loop triangles, source/base/near',dimensionStatus='photo-constrained estimates, not surveyed')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.012,True)
    for label,file,tol in [('base','base.glb',.035),('near',b['chunk']+'.glb',.02)]:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/file));bpy.context.view_layer.update()
        report[label]=check([o for o in bpy.context.scene.objects if label!='base' or root_name(o)==b['chunk']],tol,label=='near')
    report['passed']=True
except Exception as error:report['failure']=str(error)
finally:
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/data/models.json','public/models/base.glb','public/models/'+b['chunk']+'.glb']}
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Agriculture ledges:',report['passed'],report.get('failure',''),flush=True)
if not report['passed']:raise RuntimeError(report['failure'])
