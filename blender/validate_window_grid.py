"""Check the sourced eight-bay front in the editable source and actual GLBs."""
import bpy,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s3-glazing')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='relation/11564704')
if 'elevation' not in b or 'chunk' not in b:
    prior=next(x for x in json.loads((TARGET/'public/data/buildings.json').read_text()) if x['id']==b['id'])
    b.update(elevation=prior['elevation'],chunk=prior['chunk'])
f=next(f for f in b['form']['facades'] if f['edge']==11 and f['part']=='entrance-front')
g=f['rule']['windowGrid'];assert g['columns']==8 and g['firstLevel']==1 and f['levels']==7

def root_name(o):
    while o.parent:o=o.parent
    return o.name

def bvhs(objects,materials):
    result=[]
    for o in objects:
        if o.type!='MESH':continue
        faces=[tuple(p.vertices) for p in o.data.polygons if o.data.materials[p.material_index].name.split('.')[0] in materials]
        if faces:result.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],faces))
    return result

def nearest(trees,p,d,length=1):
    hits=[t.ray_cast(p,d,length) for t in trees]
    hits=[h for h in hits if h[0] is not None]
    return min(hits,key=lambda h:h[3]) if hits else None

def check(objects,tolerance,detail):
    glass=bvhs(objects,{'glass','shadeGlass'});white=bvhs(objects,{'white'})
    a=Vector((*f['start'],b['elevation']));n=Vector((*f['normal'],0))
    edge=Vector((*f['end'],b['elevation']))-a;length=edge.length;u=edge/length
    bay=(length-2*g['edgeInset'])/8;fh=f['height']/7;ww=bay*g['widthRatio'];wh=fh*g['heightRatio']
    windows=[];piers=[];bars=0
    for level in range(1,7):
        z=(level+.56)*fh
        for col in range(8):
            center=a+u*(g['edgeInset']+(col+.5)*bay)+Vector((0,0,z))
            # Material-specific ray avoids confusing a white window frame with glazing.
            hit=nearest(glass,center+n*.8,-n)
            front=.25 if detail else .07
            assert hit and abs(hit[3]-(.8-front))<=tolerance,('missing glazing bay',level,col,hit[3] if hit else None)
            windows.append({'levelIndex':level,'columnIndex':col,'frontErrorMeters':abs(hit[3]-(.8-front))})
            for row in range(1,4):
                p=center+u*(ww*.25)+Vector((0,0,-wh/2+wh*row/4))+n*.8
                hit=nearest(white,p,-n,.95)
                if detail:
                    assert hit and abs(hit[3]-.51)<=tolerance,('missing inner horizontal bar',level,col,row)
                else:
                    assert hit is None,('fine window bars leaked into base',level,col,row)
                bars+=1
    # Sample the solid spandrel intervals, where ordinary isolated frames cannot pass.
    for col in range(9):
        for level in [1,3,5]:
            p=a+u*(g['edgeInset']+col*bay)+Vector((0,0,(level+.95)*fh))+n*.8
            hit=nearest(white,p,-n)
            assert hit and abs(hit[3]-(.8-g['pilasterDepth']))<=tolerance,('missing continuous vertical pier',col,level)
            piers.append({'pierIndex':col,'levelIndex':level,'frontErrorMeters':abs(hit[3]-(.8-g['pilasterDepth']))})
    return {'passed':True,'glazingSamples':len(windows),'pierSamples':len(piers),'paneBarChecks':bars,
            'detailBarsExpected':detail,'windows':windows,'piers':piers}

report={'buildingId':b['id'],'checkedRoot':str(TARGET),'passed':False,
    'scope':'Eight front bays over six upper floors; nine continuous vertical piers at three heights; horizontal pane bars in source/near and omitted in base.',
    'tolerancesMeters':{'source':.011,'baseDraco':.05,'nearDraco':.02}}
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']];assert len(objects)==1
    report['source']=check(objects,.011,True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05,False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f'{b["chunk"]}.glb'));bpy.context.view_layer.update()
    report['near']=check(bpy.context.scene.objects,.02,True)
    report['modelManifestSha256']=hashlib.sha256((TARGET/'public/data/models.json').read_bytes()).hexdigest()
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-windows.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Window grid checks',report['passed'],flush=True)
