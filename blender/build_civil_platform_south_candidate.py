"""Bounded source/chunk export into a candidate directory, never production."""
import argparse
import hashlib
import json
import shutil
import sys
from contextlib import nullcontext
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'blender'))
from geometry import MATERIALS, Mesh
from generic_buildings import ordinary_building, compact_form_source
from export_attributes import omit_unused_uvs
from preserve_glb_geometry import preserve_geometry, compact_buffer_views, unpack

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--proposal',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.output=a.output.resolve()
if a.output==ROOT or (ROOT/'public').resolve() in a.output.parents:raise ValueError('Use a separate candidate directory')
a.output.mkdir(parents=True,exist_ok=True)
r=json.loads(a.proposal.read_text());ident=r['original']['id'];key=r['original']['chunk']
buildings=json.loads((ROOT/'public/data/buildings.json').read_text())
assert next(b for b in buildings if b['id']==ident)==r['original'], 'Production input changed'
terrain=json.loads((ROOT/'public/data/terrain.json').read_text())
def elevation(b):
    x,y=b['center'];cols,rows=terrain['cols'],terrain['rows'];xmin,ymin,xmax,ymax=terrain['bounds'];hh=terrain['heights']
    u=max(0,min(cols-1.001,(x-xmin)/(xmax-xmin)*(cols-1)));v=max(0,min(rows-1.001,(y-ymin)/(ymax-ymin)*(rows-1)))
    i,j=int(u),int(v);s,t=u-int(u),v-int(v)
    return (hh[j*cols+i]*(1-s)+hh[j*cols+i+1]*s)*(1-t)+(hh[(j+1)*cols+i]*(1-s)+hh[(j+1)*cols+i+1]*s)*t

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/gxu-campus.blend'))
base_doc=unpack((ROOT/'public/models/base.glb').read_bytes())[0]
base_node=next(n for n in base_doc['nodes'] if n.get('name')==key)
order=[base_doc['materials'][p['material']]['name'] for p in base_doc['meshes'][base_node['mesh']]['primitives']]
MATERIALS[:]=sorted(bpy.data.materials,key=lambda m:order.index(m.name) if m.name in order else len(order))
C={m.name:i for i,m in enumerate(MATERIALS)}
targets=[o for o in bpy.context.scene.objects if o.get('featureId')==ident];assert len(targets)==1
old=targets[0];name=old.name;collection=old.users_collection[0];props=dict(old.items())

mesh_signatures={}
def signature(o):
    result={'name':o.name,'type':o.type,'matrix':[list(v) for v in o.matrix_world],'props':dict(o.items())}
    if o.type=='MESH':
        m=o.data
        if m.as_pointer() not in mesh_signatures:
            data=dict(vertices=[list(v.co) for v in m.vertices],faces=[list(p.vertices) for p in m.polygons],
                      materials=[m.name for m in m.materials],indices=[p.material_index for p in m.polygons],
                      uv=[[list(v.uv) for v in layer.data] for layer in m.uv_layers])
            mesh_signatures[m.as_pointer()]=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
        result['mesh']=mesh_signatures[m.as_pointer()]
    return hashlib.sha256(json.dumps(result,sort_keys=True,default=str).encode()).hexdigest()
retained={o.name:signature(o) for o in bpy.context.scene.objects if o!=old}

def export_chunk(building_set, detail, path):
    joined=Mesh()
    for b in building_set:
        if b.get('chunk')==key:
            assert not b.get('customModel') and not b.get('landmark')
            joined.extend(ordinary_building(b,elevation(b),C,detail))
    bpy.ops.object.select_all(action='DESELECT')
    obj=joined.object(key,bpy.context.scene.collection,{'layer':'buildings','zone':key});obj.select_set(True)
    with nullcontext() if detail else omit_unused_uvs():
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,
            export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
            export_draco_position_quantization=16 if detail else 15,
            export_draco_normal_quantization=10 if detail else 6,
            export_materials='EXPORT',export_cameras=False,export_lights=False)
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)

new_buildings=[r['candidate'] if b['id']==ident else b for b in buildings]
for label,bs in [('before',buildings),('candidate',new_buildings)]:
    for detail in (False,True):export_chunk(bs,detail,a.output/f'{label}-{ "near" if detail else "base-chunk"}.glb')
shutil.copyfile(ROOT/'public/models/base.glb',a.output/'base.glb')
preserve_geometry((a.output/'candidate-base-chunk.glb').read_bytes(),a.output/'base.glb',[key])
compact_buffer_views(a.output/'base.glb')
shutil.copyfile(a.output/'candidate-near.glb',a.output/f'{key}.glb')
mesh=old.data;bpy.data.objects.remove(old,do_unlink=True)
if mesh.users==0:bpy.data.meshes.remove(mesh)
high=ordinary_building(r['candidate'],elevation(r['candidate']),C,True)
obj=high.object(name,collection,props);compact_form_source(obj)
mesh_signatures.clear()
assert retained=={o.name:signature(o) for o in bpy.context.scene.objects if o!=obj}
bpy.ops.wm.save_as_mainfile(filepath=str(a.output/'gxu-campus.blend'),compress=True,relative_remap=False)
manifest=json.loads((ROOT/'public/data/models.json').read_text())
for entry in [manifest['base']]+[v for v in manifest['zones'] if v['id']==key]:
    path=a.output/Path(entry['url']).name;raw=path.read_bytes()
    entry.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
initial=manifest['base']['bytes']+manifest['trees']['bytes'];assert initial<=6_000_000,initial
(a.output/'models.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(a.output/'source-preservation.json').write_text(json.dumps(dict(passed=True,retainedObjects=len(retained),
    changedFeatureId=ident,sourceBeforeSHA256=hashlib.sha256((ROOT/'blender/gxu-campus.blend').read_bytes()).hexdigest(),
    sourceAfterSHA256=hashlib.sha256((a.output/'gxu-campus.blend').read_bytes()).hexdigest(),
    initialBytes=initial,scope='All other current scene objects: transforms, properties, vertices, faces, material assignments and UV arrays.'),indent=2)+'\n')
print('Bounded candidate exported; retained objects',len(retained),'initial bytes',initial,flush=True)
