"""Rebuild both tree LOD assets without regenerating unchanged campus buildings."""
import bpy,sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import material
from vegetation import tree_templates
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
collection=bpy.context.scene.collection
C={}
for name,color in [('bark','#6e6650'),('leaf','#3f7049'),('leaf2','#56824c'),('leaf3','#67904f')]:
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];linear=[((v+.055)/1.055)**2.4 if v>.04045 else v/12.92 for v in rgb]
    C[name]=material(name,linear,1,0)
manifest=json.loads((ROOT/'public/data/models.json').read_text())
for detail,name,key in [(False,'trees.glb','trees'),(True,'trees-near.glb','treesNear')]:
    templates=tree_templates(C,collection,detail)
    bpy.ops.object.select_all(action='DESELECT')
    for o in templates:o.select_set(True)
    path=ROOT/'public/models'/name
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_draco_mesh_compression_enable=True)
    manifest[key]={'url':'models/'+name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(ROOT/'public/data/models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('Vegetation LODs ready',manifest['trees']['bytes'],manifest['treesNear']['bytes'],flush=True)
