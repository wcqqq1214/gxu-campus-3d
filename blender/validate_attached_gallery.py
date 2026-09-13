"""Validate attached upper galleries in source, base and actual near GLB."""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from gallery_checks import check_galleries
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-east-gallery')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/759129515')
def root_name(obj):
    while obj.parent:obj=obj.parent
    return obj.name
def tree(obj):
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                               [tuple(p.vertices) for p in obj.data.polygons])
def check_ground(ground,tolerance):
    samples=[]
    for f in b['form']['facades']:
        if 'attachedGallery' not in f:continue
        p=f['attachedGallery'];a=Vector((*f['start'],0));u=(Vector((*f['end'],0))-a).normalized();n=Vector((*f['normal'],0))
        middle=(a+Vector((*f['end'],0)))/2
        for offset in (-.9,0,.9):
            point=middle+u*offset+n*(p['depth']+.12)
            hits=[h[0].z for g in ground if (h:=g.ray_cast(point+Vector((0,0,20)),Vector((0,0,-1)),40))[0] is not None]
            assert hits,'missing ground at attached gallery front'
            h=max(hits)-b['elevation'];sill=.56*3.3-min(1.9,3.3*.55)/2
            assert -.5-tolerance<=h<=sill-.02+tolerance,('gallery base floats or lower window buried',f['edge'],offset,h,sill)
            samples.append(dict(edge=f['edge'],offset=offset,sillAboveGroundMeters=sill-h))
    return dict(passed=True,samples=samples)
report=dict(passed=False,scope='Two eastern attached upper galleries only; not whole-building acceptance',wholeBuildingAccepted=False)
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('featureId')==b['id']]
    assert len(objects)==1
    report['source']=check_galleries(b,[tree(o) for o in objects],.011,b['elevation'])
    report['sourceGround']=check_ground([tree(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('layer')=='terrain'],.011)
    for level,name in [('base','base.glb'),('near',b['chunk']+'.glb')]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/name));bpy.context.view_layer.update()
        objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and (level=='near' or root_name(o)==b['chunk'])]
        report[level]=check_galleries(b,[tree(o) for o in objects],.025 if level=='base' else .02,b['elevation'])
        if level=='base':report['baseGround']=check_ground([tree(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('layer')=='terrain'],.025)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/data/models.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error);raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Attached gallery source/base/near',report['passed'],flush=True)
