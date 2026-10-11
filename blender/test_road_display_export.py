"""Removing an extremal road tail must not move the surviving decoded vertices."""
import sys
import json
import subprocess
import tempfile
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry
from geometry import Mesh, material
from export_attributes import omit_unused_uvs


def export(mesh, path, domain=None):
    obj = mesh.object('roads', bpy.context.scene.collection)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    with omit_unused_uvs(deduplicate_vertices=True, share_position_bounds=True,
                         position_domain=domain):
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format='GLB', use_selection=True,
            export_draco_mesh_compression_enable=True,
            export_draco_position_quantization=18, export_draco_normal_quantization=6)


def decode(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    mesh = Mesh()
    mesh.v = [tuple(v.co) for v in obj.data.vertices]
    mesh.f = [tuple(p.vertices) for p in obj.data.polygons]
    mesh.m = [p.material_index for p in obj.data.polygons]
    geometry.MATERIALS = list(obj.data.materials)
    return mesh


bpy.ops.wm.read_factory_settings(use_empty=True)
material('asphalt', (.3, .3, .3))
material('edge', (.8, .8, .8))
mesh = Mesh()
a, b, c = (.137, .291, .21), (12.734, 18.419, .61), (-110, 4, .1)
mesh.face([a, b, c], 0)
mesh.face([a, (130, 5, .1), b], 1)
mesh.face([(0, 1291.73, 2), (10, 1270, 2), (-10, 1270, 2)], 0)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    export(mesh, root/'before.glb')
    old = decode(root/'before.glb')
    xyz = np.array(old.v, dtype=np.float32)[:, [0, 2, 1]]
    xyz[:, 2] *= -1
    origin = xyz.min(axis=0)
    domain = {'origin': origin.tolist(), 'range': float((xyz.max(axis=0)-origin).max())}
    trimmed = Mesh()
    for face, mat in zip(old.f, old.m):
        if all(old.v[i][1] < 100 for i in face):
            trimmed.face([old.v[i] for i in face], mat)
    expected = set(trimmed.v)
    export(trimmed, root/'unpinned.glb')
    export(trimmed, root/'pinned.glb', domain)
    unpinned = decode(root/'unpinned.glb')
    pinned = decode(root/'pinned.glb')
    assert any(min(np.linalg.norm(np.array(p)-q) for q in unpinned.v) > .0001 for p in expected)
    assert set(pinned.v) == expected, (set(pinned.v)-expected, expected-set(pinned.v))
    assert len(pinned.f) == 2, 'Quantization anchors must not become visible geometry'
    # A second cleanup must recover the first export's original encoded grid,
    # even though its northmost vertices no longer exist in the decoded mesh.
    project = Path(__file__).resolve().parents[1]
    encoded_domain = json.loads(subprocess.check_output(
        ['node', str(project/'scripts/road-position-domain.mjs'), str(root/'pinned.glb')],
        cwd=project, text=True))
    assert encoded_domain == {**domain, 'bits': 18}
    second = Mesh()
    for face, mat in zip(pinned.f, pinned.m):
        if mat == 0:
            second.face([pinned.v[i] for i in face], mat)
    expected_second = set(second.v)
    export(second, root/'second.glb', encoded_domain)
    assert set(decode(root/'second.glb').v) == expected_second
print('ROAD_DISPLAY_FIXED_QUANTIZATION passed', flush=True)
