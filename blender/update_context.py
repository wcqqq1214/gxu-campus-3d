"""Rebuild only the external building layer; preserve all campus near models."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS
from preserve_glb_geometry import preserve_geometry,unpack
previous=(ROOT/'public/models/base.glb').read_bytes()
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'public/models').glob('*.glb')}
script=ROOT/'blender/build_campus.py';ns={'__file__':str(script),'__name__':'__main__'};sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),ns)
except SystemExit as e:
    if e.code not in (0,None):raise
preserve_geometry(previous,ROOT/'public/models/base.glb',['landmark-time-gate'])
manifest=json.loads((ROOT/'public/data/models.json').read_text());blob=(ROOT/'public/models/base.glb').read_bytes()
manifest['base'].update(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
(ROOT/'public/data/models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
material_names=[m.name for m in MATERIALS]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
MATERIALS[:]=[bpy.data.materials[name] for name in material_names]
old=[o for o in bpy.data.objects if o.get('layer')=='context']
collection=old[0].users_collection[0]
for obj in old:
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
kept=[b for b in ns['buildings'] if not b['insideCampus']]
for b in kept:ns['generic'](b,False).object(b['name'],collection,{'featureId':b['id'],'layer':'context'})
assert {o.get('featureId') for o in bpy.data.objects if o.get('layer')=='context'}=={b['id'] for b in kept}
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
a,ab=unpack(previous);c,cb=unpack(blob)
def signature(doc,binary,node):
    result=[]
    for p in doc['meshes'][node['mesh']]['primitives']:
        v=doc['bufferViews'][p['extensions']['KHR_draco_mesh_compression']['bufferView']];start=v.get('byteOffset',0)
        result.append((doc['materials'][p['material']]['name'],hashlib.sha256(binary[start:start+v['byteLength']]).hexdigest()))
    return result
changed=[];retained=[]
for node in a['nodes']:
    if 'mesh' not in node:continue
    other=next(n for n in c['nodes'] if n.get('name')==node['name'])
    (retained if signature(a,ab,node)==signature(c,cb,other) else changed).append(node['name'])
assert changed==['context'],changed
assert all(hashlib.sha256((ROOT/'public/models'/n).read_bytes()).hexdigest()==h for n,h in before.items() if n!='base.glb')
assert (ROOT/'blender/gxu-campus.blend').stat().st_size<100*1024*1024
report={'changedBaseNodes':changed,'retainedBaseNodes':len(retained),'retainedNearAndTreeGlbs':len(before)-1,'sourceContextBuildings':len(kept),'initialBytes':len(blob)+manifest['trees']['bytes'],'blendBytes':(ROOT/'blender/gxu-campus.blend').stat().st_size}
(ROOT/'docs/model-checks/context-models.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
