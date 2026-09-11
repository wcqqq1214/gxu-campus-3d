"""Update campus main-road finishes and the corrected Huixue lawn tree mask."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS
from preserve_glb_geometry import preserve_geometry,unpack
previous=(ROOT/'public/models/base.glb').read_bytes()
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'public/models').glob('*.glb')}
script=ROOT/'blender/build_campus.py';namespace={'__file__':str(script),'__name__':'__main__'};sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),namespace)
except SystemExit as result:
    if result.code not in (None,0):raise
preserve_geometry(previous,ROOT/'public/models/base.glb',['landmark-time-gate'])
manifest=json.loads((ROOT/'public/data/models.json').read_text());blob=(ROOT/'public/models/base.glb').read_bytes()
manifest['base'].update(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())
(ROOT/'public/data/models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
roads=namespace['base']['roads'];names=[m.name for m in MATERIALS]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
MATERIALS[:]=[bpy.data.materials[name] for name in names]
old=bpy.data.objects['roads'];collection=old.users_collection[0];data=old.data
bpy.data.objects.remove(old,do_unlink=True);bpy.data.meshes.remove(data)
obj=roads.object('roads',collection,{'layer':'roads','basis':'主路沿用桥底沥青、浅色路缘、中心虚线；标线为示意，保留原路幅和支路'})
from huicui import compact_source
compact_source(obj)
from mathutils.kdtree import KDTree
trees=namespace['trees'];kd=KDTree(len(trees))
for i,t in enumerate(trees):kd.insert((t[0],t[1],0),i)
kd.balance();survivors=[]
for o in list(bpy.data.objects):
    if not o.name.startswith('树木示意-'):continue
    co,index,distance=kd.find((o.location.x,o.location.y,0))
    if distance>.02:bpy.data.objects.remove(o,do_unlink=True)
    else:o.name='lawn-tree-temp-'+str(index);survivors.append((o,index))
for o,i in survivors:o.name=f'树木示意-{i:04}';o.rotation_euler.z=i*2.399
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
for node in a['nodes']:
    if 'mesh' not in node:continue
    other=next(n for n in c['nodes'] if n.get('name')==node['name'])
    (retained if signature(a,ab,node)==signature(c,cb,other) else changed).append(node['name'])
assert set(changed)<= {'roads'},changed
assert all(hashlib.sha256((ROOT/'public/models'/n).read_bytes()).hexdigest()==h for n,h in before.items() if n!='base.glb')
report={'changedBaseNodes':changed,'retainedBaseNodes':len(retained),'retainedNearAndTreeGlbs':len(before)-1,'trees':len(trees),'initialBytes':len(blob)+manifest['trees']['bytes'],'blendBytes':(ROOT/'blender/gxu-campus.blend').stat().st_size}
(ROOT/'docs/model-checks/campus-roads-models.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['initialBytes']<6_000_000,report
assert report['blendBytes']<100*1024*1024,report
print(report,flush=True)
