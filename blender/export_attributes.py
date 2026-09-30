"""Omit unused UV streams before Draco compression; retain editable source UVs."""
from contextlib import contextmanager
import sys


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
            if needs_texcoords(primitive.material):
                continue
            # Accessor caches may be shared; leave the original mapping untouched.
            primitive.attributes = {name: value for name, value in primitive.attributes.items()
                                    if not name.startswith('TEXCOORD_')}


@contextmanager
def omit_unused_uvs():
    """Register the supported exporter hook only for this process and scope."""
    import bpy
    name = __name__
    assert sys.modules[name].glTF2ExportUserExtension is glTF2ExportUserExtension
    existing = bpy.context.preferences.addons.get(name)
    if existing is None:
        addon = bpy.context.preferences.addons.new()
        addon.module = name
    try:
        yield
    finally:
        if existing is None:
            bpy.context.preferences.addons.remove(addon)


@contextmanager
def omit_zero_area_terrain_faces(obj):
    """Drop exactly collapsed triangle faces only in the temporary export mesh."""
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
