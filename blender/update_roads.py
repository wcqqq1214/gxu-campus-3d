"""Update campus roads, bridge transition aprons, end railings and the lawn tree mask."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS
from preserve_glb_geometry import preserve_geometry,compact_buffer_views,unpack,mesh_nodes_by_name
previous=(ROOT/'public/models/base.glb').read_bytes()
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'public/models').glob('*.glb')}
script=ROOT/'blender/build_campus.py';namespace={'__file__':str(script),'__name__':'__main__'};sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),namespace)
except SystemExit as result:
    if result.code not in (None,0):raise
preserve_geometry(previous,ROOT/'public/models/base.glb',['landmark-time-gate'])
compact_buffer_views(ROOT/'public/models/base.glb')
high={}
for b in namespace['infrastructure']['bridges']:
    key=b['id'];high[key]=namespace['bridge'](b,namespace['C'],True)
    namespace['export'](key+'.glb',{'landmark-'+key:high[key]})
manifest=json.loads((ROOT/'public/data/models.json').read_text())
for entry in manifest['landmarks']:
    if entry['id'] in high:
        raw=(ROOT/'public'/entry['url']).read_bytes();entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
blob=(ROOT/'public/models/base.glb').read_bytes()
manifest['base'].update(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
(ROOT/'public/data/models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
roads=namespace['base']['roads']
records=[(m.name,tuple(m.diffuse_color),m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value,m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value) for m in MATERIALS]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
materials=[]
for name,color,rough,metal in records:
    mat=bpy.data.materials.get(name)
    if mat is None:
        # Unused generated palette entries are not retained in a saved blend.
        mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=color
        bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    materials.append(mat)
MATERIALS[:]=materials
from paving_geometry import sync_source_pavings
sync_source_pavings(namespace['base'])
from site_geometry import sync_source_sites
sync_source_sites(namespace['base'])
from shore_geometry import sync_source_shores
sync_source_shores(namespace['base'],include_terrain=True)
from low_planting import sync_source_low_planting
sync_source_low_planting(namespace['base'])
old=bpy.data.objects['roads'];collection=old.users_collection[0];data=old.data
bpy.data.objects.remove(old,do_unlink=True);bpy.data.meshes.remove(data)
obj=roads.object('roads',collection,{'layer':'roads','basis':'主路沿用桥底沥青、浅色路缘、中心虚线；标线为示意，保留原路幅和支路'})
from huicui import compact_source
compact_source(obj)
for key,mesh in [(k,v) for k,v in namespace['base'].items() if k.startswith('infra-approach-')]:
    old=bpy.data.objects[key];data=old.data;bpy.data.objects.remove(old,do_unlink=True);bpy.data.meshes.remove(data)
    compact_source(mesh.object(key,collection,{'layer':'roads'}))
for key,mesh in high.items():
    old=next(o for o in bpy.data.objects if o.get('landmark')==key)
    name=old.name;props=dict(old.items());group=old.users_collection[0];data=old.data
    bpy.data.objects.remove(old,do_unlink=True);bpy.data.meshes.remove(data)
    compact_source(mesh.object(name,group,props))
from mathutils.kdtree import KDTree
trees=namespace['trees'];kd=KDTree(len(trees))
for i,t in enumerate(trees):kd.insert((t[0],t[1],0),i)
kd.balance();survivors=[]
for o in list(bpy.data.objects):
    if not o.name.startswith('树木示意-'):continue
    co,index,distance=kd.find((o.location.x,o.location.y,0))
    if distance>.02:bpy.data.objects.remove(o,do_unlink=True)
    else:o.name='lawn-tree-temp-'+str(index);survivors.append((o,index))
for o,i in survivors:o.name=f'树木示意-{i:04}';o.rotation_euler.z=namespace['tree_rotation'](*trees[i][:2]);o.location.z=trees[i][4]
assert len(survivors)==len(trees)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
a,ab=unpack(previous);c,cb=unpack(blob)
def signature(doc,binary,node):
    result=[]
    for p in doc['meshes'][node['mesh']]['primitives']:
        v=doc['bufferViews'][p['extensions']['KHR_draco_mesh_compression']['bufferView']];start=v.get('byteOffset',0)
        result.append((doc['materials'][p['material']]['name'],hashlib.sha256(binary[start:start+v['byteLength']]).hexdigest()))
    return result
changed=[];retained=[]
old_nodes=mesh_nodes_by_name(a);new_nodes=mesh_nodes_by_name(c)
for name,node in old_nodes.items():
    other=new_nodes[name]
    (retained if signature(a,ab,node)==signature(c,cb,other) else changed).append(name)
assert set(changed)<= {'roads','terrain','green'}|{'infra-approach-'+k for k in high}|{k for k in namespace['base'] if k.startswith(('site-','shore-','paving-','vegetation-low-'))},changed
assert all(hashlib.sha256((ROOT/'public/models'/n).read_bytes()).hexdigest()==h for n,h in before.items() if n not in {'base.glb'}|{k+'.glb' for k in high})
report={'changedBaseNodes':changed,'retainedBaseNodes':len(retained),'retainedNearAndTreeGlbs':len(before)-1-len(high),'trees':len(trees),'initialBytes':len(blob)+manifest['trees']['bytes'],'blendBytes':(ROOT/'blender/gxu-campus.blend').stat().st_size}
(ROOT/'docs/model-checks/bridge-joins-models.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['initialBytes']<6_000_000,report
assert report['blendBytes']<100*1024*1024,report
print(report,flush=True)
