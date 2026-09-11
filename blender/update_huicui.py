"""Bounded rebuild: Huicui's existing chunk, base LOD and editable source object."""
import sys,json,hashlib
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS,Mesh
from preserve_glb_geometry import preserve_geometry,unpack

before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'public/models').glob('*.glb')}
previous_base=(ROOT/'public/models/base.glb').read_bytes()
script=ROOT/'blender/build_campus.py';ns={'__file__':str(script),'__name__':'__main__'}
sys.argv.append('--base-only')
try:exec(compile(script.read_text(),str(script),'exec'),ns)
except SystemExit as e:
    if e.code not in (0,None):raise
b=next(b for b in ns['buildings'] if b.get('customModel')=='huicui');key=b['chunk']
preserve_geometry(previous_base,ROOT/'public/models/base.glb',['landmark-time-gate'])
high=ns['generic'](b,True);zone=Mesh()
for building in ns['buildings']:
    if building.get('chunk')==key:zone.extend(high if building['id']==b['id'] else ns['generic'](building,True))
ns['export'](key+'.glb',{key:zone})
manifest=json.loads((ROOT/'public/data/models.json').read_text())
for entry in [manifest['base']]+[e for e in manifest['zones'] if e['id']==key]:
    raw=(ROOT/'public'/entry['url']).read_bytes();entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
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
old=[o for o in bpy.context.scene.objects if o.get('featureId')==b['id']]
assert len(old)==1,'Shared relation must have exactly one source object'
collection=old[0].users_collection[0];mesh=old[0].data
bpy.data.objects.remove(old[0],do_unlink=True)
if mesh.users==0:bpy.data.meshes.remove(mesh)
from huicui import compact_source
obj=high.object('荟萃楼 · 新闻传播学院共用楼体',collection,{'featureId':b['id'],'chunk':key,'layer':'buildings','customModel':'huicui','sourceUrl':b['sourceUrl'],'precision':b['architecture']['precision']})
compact_source(obj)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'),compress=True)
assert (ROOT/'blender/gxu-campus.blend').stat().st_size<100*1024*1024
assert manifest['base']['bytes']+manifest['trees']['bytes']<6_000_000

# Check exact compressed primitive bytes of all unrelated base nodes.
a,ab=unpack(previous_base);c,cb=unpack((ROOT/'public/models/base.glb').read_bytes())
def signature(doc,binary,node):
    result=[]
    for p in doc['meshes'][node['mesh']]['primitives']:
        v=doc['bufferViews'][p['extensions']['KHR_draco_mesh_compression']['bufferView']];start=v.get('byteOffset',0)
        result.append((doc['materials'][p['material']]['name'],hashlib.sha256(binary[start:start+v['byteLength']]).hexdigest()))
    return result
retained=[]
for node in a['nodes']:
    if 'mesh' not in node or node['name']==key:continue
    other=next(n for n in c['nodes'] if n.get('name')==node['name'])
    assert signature(a,ab,node)==signature(c,cb,other),node['name']
    retained.append(node['name'])
changed=[p.name for p in (ROOT/'public/models').glob('*.glb') if before[p.name]!=hashlib.sha256(p.read_bytes()).hexdigest()]
assert set(changed)<=set(['base.glb',key+'.glb'])
report={'changedGlbs':sorted(changed),'retainedBaseNodes':retained,'retainedNearAndTreeGlbs':len(before)-2,'initialBytes':manifest['base']['bytes']+manifest['trees']['bytes'],'blendBytes':(ROOT/'blender/gxu-campus.blend').stat().st_size}
(ROOT/'docs/model-checks/huicui-retained-assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Huicui source + two LODs updated:',json.dumps(report),flush=True)
