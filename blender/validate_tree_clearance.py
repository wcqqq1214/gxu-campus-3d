"""Audit independently loaded source and GLB meshes for crossings/containment.

The shell primitive is shared with generation; the mesh collection and decoded
inputs are independent. Known-volume regression fixtures test containment itself.
"""
import bpy, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'blender'))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
prefix=next((a.split('=',1)[1] for a in args if a.startswith('--report-prefix=')),'s4-tree-clearance')
if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in prefix):
    raise ValueError('Invalid clearance report prefix')
rows=json.loads((ROOT/'public/data/vegetation.json').read_text())
manifest=json.loads((ROOT/'public/data/models.json').read_text())


from tree_mesh_audit import snapshot, check_meshes


bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
source_buildings=[(str(o.get('featureId'))+'/'+o.name,snapshot(o)) for o in bpy.context.scene.objects
                  if o.type=='MESH' and o.get('layer') in ('buildings','context') and o.get('featureId')]
source_templates={o['template']:snapshot(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('template') is not None}
source=check_meshes(rows,source_buildings,{'near':source_templates})
print('Saved source', {k:v for k,v in source.items() if k!='collisions'},flush=True)
del source_buildings
bpy.ops.wm.read_factory_settings(use_empty=True)
templates={}
for key,lod in [('trees','base'),('treesNear','near')]:
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public'/manifest[key]['url']))
    templates[lod]={o['template']:snapshot(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('template') is not None}
    assert set(templates[lod])=={0,1,2}
    bpy.ops.wm.read_factory_settings(use_empty=True)
buildings=[]
assets=[manifest['base']]+manifest['zones']+manifest['landmarks']
for asset in assets:
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'public'/asset['url']))
    buildings.extend((asset['url']+'/'+o.name,snapshot(o)) for o in bpy.context.scene.objects
                     if o.type=='MESH' and o.get('layer') in ('buildings','context'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
shipping=check_meshes(rows,buildings,templates)
print('Decoded GLBs', {k:v for k,v in shipping.items() if k!='collisions'},flush=True)
report=dict(modelManifestSha256=hashlib.sha256((ROOT/'public/data/models.json').read_bytes()).hexdigest(),
            vegetationSha256=hashlib.sha256((ROOT/'public/data/vegetation.json').read_bytes()).hexdigest(),
            source=source,shipping=shipping,passed=source['passed'] and shipping['passed'],
            scope='Saved source and decoded base/all ordinary near chunks/all landmark meshes versus shipping tree transforms. Surface intersections and bidirectional containment in detected closed orientable components. Shared shell primitive with independent asset loading; no capping of open/non-manifold meshes or whole-site road/sports/water clearance proof.',
            sourceSha256=hashlib.sha256((ROOT/'blender/gxu-campus.blend').read_bytes()).hexdigest(),
            meshVolumesSha256=hashlib.sha256((ROOT/'blender/mesh_volumes.py').read_bytes()).hexdigest())
path=ROOT/'docs/model-checks/refinement'/f'{prefix}-geometry.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert report['passed'],(source['collisions'],shipping['collisions'])
