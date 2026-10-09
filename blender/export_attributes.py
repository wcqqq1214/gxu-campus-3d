"""Omit unused UV streams before Draco compression; retain editable source UVs."""
from contextlib import contextmanager
import sys

_deduplicate_vertices = False
_share_position_bounds = False


def needs_texcoords(material):
    # Unknown extensions may sample a UV set. Keep those streams conservatively.
    if material is None:
        return True
    empty_exporter_extensions = {
        'KHR_materials_clearcoat', 'KHR_materials_transmission',
        'KHR_materials_emissive_strength', 'KHR_materials_specular',
        'KHR_materials_anisotropy', 'KHR_materials_ior',
    }
    for name, extension in (material.extensions or {}).items():
        # Blender gathers empty placeholders before removing unused extensions.
        # Only those known-empty values are safe; retain UVs for active factors
        # too (anisotropy, for example, can use the tangent frame without a map).
        if name not in empty_exporter_extensions or getattr(extension, 'extension', extension) != {}:
            return True
    if any(getattr(material, name, None) is not None for name in (
            'normal_texture', 'occlusion_texture', 'emissive_texture')):
        return True
    pbr = material.pbr_metallic_roughness
    return pbr is not None and any(getattr(pbr, name, None) is not None for name in (
        'base_color_texture', 'metallic_roughness_texture'))


class glTF2ExportUserExtension:
    is_critical = True

    def gather_mesh_hook(self, mesh, blender_data, blender_object,
                         vertex_groups, modifiers, materials, export_settings):
        for primitive in mesh.primitives:
            if not needs_texcoords(primitive.material):
                # Accessor caches may be shared; leave the original mapping untouched.
                primitive.attributes = {name: value for name, value in primitive.attributes.items()
                                        if not name.startswith('TEXCOORD_')}
            if _deduplicate_vertices:
                from vertex_dedup import deduplicate_primitive_vertices
                deduplicate_primitive_vertices(primitive)
        if _share_position_bounds:
            from vertex_dedup import share_position_quantization_bounds
            share_position_quantization_bounds(mesh.primitives)


@contextmanager
def omit_unused_uvs(*, deduplicate_vertices=False, share_position_bounds=False):
    """Register the supported exporter hook only for this process and scope."""
    import bpy
    global _deduplicate_vertices, _share_position_bounds
    previous_deduplication = _deduplicate_vertices
    previous_shared_bounds = _share_position_bounds
    name = __name__
    assert sys.modules[name].glTF2ExportUserExtension is glTF2ExportUserExtension
    existing = bpy.context.preferences.addons.get(name)
    if existing is None:
        addon = bpy.context.preferences.addons.new()
        addon.module = name
    try:
        _deduplicate_vertices = deduplicate_vertices
        _share_position_bounds = share_position_bounds
        yield
    finally:
        _deduplicate_vertices = previous_deduplication
        _share_position_bounds = previous_shared_bounds
        if existing is None:
            bpy.context.preferences.addons.remove(addon)


def quantized_terrain_collapses(mesh, excluded, bits):
    """Find triangles collapsed by the same Float32, Y-up Draco position grid.

    Keep the original domain: removing a sole extremum would change every
    remaining decoded position. Non-triangular polygons are left untouched.
    """
    import numpy as np
    if type(bits) is not int or not 1 <= bits <= 30:
        raise ValueError('Expected 1–30 Draco position quantization bits')
    active = [p for p in mesh.polygons if p.index not in excluded]
    if not active:
        return set()
    xyz = np.array([tuple(v.co) for v in mesh.vertices], dtype=np.float32)
    xyz = xyz[:, [0, 2, 1]]
    xyz[:, 2] *= -1  # Match the glTF exporter's default Y-up conversion.
    used = np.array(sorted({i for p in active for i in p.vertices}))
    minimum, maximum = xyz[used].min(axis=0), xyz[used].max(axis=0)
    extent = np.float32((maximum - minimum).max())
    if not np.isfinite(xyz[used]).all() or extent <= 0:
        return set()
    max_value = (1 << bits) - 1
    values = np.floor((xyz - minimum) * np.float32(max_value / float(extent)) + np.float32(.5))
    decoded = (values * np.float32(float(extent) / max_value) + minimum).astype(np.float64)
    triangles = [p for p in active if len(p.vertices) == 3]
    if not triangles:
        return set()
    indices = np.array([tuple(p.vertices) for p in triangles])
    a, b, c = (decoded[indices[:, i]] for i in range(3))
    zero = np.all(np.cross(b - a, c - a) == 0, axis=1)
    collapsed = {p.index for p, flag in zip(triangles, zero) if flag}
    kept = sorted({i for p in active if p.index not in collapsed for i in p.vertices})
    if not kept or not (np.array_equal(xyz[kept].min(axis=0), minimum)
                        and np.array_equal(xyz[kept].max(axis=0), maximum)):
        return set()
    return collapsed


@contextmanager
def omit_zero_area_terrain_faces(obj, *, position_quantization_bits=None):
    """Drop collapsed triangles only from a temporary terrain export mesh.

    Optional quantized cleanup uses the caller's existing position precision;
    it does not lower that precision or modify the editable source geometry.
    """
    import bpy
    import bmesh
    original=obj.data
    collapsed=[]
    if obj.get('layer')=='terrain' and not original.shape_keys and not obj.modifiers:
        for face in original.polygons:
            if len(face.vertices)!=3:
                continue
            a,b,c=[tuple(original.vertices[i].co) for i in face.vertices]
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            if cross==(0,0,0):
                collapsed.append(face.index)
        if position_quantization_bits is not None:
            from mathutils import Matrix
            if obj.matrix_world != Matrix.Identity(4) or any(p.use_smooth for p in original.polygons):
                raise ValueError('Quantized terrain cleanup requires untransformed, flat-shaded geometry')
            collapsed = sorted(set(collapsed) | quantized_terrain_collapses(
                original, set(collapsed), position_quantization_bits))
    if not collapsed:
        yield 0
        return
    temporary=original.copy();bm=bmesh.new()
    try:
        bm.from_mesh(temporary);bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.faces[i] for i in collapsed],context='FACES_ONLY')
        bm.to_mesh(temporary);temporary.update();obj.data=temporary
        yield len(collapsed)
    finally:
        obj.data=original;bm.free();bpy.data.meshes.remove(temporary)
