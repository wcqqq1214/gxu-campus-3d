"""Verify calibrated roof levels in the source and both shipped LODs.

Samples deliberately cross the central/wing boundary: a uniform four-storey
extrusion or an unchanged three-storey model must fail this acceptance check.
"""
import bpy,sys,json,re,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
TARGET=next((Path(a.split('=',1)[1]).resolve() for a in sys.argv if a.startswith('--check-root=')),ROOT)
PREFIX=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--report-prefix=')),'s2-office-north')
b=next(b for b in json.loads((ROOT/'public/data/buildings.json').read_text()) if b['id']=='way/671978896')
SAMPLES=[(x,y,13.2) for x in (-250,-245,-238) for y in (-617,-623,-630)]
SAMPLES += [(-276,-635,9.9),(-264,-635,9.9),(-255,-632,9.9),(-251,-632,13.2),(-227,-628,9.9),(-215,-628,9.9),(-202,-628,9.9)]

def root_name(o):
    while o.parent:o=o.parent
    return re.sub(r'\.\d+$','',o.name)

def check(objects,tolerance):
    trees=[]
    for o in objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles()
        trees.append(BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(t.vertices) for t in o.data.loop_triangles],all_triangles=True))
    records=[]
    for x,y,expected in SAMPLES:
        hits=[tree.ray_cast(Vector((x,y,b['elevation']+20)),Vector((0,0,-1)),25) for tree in trees]
        hits=[h for h in hits if h[0] is not None]
        assert hits,('roof missing',x,y)
        hit=min(hits,key=lambda h:h[3]);height=hit[0].z-b['elevation']
        assert abs(height-expected)<tolerance,('wrong roof height',x,y,height,expected)
        assert hit[1].z>.98,('roof normal reversed',x,y,list(hit[1]))
        records.append(dict(x=x,y=y,expectedHeight=expected,actualHeight=height))
    return dict(passed=True,toleranceMeters=tolerance,samples=records)

report=dict(passed=False,checkedRoot=str(TARGET),scope='Nine central roof samples, six side-wing samples and one additional central sample across the west boundary; upward roof normals.')
try:
    bpy.ops.wm.open_mainfile(filepath=str(TARGET/'blender/gxu-campus.blend'))
    report['source']=check([o for o in bpy.context.scene.objects if o.get('featureId')==b['id']],.006)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models/base.glb'));bpy.context.view_layer.update()
    report['base']=check([o for o in bpy.context.scene.objects if root_name(o)==b['chunk']],.05)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(TARGET/'public/models'/f"{b['chunk']}.glb"));bpy.context.view_layer.update()
    report['near']=check(list(bpy.context.scene.objects),.02)
    report['fingerprints']={p:hashlib.sha256((TARGET/p).read_bytes()).hexdigest() for p in ['blender/gxu-campus.blend','public/models/base.glb',f"public/models/{b['chunk']}.glb",'public/data/buildings.json']}
    report['passed']=True
except Exception as error:
    report['failure']=str(error)
    raise
finally:
    (ROOT/'docs/model-checks/refinement'/f'{PREFIX}-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Office north roof levels:',report['passed'],flush=True)
