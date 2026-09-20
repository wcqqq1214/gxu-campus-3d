"""Check the 15 mixed-height eastern top-floor windows in actual shipping triangles."""
import bpy,sys,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s3-agriculture-windows')
b=next(x for x in json.loads((ROOT/'public/data/buildings.json').read_text()) if x['id']=='way/759185166')
f=next(x for x in b['form']['facades'] if x['edge']==7)
a=Vector((*f['start'],b['elevation']));edge=Vector((*f['end'],b['elevation']))-a;n=Vector((*f['normal'],0))
def root_name(o):
    while o.parent:o=o.parent
    return o.name

def check(objects,tolerance,detail):
    trees=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();triangles=o.data.loop_triangles
        trees.append((BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],
            [tuple(t.vertices) for t in triangles],all_triangles=True),
            [o.data.materials[t.material_index].name.split('.')[0] for t in triangles]))
    samples=[]
    def probe(kind,t,z,expected,materials):
        point=a+edge*t+Vector((0,0,z))+n*.8;hits=[]
        for tree,mats in trees:
            h=tree.ray_cast(point,-n,1.2)
            if h[0] is not None:hits.append((h[3],mats[h[2]]))
        actual=min(hits,default=None)
        assert actual and abs(actual[0]-expected)<=tolerance and actual[1] in materials,(kind,t,z,actual,expected,materials)
        samples.append(dict(kind=kind,fraction=t,height=z,firstMaterial=actual[1],distanceMeters=actual[0]))
    # Counting direction: mapped edge runs from east end toward central portico.
    # These fixed stations reflect independently reviewed photo estimates.
    for i in range(15):
        t=(i+.5)/15;small=i in (3,4,6,13,14);top=14.95 if small else 16.
        probe('top-window-glass',t+.25/edge.length,(14.15+top)/2,.76,['glass'])
        probe('top-window-side-frame',t-.795/edge.length,(14.15+top)/2,.65,['white'])
        probe('retained-wall-below-window',t,13.9,.8,['stone'])
        probe('small-window-upper-wall' if small else 'tall-window-upper-glass',t+.25/edge.length,15.65,.8 if small else .76,['stone'] if small else ['glass'])
    for i in range(14):probe('wall-between-top-windows',(i+1)/15,15.05,.8,['stone'])
    # Stay beyond the retained return-wall frame projecting 0.32 m around
    # the eastern corner, but inside the 0.45 m gap before the first panel.
    for t in [.01,.99]:probe('end-wall',t,15.05,.8,['stone'])
    count=int(edge.length/4)
    for level in range(4):
        for i in [1,5]:
            probe('lower-generic-window-preserved',(i+.5)/count+.4/edge.length,(level+.56)*3.3,.55 if detail else .73,['glass','shadeGlass'])
    return dict(passed=True,windowCount=15,smallWindowCount=5,sampleCount=len(samples),toleranceMeters=tolerance,samples=samples)
report=dict(passed=False,buildingId=b['id'],checkedRoot=str(TARGET),method='BVH over actual loop triangles, independent fixed acceptance stations',dimensionStatus='Photo-supported count and arrangement; estimated sizes and positions, exterior glass approximation')
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
    print('Agriculture windows:',report['passed'],report.get('failure',''),flush=True)
if not report['passed']:raise RuntimeError(report['failure'])
