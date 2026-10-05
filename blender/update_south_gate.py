"""Rebuild only the south gate source and both published levels of detail."""
import copy, struct
from collections import Counter
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
import geometry
from geometry import MATERIALS, Mesh
from south_gate_site import ensure_materials, repair_roads, REPAIR_BOUNDS
from south_gate import south_gate
from preserve_glb_geometry import compact_buffer_views, mesh_nodes_by_name, preserve_geometry, unpack
from export_attributes import omit_unused_uvs


def signatures(raw):
    doc, binary = unpack(raw)
    result = {}
    for name, node in mesh_nodes_by_name(doc).items():
        primitives = []
        for p in doc['meshes'][node['mesh']]['primitives']:
            view = doc['bufferViews'][p['extensions']['KHR_draco_mesh_compression']['bufferView']]
            start = view.get('byteOffset', 0)
            primitives.append((doc['materials'][p['material']]['name'],
                               hashlib.sha256(binary[start:start + view['byteLength']]).hexdigest()))
        result[name] = primitives
    return result


def export(obj, path, base=False):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    with omit_unused_uvs():
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format='GLB', use_selection=True, export_extras=True,
            export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
            export_draco_position_quantization=15 if base else 16,
            export_draco_normal_quantization=6 if base else 10,
            export_materials='EXPORT', export_cameras=False, export_lights=False)


def replace_node_geometry(raw, path, name):
    """Allow this node's material set to grow, keeping other payloads verbatim."""
    src, payload=unpack(raw);dst, old_payload=unpack(path.read_bytes());binary=bytearray(old_payload)
    source=mesh_nodes_by_name(src)[name];target=mesh_nodes_by_name(dst)[name]
    byname={m['name']:i for i,m in enumerate(dst['materials'])};primitives=[]
    for primitive in src['meshes'][source['mesh']]['primitives']:
        p=copy.deepcopy(primitive);mat=src['materials'][p['material']];matname=mat['name']
        if matname not in byname:
            assert 'Texture' not in json.dumps(mat), 'New textured material needs explicit texture remapping'
            byname[matname]=len(dst['materials']);dst['materials'].append(copy.deepcopy(mat))
        p['material']=byname[matname]
        ext=p['extensions']['KHR_draco_mesh_compression'];view=src['bufferViews'][ext['bufferView']]
        binary.extend(b'\0'*(-len(binary)%4));offset=len(binary)
        start=view.get('byteOffset',0);binary.extend(payload[start:start+view['byteLength']])
        ext['bufferView']=len(dst['bufferViews']);dst['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':view['byteLength']})
        for field,index in list(p['attributes'].items())+[('indices',p['indices'])]:
            a=copy.deepcopy(src['accessors'][index]);assert 'bufferView' not in a
            if field=='indices':p[field]=len(dst['accessors'])
            else:p['attributes'][field]=len(dst['accessors'])
            dst['accessors'].append(a)
        primitives.append(p)
    dst['meshes'][target['mesh']]['primitives']=primitives
    binary.extend(b'\0'*(-len(binary)%4));dst['buffers'][0]['byteLength']=len(binary)
    header=json.dumps(dst,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def compact_static_accessors(path):
    """Drop orphaned metadata from repeated bounded static-mesh replacements."""
    doc,binary=unpack(path.read_bytes())
    assert not doc.get('animations') and not doc.get('skins')
    refs=[]
    for mesh in doc['meshes']:
        for p in mesh['primitives']:
            refs.extend((p['attributes'],key) for key in p['attributes'])
            if 'indices' in p:refs.append((p,'indices'))
            for target in p.get('targets',[]):refs.extend((target,key) for key in target)
    live=sorted({obj[key] for obj,key in refs});remap={old:new for new,old in enumerate(live)}
    for obj,key in refs:obj[key]=remap[obj[key]]
    doc['accessors']=[doc['accessors'][i] for i in live]
    header=json.dumps(doc,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def preserve_named_road_materials(raw,path,names):
    new,_=unpack(path.read_bytes())
    newp=new['meshes'][mesh_nodes_by_name(new)['roads']['mesh']]['primitives']
    # Reuse the generic copier with a tiny source doc containing selected original
    # primitives, then combine those remapped primitives with the changed ones.
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        temp=Path(directory)/'roads.glb';temp.write_bytes(path.read_bytes())
        replace_node_geometry(raw,temp,'roads');restored,binary=unpack(temp.read_bytes())
        rp=restored['meshes'][mesh_nodes_by_name(restored)['roads']['mesh']]['primitives']
        combined=[p for p in newp if new['materials'][p['material']]['name'] not in names]
        combined += [p for p in rp if restored['materials'][p['material']]['name'] in names]
        restored['meshes'][mesh_nodes_by_name(restored)['roads']['mesh']]['primitives']=combined
        header=json.dumps(restored,separators=(',',':')).encode();header+=b' '*(-len(header)%4)
        path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def repaired_source_roads(old,x,y,colors):
    mesh=Mesh();mesh.v=[tuple(v.co) for v in old.data.vertices]
    mesh.f=[tuple(p.vertices) for p in old.data.polygons]
    mesh.m=[colors[old.data.materials[p.material_index].name] for p in old.data.polygons]
    mesh.source_uvs=[[tuple(old.data.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in old.data.polygons]
    fixed=repair_roads(mesh,x,y,colors)
    def outside_signatures(value):
        result=Counter()
        a,b,c,d=REPAIR_BOUNDS
        for face,mat,uvs in zip(value.f,value.m,value.source_uvs):
            points=tuple(value.v[i] for i in face)
            if max(v[0] for v in points)<x+a or min(v[0] for v in points)>x+c or max(v[1] for v in points)<y+b or min(v[1] for v in points)>y+d:
                result[(points,mat,tuple(uvs))]+=1
        return result
    retained=outside_signatures(mesh);after=outside_signatures(fixed)
    assert not (retained-after),'Unrelated road coordinates or UVs changed'
    print('Unchanged road faces outside south gate:',sum(retained.values()),flush=True)
    obj=fixed.object('south-gate-road-repair',old.users_collection[0],dict(old.items()))
    for p,uvs in zip(obj.data.polygons,fixed.source_uvs):
        for i,uv in zip(p.loop_indices,uvs):obj.data.uv_layers.active.data[i].uv=uv
    unchanged={name for name,index in colors.items() if index not in fixed.changed_materials}
    return obj,unchanged


def export_roads(source,path):
    # Retain the established foundation split and UV/position precision contract.
    from export_repaired_ground import road_object
    from foundation_contract import load_foundations
    obj=road_object(source,load_foundations(ROOT)['foundations'],json.loads((ROOT/'public/data/pavings.json').read_text())['pavings'])
    for uvbits,target in [(12,path),(10,path.with_name('roads-uv.glb'))]:
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        with omit_unused_uvs(deduplicate_vertices=True,share_position_bounds=True):
            bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_extras=True,
                export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,
                export_draco_position_quantization=18,export_draco_texcoord_quantization=uvbits,
                export_draco_normal_quantization=6,export_materials='EXPORT',export_cameras=False,export_lights=False)
    preserve_geometry(path.with_name('roads-uv.glb').read_bytes(),path,['roads'],materials={'road'})
    bpy.data.objects.remove(obj,do_unlink=True);source.name='roads'


def main():
    models = ROOT / 'public/models'
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in models.glob('*.glb')}
    base_before = (models / 'base.glb').read_bytes()
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'))
    old, = [o for o in bpy.context.scene.objects if o.get('landmark') == 'south-gate']
    roads=bpy.data.objects['roads']
    MATERIALS[:] = list(bpy.data.materials)
    colors = {mat.name: i for i, mat in enumerate(MATERIALS)}
    ensure_materials(colors)
    record = next(l for l in json.loads((ROOT / 'public/data/landmarks.json').read_text()) if l['id'] == 'south-gate')
    x0, y0, x1, y1 = record['bounds']
    def build(detail):
        return south_gate((x0+x1)/2, (y0+y1)/2, record['elevation'], colors,
                          detail, footprint_width=x1-x0, footprint_depth=y1-y0)
    untouched = {o.name: (o.as_pointer(), o.data.as_pointer() if o.data else None)
                 for o in bpy.context.scene.objects if o not in (old,roads)}
    props = dict(old.items())
    collection = old.users_collection[0]
    name = old.name
    high = build(True)
    low = build(False)
    def material_vertices(mesh, name):
        return {mesh.v[i] for face, mat in zip(mesh.f, mesh.m) if mat == colors[name] for i in face}
    # Plant stems/pots and lettering must not jump when a near model replaces the base.
    for material in ['bark', 'gateRed']:
        assert material_vertices(high, material) == material_vertices(low, material), material
    def pot_centres(mesh):
        result=set()
        for face,mat in zip(mesh.f,mesh.m):
            if mat!=colors['gatePot']:continue
            points=[mesh.v[i] for i in face]
            if max(p[2] for p in points)-min(p[2] for p in points)<1e-6:
                result.add(tuple(round(sum(p[k] for p in points)/len(points),5) for k in range(3)))
        return result
    assert pot_centres(high)==pot_centres(low),'Pot placement differs between LODs'
    with tempfile.TemporaryDirectory(prefix='gxu-south-gate-') as directory:
        temp = Path(directory)
        near = high.object('landmark-south-gate', collection, {'landmark': 'south-gate', 'layer': 'buildings', 'zone': '', 'sportsId': ''})
        export(near, temp / 'south-gate.glb')
        near_mesh = near.data
        bpy.data.objects.remove(near, do_unlink=True)
        bpy.data.meshes.remove(near_mesh)
        far = low.object('landmark-south-gate', collection, {'landmark': 'south-gate', 'layer': 'buildings', 'zone': '', 'sportsId': ''})
        export(far, temp / 'far.glb', base=True)
        far_mesh = far.data
        bpy.data.objects.remove(far, do_unlink=True)
        bpy.data.meshes.remove(far_mesh)
        candidate = temp / 'base.glb'
        candidate.write_bytes(base_before)
        # Replace this gate and its road patch; retain every other node verbatim.
        replace_node_geometry((temp / 'far.glb').read_bytes(), candidate, 'landmark-south-gate')
        fixed_roads,unchanged_materials=repaired_source_roads(roads,(x0+x1)/2,(y0+y1)/2,colors)
        old_roads_mesh=roads.data
        bpy.data.objects.remove(roads,do_unlink=True)
        if old_roads_mesh.users==0:bpy.data.meshes.remove(old_roads_mesh)
        fixed_roads.name='roads'
        export_roads(fixed_roads,temp/'roads.glb')
        replace_node_geometry((temp/'roads.glb').read_bytes(),candidate,'roads')
        # Reuse only streams whose source faces were not clipped by the junction.
        preserve_named_road_materials(base_before,candidate,{'white','road','path'} & unchanged_materials)
        compact_static_accessors(candidate)
        compact_buffer_views(candidate)
        a, b = signatures(base_before), signatures(candidate.read_bytes())
        assert a.keys() == b.keys()
        assert all(a[k] == b[k] for k in a if k not in ('landmark-south-gate','roads'))
        manifest_before=json.loads((ROOT/'public/data/models.json').read_text())
        assert candidate.stat().st_size+manifest_before['trees']['bytes']<=6_020_000,'Initial load budget exceeded'
        old_mesh = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        # road_object temporarily uses the source road material table.
        MATERIALS[:]=[bpy.data.materials[n] for n,_ in sorted(colors.items(),key=lambda kv:kv[1])]
        geometry.MATERIALS=MATERIALS
        high.object(name, collection, props)
        assert all((bpy.data.objects[k].as_pointer(), bpy.data.objects[k].data.as_pointer() if bpy.data.objects[k].data else None) == v
                   for k, v in untouched.items())
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'blender/gxu-campus.blend'), compress=True)
        (models / 'base.glb').write_bytes(candidate.read_bytes())
        (models / 'south-gate.glb').write_bytes((temp / 'south-gate.glb').read_bytes())
    manifest_path = ROOT / 'public/data/models.json'
    manifest = json.loads(manifest_path.read_text())
    for entry in [manifest['base'], next(e for e in manifest['landmarks'] if e['id'] == 'south-gate')]:
        raw = (ROOT / 'public' / entry['url']).read_bytes()
        entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    changed = [p.name for p in models.glob('*.glb') if before[p.name] != hashlib.sha256(p.read_bytes()).hexdigest()]
    assert set(changed) <= {'base.glb', 'south-gate.glb'}
    report = {'changedGlbs': sorted(changed), 'retainedBaseNodes': len(a)-2,
              'retainedSourceObjects': len(untouched), 'wordmark': 'official handwritten outline, same mesh in both LODs',
              'glyphDepthMeters': .045, 'checks': 'passed'}
    report['plantAnchorsAndLetteringMatchAcrossLods'] = True
    report['changedBaseNodes']=['landmark-south-gate','roads']
    report['roadRepairBounds']=[(x0+x1)/2+REPAIR_BOUNDS[0],(y0+y1)/2+REPAIR_BOUNDS[1],(x0+x1)/2+REPAIR_BOUNDS[2],(y0+y1)/2+REPAIR_BOUNDS[3]]
    (ROOT / 'docs/model-checks/south-gate-update.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
