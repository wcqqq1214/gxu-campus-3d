"""Update only basketball, general sports, terrain and draped roads; retain near assets."""
import sys,json,hashlib
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS,Mesh
from basketball import court_model,bank_paving
previous_base=(ROOT/'public/models/base.glb').read_bytes()
script=ROOT/'blender/build_campus.py';ns={'__file__':str(script),'__name__':'__main__'}
sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),ns)
except SystemExit as e:
    if e.code not in (0,None):raise
from preserve_glb_geometry import preserve_geometry
preserve_geometry(previous_base,ROOT/'public/models/base.glb',['landmark-time-gate'])
manifest=json.loads((ROOT/'public/data/models.json').read_text());blob=(ROOT/'public/models/base.glb').read_bytes();manifest['base'].update(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
(ROOT/'public/data/models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
records=[(m.name,tuple(m.diffuse_color),m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value,m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value) for m in MATERIALS]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
materials=[]
for name,color,rough,metal in records:
    mat=bpy.data.materials.get(name)
    if mat is None:
        mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=color
        bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    materials.append(mat)
MATERIALS[:]=materials
collection=bpy.data.objects['terrain'].users_collection[0]
for key,oldname,layer in [('terrain','terrain','terrain'),('roads','roads','roads'),('sports','其他运动场地','sports')]:
    old=bpy.data.objects[oldname];mesh=old.data;bpy.data.objects.remove(old,do_unlink=True);bpy.data.meshes.remove(mesh)
    ns['base'][key].object(oldname,collection,{'layer':layer})
for old in list(bpy.data.objects):
    if old.get('basketballCourt') or old.get('basketballBank'):
        mesh=old.data;bpy.data.objects.remove(old,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
for bank in ns['basketball']['banks']:
    bank_paving(bank,ns['C']).object(bank['id']+'-paving',collection,{'layer':'sports','basketballBank':bank['id']})
for court in ns['basketball']['courts']:
    court_model(court,ns['C']).object(court['id'],collection,{'layer':'sports','featureId':court['osmId'],'precision':court['precision'],'basketballCourt':court['id']})
from mathutils.kdtree import KDTree
kd=KDTree(len(ns['trees']))
for i,t in enumerate(ns['trees']):kd.insert((t[0],t[1],0),i)
kd.balance();survivors=[]
for o in list(bpy.data.objects):
    if not o.name.startswith('树木示意-'):continue
    co,index,distance=kd.find((o.location.x,o.location.y,0))
    if distance>.02:bpy.data.objects.remove(o,do_unlink=True)
    else:o.name='court-tree-temp-'+str(index);survivors.append((o,index))
for o,i in survivors:o.name=f'树木示意-{i:04}';o.rotation_euler.z=i*2.399
assert len(survivors)==len(ns['trees'])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
print('Basketball updated in editable source and base GLB',flush=True)
