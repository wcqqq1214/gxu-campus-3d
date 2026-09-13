"""Exercise the real Draco exporter on mixed plain and textured primitives."""
import bpy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blender'))
from export_attributes import needs_texcoords, omit_unused_uvs
from preserve_glb_geometry import unpack
from geometry import Mesh, material, MATERIALS

plain = SimpleNamespace(extensions=None, pbr_metallic_roughness=None)
assert not needs_texcoords(plain)
assert needs_texcoords(SimpleNamespace(extensions={'unknown': {}}, pbr_metallic_roughness=None))
assert not needs_texcoords(SimpleNamespace(extensions={'KHR_materials_clearcoat': SimpleNamespace(extension={})}, pbr_metallic_roughness=None))
assert needs_texcoords(SimpleNamespace(extensions={'KHR_materials_anisotropy': SimpleNamespace(extension={'anisotropyStrength': .2})}, pbr_metallic_roughness=None))
for slot in ['normal_texture', 'occlusion_texture', 'emissive_texture']:
    assert needs_texcoords(SimpleNamespace(**{**vars(plain), slot: object()}))
for slot in ['base_color_texture', 'metallic_roughness_texture']:
    assert needs_texcoords(SimpleNamespace(extensions=None, pbr_metallic_roughness=SimpleNamespace(**{slot: object()})))

bpy.ops.wm.read_factory_settings(use_empty=True)
a = material('plain', (.4,.5,.6))
b = material('textured', (.5,.6,.7))
texture = bpy.data.images.new('test texture', width=4, height=4)
texture.generated_color = (.2,.6,.3,1)
texture.pack()
mat = MATERIALS[b]
node = mat.node_tree.nodes.new('ShaderNodeTexImage')
node.image = texture
mat.node_tree.links.new(node.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
mesh = Mesh()
mesh.box(0,0,1,2,3,2,a)
mesh.box(5,0,1,2,3,2,b)
obj = mesh.object('mixed', bpy.context.scene.collection)
obj.select_set(True)
source_uv = [tuple(v.uv) for v in obj.data.uv_layers.active.data]

with tempfile.TemporaryDirectory() as directory:
    def export(name):
        path = Path(directory) / (name+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                 export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
        return unpack(path.read_bytes())[0]
    before = export('before')
    with omit_unused_uvs():
        after = export('after')
    restored = export('restored')
    def attrs(doc):
        return {doc['materials'][p['material']]['name']:set(p['attributes'])
                for m in doc['meshes'] for p in m['primitives']}
    assert 'TEXCOORD_0' in attrs(before)['plain']
    assert attrs(after)['plain'] == attrs(before)['plain'] - {'TEXCOORD_0'}
    assert attrs(after)['textured'] == attrs(before)['textured']
    assert attrs(restored) == attrs(before)
    assert [tuple(v.uv) for v in obj.data.uv_layers.active.data] == source_uv
    try:
        with omit_unused_uvs():
            raise RuntimeError('cleanup probe')
    except RuntimeError:
        pass
    assert bpy.context.preferences.addons.get('export_attributes') is None
print('Passed: actual mixed-material Draco export, all core texture slots, unknown extension retention, source UV preservation and scoped hook cleanup')
